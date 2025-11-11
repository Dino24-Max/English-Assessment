"""
Cruise Employee English Assessment Platform
Main FastAPI application entry point
"""

import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from core.database import engine, Base
from api.routes import assessment, admin, analytics, ui, auth
from core.config import settings


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

    # Session middleware (must be added before CORS)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "your-secret-key-change-in-production",
        max_age=3600 * 24 * 7  # 7 days
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    print("=" * 60)
    print("Cruise Employee English Assessment Platform")
    print("=" * 60)
    print(f"Server running at: http://{settings.HOST}:{settings.PORT}")
    print(f"Health check: http://{settings.HOST}:{settings.PORT}/health")
    print(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Debug mode: {settings.DEBUG}")
    print("=" * 60)
    print("\nPress CTRL+C to stop the server\n")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )