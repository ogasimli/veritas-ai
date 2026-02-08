"""Audit orchestrator — runs 4 validation agents in parallel."""

from google.adk.agents import ParallelAgent

from .callbacks import check_document_validity
from .sub_agents import (
    disclosure_compliance_agent,
    external_signal_agent,
    logic_consistency_agent,
    numeric_validation_agent,
)

audit_orchestrator = ParallelAgent(
    name="AuditOrchestrator",
    description="Coordinates parallel validation agents for financial statement audit",
    before_agent_callback=check_document_validity,
    sub_agents=[
        numeric_validation_agent,
        logic_consistency_agent,
        disclosure_compliance_agent,
        external_signal_agent,
    ],
)
