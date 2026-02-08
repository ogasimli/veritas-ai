"""Schemas for Logic Reconciliation Check Fan-out Agent."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.schema import (
    TargetCell,
)


class LogicInferredFormula(BaseModel):
    """Single inferred formula with target cell and multiple formula candidates."""

    target_cell: TargetCell = Field(
        description="The cell that holds the calculated value"
    )
    formulas: list[str] = Field(
        default_factory=list,
        description="List of evaluable formula candidates (e.g., ['sum_col(...)', '...'])",
    )


class LogicCheckAgentOutput(BaseAgentOutput):
    """Output for logic reconciliation check sub-agents."""

    formulas: list[LogicInferredFormula] = Field(
        default_factory=list,
        description="List of detected formulas with their target cells",
    )
