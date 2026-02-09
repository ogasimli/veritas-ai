from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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


@router.get("/{job_id}/agent-trace")
async def get_job_agent_trace(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Download the agent execution trace (ADK debug YAML) for a specific job."""
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

    return FileResponse(
        path=str(debug_file),
        filename=f"adk_debug_{job_id}.yaml",
        media_type="application/x-yaml",
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
