"""External Signal agent - bidirectional verification with Deep Research."""

from google.adk.agents import SequentialAgent

from .sub_agents.aggregator import aggregator_agent
from .sub_agents.verification import verification_agent

external_signal_agent = SequentialAgent(
    name="external_signal",
    description="Bidirectional ifnormation verification with unified output",
    sub_agents=[
        verification_agent,  # Step 1: Parallel verification
        aggregator_agent,  # Step 2: Aggregate & deduplicate
    ],
)
