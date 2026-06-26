from fastapi import FastAPI
from app.schemas.schemas import InputPrompt, AgentOutput
from app.agent.agent import call_agent
import uvicorn

app = FastAPI()


@app.post("/", response_model=AgentOutput)
def home(prompt: InputPrompt):
    """
    Example prompt: Find articles related to personal expenses?
    """
    result = call_agent(prompt.text)
    return result


if __name__ == "__main__":
    uvicorn.run(app=app, host="localhost", port=8000)
