"""Document processing service with agent pipeline integration."""
import sys
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
        print(f"\n{'-'*80}", flush=True)
        print(f"📊 PROCESSOR: Starting document processing", flush=True)
        print(f"   Job ID: {job_id}", flush=True)
        print(f"   Text Length: {len(extracted_text)} characters", flush=True)
        print(f"{'-'*80}\n", flush=True)
        
        # 1. Update job status
        print("🔄 Updating job status to 'processing'...", flush=True)
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
 
        job.status = "processing"
        await self.db.commit()
        print("✅ Job status updated to 'processing'", flush=True)
 
        try:
            # 2. Run orchestrator pipeline
            print(f"\n🚀 Initializing ADK runner with root_agent...", flush=True)
            try:
                # Runs agents in parallel:
                # - numeric_validation
                # - logic_consistency
                # - disclosure_compliance
                # - external_signal (bidirectional verification with Deep Research)
                runner = InMemoryRunner(agent=root_agent, app_name="veritas-ai")
                print("✅ Runner initialized successfully", flush=True)
            except Exception as e:
                print(f"❌ ERROR: Failed to initialize InMemoryRunner", flush=True)
                print(f"   Error type: {type(e).__name__}", flush=True)
                print(f"   Error message: {str(e)}", flush=True)
                raise
            
            print(f"📦 Creating session for job {job_id}...", flush=True)
            try:
                session = await runner.session_service.create_session(
                    app_name=runner.app_name,
                    user_id=str(job_id)
                )
                print(f"✅ Session created: {session.id}", flush=True)
            except Exception as e:
                print(f"❌ ERROR: Failed to create session", flush=True)
                print(f"   Error type: {type(e).__name__}", flush=True)
                print(f"   Error message: {str(e)}", flush=True)
                raise

            content = UserContent(parts=[Part(text=extracted_text)])

            # Collect final response
            final_state = {}
            # Track which agents have started (to avoid duplicate start messages)
            agents_started = set()
            # Track which agents have completed (to send completion messages with findings)
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

                # ADK Best Practice: Validate event.actions before accessing (from docs)
                # "Always check if event.actions and its fields/methods exist before accessing"
                if hasattr(event, 'actions') and event.actions and event.actions.state_delta:
                    print(f"   📝 State delta received. Keys: {list(event.actions.state_delta.keys())}", flush=True)
                    # Merge state delta into accumulated state
                    final_state.update(event.actions.state_delta)
                    print(f"   📋 Accumulated state keys: {list(final_state.keys())}", flush=True)

                # ADK Best Practice: Only process WebSocket updates on final responses
                # This prevents sending intermediate updates during agent processing
                if not (hasattr(event, 'is_final_response') and event.is_final_response()):
                    # Skip WebSocket updates for intermediate events
                    continue

                # Stream WebSocket events for each agent only on final responses
                # NOTE: State structure is FLAT - agents write to root level, not nested
                print(f"   ✅ Final response - checking for agent completions", flush=True)

                # Check for numeric_validation agent (looks for reviewer_output)
                agent_id = "numeric_validation"
                reviewer_output = final_state.get("reviewer_output", {})
                # ADK Best Practice: Validate data structure before accessing
                if isinstance(reviewer_output, dict) and reviewer_output and agent_id not in agents_started:
                    agents_started.add(agent_id)
                    print(f"   🎯 Agent '{agent_id}' STARTED", flush=True)
                    ws_message = {
                        "type": "agent_started",
                        "agent_id": agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    print(f"      📤 Sending WebSocket message: {ws_message}", flush=True)
                    await manager.send_to_audit(str(job_id), ws_message)

                if isinstance(reviewer_output, dict) and "findings" in reviewer_output and agent_id not in agents_completed:
                    findings = reviewer_output.get("findings", [])
                    # Validate findings is a list before sending
                    if isinstance(findings, list):
                        agents_completed.add(agent_id)
                        print(f"      ✅ Agent '{agent_id}' COMPLETED with {len(findings)} findings", flush=True)
                        ws_message = {
                            "type": "agent_completed",
                            "agent_id": agent_id,
                            "findings": findings,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        print(f"      📤 Sending completion WebSocket message", flush=True)
                        await manager.send_to_audit(str(job_id), ws_message)

                # Check for logic_consistency agent (looks for detector_output)
                agent_id = "logic_consistency"
                detector_output = final_state.get("detector_output", {})
                if isinstance(detector_output, dict) and detector_output and agent_id not in agents_started:
                    agents_started.add(agent_id)
                    print(f"   🎯 Agent '{agent_id}' STARTED", flush=True)
                    ws_message = {
                        "type": "agent_started",
                        "agent_id": agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    print(f"      📤 Sending WebSocket message: {ws_message}", flush=True)
                    await manager.send_to_audit(str(job_id), ws_message)

                if isinstance(detector_output, dict) and "findings" in detector_output and agent_id not in agents_completed:
                    findings = detector_output.get("findings", [])
                    if isinstance(findings, list):
                        agents_completed.add(agent_id)
                        print(f"      ✅ Agent '{agent_id}' COMPLETED with {len(findings)} findings", flush=True)
                        ws_message = {
                            "type": "agent_completed",
                            "agent_id": agent_id,
                            "findings": findings,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        print(f"      📤 Sending completion WebSocket message", flush=True)
                        await manager.send_to_audit(str(job_id), ws_message)

                # Check for disclosure_compliance agent (looks for scanner_output)
                agent_id = "disclosure_compliance"
                scanner_output = final_state.get("scanner_output", {})
                if isinstance(scanner_output, dict) and scanner_output and agent_id not in agents_started:
                    agents_started.add(agent_id)
                    print(f"   🎯 Agent '{agent_id}' STARTED", flush=True)
                    ws_message = {
                        "type": "agent_started",
                        "agent_id": agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    print(f"      📤 Sending WebSocket message: {ws_message}", flush=True)
                    await manager.send_to_audit(str(job_id), ws_message)

                # Check for completion by looking for disclosure_findings keys
                disclosure_findings_keys = [k for k in final_state.keys() if k.startswith("disclosure_findings:")]
                if disclosure_findings_keys and agent_id not in agents_completed:
                    # Aggregate all disclosure findings for WebSocket (validate each)
                    findings = []
                    for key in disclosure_findings_keys:
                        disclosure_data = final_state.get(key, {})
                        if isinstance(disclosure_data, dict):
                            findings_list = disclosure_data.get("findings", [])
                            if isinstance(findings_list, list):
                                findings.extend(findings_list)
                    agents_completed.add(agent_id)
                    print(f"      ✅ Agent '{agent_id}' COMPLETED with {len(findings)} findings", flush=True)
                    ws_message = {
                        "type": "agent_completed",
                        "agent_id": agent_id,
                        "findings": findings,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    print(f"      📤 Sending completion WebSocket message", flush=True)
                    await manager.send_to_audit(str(job_id), ws_message)

                # Check for external_signal agent (looks for internet_to_report_findings or report_to_internet_findings)
                agent_id = "external_signal"
                internet_to_report = final_state.get("internet_to_report_findings", {})
                report_to_internet = final_state.get("report_to_internet_findings", {})
                if (isinstance(internet_to_report, dict) or isinstance(report_to_internet, dict)) and agent_id not in agents_started:
                    if internet_to_report or report_to_internet:
                        agents_started.add(agent_id)
                        print(f"   🎯 Agent '{agent_id}' STARTED", flush=True)
                        ws_message = {
                            "type": "agent_started",
                            "agent_id": agent_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        print(f"      📤 Sending WebSocket message: {ws_message}", flush=True)
                        await manager.send_to_audit(str(job_id), ws_message)

                # Check if both have completed (both should have data)
                if isinstance(internet_to_report, dict) and isinstance(report_to_internet, dict) and agent_id not in agents_completed:
                    if internet_to_report and report_to_internet:
                        # Combine both finding types for WebSocket (validate each)
                        findings = []
                        i2r_findings = internet_to_report.get("findings", [])
                        r2i_findings = report_to_internet.get("verifications", [])
                        if isinstance(i2r_findings, list):
                            findings.extend(i2r_findings)
                        if isinstance(r2i_findings, list):
                            findings.extend(r2i_findings)
                        agents_completed.add(agent_id)
                        print(f"      ✅ Agent '{agent_id}' COMPLETED with {len(findings)} findings", flush=True)
                        ws_message = {
                            "type": "agent_completed",
                            "agent_id": agent_id,
                            "findings": findings,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        print(f"      📤 Sending completion WebSocket message", flush=True)
                        await manager.send_to_audit(str(job_id), ws_message)

            
            print(f"\n{'='*80}", flush=True)
            print(f"📊 AGENT PIPELINE COMPLETED", flush=True)
            print(f"   Total events processed: {event_count}", flush=True)
            print(f"   Agents started: {agents_started}", flush=True)
            print(f"   Agents completed: {agents_completed}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Fetch the final session state from the runner
            print("📦 Fetching final session state from runner...", flush=True)
            try:
                final_session = await runner.session_service.get_session(
                    app_name=runner.app_name,
                    user_id=str(job_id),
                    session_id=session.id
                )
                final_state = final_session.state
                print(f"✅ Session state retrieved. Keys: {list(final_state.keys())}", flush=True)
            except Exception as e:
                print(f"❌ Failed to retrieve session state: {e}", flush=True)
                final_state = {}
            
            # 3. Extract findings from orchestrator output
            print("📦 Step 5: Extracting findings from session state...", flush=True)
            # Orchestrator runs sub-agents in parallel and aggregates their session states

            # NOTE: State structure is FLAT - agents write to root level, not nested under agent names

            # 3a. Extract numeric validation findings (from reviewer_output at root level)
            reviewer_output = final_state.get("reviewer_output", {})
            numeric_findings = reviewer_output.get("findings", [])
            print(f"   🔢 Numeric Validation: {len(numeric_findings)} findings")

            # 3b. Extract logic consistency findings (from detector_output at root level)
            detector_output = final_state.get("detector_output", {})
            logic_findings = detector_output.get("findings", [])
            print(f"   🧠 Logic Consistency: {len(logic_findings)} findings")

            # 3c. Extract disclosure compliance findings (from disclosure_findings:* keys at root level)
            # Aggregate all disclosure findings from all standards
            disclosure_findings = []
            disclosure_findings_keys = [k for k in final_state.keys() if k.startswith("disclosure_findings:")]
            for key in disclosure_findings_keys:
                disclosure_data = final_state.get(key, {})
                disclosure_findings.extend(disclosure_data.get("findings", []))
            print(f"   📄 Disclosure Compliance: {len(disclosure_findings)} findings")

            # 3d. Extract external signal findings (from root level keys)
            # 3d.1. Internet→Report findings (signals contradicting report)
            internet_to_report_output = final_state.get("internet_to_report_findings", {})
            internet_to_report_findings = internet_to_report_output.get("findings", [])

            # 3d.2. Report→Internet findings (report claims that are contradicted)
            report_to_internet_output = final_state.get("report_to_internet_findings", {})
            report_to_internet_verifications = report_to_internet_output.get("verifications", [])
            print(f"   🌐 External Signals: {len(internet_to_report_findings)} internet→report + {len(report_to_internet_verifications)} report→internet")

            # 4. Save findings to database
            print(f"\n💾 Step 6: Saving findings to database...")
            total_findings = len(numeric_findings) + len(logic_findings) + len(disclosure_findings) + len(internet_to_report_findings) + len(report_to_internet_verifications)
            print(f"   Total findings to save: {total_findings}")
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
            print(f"\n✅ All findings saved successfully")
            print(f"🔄 Updating job status to 'completed'...")
            job.status = "completed"
            await self.db.commit()
            print("✅ Job status updated to 'completed'")

            # 6. Send audit complete message
            print(f"📤 Sending 'audit_complete' WebSocket message...")
            await manager.send_to_audit(str(job_id), {
                "type": "audit_complete",
                "timestamp": datetime.utcnow().isoformat()
            })
            print("✅ Audit complete message sent")

        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ PROCESSOR ERROR")
            print(f"   Job ID: {job_id}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            import traceback
            print(f"   Traceback:\n{traceback.format_exc()}")
            print(f"{'='*80}\n")
            
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
