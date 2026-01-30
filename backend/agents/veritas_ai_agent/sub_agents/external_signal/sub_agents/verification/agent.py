from google.adk.agents import ParallelAgent

from ..internet_to_report.agent import internet_to_report_agent
from ..report_to_internet.agent import report_to_internet_agent

verification_agent = ParallelAgent(
    name="external_signal_verification",
    description="Parallel bidirectional verification using Deep Research",
    sub_agents=[internet_to_report_agent, report_to_internet_agent],
)
