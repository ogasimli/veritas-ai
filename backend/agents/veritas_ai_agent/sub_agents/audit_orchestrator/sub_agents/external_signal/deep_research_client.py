"""Deep Research async client wrapper for Gemini Interactions API.

Rate-limit safety is enforced by a process-wide ``RateLimiter`` that
guarantees at least 65 s (configurable via ``DEEP_RESEARCH_MIN_INTERVAL``)
between consecutive ``interactions.create`` calls.  An ``asyncio.Lock``
serializes callers while the limiter sleeps, so parallel agents (e.g.
internet-to-report and report-to-internet running under a ParallelAgent)
naturally queue without exceeding the Deep Research RPM quota.

The Google ``genai`` SDK's built-in HTTP retries are disabled
(``HttpRetryOptions(attempts=1)``) so that *only* ``run_research``'s
own retry loop — which respects the rate-limiter — triggers new API calls.
"""

import asyncio
import logging
import os
import time
from typing import TypedDict

from google import genai
from google.genai import types

from veritas_ai_agent.shared.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Minimum seconds between consecutive interactions.create calls.
_MIN_INTERVAL = float(os.environ.get("DEEP_RESEARCH_MIN_INTERVAL", "65"))

_rate_limiter = RateLimiter(_MIN_INTERVAL, name="DeepResearchRateLimiter")


class DeepResearchResult(TypedDict):
    """Result from Deep Research execution."""

    result: str | None
    duration_seconds: float
    status: str  # "completed" | "timeout" | "failed"
    error: str | None


# SDK retry disabled — we handle retries in run_research.
_NO_RETRY = types.HttpRetryOptions(attempts=1)


class DeepResearchClient:
    """Client for Gemini Deep Research with robust error handling and async polling.

    All instances share a process-wide rate limiter so that concurrent callers
    are serialized *and* spaced at least ``DEEP_RESEARCH_MIN_INTERVAL`` seconds
    apart (default 60 s, matching the 1 RPM quota).
    """

    def __init__(self):
        """Initialize Deep Research client with SDK retries disabled."""
        api_key = os.getenv("GEMINI_API_KEY")
        http_options = types.HttpOptions(retry_options=_NO_RETRY)
        if api_key:
            self.client = genai.Client(api_key=api_key, http_options=http_options)
        else:
            self.client = genai.Client(http_options=http_options)

    async def _create_interaction(self, **kwargs):
        """Create a Deep Research interaction (no retry — handled by run_research)."""
        return await self.client.aio.interactions.create(**kwargs)

    async def _get_interaction(self, interaction_id):
        """Get interaction status (no retry — handled by run_research)."""
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
        enable_thinking_summaries: bool = True,
    ) -> DeepResearchResult:
        """
        Execute Deep Research with retry logic.

        On failure, retries up to *max_retries* times.  The process-wide rate
        limiter automatically enforces a 60 s gap between ``create`` calls,
        so callers never exceed the 1 RPM quota — even when two agents retry
        back-to-back through the shared limiter.

        Args:
            query: Research question
            timeout_minutes: Max time per attempt (default 10min, API max is 60min)
            max_retries: Total number of attempts (default 3)
            enable_thinking_summaries: Stream intermediate thoughts

        Returns:
            Dictionary with result, duration, status, and error
        """
        total_start = time.time()
        last_result = None

        for attempt in range(1, max_retries + 1):
            logger.info(
                "Deep Research attempt %d/%d (timeout: %d min, waiting for rate limiter...)",
                attempt,
                max_retries,
                timeout_minutes,
            )

            # Rate limiter ensures ≥60 s between create calls across all callers.
            async with _rate_limiter:
                logger.info(
                    "Deep Research rate limiter acquired for attempt %d/%d",
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

            # Don't wait after the last attempt
            if attempt < max_retries:
                logger.warning(
                    "Deep Research attempt %d/%d %s (%s). Retrying...",
                    attempt,
                    max_retries,
                    result["status"],
                    result["error"],
                )
                # No explicit sleep needed — the rate limiter will enforce
                # the 60 s gap when we re-enter ``async with _rate_limiter``
                # on the next iteration.
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
