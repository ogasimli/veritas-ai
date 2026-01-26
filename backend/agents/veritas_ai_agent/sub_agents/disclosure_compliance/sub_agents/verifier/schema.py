from typing import Literal

from pydantic import BaseModel, Field


class DisclosureFinding(BaseModel):
    """Single disclosure finding (missing requirement)."""

    standard: str = Field(description="Standard code (e.g., 'IAS 1', 'IFRS 15')")
    disclosure_id: str = Field(
        description="Disclosure ID from checklist (e.g., 'IAS1-D5')"
    )
    requirement: str = Field(description="Short requirement title")
    severity: Literal["low", "medium", "high"] = Field(
        description="Severity level based on importance"
    )
    description: str = Field(
        description="Full description of the missing disclosure requirement"
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class VerifierAgentOutput(BaseAgentOutput):
    """Output schema for disclosure VerifierAgent."""

    findings: list[DisclosureFinding] = Field(
        default_factory=list,
        description="List of missing disclosure findings for this standard",
    )
