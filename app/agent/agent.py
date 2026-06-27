import time
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.store.postgres import PostgresStore

from app.agent.prompts import SYSTEM_PROMPT
from app.config.settings import DB_URL, LLM_MODEL
from app.github.client import GitHubClient
from app.github.tools import build_github_tools
from app.memory.store import (
    build_learning_context,
    find_similar_executions,
    memory_snapshot,
    save_execution,
)
from app.schemas.schemas import ExecutionReport, MemoryDelta, StepResult
from sqlmodel import SQLModel

from app.memory.models import CapabilityMemory, ExecutionMemory  # noqa: F401
from app.memory.store import engine


def _ensure_tables() -> None:
    SQLModel.metadata.create_all(engine)


def _extract_steps(messages: list[Any]) -> list[StepResult]:
    steps: list[StepResult] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        detail = message.content if isinstance(message.content, str) else str(message.content)
        status = "error" if detail.startswith("ERROR:") else "success"
        steps.append(
            StepResult(
                instruction=message.name or "unknown_tool",
                status=status,
                detail=detail[:500],
            )
        )
    return steps


def _derive_status(steps: list[StepResult]) -> str:
    if not steps:
        return "failed"
    errors = [step for step in steps if step.status == "error"]
    if not errors:
        return "success"
    if len(errors) < len(steps):
        return "partial"
    return "failed"


def _derive_decomposition(messages: list[Any], steps: list[StepResult]) -> list[str]:
    for message in messages:
        if isinstance(message, AIMessage) and message.content:
            text = message.content if isinstance(message.content, str) else str(message.content)
            lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
            numbered = [line for line in lines if line[:2].isdigit() or line.startswith("-")]
            if numbered:
                return numbered[:8]
    return [step.instruction for step in steps]


def _learning_notes(instruction: str, api_calls: int, duration_ms: float, status: str) -> list[str]:
    notes: list[str] = []
    similar = find_similar_executions(instruction)
    if not similar:
        notes.append("First execution for this instruction pattern.")
        return notes

    successful = [record for record in similar if record.status == "success"]
    if successful:
        best = min(successful, key=lambda record: (record.api_call_count, record.duration_ms))
        if api_calls < best.api_call_count:
            notes.append(
                f"API calls improved from {best.api_call_count} to {api_calls} versus best prior run."
            )
        if duration_ms < best.duration_ms:
            notes.append(
                f"Duration improved from {best.duration_ms:.0f}ms to {duration_ms:.0f}ms."
            )

    prior_failures = [record for record in similar if record.status != "success"]
    if prior_failures and status == "success":
        notes.append("Recovered from prior failed attempts by reusing learned constraints.")

    return notes


def call_agent(prompt: str) -> ExecutionReport:
    _ensure_tables()
    client = GitHubClient()
    client.reset_call_count()

    memory_before = memory_snapshot()
    learning_context = build_learning_context(prompt)
    tools = build_github_tools(client)

    system_prompt = (
        f"{SYSTEM_PROMPT}\n\n## Memory context\n{learning_context}\n"
        f"Repository: {client.owner}/{client.repo}\n"
    )

    started = time.perf_counter()

    with PostgresStore.from_conn_string(DB_URL) as store:
        store.setup()
        agent = create_agent(
            model=LLM_MODEL,
            tools=tools,
            system_prompt=system_prompt,
            store=store,
        )
        agent_output = agent.invoke({"messages": [{"role": "user", "content": prompt}]})

    duration_ms = (time.perf_counter() - started) * 1000
    messages = agent_output["messages"]
    steps = _extract_steps(messages)
    status = _derive_status(steps)
    decomposition = _derive_decomposition(messages, steps)
    api_calls = client.api_call_count

    failure_reason = ""
    if status != "success":
        failed = next((step for step in steps if step.status == "error"), None)
        failure_reason = failed.detail if failed else "Agent finished without successful tool calls."

    save_execution(
        instruction=prompt,
        decomposition=decomposition,
        steps=[step.model_dump() for step in steps],
        status=status,
        duration_ms=duration_ms,
        api_call_count=api_calls,
        failure_reason=failure_reason,
    )

    with PostgresStore.from_conn_string(DB_URL) as store:
        store.put(("executions",), prompt, {"steps": [step.model_dump() for step in steps], "status": status})

    memory_after = memory_snapshot()
    before_names = {capability["name"] for capability in memory_before["capabilities"]}
    updated_capabilities = [
        capability["name"]
        for capability in memory_after["capabilities"]
        if capability["name"] not in before_names
    ]

    report = ExecutionReport(
        instruction=prompt,
        status=status,
        decomposition=decomposition,
        steps=steps,
        duration_ms=duration_ms,
        api_calls=api_calls,
        failure_reason=failure_reason,
        learning_notes=_learning_notes(prompt, api_calls, duration_ms, status),
        memory_before=memory_before,
        memory_after=memory_after,
        memory_delta=MemoryDelta(
            execution_saved=True,
            capabilities_updated=updated_capabilities,
        ),
    )
    return report
