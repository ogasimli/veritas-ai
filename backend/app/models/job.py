import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.finding import AgentResult


class Job(Base):
    """Job model representing a processing session."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, default="Audit", nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, processing, completed, failed
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="job", cascade="all, delete-orphan"
    )
    results: Mapped[list["AgentResult"]] = relationship(
        "AgentResult", back_populates="job", cascade="all, delete-orphan"
    )
