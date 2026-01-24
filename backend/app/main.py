"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health_router, documents_router, websockets_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()
    if settings.debug:
        print("Starting Veritas AI in debug mode")
    yield
    # Shutdown
    if settings.debug:
        print("Shutting down Veritas AI")


app = FastAPI(
    title="Veritas AI",
    description="Multi-agent AI co-auditor for financial statement analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(websockets_router)  # WebSocket routes already have /ws prefix in definition
