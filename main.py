from fastapi import FastAPI
from app.schemas.schemas import InputPrompt
from app.agent.agent import call_agent


app = FastAPI()


@app.post("/")
def home(prompt: InputPrompt):
    """
    Example prompt: Find articles related to personal expenses?
    """
    result = call_agent(prompt.text)
    return {"message": result}
