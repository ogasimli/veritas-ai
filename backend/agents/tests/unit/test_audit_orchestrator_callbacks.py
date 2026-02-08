"""Unit tests for audit orchestrator callbacks."""

import pytest

from veritas_ai_agent.sub_agents.audit_orchestrator.callbacks import (
    check_document_validity,
)


@pytest.fixture
def mock_callback_context():
    """Create a mock callback context with state."""

    class MockCallbackContext:
        def __init__(self):
            self.state = {}

    return MockCallbackContext()


@pytest.mark.asyncio
async def test_valid_financial_document_passes(mock_callback_context):
    """When validator says document is valid, callback returns None (proceed)."""
    mock_callback_context.state = {
        "document_validator_output": {"is_valid_financial_document": True}
    }

    result = await check_document_validity(mock_callback_context)

    assert result is None
    assert "validation_rejected" not in mock_callback_context.state


@pytest.mark.asyncio
async def test_invalid_document_short_circuits(mock_callback_context):
    """When validator says document is not financial, callback returns Content."""
    mock_callback_context.state = {
        "document_validator_output": {"is_valid_financial_document": False}
    }

    result = await check_document_validity(mock_callback_context)

    assert result is not None
    assert result.role == "model"
    assert result.parts is not None and len(result.parts) > 0
    first_part_text = result.parts[0].text
    assert first_part_text is not None
    assert "not a financial statement" in first_part_text
    assert mock_callback_context.state["validation_rejected"] is True


@pytest.mark.asyncio
async def test_missing_validator_output_passes(mock_callback_context):
    """When no validator output exists in state, callback returns None (proceed)."""
    mock_callback_context.state = {}

    result = await check_document_validity(mock_callback_context)

    assert result is None


@pytest.mark.asyncio
async def test_none_validator_output_passes(mock_callback_context):
    """When validator output is None, callback returns None (proceed)."""
    mock_callback_context.state = {"document_validator_output": None}

    result = await check_document_validity(mock_callback_context)

    assert result is None


@pytest.mark.asyncio
async def test_missing_is_valid_field_defaults_to_pass(mock_callback_context):
    """When is_valid_financial_document key is missing, defaults to True (proceed)."""
    mock_callback_context.state = {
        "document_validator_output": {"some_other_field": "value"}
    }

    result = await check_document_validity(mock_callback_context)

    assert result is None
