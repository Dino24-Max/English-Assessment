"""
Error handling utilities for production-safe error responses
"""

import logging
from fastapi import HTTPException
from core.config import settings

logger = logging.getLogger(__name__)


def safe_error_response(
    error: Exception,
    default_message: str = "An error occurred. Please try again later.",
    status_code: int = 500,
    log_context: str = None
) -> HTTPException:
    """
    Create a safe error response that doesn't leak sensitive information
    
    Args:
        error: The exception that occurred
        default_message: User-friendly error message for production
        status_code: HTTP status code
        log_context: Additional context for logging
        
    Returns:
        HTTPException with safe error message
    """
    # Log the error with full details
    if log_context:
        logger.error(f"{log_context}: {error}", exc_info=True)
    else:
        logger.error(f"Error: {error}", exc_info=True)
    
    # Return safe error message based on environment
    if settings.DEBUG:
        detail = f"Error: {str(error)}"
    else:
        detail = default_message
    
    return HTTPException(status_code=status_code, detail=detail)


