import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class AgentResult(Base):
    """AgentResult model representing the outcome of an agent's execution."""

    __tablename__ = "agent_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String, nullable=False
    )  # numeric, logic, disclosure, external

    # Successful finding fields (nullable)
    severity: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # high, medium, low
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_refs: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error fields (nullable)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Common fields
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="results")
