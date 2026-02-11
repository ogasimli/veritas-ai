"""JobAwareDebugPlugin — extends ADK DebugLoggingPlugin for incremental writes.

Writes debug entries to ``adk_debug_{user_id}.yaml`` incrementally as they
arrive, rather than buffering everything in memory and flushing once after the
entire agent session completes.  This lets the debug-log endpoint serve
partial debug YAML while the run is still in progress.

File format
-----------
Multi-document YAML (``---``-separated).  First document is the invocation
header (metadata); every subsequent document is a single debug entry.
Use ``yaml.safe_load_all(path.read_text())`` to iterate over all documents.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from google.adk.plugins import DebugLoggingPlugin
from typing_extensions import override

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)


def _writable_dir() -> Path:
    """Return cwd if writable, otherwise /tmp (Cloud Run has read-only /app)."""
    cwd = Path.cwd()
    if os.access(cwd, os.W_OK):
        return cwd
    return Path("/tmp")


class JobAwareDebugPlugin(DebugLoggingPlugin):
    """DebugLoggingPlugin that writes entries incrementally to a per-job file.

    Output files:  ``{cwd}/adk_debug_{user_id}.yaml``

    How it works
    ------------
    * ``before_run_callback`` resolves the per-job output path and writes the
      YAML invocation header as the first document.
    * Every call to ``_add_entry`` immediately appends the serialised entry as
      a new YAML document so that consumers can tail the file in real time.
    * ``after_run_callback`` flushes the final session-state snapshot and
      invocation-end marker, then cleans up in-memory state.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._flushed_count: dict[str, int] = {}
        self._header_written: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle: open file on run start
    # ------------------------------------------------------------------

    @override
    async def before_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """Set the per-job output path and write the YAML invocation header."""
        user_id = invocation_context.user_id
        if user_id:
            self._output_path = _writable_dir() / f"adk_debug_{user_id}.yaml"

        # Let the parent initialise _invocation_states etc.
        # Note: parent calls _add_entry("invocation_start") here — our
        # override buffers it because the header hasn't been written yet.
        result = await super().before_run_callback(
            invocation_context=invocation_context
        )

        # Write invocation header as the first YAML document
        invocation_id = invocation_context.invocation_id
        state = self._invocation_states.get(invocation_id)
        if state:
            header = {
                "invocation_id": state.invocation_id,
                "session_id": state.session_id,
                "app_name": state.app_name,
                "user_id": state.user_id,
                "start_time": state.start_time,
            }
            self._append_yaml_document(header)
            self._header_written.add(invocation_id)
            # Now flush entries that were buffered during super().before_run
            self._flush_pending_entries(invocation_id)

        return result

    # ------------------------------------------------------------------
    # Incremental entry writing
    # ------------------------------------------------------------------

    @override
    def _add_entry(
        self,
        invocation_id: str,
        entry_type: str,
        agent_name: str | None = None,
        **data: Any,
    ) -> None:
        """Add entry to in-memory state *and* append it to disk immediately."""
        super()._add_entry(invocation_id, entry_type, agent_name=agent_name, **data)
        self._flush_pending_entries(invocation_id)

    def _flush_pending_entries(self, invocation_id: str) -> None:
        """Write any un-flushed entries to disk as individual YAML documents."""
        # Don't flush until the header document has been written
        if invocation_id not in self._header_written:
            return

        state = self._invocation_states.get(invocation_id)
        if not state:
            return

        already = self._flushed_count.get(invocation_id, 0)
        pending = state.entries[already:]
        if not pending:
            return

        try:
            for entry in pending:
                entry_data = entry.model_dump(mode="json", exclude_none=True)
                self._append_yaml_document(entry_data)
            self._flushed_count[invocation_id] = len(state.entries)
        except Exception as e:
            logger.error("Failed to flush debug entries: %s", e)

    # ------------------------------------------------------------------
    # YAML helpers
    # ------------------------------------------------------------------

    def _append_yaml_document(self, data: dict[str, Any]) -> None:
        """Append a ``---``-separated YAML document to the output file."""
        try:
            with self._output_path.open("a", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120,
                )
        except Exception as e:
            logger.error("Failed to append YAML document: %s", e)

    # ------------------------------------------------------------------
    # Lifecycle: finalise on run end
    # ------------------------------------------------------------------

    @override
    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """Write final entries and clean up (skip parent's bulk write)."""
        invocation_id = invocation_context.invocation_id

        if invocation_id not in self._invocation_states:
            logger.warning(
                "No debug state for invocation %s, skipping write", invocation_id
            )
            return

        # Add session-state snapshot (mirrors parent behaviour)
        if self._include_session_state:
            session = invocation_context.session
            self._add_entry(
                invocation_id,
                "session_state_snapshot",
                state=self._safe_serialize(session.state),
                event_count=len(session.events),
            )

        # Final marker
        self._add_entry(invocation_id, "invocation_end")

        logger.debug(
            "Wrote incremental debug data for invocation %s to %s",
            invocation_id,
            self._output_path,
        )

        # Cleanup in-memory state
        self._invocation_states.pop(invocation_id, None)
        self._flushed_count.pop(invocation_id, None)
        self._header_written.discard(invocation_id)
