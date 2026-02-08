from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.storage import get_storage_service

client = TestClient(app)


def test_upload_document_exceeds_size_limit():
    """Test that uploading a file larger than 20MB returns a 413 error."""
    # Setup Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    # Mock count query to return 0
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0
    mock_db.execute.return_value = mock_count_result

    # Setup Mock Storage
    mock_storage = MagicMock()
    mock_storage.upload_file = AsyncMock(return_value="gs://bucket/path/file.docx")

    # Override dependencies
    async def override_get_db():
        yield mock_db

    def override_get_storage():
        return mock_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage

    try:
        # Create a file larger than 20MB (21MB)
        # We'll create 21 * 1024 * 1024 bytes = 22,020,096 bytes
        large_file_size = 21 * 1024 * 1024
        large_content = b"x" * large_file_size

        # Create a file-like object
        file_data = BytesIO(large_content)

        # Upload the file
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("large_test.docx", file_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )

        # Assert that we get a 413 error
        assert response.status_code == 413
        assert "exceeds the maximum allowed size" in response.json()["detail"]
        assert "21.00MB" in response.json()["detail"]
        assert "20MB" in response.json()["detail"]

        # Verify that upload_file was NOT called (since we failed validation)
        mock_storage.upload_file.assert_not_called()

    finally:
        # Cleanup
        app.dependency_overrides = {}


def test_upload_document_within_size_limit():
    """Test that uploading a file smaller than 20MB succeeds."""
    # Setup Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    # Mock count query to return 0
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0

    # Mock the final select query for job with documents
    from datetime import datetime
    from uuid import uuid4

    from app.models.job import Job

    mock_job = Job(
        id=uuid4(),
        name="Report #1",
        status="processing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_job.documents = []

    mock_final_result = MagicMock()
    mock_final_result.scalar_one.return_value = mock_job

    # Set up the mock to return different results for different queries
    mock_db.execute.side_effect = [mock_count_result, mock_final_result]

    # Setup Mock Storage
    mock_storage = MagicMock()
    mock_storage.upload_file = AsyncMock(return_value="gs://bucket/path/file.docx")

    # Override dependencies
    async def override_get_db():
        yield mock_db

    def override_get_storage():
        return mock_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage

    try:
        # Create a small file (1MB)
        small_file_size = 1 * 1024 * 1024
        small_content = b"x" * small_file_size

        # Create a file-like object
        file_data = BytesIO(small_content)

        # Mock the background task to prevent it from running
        with patch("app.api.routes.documents.BackgroundTasks.add_task"):
            # Upload the file
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("small_test.docx", file_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )

            # Assert that the upload succeeds
            assert response.status_code == 200
            assert response.json()["name"] == "Report #1"
            assert response.json()["status"] == "processing"

            # Verify that upload_file WAS called
            mock_storage.upload_file.assert_called_once()

    finally:
        # Cleanup
        app.dependency_overrides = {}


def test_upload_document_edge_case_exactly_20mb():
    """Test that uploading a file exactly at the 20MB limit succeeds."""
    # Setup Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    # Mock count query to return 0
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0

    # Mock the final select query for job with documents
    from datetime import datetime
    from uuid import uuid4

    from app.models.job import Job

    mock_job = Job(
        id=uuid4(),
        name="Report #1",
        status="processing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_job.documents = []

    mock_final_result = MagicMock()
    mock_final_result.scalar_one.return_value = mock_job

    # Set up the mock to return different results for different queries
    mock_db.execute.side_effect = [mock_count_result, mock_final_result]

    # Setup Mock Storage
    mock_storage = MagicMock()
    mock_storage.upload_file = AsyncMock(return_value="gs://bucket/path/file.docx")

    # Override dependencies
    async def override_get_db():
        yield mock_db

    def override_get_storage():
        return mock_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage

    try:
        # Create a file exactly 20MB
        exact_file_size = 20 * 1024 * 1024
        exact_content = b"x" * exact_file_size

        # Create a file-like object
        file_data = BytesIO(exact_content)

        # Mock the background task to prevent it from running
        with patch("app.api.routes.documents.BackgroundTasks.add_task"):
            # Upload the file
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("exact_test.docx", file_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )

            # Assert that the upload succeeds (20MB is at the limit, not over)
            assert response.status_code == 200
            assert response.json()["name"] == "Report #1"
            assert response.json()["status"] == "processing"

            # Verify that upload_file WAS called
            mock_storage.upload_file.assert_called_once()

    finally:
        # Cleanup
        app.dependency_overrides = {}
