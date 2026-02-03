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

    ``check_type`` differentiates the two pipelines.  Fields prefixed with
    *in-table* are populated only when check_type=="in_table"; the *cross-table*
    fields are populated only when check_type=="cross_table".
    """

    check_type: Literal["in_table", "cross_table"]
    inferred_formulas: Optional[list[InferredFormula]] = None
