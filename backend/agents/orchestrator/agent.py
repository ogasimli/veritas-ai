"""Root orchestrator agent definition."""
from google.adk.agents import ParallelAgent
from .sub_agents import numeric_validation_agent

orchestrator_agent = ParallelAgent(
    name='audit_orchestrator',
    description='Coordinates parallel validation agents for financial statement audit',
    sub_agents=[
        numeric_validation_agent,    # Phase 3: Numeric validation pipeline
        # Future agents: logic_consistency (Phase 4), disclosure_compliance (Phase 5), external_signal (Phase 6)
    ],
)
