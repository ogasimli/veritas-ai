import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.finding import AgentResult


class AgentId(StrEnum):
    NUMERIC_VALIDATION = "numeric_validation"
    LOGIC_CONSISTENCY = "logic_consistency"
    DISCLOSURE_COMPLIANCE = "disclosure_compliance"
    EXTERNAL_SIGNAL = "external_signal"

    @property
    def adk_name(self) -> str:
        """PascalCase name used by ADK agent definitions.

        Assumes each underscore-separated word is a full word (not an acronym).
        E.g. ``numeric_validation`` → ``NumericValidation``.
        """
        return "".join(word.capitalize() for word in self.value.split("_"))


ALL_AGENT_IDS = list(AgentId)


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
    enabled_agents: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        server_default="{numeric_validation,logic_consistency,disclosure_compliance,external_signal}",
        nullable=False,
    )

    def __init__(self, **kwargs):
        if "enabled_agents" not in kwargs:
            kwargs["enabled_agents"] = ALL_AGENT_IDS.copy()
        super().__init__(**kwargs)

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
