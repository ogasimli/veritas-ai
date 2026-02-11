"""FileLoggingPlugin — extends ADK LoggingPlugin to write per-job log files.

Uses ``contextvars`` so that ``_log()`` (which receives no context argument)
can look up the correct file handle for the current async task.  This makes
concurrent jobs safe — each writes to its own ``agent_trace_{user_id}.log``.
"""

from __future__ import annotations

import contextvars
import os
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING

from google.adk.plugins import LoggingPlugin
from google.genai import types

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext


def _writable_dir() -> Path:
    """Return cwd if writable, otherwise /tmp (Cloud Run has read-only /app)."""
    cwd = Path.cwd()
    if os.access(cwd, os.W_OK):
        return cwd
    return Path("/tmp")


# Async-safe: each coroutine chain gets its own value.
_current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_user_id", default=None
)


class FileLoggingPlugin(LoggingPlugin):
    """Extends LoggingPlugin to also persist log lines to a per-job file.

    File lifecycle is fully self-managed via ADK callbacks — no external
    setup or teardown is needed.  The processor only needs to include this
    plugin in the ``App.plugins`` list.

    Output files:  ``{cwd}/agent_trace_{user_id}.log``
    """

    def __init__(self, name: str = "logging_plugin"):
        super().__init__(name)
        # user_id (== job_id) → open file handle
        self._files: dict[str, TextIOWrapper] = {}

    # ------------------------------------------------------------------
    # ADK callback overrides (lifecycle)
    # ------------------------------------------------------------------

    async def before_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> types.Content | None:
        """Open the per-job log file and stash user_id in the contextvar."""
        user_id = invocation_context.user_id
        _current_user_id.set(user_id)

        if user_id and user_id not in self._files:
            path = _writable_dir() / f"agent_trace_{user_id}.log"
            self._files[user_id] = open(path, "w", encoding="utf-8")

        return await super().before_run_callback(invocation_context=invocation_context)

    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """Flush and close the log file for this job."""
        result = await super().after_run_callback(invocation_context=invocation_context)

        user_id = invocation_context.user_id
        f = self._files.pop(user_id, None)
        if f:
            f.close()

        return result

    # ------------------------------------------------------------------
    # Log routing
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        # Console output with ANSI colours (original behaviour)
        super()._log(message)

        # File output without ANSI codes
        user_id = _current_user_id.get()
        f = self._files.get(user_id) if user_id else None
        if f:
            f.write(f"[{self.name}] {message}\n")
            f.flush()
