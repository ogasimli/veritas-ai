"""Dummy agent service with InMemoryRunner-compatible interface for testing.

This service mimics the InMemoryRunner interface to allow drop-in replacement
for frontend testing without inference costs. It replays realistic event sequences
extracted from real agent runs.
"""

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


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
            # Populate with final accumulated state from dummy service
            session.state = self._dummy_service._accumulated_state.copy()
        return session or MockSession(session_id=session_id, user_id=user_id)


class DummyAgentService:
    """Simulates agent responses with InMemoryRunner-compatible interface."""

    def __init__(self, app: Any = None):
        """Initialize dummy agent service.

        Args:
            app: ADK app object (ignored, included for interface compatibility)
        """
        self.app = app
        self.app_name = "dummy_veritas_ai"
        self._session_service = MockSessionService(self)
        self._accumulated_state: dict[str, Any] = {}

        # Load event sequence from JSON
        self.events_data = self._load_events()

    @property
    def session_service(self) -> MockSessionService:
        """Get the mock session service."""
        return self._session_service

    def _load_events(self) -> dict[str, Any]:
        """Load event sequence from JSON file."""
        events_file = Path(__file__).parent / "dummy_events.json"

        if events_file.exists():
            with open(events_file) as f:
                return json.load(f)
        else:
            # Return default events if file doesn't exist
            print(
                "⚠️  Warning: dummy_events.json not found, using minimal event sequence",
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

    async def run_async(self, user_id: str, session_id: str, new_message: Any) -> Any:
        """
        Run the dummy agent pipeline, yielding events.

        This mimics InMemoryRunner.run_async() interface by replaying
        real events extracted from a session dump.

        Args:
            user_id: User ID for the session
            session_id: Session ID
            new_message: User message (ignored in dummy mode)
        """
        # Reset accumulated state for this run
        self._accumulated_state = {}

        events = self.events_data.get("events", [])

        for event_data in events:
            # Use a much smaller delay for faster testing
            raw_delay = event_data.get("delay_ms", 100)
            # Cap at 500ms and scale down significantly (e.g., 5% of original)
            delay_seconds = min(500, raw_delay * 0.05) / 1000.0
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            # Get state delta and is_final from event data
            state_delta = event_data.get("state_delta", {})
            is_final = event_data.get("is_final", False)
            branch = event_data.get("branch", "")
            author = event_data.get("author", "")

            # Accumulate state
            if state_delta:
                self._accumulated_state.update(state_delta)

            # Create and yield mock event with proper is_final marking and branch info
            event = MockEvent(
                event_type=event_data.get("type", "AgentEvent"),
                state_delta=state_delta,
                is_final=is_final,
                branch=branch,
                author=author,
            )

            yield event
