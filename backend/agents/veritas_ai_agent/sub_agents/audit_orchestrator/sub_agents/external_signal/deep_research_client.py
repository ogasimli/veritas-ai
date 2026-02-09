"""Deep Research async client wrapper for Gemini Interactions API.

Concurrency is controlled by a process-wide ``asyncio.Semaphore`` whose limit
is set via the ``DEEP_RESEARCH_MAX_CONCURRENCY`` environment variable
(default: 1, matching Deep Research's 1 RPM limit). This allows callers to
run in parallel while the semaphore serializes actual Deep Research operations.
"""

import asyncio
import logging
import os
import time
from typing import TypedDict

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_MAX_CONCURRENCY = int(os.environ.get("DEEP_RESEARCH_MAX_CONCURRENCY", "1"))
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazily create the semaphore on first use (must happen inside an event loop)."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
        logger.info(
            "Deep Research concurrency semaphore initialized (max_concurrency=%d)",
            _MAX_CONCURRENCY,
        )
    return _semaphore


class DeepResearchResult(TypedDict):
    """Result from Deep Research execution."""

    result: str | None
    duration_seconds: float
    status: str  # "completed" | "timeout" | "failed"
    error: str | None


class DeepResearchClient:
    """Client for Gemini Deep Research with robust error handling and async polling.

    All instances share a process-wide semaphore (configured via
    ``DEEP_RESEARCH_MAX_CONCURRENCY``, default 1) so that concurrent callers
    are serialized at the Deep Research level while remaining parallel elsewhere.
    """

    def __init__(self):
        """Initialize Deep Research client."""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            # Use AI Studio (Google Generative AI)
            self.client = genai.Client(api_key=api_key)
        else:
            # Fallback to Vertex AI (Default)
            self.client = genai.Client()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _create_interaction(self, **kwargs):
        """Create interaction with retry logic."""
        return await self.client.aio.interactions.create(**kwargs)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _get_interaction(self, interaction_id):
        """Get interaction status with retry logic."""
        return await self.client.aio.interactions.get(interaction_id)

    async def _run_single_attempt(
        self,
        query: str,
        timeout_minutes: int = 10,
        enable_thinking_summaries: bool = True,
    ) -> DeepResearchResult:
        """Execute a single Deep Research attempt with polling and timeout."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        try:
            # Create Deep Research interaction via Interactions API (Async)
            interaction = await self._create_interaction(
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

            logger.info("Deep Research interaction created: %s", interaction.id)

            # Poll every 10 seconds for completion
            poll_interval = 10
            poll_count = 0

            while True:
                elapsed = time.time() - start_time
                poll_count += 1

                # Check application timeout (10 min default, not API's 60 min max)
                if elapsed > timeout_seconds:
                    logger.warning(
                        "Deep Research timed out after %.1fs (%d polls), interaction: %s",
                        elapsed,
                        poll_count,
                        interaction.id,
                    )
                    return DeepResearchResult(
                        result=None,
                        duration_seconds=elapsed,
                        status="timeout",
                        error=f"Research exceeded {timeout_minutes} minute timeout",
                    )

                # Get current status (Async)
                interaction = await self._get_interaction(interaction.id)

                logger.info(
                    "Deep Research poll [%d] - status: %s, elapsed: %.1fs, interaction: %s",
                    poll_count,
                    interaction.status,
                    elapsed,
                    interaction.id,
                )

                if interaction.status == "completed":
                    outputs = getattr(interaction, "outputs", [])
                    result_text = (
                        outputs[-1].text if outputs and len(outputs) > 0 else None
                    )
                    logger.info(
                        "Deep Research completed in %.1fs (%d polls)",
                        elapsed,
                        poll_count,
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
                    logger.error(
                        "Deep Research failed after %.1fs: %s",
                        elapsed,
                        error_msg,
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
            elapsed = time.time() - start_time
            logger.error("Deep Research exception after %.1fs: %s", elapsed, str(e))
            return DeepResearchResult(
                result=None,
                duration_seconds=elapsed,
                status="failed",
                error=str(e),
            )

    async def run_research(
        self,
        query: str,
        timeout_minutes: int = 10,
        max_retries: int = 3,
        initial_backoff_seconds: float = 15,
        backoff_multiplier: float = 2,
        enable_thinking_summaries: bool = True,
    ) -> DeepResearchResult:
        """
        Execute Deep Research with retry and exponential backoff.

        On timeout or failure, retries with exponentially increasing wait times
        between attempts (15s, 30s, 60s by default).

        Args:
            query: Research question
            timeout_minutes: Max time per attempt (default 10min, API max is 60min)
            max_retries: Total number of attempts (default 3)
            initial_backoff_seconds: Wait before first retry (default 15s)
            backoff_multiplier: Multiplier applied each retry (default 2x)
            enable_thinking_summaries: Stream intermediate thoughts

        Returns:
            Dictionary with result, duration, status, and error
        """
        total_start = time.time()
        last_result = None
        semaphore = _get_semaphore()

        for attempt in range(1, max_retries + 1):
            logger.info(
                "Deep Research attempt %d/%d (timeout: %d min, waiting for semaphore...)",
                attempt,
                max_retries,
                timeout_minutes,
            )

            # Acquire semaphore to respect RPM limits; released after each
            # attempt so backoff sleep doesn't block other callers.
            async with semaphore:
                logger.info(
                    "Deep Research semaphore acquired for attempt %d/%d",
                    attempt,
                    max_retries,
                )
                result = await self._run_single_attempt(
                    query=query,
                    timeout_minutes=timeout_minutes,
                    enable_thinking_summaries=enable_thinking_summaries,
                )
            last_result = result

            if result["status"] == "completed":
                if attempt > 1:
                    logger.info(
                        "Deep Research succeeded on attempt %d/%d, total time: %.1fs",
                        attempt,
                        max_retries,
                        time.time() - total_start,
                    )
                return result

            # Don't backoff after the last attempt
            if attempt < max_retries:
                backoff = initial_backoff_seconds * (
                    backoff_multiplier ** (attempt - 1)
                )
                logger.warning(
                    "Deep Research attempt %d/%d %s (%s). Retrying in %.0fs...",
                    attempt,
                    max_retries,
                    result["status"],
                    result["error"],
                    backoff,
                )
                await asyncio.sleep(backoff)
            else:
                logger.error(
                    "Deep Research exhausted all %d attempts. Last status: %s, total time: %.1fs",
                    max_retries,
                    result["status"],
                    time.time() - total_start,
                )

        # Update duration to reflect total time across all attempts
        last_result["duration_seconds"] = time.time() - total_start
        return last_result
