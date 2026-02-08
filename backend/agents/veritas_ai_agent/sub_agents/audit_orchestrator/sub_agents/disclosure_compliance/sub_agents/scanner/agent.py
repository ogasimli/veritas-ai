"""Scanner sub-agent definition."""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_FLASH

from . import prompt
from .schema import DisclosureScannerOutput

scanner_agent = LlmAgent(
    name="DisclosureScanner",
    model=GEMINI_FLASH,
    instruction=prompt.INSTRUCTION,
    output_key="disclosure_scanner_output",
    output_schema=DisclosureScannerOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
