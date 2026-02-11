"""Tests for custom ADK plugins (FileLoggingPlugin, JobAwareDebugPlugin)."""

import asyncio
from unittest.mock import MagicMock

import pytest
import yaml
from veritas_ai_agent.shared.debug_plugin import JobAwareDebugPlugin
from veritas_ai_agent.shared.file_logging_plugin import FileLoggingPlugin


def _make_invocation_context(user_id: str) -> MagicMock:
    """Create a minimal mock InvocationContext with the given user_id."""
    session = MagicMock()
    session.id = "sess-1"
    session.user_id = user_id
    session.app_name = "test_app"
    session.state = {}
    session.events = []

    agent = MagicMock()
    agent.name = "TestAgent"

    ctx = MagicMock()
    ctx.user_id = user_id
    ctx.invocation_id = f"inv-{user_id}"
    ctx.session = session
    ctx.branch = None
    ctx.agent = agent
    ctx.app_name = "test_app"
    return ctx


# -----------------------------------------------------------------------
# FileLoggingPlugin
# -----------------------------------------------------------------------


class TestFileLoggingPlugin:
    @pytest.mark.asyncio
    async def test_creates_log_file_on_before_run(self, tmp_path, monkeypatch):
        """Plugin should create agent_trace_{user_id}.log on before_run."""
        monkeypatch.chdir(tmp_path)
        plugin = FileLoggingPlugin()
        ctx = _make_invocation_context("job-111")

        await plugin.before_run_callback(invocation_context=ctx)

        log_file = tmp_path / "agent_trace_job-111.log"
        assert log_file.exists()

        # Cleanup
        await plugin.after_run_callback(invocation_context=ctx)

    @pytest.mark.asyncio
    async def test_log_writes_to_file(self, tmp_path, monkeypatch):
        """_log() should write to the correct per-job file."""
        monkeypatch.chdir(tmp_path)
        plugin = FileLoggingPlugin()
        ctx = _make_invocation_context("job-222")

        await plugin.before_run_callback(invocation_context=ctx)
        plugin._log("Hello from the test")

        log_file = tmp_path / "agent_trace_job-222.log"
        content = log_file.read_text()
        assert "[logging_plugin] Hello from the test" in content

        await plugin.after_run_callback(invocation_context=ctx)

    @pytest.mark.asyncio
    async def test_after_run_closes_file(self, tmp_path, monkeypatch):
        """after_run should close the file handle and remove it from _files."""
        monkeypatch.chdir(tmp_path)
        plugin = FileLoggingPlugin()
        ctx = _make_invocation_context("job-333")

        await plugin.before_run_callback(invocation_context=ctx)
        assert "job-333" in plugin._files

        await plugin.after_run_callback(invocation_context=ctx)
        assert "job-333" not in plugin._files

    @pytest.mark.asyncio
    async def test_concurrent_jobs_isolated(self, tmp_path, monkeypatch):
        """Two concurrent jobs should write to separate files without cross-talk."""
        monkeypatch.chdir(tmp_path)
        plugin = FileLoggingPlugin()

        ctx_a = _make_invocation_context("job-aaa")
        ctx_b = _make_invocation_context("job-bbb")

        async def run_job(ctx: MagicMock, message: str):
            await plugin.before_run_callback(invocation_context=ctx)
            plugin._log(message)
            # Yield control to simulate interleaving
            await asyncio.sleep(0)
            plugin._log(f"{message} again")
            await plugin.after_run_callback(invocation_context=ctx)

        await asyncio.gather(
            run_job(ctx_a, "from-A"),
            run_job(ctx_b, "from-B"),
        )

        file_a = (tmp_path / "agent_trace_job-aaa.log").read_text()
        file_b = (tmp_path / "agent_trace_job-bbb.log").read_text()

        assert "from-A" in file_a
        assert "from-A again" in file_a
        assert "from-B" not in file_a

        assert "from-B" in file_b
        assert "from-B again" in file_b
        assert "from-A" not in file_b

    @pytest.mark.asyncio
    async def test_log_without_active_job_does_not_crash(self):
        """_log() should not raise when no job file is active."""
        plugin = FileLoggingPlugin()
        # Should not raise — just prints to console
        plugin._log("orphan message")


# -----------------------------------------------------------------------
# JobAwareDebugPlugin
# -----------------------------------------------------------------------


