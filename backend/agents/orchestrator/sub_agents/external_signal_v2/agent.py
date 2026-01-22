"""External Signal V2 agent - bidirectional verification with Deep Research."""
from google.adk.agents import ParallelAgent
from .sub_agents.internet_to_report import internet_to_report_agent
from .sub_agents.report_to_internet import report_to_internet_agent

external_signal_v2_agent = ParallelAgent(
    name='external_signal_v2',
    description='Bidirectional verification using Deep Research for comprehensive external signal analysis',
    sub_agents=[
        internet_to_report_agent,    # Searches web for info contradicting report (Phase 6 enhanced)
        report_to_internet_agent,    # Verifies report claims against web (new bidirectional)
    ],
)
