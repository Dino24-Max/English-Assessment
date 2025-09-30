"""
Security Middleware for FastAPI
Provides comprehensive security features including CSRF protection, rate limiting,
input validation, and security headers
"""

import secrets
import hashlib
import time
import re
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration settings"""

    # CSRF Protection
    CSRF_TOKEN_LENGTH: int = 32
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_COOKIE_SECURE: bool = False  # Set True in production with HTTPS
    CSRF_COOKIE_HTTPONLY: bool = False  # Must be False so JS can read it
    CSRF_COOKIE_SAMESITE: str = "lax"
    CSRF_COOKIE_MAX_AGE: int = 3600 * 8  # 8 hours
    CSRF_EXEMPT_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}
    CSRF_EXEMPT_PATHS: List[str] = ["/api/health", "/health", "/api/docs", "/docs", "/openapi.json"]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REDIS_PREFIX: str = "rate_limit:"

    # Default rate limits (requests per window)
    RATE_LIMIT_DEFAULT: int = 100  # 100 requests
    RATE_LIMIT_WINDOW: int = 60  # per 60 seconds

    # Endpoint-specific rate limits
    RATE_LIMIT_AUTH: int = 5  # Login attempts
    RATE_LIMIT_AUTH_WINDOW: int = 300  # per 5 minutes

    RATE_LIMIT_API: int = 60  # API calls
    RATE_LIMIT_API_WINDOW: int = 60  # per minute

    RATE_LIMIT_UPLOAD: int = 10  # File uploads
    RATE_LIMIT_UPLOAD_WINDOW: int = 3600  # per hour

    # Rate limit response
    RATE_LIMIT_STATUS_CODE: int = 429
    RATE_LIMIT_MESSAGE: str = "Rate limit exceeded. Please try again later."

    # Input Validation
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_JSON_SIZE: int = 1 * 1024 * 1024  # 1MB
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB for audio files

    # Security patterns
    XSS_PATTERNS: List[str] = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
        r"eval\(",
        r"expression\(",
    ]

    SQL_INJECTION_PATTERNS: List[str] = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--\s)",
        r"(/\*.*\*/)",
        r"(\bEXEC\b|\bEXECUTE\b)",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS: List[str] = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"%252e%252e",
    ]

    # Security Headers
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    # Trusted IPs (for rate limit bypass)
    TRUSTED_IPS: List[str] = ["127.0.0.1", "::1"]


class CSRFProtection:
    """CSRF token generation and validation"""

    def __init__(self):
        self.config = SecurityConfig()

    def generate_token(self) -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(self.config.CSRF_TOKEN_LENGTH)

    def is_exempt(self, method: str, path: str) -> bool:
        """Check if request is exempt from CSRF protection"""
        # Exempt safe methods
        if method.upper() in self.config.CSRF_EXEMPT_METHODS:
            return True

        # Exempt specific paths
        for exempt_path in self.config.CSRF_EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True

        return False

    def validate_token(self, request_token: Optional[str], cookie_token: Optional[str]) -> bool:
        """Validate CSRF token"""
        if not request_token or not cookie_token:
            return False

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(request_token, cookie_token)


class RateLimiter:
    """Redis-based rate limiting"""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        self.config = SecurityConfig()
        self.local_cache: Dict[str, Dict[str, Any]] = {}  # Fallback if Redis unavailable

    async def connect(self):
        """Connect to Redis"""
        if self.redis_client is None:
            try:
                self.redis_client = await redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis connection failed, using local cache: {e}")

    async def is_rate_limited(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if identifier is rate limited
        Returns: (is_limited, rate_limit_info)
        """
        try:
            if self.redis_client:
                return await self._redis_rate_limit(identifier, max_requests, window_seconds)
            else:
                return await self._local_rate_limit(identifier, max_requests, window_seconds)
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False, {}  # Fail open on error

    async def _redis_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, Dict[str, Any]]:
        """Redis-based rate limiting using sliding window"""
        key = f"{self.config.RATE_LIMIT_REDIS_PREFIX}{identifier}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, window_seconds)

            results = await pipe.execute()
            current_requests = results[1]

            # Calculate rate limit info
            is_limited = current_requests >= max_requests
            remaining = max(0, max_requests - current_requests - 1)
            reset_time = int(now + window_seconds)

            rate_limit_info = {
                "limit": max_requests,
                "remaining": remaining,
                "reset": reset_time,
                "retry_after": window_seconds if is_limited else 0
            }

            return is_limited, rate_limit_info

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            return False, {}

    async def _local_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, Dict[str, Any]]:
        """Local memory-based rate limiting (fallback)"""
        now = time.time()
        window_start = now - window_seconds

        if identifier not in self.local_cache:
            self.local_cache[identifier] = {"requests": [], "last_cleanup": now}

        cache_entry = self.local_cache[identifier]

        # Cleanup old entries periodically
        if now - cache_entry["last_cleanup"] > 60:
            cache_entry["requests"] = [
                req_time for req_time in cache_entry["requests"]
                if req_time > window_start
            ]
            cache_entry["last_cleanup"] = now

        # Filter requests in current window
        recent_requests = [
            req_time for req_time in cache_entry["requests"]
            if req_time > window_start
        ]

        is_limited = len(recent_requests) >= max_requests

        if not is_limited:
            cache_entry["requests"].append(now)

        rate_limit_info = {
            "limit": max_requests,
            "remaining": max(0, max_requests - len(recent_requests) - 1),
            "reset": int(now + window_seconds),
            "retry_after": window_seconds if is_limited else 0
        }

        return is_limited, rate_limit_info

    def get_rate_limit_for_path(self, path: str) -> tuple[int, int]:
        """Get rate limit settings for specific path"""
        # Authentication endpoints
        if "/auth/" in path or "/login" in path:
            return self.config.RATE_LIMIT_AUTH, self.config.RATE_LIMIT_AUTH_WINDOW

        # Upload endpoints
        if "/upload" in path or "/audio" in path:
            return self.config.RATE_LIMIT_UPLOAD, self.config.RATE_LIMIT_UPLOAD_WINDOW

        # API endpoints
        if path.startswith("/api/"):
            return self.config.RATE_LIMIT_API, self.config.RATE_LIMIT_API_WINDOW

        # Default rate limit
        return self.config.RATE_LIMIT_DEFAULT, self.config.RATE_LIMIT_WINDOW


