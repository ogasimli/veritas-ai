from google.adk.agents import SequentialAgent

from .sub_agents.internet_to_report.agent import internet_to_report_agent
from .sub_agents.report_to_internet.agent import report_to_internet_agent

# TODO: Change to parallel agent once we have higher RPMs
verification_agent = SequentialAgent(
    name="ExternalSignalVerification",
    description="Sequential bidirectional verification using Deep Research (sequential to avoid RPM limits)",
    sub_agents=[internet_to_report_agent, report_to_internet_agent],
)
