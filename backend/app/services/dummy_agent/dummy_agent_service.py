"""Dummy agent service with InMemoryRunner-compatible interface for testing.

This service mimics the InMemoryRunner interface to allow drop-in replacement
for frontend testing without inference costs. It replays realistic event sequences
extracted from real agent runs.

Supports two fixture sources:
1. Per-validator YAML files in ``fixtures/`` (preferred — derived from ``adk_debug.yaml``)
2. Legacy ``dummy_events.json`` (fallback during transition)
"""

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml  # type: ignore[import-untyped]

# Branch prefix → processor agent_id mapping
_BRANCH_PREFIX_TO_AGENT = {
    "AuditOrchestrator.NumericValidation": "numeric_validation",
    "AuditOrchestrator.LogicConsistency": "logic_consistency",
    "AuditOrchestrator.DisclosureCompliance": "disclosure_compliance",
    "AuditOrchestrator.ExternalSignal": "external_signal",
}

# Validator filenames → expected processor agent_ids
_VALID_FIXTURES = {
    "numeric_validation",
    "logic_consistency",
    "disclosure_compliance",
    "external_signal",
}


class MockActions:
    """Mock actions object with state delta."""

    def __init__(self, state_delta: dict[str, Any] | None = None):
        self.state_delta = state_delta or {}


class MockEvent:
    """Mock event that mimics ADK event structure."""

    def __init__(
        self,
        event_type: str,
        state_delta: dict[str, Any] | None = None,
        is_final: bool = False,
        branch: str | None = None,
        author: str | None = None,
    ):
        self.event_type = event_type
        self.actions = MockActions(state_delta) if state_delta else None
        self._is_final = is_final
        self.branch = branch
        self.author = author

    def is_final_response(self) -> bool:
        """Check if this is a final response event."""
        return self._is_final


class MockSession:
    """Mock session object."""

    def __init__(
        self, session_id: str, user_id: str, state: dict[str, Any] | None = None
    ):
        self.id = session_id
        self.user_id = user_id
        self.state = state or {}


