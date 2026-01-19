from typing import List, Literal
from pydantic import BaseModel, Field

class ExternalFinding(BaseModel):
    """A risk signal found through external search."""
    signal_type: Literal["news", "litigation", "financial_distress"] = Field(
        description="Type of signal detected"
    )
    summary: str = Field(
        description="Brief summary of the signal"
    )
    source_url: str = Field(
        description="URL of the source article/filing"
    )
    publication_date: str = Field(
        default="",
        description="Publication date if available (YYYY-MM-DD format)"
    )
    potential_contradiction: str = Field(
        default="",
        description="What financial statement claim this might contradict (empty if no contradiction)"
    )

class ExternalSignalOutput(BaseModel):
    """Output from external signal agent - risk signals from news/litigation search."""
    findings: List[ExternalFinding] = Field(
        default_factory=list,
        description="External risk signals discovered through search"
    )
