---
phase: 02-document-ingestion
plan: 02-01
tags: backend, api, upload, storage
metrics:
  duration: 7m
  tasks: 4
  commits: 4
---

# Summary 02-01: Upload API & Storage

Successfully implemented the document upload endpoint, supporting both local storage and database tracking.

## Accomplishments
- **Schemas**: Created Pydantic schemas for `Job` and `Document` in `backend/app/schemas/`.
- **API Route**: Implemented `POST /api/v1/documents/upload` which:
    - Creates a `Job` record.
    - Uploads `.docx` files to storage (GCS or local `uploads/`).
    - Creates a `Document` record linked to the job.
    - Returns the job details with nested document information.
- **Router Registration**: Integrated the documents router into the main FastAPI application.
- **Dependency Verification**: Confirmed `python-docx` is installed.

## Decisions
- **Eager Loading**: Used `selectinload` in the upload route to ensure document details are returned in the response, as `refresh()` can be problematic with async relationships.
- **Path Pattern**: Organized uploads under `jobs/{job_id}/{filename}` to ensure unique paths.

## Deviations
- **Schemas Structure**: Created a new `backend/app/schemas/` directory and `__init__.py` to provide a clean interface, which wasn't explicitly mentioned but is best practice.

## Issues
- None.

## Next steps
- **02-02**: Implement the Extractor agent to parse `.docx` files into structured markdown.
