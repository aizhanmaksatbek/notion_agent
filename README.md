# GitHub Platform Agent

Autonomous Platform Intelligence Agent for GitHub — a take-home assignment implementation.

The agent accepts natural language instructions, executes them against a real GitHub repository via the REST API, persists structured memory across sessions, synthesizes missing capabilities at runtime, and improves on repeated runs.

## Setup

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Create a PostgreSQL database and update `DB_URL`.

3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
python main.py
```

Or run a single instruction from the CLI:

```bash
python run_agent.py "Create a bug report for the login timeout issue"
```

## Usage

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Create a bug report for the login timeout issue"}'
```

Inspect memory:

```bash
curl http://localhost:8000/memory
```

## Demo

See `DEMO.md` for the three live walkthrough instructions and `ARCHITECTURE.md` for design decisions.

## Requirements

- Python 3.11+
- PostgreSQL
- GitHub personal access token with `repo` scope
- OpenAI API key
