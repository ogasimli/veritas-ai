"""Root orchestrator agent definition."""

from google.adk.agents import ParallelAgent

from .app_utils.state_wrapper import StateAwareWrapperAgent
from .sub_agents import (
    disclosure_compliance_agent,
    external_signal_agent,
    logic_consistency_agent,
    numeric_validation_agent,
)

root_agent = ParallelAgent(
    name="audit_orchestrator",
    description="Coordinates parallel validation agents for financial statement audit",
    sub_agents=[
        numeric_validation_agent,  # Numeric validation pipeline (adaptive batching)
        StateAwareWrapperAgent(logic_consistency_agent),  # Logic consistency detection
        StateAwareWrapperAgent(
            disclosure_compliance_agent
        ),  # Disclosure compliance checking
        StateAwareWrapperAgent(
            external_signal_agent
        ),  # Bidirectional external verification with Deep Research
    ],
)
