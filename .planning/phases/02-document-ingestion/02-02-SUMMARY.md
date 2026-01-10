---
phase: 02-document-ingestion
plan: 02-02
tags: extractor, background-tasks, docx
metrics:
  duration: 12m
  lines_added: 207
  tests_passed: 1
---

# Summary 02-02: Extractor Agent

Implemented the full extraction pipeline from `.docx` upload to structured Markdown storage via background tasks.

## Accomplishments

- **Extractor Service**: Created `ExtractorService` using `python-docx` that iterates through document body elements to preserve order.
- **Markdown Conversion**: Implemented ordering logic for paragraphs and tables, converting tables to valid Markdown format.
- **Background Processing**: Integrated FastAPI `BackgroundTasks` into the upload endpoint to trigger extraction without blocking the user response.
- **Unit Testing**: Added `backend/tests/test_extractor.py` ensuring table integrity and document order are maintained.

## Decisions

- **Document Item Iteration**: Used `document.element.body.iterchildren()` to ensure paragraphs and tables are processed in the exact order they appear in the file.
- **Async DB Sessions in BG**: Chose to create a fresh `async_session` inside the background task to avoid issues with the request-scoped session being closed.
- **Heading Detection**: Implemented basic style-based heading detection (e.g., "Heading 1" -> `#`).

## Deviations

- **Import Fix**: Encountered a `TypeError` when checking `isinstance(parent, Document)` because `Document` in `docx` is a factory function. Fixed by importing `docx.document.Document` for type checking and aliasing the factory as `DocumentFactory`.
- **Test Dependencies**: Had to manually install `pytest` and `pytest-asyncio` in the `venv` as they weren't in the initial `requirements.txt`.

## Issues

- None.

## Next steps

- Progress to Phase 3: Numeric Validation.
- Plan 03-01: Implement the Planner agent to identify Financial Statement Line Items (FSLIs).
