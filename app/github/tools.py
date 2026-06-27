import json

from langchain.tools import tool
from langchain_core.tools import StructuredTool

from app.github.client import GitHubAPIError, GitHubClient
from app.memory.store import list_capabilities, record_capability_result
from app.synthesis.synthesizer import synthesize_capability


def build_github_tools(client: GitHubClient) -> list:
    """Create base GitHub tools plus any synthesized capabilities."""

    @tool
    def list_open_issues(labels: str = "") -> str:
        """List open issues in the configured repository. Optional labels filter."""
        try:
            issues = client.list_issues(state="open", labels=labels or None)
            summary = [
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "assignees": [user["login"] for user in issue.get("assignees", [])],
                    "labels": [label["name"] for label in issue.get("labels", [])],
                }
                for issue in issues
            ]
            return json.dumps(summary, indent=2)
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def create_issue(title: str, body: str = "", labels: str = "") -> str:
        """Create a new GitHub issue. Labels should be comma-separated."""
        try:
            label_list = [label.strip() for label in labels.split(",") if label.strip()]
            issue = client.create_issue(title=title, body=body, labels=label_list or None)
            return json.dumps(
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "url": issue["html_url"],
                },
                indent=2,
            )
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def update_issue(
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        labels: str = "",
        assignees: str = "",
    ) -> str:
        """Update an existing issue. Only pass fields that should change."""
        try:
            issue = client.update_issue(
                issue_number=issue_number,
                title=title or None,
                body=body or None,
                state=state or None,
                labels=[label.strip() for label in labels.split(",") if label.strip()] or None,
                assignees=[user.strip() for user in assignees.split(",") if user.strip()] or None,
            )
            return json.dumps(
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "url": issue["html_url"],
                },
                indent=2,
            )
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def comment_on_issue(issue_number: int, body: str) -> str:
        """Add a comment to an issue."""
        try:
            comment = client.add_comment(issue_number=issue_number, body=body)
            return json.dumps({"id": comment["id"], "url": comment["html_url"]}, indent=2)
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def list_open_pull_requests() -> str:
        """List open pull requests in the configured repository."""
        try:
            pulls = client.list_pull_requests(state="open")
            summary = [
                {
                    "number": pull["number"],
                    "title": pull["title"],
                    "author": pull["user"]["login"],
                    "url": pull["html_url"],
                }
                for pull in pulls
            ]
            return json.dumps(summary, indent=2)
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def search_repository_issues(query: str) -> str:
        """Search issues and pull requests in the configured repository."""
        try:
            items = client.search_issues(query=query)
            summary = [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "state": item["state"],
                    "url": item["html_url"],
                }
                for item in items
            ]
            return json.dumps(summary, indent=2)
        except GitHubAPIError as error:
            return f"ERROR: {error.message}"

    @tool
    def request_new_capability(operation_description: str) -> str:
        """Request synthesis of a missing GitHub capability at runtime."""
        try:
            result = synthesize_capability(client, operation_description)
            return json.dumps(result, indent=2)
        except RuntimeError as error:
            return f"ERROR: {error}"

    tools: list = [
        list_open_issues,
        create_issue,
        update_issue,
        comment_on_issue,
        list_open_pull_requests,
        search_repository_issues,
        request_new_capability,
    ]

    for capability in list_capabilities():
        tools.append(_build_synthesized_tool(client, capability.name, capability.description))

    return tools


def _build_synthesized_tool(client: GitHubClient, name: str, description: str) -> StructuredTool:
    def run(params_json: str = "{}") -> str:
        params = json.loads(params_json or "{}")
        capability = next(
            (item for item in list_capabilities() if item.name == name),
            None,
        )
        if not capability:
            return f"ERROR: capability {name} not found"

        api_spec = json.loads(capability.api_spec_json)
        try:
            result = client.execute_spec(api_spec, params=params)
            record_capability_result(name, success=True)
            return json.dumps(result, indent=2)
        except GitHubAPIError as error:
            record_capability_result(name, success=False, constraint=error.message)
            return f"ERROR: {error.message}"

    return StructuredTool.from_function(
        func=run,
        name=name,
        description=description,
    )
