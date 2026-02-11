"""JobAwareDebugPlugin — extends ADK DebugLoggingPlugin to write per-job files.

Overrides ``after_run_callback`` to write to ``adk_debug_{user_id}.yaml``
instead of a fixed path, making concurrent jobs safe and removing the need
for the processor to rename the file after the run.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from google.adk.plugins import DebugLoggingPlugin

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext


class JobAwareDebugPlugin(DebugLoggingPlugin):
    """DebugLoggingPlugin that writes to a per-job file automatically.

    Output files:  ``{cwd}/adk_debug_{user_id}.yaml``
    """

    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """Point output path to the per-job file, then let parent write."""
        user_id = invocation_context.user_id
        if user_id:
            self._output_path = Path.cwd() / f"adk_debug_{user_id}.yaml"
        return await super().after_run_callback(invocation_context=invocation_context)
