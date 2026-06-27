import json
from typing import Any

import httpx

from app.config.settings import GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.owner = GITHUB_OWNER
        self.repo = GITHUB_REPO
        self._call_count = 0

    @property
    def api_call_count(self) -> int:
        return self._call_count

    def reset_call_count(self) -> None:
        self._call_count = 0

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _resolve_path(self, path: str, extra: dict | None = None) -> str:
        values = {"owner": self.owner, "repo": self.repo, **(extra or {})}
        return path.format(**values)

    def verify_repository(self) -> dict[str, Any]:
        """Validate token access and repo configuration."""
        if not self.owner or not self.repo:
            raise GitHubAPIError(
                400,
                "GITHUB_OWNER and GITHUB_REPO must be set (repo name only, not a full URL).",
            )
        if not GITHUB_TOKEN:
            raise GitHubAPIError(401, "GITHUB_TOKEN is not configured.")

        return self.request("GET", "/repos/{owner}/{repo}")

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        *,
        path_params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        resolved_path = self._resolve_path(path, path_params)
        url = f"{self.BASE_URL}{resolved_path}"
        self._call_count += 1

        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                params=params,
                json=json_body,
            )

        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("message", detail)
            except json.JSONDecodeError:
                pass
            raise GitHubAPIError(
                response.status_code,
                f"{detail} (url={url})",
            )

        if response.status_code == 204:
            return {"status": "ok"}

        return response.json()

    def list_issues(self, state: str = "open", labels: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = labels
        result = self.request("GET", "/repos/{owner}/{repo}/issues", params=params)
        return [issue for issue in result if "pull_request" not in issue]

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return self.request("POST", "/repos/{owner}/{repo}/issues", json_body=payload)

    def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        if assignees is not None:
            payload["assignees"] = assignees
        return self.request(
            "PATCH",
            f"/repos/{{owner}}/{{repo}}/issues/{issue_number}",
            json_body=payload,
        )

    def add_comment(self, issue_number: int, body: str) -> dict:
        return self.request(
            "POST",
            f"/repos/{{owner}}/{{repo}}/issues/{issue_number}/comments",
            json_body={"body": body},
        )

    def list_pull_requests(self, state: str = "open") -> list[dict]:
        result = self.request(
            "GET",
            "/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": 100},
        )
        return result

    def list_labels(self) -> list[dict]:
        return self.request("GET", "/repos/{owner}/{repo}/labels", params={"per_page": 100})

    def list_milestones(self, state: str = "open") -> list[dict]:
        return self.request(
            "GET",
            "/repos/{owner}/{repo}/milestones",
            params={"state": state, "per_page": 100},
        )

    def create_label(self, name: str, color: str = "ededed", description: str = "") -> dict:
        return self.request(
            "POST",
            "/repos/{owner}/{repo}/labels",
            json_body={"name": name, "color": color, "description": description},
        )

    def search_issues(self, query: str) -> list[dict]:
        scoped_query = f"{query} repo:{self.owner}/{self.repo}"
        result = self.request(
            "GET",
            "/search/issues",
            params={"q": scoped_query, "per_page": 100},
        )
        return result.get("items", [])

    def execute_spec(self, spec: dict[str, Any], params: dict[str, Any] | None = None) -> Any:
        """Run a synthesized API capability."""
        params = params or {}
        return self.request(
            spec["method"],
            spec["path"],
            params=spec.get("query"),
            json_body=spec.get("body"),
            path_params=params,
        )


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API {status_code}: {message}")
