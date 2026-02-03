"""Unit tests for DocumentMarkdownPlugin."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from veritas_ai_agent.app_utils.document_markdown_plugin import (
    DocumentMarkdownPlugin,
)


def _create_text_part(text: str):
    """Create a mock part with text content (not an artifact)."""
    part = SimpleNamespace()
    part.text = text
    # Explicitly no file_data attribute
    return part


def _create_artifact_part(
    mime_type: str, file_uri: str, text_content: str | None = None
):
    """Create a mock part representing an artifact with file_data."""
    part = SimpleNamespace()
    file_data = SimpleNamespace()
    file_data.mime_type = mime_type
    file_data.file_uri = file_uri
    if text_content:
        file_data.text = text_content
    part.file_data = file_data
    return part


@pytest.mark.asyncio
async def test_plugin_captures_text_message():
    """Test that plugin captures markdown from text message parts."""
    plugin = DocumentMarkdownPlugin(state_key="document_markdown")

    ctx = MagicMock()
    ctx.state = {}

    # Text part (not an artifact)
    text_part = _create_text_part("# Financial Statement\n\nRevenue: $1M")

    user_message = SimpleNamespace()
    user_message.parts = [text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert "document_markdown" in ctx.state
    assert ctx.state["document_markdown"] == "# Financial Statement\n\nRevenue: $1M"


@pytest.mark.asyncio
async def test_plugin_captures_multiple_text_parts():
    """Test that plugin combines multiple text parts into one."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    part1 = _create_text_part("# Header")
    part2 = _create_text_part("Content paragraph")

    user_message = SimpleNamespace()
    user_message.parts = [part1, part2]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert ctx.state["document_markdown"] == "# Header\nContent paragraph"


@pytest.mark.asyncio
async def test_plugin_only_runs_once():
    """Test that plugin doesn't overwrite existing document_markdown."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {"document_markdown": "Original content"}

    text_part = _create_text_part("New content")

    user_message = SimpleNamespace()
    user_message.parts = [text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert ctx.state["document_markdown"] == "Original content"


@pytest.mark.asyncio
async def test_plugin_prioritizes_markdown_artifact_over_text():
    """Test that plugin prefers .md artifact over text message."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    # Artifact with actual content
    artifact_part = _create_artifact_part(
        mime_type="text/markdown",
        file_uri="gs://bucket/document.md",
        text_content="# Artifact Content\n\nThis is from the artifact.",
    )

    # Text part (should be ignored)
    text_part = _create_text_part("Fallback text content")

    user_message = SimpleNamespace()
    user_message.parts = [artifact_part, text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert "document_markdown" in ctx.state
    # Should use artifact content, not text
    assert (
        ctx.state["document_markdown"]
        == "# Artifact Content\n\nThis is from the artifact."
    )


@pytest.mark.asyncio
async def test_plugin_accepts_txt_artifact():
    """Test that plugin accepts .txt files as well as .md."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    artifact_part = _create_artifact_part(
        mime_type="text/plain",
        file_uri="gs://bucket/document.txt",
        text_content="Plain text content",
    )

    user_message = SimpleNamespace()
    user_message.parts = [artifact_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert ctx.state["document_markdown"] == "Plain text content"


@pytest.mark.asyncio
async def test_plugin_ignores_non_text_artifacts():
    """Test that plugin ignores PDF or other non-text artifacts."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    # PDF artifact (should be ignored)
    pdf_part = _create_artifact_part(
        mime_type="application/pdf", file_uri="gs://bucket/document.pdf"
    )

    # Fallback text
    text_part = _create_text_part("Fallback markdown content")

    user_message = SimpleNamespace()
    user_message.parts = [pdf_part, text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    # Should fall back to text, NOT save PDF
    assert ctx.state["document_markdown"] == "Fallback markdown content"


@pytest.mark.asyncio
async def test_plugin_handles_artifact_without_content():
    """Test that plugin falls back to text if artifact has no content."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    # Artifact without text content
    artifact_part = _create_artifact_part(
        mime_type="text/markdown",
        file_uri="gs://bucket/document.md",
        # No text_content provided
    )

    # Fallback text
    text_part = _create_text_part("Fallback content from message")

    user_message = SimpleNamespace()
    user_message.parts = [artifact_part, text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    # Should fall back to text since artifact has no content
    assert ctx.state["document_markdown"] == "Fallback content from message"


@pytest.mark.asyncio
async def test_plugin_handles_no_user_message():
    """Test that plugin handles missing user message gracefully."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}
    ctx.llm_input = None

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert "document_markdown" not in ctx.state


@pytest.mark.asyncio
async def test_plugin_handles_empty_parts():
    """Test that plugin handles empty message parts."""
    plugin = DocumentMarkdownPlugin()

    ctx = MagicMock()
    ctx.state = {}

    user_message = SimpleNamespace()
    user_message.parts = []

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert "document_markdown" not in ctx.state


@pytest.mark.asyncio
async def test_plugin_uses_custom_state_key():
    """Test that plugin respects custom state key."""
    plugin = DocumentMarkdownPlugin(state_key="custom_md_key")

    ctx = MagicMock()
    ctx.state = {}

    text_part = _create_text_part("Content")

    user_message = SimpleNamespace()
    user_message.parts = [text_part]

    ctx.llm_input = SimpleNamespace()
    ctx.llm_input.user_message = user_message

    agent = MagicMock()

    result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)

    assert result is None
    assert "custom_md_key" in ctx.state
    assert ctx.state["custom_md_key"] == "Content"
    assert "document_markdown" not in ctx.state
