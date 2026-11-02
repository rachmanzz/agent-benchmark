"""Data schemas for agent benchmark executions and results."""

from datetime import datetime, timezone
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class BenchmarkStatus(str, Enum):
    """Execution status of a benchmark run."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"


class TokenUsage(BaseModel):
    """Token consumption metrics."""
    input_tokens: int = Field(default=0, ge=0, description="Count of input/prompt tokens")
    output_tokens: int = Field(default=0, ge=0, description="Count of completion/output tokens")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")

    def add(self, other: "TokenUsage") -> None:
        """Accumulate token counts in place."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens


class TrajectoryStep(BaseModel):
    """Single captured action or output step during agent execution."""
    step: int = Field(ge=1, description="Sequential step index")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of the step")
    action: str = Field(description="Action name or output stream identifier (e.g. stdout, stderr, tool_call)")
    content: str = Field(description="Captured content, arguments, or logs")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Step duration in seconds")


class BenchmarkRecord(BaseModel):
    """Complete record of a single benchmark run."""
    run_id: str = Field(description="Unique benchmark execution identifier")
    agent: str = Field(description="Identifier or name of the evaluated agent (e.g. codex, claude, opencode)")
    user_prompt: str = Field(description="The exact user prompt dispatched to the agent")
    start_time: str = Field(description="ISO 8601 UTC execution start timestamp")
    end_time: str = Field(description="ISO 8601 UTC execution end timestamp")
    duration_seconds: float = Field(ge=0.0, description="Total execution duration in seconds")
    token_usage: TokenUsage = Field(default_factory=TokenUsage, description="Aggregated token usage")
    trajectory: List[TrajectoryStep] = Field(default_factory=list, description="Ordered execution trajectory")
    exit_code: int = Field(default=0, description="Process exit code")
    status: BenchmarkStatus = Field(description="Outcome status of the run")
    final_output: str = Field(default="", description="Final text output or response produced by the agent")


def current_utc_iso() -> str:
    """Return the current UTC timestamp formatted in ISO 8601 with timezone marker."""
    return datetime.now(timezone.utc).isoformat()
