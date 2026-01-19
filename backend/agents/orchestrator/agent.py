"""Root orchestrator agent definition."""
from google.adk.agents import ParallelAgent
from .sub_agents import (
    numeric_validation_agent,
    logic_consistency_agent,
    disclosure_compliance_agent,
    external_signal_agent,
)

root_agent = ParallelAgent(
    name='audit_orchestrator',
    description='Coordinates parallel validation agents for financial statement audit',
    sub_agents=[
        numeric_validation_agent,       # Phase 3: Numeric validation pipeline
        logic_consistency_agent,        # Phase 4: Logic consistency detection
        disclosure_compliance_agent,    # Phase 5: Disclosure compliance checking
        external_signal_agent,          # Phase 6: External risk signal search
    ],
)
