"""Table Namer LLM agent.

Pipeline position
-----------------
    before_agent_callback   ->   LlmAgent (names tables)   ->   after_agent_callback
           |                                                            |
    runs programmatic                                         parses LLM JSON,
    extraction, stores                                        merges names into
    raw tables in state                                       raw tables, writes
                                                              state["extracted_tables"]

The agent itself is very lightweight: it reads raw table data and
returns a JSON list of ``{table_index, name}`` pairs.  All heavy lifting
(extraction before, merging after) happens in the two callbacks.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_PRO

from . import prompt
from .callbacks import after_agent_callback, before_agent_callback
from .schema import TableNamerOutput

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

table_namer_agent = LlmAgent(
    name="TableNamer",
    model=GEMINI_PRO,
    instruction=prompt.INSTRUCTION,
    output_key="table_namer_output",
    output_schema=TableNamerOutput,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
