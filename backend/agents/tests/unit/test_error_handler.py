import json
from unittest.mock import MagicMock

import pytest
from google.adk.models.llm_response import LlmResponse

from veritas_ai_agent.schemas import AgentError
from veritas_ai_agent.shared.error_handler import default_model_error_handler


@pytest.mark.asyncio
async def test_error_handler_returns_structured_error():
    """Test that the error handler returns a structured AgentError for 429/500."""
    ctx = MagicMock()
    ctx.agent_name = "TestAgent"

    req = MagicMock()

    # Simulate a 429 Rate Limit error
    error = MagicMock()
    error.code = 429
    error.message = "Resource exhausted"

    response = await default_model_error_handler(ctx, req, error)

    assert isinstance(response, LlmResponse)
    assert response.content is not None
    assert response.content.parts is not None
    assert len(response.content.parts) > 0

    error_json = json.loads(response.content.parts[0].text)

    # Validate against AgentError schema
    agent_error = AgentError(**error_json)
    assert agent_error.is_error is True
    assert agent_error.agent_name == "TestAgent"
    assert agent_error.error_type == "rate_limit"
    assert "TestAgent" in agent_error.error_message


@pytest.mark.asyncio
async def test_error_handler_returns_none_for_fatal_error():
    """Test that the error handler returns None (crashes) for fatal errors (e.g. 400)."""
    ctx = MagicMock()
    ctx.agent_name = "TestAgent"

    req = MagicMock()

    # Simulate a 400 Bad Request (not in retryable list)
    error = MagicMock()
    error.code = 400
    error.message = "Bad Request"

    response = await default_model_error_handler(ctx, req, error)

    assert response is None
