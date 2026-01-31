from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class CalculationIssue(BaseModel):
    issue_description: str = Field(
        description="Human readable short description of issue. Include details on where is the issue, what is the issue and what is the difference."
    )


class AggregatedResult(BaseAgentOutput):
    """Output schema for InTableAggregatorAgent."""

    issues: list[CalculationIssue] = Field(
        default_factory=list,
        description="List of genuine calculation issues, sorted by severity (abs(difference)) descending",
    )
