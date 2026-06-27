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
- Include {owner} and {repo} placeholders in the path.
- Do not invent unsupported endpoints.
- Keep the capability focused on one operation.

Examples:
- List open milestones:
  {"name":"list_open_milestones","description":"List open milestones","method":"GET","path":"/repos/{owner}/{repo}/milestones","query":{"state":"open","per_page":100}}
- List releases:
  {"name":"list_releases","description":"List repository releases","method":"GET","path":"/repos/{owner}/{repo}/releases","query":{"per_page":100}}
"""


KNOWN_OPERATIONS: list[tuple[tuple[str, ...], dict]] = [
    (
        ("milestone", "milestones"),
        {
            "name": "list_open_milestones",
            "description": "List open milestones in the configured repository",
            "method": "GET",
            "path": "/repos/{owner}/{repo}/milestones",
            "query": {"state": "open", "per_page": 100},
        },
    ),
    (
        ("release", "releases"),
        {
            "name": "list_releases",
            "description": "List releases in the configured repository",
            "method": "GET",
            "path": "/repos/{owner}/{repo}/releases",
            "query": {"per_page": 100},
        },
    ),
    (
        ("collaborator", "collaborators"),
        {
            "name": "list_collaborators",
            "description": "List repository collaborators",
            "method": "GET",
            "path": "/repos/{owner}/{repo}/collaborators",
            "query": {"per_page": 100},
        },
    ),
]


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM did not return JSON")
    return json.loads(match.group())


def _normalize_spec(spec: dict) -> dict:
    path = spec["path"]
    if not path.startswith("/"):
        path = f"/{path}"
    if "{owner}" not in path and "/repos/" in path:
        path = re.sub(
            r"/repos/[^/]+/[^/]+/",
            "/repos/{owner}/{repo}/",
            path,
            count=1,
        )
    return {
        "name": spec["name"],
        "description": spec["description"],
        "method": spec["method"].upper(),
        "path": path,
        "query": spec.get("query"),
        "body": spec.get("body"),
    }


def _known_spec_for(operation_description: str) -> dict | None:
    lowered = operation_description.lower()
    for keywords, spec in KNOWN_OPERATIONS:
        if any(keyword in lowered for keyword in keywords):
            return _normalize_spec(spec)
    return None


def _register_spec(client: GitHubClient, spec: dict, source: str) -> dict:
    api_spec = {
        "method": spec["method"],
        "path": spec["path"],
        "query": spec.get("query"),
        "body": spec.get("body"),
    }
    client.execute_spec(api_spec)
    save_capability(
        name=spec["name"],
        description=spec["description"],
        api_spec=api_spec,
        synthesized=True,
    )
    record_capability_result(spec["name"], success=True)
    return {
        "name": spec["name"],
        "description": spec["description"],
        "api_spec": api_spec,
        "source": source,
        "status": "registered",
    }


def synthesize_capability(
    client: GitHubClient,
    operation_description: str,
    test_params: dict | None = None,
) -> dict:
    """Generate, test, and register a new GitHub capability at runtime."""
    client.verify_repository()

    known = _known_spec_for(operation_description)
    if known:
        try:
            result = _register_spec(client, known, source="known_template")
            result["attempts"] = 1
            return result
        except GitHubAPIError as error:
            last_error = str(error)
        except (ValueError, KeyError) as error:
            last_error = str(error)
    else:
        last_error = "No known template matched"

    llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    for attempt in range(1, SYNTHESIS_MAX_ATTEMPTS + 1):
        response = llm.invoke(
            [
                SystemMessage(content=SYNTHESIS_PROMPT),
                HumanMessage(
                    content=(
                        f"Operation needed: {operation_description}\n"
                        f"Repository: {client.owner}/{client.repo}\n"
                        f"Attempt: {attempt}\n"
                        f"Previous error: {last_error}"
                    )
                ),
            ]
        )
        spec = _normalize_spec(_extract_json(response.content))

        try:
            api_spec = {
                "method": spec["method"],
                "path": spec["path"],
                "query": spec.get("query"),
                "body": spec.get("body"),
            }
            client.execute_spec(api_spec, params=test_params or {})
            save_capability(
                name=spec["name"],
                description=spec["description"],
                api_spec=api_spec,
                synthesized=True,
            )
            record_capability_result(spec["name"], success=True)
            return {
                "name": spec["name"],
                "description": spec["description"],
                "api_spec": api_spec,
                "attempts": attempt,
                "source": "llm",
                "status": "registered",
            }
        except (GitHubAPIError, ValueError, KeyError) as error:
            last_error = str(error)
            record_capability_result(spec["name"], success=False, constraint=last_error)

    raise RuntimeError(
        f"Could not synthesize capability after {SYNTHESIS_MAX_ATTEMPTS} attempts: {last_error}"
    )
