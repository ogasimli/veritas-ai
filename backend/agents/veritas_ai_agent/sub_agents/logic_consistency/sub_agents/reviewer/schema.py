from typing import Literal

from pydantic import BaseModel, Field


class RefinedLogicConsistencyFinding(BaseModel):
    """A confirmed logic inconsistency that passed the false-positive filter."""

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
        description="Business-impact severity: 'high' (material/going concern impact), 'medium' (operational/compliance concern), 'low' (minor oddity)"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning chain showing how the contradiction was identified"
    )
    source_refs: list[str] = Field(
        description="References to locations in the document (e.g., 'Table 4', 'Note 12', 'MD&A Section 3')"
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class LogicConsistencyReviewerOutput(BaseAgentOutput):
    """Output from logic reviewer agent - confirmed findings that passed false-positive filter."""

    findings: list[RefinedLogicConsistencyFinding] = Field(
        default_factory=list,
        description="List of confirmed logic inconsistencies (false positives removed)",
    )
