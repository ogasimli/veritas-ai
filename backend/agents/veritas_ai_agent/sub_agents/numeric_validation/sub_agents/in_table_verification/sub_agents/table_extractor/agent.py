"""Table Extractor sub-agent definition."""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import callbacks, prompt
from .schema import TableExtractorOutput

table_extractor_agent = LlmAgent(
    name="TableExtractor",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="table_extractor_output",
    output_schema=TableExtractorOutput,
    after_agent_callback=callbacks.resolve_and_verify_formulas,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
