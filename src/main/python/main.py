"""
Cruise Employee English Assessment Platform
Main FastAPI application entry point
"""

import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.database import engine, Base
from api.routes import assessment, admin, analytics, ui
from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Cruise Employee English Assessment Platform",
        description="AI-powered English proficiency testing for cruise ship employees",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # UI routes (frontend pages)
    app.include_router(ui.router, tags=["UI"])

    # API routes (backend endpoints)
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
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )