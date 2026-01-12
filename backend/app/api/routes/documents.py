import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.db import get_db, async_session
from app.config import get_settings
from app.services.storage import StorageService, get_storage_service
from app.services.extractor import ExtractorService, get_extractor_service
from app.services.processor import DocumentProcessor
from app.models.job import Job
from app.models.document import Document
from app.schemas.job import JobRead

router = APIRouter()

async def process_document_task(
    job_id: uuid.UUID,
    doc_id: uuid.UUID,
    gcs_path: str,
):
    """Background task to extract text from docx and update the database."""
    async with async_session() as db:
        try:
            settings = get_settings()
            storage = StorageService(bucket_name=settings.gcs_bucket)
            extractor = ExtractorService()

            # 1. Download content
            content = await storage.download_file(gcs_path)
            
            # 2. Extract markdown
            markdown = extractor.extract_markdown(content)
            
            # 3. Update Document record
            stmt = select(Document).where(Document.id == doc_id)
            result = await db.execute(stmt)
            doc = result.scalar_one()
            doc.extracted_text = markdown
            await db.commit()
            
            # 4. Run Agent Pipeline via DocumentProcessor
            processor = DocumentProcessor(db)
            await processor.process_document(job_id=job_id, extracted_text=markdown)

        except Exception as e:
            # Update Job status to failed
            job_stmt = select(Job).where(Job.id == job_id)
            job_result = await db.execute(job_stmt)
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
            print(f"Error processing document {doc_id}: {e}")

@router.post("/upload", response_model=JobRead)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    # 1. Create a new Job
    job = Job(status="processing")
    db.add(job)
    await db.flush()  # Get the job ID

    # 2. Upload file to storage
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
    await db.flush() # Get the doc ID
    
    await db.commit()
    
    # 4. Trigger background processing
    background_tasks.add_task(
        process_document_task,
        job_id=job.id,
        doc_id=doc.id,
        gcs_path=gcs_path
    )
    
    # 5. Fetch job with documents loaded for the response
    stmt = select(Job).where(Job.id == job.id).options(selectinload(Job.documents))
    result = await db.execute(stmt)
    job_with_docs = result.scalar_one()

    return job_with_docs
