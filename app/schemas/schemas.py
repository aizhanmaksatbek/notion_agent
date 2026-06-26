from pydantic import BaseModel, Field
from typing import List


class InputPrompt(BaseModel):
    text: str = Field(..., max_length=50)


class PromptInstruction(BaseModel):
    instruction: str
    status: str


class AgentOutput(BaseModel):
    prompt: str
    instructions: List[PromptInstruction]
