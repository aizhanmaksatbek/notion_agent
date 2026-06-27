from fastapi import FastAPI

from app.agent.agent import call_agent
from app.memory.store import memory_snapshot
from app.schemas.schemas import AgentOutput, InputPrompt, MemorySnapshot

import uvicorn

app = FastAPI(title="GitHub Platform Agent")


@app.post("/", response_model=AgentOutput)
def execute_instruction(prompt: InputPrompt):
    """
    Example: Create a bug report for the login timeout issue.
    """
    report = call_agent(prompt.text)
    return AgentOutput(report=report)


@app.get("/memory", response_model=MemorySnapshot)
def get_memory():
    snapshot = memory_snapshot()
    return MemorySnapshot(**snapshot)


if __name__ == "__main__":
    uvicorn.run(app=app, host="localhost", port=8000)
