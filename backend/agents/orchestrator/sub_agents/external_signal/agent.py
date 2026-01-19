"""External signal agent - searches news/litigation via google_search."""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai.types import GenerateContentConfig
from . import prompt
from .schema import ExternalSignalOutput

external_signal_agent = LlmAgent(
    name="external_signal",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    tools=[google_search],
    output_key="external_signal_output",
    output_schema=ExternalSignalOutput,
    generate_content_config=GenerateContentConfig(
        temperature=1.0,
    ),
)
