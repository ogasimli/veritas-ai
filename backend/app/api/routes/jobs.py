from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db import get_db
from app.models.job import Job
from app.models.finding import Finding
from app.schemas.job import JobRead
from app.schemas.finding import FindingRead

router = APIRouter()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get job details by ID."""
    stmt = select(Job).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/{job_id}/findings", response_model=List[FindingRead])
async def get_job_findings(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
