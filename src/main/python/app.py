"""
CCL English Assessment Platform - Main Application
FastAPI application with router-based architecture and template system
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn

# Import routers
from api.routes import ui

# Initialize FastAPI app
app = FastAPI(
    title="CCL English Assessment Platform",
    description="AI-powered English proficiency testing for cruise ship employees",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get python source directory (where this file is located)
python_src_dir = Path(__file__).parent
static_dir = python_src_dir / "static"
templates_dir = python_src_dir / "templates"

# Create static directories if they don't exist
static_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)
(static_dir / "audio").mkdir(exist_ok=True)
(static_dir / "images").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(ui.router, tags=["UI"])

# Root redirect handled by ui router


@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "CCL English Assessment Platform",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    print("Starting CCL English Assessment Platform...")
    print(f"Python source: {python_src_dir}")
    print(f"Static files: {static_dir}")
    print(f"Templates: {templates_dir}")
    print("Server running at: http://127.0.0.1:8080")
    print("\nPress CTRL+C to stop the server\n")

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        log_level="info"
    )
