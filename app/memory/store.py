import json
import re
from typing import Any

from sqlmodel import Session, create_engine, select

from app.config.settings import DB_URL
from app.memory.models import CapabilityMemory, ExecutionMemory


engine = create_engine(DB_URL)


def normalize_instruction(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def instruction_key(text: str) -> str:
    words = sorted(set(normalize_instruction(text).split()))
    return " ".join(words[:12])


def save_execution(
    instruction: str,
    decomposition: list[str],
    steps: list[dict[str, Any]],
    status: str,
    duration_ms: float,
    api_call_count: int,
    failure_reason: str = "",
) -> ExecutionMemory:
    record = ExecutionMemory(
        instruction=instruction,
        instruction_key=instruction_key(instruction),
        decomposition=json.dumps(decomposition),
        steps_json=json.dumps(steps),
        status=status,
        duration_ms=duration_ms,
        api_call_count=api_call_count,
        failure_reason=failure_reason,
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def find_similar_executions(instruction: str, limit: int = 5) -> list[ExecutionMemory]:
    key = instruction_key(instruction)
    words = set(key.split())

    with Session(engine) as session:
        records = session.exec(
            select(ExecutionMemory).order_by(ExecutionMemory.created_at.desc())
        ).all()

    scored: list[tuple[float, ExecutionMemory]] = []
    for record in records:
        record_words = set(record.instruction_key.split())
        if not record_words:
            continue
        overlap = len(words & record_words) / max(len(words | record_words), 1)
        if overlap >= 0.4:
            scored.append((overlap, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in scored[:limit]]


def get_capability(name: str) -> CapabilityMemory | None:
    with Session(engine) as session:
        return session.exec(
            select(CapabilityMemory).where(CapabilityMemory.name == name)
        ).first()


def list_capabilities() -> list[CapabilityMemory]:
    with Session(engine) as session:
        return session.exec(select(CapabilityMemory)).all()


def save_capability(
    name: str,
    description: str,
    api_spec: dict[str, Any],
    synthesized: bool = False,
) -> CapabilityMemory:
    with Session(engine) as session:
        existing = session.exec(
            select(CapabilityMemory).where(CapabilityMemory.name == name)
        ).first()
        if existing:
            existing.description = description
            existing.api_spec_json = json.dumps(api_spec)
            existing.synthesized = synthesized
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        record = CapabilityMemory(
            name=name,
            description=description,
            api_spec_json=json.dumps(api_spec),
            synthesized=synthesized,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def record_capability_result(name: str, success: bool, constraint: str | None = None) -> None:
    with Session(engine) as session:
        record = session.exec(
            select(CapabilityMemory).where(CapabilityMemory.name == name)
        ).first()
        if not record:
            return

        if success:
            record.success_count += 1
        else:
            record.failure_count += 1

        if constraint:
            constraints = json.loads(record.constraints_json or "[]")
            if constraint not in constraints:
                constraints.append(constraint)
                record.constraints_json = json.dumps(constraints)

        session.add(record)
        session.commit()


def build_learning_context(instruction: str) -> str:
    similar = find_similar_executions(instruction)
    if not similar:
        return "No prior executions for similar instructions."

    lines = ["Prior similar executions:"]
    for record in similar:
        steps = json.loads(record.steps_json)
        decomposition = json.loads(record.decomposition)
        lines.append(
            f"- status={record.status}, duration_ms={record.duration_ms:.0f}, "
            f"api_calls={record.api_call_count}, decomposition={decomposition}, "
            f"failed_steps={[step['instruction'] for step in steps if step['status'] == 'error']}"
        )

    best = min(
        (record for record in similar if record.status == "success"),
        key=lambda record: (record.api_call_count, record.duration_ms),
        default=None,
    )
    if best:
        lines.append(
            f"Best prior run used {best.api_call_count} API calls in {best.duration_ms:.0f}ms. "
            "Prefer that decomposition when possible."
        )

    capabilities = list_capabilities()
    if capabilities:
        lines.append("Known capabilities:")
        for capability in capabilities:
            total = capability.success_count + capability.failure_count
            rate = capability.success_count / total if total else 0
            constraints = json.loads(capability.constraints_json or "[]")
            lines.append(
                f"- {capability.name}: success_rate={rate:.0%}, constraints={constraints}"
            )

    return "\n".join(lines)


def memory_snapshot() -> dict[str, Any]:
    with Session(engine) as session:
        executions = session.exec(
            select(ExecutionMemory).order_by(ExecutionMemory.created_at.desc()).limit(10)
        ).all()
        capabilities = session.exec(select(CapabilityMemory)).all()

    return {
        "executions": [
            {
                "instruction": record.instruction,
                "status": record.status,
                "duration_ms": record.duration_ms,
                "api_call_count": record.api_call_count,
                "decomposition": json.loads(record.decomposition),
            }
            for record in executions
        ],
        "capabilities": [
            {
                "name": record.name,
                "description": record.description,
                "success_count": record.success_count,
                "failure_count": record.failure_count,
                "synthesized": record.synthesized,
                "constraints": json.loads(record.constraints_json or "[]"),
            }
            for record in capabilities
        ],
    }
