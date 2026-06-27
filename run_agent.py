import json
import sys

from app.agent.agent import call_agent


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]).strip()
    if not prompt:
        print("Usage: python run_agent.py <instruction>")
        raise SystemExit(1)

    report = call_agent(prompt)
    print(json.dumps(report.model_dump(), indent=2))
