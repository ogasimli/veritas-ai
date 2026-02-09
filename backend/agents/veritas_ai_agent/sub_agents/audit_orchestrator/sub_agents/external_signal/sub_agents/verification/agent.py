from google.adk.agents import ParallelAgent

from .sub_agents.internet_to_report.agent import internet_to_report_agent
from .sub_agents.report_to_internet.agent import report_to_internet_agent

# Both agents run in parallel; actual Deep Research API calls are serialized
# by the process-wide RateLimiter (≥65 s between calls, matching 1 RPM quota).
verification_agent = ParallelAgent(
    name="ExternalSignalVerification",
    description="Parallel bidirectional verification using Deep Research",
    sub_agents=[report_to_internet_agent, internet_to_report_agent],
)
