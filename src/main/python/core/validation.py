"""
Input validation utilities for the assessment platform.
Provides Pydantic models and validation functions for all user inputs.
"""

import re
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Enums for Validation
# =============================================================================

class OperationType(str, Enum):
    """Valid operation types for assessments."""
    HOTEL = "HOTEL"
    MARINE = "MARINE"
    CASINO = "CASINO"


class ModuleType(str, Enum):
    """Valid module types for questions."""
    LISTENING = "listening"
    TIME_NUMBERS = "time_numbers"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    READING = "reading"
    SPEAKING = "speaking"


# =============================================================================
# Common Validators
# =============================================================================

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string input by removing potentially dangerous characters.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Trim to max length
    value = value[:max_length]
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Strip leading/trailing whitespace
    value = value.strip()
    
    return value


def validate_question_number(value: int) -> int:
    """
    Validate question number is within valid range.
    
    Args:
        value: Question number
        
    Returns:
        Validated question number
        
    Raises:
        ValueError: If question number is invalid
    """
    if not isinstance(value, int) or value < 1 or value > 21:
        raise ValueError("Question number must be between 1 and 21")
    return value


def validate_operation(value: str) -> str:
    """
    Validate operation type.
    
    Args:
        value: Operation string
        
    Returns:
        Validated operation in uppercase
        
    Raises:
        ValueError: If operation is invalid
    """
    if not value:
        raise ValueError("Operation is required")
    
    value = value.upper().strip()
    valid_operations = {"HOTEL", "MARINE", "CASINO"}
    
    if value not in valid_operations:
        raise ValueError(f"Operation must be one of: {', '.join(valid_operations)}")
    
    return value


# =============================================================================
# Request Models
# =============================================================================

class AnswerSubmission(BaseModel):
    """Model for answer submission validation."""
    
    question_num: int = Field(..., ge=1, le=21, description="Question number (1-21)")
    answer: str = Field(..., min_length=1, max_length=10000, description="User's answer")
    operation: Optional[str] = Field(None, description="Operation type (HOTEL, MARINE, CASINO)")
    time_spent: Optional[int] = Field(None, ge=0, le=3600, description="Time spent in seconds")
    
    @field_validator('answer')
    @classmethod
    def sanitize_answer(cls, v: str) -> str:
        """Sanitize the answer input."""
        return sanitize_string(v, max_length=10000)
    
    @field_validator('operation')
    @classmethod
    def validate_operation_field(cls, v: Optional[str]) -> Optional[str]:
        """Validate operation if provided."""
        if v is None or v == "":
            return None
        return validate_operation(v)


class AssessmentStartRequest(BaseModel):
    """Model for starting an assessment."""
    
    operation: str = Field(..., description="Operation type (HOTEL, MARINE, CASINO)")
    
    @field_validator('operation')
    @classmethod
    def validate_operation_field(cls, v: str) -> str:
        """Validate operation."""
        return validate_operation(v)


class InvitationCodeValidation(BaseModel):
    """Model for invitation code validation."""
    
    code: str = Field(..., min_length=16, max_length=16, description="16-character invitation code")
    
    @field_validator('code')
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Validate invitation code format."""
        v = v.strip()
        if len(v) != 16:
            raise ValueError("Invitation code must be exactly 16 characters")
        # Only allow alphanumeric characters
        if not re.match(r'^[A-Za-z0-9]+$', v):
            raise ValueError("Invitation code must contain only letters and numbers")
        return v


class VocabularyMatchAnswer(BaseModel):
    """Model for vocabulary matching answer validation."""
    
    matches: Dict[str, str] = Field(..., description="Dictionary of term -> definition matches")
    
    @field_validator('matches')
    @classmethod
    def validate_matches(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate vocabulary matches."""
        if not v:
            raise ValueError("At least one match is required")
        
        if len(v) > 10:
            raise ValueError("Too many matches (maximum 10)")
        
        # Sanitize all keys and values
        sanitized = {}
        for key, value in v.items():
            clean_key = sanitize_string(key, max_length=200)
            clean_value = sanitize_string(value, max_length=500)
            if clean_key and clean_value:
                sanitized[clean_key] = clean_value
        
        return sanitized


