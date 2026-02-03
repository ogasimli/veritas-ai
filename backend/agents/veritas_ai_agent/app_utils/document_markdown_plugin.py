"""Plugin to capture initial user message (markdown) and store in state.

This plugin ensures that document_markdown is available to all sub-agents
by extracting it from the user's initial message and storing it in state.

Handles both:
- Text passed directly in message parts
- Text passed as artifacts (files)
"""

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types


class DocumentMarkdownPlugin(BasePlugin):
    """
    Plugin to capture the initial user message as document_markdown.

    On the first agent invocation, extracts the user's message text
    (from either text parts or artifacts) and stores it in
    state["document_markdown"] for all downstream agents.
    """

    def __init__(self, state_key: str = "document_markdown"):
        """
        Initialize the plugin.

        Args:
            state_key: State key to store the document markdown under.
        """
        super().__init__(name="document_markdown_capture")
        self.state_key = state_key

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        """Capture user message text and store in state before first agent runs."""
        # Only capture if not already present (run once per session)
        if self.state_key in callback_context.state:
            return None

        # Extract text from the user's message in the current turn
        if callback_context.llm_input and callback_context.llm_input.user_message:
            user_message = callback_context.llm_input.user_message

            # Priority 1: Check for markdown/text artifacts first
            for part in user_message.parts:
                if hasattr(part, "file_data") and part.file_data:
                    file_data = part.file_data

                    # Check if it's a .md or .txt file
                    mime_type = getattr(file_data, "mime_type", "")
                    file_uri = getattr(file_data, "file_uri", "")

                    # Accept markdown or plain text files
                    is_markdown = mime_type in [
                        "text/markdown",
                        "text/plain",
                    ] or file_uri.endswith((".md", ".txt"))

                    if is_markdown:
                        # Extract the actual text content from the artifact
                        # ADK may expose this as file_data.text or we may need to fetch it
                        content = None

                        # Try to get text content directly from file_data
                        if hasattr(file_data, "text") and file_data.text:
                            content = file_data.text
                        # Some artifacts might have the content in a different attribute
                        elif hasattr(part, "text") and part.text:
                            content = part.text

                        if content:
                            callback_context.state[self.state_key] = content
                            return None

                        # If we can't get content, log a warning and fall through to text parts
                        # In production, we might want to fetch from file_uri here
                        import logging

                        logging.warning(
                            f"Found markdown artifact at {file_uri} but couldn't "
                            f"extract text content. Falling back to message text."
                        )

            # Priority 2: Fall back to text message parts if no suitable artifact found
            text_parts = []
            for part in user_message.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            # Save combined text parts if any exist
            if text_parts:
                markdown = "\n".join(text_parts)
                callback_context.state[self.state_key] = markdown

        return None  # Don't short-circuit execution


def create_document_markdown_plugin() -> DocumentMarkdownPlugin:
    """Factory function to create the document markdown plugin."""
    return DocumentMarkdownPlugin()
