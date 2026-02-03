"""FSLI Extractor - lightweight LlmAgent that identifies cross-table FSLIs.

Pipeline position
-----------------
    LlmAgent (extracts FSLIs)   →   state["fsli_extractor_output"]

The agent reads ``{document_markdown}`` and ``{extracted_tables}`` via
ADK's automatic state-key substitution and returns a categorised list of
FSLIs that appear in more than one table.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import prompt
from .schema import FsliExtractorOutput

fsli_extractor_agent = LlmAgent(
    name="FsliExtractor",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="fsli_extractor_output",
    output_schema=FsliExtractorOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
