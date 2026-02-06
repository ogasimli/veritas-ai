"""Logic Reconciliation Check Screener Agent."""

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .prompt import INSTRUCTION
from .schema import LogicReconciliationCheckScreenerOutput

logic_reconciliation_check_screener_agent = LlmAgent(
    name="LogicReconciliationCheckScreener",
    model="gemini-3-pro-preview",
    instruction=INSTRUCTION,
    output_schema=LogicReconciliationCheckScreenerOutput,
    output_key="logic_reconciliation_check_screener_output",
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
