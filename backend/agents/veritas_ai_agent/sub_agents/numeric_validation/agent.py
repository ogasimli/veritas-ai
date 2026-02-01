import os

from google.adk.agents import ParallelAgent

from .sub_agents.in_table_verification.agent import in_table_pipeline
from .sub_agents.legacy_numeric_validation.agent import legacy_pipeline

# Configure enabled pipelines via environment variables
agent_mode = os.getenv("NUMERIC_VALIDATION_AGENT_MODE", "all")

sub_agents = []
if agent_mode == "legacy_pipeline":
    sub_agents = [legacy_pipeline]
elif agent_mode == "in_table_pipeline":
    sub_agents = [in_table_pipeline]
else:
    sub_agents = [legacy_pipeline, in_table_pipeline]

numeric_validation_agent = ParallelAgent(
    name="numeric_validation",
    description="Parallel pipeline for financial statement numeric validation (In-Table & Legacy Cross-Check)",
    sub_agents=sub_agents,
)
