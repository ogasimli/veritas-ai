import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import async_session, get_db
from app.models.document import Document
from app.models.job import Job
from app.schemas.job import JobRead
from app.services.extractor import ExtractorService
from app.services.processor import DocumentProcessor
from app.services.storage import StorageService, get_storage_service
from app.services.websocket_manager import manager
from app.utils.validators import validate_document_content

router = APIRouter()

# File size limit in MB
MAX_FILE_SIZE_MB = 20


async def process_document_task(
    job_id: uuid.UUID,
    doc_id: uuid.UUID,
    gcs_path: str,
):
    """Background task to extract text from docx and update the database."""
    print(f"\n{'=' * 80}")
    print("🚀 BACKGROUND TASK STARTED")
    print(f"   Job ID: {job_id}")
    print(f"   Document ID: {doc_id}")
    print(f"   Storage Path: {gcs_path}")
    print(f"{'=' * 80}\n")

    async with async_session() as db:
        try:
            settings = get_settings()
            storage = StorageService(bucket_name=settings.gcs_bucket)
            extractor = ExtractorService()

            # 1. Download content
            print("📥 Step 1: Downloading document from storage...")
            content = await storage.download_file(gcs_path)
            print(f"✅ Downloaded {len(content)} bytes")

            # 2. Extract markdown
            print("📝 Step 2: Extracting markdown from .docx...")
            markdown = extractor.extract_markdown(content)
            print(f"✅ Extracted {len(markdown)} characters of markdown")
            print(f"   Preview (first 200 chars): {markdown[:200]}...")

            # 2.5. Deterministic content validation
            print("🔍 Step 2.5: Validating document content...")
            is_valid, error_msg = validate_document_content(markdown)

            if not is_valid:
                print(f"❌ {error_msg}")

                # Update Job status to failed
                job_stmt = select(Job).where(Job.id == job_id)
                job_result = await db.execute(job_stmt)
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = error_msg
                    await db.commit()

                await manager.send_to_audit(
                    str(job_id),
                    {
                        "type": "validation_failed",
                        "error": error_msg,
                    },
                )
                return

            print("✅ Document content validation passed")

            # 3. Update Document record
            print("💾 Step 3: Updating document record in database...")
            stmt = select(Document).where(Document.id == doc_id)
            result = await db.execute(stmt)
            doc = result.scalar_one()
            doc.extracted_text = markdown
            await db.commit()
            print("✅ Document record updated")

            # 4. Run Agent Pipeline via DocumentProcessor
            print(f"\n{'=' * 80}")
            print("🤖 Step 4: INVOKING AGENT PIPELINE")
            print(f"{'=' * 80}\n")
            processor = DocumentProcessor(db)
            await processor.process_document(job_id=job_id, extracted_text=markdown)
            print("\n✅ Agent pipeline completed successfully")

        except Exception as e:
            print(f"\n{'=' * 80}")
            print("❌ ERROR IN BACKGROUND TASK")
            print(f"   Job ID: {job_id}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {e!s}")
            print(f"{'=' * 80}\n")

            # Update Job status to failed
            job_stmt = select(Job).where(Job.id == job_id)
            job_result = await db.execute(job_stmt)
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
            raise


@router.post("/upload", response_model=JobRead)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    # 1. Generate default name
    # Count existing jobs to determine the number
    from sqlalchemy import func

    count_stmt = select(func.count(Job.id))
    count_result = await db.execute(count_stmt)
    count = count_result.scalar_one()

    default_name = f"Report #{count + 1}"

    # 2. Create a new Job
    job = Job(status="processing", name=default_name)
    db.add(job)
    await db.flush()  # Get the job ID

    # 3. Validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size_mb:.2f}MB) exceeds the maximum allowed size of {MAX_FILE_SIZE_MB}MB",
        )

    # 4. Upload file to storage
    destination_path = f"jobs/{job.id}/{file.filename}"
    gcs_path = await storage.upload_file(
        file_content=content,
        destination_path=destination_path,
        content_type=file.content_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    # 5. Create Document record
    doc = Document(
        job_id=job.id,
        filename=file.filename,
        gcs_path=gcs_path,
        content_type=file.content_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    db.add(doc)
    await db.flush()  # Get the doc ID

    await db.commit()

    # 6. Trigger background processing
    background_tasks.add_task(
        process_document_task, job_id=job.id, doc_id=doc.id, gcs_path=gcs_path
    )

    # 7. Fetch job with documents loaded for the response
    stmt = select(Job).where(Job.id == job.id).options(selectinload(Job.documents))
    result = await db.execute(stmt)
    job_with_docs = result.scalar_one()

    return job_with_docs
