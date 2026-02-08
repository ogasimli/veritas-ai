"""Callbacks for the audit orchestrator."""

from google.adk.agents.callback_context import CallbackContext
from google.genai import types


async def check_document_validity(
    callback_context: CallbackContext,
) -> types.Content | None:
    """Skip audit if document validator determined this isn't a financial document."""
    validator_output = callback_context.state.get("document_validator_output")
    if validator_output and not validator_output.get(
        "is_valid_financial_document", True
    ):
        callback_context.state["validation_rejected"] = True
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    text="Document validation failed: not a financial statement."
                )
            ],
        )
    return None
