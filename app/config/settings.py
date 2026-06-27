import os
import re

from dotenv import load_dotenv

load_dotenv()


def _parse_github_target(owner: str, repo: str) -> tuple[str, str]:
    """Accept repo slug or full GitHub URL in GITHUB_REPO."""
    raw_repo = (repo or "").strip().rstrip("/")
    raw_owner = (owner or "").strip()

    if "github.com" in raw_repo:
        path = raw_repo.split("github.com/")[-1].strip("/")
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2:
            return parts[0], parts[1]
        if len(parts) == 1:
            return raw_owner or parts[0], parts[0]

    if "/" in raw_repo and "://" not in raw_repo:
        parsed_owner, parsed_repo = raw_repo.split("/", 1)
        return parsed_owner, parsed_repo

    return raw_owner, raw_repo


def _to_psycopg_url(url: str) -> str:
    """LangGraph/psycopg expect postgresql://, not SQLAlchemy driver suffixes."""
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url.strip())


def _to_sqlalchemy_url(url: str) -> str:
    """SQLModel/SQLAlchemy use the psycopg3 driver suffix."""
    base = _to_psycopg_url(url)
    if base.startswith("postgresql://"):
        return base.replace("postgresql://", "postgresql+psycopg://", 1)
    return base


_RAW_DB_URL = os.getenv(
    "DB_URL",
    "postgresql://githubuser:githubuser@localhost:5432/github_agent",
)

DB_URL = _to_psycopg_url(_RAW_DB_URL)
SQLALCHEMY_DB_URL = _to_sqlalchemy_url(_RAW_DB_URL)

GITHUB_OWNER, GITHUB_REPO = _parse_github_target(
    os.getenv("GITHUB_OWNER", ""),
    os.getenv("GITHUB_REPO", ""),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
SYNTHESIS_MAX_ATTEMPTS = int(os.getenv("SYNTHESIS_MAX_ATTEMPTS", "3"))
