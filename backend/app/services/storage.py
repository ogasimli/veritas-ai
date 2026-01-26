import os
from pathlib import Path

from fastapi import Depends
from google.cloud import storage

from app.config import Settings, get_settings


class StorageService:
    """Service for handling file storage, supporting both GCS and local filesystem."""

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name
        self.use_gcs = bool(bucket_name)

        if self.use_gcs:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
        else:
            # Fallback to local storage
            self.base_path = Path("uploads")
            self.base_path.mkdir(exist_ok=True)

    async def upload_file(
        self, file_content: bytes, destination_path: str, content_type: str
    ) -> str:
        """Uploads a file and returns its path (gs:// or local path)."""
        if self.use_gcs:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_string(file_content, content_type=content_type)
            return f"gs://{self.bucket_name}/{destination_path}"
        else:
            # Local fallback
            local_path = self.base_path / destination_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_content)
            return str(local_path.absolute())

    async def download_file(self, file_path: str) -> bytes:
        """Downloads file content from GCS or local filesystem."""
        if self.use_gcs and file_path.startswith("gs://"):
            # Extract bucket name and path from gs:// uri
            parts = file_path.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid GCS path: {file_path}")

            blob = self.client.bucket(parts[0]).blob(parts[1])
            return blob.download_as_bytes()
        else:
            # Assume local path or absolute path
            with open(file_path, "rb") as f:
                return f.read()

    async def delete_file(self, file_path: str) -> None:
        """Deletes file from GCS or local filesystem."""
        if self.use_gcs and file_path.startswith("gs://"):
            parts = file_path.replace("gs://", "").split("/", 1)
            if len(parts) == 2:
                blob = self.client.bucket(parts[0]).blob(parts[1])
                blob.delete()
        else:
            if os.path.exists(file_path):
                os.remove(file_path)


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    """Dependency that provides a StorageService instance."""
    return StorageService(
        bucket_name=settings.gcs_bucket if settings.gcs_bucket else None
    )
