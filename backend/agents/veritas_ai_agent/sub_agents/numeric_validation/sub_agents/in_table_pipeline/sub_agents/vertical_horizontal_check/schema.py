"""Pydantic schema for vertical and horizontal check agents."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput

from ...schema import TargetCell


class HorizontalVerticalCheckInferredFormula(BaseModel):
    """Single inferred formula with target cell."""

    target_cell: TargetCell = Field(
        description="The cell that holds the calculated value"
    )
    formula: str = Field(description="Evaluable formula (e.g., sum_col(0, 1, 2, 4))")


class HorizontalVerticalCheckAgentOutput(BaseAgentOutput):
    """Output for numeric check sub-agents."""

    formulas: list[HorizontalVerticalCheckInferredFormula] = Field(
        default_factory=list,
        description="List of detected formulas with their target cells",
    )
