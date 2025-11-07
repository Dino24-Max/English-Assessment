"""
Admin API endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from models.assessment import Assessment, User
from utils.anti_cheating import AntiCheatingService
from typing import List, Dict, Any

router = APIRouter()

@router.get("/stats")
async def get_admin_stats():
    return {"message": "Admin stats endpoint"}


@router.get("/anti-cheating/assessments", response_model=List[Dict[str, Any]])
async def get_all_assessments_with_cheating_data(db: AsyncSession = Depends(get_db)):
    """
    Get all assessments with anti-cheating data
    Shows IP addresses, user agents, suspicious scores, and behavior tracking
    """
    result = await db.execute(
        select(Assessment, User).join(User, Assessment.user_id == User.id)
    )

    assessments_data = []
    anti_cheating = AntiCheatingService(db)

    for assessment, user in result.all():
        # Get suspicious score
        suspicious_score = await anti_cheating.get_suspicious_score(assessment.id)

        # Extract analytics data
        analytics = assessment.analytics_data or {}

        assessment_info = {
            "assessment_id": assessment.id,
            "user_name": f"{user.first_name} {user.last_name}",
            "user_email": user.email,
            "division": assessment.division.value,
            "status": assessment.status.value,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,

            # Anti-cheating data
            "ip_address": assessment.ip_address,
            "user_agent": assessment.user_agent,

            # Behavior tracking
            "tab_switches": analytics.get("tab_switches", 0),
            "copy_paste_attempts": analytics.get("copy_paste_attempts", 0),
            "suspicious_events": analytics.get("suspicious_events", []),

            # Suspicious score
            "suspicious_score": suspicious_score.get("score", 0),
            "risk_level": suspicious_score.get("level", "clean"),
            "requires_review": suspicious_score.get("requires_review", False),
            "risk_factors": suspicious_score.get("factors", []),

            # Session info
            "session_start_time": analytics.get("session_start_time"),
            "initial_ip": analytics.get("initial_ip"),
            "initial_user_agent": analytics.get("initial_user_agent"),
            "flagged_for_review": analytics.get("flagged_for_review", False),
        }

        assessments_data.append(assessment_info)

    return assessments_data


@router.get("/anti-cheating/assessment/{assessment_id}")
async def get_assessment_cheating_details(
    assessment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed anti-cheating data for a specific assessment
    """
    result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        return {"error": "Assessment not found"}

    # Get suspicious score and details
    anti_cheating = AntiCheatingService(db)
    suspicious_score = await anti_cheating.get_suspicious_score(assessment_id)

    analytics = assessment.analytics_data or {}

    return {
        "assessment_id": assessment.id,
        "ip_address": assessment.ip_address,
        "user_agent": assessment.user_agent,
        "analytics_data": analytics,
        "suspicious_score": suspicious_score,
        "risk_breakdown": {
            "tab_switches": {
                "count": analytics.get("tab_switches", 0),
                "threshold": 3,
                "status": "warning" if analytics.get("tab_switches", 0) > 3 else "ok"
            },
            "copy_paste": {
                "count": analytics.get("copy_paste_attempts", 0),
                "threshold": 5,
                "status": "warning" if analytics.get("copy_paste_attempts", 0) > 5 else "ok"
            },
            "ip_consistency": {
                "initial": analytics.get("initial_ip"),
                "current": assessment.ip_address,
                "changed": analytics.get("initial_ip") != assessment.ip_address if analytics.get("initial_ip") else False
            },
            "user_agent_consistency": {
                "initial": analytics.get("initial_user_agent"),
                "current": assessment.user_agent,
                "changed": analytics.get("initial_user_agent") != assessment.user_agent if analytics.get("initial_user_agent") else False
            }
        }
    }