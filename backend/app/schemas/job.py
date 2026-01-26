from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentRead] = []