class MockSessionService:
    """Mock session service that mimics ADK's session service."""

    def __init__(self, dummy_service: "DummyAgentService"):
        self._dummy_service = dummy_service
        self._sessions: dict[str, MockSession] = {}

    async def create_session(self, app_name: str, user_id: str) -> MockSession:
        """Create a new mock session."""
        session_id = str(uuid4())
        session = MockSession(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        return session

    async def get_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> MockSession:
        """Get an existing mock session with final state."""
        session = self._sessions.get(session_id)
        if session:
            session.state = self._dummy_service._final_state.copy()
        return session or MockSession(session_id=session_id, user_id=user_id)


class DummyAgentService:
    """Simulates agent responses with InMemoryRunner-compatible interface."""

    def __init__(self, app: Any = None):
        self.app = app
        self.app_name = "dummy_veritas_ai"
        self._session_service = MockSessionService(self)
        self._accumulated_state: dict[str, Any] = {}
        self._final_state: dict[str, Any] = {}

        # Load event sequence
        self.events_data = self._load_events()

    @property
    def session_service(self) -> MockSessionService:
        return self._session_service

    # ── Fixture loading ──────────────────────────────────────────────

    def _load_events(self) -> dict[str, Any]:
        """Load event sequence from per-validator YAMLs or legacy JSON."""
        fixtures_dir = Path(__file__).parent / "fixtures"

        # Prefer per-validator YAML fixtures
        if fixtures_dir.is_dir():
            yamls = list(fixtures_dir.glob("*.yaml"))
            if yamls:
                print(
                    f"📂 Loading per-validator fixtures from {fixtures_dir} "
                    f"({len(yamls)} files)",
                    flush=True,
                )
                return self._load_per_validator_fixtures(fixtures_dir, yamls)

        # Fallback: legacy JSON
        events_file = Path(__file__).parent / "dummy_events.json"
        if events_file.exists():
            print(
                "📂 Loading legacy dummy_events.json",
                flush=True,
            )
            with open(events_file) as f:
                return json.load(f)

        print(
            "⚠️  Warning: No fixtures found, using minimal event sequence",
            flush=True,
        )
        return {
            "metadata": {"source": "inline_default"},
            "events": [
                {
                    "event_number": 1,
                    "type": "AgentEvent",
                    "state_delta": {},
                    "delay_ms": 0,
                }
            ],
            "final_state": {},
        }

    def _load_per_validator_fixtures(
        self, fixtures_dir: Path, yaml_files: list[Path]
    ) -> dict[str, Any]:
        """Load and merge per-validator YAML fixture files."""
        all_events: list[dict[str, Any]] = []
        merged_final_state: dict[str, Any] = {}
        loaded_validators: list[str] = []

        for yaml_path in yaml_files:
            validator_name = yaml_path.stem
            if validator_name not in _VALID_FIXTURES:
                print(
                    f"   ⚠️  Skipping unknown fixture: {yaml_path.name}",
                    flush=True,
                )
                continue

            parsed = self._parse_adk_debug_yaml(yaml_path, validator_name)
            all_events.extend(parsed["events"])
            merged_final_state.update(parsed["final_state"])
            loaded_validators.append(validator_name)
            print(
                f"   ✅ {validator_name}: {len(parsed['events'])} events, "
                f"{len(parsed['final_state'])} state keys",
                flush=True,
            )

        # Sort by timestamp to interleave events realistically
        all_events.sort(key=lambda e: e.get("timestamp", 0))

        # Re-compute delay_ms from timestamp diffs
        for i in range(len(all_events)):
            if i == 0:
                all_events[i]["delay_ms"] = 0
            else:
                prev_ts = all_events[i - 1].get("timestamp", 0)
                curr_ts = all_events[i].get("timestamp", 0)
                all_events[i]["delay_ms"] = max(0, int((curr_ts - prev_ts) * 1000))

        print(
            f"   📊 Merged: {len(all_events)} events from {loaded_validators}",
            flush=True,
        )

        self._final_state = merged_final_state

        return {
            "metadata": {
                "source": "per_validator_fixtures",
                "validators": loaded_validators,
            },
            "events": all_events,
            "final_state": merged_final_state,
        }

    @staticmethod
    def _parse_adk_debug_yaml(path: Path, validator_name: str) -> dict[str, Any]:
        """Parse an ``adk_debug.yaml`` file into events and final state.

        Extracts ``entry_type == "event"`` entries and the
        ``session_state_snapshot`` if present.
        """
        with open(path) as f:
            doc = yaml.safe_load(f)

        if not isinstance(doc, dict) or "entries" not in doc:
            return {"events": [], "final_state": {}}

        raw_entries = doc["entries"]
        events: list[dict[str, Any]] = []
        final_state: dict[str, Any] = {}
        prev_timestamp = 0.0

        for entry in raw_entries:
            entry_type = entry.get("entry_type")
            data = entry.get("data", {})

            if entry_type == "event":
                # Extract timestamp
                ts_raw = entry.get("timestamp", "")
                if isinstance(ts_raw, str):
                    # ISO format — convert to epoch-ish float for sorting
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(ts_raw)
                        ts = dt.timestamp()
                    except (ValueError, TypeError):
                        ts = prev_timestamp
                elif isinstance(ts_raw, (int, float)):
                    ts = float(ts_raw)
                else:
                    ts = prev_timestamp

                delay_ms = (
                    max(0, int((ts - prev_timestamp) * 1000)) if prev_timestamp else 0
                )
                prev_timestamp = ts

                # Extract event fields
                state_delta = {}
                actions = data.get("actions") or {}
                if isinstance(actions, dict):
                    state_delta = actions.get("state_delta") or {}

                branch_raw = data.get("branch") or ""
                author = data.get("author") or ""
                is_final = bool(data.get("is_final_response"))

                # Prefix branch so processor's branch-based agent detection works.
                # In a full orchestrator run, branches look like
                #   audit_orchestrator.numeric_validation.NumericValidation.Aggregator
                # Per-validator fixtures have branches like
                #   AuditOrchestrator.NumericValidation...
                # We map to: audit_orchestrator.<agent_id>.<original_branch>
                if branch_raw:
                    branch = f"audit_orchestrator.{validator_name}.{branch_raw}"
                else:
                    branch = f"audit_orchestrator.{validator_name}"

                events.append(
                    {
                        "event_number": len(events) + 1,
                        "type": "AgentEvent",
                        "author": author,
                        "branch": branch,
                        "state_delta": state_delta,
                        "is_final": is_final,
                        "timestamp": ts,
                        "delay_ms": delay_ms,
                    }
                )

            elif entry_type == "session_state_snapshot":
                # The snapshot data contains {"state": {...}, "event_count": N}
                snapshot = data.get("state", data)
                if isinstance(snapshot, dict):
                    final_state.update(snapshot)

        return {"events": events, "final_state": final_state}

    # ── Runner interface ─────────────────────────────────────────────

    async def run_async(self, user_id: str, session_id: str, new_message: Any) -> Any:
        """
        Run the dummy agent pipeline, yielding events.

        Mimics InMemoryRunner.run_async() by replaying real events.
        """
        self._accumulated_state = {}

        events = self.events_data.get("events", [])

        for event_data in events:
            # Smaller delay for faster testing
            raw_delay = event_data.get("delay_ms", 100)
            delay_seconds = min(500, raw_delay * 0.05) / 1000.0
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            state_delta = event_data.get("state_delta", {})
            is_final = event_data.get("is_final", False)
            branch = event_data.get("branch", "")
            author = event_data.get("author", "")

            if state_delta:
                self._accumulated_state.update(state_delta)

            event = MockEvent(
                event_type=event_data.get("type", "AgentEvent"),
                state_delta=state_delta,
                is_final=is_final,
                branch=branch,
                author=author,
            )

            yield event

        # Merge final state from fixtures if available
        if self._final_state:
            self._accumulated_state.update(self._final_state)
