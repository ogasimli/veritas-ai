from typing import Literal

from pydantic import BaseModel, Field


class DisclosureFinding(BaseModel):
    """Single disclosure finding (missing requirement)."""

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


class DisclosureVerifierOutput(BaseAgentOutput):
    """Output schema for disclosure VerifierAgent."""

    findings: list[DisclosureFinding] = Field(
        default_factory=list,
        description="List of missing disclosure findings for this standard",
    )
