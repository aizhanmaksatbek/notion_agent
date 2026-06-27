from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ExecutionMemory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    instruction: str
    instruction_key: str = Field(index=True)
    decomposition: str = Field(default="[]")
    steps_json: str = Field(default="[]")
    status: str
    duration_ms: float
    api_call_count: int
    failure_reason: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CapabilityMemory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str
    api_spec_json: str
    success_count: int = 0
    failure_count: int = 0
    constraints_json: str = Field(default="[]")
    synthesized: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
