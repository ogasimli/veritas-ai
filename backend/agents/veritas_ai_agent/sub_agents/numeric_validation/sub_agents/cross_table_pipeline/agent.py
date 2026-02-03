"""Cross-Table Pipeline - SequentialAgent that runs FSLI extraction
followed by the cross-table formula fan-out.

Pipeline position
-----------------
    FsliExtractor   →   CrossTableFormulaFanOut
         |                       |
    writes                 reads FSLIs, writes
    fsli_extractor_output  cross-table formulas
                           to reconstructed_formulas
"""

from google.adk.agents import SequentialAgent

from .sub_agents.cross_table_fan_out.agent import cross_table_fan_out_agent
from .sub_agents.fsli_extractor.agent import fsli_extractor_agent

cross_table_pipeline_agent = SequentialAgent(
    name="CrossTablePipeline",
    description=(
        "Sequential pipeline: extract cross-table FSLIs, then fan out "
        "parallel agents to propose cross-table formulas."
    ),
    sub_agents=[fsli_extractor_agent, cross_table_fan_out_agent],
)
