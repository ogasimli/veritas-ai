"""Pydantic schema for in-table check agents."""

from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class InferredFormula(BaseModel):
    """Single inferred formula with target cell and check type."""

    target_cell: tuple[int, int, int] = Field(
        description="(table_index, row_index, col_index) - the cell that holds the calculated value"
    )
    formula: str = Field(description="Formula expression, e.g. sum_col(0, 1, 2, 4)")
    check_type: Literal["vertical", "horizontal", "logical"] = Field(
        description="Type of check: vertical (column-based), horizontal (row-based), or logical"
    )


class CheckAgentOutput(BaseAgentOutput):
    """Output schema for vertical/horizontal check agents."""

    formulas: list[InferredFormula] = Field(
        default_factory=list,
        description="List of detected formulas with their target cells",
    )
