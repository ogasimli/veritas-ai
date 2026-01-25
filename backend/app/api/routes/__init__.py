from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.websockets import router as websockets_router
from app.api.routes.jobs import router as jobs_router

__all__ = ["health_router", "documents_router", "websockets_router", "jobs_router"]
