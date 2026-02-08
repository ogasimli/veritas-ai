"""Document processing service with agent pipeline integration."""

from datetime import datetime
from typing import Any
from uuid import UUID

from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
from sqlalchemy.ext.asyncio import AsyncSession
from veritas_ai_agent import app

from app.config import get_settings
from app.models.finding import AgentResult as AgentResultModel
from app.models.job import Job
from app.schemas.finding import NormalizedFinding
from app.services.adapters import ADAPTER_REGISTRY, AgentAdapter
from app.services.dummy_agent.dummy_agent_service import DummyAgentService
from app.services.websocket_manager import manager


class DocumentProcessor:
    """Processes documents through validation agent pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _get_agent_namespace(
        state: dict[str, Any], agent_id: str
    ) -> dict[str, Any]:
        """Get the state namespace for an agent, or return the state itself if not namespaced."""
        if agent_id in state and isinstance(state[agent_id], dict):
            return state[agent_id]
        return state

    async def _send_websocket_message(
        self, job_id: UUID, message_type: str, agent_id: str
    ):
        """Send WebSocket message for agent state change."""
        message = {
            "type": message_type,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        log_prefix = "🎯" if message_type == "agent_started" else "✅"
        status_msg = "STARTED" if message_type == "agent_started" else "COMPLETED"

        print(f"   {log_prefix} Agent '{agent_id}' {status_msg}", flush=True)
        print("      📤 Sending WebSocket message", flush=True)

        await manager.send_to_audit(str(job_id), message)

    async def _save_agent_results_to_db(
        self,
        job_id: UUID,
        adapter: AgentAdapter,
        findings: list[NormalizedFinding] | None,
        error: dict | None,
    ):
        """Save results (findings or error) to database immediately."""
        if error:
            result = AgentResultModel(
                job_id=job_id,
                agent_id=adapter.agent_id,
                category=adapter.category,
                error=error.get("error_message", str(error)),
                raw_data=error,
            )
            self.db.add(result)
            print(
                f"      💾 Saved ERROR to DB for agent '{adapter.agent_id}'", flush=True
            )

        elif findings:
            for nf in findings:
                result = AgentResultModel(
                    job_id=job_id,
                    agent_id=adapter.agent_id,
                    category=adapter.category,
                    raw_data=nf.model_dump(),
                    description=nf.description,
                    severity=nf.severity,
                    source_refs=nf.source_refs,
                    reasoning=nf.reasoning,
                )
                self.db.add(result)
            print(
                f"      💾 Saved {len(findings)} findings to DB for agent '{adapter.agent_id}'",
                flush=True,
            )

        elif findings is not None:
            # findings is empty list -> Save empty success result
            result = AgentResultModel(
                job_id=job_id,
                agent_id=adapter.agent_id,
                category=adapter.category,
                raw_data={},
                description=None,
                severity=None,
            )
            self.db.add(result)
            print(
                f"      💾 Saved EMPTY result to DB for agent '{adapter.agent_id}'",
                flush=True,
            )

        # Commit immediately so frontend can fetch
        await self.db.commit()

    async def _check_and_notify_agents(
        self,
        job_id: UUID,
        state: dict[str, Any],
        agents_started: set,
        agents_completed: set,
        specific_agent: str | None = None,
        is_final: bool = False,
    ):
        """Check agent states and send WebSocket notifications."""
        for adapter in ADAPTER_REGISTRY.values():
            agent_id = adapter.agent_id
            if agent_id in agents_started and agent_id not in agents_completed:
                ns = self._get_agent_namespace(state, agent_id)

                # Check for errors on every event
                error = adapter.extract_error(ns)

                # Check for findings only if this is the final event for this specific agent
                findings = None
                is_agent_final = is_final and (
                    specific_agent is None or specific_agent == agent_id
                )

                if is_agent_final:
                    findings = adapter.extract_findings(ns)

                # Check if we have a definitive result (error present OR findings is not None)
                if error or (
                    is_agent_final
                    and findings is not None
                    and isinstance(findings, list)
                ):
                    agents_completed.add(agent_id)

                    await self._save_agent_results_to_db(
                        job_id, adapter, findings, error
                    )

                    await self._send_websocket_message(
                        job_id, "agent_completed", agent_id
                    )

    def _extract_all_findings(self, state: dict[str, Any]) -> dict[str, list[NormalizedFinding]]:
        """Extract findings for all agents from final state."""
        findings_by_agent: dict[str, list[NormalizedFinding]] = {}

        for adapter in ADAPTER_REGISTRY.values():
            ns = self._get_agent_namespace(state, adapter.agent_id)
            findings = adapter.extract_findings(ns)
            if findings and isinstance(findings, list):
                findings_by_agent[adapter.agent_id] = findings
                print(f"   📋 {adapter.agent_id}: {len(findings)} findings", flush=True)
            else:
                findings_by_agent[adapter.agent_id] = []
                print(f"   📋 {adapter.agent_id}: 0 findings", flush=True)

        return findings_by_agent

    async def _save_findings_to_database(
        self, job_id: UUID, findings_by_agent: dict[str, list[NormalizedFinding]]
    ):
        """Save any remaining findings to database (fallback for agents that didn't notify)."""
        from sqlalchemy import select

        total_count = sum(len(findings) for findings in findings_by_agent.values())
        print(
            f"\n💾 Checking findings against database (Total: {total_count})...",
            flush=True,
        )

        saved_count = 0
        for adapter in ADAPTER_REGISTRY.values():
            findings = findings_by_agent.get(adapter.agent_id)

            if findings is None:
                continue

            # Check if ANY result already exists for this agent
            stmt = select(AgentResultModel).where(
                AgentResultModel.job_id == job_id,
                AgentResultModel.agent_id == adapter.agent_id,
            )
            result = await self.db.execute(stmt)
            existing_results = result.scalars().all()

            if existing_results:
                print(
                    f"   ⏭️  Skipping agent '{adapter.agent_id}' (already saved)",
                    flush=True,
                )
                continue

            if not findings:
                result = AgentResultModel(
                    job_id=job_id,
                    agent_id=adapter.agent_id,
                    category=adapter.category,
                    raw_data={},
                    description=None,
                    severity=None,
                )
                self.db.add(result)
                saved_count += 1
            else:
                for nf in findings:
                    result = AgentResultModel(
                        job_id=job_id,
                        agent_id=adapter.agent_id,
                        category=adapter.category,
                        raw_data=nf.model_dump(),
                        description=nf.description,
                        severity=nf.severity,
                        source_refs=nf.source_refs,
                        reasoning=nf.reasoning,
                    )
                    self.db.add(result)
                    saved_count += 1

        if saved_count > 0:
            print(f"   💾 Saved {saved_count} new result rows", flush=True)
        print("✅ All agents verified in database", flush=True)

    async def process_document(self, job_id: UUID, extracted_text: str) -> None:
        """Run orchestrator with validation agents and save findings."""
        print(f"\n{'-' * 80}", flush=True)
        print("📊 PROCESSOR: Starting document processing", flush=True)
        print(f"   Job ID: {job_id}", flush=True)
        print(f"   Text Length: {len(extracted_text)} characters", flush=True)
        print(f"{'-' * 80}\n", flush=True)

        # Update job status to processing
        print("🔄 Updating job status to 'processing'...", flush=True)
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "processing"
        await self.db.commit()
        print("✅ Job status updated to 'processing'", flush=True)

        # Check if dummy agent mode is enabled
        settings = get_settings()
        use_dummy_agents = settings.use_dummy_agents

        try:
            # Initialize the appropriate runner based on mode
            if use_dummy_agents:
                print(f"\n{'🎭' * 40}", flush=True)
                print("⚠️  DUMMY AGENT MODE ENABLED", flush=True)
                print(
                    "   → Using simulated agent responses (NO INFERENCE COSTS)",
                    flush=True,
                )
                print(
                    "   → Set USE_DUMMY_AGENTS=false in .env to use real agents",
                    flush=True,
                )
                print(f"{'🎭' * 40}\n", flush=True)

                print("\n🚀 Initializing dummy agent service...", flush=True)
                runner = DummyAgentService(app=app)
                print("✅ Dummy runner initialized successfully", flush=True)

            else:
                print(f"\n{'🤖' * 40}", flush=True)
                print("✅ REAL AGENT MODE ENABLED", flush=True)
                print(
                    "   → Using actual ADK agents (INFERENCE COSTS APPLY)", flush=True
                )
                print(
                    "   → Set USE_DUMMY_AGENTS=true in .env to use dummy agents",
                    flush=True,
                )
                print(f"{'🤖' * 40}\n", flush=True)

                print("\n🚀 Initializing ADK runner with app...", flush=True)
                runner = InMemoryRunner(app=app)
                print("✅ Runner initialized successfully", flush=True)

            # Unified runner interface for both dummy and real agents
            print(f"📦 Creating session for job {job_id}...", flush=True)
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id=str(job_id)
            )
            print(f"✅ Session created: {session.id}", flush=True)

            # Run agent pipeline with event streaming
            content = UserContent(parts=[Part(text=extracted_text)])
            final_state = {}
            agents_started = set()
            agents_completed = set()

            print(f"\n{'=' * 80}", flush=True)
            print("🎬 STARTING AGENT PIPELINE EXECUTION", flush=True)
            print(f"{'=' * 80}\n", flush=True)

            event_count = 0
            adapter_agent_ids = set(ADAPTER_REGISTRY.keys())

            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                event_count += 1

                # Mark all agents as started on the very first event
                if event_count == 1:
                    print("🚀 Starting all agents...", flush=True)
                    for agent_id in adapter_agent_ids:
                        agents_started.add(agent_id)
                        await self._send_websocket_message(
                            job_id, "agent_started", agent_id
                        )

                print(
                    f"\n📡 Event #{event_count} received: {type(event).__name__} (author={getattr(event, 'author', 'unknown')}, branch={getattr(event, 'branch', 'none')}, is_final={getattr(event, 'is_final_response', lambda: False)()})",
                    flush=True,
                )

                # Accumulate state from event deltas
                if (
                    hasattr(event, "actions")
                    and event.actions
                    and event.actions.state_delta
                ):
                    final_state.update(event.actions.state_delta)

                # Check for completion vs continuous error monitoring
                is_final = (
                    hasattr(event, "is_final_response") and event.is_final_response()
                )
                specific_agent = None

                if is_final and hasattr(event, "branch") and event.branch:
                    branch_parts = event.branch.split(".")
                    for part in reversed(branch_parts):
                        if part in adapter_agent_ids:
                            specific_agent = part
                            break

                await self._check_and_notify_agents(
                    job_id,
                    final_state,
                    agents_started,
                    agents_completed,
                    specific_agent=specific_agent,
                    is_final=is_final,
                )

            print(f"\n{'=' * 80}", flush=True)
            print("📊 AGENT PIPELINE COMPLETED", flush=True)
            print(f"   Total events processed: {event_count}", flush=True)
            print(f"   Agents started: {agents_started}", flush=True)
            print(f"   Agents completed: {agents_completed}", flush=True)
            print(f"{'=' * 80}\n", flush=True)

            # Fetch final session state
            print("📦 Fetching final session state from runner...", flush=True)
            final_session = await runner.session_service.get_session(
                app_name=runner.app_name, user_id=str(job_id), session_id=session.id
            )
            final_state = final_session.state
            print(
                f"✅ Session state retrieved. Keys: {list(final_state.keys())}",
                flush=True,
            )

            # Check if validation rejected the document
            validator_output = final_state.get("document_validator_output")
            if validator_output and not validator_output.get(
                "is_valid_financial_document", True
            ):
                print("❌ Document rejected by DocumentValidator agent", flush=True)
                job.status = "failed"
                job.error_message = "Document is not a valid financial statement."
                await self.db.commit()
                await manager.send_to_audit(
                    str(job_id),
                    {
                        "type": "validation_failed",
                        "error": job.error_message,
                    },
                )
                return  # Skip findings extraction

            # Extract and save findings
            print("\n📦 Extracting findings from session state...", flush=True)
            findings_by_agent = self._extract_all_findings(final_state)
            await self._save_findings_to_database(job_id, findings_by_agent)

            # Update job status to completed
            print("\n🔄 Updating job status to 'completed'...", flush=True)
            job.status = "completed"
            await self.db.commit()
            print("✅ Job status updated to 'completed'", flush=True)

            # Send audit complete message
            print("📤 Sending 'audit_complete' WebSocket message...", flush=True)
            await manager.send_to_audit(
                str(job_id),
                {
                    "type": "audit_complete",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            print("✅ Audit complete message sent", flush=True)

        except Exception as e:
            print(f"\n{'=' * 80}", flush=True)
            print("❌ PROCESSOR ERROR", flush=True)
            print(f"   Job ID: {job_id}", flush=True)
            print(f"   Error Type: {type(e).__name__}", flush=True)
            print(f"   Error Message: {e!s}", flush=True)
            import traceback

            print(f"   Traceback:\n{traceback.format_exc()}", flush=True)
            print(f"{'=' * 80}\n", flush=True)

            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()

            raise
