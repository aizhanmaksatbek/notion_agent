from fastapi import FastAPI
from app.schemas.schemas import InputPrompt, AgentOutput
from app.agent.agent import call_agent
import uvicorn
from langchain_core.utils.uuid import uuid7

app = FastAPI()


@app.post("/", response_model=AgentOutput)
def home(prompt: InputPrompt):
    """
    Example prompt: Find articles related to personal expenses?
    """
    config = {"configurable": {"thread_id": str(uuid7())}}
    result = call_agent(prompt.text, config=config)
    return result


if __name__ == "__main__":
    uvicorn.run(app=app, host="localhost", port=8000)
