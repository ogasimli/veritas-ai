from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NormalizedFinding(BaseModel):
    """Canonical finding shape — shared contract between adapters and DB layer."""

    description: str
    severity: str  # "high" | "medium" | "low"
    reasoning: str
    source_refs: list[str] = []


class AgentResultEnvelope(BaseModel):
    """Uniform wrapper for any agent's output."""

    agent_id: str
    category: str
    status: Literal["success", "error"] = "success"
    findings: list[NormalizedFinding] = []
    error_message: str | None = None
    error_type: str | None = None


class AgentResultBase(BaseModel):
    category: str
    agent_id: str

    # Success fields (optional)
    severity: str | None = None
    description: str | None = None
    source_refs: list[str] | None = None
    reasoning: str | None = None

    # Error fields (optional)
    error: str | None = None

    # Common fields
    raw_data: dict[str, Any]


class AgentResultRead(AgentResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    created_at: datetime
