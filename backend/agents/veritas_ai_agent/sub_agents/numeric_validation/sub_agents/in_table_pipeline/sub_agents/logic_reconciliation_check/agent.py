"""Logic Reconciliation Check Pipeline.

Screens tables for rollforward/movement candidates, then fans out per-table checks.
"""

from google.adk.agents import SequentialAgent

from .sub_agents.fan_out.agent import LogicReconciliationFormulaInferer
from .sub_agents.screener.agent import logic_reconciliation_check_screener_agent

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_logic_reconciliation_check_pipeline = SequentialAgent(
    name="LogicReconciliationCheckPipeline",
    description="Screens tables for rollforward/movement candidates and detects logical reconciliation formulas.",
    sub_agents=[
        logic_reconciliation_check_screener_agent,
        LogicReconciliationFormulaInferer(),
    ],
)
