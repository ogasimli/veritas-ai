from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.job import ALL_AGENT_IDS
from app.schemas.document import DocumentRead


class JobBase(BaseModel):
    status: str = "pending"


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    name: str | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    error_message: str | None = None
    enabled_agents: list[str] = list(ALL_AGENT_IDS)
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentRead] = []


class UploadParams(BaseModel):
    """Query/body params for the upload endpoint."""

    enabled_agents: list[str] = list(ALL_AGENT_IDS)

    @field_validator("enabled_agents")
    @classmethod
    def validate_agents(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))  # deduplicate, preserving order
        if not v:
            raise ValueError("At least one agent must be enabled")
        invalid = set(v) - set(ALL_AGENT_IDS)
        if invalid:
            raise ValueError(f"Invalid agent IDs: {invalid}")
        return v
