"""
Analytics API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard():
    return {"message": "Analytics dashboard endpoint"}