"""Schema for report-to-internet verification output."""

from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class ExternalSignalVerifiableClaim(BaseModel):
    """A publicly verifiable claim extracted from financial statement."""

    claim_text: str = Field(description="Exact quote from report")
    claim_category: str = Field(
        description="Classification of the information/statement/claim (e.g., Incorporation date, Acquisition, Macroeconomic indicator, etc.)"
    )
    verification_query: str = Field(description="Search query to validate this claim")
    entity_subject: str = Field(
        description="Entity subject (the company, country, regulator, party, etc.) to which the fact refers to."
    )


class ExternalSignalClaimVerification(BaseModel):
    """Result of verifying a claim against internet sources."""

    claim_text: str = Field(description="The claim being verified")
    claim_category: str = Field(
        description="Classification of the information/statement/claim (e.g., Incorporation date, Acquisition, Macroeconomic indicator, etc.)"
    )
    verification_status: Literal["VERIFIED", "CONTRADICTED", "CANNOT_VERIFY"] = Field(
        description="Verification result"
    )
    evidence_summary: str = Field(description="What was found online")
    source_urls: list[str] = Field(default_factory=list, description="Supporting URLs")
    discrepancy: str = Field(
        default="",
        description="Any discrepancies found (dates off, wording differences, etc.)",
    )


class ExternalSignalReportToInternetOutput(BaseAgentOutput):
    """Output from report-to-internet agent - verification results for extracted claims."""

    verifications: list[ExternalSignalClaimVerification] = Field(
        default_factory=list,
        description="Verification results for publicly verifiable claims",
    )
