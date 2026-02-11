from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.finding import AgentResult
from app.models.job import Job
from app.schemas.finding import AgentResultRead
from app.schemas.job import JobRead, JobUpdate

router = APIRouter()


@router.get("/", response_model=list[JobRead])
async def get_jobs(db: AsyncSession = Depends(get_db)):
    """Get all jobs ordered by creation date."""
    stmt = (
        select(Job).options(selectinload(Job.documents)).order_by(Job.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get job details by ID."""
    stmt = select(Job).options(selectinload(Job.documents)).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/{job_id}/results", response_model=list[AgentResultRead])
async def get_job_results(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all agent results for a specific job."""
    # First verify job exists
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all results for this job
    stmt = (
        select(AgentResult)
        .where(AgentResult.job_id == job_id)
        .order_by(AgentResult.created_at)
    )
    result = await db.execute(stmt)
    results = result.scalars().all()

    return results


@router.get("/{job_id}/results/agent/{agent_id}", response_model=list[AgentResultRead])
async def get_agent_results(
    job_id: UUID, agent_id: str, db: AsyncSession = Depends(get_db)
):
    """Get results for a specific agent in a job."""
    # First verify job exists
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get results for this specific agent
    stmt = (
        select(AgentResult)
        .where(AgentResult.job_id == job_id, AgentResult.agent_id == agent_id)
        .order_by(AgentResult.created_at)
    )
    result = await db.execute(stmt)
    results = result.scalars().all()

    return results


@router.get("/{job_id}/agent-traces/debug-log")
async def get_job_debug_log(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Return the structured ADK debug YAML for a specific job."""
    # First verify job exists
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Look for debug file
    debug_file = Path.cwd() / f"adk_debug_{job_id}.yaml"
    if not debug_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Debug file not found for job {job_id}. File may have been cleaned up or job did not complete.",
        )

    return PlainTextResponse(content=debug_file.read_text(encoding="utf-8"))


@router.get("/{job_id}/agent-traces/trace-log")
async def get_job_trace_log(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
):
    """Get the real-time logging plugin trace for a job.

    Returns log lines produced by the ADK LoggingPlugin during agent execution.
    The log file is written to continuously while the job is processing, so
    clients can poll this endpoint to follow progress in real time.

    Query params:
        offset: Byte offset to start reading from (default 0). The response
                includes an X-Log-Offset header with the end offset so the
                next request can pick up where it left off.
    """
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    log_file = Path.cwd() / f"agent_trace_{job_id}.log"
    if not log_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Trace log not found for job {job_id}. The job may not have started yet.",
        )

    content = log_file.read_text(encoding="utf-8")
    content_bytes = content.encode("utf-8")

    # Slice from the requested byte offset
    chunk = content_bytes[offset:]
    new_offset = offset + len(chunk)

    return PlainTextResponse(
        content=chunk.decode("utf-8"),
        headers={
            "X-Log-Offset": str(new_offset),
            "X-Job-Status": job.status,
        },
    )


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: UUID, job_update: JobUpdate, db: AsyncSession = Depends(get_db)
):
    """Update job details."""
    stmt = select(Job).options(selectinload(Job.documents)).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a job."""
    stmt = select(Job).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()

    return {"ok": True}
