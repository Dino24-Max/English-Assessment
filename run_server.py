#!/usr/bin/env python3
"""
Development server runner for English Assessment Platform
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add src/main/python to Python path
project_root = Path(__file__).parent
src_path = project_root / "src" / "main" / "python"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    print("🚢 Starting Cruise Employee English Assessment Platform...")
    print("📊 Dashboard will be available at: http://127.0.0.1:8000")
    print("📖 API docs available at: http://127.0.0.1:8000/docs")
    print("🔍 Health check: http://127.0.0.1:8000/health")
    print()

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )