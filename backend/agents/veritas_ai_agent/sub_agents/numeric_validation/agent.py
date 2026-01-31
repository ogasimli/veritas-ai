"""Root agent definition."""

from google.adk.agents import ParallelAgent

from .sub_agents.in_table_verification.agent import in_table_pipeline
from .sub_agents.legacy_numeric_validation.agent import legacy_pipeline

numeric_validation_agent = ParallelAgent(
    name="numeric_validation",
    description="Parallel pipeline for financial statement numeric validation (In-Table & Legacy Cross-Check)",
    sub_agents=[
        legacy_pipeline,
        in_table_pipeline,
    ],
)
