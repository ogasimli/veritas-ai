from typing import Optional

from pydantic import BaseModel, Field


class AgentError(BaseModel):
    """Encapsulates error details for any agent failure."""

    is_error: bool = Field(
        default=True, description="Flag indicating an error occurred"
    )
    agent_name: str = Field(..., description="Name of the agent that failed")
    error_type: str = Field(
        ..., description="Category of error (e.g. rate_limit, server_error)"
    )
    error_message: str = Field(..., description="Human-readable error description")


class BaseAgentOutput(BaseModel):
    """Base schema for agent outputs that might include errors."""

    error: Optional[AgentError] = None
