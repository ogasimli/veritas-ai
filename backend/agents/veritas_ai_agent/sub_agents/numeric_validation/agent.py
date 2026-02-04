from google.adk.agents import ParallelAgent, SequentialAgent

from .sub_agents.aggregator.agent import aggregator_agent
from .sub_agents.cross_table_pipeline.agent import cross_table_pipeline_agent
from .sub_agents.in_table_pipeline.agent import in_table_pipeline_agent
from .sub_agents.table_namer.agent import table_namer_agent

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
            sub_agents=[in_table_pipeline_agent, cross_table_pipeline_agent],
        ),
        aggregator_agent,
    ],
)
