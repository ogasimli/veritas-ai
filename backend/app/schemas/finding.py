from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
