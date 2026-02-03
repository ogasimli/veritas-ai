"""Shared Pydantic schemas for the numeric validation pipeline.

Every agent that writes to the shared ``reconstructed_formulas`` state key
should serialise its output using these types so that the formula-execution
callback and the aggregator can consume it uniformly.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class TargetCell(BaseModel):
    """Pointer to a single cell inside a table grid."""

    table_index: int
    row: int
    col: int


class InferredFormula(BaseModel):
    """One candidate formula for a calculable cell."""

    formula: str = Field(
        description="Evaluable formula string (e.g. sum_col(0, 1, 2, 4))"
    )


# ---------------------------------------------------------------------------
# Unified formula entry written to ``reconstructed_formulas``
# ---------------------------------------------------------------------------


class ReconstructedFormula(BaseModel):
    """
    Unified schema stored in state["reconstructed_formulas"].

    ``check_type`` differentiates the two pipelines.  Both pipelines use the
    same set of fields; ``target_cells`` holds one entry for in-table checks
    and multiple entries for cross-table relationship checks.
    """

    check_type: Literal["in_table", "cross_table"]
    target_cells: list[TargetCell] = Field(default_factory=list)
    actual_value: Optional[float] = None
    inferred_formulas: list[InferredFormula] = Field(default_factory=list)
