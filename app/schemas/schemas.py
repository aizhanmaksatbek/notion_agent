from pydantic import BaseModel, Field


class InputPrompt(BaseModel):
    text: str = Field(..., max_length=50)
