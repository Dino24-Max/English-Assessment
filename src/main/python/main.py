"""
Cruise Employee English Assessment Platform
Main FastAPI application entry point
"""

import os
import uvicorn
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from core.database import engine, Base
from api.routes import assessment, admin, analytics, ui, auth
from core.config import settings
from core.logging_config import setup_logging
from core.security import (
    CSRFMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    get_csrf_token
)

# Setup logging first, before any other imports that might log
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    from utils.cache import cache_manager
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Redis cache
    await cache_manager.connect()
    
    yield
    
    # Shutdown
    await cache_manager.disconnect()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Cruise Employee English Assessment Platform",
        description="AI-powered English proficiency testing for cruise ship employees",
        version="1.0.0",
        lifespan=lifespan
    )

    # Security: Validate SECRET_KEY
    if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
        logger.error("SECRET_KEY is not configured. This is a security risk!")
        raise ValueError("SECRET_KEY must be set in production environment")

    # Middleware order matters! In Starlette, last added = outermost (processed first).
    # Desired request flow: Session → CSRF → RateLimit → SecurityHeaders → CORS → App

    # CORS middleware (innermost of security chain)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "X-CSRF-Token"],
        expose_headers=["Content-Type", "Content-Length", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        max_age=3600,
    )
    
    # Security Headers middleware
    if settings.SECURITY_HEADERS_ENABLED:
        app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate Limiting middleware
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
        logger.info("Rate limiting middleware enabled")
    
    # CSRF Protection middleware
    if settings.CSRF_ENABLED:
        app.add_middleware(CSRFMiddleware)
        logger.info("CSRF protection middleware enabled")

    # Session middleware (added LAST = outermost = processed first on request)
    # This ensures request.session is available to all inner middleware (CSRF, etc.)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600 * 24 * 7,  # 7 days
        same_site="lax",
        https_only=not settings.DEBUG,
    )

    # Static files - Ensure directories exist
    python_src_dir = Path(__file__).parent
    static_dir = python_src_dir / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)
    (static_dir / "audio").mkdir(exist_ok=True)
    (static_dir / "images").mkdir(exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # UI routes (frontend pages)
    app.include_router(ui.router, tags=["UI"])

    # API routes (backend endpoints)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(assessment.router, prefix="/api/v1/assessment", tags=["Assessment"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

    @app.get("/api")
    async def api_root():
        return {
            "message": "Cruise Employee English Assessment Platform API",
            "version": "1.0.0",
            "status": "operational",
            "endpoints": {
                "assessment": "/api/v1/assessment",
                "admin": "/api/v1/admin",
                "analytics": "/api/v1/analytics"
            }
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "database": "connected"}

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Cruise Employee English Assessment Platform")
    logger.info("=" * 60)
    logger.info(f"Server running at: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Health check: http://{settings.HOST}:{settings.PORT}/health")
    logger.info(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)
    logger.info("Press CTRL+C to stop the server")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )