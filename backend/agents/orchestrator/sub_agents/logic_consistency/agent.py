"""Logic Consistency Agent - detects and refines semantic contradictions in financial statements."""
from google.adk.agents import SequentialAgent

from .sub_agents import detector_agent, reviewer_agent
from .schema import LogicConsistencyOutput

logic_consistency_agent = SequentialAgent(
    name="logic_consistency",
    sub_agents=[detector_agent, reviewer_agent],
    output_key="logic_consistency_output",
    output_schema=LogicConsistencyOutput,
)
