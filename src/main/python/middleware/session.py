"""
Session Management Middleware for FastAPI
Provides secure session handling with encryption, timeout management, and assessment tracking
"""

import secrets
import json
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class SessionConfig:
    """Session configuration settings"""

    # Session cookie settings
    COOKIE_NAME: str = "assessment_session_id"
    COOKIE_MAX_AGE: int = 3600 * 4  # 4 hours
    COOKIE_SECURE: bool = False  # Set to True in production with HTTPS
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_PATH: str = "/"

    # Session timeout settings
    SESSION_TIMEOUT_SECONDS: int = 3600 * 4  # 4 hours of inactivity
    SESSION_WARNING_SECONDS: int = 300  # 5 minutes warning before timeout

    # Assessment specific timeouts
    ASSESSMENT_ACTIVE_TIMEOUT: int = 7200  # 2 hours max for active assessment
    ASSESSMENT_PAUSE_TIMEOUT: int = 1800  # 30 minutes when paused

    # Session security
    SESSION_ROTATION_INTERVAL: int = 1800  # Rotate session ID every 30 minutes
    MAX_SESSIONS_PER_USER: int = 3

    # Redis settings
    REDIS_KEY_PREFIX: str = "session:"
    REDIS_KEY_TTL: int = COOKIE_MAX_AGE


class SessionEncryption:
    """Handles encryption/decryption of session data"""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize encryption with secret key"""
        if secret_key is None:
            secret_key = settings.SECRET_KEY

        # Generate Fernet key from secret
        self.key = self._generate_fernet_key(secret_key)
        self.cipher = Fernet(self.key)

    @staticmethod
    def _generate_fernet_key(secret: str) -> bytes:
        """Generate Fernet-compatible key from secret string"""
        import hashlib
        import base64
        # Use SHA256 to get 32 bytes, then base64 encode for Fernet
        hash_digest = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(hash_digest)

    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt session data"""
        try:
            json_data = json.dumps(data)
            encrypted = self.cipher.encrypt(json_data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Session encryption error: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt session data"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Session decryption error: {e}")
            raise


