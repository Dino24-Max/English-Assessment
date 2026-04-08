"""
Cruise Employee English Assessment Platform
Main FastAPI application entry point
"""

import os
import traceback
import uvicorn
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from sqlalchemy import text
from core.database import engine, Base
from api.routes import assessment, admin, analytics, ui, auth
from core.config import settings
from core.logging_config import setup_logging
from core.security import (
    CSRFMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    get_csrf_token
)

# Setup logging first, before any other imports that might log
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    from utils.cache import cache_manager
    
    # Initialize database - import all models so they register with Base.metadata before create_all
    import models.assessment  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add InvitationCode columns if missing (model was extended)
        migrations = [
            ("first_name", "VARCHAR(100)"),
            ("last_name", "VARCHAR(100)"),
            ("nationality", "VARCHAR(100)"),
            ("assessment_completed", "INTEGER DEFAULT 0"),
        ]
        for col, col_type in migrations:
            try:
                await conn.execute(text(
                    f"ALTER TABLE invitation_codes ADD COLUMN {col} {col_type}"
                ))
                logger.info(f"Added column invitation_codes.{col}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    pass
                else:
                    raise

        # Migration: add questions.cefr_level if missing (CEFR per department bank)
        try:
            await conn.execute(text(
                "ALTER TABLE questions ADD COLUMN cefr_level VARCHAR(2)"
            ))
            logger.info("Added column questions.cefr_level")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                pass
            else:
                raise

        # Migration: add assessments.department if missing (record question pool used)
        try:
            await conn.execute(text(
                "ALTER TABLE assessments ADD COLUMN department VARCHAR(100)"
            ))
            logger.info("Added column assessments.department")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                pass
            else:
                raise

        # Migration: add assessments.question_order if missing (department-specific question IDs)
        try:
            await conn.execute(text(
                "ALTER TABLE assessments ADD COLUMN question_order TEXT"
            ))
            logger.info("Added column assessments.question_order")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                pass
            else:
                raise

    # Ensure default admin exists
    from sqlalchemy import select
    from core.database import async_session_maker
    from models.assessment import User, DivisionType
    from utils.auth import hash_password

    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@carnival.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    if not admin_password:
        if os.getenv("DEBUG", "false").lower() == "true":
            admin_password = "admin123"
            logger.warning("Using default admin password - set DEFAULT_ADMIN_PASSWORD in production")
        else:
            admin_password = None
            logger.info("No DEFAULT_ADMIN_PASSWORD set - skipping default admin creation")

    if admin_password:
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.email == admin_email))
            admin_user = result.scalar_one_or_none()
            if admin_user:
                admin_user.is_admin = True
                admin_user.password_hash = hash_password(admin_password)
                await db.commit()
                logger.info(f"Updated existing user {admin_email} to admin")
            else:
                admin_user = User(
                    first_name="Admin",
                    last_name="User",
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    nationality="Admin",
                    division=DivisionType.HOTEL,
                    department="Admin",
                    is_active=True,
                    is_admin=True,
                )
                db.add(admin_user)
                await db.commit()
                await db.refresh(admin_user)
                logger.info(f"Created default admin: {admin_email}")

    # Auto-load question bank when empty or incomplete
    from models.assessment import Question, ModuleType
    from sqlalchemy import func
    from data.question_bank_loader import QuestionBankLoader

    MINIMUM_EXPECTED_QUESTIONS = 100

    async with async_session_maker() as db:
        r = await db.execute(select(func.count()).select_from(Question))
        question_count = r.scalar() or 0

        needs_reload = False
        if question_count == 0:
            needs_reload = True
            logger.info("Question bank is empty – will auto-load.")
        elif question_count < MINIMUM_EXPECTED_QUESTIONS:
            r_speaking = await db.execute(
                select(func.count()).select_from(Question).where(
                    Question.module_type == ModuleType.SPEAKING.value
                )
            )
            speaking_count = r_speaking.scalar() or 0
            if speaking_count == 0:
                needs_reload = True
                logger.warning(
                    "Question bank incomplete (%d questions, 0 speaking) – will reload.",
                    question_count,
                )
            else:
                logger.info("Question bank has %d questions (%d speaking) – OK.", question_count, speaking_count)

        if needs_reload:
            data_dir = Path(__file__).parent / "data"
            full_path = data_dir / "question_bank_full.json"
            sample_path = data_dir / "question_bank_sample.json"
            json_path = str(full_path) if full_path.exists() else (str(sample_path) if sample_path.exists() else None)
            if json_path:
                try:
                    loader = QuestionBankLoader(db)
                    count = await loader.load_full_question_bank(json_file_path=json_path, clear_first=True)
                    logger.info(f"Auto-loaded question bank: {count} questions from {Path(json_path).name}")
                except Exception as e:
                    logger.warning(f"Auto-load question bank failed (non-fatal): {e}")
            else:
                logger.warning("Question bank empty and no question_bank_full.json or question_bank_sample.json found; load via Admin API when ready.")
        else:
            if question_count > 0:
                logger.info("Question bank already loaded: %d questions.", question_count)

    # Initialize Redis cache
    await cache_manager.connect()
    
    yield
    
    # Shutdown
    await cache_manager.disconnect()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Cruise Employee English Assessment Platform",
        description="AI-powered English proficiency testing for cruise ship employees",
        version="1.0.0",
        lifespan=lifespan
    )

    # Security: Validate SECRET_KEY
    if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
        logger.error("SECRET_KEY is not configured. This is a security risk!")
        raise ValueError("SECRET_KEY must be set in production environment")

    # Middleware order matters! In Starlette, last added = outermost (processed first).
    # Desired request flow: Session → CSRF → RateLimit → SecurityHeaders → CORS → App

    # CORS middleware (innermost of security chain)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "X-CSRF-Token"],
        expose_headers=["Content-Type", "Content-Length", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        max_age=3600,
    )
    
    # Security Headers middleware
    if settings.SECURITY_HEADERS_ENABLED:
        app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate Limiting middleware
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
        logger.info("Rate limiting middleware enabled")
    
    # CSRF Protection middleware
    if settings.CSRF_ENABLED:
        app.add_middleware(CSRFMiddleware)
        logger.info("CSRF protection middleware enabled")

    # Session middleware (added LAST = outermost = processed first on request)
    # This ensures request.session is available to all inner middleware (CSRF, etc.)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600 * 24 * 7,  # 7 days
        same_site="lax",
        https_only=not settings.DEBUG,
    )

    # Static files - Ensure directories exist
    python_src_dir = Path(__file__).parent
    static_dir = python_src_dir / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)
    (static_dir / "audio").mkdir(exist_ok=True)
    (static_dir / "images").mkdir(exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # UI routes (frontend pages)
    app.include_router(ui.router, tags=["UI"])

    # API routes (backend endpoints)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(assessment.router, prefix="/api/v1/assessment", tags=["Assessment"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

    @app.get("/api")
    async def api_root():
        return {
            "message": "Cruise Employee English Assessment Platform API",
            "version": "1.0.0",
            "status": "operational",
            "endpoints": {
                "assessment": "/api/v1/assessment",
                "admin": "/api/v1/admin",
                "analytics": "/api/v1/analytics"
            }
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "database": "connected"}

    # Global handler to log full traceback for unhandled exceptions (excluding HTTPException)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc  # Let FastAPI handle HTTPException
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb = "".join(tb_lines)
        logger.error(f"Unhandled exception: {exc}\n{tb}", exc_info=True)
        for base in [Path(__file__).resolve().parent, Path(__file__).resolve().parents[2], Path.cwd()]:
            try:
                fpath = base / "unhandled_error_traceback.txt"
                fpath.write_text(f"Error: {exc}\n\n{tb}", encoding="utf-8")
                logger.info(f"Traceback written to {fpath}")
                break
            except Exception as we:
                logger.warning(f"Could not write traceback to {base}: {we}")
        # Always include traceback in response when UnboundLocalError (debugging)
        include_tb = settings.DEBUG or "UnboundLocalError" in type(exc).__name__
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb if include_tb else None}
        )

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Cruise Employee English Assessment Platform")
    logger.info("=" * 60)
    logger.info(f"Server running at: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Health check: http://{settings.HOST}:{settings.PORT}/health")
    logger.info(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)
    logger.info("Press CTRL+C to stop the server")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )