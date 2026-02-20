"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import admin_router, intent_router
from app.core import get_settings, cache_manager, get_async_log_service
from app.db import async_session_maker, get_db, dispose_engine
from app.models import HealthResponse, ReadyResponse

logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize cache
    await cache_manager.connect()

    # Initialize async log service
    async_log_service = get_async_log_service()
    await async_log_service.start()

    # Preload models for better performance
    try:
        logger.info("Preloading models...")
        from app.services.intent_service import IntentService
        # Initialize intent service to preload models
        intent_service = IntentService()
        # This will trigger model loading
        logger.info("Models preloaded successfully")
    except Exception as e:
        logger.warning(f"Failed to preload models: {e}")
        logger.info("Models will load on first request")

    logger.info("Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down service...")

    # Stop async log service
    await async_log_service.stop()

    # Disconnect cache
    await cache_manager.disconnect()

    # Dispose database engine
    await dispose_engine()

    logger.info("Service stopped")


# ============================================================================
# Application Factory
# ============================================================================

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Intent Recognition Service for PLM Applications",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(intent_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)

    # Serve static files
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse, tags=["ui"])
    async def ui_index():
        """Serve main UI page."""
        html_path = static_dir / "index.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Intent Recognition Service</h1><p>UI not found. Please rebuild service.</p>")

    # Health check endpoints
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=datetime.utcnow(),
            dependencies={
                "database": "ok",
                "cache": "ok" if cache_manager._pool else "disabled",
            },
        )

    @app.get("/ready", response_model=ReadyResponse, tags=["health"])
    async def readiness_check():
        """Readiness check endpoint."""
        # Check database
        from sqlalchemy import text
        database_connected = False
        try:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
                database_connected = True
        except Exception:
            pass

        # Check cache
        cache_connected = cache_manager._pool is not None

        # Check if model is loaded
        model_loaded = False
        try:
            from app.services.intent_service import IntentService
            intent_service = IntentService()
            model_loaded = hasattr(intent_service, "_embedding_model") and intent_service._embedding_model is not None
        except Exception:
            pass

        ready = database_connected

        if not ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready",
            )

        return ReadyResponse(
            ready=ready,
            model_loaded=model_loaded,
            database_connected=database_connected,
            cache_connected=cache_connected,
        )

    # Metrics endpoint (optional)
    if settings.enable_metrics:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


# Create application instance
app = create_app()


# ============================================================================
# Run with Uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
