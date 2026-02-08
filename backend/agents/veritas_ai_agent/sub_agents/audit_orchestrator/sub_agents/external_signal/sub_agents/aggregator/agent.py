from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_FLASH

from . import prompt
from .callbacks import after_aggregator_callback
from .schema import ExternalSignalFindingsAggregatorOutput

aggregator_agent = LlmAgent(
    name="ExternalSignalFindingsAggregator",
    model=GEMINI_FLASH,
    instruction=prompt.INSTRUCTION,
    output_key="external_signal_findings_aggregator_output",
    output_schema=ExternalSignalFindingsAggregatorOutput,
    on_model_error_callback=default_model_error_handler,
    after_agent_callback=after_aggregator_callback,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