class TestJobAwareDebugPlugin:
    @pytest.mark.asyncio
    async def test_writes_per_job_yaml(self, tmp_path, monkeypatch):
        """Plugin should write to adk_debug_{user_id}.yaml, not adk_debug.yaml."""
        monkeypatch.chdir(tmp_path)
        plugin = JobAwareDebugPlugin()

        ctx = _make_invocation_context("job-444")

        # before_run sets up internal state
        await plugin.before_run_callback(invocation_context=ctx)
        # after_run writes the YAML file
        await plugin.after_run_callback(invocation_context=ctx)

        per_job_file = tmp_path / "adk_debug_job-444.yaml"
        default_file = tmp_path / "adk_debug.yaml"

        assert per_job_file.exists(), "Per-job debug file was not created"
        assert not default_file.exists(), "Default adk_debug.yaml should not be created"

        # Verify it's valid YAML with expected structure
        content = per_job_file.read_text()
        docs = list(yaml.safe_load_all(content))
        assert len(docs) >= 1
        assert docs[0]["invocation_id"] == "inv-job-444"

    @pytest.mark.asyncio
    async def test_concurrent_jobs_write_separate_files(self, tmp_path, monkeypatch):
        """Two jobs should produce two separate debug YAML files."""
        monkeypatch.chdir(tmp_path)
        plugin = JobAwareDebugPlugin()

        ctx_x = _make_invocation_context("job-xxx")
        ctx_y = _make_invocation_context("job-yyy")

        # Run both invocations sequentially (debug plugin is sync-safe
        # since it writes in after_run only)
        await plugin.before_run_callback(invocation_context=ctx_x)
        await plugin.after_run_callback(invocation_context=ctx_x)

        await plugin.before_run_callback(invocation_context=ctx_y)
        await plugin.after_run_callback(invocation_context=ctx_y)

        assert (tmp_path / "adk_debug_job-xxx.yaml").exists()
        assert (tmp_path / "adk_debug_job-yyy.yaml").exists()

        # Verify each file has the correct invocation_id
        doc_x = next(
            yaml.safe_load_all((tmp_path / "adk_debug_job-xxx.yaml").read_text())
        )
        doc_y = next(
            yaml.safe_load_all((tmp_path / "adk_debug_job-yyy.yaml").read_text())
        )
        assert doc_x["invocation_id"] == "inv-job-xxx"
        assert doc_y["invocation_id"] == "inv-job-yyy"

    @pytest.mark.asyncio
    async def test_entries_written_incrementally(self, tmp_path, monkeypatch):
        """Entries should appear on disk before after_run_callback."""
        monkeypatch.chdir(tmp_path)
        plugin = JobAwareDebugPlugin()

        ctx = _make_invocation_context("job-inc")
        per_job_file = tmp_path / "adk_debug_job-inc.yaml"

        await plugin.before_run_callback(invocation_context=ctx)

        # File should already exist with header + invocation_start entry
        assert per_job_file.exists(), "File should be created at before_run"
        docs_before = list(yaml.safe_load_all(per_job_file.read_text()))
        assert docs_before[0]["invocation_id"] == "inv-job-inc"
        entry_types_before = {d["entry_type"] for d in docs_before[1:]}
        assert "invocation_start" in entry_types_before

        # Simulate an event callback — this triggers _add_entry internally
        event = MagicMock()
        event.id = "evt-1"
        event.author = "TestAgent"
        event.content = None
        event.partial = False
        event.turn_complete = False
        event.branch = None
        event.actions = None
        event.grounding_metadata = None
        event.usage_metadata = None
        event.error_code = None
        event.long_running_tool_ids = None
        event.is_final_response = MagicMock(return_value=False)

        await plugin.on_event_callback(invocation_context=ctx, event=event)

        # The event entry should be on disk already (before after_run)
        docs_mid = list(yaml.safe_load_all(per_job_file.read_text()))
        entry_types_mid = {d["entry_type"] for d in docs_mid[1:]}
        assert "event" in entry_types_mid

        # Finalize
        await plugin.after_run_callback(invocation_context=ctx)

        docs_final = list(yaml.safe_load_all(per_job_file.read_text()))
        entry_types_final = {d["entry_type"] for d in docs_final[1:]}
        assert "invocation_end" in entry_types_final
