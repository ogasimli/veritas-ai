"""In-Table Verification Pipeline (Sequential Agent)."""

from google.adk.agents import SequentialAgent

from .sub_agents.in_table_aggregator.agent import in_table_aggregator_agent
from .sub_agents.table_extractor.agent import table_extractor_agent

in_table_pipeline = SequentialAgent(
    name="InTableVerification",
    description="Pipeline to extract tables, verify calculations, and report issues.",
    sub_agents=[
        table_extractor_agent,
        in_table_aggregator_agent,
    ],
)
