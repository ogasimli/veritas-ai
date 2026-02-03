"""Pydantic schemas for the Aggregator agent output."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class NumericIssue(BaseModel):
    """A single validated numeric discrepancy surfaced by formula execution."""

    issue_description: str = Field(
        description="Human-readable description of the numeric discrepancy"
    )
    check_type: str = Field(
        description="Pipeline that surfaced the issue: 'in_table' or 'cross_table'"
    )
    formula: str = Field(description="The formula that was evaluated")
    difference: float = Field(
        description=(
            "Signed difference: calculated - actual for in_table; "
            "raw formula result for cross_table (expected 0)"
        )
    )


class AggregatorOutput(BaseAgentOutput):
    """Final output of the numeric validation pipeline.

    Written to ``state["numeric_validation_output"]`` by the Aggregator
    LlmAgent.  ``issues`` is already deduplicated and ordered by absolute
    difference (largest first) by the time the LLM sees it; the agent only
    needs to generate descriptions and drop true duplicates.
    """

    issues: list[NumericIssue] = Field(
        default_factory=list,
        description=(
            "Validated and deduplicated numeric discrepancies, "
            "ranked by absolute difference (largest first)"
        ),
    )
