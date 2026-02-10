"""
Security middleware and utilities for CSRF protection and rate limiting.
Implements P1 security requirements for production deployment.
"""

import logging
import secrets
import time
import hashlib
from typing import Dict, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CSRF Protection
# =============================================================================

class CSRFProtection:
    """
    CSRF (Cross-Site Request Forgery) protection implementation.
    
    Features:
    - Token generation and validation
    - Double-submit cookie pattern
    - Session-based token storage
    - Configurable exempt paths
    """
    
    # HTTP methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Paths exempt from CSRF protection (API endpoints with other auth)
    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/health",
        "/api",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Paths that start with these prefixes are exempt
    EXEMPT_PREFIXES = [
        "/api/v1/admin",  # Admin API uses API key auth
        "/static/",
        "/debug/",
    ]
    
    def __init__(self, token_length: int = 32):
        """
        Initialize CSRF protection.
        
        Args:
            token_length: Length of CSRF tokens in bytes
        """
        self.token_length = token_length
    
    def generate_token(self) -> str:
        """
        Generate a cryptographically secure CSRF token.
        
        Returns:
            URL-safe base64 encoded token
        """
        return secrets.token_urlsafe(self.token_length)
    
    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract CSRF token from request.
        
        Checks in order:
        1. X-CSRF-Token header
        2. csrf_token form field
        3. _csrf query parameter
        
        Args:
            request: FastAPI request object
            
        Returns:
            CSRF token if found, None otherwise
        """
        # Check header first (preferred for AJAX requests)
        token = request.headers.get("X-CSRF-Token")
        if token:
            return token
        
        # Check form data (for regular form submissions)
        # Note: This requires the request body to be parsed
        # We'll handle this in the middleware
        
        # Check query parameter (fallback)
        token = request.query_params.get("_csrf")
        if token:
            return token
        
        return None
    
    def get_token_from_session(self, request: Request) -> Optional[str]:
        """
        Get CSRF token from session.
        
        Args:
            request: FastAPI request object
            
        Returns:
            CSRF token from session if exists
        """
        try:
            return request.session.get("csrf_token")
        except Exception:
            return None
    
    def set_token_in_session(self, request: Request, token: str) -> None:
        """
        Store CSRF token in session.
        
        Args:
            request: FastAPI request object
            token: CSRF token to store
        """
        try:
            request.session["csrf_token"] = token
        except Exception as e:
            logger.warning(f"Failed to set CSRF token in session: {e}")
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from CSRF protection.
        
        Args:
            path: Request path
            
        Returns:
            True if exempt, False otherwise
        """
        # Check exact matches
        if path in self.EXEMPT_PATHS:
            return True
        
        # Check prefix matches
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def validate_token(self, request_token: str, session_token: str) -> bool:
        """
        Validate CSRF token using constant-time comparison.
        
        Args:
            request_token: Token from request
            session_token: Token from session
            
        Returns:
            True if tokens match, False otherwise
        """
        if not request_token or not session_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(request_token, session_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for FastAPI.
    
    Validates CSRF tokens on protected methods and generates
    tokens for GET requests to be used in subsequent requests.
    """
    
    def __init__(self, app: ASGIApp, csrf: Optional[CSRFProtection] = None):
        super().__init__(app)
        self.csrf = csrf or CSRFProtection()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with CSRF protection.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler or error response
        """
        # Skip if CSRF is disabled
        if not settings.CSRF_ENABLED:
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        
        # Generate token for GET requests (for forms to use)
        if method == "GET":
            # Ensure session has a CSRF token
            session_token = self.csrf.get_token_from_session(request)
            if not session_token:
                new_token = self.csrf.generate_token()
                self.csrf.set_token_in_session(request, new_token)
            
            response = await call_next(request)
            return response
        
        # Check if path is exempt
        if self.csrf.is_path_exempt(path):
            return await call_next(request)
        
        # Validate CSRF token for protected methods
        if method in CSRFProtection.PROTECTED_METHODS:
            session_token = self.csrf.get_token_from_session(request)
            
            if not session_token:
                logger.warning(f"CSRF validation failed: No session token for {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing. Please refresh the page and try again."}
                )
            
            # Get token from request
            request_token = self.csrf.get_token_from_request(request)
            
            # If not in header, try to get from form data
            if not request_token:
                try:
                    # Check if content type is form data
                    content_type = request.headers.get("content-type", "")
                    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                        form = await request.form()
                        request_token = form.get("csrf_token")
                except Exception as e:
                    logger.debug(f"Could not parse form data for CSRF token: {e}")
            
            # Validate token
            if not self.csrf.validate_token(request_token, session_token):
                logger.warning(f"CSRF validation failed: Token mismatch for {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token invalid. Please refresh the page and try again."}
                )
        
        return await call_next(request)


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Features:
    - Configurable limits per endpoint
    - IP-based and user-based limiting
    - Sliding window for smooth rate limiting
    - Automatic cleanup of old entries
    """
    
    def __init__(self):
        """Initialize rate limiter with default settings."""
        # Store: {key: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Cleanup every 60 seconds
    
    def _get_client_key(self, request: Request, endpoint: str = "") -> str:
        """
        Generate a unique key for the client.
        
        Args:
            request: FastAPI request object
            endpoint: Optional endpoint identifier
            
        Returns:
            Unique client key
        """
        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include endpoint in key for per-endpoint limiting
        if endpoint:
            return f"{client_ip}:{endpoint}"
        return client_ip
    
    def _cleanup_old_entries(self, window_seconds: int) -> None:
        """
        Remove entries older than the window.
        
        Args:
            window_seconds: Time window in seconds
        """
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        cutoff = current_time - window_seconds
        
        keys_to_delete = []
        for key, timestamps in self._requests.items():
            # Remove old timestamps
            self._requests[key] = [ts for ts in timestamps if ts > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)
        
        # Remove empty keys
        for key in keys_to_delete:
            del self._requests[key]
    
    def is_rate_limited(
        self,
        request: Request,
        limit: int,
        window_seconds: int,
        endpoint: str = ""
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request should be rate limited.
        
        Args:
            request: FastAPI request object
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            endpoint: Optional endpoint identifier
            
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_time = time.time()
        client_key = self._get_client_key(request, endpoint)
        
        # Cleanup old entries periodically
        self._cleanup_old_entries(window_seconds)
        
        # Get timestamps within window
        cutoff = current_time - window_seconds
        valid_requests = [ts for ts in self._requests[client_key] if ts > cutoff]
        
        # Calculate remaining requests
        request_count = len(valid_requests)
        remaining = max(0, limit - request_count)
        reset_time = int(cutoff + window_seconds)
        
        rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "window": window_seconds
        }
        
        if request_count >= limit:
            logger.warning(f"Rate limit exceeded for {client_key}: {request_count}/{limit}")
            return True, rate_limit_info
        
        # Record this request
        self._requests[client_key].append(current_time)
        rate_limit_info["remaining"] = remaining - 1
        
        return False, rate_limit_info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Implements different rate limits for different endpoints:
    - Default: 100 requests per minute
    - Auth endpoints: 5 requests per 5 minutes
    - API endpoints: 60 requests per minute
    """
    
    # Endpoint-specific rate limits: (limit, window_seconds)
    ENDPOINT_LIMITS = {
        "/api/v1/auth/login": (settings.RATE_LIMIT_AUTH, settings.RATE_LIMIT_AUTH_WINDOW),
        "/api/v1/auth/register": (settings.RATE_LIMIT_AUTH, settings.RATE_LIMIT_AUTH_WINDOW),
        "/api/v1/auth/forgot-password": (3, 300),  # 3 per 5 minutes
        "/submit": (30, 60),  # 30 per minute (for assessment submissions)
    }
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/static/",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(self, app: ASGIApp, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False
    
    def _get_limit_for_path(self, path: str) -> tuple[int, int]:
        """
        Get rate limit for a specific path.
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (limit, window_seconds)
        """
        # Check exact matches first
        if path in self.ENDPOINT_LIMITS:
            return self.ENDPOINT_LIMITS[path]
        
        # Check prefix matches
        for endpoint, limits in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return limits
        
        # Default limit
        return (settings.RATE_LIMIT_DEFAULT, settings.RATE_LIMIT_WINDOW)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler or rate limit error
        """
        # Skip if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        path = request.url.path
        
        # Skip exempt paths
        if self._is_exempt(path):
            return await call_next(request)
        
        # Get rate limit for this path
        limit, window = self._get_limit_for_path(path)
        
        # Check rate limit
        is_limited, info = self.limiter.is_rate_limited(
            request, limit, window, endpoint=path
        )
        
        if is_limited:
            retry_after = info["reset"] - int(time.time())
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"])
                }
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: Basic CSP
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        if not settings.SECURITY_HEADERS_ENABLED:
            return await call_next(request)
        
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Basic Content Security Policy
        # Note: Adjust based on your application's needs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self' blob:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


# =============================================================================
# Helper Functions
# =============================================================================

def get_csrf_token(request: Request) -> str:
    """
    Get or generate CSRF token for templates.
    
    Usage in Jinja2 templates:
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    
    Args:
        request: FastAPI request object
        
    Returns:
        CSRF token string
    """
    csrf = CSRFProtection()
    token = csrf.get_token_from_session(request)
    
    if not token:
        token = csrf.generate_token()
        csrf.set_token_in_session(request, token)
    
    return token


def csrf_protect(func: Callable) -> Callable:
    """
    Decorator for CSRF protection on individual routes.
    
    Usage:
        @router.post("/submit")
        @csrf_protect
        async def submit_form(request: Request):
            ...
    
    Args:
        func: Route handler function
        
    Returns:
        Wrapped function with CSRF protection
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not settings.CSRF_ENABLED:
            return await func(request, *args, **kwargs)
        
        csrf = CSRFProtection()
        session_token = csrf.get_token_from_session(request)
        
        if not session_token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing. Please refresh the page."
            )
        
        request_token = csrf.get_token_from_request(request)
        
        if not csrf.validate_token(request_token, session_token):
            raise HTTPException(
                status_code=403,
                detail="CSRF token invalid. Please refresh the page."
            )
        
        return await func(request, *args, **kwargs)
    
    return wrapper


# Global instances for easy access
csrf_protection = CSRFProtection()
rate_limiter = RateLimiter()
