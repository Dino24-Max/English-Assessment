"""
Authentication API Routes
Handles user registration, login, and authentication-related endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from core.database import get_db
from models.assessment import User, InvitationCode, DivisionType
from utils.auth import hash_password, verify_password
from datetime import datetime


# Initialize router
router = APIRouter()


# Pydantic models for request/response validation
class RegisterRequest(BaseModel):
    """Registration request model"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    nationality: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    invitation_code: str = Field(..., min_length=16, max_length=16)  # Required invitation code


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember: bool = False


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool
    message: str
    user_id: int
    email: str


@router.post("/register", response_model=Dict[str, Any])
async def register(
    request_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password

    Args:
        request_data: Registration data including email and password
        request: FastAPI request object for session management
        db: Database session

    Returns:
        Success message with redirect instruction

    Raises:
        HTTPException: If email already exists or registration fails
    """
    try:
        # Validate invitation code (required)
        # Find invitation code
        inv_result = await db.execute(
            select(InvitationCode).where(InvitationCode.code == request_data.invitation_code)
        )
        invitation = inv_result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=404, 
                detail="Invalid invitation code. Please contact administrator for a new code."
            )
        
        if invitation.is_used:
            raise HTTPException(
                status_code=400, 
                detail="This invitation code has already been used. Please request a new code from administrator."
            )
        
        # Check expiration
        if invitation.expires_at and invitation.expires_at < datetime.now():
            raise HTTPException(
                status_code=400, 
                detail="This invitation code has expired. Please contact administrator for a new code."
            )
        
        # Verify email matches
        if invitation.email.lower() != request_data.email.lower():
            raise HTTPException(
                status_code=400, 
                detail="Email does not match invitation code. Please use the email associated with your invitation."
            )
        
        # Get operation and department from invitation
        division = invitation.operation
        department = invitation.department
        
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == request_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered. Please login or use a different email."
            )

        # Hash password
        password_hash = hash_password(request_data.password)

        # Create new user with invitation data if available
        new_user = User(
            first_name=request_data.first_name,
            last_name=request_data.last_name,
            email=request_data.email,
            nationality=request_data.nationality,
            password_hash=password_hash,
            division=division,  # Set from invitation or None
            department=department,  # Set from invitation or None
            is_active=True
        )

        db.add(new_user)
        await db.flush()  # Get user ID before marking invitation as used
        
        # Mark invitation code as used (invitation is always present now)
        invitation.is_used = True
        invitation.used_at = datetime.now()
        invitation.used_by_user_id = new_user.id
        
        await db.commit()
        await db.refresh(new_user)

        return {
            "success": True,
            "message": "Registration successful! Please login with your credentials.",
            "redirect": "/login?registered=true",
            "invitation_used": True
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user with email and password

    Args:
        login_data: Login credentials
        request: FastAPI request object for session management
        db: Database session

    Returns:
        Authentication response with user_id and email

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()

        # Verify user exists and password is correct
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is inactive. Please contact support."
            )

        # Create session
        if not hasattr(request, 'session'):
            # If session middleware is not configured, use a fallback
            # In production, ensure session middleware is properly configured
            pass
        else:
            request.session["user_id"] = user.id
            request.session["email"] = user.email
            request.session["authenticated"] = True

        return AuthResponse(
            success=True,
            message="Login successful",
            user_id=user.id,
            email=user.email
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/check-email")
async def check_email_availability(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if email is available for registration

    Args:
        email: Email address to check
        db: Database session

    Returns:
        JSON with availability status: {"available": true/false}
    """
    try:
        # Query database for existing email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        return {
            "available": existing_user is None,
            "email": email
        }

    except Exception as e:
        # On error, return available=false to be safe
        return {
            "available": False,
            "email": email,
            "error": "Unable to check email availability"
        }


@router.post("/logout")
async def logout(request: Request):
    """
    Logout current user and clear session

    Args:
        request: FastAPI request object

    Returns:
        Success message
    """
    try:
        if hasattr(request, 'session'):
            request.session.clear()

        return {
            "success": True,
            "message": "Logged out successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User information

    Raises:
        HTTPException: If user is not authenticated
    """
    try:
        if not hasattr(request, 'session') or "user_id" not in request.session:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated"
            )

        user_id = request.session["user_id"]

        # Fetch user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nationality": user.nationality,
            "division": user.division.value if user.division else None,
            "department": user.department,
            "is_active": user.is_active
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user: {str(e)}"
        )