class InputValidator:
    """Input validation and sanitization"""

    def __init__(self):
        self.config = SecurityConfig()
        self.xss_pattern = re.compile("|".join(self.config.XSS_PATTERNS), re.IGNORECASE)
        self.sql_pattern = re.compile("|".join(self.config.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.path_pattern = re.compile("|".join(self.config.PATH_TRAVERSAL_PATTERNS), re.IGNORECASE)

    def validate_request_size(self, content_length: Optional[int], path: str) -> bool:
        """Validate request size based on endpoint"""
        if content_length is None:
            return True

        # Upload endpoints have higher limits
        if "/upload" in path or "/audio" in path:
            return content_length <= self.config.MAX_UPLOAD_SIZE

        # JSON endpoints
        if "application/json" in path or "/api/" in path:
            return content_length <= self.config.MAX_JSON_SIZE

        # Default limit
        return content_length <= self.config.MAX_REQUEST_SIZE

    def check_xss(self, value: str) -> bool:
        """Check for XSS patterns"""
        if not value:
            return True
        return not self.xss_pattern.search(value)

    def check_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns"""
        if not value:
            return True
        return not self.sql_pattern.search(value)

    def check_path_traversal(self, value: str) -> bool:
        """Check for path traversal patterns"""
        if not value:
            return True
        return not self.path_pattern.search(value)

    def validate_string(self, value: str, check_xss: bool = True, check_sql: bool = True) -> bool:
        """Validate string input"""
        if not isinstance(value, str):
            return False

        if check_xss and not self.check_xss(value):
            logger.warning(f"XSS pattern detected in input")
            return False

        if check_sql and not self.check_sql_injection(value):
            logger.warning(f"SQL injection pattern detected in input")
            return False

        if not self.check_path_traversal(value):
            logger.warning(f"Path traversal pattern detected in input")
            return False

        return True

    def sanitize_string(self, value: str) -> str:
        """Sanitize string input by removing dangerous patterns"""
        if not value:
            return value

        # Remove HTML tags
        value = re.sub(r"<[^>]*>", "", value)

        # Remove SQL comments
        value = re.sub(r"--.*$", "", value, flags=re.MULTILINE)
        value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)

        # Remove path traversal
        value = value.replace("../", "").replace("..\\", "")

        return value


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    def __init__(self, app):
        super().__init__(app)
        self.config = SecurityConfig()

    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to response"""
        response = await call_next(request)

        # Add security headers
        for header_name, header_value in self.config.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # Add custom headers
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", secrets.token_hex(16))

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""

    def __init__(self, app):
        super().__init__(app)
        self.csrf = CSRFProtection()
        self.config = SecurityConfig()

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate CSRF token for unsafe methods"""

        # Check if request is exempt
        if self.csrf.is_exempt(request.method, request.url.path):
            response = await call_next(request)

            # Set CSRF token cookie for exempt requests
            csrf_token = request.cookies.get(self.config.CSRF_COOKIE_NAME)
            if not csrf_token:
                csrf_token = self.csrf.generate_token()
                response.set_cookie(
                    key=self.config.CSRF_COOKIE_NAME,
                    value=csrf_token,
                    max_age=self.config.CSRF_COOKIE_MAX_AGE,
                    secure=self.config.CSRF_COOKIE_SECURE,
                    httponly=self.config.CSRF_COOKIE_HTTPONLY,
                    samesite=self.config.CSRF_COOKIE_SAMESITE
                )

            return response

        # Validate CSRF token for unsafe methods
        cookie_token = request.cookies.get(self.config.CSRF_COOKIE_NAME)
        request_token = request.headers.get(self.config.CSRF_HEADER_NAME)

        if not self.csrf.validate_token(request_token, cookie_token):
            logger.warning(
                f"CSRF validation failed for {request.method} {request.url.path} "
                f"from {request.client.host}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed"
            )

        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, redis_client: Optional[Redis] = None):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client)
        self.config = SecurityConfig()

    async def dispatch(self, request: Request, call_next: Callable):
        """Apply rate limiting"""

        if not self.config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for trusted IPs
        client_ip = request.client.host
        if client_ip in self.config.TRUSTED_IPS:
            return await call_next(request)

        # Get rate limit for this path
        max_requests, window_seconds = self.rate_limiter.get_rate_limit_for_path(
            request.url.path
        )

        # Create identifier (IP + user_id if available)
        identifier = client_ip
        if hasattr(request.state, "session") and request.state.session:
            user_id = request.state.session.get("user_id")
            if user_id:
                identifier = f"{client_ip}:{user_id}"

        # Check rate limit
        is_limited, rate_info = await self.rate_limiter.is_rate_limited(
            identifier,
            max_requests,
            window_seconds
        )

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.url.path}"
            )
            raise HTTPException(
                status_code=self.config.RATE_LIMIT_STATUS_CODE,
                detail=self.config.RATE_LIMIT_MESSAGE,
                headers={
                    "Retry-After": str(rate_info.get("retry_after", window_seconds)),
                    "X-RateLimit-Limit": str(rate_info.get("limit", max_requests)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info.get("reset", 0))
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if rate_info:
            response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", max_requests))
            response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset", 0))

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation middleware"""

    def __init__(self, app):
        super().__init__(app)
        self.validator = InputValidator()
        self.config = SecurityConfig()

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate request inputs"""

        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length = int(content_length)
                if not self.validator.validate_request_size(content_length, request.url.path):
                    logger.warning(
                        f"Request size exceeded for {request.url.path}: {content_length} bytes"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request size exceeds maximum allowed"
                    )
            except ValueError:
                pass

        # Validate query parameters
        for key, value in request.query_params.items():
            if not self.validator.validate_string(str(value)):
                logger.warning(
                    f"Suspicious query parameter detected: {key}={value[:100]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid query parameter detected"
                )

        # Validate path parameters
        if not self.validator.check_path_traversal(str(request.url.path)):
            logger.warning(f"Path traversal attempt detected: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path"
            )

        response = await call_next(request)
        return response


# Utility functions for route-level security

def require_csrf(func):
    """Decorator to require CSRF token validation"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        csrf = CSRFProtection()
        config = SecurityConfig()

        cookie_token = request.cookies.get(config.CSRF_COOKIE_NAME)
        request_token = request.headers.get(config.CSRF_HEADER_NAME)

        if not csrf.validate_token(request_token, cookie_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed"
            )

        return await func(request, *args, **kwargs)

    return wrapper


def rate_limit(max_requests: int, window_seconds: int):
    """Decorator for custom rate limiting on specific routes"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = RateLimiter()
            await rate_limiter.connect()

            identifier = request.client.host
            is_limited, rate_info = await rate_limiter.is_rate_limited(
                identifier,
                max_requests,
                window_seconds
            )

            if is_limited:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(rate_info.get("retry_after", window_seconds))}
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def validate_input(check_xss: bool = True, check_sql: bool = True):
    """Decorator for input validation on specific routes"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            validator = InputValidator()

            # Validate query parameters
            for key, value in request.query_params.items():
                if not validator.validate_string(str(value), check_xss, check_sql):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid input in parameter: {key}"
                    )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# Helper function to get CSRF token
async def get_csrf_token(request: Request) -> str:
    """Get or generate CSRF token for current request"""
    config = SecurityConfig()
    csrf = CSRFProtection()

    token = request.cookies.get(config.CSRF_COOKIE_NAME)
    if not token:
        token = csrf.generate_token()

    return token
