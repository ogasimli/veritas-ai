"""Root agent definition for numeric validation."""
from google.adk.agents import SequentialAgent
from .sub_agents.planner import planner_agent

# Note: validator and manager agents will be added in subsequent plans
root_agent = SequentialAgent(
    name='numeric_validation',
    description='Pipeline for financial statement numeric validation',
    sub_agents=[planner_agent],
)
