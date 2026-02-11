"""Tests for the agent selection feature.

Covers:
1. AgentId enum and Job model defaults
2. UploadParams schema validation
3. Upload route enabled_agents parsing
4. AgentSelectionPlugin before_agent_callback
5. Processor enabled_agents filtering
"""

import json
from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.job import ALL_AGENT_IDS, AgentId, Job
from app.schemas.job import UploadParams
from app.services.adapters import ADAPTER_REGISTRY
from app.services.processor import DocumentProcessor

# ---------------------------------------------------------------------------
# 1. AgentId enum + Job Model defaults
# ---------------------------------------------------------------------------


class TestAgentIdEnum:
    """Tests for the AgentId StrEnum."""

    def test_enum_has_four_members(self):
        assert len(AgentId) == 4

    def test_enum_values_are_strings(self):
        for member in AgentId:
            assert isinstance(member, str)
            assert isinstance(member.value, str)

    def test_enum_values(self):
        assert AgentId.NUMERIC_VALIDATION == "numeric_validation"
        assert AgentId.LOGIC_CONSISTENCY == "logic_consistency"
        assert AgentId.DISCLOSURE_COMPLIANCE == "disclosure_compliance"
        assert AgentId.EXTERNAL_SIGNAL == "external_signal"

    def test_all_agent_ids_matches_enum(self):
        assert ALL_AGENT_IDS == list(AgentId)

    def test_enum_is_json_serializable(self):
        """StrEnum values serialize cleanly as plain strings."""
        result = json.dumps(list(AgentId))
        parsed = json.loads(result)
        assert parsed == [
            "numeric_validation",
            "logic_consistency",
            "disclosure_compliance",
            "external_signal",
        ]

    def test_string_comparison(self):
        """StrEnum members compare equal to plain strings."""
        assert AgentId.NUMERIC_VALIDATION == "numeric_validation"
        assert "logic_consistency" in list(AgentId)

    def test_adk_name_property(self):
        """adk_name converts snake_case to PascalCase."""
        assert AgentId.NUMERIC_VALIDATION.adk_name == "NumericValidation"
        assert AgentId.LOGIC_CONSISTENCY.adk_name == "LogicConsistency"
        assert AgentId.DISCLOSURE_COMPLIANCE.adk_name == "DisclosureCompliance"
        assert AgentId.EXTERNAL_SIGNAL.adk_name == "ExternalSignal"


class TestJobModelDefaults:
    """Tests for the Job model's enabled_agents default behaviour."""

    def test_all_agent_ids_contains_exactly_four(self):
        assert len(ALL_AGENT_IDS) == 4
        assert "numeric_validation" in ALL_AGENT_IDS
        assert "logic_consistency" in ALL_AGENT_IDS
        assert "disclosure_compliance" in ALL_AGENT_IDS
        assert "external_signal" in ALL_AGENT_IDS

    def test_job_defaults_to_all_agents(self):
        job = Job()
        assert job.enabled_agents == ALL_AGENT_IDS

    def test_job_default_is_independent_copy(self):
        """Mutating one Job's list must not affect the constant or other Jobs."""
        job1 = Job()
        job1.enabled_agents.append("fake_agent")
        assert "fake_agent" not in ALL_AGENT_IDS
        job2 = Job()
        assert "fake_agent" not in job2.enabled_agents

    def test_job_with_explicit_enabled_agents(self):
        job = Job(enabled_agents=["numeric_validation"])
        assert job.enabled_agents == ["numeric_validation"]

    def test_job_with_two_agents(self):
        job = Job(enabled_agents=["numeric_validation", "logic_consistency"])
        assert job.enabled_agents == ["numeric_validation", "logic_consistency"]


# ---------------------------------------------------------------------------
# 2. UploadParams schema validation
# ---------------------------------------------------------------------------


