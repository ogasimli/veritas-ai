from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from app.schemas.document import DocumentRead

class JobBase(BaseModel):
    status: str = "pending"

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    name: Optional[str] = None

class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentRead] = []
