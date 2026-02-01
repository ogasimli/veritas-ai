from typing import Literal

from pydantic import BaseModel, Field


class ConfirmedDisclosureFinding(BaseModel):
    """A confirmed missing disclosure (passed false-positive filter)."""

    standard: str = Field(description="Standard code (e.g., 'IAS 1', 'IFRS 15')")
    disclosure_id: str = Field(
        description="Disclosure ID from checklist (e.g., 'G.6.18')"
    )
    reference: str = Field(
        description="Disclosure reference from checklist (e.g., 'IFRS15p118(c)')"
    )
    requirement: str = Field(description="Full disclosure requirement from checklist")
    severity: Literal["low", "medium", "high"] = Field(
        description="Severity level based on importance"
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class DisclosureReviewerOutput(BaseAgentOutput):
    """Output from disclosure Reviewer - findings that passed false-positive filter."""

    findings: list[ConfirmedDisclosureFinding] = Field(
        default_factory=list,
        description="Confirmed missing disclosures (false positives removed)",
    )
