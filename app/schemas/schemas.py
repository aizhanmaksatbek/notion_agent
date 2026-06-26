from pydantic import BaseModel, Field
from typing import Tuple, List


class InputPrompt(BaseModel):
    text: str = Field(..., max_length=50)


class PromptInstruction(BaseModel):
    instruction: str
    status: Tuple


class AgentOutput(BaseModel):
    result: List[PromptInstruction]
