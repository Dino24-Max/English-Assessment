"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Cruise Employee English Assessment Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Security - REQUIRED environment variables (no defaults for security)
    SECRET_KEY: str  # Must be set via environment variable
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:8000", "http://127.0.0.1:8080"]

    # Database - REQUIRED environment variable (no default for security)
    DATABASE_URL: str  # Must be set via environment variable

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """Return database URL for SQLAlchemy"""
        return self.DATABASE_URL

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 20  # Number of connections to maintain in the pool
    DB_MAX_OVERFLOW: int = 10  # Maximum number of connections to create beyond pool_size
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait before giving up on getting a connection
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour (prevents stale connections)
    DB_POOL_PRE_PING: bool = True  # Test connections before using them
    DB_ECHO: bool = False  # Log all SQL statements (override with DEBUG if needed)

    # AI Services
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # AI Service Configuration
    AI_TIMEOUT_SECONDS: int = 30  # Timeout for AI API calls
    AI_RETRY_ATTEMPTS: int = 3  # Number of retry attempts
    AI_RETRY_DELAY: float = 1.0  # Initial retry delay in seconds

    # Assessment Settings
    LISTENING_DURATION_SECONDS: int = 40
    SPEAKING_MAX_DURATION_SECONDS: int = 20
    TIME_NUMBERS_DURATION_SECONDS: int = 10

    # Question Bank Settings
    TOTAL_QUESTIONS_PER_MODULE: int = 40
    QUESTIONS_PER_DIVISION: int = 3  # Hotel, Marine, Casino
    TOTAL_SPEAKING_SCENARIOS: int = 10

    # Scoring
    PASS_THRESHOLD_TOTAL: int = 70
    PASS_THRESHOLD_SAFETY: float = 0.8
    PASS_THRESHOLD_SPEAKING: int = 12

    # File Storage
    AUDIO_UPLOAD_DIR: str = "data/audio"
    STATIC_FILES_DIR: str = "static"

    # Redis (for caching and sessions)
    REDIS_URL: str = "redis://localhost:6379"

    # Session Management
    SESSION_COOKIE_NAME: str = "assessment_session_id"
    SESSION_TIMEOUT_SECONDS: int = 14400  # 4 hours
    SESSION_WARNING_SECONDS: int = 300  # 5 minutes
    SESSION_SECURE_COOKIE: bool = os.getenv("SESSION_SECURE_COOKIE", "false").lower() == "true"
    SESSION_ROTATION_INTERVAL: int = 1800  # 30 minutes

    # Celery (for background tasks)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security Settings
    CSRF_ENABLED: bool = True
    CSRF_TOKEN_LENGTH: int = 32
    CSRF_COOKIE_SECURE: bool = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 100  # requests per window
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_AUTH: int = 5  # login attempts per window
    RATE_LIMIT_AUTH_WINDOW: int = 300  # 5 minutes

    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    SECURITY_HEADERS_ENABLED: bool = True
    INPUT_VALIDATION_ENABLED: bool = True

    # Admin API Key for question bank management
    ADMIN_API_KEY: str = "admin123"  # Default admin key for demo/development

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra environment variables


# Create settings instance
settings = Settings()

# Ensure directories exist
Path(settings.AUDIO_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.STATIC_FILES_DIR).mkdir(parents=True, exist_ok=True)