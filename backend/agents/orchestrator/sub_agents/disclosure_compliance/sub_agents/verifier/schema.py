from pydantic import BaseModel, Field
from typing import List, Literal


class DisclosureFinding(BaseModel):
    """Single disclosure finding (missing requirement)."""
    standard: str = Field(description="Standard code (e.g., 'IAS 1', 'IFRS 15')")
    disclosure_id: str = Field(description="Disclosure ID from checklist (e.g., 'IAS1-D5')")
    requirement: str = Field(description="Short requirement title")
    severity: Literal["low", "medium", "high"] = Field(description="Severity level based on importance")
    description: str = Field(description="Full description of the missing disclosure requirement")


class VerifierAgentOutput(BaseModel):
    """Output schema for disclosure VerifierAgent."""
    findings: List[DisclosureFinding] = Field(
        default_factory=list,
        description="List of missing disclosure findings for this standard"
    )
