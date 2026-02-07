"""Logic Consistency Agent - detects and refines semantic contradictions in financial statements.

Pipeline:
1. Detector (MultiPassRefinementAgent): N chains x M passes to find all contradictions
2. Reviewer (FanOutAgent): Parallel batches to filter false positives and assign severity
"""

from google.adk.agents import SequentialAgent

from .sub_agents import detector_agent, reviewer_agent

logic_consistency_agent = SequentialAgent(
    name="LogicConsistency",
    description="Detects and refines semantic contradictions in financial statements",
    sub_agents=[detector_agent, reviewer_agent],
)
