"""
Authentication API Routes
Handles user registration, login, and authentication-related endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, Optional
import secrets
import hashlib

from core.database import get_db
from models.assessment import User, InvitationCode, DivisionType, PasswordResetToken
from utils.auth import hash_password, verify_password
from datetime import datetime, timedelta


# Initialize router
router = APIRouter()


# Pydantic models for request/response validation
class RegisterRequest(BaseModel):
    """Registration request model"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    nationality: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = Field(None)  # Optional - not required for invitation-based registration
    invitation_code: Optional[str] = Field(None)  # Optional - required for invitation-based registration
    
    @field_validator('password', mode='before')
    @classmethod
    def validate_password(cls, v):
        """Validate password if provided"""
        if v is not None and v != "":
            v = v.strip()
            if len(v) < 6 or len(v) > 100:
                raise ValueError('Password must be between 6 and 100 characters')
        return v if v else None
    
    @field_validator('invitation_code', mode='before')
    @classmethod
    def validate_invitation_code(cls, v):
        """Validate invitation code if provided"""
        if v is not None and v != "":
            v = v.strip()
            if len(v) != 16:
                raise ValueError('Invitation code must be exactly 16 characters')
        return v if v else None
    
    @model_validator(mode='after')
    def validate_registration(self):
        """Validate that either password or invitation_code is provided"""
        # Check if password is provided and not empty
        has_password = self.password and self.password.strip() != ""
        # Check if invitation_code is provided and not empty
        has_invitation = self.invitation_code and self.invitation_code.strip() != ""
        
        if not has_password and not has_invitation:
            raise ValueError('Either password or invitation_code must be provided')
        return self


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember: bool = False
    is_admin: bool = False  # Admin login flag


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool
    message: str
    user_id: int
    email: str
    is_admin: bool = False  # Indicate if user is admin
    division: Optional[str] = None  # User's division for redirect


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
        # Validate invitation code if provided
        invitation = None
        division = None
        department = None
        
        if request_data.invitation_code and request_data.invitation_code.strip():
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
            
            # Check if invitation is already used or assessment completed
            if invitation.is_used:
                if invitation.assessment_completed:
                    raise HTTPException(
                        status_code=400, 
                        detail="This invitation link has already been used and the assessment has been completed. Please contact administrator for a new invitation."
                    )
                else:
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
        else:
            # No invitation code - require password for traditional registration
            if not request_data.password:
                raise HTTPException(
                    status_code=400,
                    detail="Password is required for registration without invitation code."
                )
        
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == request_data.email)
        )
        existing_user = result.scalar_one_or_none()

        # If user exists and invitation code is provided, allow them to start assessment
        if existing_user:
            if invitation:
                # User exists and has invitation code - create assessment directly
                # Verify invitation email matches
                if invitation.email.lower() != request_data.email.lower():
                    raise HTTPException(
                        status_code=400,
                        detail="Email does not match invitation code. Please use the email associated with your invitation."
                    )
                
                # Check if invitation is already used by this user
                if invitation.is_used and invitation.used_by_user_id != existing_user.id:
                    if invitation.assessment_completed:
                        raise HTTPException(
                            status_code=400,
                            detail="This invitation link has already been used and the assessment has been completed. Please contact administrator for a new invitation."
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail="This invitation code has already been used by another user. Please contact administrator for a new code."
                        )
                
                # Update user info if needed
                if request_data.first_name:
                    existing_user.first_name = request_data.first_name
                if request_data.last_name:
                    existing_user.last_name = request_data.last_name
                if request_data.nationality:
                    existing_user.nationality = request_data.nationality
                
                # Mark invitation as used if not already
                if not invitation.is_used:
                    invitation.is_used = True
                    invitation.used_at = datetime.now()
                    invitation.used_by_user_id = existing_user.id
                
                await db.commit()
                await db.refresh(existing_user)
                
                # Create assessment for existing user (but don't start yet - user will see instructions first)
                from core.assessment_engine import AssessmentEngine
                
                engine = AssessmentEngine(db)
                assessment = await engine.create_assessment(
                    user_id=existing_user.id,
                    division=division
                )
                
                # Don't start assessment yet - user needs to see instructions first
                # Assessment will be started when user clicks "Start Assessment" on instructions page
                
                # Store in session for UI routes
                request.session["user_id"] = existing_user.id
                request.session["assessment_id"] = assessment.id
                request.session["operation"] = division.value.upper()
                request.session["invitation_code"] = invitation.code
                
                return {
                    "success": True,
                    "message": "Registration successful! Please read the instructions before starting.",
                    "redirect": f"/instructions?operation={division.value.upper()}",
                    "invitation_used": True,
                    "assessment_id": assessment.id,
                    "auto_start": False
                }
            else:
                # User exists but no invitation code - require login
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered. Please login or use a different email."
                )

        # Handle password - if not provided (invitation-based), use secure random hash
        if request_data.password:
            password_hash = hash_password(request_data.password)
        elif invitation:
            # For invitation-based registration without password:
            # Generate a secure random password hash that cannot be guessed
            # Users with this marker cannot login via password (they use invitation links)
            # SECURITY: Use hash of random bytes, not the invitation code itself
            random_password = secrets.token_urlsafe(32)
            password_hash = "INVITATION_ONLY:" + hash_password(random_password)
        else:
            # This should not happen due to validation above, but add safety check
            raise HTTPException(
                status_code=400,
                detail="Password is required for registration."
            )

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
        
        # Mark invitation code as used if invitation was provided
        if invitation:
            invitation.is_used = True
            invitation.used_at = datetime.now()
            invitation.used_by_user_id = new_user.id
        
        await db.commit()
        await db.refresh(new_user)

        # All registrations should create assessment and redirect to instructions page
        # This applies to both invitation-based and password-based registrations
        if invitation:
            # Invitation-based registration - create assessment
            from core.assessment_engine import AssessmentEngine
            
            # Create assessment session
            engine = AssessmentEngine(db)
            assessment = await engine.create_assessment(
                user_id=new_user.id,
                division=division
            )
            
            # Don't start assessment yet - user needs to see instructions first
            # Assessment will be started when user clicks "Start Assessment" on instructions page
            
            # Store in session for UI routes
            request.session["user_id"] = new_user.id
            request.session["assessment_id"] = assessment.id
            request.session["operation"] = division.value.upper()
            request.session["invitation_code"] = invitation.code
            
            return {
                "success": True,
                "message": "Registration successful! Please read the instructions before starting.",
                "redirect": f"/instructions?operation={division.value.upper()}",
                "invitation_used": True,
                "assessment_id": assessment.id,
                "auto_start": False
            }
        else:
            # No invitation code - registration not allowed
            raise HTTPException(
                status_code=400,
                detail="Registration requires a valid invitation code. Please contact administrator."
            )

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

        # Check if user exists
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Check if this is an invitation-only user (cannot login with password)
        # Support both old format (INVITATION_ONLY_) and new secure format (INVITATION_ONLY:)
        if user.password_hash and (user.password_hash.startswith("INVITATION_ONLY:") or 
                                    user.password_hash.startswith("INVITATION_ONLY_")):
            raise HTTPException(
                status_code=403,
                detail="This account was created via invitation link and cannot be accessed with password. Please use your invitation link to access the assessment."
            )

        # Verify password is correct
        if not verify_password(login_data.password, user.password_hash):
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
        
        # Admin login checkbox removed from UI
        # All users can login normally, admin status is checked from user record
        user_is_admin = getattr(user, 'is_admin', False)

        # Create session
        if not hasattr(request, 'session'):
            # If session middleware is not configured, use a fallback
            # In production, ensure session middleware is properly configured
            pass
        else:
            request.session["user_id"] = user.id
            request.session["email"] = user.email
            request.session["authenticated"] = True
            request.session["is_admin"] = getattr(user, 'is_admin', False)  # Set admin flag in session

        # Get user's division for redirect
        user_division = None
        if hasattr(user, 'division') and user.division:
            user_division = user.division.value.upper()
        
        return AuthResponse(
            success=True,
            message="Login successful",
            user_id=user.id,
            email=user.email,
            is_admin=getattr(user, 'is_admin', False),
            division=user_division
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


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request model"""
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)


@router.post("/forgot-password")
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset process.
    Generates a reset token and sends a reset link.
    """
    try:
        result = await db.execute(
            select(User).where(User.email == request_data.email)
        )
        user = result.scalar_one_or_none()

        # Always return success message to prevent email enumeration
        if not user:
            return {"success": True, "message": "If an account with that email exists, a password reset link has been sent."}

        # Prevent invitation-only users from resetting password
        # Support both old format (INVITATION_ONLY_) and new secure format (INVITATION_ONLY:)
        if user.password_hash and (user.password_hash.startswith("INVITATION_ONLY:") or 
                                    user.password_hash.startswith("INVITATION_ONLY_")):
            return {"success": True, "message": "If an account with that email exists, a password reset link has been sent."}

        # Invalidate any existing tokens for this user
        from sqlalchemy import update
        await db.execute(
            update(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.now()
            ).values(used=True)
        )
        await db.commit()

        # Generate a new token
        token_value = secrets.token_urlsafe(32)
        hashed_token = hashlib.sha256(token_value.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=1)

        new_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=expires_at
        )
        db.add(new_token)
        await db.commit()

        # Build reset link
        from core.config import settings
        base_url = "http://127.0.0.1:8000" if settings.DEBUG else os.getenv("BASE_URL", "https://your-domain.com")
        reset_link = f"{base_url}/reset-password?token={token_value}"
        
        # In production: Send email with reset link
        # TODO: Implement email sending (SendGrid, SES, etc.)
        # await send_password_reset_email(user.email, reset_link)
        
        # Log for debugging (only in development)
        import logging
        logger = logging.getLogger(__name__)
        if settings.DEBUG:
            logger.info(f"Password reset link for {user.email}: {reset_link}")

        # SECURITY: Never return reset_link in API response
        # The link should only be sent via email
        response = {
            "success": True,
            "message": "If an account with that email exists, a password reset link has been sent."
        }
        
        # Only include link in development mode for testing
        if settings.DEBUG and settings.ENVIRONMENT == "development":
            response["_debug_reset_link"] = reset_link
            response["_debug_warning"] = "This field is only available in development mode"
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate password reset. Please try again later.")


@router.post("/reset-password")
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user's password using a valid token.
    """
    try:
        # Hash the incoming token to match what's stored
        hashed_token = hashlib.sha256(request_data.token.encode()).hexdigest()

        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == hashed_token,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.now()
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

        # Mark token as used
        reset_token.used = True
        
        # Update user's password
        user = await db.get(User, reset_token.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        user.password_hash = hash_password(request_data.new_password)
        
        await db.commit()

        return {"success": True, "message": "Your password has been reset successfully."}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password reset failed: {e}", exc_info=True)
        from core.config import settings
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "Failed to reset password. Please try again later."
        raise HTTPException(status_code=500, detail=detail)
