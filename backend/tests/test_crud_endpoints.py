from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.job import Job

client = TestClient(app)


def test_jobs_crud():
    # Setup Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.delete = AsyncMock()

    # Override get_db
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # ---------------------------------------------------------
    # Test GET / (List)
    # ---------------------------------------------------------
    mock_job = Job(
        id=uuid4(),
        name="Audit #001",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock result for select(Job)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_job]
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Audit #001"

    # ---------------------------------------------------------
    # Test PATCH (Rename)
    # ---------------------------------------------------------
    job_id = mock_job.id
    # Reset mock to return the job for the update query
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_job

    response = client.patch(f"/api/v1/jobs/{job_id}", json={"name": "Renamed Audit"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Audit"

    # Check if object was updated
    assert mock_job.name == "Renamed Audit"

    # ---------------------------------------------------------
    # Test DELETE
    # ---------------------------------------------------------
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify delete was called on DB
    mock_db.delete.assert_called_with(mock_job)

    # Cleanup
    app.dependency_overrides = {}
