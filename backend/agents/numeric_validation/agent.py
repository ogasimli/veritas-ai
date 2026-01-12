"""Root agent definition."""
from google.adk.agents import SequentialAgent
from .sub_agents import extractor_agent, fan_out_verifier_agent

root_agent = SequentialAgent(
    name='numeric_validation',
    description='Pipeline for financial statement numeric validation',
    sub_agents=[
        extractor_agent,        # Extract FSLI names
        fan_out_verifier_agent, # Parallel verification per FSLI
        # reviewer_agent,       # To be added in 03-03
    ],
)
