"""Pydantic schema for in-table check agents."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class InferredFormula(BaseModel):
    """Single inferred formula with target cell."""

    target_cell: list[int] = Field(
        description="3-element list: [table_index, row_index, col_index] - the cell that holds the calculated value",
        min_length=3,
        max_length=3,
    )
    formula: str = Field(description="Formula expression, e.g. sum_col(0, 1, 2, 4)")


class CheckAgentOutput(BaseAgentOutput):
    """Output schema for vertical/horizontal check agents."""

    formulas: list[InferredFormula] = Field(
        default_factory=list,
        description="List of detected formulas with their target cells",
    )
