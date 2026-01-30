from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from .prompt import INSTRUCTION
from .schema import AggregatorAgentOutput

aggregator_agent = LlmAgent(
    name="external_signal_aggregator",
    model="gemini-3-flash-preview",
    instruction=INSTRUCTION,
    output_key="external_signal_findings",
    output_schema=AggregatorAgentOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
