"""In-Table Pipeline - ParallelAgent that runs specialized check agents
in parallel, then replicates detected formulas across rows/columns.

Pipeline architecture
---------------------
    VerticalCheckAgent     (detects column-based formulas for anchor column)
          ↓
    HorizontalCheckAgent   (detects row-based formulas for anchor row)
          ↓
    after_agent_callback   (replicates formulas, populates actual_value)
          ↓
    reconstructed_formulas (written to state with check_type="in_table")

Design notes
------------
* Agents output "anchor" formulas for the first numeric column/row only.
* Python replication expands these to all applicable columns/rows.
* Target cells are identified to enable actual_value lookup from table grids.
* Sub-check types (vertical/horizontal/logical) are preserved in state.
"""

from google.adk.agents import ParallelAgent

from .callbacks import after_in_table_parallel_callback
from .sub_agents.vertical_horizontal_check.agent import (
    create_horizontal_check_agent,
    create_vertical_check_agent,
)

# Create sub-agents
_vertical_agent = create_vertical_check_agent()
_horizontal_agent = create_horizontal_check_agent()
# TODO: _logical_agent = create_logical_check_agent()

# Module-level singleton
in_table_pipeline_agent = ParallelAgent(
    name="InTablePipeline",
    sub_agents=[_vertical_agent, _horizontal_agent],
    # TODO: Add _logical_agent when implemented
    after_agent_callback=after_in_table_parallel_callback,
)
