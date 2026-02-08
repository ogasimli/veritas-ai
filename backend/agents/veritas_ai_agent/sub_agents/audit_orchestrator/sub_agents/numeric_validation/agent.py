import os

from google.adk.agents import ParallelAgent, SequentialAgent

from .sub_agents.aggregator.agent import aggregator_agent
from .sub_agents.cross_table_pipeline.agent import cross_table_pipeline_agent
from .sub_agents.in_table_pipeline.agent import in_table_pipeline_agent
from .sub_agents.table_namer.agent import table_namer_agent

# Configure enabled pipelines via environment variables
agent_mode = os.getenv("NUMERIC_VALIDATION_AGENT_MODE", "all")

parallel_sub_agents = []
if agent_mode == "legacy_pipeline":
    parallel_sub_agents = [cross_table_pipeline_agent]
elif agent_mode == "in_table_pipeline":
    parallel_sub_agents = [in_table_pipeline_agent]
else:
    parallel_sub_agents = [in_table_pipeline_agent, cross_table_pipeline_agent]

numeric_validation_agent = SequentialAgent(
    name="NumericValidation",
    description=(
        "End-to-end numeric validation pipeline: name tables, then run "
        "in-table and cross-table checks in parallel, then aggregate findings."
    ),
    sub_agents=[
        table_namer_agent,
        ParallelAgent(
            name="NumericValidationParallel",
            description="In-table and cross-table checks run concurrently.",
            sub_agents=parallel_sub_agents,
        ),
        aggregator_agent,
    ],
)
