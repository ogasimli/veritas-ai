"""Root agent definition."""

from google.adk.agents import SequentialAgent

from .sub_agents import extractor_agent, reviewer_agent, verifier_agent

numeric_validation_agent = SequentialAgent(
    name="numeric_validation",
    description="Pipeline for financial statement numeric validation",
    sub_agents=[
        extractor_agent,  # Extract FSLI names
        verifier_agent,  # Parallel verification per FSLI
        reviewer_agent,  # Filter, re-verify, output findings
    ],
)
