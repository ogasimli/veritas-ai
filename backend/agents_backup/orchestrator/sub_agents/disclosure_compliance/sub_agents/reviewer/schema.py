from pydantic import BaseModel, Field
from typing import List, Literal


class ConfirmedFinding(BaseModel):
    """A confirmed missing disclosure (passed false-positive filter)."""
    standard: str = Field(description="Standard code (e.g., 'IAS 1', 'IFRS 15')")
    disclosure_id: str = Field(description="Disclosure ID from checklist (e.g., 'IAS1-D5')")
    requirement: str = Field(description="Short requirement title")
    severity: Literal["low", "medium", "high"] = Field(description="Severity level from verifier")
    description: str = Field(description="Full description of the missing disclosure requirement")


class ReviewerAgentOutput(BaseModel):
    """Output from disclosure Reviewer - findings that passed false-positive filter."""
    findings: List[ConfirmedFinding] = Field(
        default_factory=list,
        description="Confirmed missing disclosures (false positives removed)"
    )
