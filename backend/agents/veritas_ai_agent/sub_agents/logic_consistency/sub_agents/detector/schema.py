from typing import Literal

from pydantic import BaseModel, Field


class LogicConsistencyFinding(BaseModel):
    """A logic consistency finding - a claim that is logically inconsistent or contradictory."""

    fsli_name: str = Field(
        description="Name of the Financial Statement Line Item involved in the contradiction"
    )
    claim: str = Field(
        description="The specific claim being made in the financial statement"
    )
    contradiction: str = Field(
        description="Explanation of why the claim is logically inconsistent or contradictory"
    )
    severity: Literal["high", "medium", "low"] = Field(
        description="Severity level: 'high' (core business contradiction), 'medium' (suspicious pattern), 'low' (minor inconsistency)"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning chain showing how the contradiction was identified"
    )
    source_refs: list[str] = Field(
        description="References to locations in the document (e.g., 'Table 4', 'Note 12', 'MD&A Section 3')"
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class LogicConsistencyDetectorOutput(BaseAgentOutput):
    """Output from logic detector agent - list of potential logic inconsistencies found."""

    findings: list[LogicConsistencyFinding] = Field(
        default_factory=list,
        description="List of logic consistency findings (claims that are logically contradictory)",
    )
