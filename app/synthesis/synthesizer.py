import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import LLM_MODEL, OPENAI_API_KEY, SYNTHESIS_MAX_ATTEMPTS
from app.github.client import GitHubAPIError, GitHubClient
from app.memory.store import record_capability_result, save_capability


SYNTHESIS_PROMPT = """You design GitHub REST API operations for an autonomous agent.

Return ONLY valid JSON with this shape:
{
  "name": "snake_case_capability_name",
  "description": "what the capability does",
  "method": "GET|POST|PATCH|PUT|DELETE",
  "path": "/repos/{owner}/{repo}/...",
  "query": {"optional": "query params"},
  "body": {"optional": "json body for write operations"}
}

Rules:
- Use GitHub REST API v3 paths only.
- Include {owner} and {repo} placeholders in the path when needed.
- Do not invent unsupported endpoints.
- Keep the capability focused on one operation.
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM did not return JSON")
    return json.loads(match.group())


def synthesize_capability(
    client: GitHubClient,
    operation_description: str,
    test_params: dict | None = None,
) -> dict:
    """Generate, test, and register a new GitHub capability at runtime."""
    llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    last_error = "Unknown synthesis failure"

    for attempt in range(1, SYNTHESIS_MAX_ATTEMPTS + 1):
        response = llm.invoke(
            [
                SystemMessage(content=SYNTHESIS_PROMPT),
                HumanMessage(
                    content=(
                        f"Operation needed: {operation_description}\n"
                        f"Attempt: {attempt}\n"
                        f"Previous error: {last_error}"
                    )
                ),
            ]
        )
        spec = _extract_json(response.content)
        name = spec["name"]
        description = spec["description"]
        api_spec = {
            "method": spec["method"],
            "path": spec["path"],
            "query": spec.get("query"),
            "body": spec.get("body"),
        }

        try:
            client.execute_spec(api_spec, params=test_params or {})
            save_capability(name=name, description=description, api_spec=api_spec, synthesized=True)
            record_capability_result(name, success=True)
            return {
                "name": name,
                "description": description,
                "api_spec": api_spec,
                "attempts": attempt,
                "status": "registered",
            }
        except (GitHubAPIError, ValueError, KeyError) as error:
            last_error = str(error)
            record_capability_result(name, success=False, constraint=last_error)

    raise RuntimeError(
        f"Could not synthesize capability after {SYNTHESIS_MAX_ATTEMPTS} attempts: {last_error}"
    )
