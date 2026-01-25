from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional


class FindingBase(BaseModel):
    category: str
    severity: str
    description: str
    source_refs: List[Dict[str, Any]] = []
    reasoning: Optional[str] = None
    agent_id: str


class FindingRead(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    created_at: datetime
