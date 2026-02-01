from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class ExternalSignalUnifiedFinding(BaseModel):
    """
    Unified finding that combines both external signal and claim verification types.

    This schema standardizes outputs from:
    - internet_to_report (external signals found via Deep Research)
    - report_to_internet (claim verifications from the report)
    """

    finding_type: Literal["external_signal", "claim_contradiction"] = Field(
        description="Type of finding: 'external_signal' from internet-to-report, 'claim_contradiction' from report-to-internet"
    )
    summary: str = Field(description="Concise summary of the finding (1-2 sentences)")
    severity: Literal["high", "medium", "low"] = Field(
        description="Severity level based on materiality and risk"
    )
    source_urls: list[str] = Field(
        description="List of source URLs supporting this finding"
    )
    category: str = Field(
        description="Category of the finding (e.g., 'litigation', 'news', 'claim_verification')"
    )
    details: str = Field(
        description="Detailed explanation including claim, evidence, dates, or contradiction details"
    )


class ExternalSignalFindingsAggregatorOutput(BaseAgentOutput):
    """Output schema for the external signal aggregator agent."""

    findings: list[ExternalSignalUnifiedFinding] = Field(
        default_factory=list,
        description="Unified and deduplicated findings from both verification directions",
    )
