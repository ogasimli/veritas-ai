"""Cross-Table Pipeline — detects cross-table discrepancies and reviews them.

Architecture
------------
    CrossTablePipeline (SequentialAgent)
      ├─ CrossTableDetectors (ParallelAgent)
      │   ├─ BalanceSheetCrossTableInconsistencyDetector     (1x3 MultiPassRefinementAgent)
      │   ├─ IncomeStatementCrossTableInconsistencyDetector  (1x3 MultiPassRefinementAgent)
      │   └─ CashFlowCrossTableInconsistencyDetector         (2x3 MultiPassRefinementAgent)
      └─ CrossTableReviewer           (FanOutAgent, max 5 findings/batch)
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from .sub_agents.detectors import (
    balance_sheet_detector_agent,
    cash_flow_detector_agent,
    income_statement_detector_agent,
)
from .sub_agents.reviewer import reviewer_agent

cross_table_pipeline_agent = SequentialAgent(
    name="CrossTablePipeline",
    sub_agents=[
        ParallelAgent(
            name="CrossTableDetectors",
            sub_agents=[
                balance_sheet_detector_agent,
                income_statement_detector_agent,
                cash_flow_detector_agent,
            ],
        ),
        reviewer_agent,
    ],
)