class SpeakingAnswer(BaseModel):
    """Model for speaking module answer validation."""
    
    duration_seconds: int = Field(..., ge=0, le=300, description="Recording duration in seconds")
    transcript: Optional[str] = Field(None, max_length=5000, description="Transcribed text")
    
    @field_validator('transcript')
    @classmethod
    def sanitize_transcript(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize transcript if provided."""
        if v is None:
            return None
        return sanitize_string(v, max_length=5000)


class AdminScoreboardFilters(BaseModel):
    """Model for admin scoreboard filter validation."""
    
    division: Optional[str] = Field(None, description="Filter by division")
    department: Optional[str] = Field(None, max_length=100, description="Filter by department")
    passed: Optional[bool] = Field(None, description="Filter by pass/fail status")
    date_from: Optional[str] = Field(None, description="Filter from date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="Filter to date (YYYY-MM-DD)")
    page: int = Field(1, ge=1, le=1000, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    
    @field_validator('division')
    @classmethod
    def validate_division(cls, v: Optional[str]) -> Optional[str]:
        """Validate division if provided."""
        if v is None or v == "":
            return None
        return validate_operation(v)
    
    @field_validator('date_from', 'date_to')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v is None or v == "":
            return None
        
        # Check format YYYY-MM-DD
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        
        return v


class AntiCheatingTrackRequest(BaseModel):
    """Model for anti-cheating tracking requests."""
    
    assessment_id: Optional[str] = Field(None, max_length=100, description="Assessment ID")
    count: int = Field(..., ge=0, le=1000, description="Event count")
    action: Optional[str] = Field(None, max_length=50, description="Action type (copy/paste)")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        """Validate action type."""
        if v is None:
            return None
        
        valid_actions = {"copy", "paste"}
        v = v.lower().strip()
        
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        
        return v


# =============================================================================
# Response Models
# =============================================================================

class ValidationErrorResponse(BaseModel):
    """Standard validation error response."""
    
    detail: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that failed validation")
    code: str = Field("validation_error", description="Error code")


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    success: bool = Field(True, description="Success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_json_answer(answer: str, expected_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate and parse a JSON answer string.
    
    Args:
        answer: JSON string to validate
        expected_keys: Optional list of expected keys
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If JSON is invalid or missing expected keys
    """
    import json
    
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")
    
    if not isinstance(parsed, dict):
        raise ValueError("Answer must be a JSON object")
    
    if expected_keys:
        missing_keys = set(expected_keys) - set(parsed.keys())
        if missing_keys:
            raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")
    
    return parsed


def validate_speaking_answer_format(answer: str) -> tuple[int, str]:
    """
    Validate and parse speaking answer format.
    
    Expected format: "recorded_Xs|transcript" or "recorded_Xs"
    
    Args:
        answer: Speaking answer string
        
    Returns:
        Tuple of (duration_seconds, transcript)
        
    Raises:
        ValueError: If format is invalid
    """
    if not answer.startswith("recorded_"):
        raise ValueError("Speaking answer must start with 'recorded_'")
    
    # Parse duration
    duration_match = re.match(r'recorded_(\d+)s?', answer)
    if not duration_match:
        raise ValueError("Invalid recording duration format")
    
    duration = int(duration_match.group(1))
    
    if duration < 0 or duration > 300:
        raise ValueError("Recording duration must be between 0 and 300 seconds")
    
    # Parse transcript if present
    transcript = ""
    if "|" in answer:
        parts = answer.split("|", 1)
        if len(parts) > 1:
            transcript = parts[1].strip()
    
    return duration, transcript


def validate_email_format(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValueError: If email format is invalid
    """
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    email = email.strip().lower()
    
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    
    if len(email) > 254:
        raise ValueError("Email address too long (maximum 254 characters)")
    
    return email


def validate_password_strength(password: str) -> str:
    """
    Validate password meets minimum requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        Validated password
        
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")
    
    if len(password) > 100:
        raise ValueError("Password must be at most 100 characters long")
    
    # Check for at least one letter and one number (optional but recommended)
    # if not re.search(r'[a-zA-Z]', password):
    #     raise ValueError("Password must contain at least one letter")
    # if not re.search(r'\d', password):
    #     raise ValueError("Password must contain at least one number")
    
    return password


# =============================================================================
# Request Size Validation
# =============================================================================

def validate_request_size(content_length: int, max_size: int) -> bool:
    """
    Validate request content length.
    
    Args:
        content_length: Request content length in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If content too large
    """
    if content_length > max_size:
        raise ValueError(f"Request too large. Maximum size is {max_size / (1024 * 1024):.1f} MB")
    
    return True
