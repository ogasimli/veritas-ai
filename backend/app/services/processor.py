"""Document processing service with agent pipeline integration."""
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent

from veritas_ai_agent.agent import root_agent
from app.models.finding import Finding as FindingModel
from app.models.job import Job
from app.services.websocket_manager import manager
 
 
class DocumentProcessor:
    """Processes documents through validation agent pipelines."""
 
    def __init__(self, db: AsyncSession):
        self.db = db
 
    async def process_document(self, job_id: UUID, extracted_text: str) -> None:
        """Run orchestrator with validation agents and save findings."""
        # 1. Update job status
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
 
        job.status = "processing"
        await self.db.commit()
 
        try:
            # 2. Run orchestrator pipeline
            # Runs agents in parallel:
            # - numeric_validation
            # - logic_consistency
            # - disclosure_compliance
            # - external_signal (bidirectional verification with Deep Research)
            runner = InMemoryRunner(agent=root_agent, app_name="veritas-ai")
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=str(job_id)
            )

            content = UserContent(parts=[Part(text=extracted_text)])

            # Collect final response
            final_state = {}
            # Track which agents have started (to avoid duplicate start messages)
            agents_started = set()
            # Track which agents have completed (to send completion messages with findings)
            agents_completed = set()

            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                # Capture session state updates
                if hasattr(event, 'session') and event.session:
                    final_state = event.session.state

                    # Stream WebSocket events for each agent
                    # Check for agent state updates in session state
                    for agent_id in ["numeric_validation", "logic_consistency", "disclosure_compliance", "external_signal"]:
                        agent_state = final_state.get(agent_id, {})

                        # Send agent_started message when agent state first appears
                        if agent_state and agent_id not in agents_started:
                            agents_started.add(agent_id)
                            await manager.send_to_audit(str(job_id), {
                                "type": "agent_started",
                                "agent_id": agent_id,
                                "timestamp": datetime.utcnow().isoformat()
                            })

                        # Send agent_completed message when agent output appears
                        # Each agent has different output structure, check for completion markers
                        is_completed = False
                        findings = []

                        if agent_id == "numeric_validation":
                            reviewer_output = agent_state.get("reviewer_output", {})
                            if reviewer_output and "findings" in reviewer_output:
                                is_completed = True
                                findings = reviewer_output.get("findings", [])

                        elif agent_id == "logic_consistency":
                            logic_output = agent_state.get("reviewer_output", {})
                            if logic_output and "findings" in logic_output:
                                is_completed = True
                                findings = logic_output.get("findings", [])

                        elif agent_id == "disclosure_compliance":
                            disclosure_output = agent_state.get("reviewer_output", {})
                            if disclosure_output and "findings" in disclosure_output:
                                is_completed = True
                                findings = disclosure_output.get("findings", [])

                        elif agent_id == "external_signal":
                            # External signal has two outputs: internet_to_report and report_to_internet
                            internet_to_report = agent_state.get("internet_to_report_findings", {})
                            report_to_internet = agent_state.get("report_to_internet_findings", {})
                            if internet_to_report or report_to_internet:
                                is_completed = True
                                # Combine both finding types for WebSocket
                                findings = []
                                if internet_to_report:
                                    findings.extend(internet_to_report.get("findings", []))
                                if report_to_internet:
                                    findings.extend(report_to_internet.get("verifications", []))

                        # Send completion message if agent completed and not already sent
                        if is_completed and agent_id not in agents_completed:
                            agents_completed.add(agent_id)
                            await manager.send_to_audit(str(job_id), {
                                "type": "agent_completed",
                                "agent_id": agent_id,
                                "findings": findings,
                                "timestamp": datetime.utcnow().isoformat()
                            })

            # 3. Extract findings from orchestrator output
            # Orchestrator runs sub-agents in parallel and aggregates their session states

            # 3a. Extract numeric validation findings
            numeric_validation_state = final_state.get("numeric_validation", {})
            reviewer_output = numeric_validation_state.get("reviewer_output", {})
            numeric_findings = reviewer_output.get("findings", [])

            # 3b. Extract logic consistency findings
            logic_state = final_state.get("logic_consistency", {})
            logic_output = logic_state.get("reviewer_output", {})  # Changed from logic_consistency_output
            logic_findings = logic_output.get("findings", [])

            # 3c. Extract disclosure compliance findings (Consolidated by Reviewer)
            disclosure_state = final_state.get("disclosure_compliance", {})
            disclosure_output = disclosure_state.get("reviewer_output", {})
            disclosure_findings = disclosure_output.get("findings", [])

            # 3d. Extract external signal findings (Phase 6.1: bidirectional verification)
            external_state = final_state.get("external_signal", {})

            # 3d.1. Internet→Report findings (signals contradicting report)
            internet_to_report_output = external_state.get("internet_to_report_findings", {})
            internet_to_report_findings = internet_to_report_output.get("findings", [])

            # 3d.2. Report→Internet findings (report claims that are contradicted)
            report_to_internet_output = external_state.get("report_to_internet_findings", {})
            report_to_internet_verifications = report_to_internet_output.get("verifications", [])

            # 4. Save findings to database
            # 4a. Save numeric validation findings
            for finding_data in numeric_findings:
                finding = FindingModel(
                    job_id=job_id,
                    category="numeric",
                    severity=finding_data.get("severity", "medium"),
                    description=finding_data.get("summary", ""),
                    source_refs=finding_data.get("source_refs", []),
                    reasoning=f"Expected: {finding_data.get('expected_value')}, "
                             f"Actual: {finding_data.get('actual_value')}, "
                             f"Discrepancy: {finding_data.get('discrepancy')}",
                    agent_id="numeric_validation",
                )
                self.db.add(finding)

            for finding_data in logic_findings:
                finding = FindingModel(
                    job_id=job_id,
                    category="logic",
                    severity=finding_data.get("severity", "medium"),
                    description=finding_data.get("contradiction", ""),
                    source_refs=finding_data.get("source_refs", []),
                    reasoning=f"Claim: {finding_data.get('claim', '')}\n\n"
                              f"Reasoning: {finding_data.get('reasoning', '')}",
                    agent_id="logic_consistency",
                )
                self.db.add(finding)

            # 4c. Save disclosure compliance findings
            for finding_data in disclosure_findings:
                finding = FindingModel(
                    job_id=job_id,
                    category="disclosure",
                    severity=finding_data.get("severity", "medium"),
                    description=finding_data.get("requirement", ""),
                    source_refs=[],  # Disclosure findings don't have specific source refs
                    reasoning=f"Standard: {finding_data.get('standard')}\n"
                              f"ID: {finding_data.get('disclosure_id')}\n\n"
                              f"Requirement Detail: {finding_data.get('description', '')}",
                    agent_id="disclosure_compliance",
                )
                self.db.add(finding)

            # 4d. Save external signal findings (Phase 6.1: bidirectional)
            # 4d.1. Save Internet→Report findings (signals contradicting report)
            for finding_data in internet_to_report_findings:
                finding = FindingModel(
                    job_id=job_id,
                    category="external",
                    severity="medium",
                    description=finding_data.get("summary", ""),
                    source_refs=[finding_data.get("source_url", "")],
                    reasoning=f"Signal type: {finding_data.get('signal_type')}, "
                             f"Publication: {finding_data.get('publication_date', 'unknown')}, "
                             f"Potential contradiction: {finding_data.get('potential_contradiction', 'none')}",
                    agent_id="external_signal:internet_to_report",
                )
                self.db.add(finding)

            # 4d.2. Save Report→Internet findings (report claims that are contradicted)
            for verification_data in report_to_internet_verifications:
                # Only save findings for claims that are CONTRADICTED
                if verification_data.get("status") == "CONTRADICTED":
                    source_urls = verification_data.get("source_urls", [])
                    finding = FindingModel(
                        job_id=job_id,
                        category="external",
                        severity="high",  # Contradicted claims are high severity
                        description=f"Report claim contradicted: {verification_data.get('claim', '')}",
                        source_refs=source_urls,
                        reasoning=f"Evidence: {verification_data.get('evidence_summary', '')}, "
                                 f"Discrepancy: {verification_data.get('discrepancy', 'none')}",
                        agent_id="external_signal:report_to_internet",
                    )
                    self.db.add(finding)

            # 5. Update job status
            job.status = "completed"
            await self.db.commit()

            # 6. Send audit complete message
            await manager.send_to_audit(str(job_id), {
                "type": "audit_complete",
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()

            # Send error message to WebSocket
            await manager.send_to_audit(str(job_id), {
                "type": "agent_error",
                "agent_id": "audit_pipeline",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            raise
