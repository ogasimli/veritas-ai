"""Shared callbacks for agent pipelines."""

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest


def strip_injected_context(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """Remove ADK-injected 'For context:' contents from the LLM request.

    ADK propagates prior agent outputs as conversation history even with
    include_contents='none'. This callback strips those injected messages
    so each reviewer batch agent only sees its instruction (which already
    contains the specific findings assigned to it).
    """
    llm_request.contents = [
        c
        for c in llm_request.contents
        if not (
            c.role == "user"
            and c.parts
            and any(p.text == "For context:" for p in c.parts if p.text)
        )
    ]
