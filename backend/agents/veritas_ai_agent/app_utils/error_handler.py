"""
Centralized error handling utilities for all Veritas AI agents.
Provides callbacks for graceful degradation on API errors.
"""

import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
import json
from veritas_ai_agent.schemas import AgentError

# Configure logger
logger = logging.getLogger("veritas_ai_agent.error_handler")


async def default_model_error_handler(
    callback_context: CallbackContext, llm_request: LlmRequest, error: Exception
) -> LlmResponse | None:
    """
    Universal error handler for LlmAgents.

    1. Logs the full error with agent context.
    2. Checks for rate limits or other survivable errors.
    3. Returns an empty/safe response matching the agent's schema if possible.
    4. Re-raises only if we absolutely cannot recover.
    """
    agent_name = callback_context.agent_name
    error_str = str(error)

    logger.error(f"Agent '{agent_name}' encountered error: {error_str}", exc_info=True)

    # 1. Check for formal status codes (more reliable)
    # google-genai and api_core errors usually have a .code attribute (int)
    status_code = getattr(error, "code", None)

    # 2. Define survivable numeric codes
    # 429: Rate Limit/Resource Exhausted
    # 500, 503, 504: Transient Server Errors
    survivable_codes = {429, 500, 503, 504}

    is_survivable = status_code in survivable_codes

    if is_survivable:
        logger.warning(
            f"Suppressing error for agent '{agent_name}'. Returning structured error response."
        )
        # Attempt to synthesize an empty JSON response based on what we know
        # about common schemas in our system.
        # We return an empty JSON object. Most Pydantic models with default factories
        # (like List fields) will handle "{}" gracefully.
        
        error_type = "rate_limit" if status_code == 429 else "server_error"
        error_msg = f"Agent '{agent_name}' encountered a temporary error ({error_type}). Please retry."
        
        agent_error = AgentError(
            is_error=True,
            agent_name=agent_name,
            error_type=error_type,
            error_message=error_msg
        )
        
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=agent_error.model_dump_json())])
        )

    # If it's a logic error or something we don't know, let it crash or
    # handle it differently.
    return None


def attach_error_handler(agent: LlmAgent) -> None:
    """
    Helper to attach the default error handler to an agent
    if it doesn't already have one.
    """
    if not agent.on_model_error_callback:
        agent.on_model_error_callback = default_model_error_handler
