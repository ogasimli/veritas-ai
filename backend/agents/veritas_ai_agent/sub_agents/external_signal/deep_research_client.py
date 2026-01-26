"""Deep Research async client wrapper for Gemini Interactions API."""

import asyncio
import time
from typing import TypedDict

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential


class DeepResearchResult(TypedDict):
    """Result from Deep Research execution."""

    result: str | None
    duration_seconds: float
    status: str  # "completed" | "timeout" | "failed"
    error: str | None


class DeepResearchClient:
    """Client for Gemini Deep Research with robust error handling and async polling."""

    def __init__(self):
        """Initialize Deep Research client."""
        self.client = genai.Client()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def run_research(
        self,
        query: str,
        timeout_minutes: int = 20,
        enable_thinking_summaries: bool = True,
    ) -> DeepResearchResult:
        """
        Execute Deep Research with polling and timeout protection.

        Args:
            query: Research question
            timeout_minutes: Max time to wait (default 20 min, API max is 60 min)
            enable_thinking_summaries: Stream intermediate thoughts

        Returns:
            Dictionary with result, duration, status, and error
        """
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        try:
            # Create Deep Research interaction via Interactions API (Async)
            interaction = await self.client.aio.interactions.create(
                input=query,
                agent="deep-research-pro-preview-12-2025",
                background=True,
                agent_config={
                    "type": "deep-research",
                    "thinking_summaries": "auto"
                    if enable_thinking_summaries
                    else "none",
                },
            )

            # Poll every 10 seconds for completion
            poll_interval = 10

            while True:
                elapsed = time.time() - start_time

                # Check application timeout (20 min default, not API's 60 min max)
                if elapsed > timeout_seconds:
                    return DeepResearchResult(
                        result=None,
                        duration_seconds=elapsed,
                        status="timeout",
                        error=f"Research exceeded {timeout_minutes} minute timeout",
                    )

                # Get current status (Async)
                interaction = await self.client.aio.interactions.get(interaction.id)

                if interaction.status == "completed":
                    outputs = getattr(interaction, "outputs", [])
                    result_text = (
                        outputs[-1].text if outputs and len(outputs) > 0 else None
                    )
                    return DeepResearchResult(
                        result=result_text,
                        duration_seconds=elapsed,
                        status="completed",
                        error=None,
                    )

                elif interaction.status == "failed":
                    interaction_error = getattr(interaction, "error", None)
                    error_msg = (
                        str(interaction_error)
                        if interaction_error is not None
                        else "Unknown error"
                    )
                    return DeepResearchResult(
                        result=None,
                        duration_seconds=elapsed,
                        status="failed",
                        error=error_msg,
                    )

                # Still in progress, yield to event loop
                await asyncio.sleep(poll_interval)

        except Exception as e:
            return DeepResearchResult(
                result=None,
                duration_seconds=time.time() - start_time,
                status="failed",
                error=str(e),
            )
