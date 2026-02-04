"""Agent factory for vertical and horizontal check agents.

Factory pattern
---------------
Creates specialized LlmAgents with:
  * Specialized naming (VerticalCheckAgent, HorizontalCheckAgent)
  * Specialized prompts (VERTICAL_INSTRUCTION, HORIZONTAL_INSTRUCTION)
  * Shared configuration (model, output schema, error handling)
  * Unique output keys (vertical_check_output, horizontal_check_output)

Agent responsibilities
----------------------
VerticalCheckAgent:
  * Detects column-based formulas (sum_col, sum_cells with same column)
  * Outputs formulas for LEFT-MOST numeric column only (anchor cell strategy)
  * Ignores horizontal patterns

HorizontalCheckAgent:
  * Detects row-based formulas (sum_row, sum_cells with same row)
  * Outputs formulas for TOP-MOST numeric row only (anchor cell strategy)
  * Ignores vertical patterns

Design notes
------------
* Single factory function (_create_check_agent) reduces code duplication
* Prompts enforce "anchor only" rule to minimize LLM output tokens
* Python replication handles expansion (see formula_replicator.py)
"""

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from ...schema import CheckAgentOutput
from .prompt import HORIZONTAL_INSTRUCTION, VERTICAL_INSTRUCTION


def create_vertical_check_agent() -> LlmAgent:
    """Create the vertical check agent."""
    return _create_check_agent(
        name="VerticalCheckAgent",
        instruction=VERTICAL_INSTRUCTION,
        output_key="vertical_check_output",
    )


def create_horizontal_check_agent() -> LlmAgent:
    """Create the horizontal check agent."""
    return _create_check_agent(
        name="HorizontalCheckAgent",
        instruction=HORIZONTAL_INSTRUCTION,
        output_key="horizontal_check_output",
    )


def _create_check_agent(name: str, instruction: str, output_key: str) -> LlmAgent:
    """Shared factory for check agents."""
    return LlmAgent(
        name=name,
        model="gemini-3-pro-preview",
        instruction=instruction,
        output_schema=CheckAgentOutput,
        output_key=output_key,
        on_model_error_callback=default_model_error_handler,
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False, thinking_level="high"
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            http_options=types.HttpOptions(retry_options=get_default_retry_config())
        ),
    )
