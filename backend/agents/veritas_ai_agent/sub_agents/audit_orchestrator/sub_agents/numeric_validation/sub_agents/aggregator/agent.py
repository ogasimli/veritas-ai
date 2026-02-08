"""Aggregator LLM agent.

Pipeline position
-----------------
    before_agent_callback   ->   LlmAgent (aggregator)
           |                            |
    evaluates every formula     deduplicates findings,
    in reconstructed_formulas,  writes human-readable
    filters & sorts issues,     descriptions, writes
    writes formula_execution_   numeric_validation_output
    issues to state

The ``before_agent_callback`` (``callbacks.py``) does the heavy lifting:
it evaluates every formula in ``state["reconstructed_formulas"]`` using
``formula_engine``, filters to issues with |diff| >= 1.0, and writes
``state["formula_execution_issues"]``.  The LLM agent that follows only
needs to deduplicate and produce human-readable descriptions.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_PRO

from . import prompt
from .callbacks import before_agent_callback
from .schema import AggregatorOutput

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

aggregator_agent = LlmAgent(
    name="Aggregator",
    model=GEMINI_PRO,
    instruction=prompt.INSTRUCTION,
    output_key="numeric_validation_output",
    output_schema=AggregatorOutput,
    before_agent_callback=before_agent_callback,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
