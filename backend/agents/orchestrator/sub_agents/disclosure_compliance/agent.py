"""Disclosure compliance validation agent."""
from google.adk.agents import SequentialAgent
from .sub_agents import scanner_agent, disclosure_verifier_agent

disclosure_compliance_agent = SequentialAgent(
    name='disclosure_compliance',
    description='Validates IFRS disclosure compliance by scanning for applicable standards and verifying required disclosures',
    sub_agents=[
        scanner_agent,              # Step 1: Identify applicable standards
        disclosure_verifier_agent,  # Step 2: Verify disclosures per standard in parallel
    ],
)
