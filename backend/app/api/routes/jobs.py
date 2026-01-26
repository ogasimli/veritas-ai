from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.finding import Finding
from app.models.job import Job
from app.schemas.finding import FindingRead
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


@router.get("/{job_id}/findings", response_model=list[FindingRead])
async def get_job_findings(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all findings for a specific job."""
    # First verify job exists
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all findings for this job
    stmt = select(Finding).where(Finding.job_id == job_id).order_by(Finding.created_at)
    result = await db.execute(stmt)
    findings = result.scalars().all()

    return findings


@router.get("/{job_id}/findings/agent/{agent_id}", response_model=list[FindingRead])
async def get_agent_findings(
    job_id: UUID, agent_id: str, db: AsyncSession = Depends(get_db)
):
    """Get findings for a specific agent in a job."""
    # First verify job exists
    stmt_job = select(Job).where(Job.id == job_id)
    result_job = await db.execute(stmt_job)
    job = result_job.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get findings for this specific agent
    stmt = (
        select(Finding)
        .where(Finding.job_id == job_id, Finding.agent_id == agent_id)
        .order_by(Finding.created_at)
    )
    result = await db.execute(stmt)
    findings = result.scalars().all()

    return findings


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
