from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FindingBase(BaseModel):
    category: str
    severity: str
    description: str
    source_refs: list[dict[str, Any]] = []
    reasoning: str | None = None
    agent_id: str


class FindingRead(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    created_at: datetime
