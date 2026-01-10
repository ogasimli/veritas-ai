from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class DocumentBase(BaseModel):
    filename: str
    content_type: str

class DocumentCreate(DocumentBase):
    job_id: UUID
    gcs_path: str

class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    gcs_path: str
    extracted_text: str | None = None
    created_at: datetime
