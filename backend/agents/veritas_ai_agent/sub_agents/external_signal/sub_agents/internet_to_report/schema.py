"""Schema for internet-to-report verification output."""

from typing import Literal

from pydantic import BaseModel, Field


class ExternalFinding(BaseModel):
    """A risk signal found through external search."""

    signal_type: Literal["news", "litigation", "financial_distress"] = Field(
        description="Type of signal detected"
    )
    summary: str = Field(description="Brief summary of the signal")
    source_url: str = Field(description="URL of the source article/filing")
    publication_date: str = Field(
        default="", description="Publication date if available (YYYY-MM-DD format)"
    )
    potential_contradiction: str = Field(
        default="",
        description="What financial statement claim this might contradict (empty if no contradiction)",
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class InternetToReportOutput(BaseAgentOutput):
    """Output from internet-to-report agent - external signals that may contradict report."""

    findings: list[ExternalFinding] = Field(
        default_factory=list,
        description="External risk signals discovered through Deep Research",
    )
