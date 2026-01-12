"""Document processing service with agent pipeline integration."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent

from agents.numeric_validation.agent import root_agent
from app.models.finding import Finding as FindingModel
from app.models.job import Job


class DocumentProcessor:
    """Processes documents through the numeric validation pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_document(self, job_id: UUID, extracted_text: str) -> None:
        """Run numeric validation pipeline and save findings."""
        # 1. Update job status
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "processing"
        await self.db.commit()

        try:
            # 2. Run pipeline
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

            # 3. Extract findings from reviewer output
            reviewer_output = final_state.get("reviewer_output", {})
            findings = reviewer_output.get("findings", [])

            # 4. Save findings to database
            for finding_data in findings:
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

            # 5. Update job status
            job.status = "completed"
            await self.db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()
            raise
