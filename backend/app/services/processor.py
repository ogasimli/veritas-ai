"""Document processing service with agent pipeline integration."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent

from agents.orchestrator.agent import root_agent
from app.models.finding import Finding as FindingModel
from app.models.job import Job
 
 
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
            # - numeric_validation (Phase 3)
            # - logic_consistency (Phase 4)
            # - disclosure_compliance (Phase 5)
            # Future agents: external_signal (Phase 6)
            runner = InMemoryRunner(agent=root_agent, app_name="veritas-ai")
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=str(job_id)
            )

            content = UserContent(parts=[Part(text=extracted_text)])

            # Collect final response
            final_state = {}
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                # Capture session state updates
                if hasattr(event, 'session') and event.session:
                    final_state = event.session.state

            # 3. Extract findings from orchestrator output
            # Orchestrator runs sub-agents in parallel and aggregates their session states

            # 3a. Extract numeric validation findings
            numeric_validation_state = final_state.get("numeric_validation", {})
            reviewer_output = numeric_validation_state.get("reviewer_output", {})
            numeric_findings = reviewer_output.get("findings", [])

            # 3b. Extract logic consistency findings
            logic_state = final_state.get("logic_consistency", {})
            logic_output = logic_state.get("logic_consistency_output", {})
            logic_findings = logic_output.get("findings", [])

            # 3c. Extract disclosure compliance findings
            # Disclosure findings are stored per standard with keys like "disclosure_findings:IAS 1"
            disclosure_state = final_state.get("disclosure_compliance", {})
            disclosure_findings = []
            for key, value in disclosure_state.items():
                if key.startswith("disclosure_findings:") and isinstance(value, dict):
                    # Each value is a VerifierAgentOutput with a "findings" list
                    disclosure_findings.extend(value.get("findings", []))

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

            # 4b. Save logic consistency findings
            for finding_data in logic_findings:
                finding = FindingModel(
                    job_id=job_id,
                    category="logic",
                    severity=finding_data.get("severity", "medium"),
                    description=finding_data.get("claim", ""),
                    source_refs=finding_data.get("source_refs", []),
                    reasoning=finding_data.get("reasoning", ""),
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
                    reasoning=f"{finding_data.get('standard')} {finding_data.get('disclosure_id')}: "
                             f"{finding_data.get('description', '')}",
                    agent_id="disclosure_compliance",
                )
                self.db.add(finding)

            # 5. Update job status
            job.status = "completed"
            await self.db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()
            raise
