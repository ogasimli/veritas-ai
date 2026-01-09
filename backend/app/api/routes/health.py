"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db import async_session

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Check application and database health.

    Returns 200 even if database is disconnected, but status field shows it.
    """
    db_status = "disconnected"

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        # Database is not available, but we still return 200
        pass

    return {
        "status": "ok",
        "database": db_status,
    }
