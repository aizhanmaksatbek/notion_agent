import os

from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv(
    "DB_URL",
    "postgresql://githubuser:githubuser@localhost:5432/github_agent",
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
SYNTHESIS_MAX_ATTEMPTS = int(os.getenv("SYNTHESIS_MAX_ATTEMPTS", "3"))
