from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.db import get_db
from app.services.storage import StorageService, get_storage_service
from app.models.job import Job
from app.models.document import Document
from app.schemas.job import JobRead

router = APIRouter()

@router.post("/upload", response_model=JobRead)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    # 1. Create a new Job
    job = Job(status="pending")
    db.add(job)
    await db.flush()  # Get the job ID

    # 2. Upload file to storage
    # We use job ID and filename for destination path to avoid collisions
    content = await file.read()
    destination_path = f"jobs/{job.id}/{file.filename}"
    gcs_path = await storage.upload_file(
        file_content=content,
        destination_path=destination_path,
        content_type=file.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # 3. Create Document record
    doc = Document(
        job_id=job.id,
        filename=file.filename,
        gcs_path=gcs_path,
        content_type=file.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    db.add(doc)
    
    await db.commit()
    
    # 4. Fetch job with documents loaded for the response
    # refresh() often struggles with eager loading of relationships in async SQLAlchemy
    stmt = select(Job).where(Job.id == job.id).options(selectinload(Job.documents))
    result = await db.execute(stmt)
    job_with_docs = result.scalar_one()

    return job_with_docs
