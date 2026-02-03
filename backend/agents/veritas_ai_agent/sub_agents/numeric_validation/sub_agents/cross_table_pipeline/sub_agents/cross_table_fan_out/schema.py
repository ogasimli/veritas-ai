"""Pydantic schema for a single cross-table batch agent output."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class CrossTableFormula(BaseModel):
    """One cross-table relationship proposal.

    ``target_cells`` contains all cells involved in the relationship
    (typically one per table).  ``actual_value`` is ``None`` for
    cross-table checks because the "expected" value is encoded in the
    formula itself (e.g. difference == 0).
    """

    target_cells: list[dict] = Field(
        default_factory=list,
        description="TargetCell-shaped dicts for every cell involved",
    )
    actual_value: float | None = None
    inferred_formulas: list[dict] = Field(
        default_factory=list,
        description="List of {formula: str} dicts proposed by the LLM",
    )


class CrossTableBatchOutput(BaseAgentOutput):
    """Envelope written to state by each cross-table batch sub-agent.

    ``formulas`` mirrors the ``ReconstructedFormula`` shape but omits
    ``check_type`` — the fan-out aggregator adds ``"cross_table"`` before
    appending to the shared ``reconstructed_formulas`` list.
    """

    formulas: list[CrossTableFormula] = Field(default_factory=list)