class TestUploadParamsValidation:
    """Tests for Pydantic validation rules on UploadParams."""

    def test_defaults_to_all_agents(self):
        params = UploadParams()
        assert params.enabled_agents == list(ALL_AGENT_IDS)

    def test_single_valid_agent(self):
        params = UploadParams(enabled_agents=["numeric_validation"])
        assert params.enabled_agents == ["numeric_validation"]

    def test_multiple_valid_agents(self):
        params = UploadParams(
            enabled_agents=["numeric_validation", "disclosure_compliance"]
        )
        assert len(params.enabled_agents) == 2

    def test_all_four_agents_explicit(self):
        params = UploadParams(enabled_agents=list(ALL_AGENT_IDS))
        assert params.enabled_agents == list(ALL_AGENT_IDS)

    def test_empty_list_raises_error(self):
        with pytest.raises(ValidationError, match="At least one agent must be enabled"):
            UploadParams(enabled_agents=[])

    def test_invalid_agent_id_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid agent IDs"):
            UploadParams(enabled_agents=["invalid_agent"])

    def test_mix_valid_and_invalid_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid agent IDs"):
            UploadParams(enabled_agents=["numeric_validation", "totally_bogus"])

    def test_duplicates_are_deduplicated(self):
        """Duplicates should be removed while preserving order."""
        params = UploadParams(
            enabled_agents=[
                "logic_consistency",
                "numeric_validation",
                "numeric_validation",
            ]
        )
        assert params.enabled_agents == ["logic_consistency", "numeric_validation"]


# ---------------------------------------------------------------------------
# 3. Upload route enabled_agents parsing
# ---------------------------------------------------------------------------


