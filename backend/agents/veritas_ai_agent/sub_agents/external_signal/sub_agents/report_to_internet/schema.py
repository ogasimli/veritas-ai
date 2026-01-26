"""Schema for report-to-internet verification output."""
from typing import List, Literal
from pydantic import BaseModel, Field


class VerifiableClaim(BaseModel):
    """A publicly verifiable claim extracted from financial statement."""
    claim_text: str = Field(
        description="Exact quote from report"
    )
    claim_type: Literal[
        "date",
        "location",
        "partnership",
        "regulatory_filing",
        "award",
        "acquisition",
        "management"
    ] = Field(
        description="Category of claim"
    )
    verification_query: str = Field(
        description="Search query to validate this claim"
    )


class ClaimVerification(BaseModel):
    """Result of verifying a claim against internet sources."""
    claim: str = Field(
        description="The claim being verified"
    )
    status: Literal["VERIFIED", "CONTRADICTED", "CANNOT_VERIFY"] = Field(
        description="Verification result"
    )
    evidence_summary: str = Field(
        description="What was found online"
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="Supporting URLs"
    )
    discrepancy: str = Field(
        default="",
        description="Any discrepancies found (dates off, wording differences, etc.)"
    )


from veritas_ai_agent.schemas import BaseAgentOutput

class ReportToInternetOutput(BaseAgentOutput):
    """Output from report-to-internet agent - verification results for extracted claims."""
    verifications: List[ClaimVerification] = Field(
        default_factory=list,
        description="Verification results for publicly verifiable claims"
    )