class SessionStore:
    """Redis-based session storage with encryption"""

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize session store"""
        self.redis_client = redis_client
        self.encryption = SessionEncryption()
        self.config = SessionConfig()

    async def connect(self):
        """Connect to Redis"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    def _get_redis_key(self, session_id: str) -> str:
        """Get Redis key for session"""
        return f"{self.config.REDIS_KEY_PREFIX}{session_id}"

    async def create_session(self, user_id: Optional[str] = None) -> str:
        """Create new session and return session ID"""
        session_id = secrets.token_urlsafe(32)

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "data": {},
            "assessment": {
                "active": False,
                "assessment_id": None,
                "started_at": None,
                "current_module": None,
                "paused": False
            }
        }

        await self.save_session(session_id, session_data)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        try:
            if not self.redis_client:
                await self.connect()

            redis_key = self._get_redis_key(session_id)
            encrypted_data = await self.redis_client.get(redis_key)

            if not encrypted_data:
                return None

            session_data = self.encryption.decrypt(encrypted_data)

            # Check if session has expired
            if self._is_session_expired(session_data):
                await self.delete_session(session_id)
                return None

            return session_data

        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

    async def save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data"""
        try:
            if not self.redis_client:
                await self.connect()

            # Update last activity
            session_data["last_activity"] = datetime.utcnow().isoformat()

            # Encrypt and store
            encrypted_data = self.encryption.encrypt(session_data)
            redis_key = self._get_redis_key(session_id)

            await self.redis_client.setex(
                redis_key,
                self.config.REDIS_KEY_TTL,
                encrypted_data
            )

        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
            raise

    async def delete_session(self, session_id: str):
        """Delete session"""
        try:
            if not self.redis_client:
                await self.connect()

            redis_key = self._get_redis_key(session_id)
            await self.redis_client.delete(redis_key)

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update specific session fields"""
        session_data = await self.get_session(session_id)
        if session_data:
            session_data["data"].update(updates)
            await self.save_session(session_id, session_data)

    async def extend_session(self, session_id: str):
        """Extend session TTL"""
        try:
            if not self.redis_client:
                await self.connect()

            redis_key = self._get_redis_key(session_id)
            await self.redis_client.expire(redis_key, self.config.REDIS_KEY_TTL)

        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")

    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if session has expired based on last activity"""
        try:
            last_activity = datetime.fromisoformat(session_data["last_activity"])
            time_since_activity = (datetime.utcnow() - last_activity).total_seconds()

            # Check assessment-specific timeouts
            if session_data.get("assessment", {}).get("active"):
                if session_data["assessment"].get("paused"):
                    return time_since_activity > self.config.ASSESSMENT_PAUSE_TIMEOUT
                else:
                    return time_since_activity > self.config.ASSESSMENT_ACTIVE_TIMEOUT

            # Standard session timeout
            return time_since_activity > self.config.SESSION_TIMEOUT_SECONDS

        except Exception as e:
            logger.error(f"Error checking session expiration: {e}")
            return True

    async def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user"""
        try:
            if not self.redis_client:
                await self.connect()

            pattern = f"{self.config.REDIS_KEY_PREFIX}*"
            sessions = []

            async for key in self.redis_client.scan_iter(match=pattern):
                encrypted_data = await self.redis_client.get(key)
                if encrypted_data:
                    try:
                        session_data = self.encryption.decrypt(encrypted_data)
                        if session_data.get("user_id") == user_id:
                            sessions.append(session_data)
                    except:
                        continue

            return sessions

        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (called by background task)"""
        try:
            if not self.redis_client:
                await self.connect()

            pattern = f"{self.config.REDIS_KEY_PREFIX}*"
            cleaned = 0

            async for key in self.redis_client.scan_iter(match=pattern):
                encrypted_data = await self.redis_client.get(key)
                if encrypted_data:
                    try:
                        session_data = self.encryption.decrypt(encrypted_data)
                        if self._is_session_expired(session_data):
                            await self.redis_client.delete(key)
                            cleaned += 1
                    except:
                        continue

            logger.info(f"Cleaned up {cleaned} expired sessions")
            return cleaned

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0


class SessionMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for session management"""

    def __init__(self, app, redis_client: Optional[Redis] = None):
        super().__init__(app)
        self.session_store = SessionStore(redis_client)
        self.config = SessionConfig()

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and manage session"""

        # Get or create session
        session_id = request.cookies.get(self.config.COOKIE_NAME)
        session_data = None

        if session_id:
            session_data = await self.session_store.get_session(session_id)

        # Create new session if none exists or expired
        if not session_data:
            session_id = await self.session_store.create_session()
            session_data = await self.session_store.get_session(session_id)

        # Attach session to request state
        request.state.session_id = session_id
        request.state.session = session_data

        # Process request
        response = await call_next(request)

        # Save updated session
        if hasattr(request.state, "session_modified") and request.state.session_modified:
            await self.session_store.save_session(session_id, request.state.session)

        # Extend session TTL on activity
        await self.session_store.extend_session(session_id)

        # Set session cookie
        response.set_cookie(
            key=self.config.COOKIE_NAME,
            value=session_id,
            max_age=self.config.COOKIE_MAX_AGE,
            secure=self.config.COOKIE_SECURE,
            httponly=self.config.COOKIE_HTTPONLY,
            samesite=self.config.COOKIE_SAMESITE,
            path=self.config.COOKIE_PATH
        )

        return response


class Session:
    """Session helper class for request handlers"""

    def __init__(self, request: Request):
        self.request = request
        self.session_id = request.state.session_id
        self.data = request.state.session

    def get(self, key: str, default: Any = None) -> Any:
        """Get session value"""
        return self.data.get("data", {}).get(key, default)

    def set(self, key: str, value: Any):
        """Set session value"""
        if "data" not in self.data:
            self.data["data"] = {}
        self.data["data"][key] = value
        self.request.state.session_modified = True

    def delete(self, key: str):
        """Delete session value"""
        if "data" in self.data and key in self.data["data"]:
            del self.data["data"][key]
            self.request.state.session_modified = True

    def clear(self):
        """Clear all session data"""
        self.data["data"] = {}
        self.request.state.session_modified = True

    def get_user_id(self) -> Optional[str]:
        """Get user ID from session"""
        return self.data.get("user_id")

    def set_user_id(self, user_id: str):
        """Set user ID in session"""
        self.data["user_id"] = user_id
        self.request.state.session_modified = True

    def get_assessment_data(self) -> Dict[str, Any]:
        """Get assessment tracking data"""
        return self.data.get("assessment", {})

    def start_assessment(self, assessment_id: str, module: str):
        """Mark assessment as started"""
        self.data["assessment"] = {
            "active": True,
            "assessment_id": assessment_id,
            "started_at": datetime.utcnow().isoformat(),
            "current_module": module,
            "paused": False
        }
        self.request.state.session_modified = True

    def update_assessment_module(self, module: str):
        """Update current assessment module"""
        if "assessment" in self.data:
            self.data["assessment"]["current_module"] = module
            self.request.state.session_modified = True

    def pause_assessment(self):
        """Pause active assessment"""
        if "assessment" in self.data:
            self.data["assessment"]["paused"] = True
            self.data["assessment"]["paused_at"] = datetime.utcnow().isoformat()
            self.request.state.session_modified = True

    def resume_assessment(self):
        """Resume paused assessment"""
        if "assessment" in self.data:
            self.data["assessment"]["paused"] = False
            self.request.state.session_modified = True

    def end_assessment(self):
        """Mark assessment as completed"""
        self.data["assessment"] = {
            "active": False,
            "assessment_id": None,
            "started_at": None,
            "current_module": None,
            "paused": False
        }
        self.request.state.session_modified = True

    def is_assessment_active(self) -> bool:
        """Check if assessment is currently active"""
        return self.data.get("assessment", {}).get("active", False)

    def get_time_remaining(self) -> Optional[int]:
        """Get seconds remaining before timeout warning"""
        try:
            last_activity = datetime.fromisoformat(self.data["last_activity"])
            time_since_activity = (datetime.utcnow() - last_activity).total_seconds()

            config = SessionConfig()
            time_remaining = config.SESSION_TIMEOUT_SECONDS - time_since_activity

            return max(0, int(time_remaining))
        except:
            return None

    def needs_warning(self) -> bool:
        """Check if session timeout warning should be shown"""
        time_remaining = self.get_time_remaining()
        if time_remaining is None:
            return False
        return time_remaining <= SessionConfig.SESSION_WARNING_SECONDS


# Dependency for FastAPI routes
async def get_session(request: Request) -> Session:
    """FastAPI dependency to get session from request"""
    return Session(request)


# Background task for session cleanup
async def session_cleanup_task(session_store: SessionStore, interval_seconds: int = 3600):
    """Background task to clean up expired sessions"""
    import asyncio

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await session_store.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error
