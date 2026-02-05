"""Pydantic schema for in-table check agents."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class TargetCell(BaseModel):
    """Identifies a specific cell in a specific table."""

    table_index: int = Field(description="Index of the table containing the cell")
    row_index: int = Field(description="Row index of the cell")
    col_index: int = Field(description="Column index of the cell")


class InferredFormula(BaseModel):
    """Single inferred formula with target cell."""

    target_cell: TargetCell = Field(
        description="The cell that holds the calculated value"
    )
    formula: str = Field(description="Evaluable formula (e.g., sum_col(0, 1, 2, 4))")


class CheckAgentOutput(BaseAgentOutput):
    """Output for numeric check sub-agents."""

    formulas: list[InferredFormula] = Field(
        default_factory=list,
        description="List of detected formulas with their target cells",
    )
