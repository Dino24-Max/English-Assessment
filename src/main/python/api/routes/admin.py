"""
Admin API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import get_db
from models.assessment import Assessment, User, InvitationCode, DivisionType
from utils.anti_cheating import AntiCheatingService
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import secrets
import string

router = APIRouter()


@router.post("/load-full-question-bank")
async def load_full_question_bank(
    admin_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Load complete 1600-question bank into database
    Requires admin authentication
    """
    from core.config import settings
    from data.question_bank_loader import QuestionBankLoader
    import os
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key or admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        loader = QuestionBankLoader(db)
        count = await loader.load_full_question_bank()
        
        return {
            "status": "success",
            "message": f"Successfully loaded {count} questions into database",
            "total_questions": count,
            "structure": "16 departments × 10 scenarios × 10 questions"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Question bank file not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load questions: {str(e)}")


# Pydantic models for invitation API
class InvitationCreateRequest(BaseModel):
    """Request model for creating invitation code"""
    email: EmailStr
    operation: str
    department: Optional[str] = None
    admin_key: str
    expires_in_days: int = 7


class InvitationCreateResponse(BaseModel):
    """Response model for created invitation"""
    code: str
    link: str
    email: str
    operation: str
    expires_at: Optional[datetime]


@router.get("/stats")
async def get_admin_stats(
    admin_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics
    """
    from core.config import settings
    import os
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key or admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        # Count total users
        users_result = await db.execute(select(func.count(User.id)))
        total_users = users_result.scalar()
        
        # Count total assessments
        assessments_result = await db.execute(select(func.count(Assessment.id)))
        total_assessments = assessments_result.scalar()
        
        # Count passed assessments today
        today = datetime.now().date()
        passed_today_result = await db.execute(
            select(func.count(Assessment.id)).where(
                Assessment.passed == True,
                func.date(Assessment.completed_at) == today
            )
        )
        passed_today = passed_today_result.scalar()
        
        # Count pending (unused) invitations
        pending_invitations_result = await db.execute(
            select(func.count(InvitationCode.id)).where(
                InvitationCode.is_used == False
            )
        )
        pending_invitations = pending_invitations_result.scalar()
        
        return {
            "total_users": total_users,
            "total_assessments": total_assessments,
            "passed_today": passed_today,
            "pending_invitations": pending_invitations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/check-config")
async def check_admin_config():
    """Debug endpoint to check admin configuration"""
    from core.config import settings
    import os
    
    env_key = os.getenv("ADMIN_API_KEY")
    settings_key = settings.ADMIN_API_KEY
    
    return {
        "env_admin_key": env_key if env_key else "NOT SET",
        "settings_admin_key": settings_key if settings_key else "NOT SET",
        "final_key": env_key or settings_key,
        "is_configured": bool(env_key or settings_key)
    }


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


# ==================== INVITATION CODE MANAGEMENT ====================

def generate_invitation_code(length: int = 16) -> str:
    """
    Generate secure random invitation code
    
    Args:
        length: Length of code (default 16)
        
    Returns:
        Random alphanumeric code
    """
    alphabet = string.ascii_letters + string.digits
    code = ''.join(secrets.choice(alphabet) for _ in range(length))
    return code


@router.post("/invitation/create", response_model=InvitationCreateResponse)
async def create_invitation_code(
    request_data: InvitationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create invitation code for user registration
    
    Admin generates a unique code and link to send to candidate's email
    """
    from core.config import settings
    import os
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key:
        raise HTTPException(status_code=500, detail="Admin authentication not configured")
    
    if request_data.admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized - Invalid admin key")
    
    # Validate operation
    try:
        operation_enum = DivisionType(request_data.operation.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid operation. Must be: hotel, marine, or casino"
        )
    
    # Generate unique code
    code = generate_invitation_code(16)
    
    # Ensure code is unique
    existing = await db.execute(
        select(InvitationCode).where(InvitationCode.code == code)
    )
    while existing.scalar_one_or_none():
        code = generate_invitation_code(16)
        existing = await db.execute(
            select(InvitationCode).where(InvitationCode.code == code)
        )
    
    # Calculate expiration
    expires_at = datetime.now() + timedelta(days=request_data.expires_in_days)
    
    # Create invitation record
    invitation = InvitationCode(
        code=code,
        email=request_data.email,
        operation=operation_enum,
        department=request_data.department,
        created_by="admin",  # Could be enhanced with admin user ID
        expires_at=expires_at,
        is_used=False
    )
    
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    
    # Generate registration link
    base_url = str(request.base_url).rstrip('/')
    registration_link = f"{base_url}/register?code={code}"
    
    return InvitationCreateResponse(
        code=code,
        link=registration_link,
        email=request_data.email,
        operation=operation_enum.value,
        expires_at=expires_at
    )


@router.get("/invitations")
async def get_all_invitations(
    show_used: bool = True,
    show_expired: bool = True,
    operation: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all invitation codes with filtering options
    
    Query parameters:
    - show_used: Include used codes (default True)
    - show_expired: Include expired codes (default True)
    - operation: Filter by operation (hotel/marine/casino)
    """
    query = select(InvitationCode)
    
    # Apply filters
    filters = []
    
    if not show_used:
        filters.append(InvitationCode.is_used == False)
    
    if not show_expired:
        filters.append(
            (InvitationCode.expires_at.is_(None)) | 
            (InvitationCode.expires_at > datetime.now())
        )
    
    if operation:
        try:
            op_enum = DivisionType(operation.lower())
            filters.append(InvitationCode.operation == op_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid operation")
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(InvitationCode.created_at.desc())
    
    result = await db.execute(query)
    invitations = result.scalars().all()
    
    # Format response
    invitation_list = []
    for inv in invitations:
        # Check if expired
        is_expired = False
        if inv.expires_at:
            is_expired = inv.expires_at < datetime.now()
        
        invitation_list.append({
            "id": inv.id,
            "code": inv.code,
            "email": inv.email,
            "operation": inv.operation.value,
            "department": inv.department,
            "created_by": inv.created_by,
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "is_used": inv.is_used,
            "used_at": inv.used_at.isoformat() if inv.used_at else None,
            "used_by_user_id": inv.used_by_user_id,
            "is_expired": is_expired,
            "status": "used" if inv.is_used else ("expired" if is_expired else "active")
        })
    
    return {
        "total": len(invitation_list),
        "invitations": invitation_list
    }


@router.get("/invitation/{code}/status")
async def get_invitation_status(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a specific invitation code
    """
    result = await db.execute(
        select(InvitationCode).where(InvitationCode.code == code)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation code not found")
    
    # Check if expired
    is_expired = False
    if invitation.expires_at:
        is_expired = invitation.expires_at < datetime.now()
    
    # Get user info if used
    user_info = None
    if invitation.used_by_user_id:
        user_result = await db.execute(
            select(User).where(User.id == invitation.used_by_user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            user_info = {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email
            }
    
    return {
        "code": invitation.code,
        "email": invitation.email,
        "operation": invitation.operation.value,
        "department": invitation.department,
        "created_at": invitation.created_at.isoformat(),
        "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
        "is_used": invitation.is_used,
        "used_at": invitation.used_at.isoformat() if invitation.used_at else None,
        "is_expired": is_expired,
        "status": "used" if invitation.is_used else ("expired" if is_expired else "active"),
        "used_by": user_info
    }


@router.delete("/invitation/{code}")
async def revoke_invitation(
    code: str,
    admin_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke/delete an invitation code (only if not used)
    """
    from core.config import settings
    import os
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key or admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Find invitation
    result = await db.execute(
        select(InvitationCode).where(InvitationCode.code == code)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation code not found")
    
    if invitation.is_used:
        raise HTTPException(
            status_code=400, 
            detail="Cannot revoke used invitation code"
        )
    
    # Delete invitation
    await db.delete(invitation)
    await db.commit()
    
    return {
        "message": "Invitation code revoked successfully",
        "code": code
    }


@router.get("/invitation/{code}/validate")
async def validate_invitation_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate invitation code for frontend verification (no admin key required)
    
    Used by invitation verification page for real-time validation.
    Returns validity status and basic information without sensitive data.
    
    Args:
        code: Invitation code to validate
        db: Database session
        
    Returns:
        Validation result with status and message
    """
    try:
        # Find invitation code
        result = await db.execute(
            select(InvitationCode).where(InvitationCode.code == code)
        )
        invitation = result.scalar_one_or_none()
        
        # Check if code exists
        if not invitation:
            return {
                "valid": False,
                "message": "Invalid invitation code",
                "email": None,
                "operation": None,
                "department": None
            }
        
        # Check if already used
        if invitation.is_used:
            return {
                "valid": False,
                "message": "This invitation code has already been used",
                "email": None,
                "operation": None,
                "department": None
            }
        
        # Check if expired
        if invitation.expires_at and invitation.expires_at < datetime.now():
            return {
                "valid": False,
                "message": "This invitation code has expired",
                "email": None,
                "operation": None,
                "department": None
            }
        
        # Valid invitation code
        return {
            "valid": True,
            "message": "Valid invitation code",
            "email": invitation.email,
            "operation": invitation.operation.value,
            "department": invitation.department
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error validating code: {str(e)}",
            "email": None,
            "operation": None,
            "department": None
        }


# ==================== USER SCOREBOARD API ====================

@router.get("/assessments")
async def get_all_assessments(
    admin_key: str,
    operation: Optional[str] = None,
    department: Optional[str] = None,
    passed: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all user assessments with filtering
    
    Args:
        admin_key: Admin authentication key
        operation: Filter by operation (hotel/marine/casino)
        department: Filter by department
        passed: Filter by pass status (true/false)
        search: Search in name or email
        db: Database session
        
    Returns:
        List of assessments with user information
    """
    from core.config import settings
    import os
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key or admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        # Build query - join User and Assessment tables
        query = select(Assessment, User).join(
            User, Assessment.user_id == User.id
        ).where(Assessment.status == "completed")
        
        # Apply filters
        if operation:
            query = query.where(User.division == operation)
        
        if department:
            query = query.where(User.department == department)
        
        if passed is not None:
            query = query.where(Assessment.passed == passed)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Format results
        assessments = []
        for assessment, user in rows:
            # Apply search filter in memory (for name/email)
            if search:
                search_lower = search.lower()
                full_name = f"{user.first_name} {user.last_name}".lower()
                email_lower = user.email.lower()
                
                if search_lower not in full_name and search_lower not in email_lower:
                    continue
            
            assessments.append({
                "assessment_id": assessment.id,
                "user_id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "operation": user.division.value if user.division else None,
                "department": user.department,
                "listening_score": assessment.listening_score or 0,
                "time_numbers_score": assessment.time_numbers_score or 0,
                "grammar_score": assessment.grammar_score or 0,
                "vocabulary_score": assessment.vocabulary_score or 0,
                "reading_score": assessment.reading_score or 0,
                "speaking_score": assessment.speaking_score or 0,
                "total_score": assessment.total_score or 0,
                "passed": assessment.passed or False,
                "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None
            })
        
        return {
            "assessments": assessments,
            "total": len(assessments)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching assessments: {str(e)}")


@router.get("/assessments/export")
async def export_assessments_csv(
    admin_key: str,
    operation: Optional[str] = None,
    department: Optional[str] = None,
    passed: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Export assessments to CSV file
    """
    from core.config import settings
    import os
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    # Verify admin key
    expected_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY
    if not expected_key or admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        # Get assessments (reuse the logic from get_all_assessments)
        query = select(Assessment, User).join(
            User, Assessment.user_id == User.id
        ).where(Assessment.status == "completed")
        
        if operation:
            query = query.where(User.division == operation)
        if department:
            query = query.where(User.department == department)
        if passed is not None:
            query = query.where(Assessment.passed == passed)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'User ID', 'Full Name', 'Email', 'Operation', 'Department',
            'Listening', 'Time & Numbers', 'Grammar', 'Vocabulary', 'Reading', 'Speaking',
            'Total Score', 'Status', 'Test Date'
        ])
        
        # Write data
        for assessment, user in rows:
            # Apply search filter
            if search:
                search_lower = search.lower()
                full_name = f"{user.first_name} {user.last_name}".lower()
                email_lower = user.email.lower()
                if search_lower not in full_name and search_lower not in email_lower:
                    continue
            
            writer.writerow([
                user.id,
                f"{user.first_name} {user.last_name}",
                user.email,
                user.division.value if user.division else '',
                user.department or '',
                round(assessment.listening_score or 0),
                round(assessment.time_numbers_score or 0),
                round(assessment.grammar_score or 0),
                round(assessment.vocabulary_score or 0),
                round(assessment.reading_score or 0),
                round(assessment.speaking_score or 0),
                round(assessment.total_score or 0),
                'PASSED' if assessment.passed else 'FAILED',
                assessment.completed_at.strftime('%Y-%m-%d %H:%M:%S') if assessment.completed_at else ''
            ])
        
        # Return CSV file
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=assessment_results.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting CSV: {str(e)}")