class TestUploadRouteAgentParsing:
    """Tests for the POST /api/v1/documents/upload endpoint's enabled_agents handling."""

    @staticmethod
    def _make_mock_db(mock_job):
        """Build a mock AsyncSession that satisfies the upload route."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_final_result = MagicMock()
        mock_final_result.scalar_one.return_value = mock_job

        mock_db.execute.side_effect = [mock_count_result, mock_final_result]
        return mock_db

    @staticmethod
    def _make_mock_job(**overrides):
        defaults = {
            "id": uuid4(),
            "name": "Report #1",
            "status": "processing",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        defaults.update(overrides)
        job = Job(**defaults)
        job.documents = []
        return job

    def test_upload_with_enabled_agents_json(self):
        """enabled_agents form field as JSON array string should be parsed correctly."""
        from fastapi.testclient import TestClient

        from app.db import get_db
        from app.main import app

        mock_job = self._make_mock_job(
            enabled_agents=["numeric_validation"],
        )
        mock_db = self._make_mock_db(mock_job)

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        try:
            with patch("app.api.routes.documents.BackgroundTasks.add_task") as mock_bg:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={
                        "file": (
                            "test.docx",
                            BytesIO(b"x" * 1024),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                    data={"enabled_agents": json.dumps(["numeric_validation"])},
                )
                assert response.status_code == 200
                body = response.json()
                assert body["enabled_agents"] == ["numeric_validation"]

                # Verify background task was called with the selected agents
                mock_bg.assert_called_once()
                call_kwargs = mock_bg.call_args
                assert call_kwargs.kwargs.get("enabled_agents") == [
                    "numeric_validation"
                ] or (
                    len(call_kwargs.args) >= 5
                    and call_kwargs.args[4] == ["numeric_validation"]
                )
        finally:
            app.dependency_overrides = {}

    def test_upload_without_enabled_agents_defaults_to_all(self):
        """Omitting enabled_agents should default to all 4 agents."""
        from fastapi.testclient import TestClient

        from app.db import get_db
        from app.main import app

        mock_job = self._make_mock_job()
        mock_db = self._make_mock_db(mock_job)

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        try:
            with patch("app.api.routes.documents.BackgroundTasks.add_task"):
                response = client.post(
                    "/api/v1/documents/upload",
                    files={
                        "file": (
                            "test.docx",
                            BytesIO(b"x" * 1024),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                )
                assert response.status_code == 200
                body = response.json()
                assert body["enabled_agents"] == list(ALL_AGENT_IDS)
        finally:
            app.dependency_overrides = {}

    def test_upload_with_invalid_json_returns_400(self):
        """Malformed JSON in enabled_agents form field should return 400."""
        from fastapi.testclient import TestClient

        from app.db import get_db
        from app.main import app

        mock_job = self._make_mock_job()
        mock_db = self._make_mock_db(mock_job)

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        try:
            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "test.docx",
                        BytesIO(b"x" * 1024),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"enabled_agents": "not-valid-json["},
            )
            assert response.status_code == 400
            assert "Invalid enabled_agents format" in response.json()["detail"]
        finally:
            app.dependency_overrides = {}

    def test_upload_with_invalid_agent_id_returns_422(self):
        """Valid JSON but invalid agent ID should return 422."""
        from fastapi.testclient import TestClient

        from app.db import get_db
        from app.main import app

        mock_job = self._make_mock_job()
        mock_db = self._make_mock_db(mock_job)

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        try:
            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "test.docx",
                        BytesIO(b"x" * 1024),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={
                    "enabled_agents": json.dumps(["invalid_agent"]),
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 4. AgentSelectionPlugin
# ---------------------------------------------------------------------------


class TestAgentSelectionPlugin:
    """Tests for the AgentSelectionPlugin before_agent_callback."""

    @staticmethod
    def _make_agent(name: str):
        agent = MagicMock()
        agent.name = name
        return agent

    @staticmethod
    def _make_callback_context(state: dict):
        ctx = MagicMock()
        ctx.state = state
        return ctx

    @pytest.mark.asyncio
    async def test_returns_none_when_enabled_agents_not_in_state(self):
        """No enabled_agents key in state -> allow all agents (backwards compat)."""
        from agents.veritas_ai_agent.shared.agent_selection_plugin import (
            AgentSelectionPlugin,
        )

        plugin = AgentSelectionPlugin()
        agent = self._make_agent("NumericValidation")
        ctx = self._make_callback_context({})
        result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_agent_is_enabled(self):
        """Agent is in the enabled list -> allow (return None)."""
        from agents.veritas_ai_agent.shared.agent_selection_plugin import (
            AgentSelectionPlugin,
        )

        plugin = AgentSelectionPlugin()
        agent = self._make_agent("NumericValidation")
        ctx = self._make_callback_context(
            {"enabled_agents": ["NumericValidation", "LogicConsistency"]}
        )
        result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_content_when_agent_is_disabled(self):
        """Agent not in enabled list -> skip (return Content)."""
        from google.genai import types

        from agents.veritas_ai_agent.shared.agent_selection_plugin import (
            AgentSelectionPlugin,
        )

        plugin = AgentSelectionPlugin()
        agent = self._make_agent("NumericValidation")
        ctx = self._make_callback_context({"enabled_agents": ["LogicConsistency"]})
        result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)
        assert isinstance(result, types.Content)
        assert result.role == "model"
        assert "skipped" in result.parts[0].text.lower()

    @pytest.mark.asyncio
    async def test_all_four_agents_skip_correctly(self):
        """Each ADK agent name is checked directly against enabled list."""
        from google.genai import types

        from agents.veritas_ai_agent.shared.agent_selection_plugin import (
            AgentSelectionPlugin,
        )

        plugin = AgentSelectionPlugin()
        adk_names = [
            "NumericValidation",
            "LogicConsistency",
            "DisclosureCompliance",
            "ExternalSignal",
        ]

        for adk_name in adk_names:
            agent = self._make_agent(adk_name)

            # Agent IS enabled
            ctx_allow = self._make_callback_context({"enabled_agents": [adk_name]})
            assert (
                await plugin.before_agent_callback(
                    agent=agent, callback_context=ctx_allow
                )
                is None
            ), f"{adk_name} should be allowed when in enabled list"

            # Agent is NOT enabled
            ctx_skip = self._make_callback_context({"enabled_agents": []})
            result = await plugin.before_agent_callback(
                agent=agent, callback_context=ctx_skip
            )
            assert isinstance(result, types.Content), (
                f"{adk_name} should be skipped when not in enabled list"
            )

    @pytest.mark.asyncio
    async def test_unknown_agent_name_passes_through(self):
        """A sub-agent name not in _SELECTABLE should NOT be blocked."""
        from agents.veritas_ai_agent.shared.agent_selection_plugin import (
            AgentSelectionPlugin,
        )

        plugin = AgentSelectionPlugin()
        agent = self._make_agent("TableNamer")
        ctx = self._make_callback_context({"enabled_agents": ["NumericValidation"]})
        result = await plugin.before_agent_callback(agent=agent, callback_context=ctx)
        assert result is None


# ---------------------------------------------------------------------------
# 5. Processor enabled_agents filtering
# ---------------------------------------------------------------------------


class TestProcessorEnabledAgentsFiltering:
    """Tests for DocumentProcessor methods that filter by enabled_agents."""

    def test_extract_all_findings_only_enabled_agents(self):
        """_extract_all_findings should only iterate adapters for enabled_agents."""
        db = MagicMock()
        processor = DocumentProcessor(db)

        state = {
            "numeric_validation": {
                "numeric_validation_output": {
                    "issues": [
                        {
                            "issue_description": "Test issue",
                            "check_type": "in_table",
                            "formula": "1+1=3",
                            "difference": 1.0,
                        }
                    ]
                }
            },
            "logic_consistency": {
                "logic_consistency_reviewer_output": {
                    "findings": [
                        {
                            "contradiction": "Test contradiction",
                            "severity": "high",
                            "claim": "claim",
                            "reasoning": "reason",
                            "source_refs": [],
                        }
                    ]
                }
            },
        }

        # Only enable numeric_validation
        result = processor._extract_all_findings(
            state, enabled_agents=["numeric_validation"]
        )
        assert "numeric_validation" in result
        assert "logic_consistency" not in result
        assert "disclosure_compliance" not in result
        assert "external_signal" not in result
        assert len(result["numeric_validation"]) == 1

    def test_extract_all_findings_all_agents_when_none(self):
        """_extract_all_findings with enabled_agents=None iterates all adapters."""
        db = MagicMock()
        processor = DocumentProcessor(db)

        # Empty state -> all adapters are iterated but return empty lists
        result = processor._extract_all_findings({}, enabled_agents=None)
        assert len(result) == len(ADAPTER_REGISTRY)

    def test_extract_all_findings_two_agents(self):
        """Two-agent subset should only include those two in the output."""
        db = MagicMock()
        processor = DocumentProcessor(db)

        state = {
            "numeric_validation": {"numeric_validation_output": {"issues": []}},
            "disclosure_compliance": {"disclosure_reviewer_output": {"findings": []}},
        }

        result = processor._extract_all_findings(
            state,
            enabled_agents=["numeric_validation", "disclosure_compliance"],
        )
        assert set(result.keys()) == {"numeric_validation", "disclosure_compliance"}

    @pytest.mark.asyncio
    async def test_check_and_notify_agents_filters_by_enabled(self):
        """_check_and_notify_agents should only process enabled adapters."""
        db = MagicMock()
        db.commit = AsyncMock()
        processor = DocumentProcessor(db)

        job_id = uuid4()
        agents_started = {"numeric_validation", "logic_consistency"}
        agents_completed = set()

        state = {
            "numeric_validation_output": {
                "issues": [
                    {
                        "issue_description": "test",
                        "check_type": "in_table",
                        "formula": "1=2",
                        "difference": 1.0,
                    }
                ]
            },
        }

        with patch.object(processor, "_send_websocket_message", new_callable=AsyncMock):
            await processor._check_and_notify_agents(
                job_id=job_id,
                state=state,
                agents_started=agents_started,
                agents_completed=agents_completed,
                is_final=True,
                enabled_agents=["numeric_validation"],
            )

        # Only numeric_validation should have been checked/completed
        assert "numeric_validation" in agents_completed
        assert "logic_consistency" not in agents_completed

    @pytest.mark.asyncio
    async def test_check_and_notify_all_when_enabled_is_none(self):
        """When enabled_agents is None, all adapters should be processed."""
        db = MagicMock()
        db.commit = AsyncMock()
        processor = DocumentProcessor(db)

        job_id = uuid4()
        agents_started = {"numeric_validation", "logic_consistency"}
        agents_completed = set()

        # State with numeric output at the flat level
        state = {
            "numeric_validation_output": {
                "issues": [
                    {
                        "issue_description": "test",
                        "check_type": "in_table",
                        "formula": "1=2",
                        "difference": 1.0,
                    }
                ]
            },
            "logic_consistency_reviewer_output": {
                "findings": [
                    {
                        "contradiction": "test",
                        "severity": "high",
                        "claim": "c",
                        "reasoning": "r",
                        "source_refs": [],
                    }
                ]
            },
        }

        with patch.object(processor, "_send_websocket_message", new_callable=AsyncMock):
            await processor._check_and_notify_agents(
                job_id=job_id,
                state=state,
                agents_started=agents_started,
                agents_completed=agents_completed,
                is_final=True,
                enabled_agents=None,
            )

        # Both should be completed
        assert "numeric_validation" in agents_completed
        assert "logic_consistency" in agents_completed
