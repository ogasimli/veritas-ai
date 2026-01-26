"""Document processing service with agent pipeline integration."""
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent

from veritas_ai_agent.agent import root_agent
from app.models.finding import Finding as FindingModel
from app.models.job import Job
from app.services.websocket_manager import manager


@dataclass
class AgentConfig:
    """Configuration for agent detection and findings extraction."""
    agent_id: str
    start_keys: List[str]  # Keys that indicate agent has started
    completion_check: Callable[[Dict[str, Any]], Optional[List[Dict]]]  # Function to extract findings
    error_check: Callable[[Dict[str, Any]], Optional[Dict]] # Function to check for errors
    category: str  # Database category
    db_transformer: Callable[[Dict], Dict]  # Transform finding data for DB


class DocumentProcessor:
    """Processes documents through validation agent pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_configs = self._initialize_agent_configs()

    def _initialize_agent_configs(self) -> List[AgentConfig]:
        """Define configuration for all agents."""
        return [
            AgentConfig(
                agent_id="numeric_validation",
                start_keys=["reviewer_output"],
                completion_check=lambda state: state.get("reviewer_output", {}).get("findings")
                    if isinstance(state.get("reviewer_output"), dict) else None,
                error_check=lambda state: self._check_standard_error(state, ["extractor_output", "reviewer_output"]),
                category="numeric",
                db_transformer=lambda f: {
                    "description": f.get("summary", ""),
                    "severity": f.get("severity", "medium"),
                    "source_refs": f.get("source_refs", []),
                    "reasoning": f"Expected: {f.get('expected_value')}, "
                                f"Actual: {f.get('actual_value')}, "
                                f"Discrepancy: {f.get('discrepancy')}"
                }
            ),
            AgentConfig(
                agent_id="logic_consistency",
                start_keys=["detector_output"],
                completion_check=lambda state: state.get("detector_output", {}).get("findings")
                    if isinstance(state.get("detector_output"), dict) else None,
                error_check=lambda state: self._check_standard_error(state, ["detector_output", "reviewer_output"]),
                category="logic",
                db_transformer=lambda f: {
                    "description": f.get("contradiction", ""),
                    "severity": f.get("severity", "medium"),
                    "source_refs": f.get("source_refs", []),
                    "reasoning": f"Claim: {f.get('claim', '')}\n\nReasoning: {f.get('reasoning', '')}"
                }
            ),
            AgentConfig(
                agent_id="disclosure_compliance",
                start_keys=["scanner_output"],
                completion_check=lambda state: self._aggregate_disclosure_findings(state),
                error_check=lambda state: self._check_standard_error(state, ["scanner_output", "reviewer_output"]),
                category="disclosure",
                db_transformer=lambda f: {
                    "description": f.get("requirement", ""),
                    "severity": f.get("severity", "medium"),
                    "source_refs": [],
                    "reasoning": f"Standard: {f.get('standard')}\n"
                                f"ID: {f.get('disclosure_id')}\n\n"
                                f"Requirement Detail: {f.get('description', '')}"
                }
            ),
            AgentConfig(
                agent_id="external_signal",
                start_keys=["internet_to_report_findings", "report_to_internet_findings"],
                completion_check=lambda state: self._aggregate_external_findings(state),
                error_check=lambda state: self._check_standard_error(state, ["internet_to_report_findings", "report_to_internet_findings"]),
                category="external",
                db_transformer=lambda f: self._transform_external_finding(f)
            ),
        ]

    def _check_standard_error(self, state: Dict[str, Any], keys: List[str]) -> Optional[Dict]:
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

    def _aggregate_disclosure_findings(self, state: Dict[str, Any]) -> Optional[List[Dict]]:
        """Aggregate disclosure findings from all standards."""
        disclosure_keys = [k for k in state.keys() if k.startswith("disclosure_findings:")]
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

    def _aggregate_external_findings(self, state: Dict[str, Any]) -> Optional[List[Dict]]:
        """Aggregate external findings from both directions."""
        i2r = state.get("internet_to_report_findings", {})
        r2i = state.get("report_to_internet_findings", {})

        if not (isinstance(i2r, dict) and isinstance(r2i, dict) and i2r and r2i):
            return None

        findings = []
        i2r_findings = i2r.get("findings", [])
        r2i_findings = r2i.get("verifications", [])

        if isinstance(i2r_findings, list):
            findings.extend(i2r_findings)
        if isinstance(r2i_findings, list):
            findings.extend(r2i_findings)

        return findings if findings else None

    def _transform_external_finding(self, finding: Dict) -> Dict:
        """Transform external finding based on its type."""
        if finding.get("status"):  # Report→Internet verification
            return {
                "description": f"Report claim contradicted: {finding.get('claim', '')}",
                "severity": "high" if finding.get("status") == "CONTRADICTED" else "medium",
                "source_refs": finding.get("source_urls", []),
                "reasoning": f"Evidence: {finding.get('evidence_summary', '')}, "
                           f"Discrepancy: {finding.get('discrepancy', 'none')}"
            }
        else:  # Internet→Report signal
            return {
                "description": finding.get("summary", ""),
                "severity": "medium",
                "source_refs": [finding.get("source_url", "")],
                "reasoning": f"Signal type: {finding.get('signal_type')}, "
                           f"Publication: {finding.get('publication_date', 'unknown')}, "
                           f"Potential contradiction: {finding.get('potential_contradiction', 'none')}"
            }

    async def _send_websocket_message(self, job_id: UUID, message_type: str, agent_id: str, payload: Optional[Any] = None):
        """Send WebSocket message for agent state change."""
        message = {
            "type": message_type,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        if payload is not None:
             if message_type == "agent_error":
                 message["error"] = payload
             else:
                message["findings"] = payload

        log_prefix = "🎯" if message_type == "agent_started" else ("❌" if message_type == "agent_error" else "✅")
        status_msg = "STARTED"
        if message_type == "agent_completed":
            status_msg = f"COMPLETED with {len(payload) if isinstance(payload, list) else 0} findings"
        elif message_type == "agent_error":
            status_msg = f"FAILED: {payload.get('error_message')}"
            
        print(f"   {log_prefix} Agent '{agent_id}' {status_msg}", flush=True)
        print(f"      📤 Sending WebSocket message", flush=True)

        await manager.send_to_audit(str(job_id), message)

    async def _check_and_notify_agents(self, job_id: UUID, state: Dict[str, Any], agents_started: set, agents_completed: set):
        """Check agent states and send WebSocket notifications."""
        for config in self.agent_configs:
            agent_id = config.agent_id

            # Check if agent has started (any start key exists)
            if agent_id not in agents_started:
                for key in config.start_keys:
                    value = state.get(key)
                    if isinstance(value, dict) and value:
                        agents_started.add(agent_id)
                        await self._send_websocket_message(job_id, "agent_started", agent_id)
                        break

            # Check if agent has completed (completion check returns findings OR error)
            if agent_id not in agents_completed:
                # 1. Check for errors first
                error = config.error_check(state)
                if error:
                    agents_completed.add(agent_id)
                    await self._send_websocket_message(job_id, "agent_error", agent_id, error)
                    continue

                # 2. Check for successful completion
                findings = config.completion_check(state)
                if findings and isinstance(findings, list):
                    agents_completed.add(agent_id)
                    await self._send_websocket_message(job_id, "agent_completed", agent_id, findings)

    def _extract_all_findings(self, state: Dict[str, Any]) -> Dict[str, List[Dict]]:
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

    async def _save_findings_to_database(self, job_id: UUID, findings_by_agent: Dict[str, List[Dict]]):
        """Save all findings to database."""
        total_count = sum(len(findings) for findings in findings_by_agent.values())
        print(f"\n💾 Saving {total_count} findings to database...", flush=True)

        for config in self.agent_configs:
            findings = findings_by_agent.get(config.agent_id, [])
            for finding_data in findings:
                transformed = config.db_transformer(finding_data)
                finding = FindingModel(
                    job_id=job_id,
                    category=config.category,
                    severity=transformed["severity"],
                    description=transformed["description"],
                    source_refs=transformed["source_refs"],
                    reasoning=transformed["reasoning"],
                    agent_id=config.agent_id,
                )
                self.db.add(finding)

        print(f"✅ All findings saved successfully", flush=True)

    async def process_document(self, job_id: UUID, extracted_text: str) -> None:
        """Run orchestrator with validation agents and save findings."""
        print(f"\n{'-'*80}", flush=True)
        print(f"📊 PROCESSOR: Starting document processing", flush=True)
        print(f"   Job ID: {job_id}", flush=True)
        print(f"   Text Length: {len(extracted_text)} characters", flush=True)
        print(f"{'-'*80}\n", flush=True)

        # Update job status to processing
        print("🔄 Updating job status to 'processing'...", flush=True)
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "processing"
        await self.db.commit()
        print("✅ Job status updated to 'processing'", flush=True)

        try:
            # Initialize ADK runner and session
            print(f"\n🚀 Initializing ADK runner with root_agent...", flush=True)
            runner = InMemoryRunner(agent=root_agent, app_name="veritas-ai")
            print("✅ Runner initialized successfully", flush=True)

            print(f"📦 Creating session for job {job_id}...", flush=True)
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=str(job_id)
            )
            print(f"✅ Session created: {session.id}", flush=True)

            # Run agent pipeline with event streaming
            content = UserContent(parts=[Part(text=extracted_text)])
            final_state = {}
            agents_started = set()
            agents_completed = set()

            print(f"\n{'='*80}", flush=True)
            print(f"🎬 STARTING AGENT PIPELINE EXECUTION", flush=True)
            print(f"{'='*80}\n", flush=True)

            event_count = 0
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                event_count += 1
                print(f"\n📡 Event #{event_count} received: {type(event).__name__}", flush=True)

                # Accumulate state from event deltas
                if hasattr(event, 'actions') and event.actions and event.actions.state_delta:
                    print(f"   📝 State delta received. Keys: {list(event.actions.state_delta.keys())}", flush=True)
                    final_state.update(event.actions.state_delta)
                    print(f"   📋 Accumulated state keys: {list(final_state.keys())}", flush=True)

                # Only process WebSocket updates on final responses
                if not (hasattr(event, 'is_final_response') and event.is_final_response()):
                    continue

                print(f"   ✅ Final response - checking for agent completions", flush=True)
                await self._check_and_notify_agents(job_id, final_state, agents_started, agents_completed)

            print(f"\n{'='*80}", flush=True)
            print(f"📊 AGENT PIPELINE COMPLETED", flush=True)
            print(f"   Total events processed: {event_count}", flush=True)
            print(f"   Agents started: {agents_started}", flush=True)
            print(f"   Agents completed: {agents_completed}", flush=True)
            print(f"{'='*80}\n", flush=True)

            # Fetch final session state
            print("📦 Fetching final session state from runner...", flush=True)
            final_session = await runner.session_service.get_session(
                app_name=runner.app_name,
                user_id=str(job_id),
                session_id=session.id
            )
            final_state = final_session.state
            print(f"✅ Session state retrieved. Keys: {list(final_state.keys())}", flush=True)

            # Extract and save findings
            print("\n📦 Extracting findings from session state...", flush=True)
            findings_by_agent = self._extract_all_findings(final_state)
            await self._save_findings_to_database(job_id, findings_by_agent)

            # Update job status to completed
            print(f"\n🔄 Updating job status to 'completed'...", flush=True)
            job.status = "completed"
            await self.db.commit()
            print("✅ Job status updated to 'completed'", flush=True)

            # Send audit complete message
            print(f"📤 Sending 'audit_complete' WebSocket message...", flush=True)
            await manager.send_to_audit(str(job_id), {
                "type": "audit_complete",
                "timestamp": datetime.utcnow().isoformat()
            })
            print("✅ Audit complete message sent", flush=True)

        except Exception as e:
            print(f"\n{'='*80}", flush=True)
            print(f"❌ PROCESSOR ERROR", flush=True)
            print(f"   Job ID: {job_id}", flush=True)
            print(f"   Error Type: {type(e).__name__}", flush=True)
            print(f"   Error Message: {str(e)}", flush=True)
            import traceback
            print(f"   Traceback:\n{traceback.format_exc()}", flush=True)
            print(f"{'='*80}\n", flush=True)

            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()

            await manager.send_to_audit(str(job_id), {
                "type": "agent_error",
                "agent_id": "audit_pipeline",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            raise
