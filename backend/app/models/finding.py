import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class Finding(Base):
    """Finding model representing a detected issue."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String, nullable=False
    )  # numeric, logic, disclosure, external
    severity: Mapped[str] = mapped_column(String, nullable=False)  # high, medium, low
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="findings")
