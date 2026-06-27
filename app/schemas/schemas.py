from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class InputPrompt(BaseModel):
    text: str = Field(..., max_length=2000)


class StepResult(BaseModel):
    instruction: str
    status: Literal["success", "error"]
    detail: str = ""


class MemoryDelta(BaseModel):
    execution_saved: bool
    capabilities_updated: List[str] = Field(default_factory=list)


class ExecutionReport(BaseModel):
    instruction: str
    status: Literal["success", "partial", "failed"]
    decomposition: List[str] = Field(default_factory=list)
    steps: List[StepResult] = Field(default_factory=list)
    duration_ms: float
    api_calls: int
    failure_reason: str = ""
    learning_notes: List[str] = Field(default_factory=list)
    memory_before: dict[str, Any] = Field(default_factory=dict)
    memory_after: dict[str, Any] = Field(default_factory=dict)
    memory_delta: MemoryDelta = Field(default_factory=MemoryDelta)


class MemorySnapshot(BaseModel):
    executions: List[dict[str, Any]]
    capabilities: List[dict[str, Any]]


class AgentOutput(BaseModel):
    report: ExecutionReport


class PromptInstruction(BaseModel):
    instruction: str
    status: str


class LegacyAgentOutput(BaseModel):
    prompt: str
    instructions: List[PromptInstruction]
