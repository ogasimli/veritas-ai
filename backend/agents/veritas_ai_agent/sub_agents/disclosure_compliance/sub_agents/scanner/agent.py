"""Scanner sub-agent definition."""
from google.adk.agents import LlmAgent
from .schema import ScannerAgentOutput
from . import prompt
from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config
from google.genai import types

scanner_agent = LlmAgent(
    name="ScannerAgent",
    model="gemini-3-flash-preview",
    instruction=prompt.INSTRUCTION,
    output_key="scanner_output",
    output_schema=ScannerAgentOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
