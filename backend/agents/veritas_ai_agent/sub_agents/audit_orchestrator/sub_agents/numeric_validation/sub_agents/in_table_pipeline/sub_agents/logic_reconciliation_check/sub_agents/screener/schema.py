"""Pydantic schema for the logic-reconciliation-check screener output."""

from pydantic import Field

from veritas_ai_agent.schemas import BaseAgentOutput


class LogicReconciliationCheckScreenerOutput(BaseAgentOutput):
    """Screener output: subset of tables worth investigating for reconciliation formulas."""

    candidate_table_indexes: list[int] = Field(
        default_factory=list,
        description=(
            "0-based indexes of tables that likely contain logical (roll-forward / movement) formulas"
        ),
    )
