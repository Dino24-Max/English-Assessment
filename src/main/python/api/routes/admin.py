"""
Admin API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/stats")
async def get_admin_stats():
    return {"message": "Admin stats endpoint"}