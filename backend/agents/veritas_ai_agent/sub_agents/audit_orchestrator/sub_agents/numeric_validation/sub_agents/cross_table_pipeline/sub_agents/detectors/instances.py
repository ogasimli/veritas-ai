"""Cross-table detector instances — one per financial statement type."""

from .agent import create_cross_table_detector
from .prompt import (
    BS_FIRST_PASS_INSTRUCTION,
    BS_REFINEMENT_INSTRUCTION,
    CF_FIRST_PASS_INSTRUCTION,
    CF_REFINEMENT_INSTRUCTION,
    IS_FIRST_PASS_INSTRUCTION,
    IS_REFINEMENT_INSTRUCTION,
)

# Balance Sheet Detector (1 chain x 3 passes)
balance_sheet_detector_agent = create_cross_table_detector(
    agent_name="BalanceSheetCrossTableInconsistencyDetector",
    output_key="balance_sheet_cross_table_inconsistency_detector_output",
    first_pass_instruction=BS_FIRST_PASS_INSTRUCTION,
    refinement_instruction=BS_REFINEMENT_INSTRUCTION,
    n_parallel_chains=1,
    m_sequential_passes=3,
)

# Income Statement Detector (1 chain x 3 passes)
income_statement_detector_agent = create_cross_table_detector(
    agent_name="IncomeStatementCrossTableInconsistencyDetector",
    output_key="income_statement_cross_table_inconsistency_detector_output",
    first_pass_instruction=IS_FIRST_PASS_INSTRUCTION,
    refinement_instruction=IS_REFINEMENT_INSTRUCTION,
    n_parallel_chains=1,
    m_sequential_passes=3,
)

# Cash Flow Detector (2 chains x 3 passes)
cash_flow_detector_agent = create_cross_table_detector(
    agent_name="CashFlowCrossTableInconsistencyDetector",
    output_key="cash_flow_cross_table_inconsistency_detector_output",
    first_pass_instruction=CF_FIRST_PASS_INSTRUCTION,
    refinement_instruction=CF_REFINEMENT_INSTRUCTION,
    n_parallel_chains=2,
    m_sequential_passes=3,
)
