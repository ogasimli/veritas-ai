"""Document processing service with agent pipeline integration."""

from collections.abc import Callable
from dataclasses import dataclass
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
from app.services.dummy_agent.dummy_agent_service import DummyAgentService
from app.services.websocket_manager import manager


@dataclass
class AgentConfig:
    """Configuration for agent detection and findings extraction."""

    agent_id: str
    completion_check: Callable[
        [dict[str, Any]], list[dict] | None
    ]  # Function to extract findings
    error_check: Callable[[dict[str, Any]], dict | None]  # Function to check for errors
    category: str  # Database category
    db_transformer: Callable[[dict], dict]  # Transform finding data for DB


class DocumentProcessor:
    """Processes documents through validation agent pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_configs = self._initialize_agent_configs()

    def _initialize_agent_configs(self) -> list[AgentConfig]:
        """Define configuration for all agents."""
        return [
            AgentConfig(
                agent_id="numeric_validation",
                completion_check=lambda state: self._get_nested_findings(
                    state, "numeric_validation", "reviewer_output"
                ),
                error_check=lambda state: self._check_standard_error(
                    self._get_agent_namespace(state, "numeric_validation"),
                    ["extractor_output", "reviewer_output"],
                ),
                category="numeric",
                db_transformer=lambda f: {
                    "description": f.get("summary", ""),
                    "severity": f.get("severity", "medium"),
                    "source_refs": f.get("source_refs", []),
                    "reasoning": f"Expected: {f.get('expected_value')}, "
                    f"Actual: {f.get('actual_value')}, "
                    f"Discrepancy: {f.get('discrepancy')}",
                },
            ),
            AgentConfig(
                agent_id="logic_consistency",
                completion_check=lambda state: self._get_nested_findings(
                    state, "logic_consistency", "reviewer_output"
                ),
                error_check=lambda state: self._check_standard_error(
                    self._get_agent_namespace(state, "logic_consistency"),
                    ["detector_output", "reviewer_output"],
                ),
                category="logic",
                db_transformer=lambda f: {
                    "description": f.get("contradiction", ""),
                    "severity": f.get("severity", "medium"),
                    "source_refs": f.get("source_refs", []),
                    "reasoning": f"Claim: {f.get('claim', '')}\n\nReasoning: {f.get('reasoning', '')}",
                },
            ),
            AgentConfig(
                agent_id="disclosure_compliance",
                completion_check=lambda state: self._get_nested_findings(
                    state, "disclosure_compliance", "reviewer_output"
                ),
                error_check=lambda state: self._check_standard_error(
                    self._get_agent_namespace(state, "disclosure_compliance"),
                    ["scanner_output", "reviewer_output"],
                ),
                category="disclosure",
                db_transformer=lambda f: {
                    "description": f"{f.get('reference', '')}: {f.get('requirement', '')}",
                    "severity": f.get("severity", "medium"),
                    "source_refs": [],
                    "reasoning": f"Standard: {f.get('standard')}\n"
                    f"ID: {f.get('disclosure_id')}\n"
                    f"requirement: {f.get('reference', '')}: {f.get('requirement', '')}",
                },
            ),
            AgentConfig(
                agent_id="external_signal",
                completion_check=lambda state: self._get_nested_findings(
                    state, "external_signal", "external_signal_findings"
                ),
                error_check=lambda state: self._check_standard_error(
                    self._get_agent_namespace(state, "external_signal"),
                    [
                        "internet_to_report_findings",
                        "report_to_internet_findings",
                        "external_signal_findings",
                    ],
                ),
                category="external",
                db_transformer=lambda f: self._transform_unified_external_finding(f),
            ),
        ]

    def _get_agent_namespace(
        self, state: dict[str, Any], agent_id: str
    ) -> dict[str, Any]:
        """Get the state namespace for an agent, or return the state itself if not namespaced."""
        if agent_id in state and isinstance(state[agent_id], dict):
            return state[agent_id]
        return state

    def _get_nested_findings(
        self, state: dict[str, Any], agent_id: str, output_key: str
    ) -> list[dict] | None:
        """Extract findings from a potentially namespaced state."""
        ns = self._get_agent_namespace(state, agent_id)
        output = ns.get(output_key)
        if isinstance(output, dict):
            return output.get("findings")
        return None

    def _check_standard_error(
        self, state: dict[str, Any], keys: list[str]
    ) -> dict | None:
        """Check for AgentError in standard output keys."""
        for key in keys:
            data = state.get(key)
            if isinstance(data, dict):
                # Check for direct error field (from AgentError schema)
                if data.get("error") and isinstance(data["error"], dict):
                    return data["error"]
                # Check directly if the output itself is an error (fallback)
                if data.get("is_error"):
                    return data
        return None

    def _aggregate_disclosure_findings(
        self, state: dict[str, Any]
    ) -> list[dict] | None:
        """Aggregate disclosure findings from all standards."""
        disclosure_keys = [
            k for k in state.keys() if k.startswith("disclosure_findings:")
        ]
        if not disclosure_keys:
            return None

        findings = []
        for key in disclosure_keys:
            disclosure_data = state.get(key, {})
            if isinstance(disclosure_data, dict):
                findings_list = disclosure_data.get("findings", [])
                if isinstance(findings_list, list):
                    findings.extend(findings_list)
        return findings if findings else None

    def _transform_unified_external_finding(self, finding: dict) -> dict:
        """Transform unified external finding for database storage."""
        return {
            "description": finding.get("summary", ""),
            "severity": finding.get("severity", "medium"),
            "source_refs": finding.get("source_urls", []),
            "reasoning": (
                f"Type: {finding.get('finding_type', '')}\n"
                f"Category: {finding.get('category', '')}\n\n"
                f"{finding.get('details', '')}"
            ),
        }

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
        config: AgentConfig,
        findings: list[dict] | None,
        error: dict | None,
    ):
        """Save results (findings or error) to database immediately."""
        if error:
            # Save error result
            result = AgentResultModel(
                job_id=job_id,
                agent_id=config.agent_id,
                category=config.category,
                error=error.get("error_message", str(error)),
                raw_data=error,
            )
            self.db.add(result)
            print(
                f"      💾 Saved ERROR to DB for agent '{config.agent_id}'", flush=True
            )

        elif findings:
            # Save each finding result
            for finding_data in findings:
                transformed = config.db_transformer(finding_data)
                result = AgentResultModel(
                    job_id=job_id,
                    agent_id=config.agent_id,
                    category=config.category,
                    raw_data=finding_data,
                    **transformed,
                )
                self.db.add(result)
            print(
                f"      💾 Saved {len(findings)} findings to DB for agent '{config.agent_id}'",
                flush=True,
            )

        elif findings is not None:
            # findings is empty list -> Save empty success result
            result = AgentResultModel(
                job_id=job_id,
                agent_id=config.agent_id,
                category=config.category,
                raw_data={},
                description=None,
                severity=None,
            )
            self.db.add(result)
            print(
                f"      💾 Saved EMPTY result to DB for agent '{config.agent_id}'",
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
        """Check agent states and send WebSocket notifications.

        Args:
            job_id: The job ID
            state: Current accumulated state
            agents_started: Set of agent IDs that have started
            agents_completed: Set of agent IDs that have completed
            specific_agent: If provided, only check this specific agent for findings.
            is_final: Whether this is a final event for specific_agent
        """
        # We always check for errors for all agents that have started but not completed
        for config in self.agent_configs:
            agent_id = config.agent_id
            if agent_id in agents_started and agent_id not in agents_completed:
                # Check for errors on every event
                error = config.error_check(state)

                # Check for findings only if this is the final event for this specific agent
                findings = None
                is_agent_final = is_final and (
                    specific_agent is None or specific_agent == agent_id
                )

                if is_agent_final:
                    findings = config.completion_check(state)

                # Check if we have a definitive result (error present OR findings is not None)
                if error or (
                    is_agent_final
                    and findings is not None
                    and isinstance(findings, list)
                ):
                    agents_completed.add(agent_id)

                    # Unified save call - logic handled inside
                    await self._save_agent_results_to_db(
                        job_id, config, findings, error
                    )

                    # Unified notification
                    await self._send_websocket_message(
                        job_id, "agent_completed", agent_id
                    )

    def _extract_all_findings(self, state: dict[str, Any]) -> dict[str, list[dict]]:
        """Extract findings for all agents from final state."""
        findings_by_agent = {}

        for config in self.agent_configs:
            findings = config.completion_check(state)
            if findings and isinstance(findings, list):
                findings_by_agent[config.agent_id] = findings
                print(f"   📋 {config.agent_id}: {len(findings)} findings", flush=True)
            else:
                findings_by_agent[config.agent_id] = []
                print(f"   📋 {config.agent_id}: 0 findings", flush=True)

        return findings_by_agent

    async def _save_findings_to_database(
        self, job_id: UUID, findings_by_agent: dict[str, list[dict]]
    ):
        """Save any remaining findings to database (fallback for agents that didn't notify)."""
        from sqlalchemy import select

        total_count = sum(len(findings) for findings in findings_by_agent.values())
        print(
            f"\n💾 Checking findings against database (Total: {total_count})...",
            flush=True,
        )

        saved_count = 0
        for config in self.agent_configs:
            findings = findings_by_agent.get(config.agent_id)

            # If findings is None, skip (maybe agent didn't run or produce valid output)
            if findings is None:
                continue

            # Check if ANY result (findings or error/empty) already exists for this agent
            stmt = select(AgentResultModel).where(
                AgentResultModel.job_id == job_id,
                AgentResultModel.agent_id == config.agent_id,
            )
            result = await self.db.execute(stmt)
            existing_results = result.scalars().all()

            if existing_results:
                print(
                    f"   ⏭️  Skipping agent '{config.agent_id}' (already saved)",
                    flush=True,
                )
                continue

            # Save findings (or empty result) if not already present
            if not findings:
                # Save empty result
                result = AgentResultModel(
                    job_id=job_id,
                    agent_id=config.agent_id,
                    category=config.category,
                    raw_data={},
                    description=None,
                    severity=None,
                )
                self.db.add(result)
                saved_count += 1
            else:
                for finding_data in findings:
                    transformed = config.db_transformer(finding_data)
                    result = AgentResultModel(
                        job_id=job_id,
                        agent_id=config.agent_id,
                        category=config.category,
                        raw_data=finding_data,
                        **transformed,
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

                # Use dummy agent service (mimics InMemoryRunner interface)
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

                # Real agent mode: Initialize ADK runner
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
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                event_count += 1

                # Mark all agents as started on the very first event to ensure frontend is ready
                if event_count == 1:
                    print("🚀 Starting all agents...", flush=True)
                    for config in self.agent_configs:
                        agents_started.add(config.agent_id)
                        await self._send_websocket_message(
                            job_id, "agent_started", config.agent_id
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
                    # Identify which agent this branch belongs to
                    branch_parts = event.branch.split(".")
                    config_agent_ids = {c.agent_id for c in self.agent_configs}
                    for part in reversed(branch_parts):
                        if part in config_agent_ids:
                            specific_agent = part
                            break

                # Call check_and_notify on EVERY event for error detection
                # findings will only be checked if is_final=True and specific_agent matches
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

            # Note: We rely on job status update for pipeline errors
            # agent_error message is deprecated

            raise
