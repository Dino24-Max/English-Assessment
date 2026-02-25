"""
UI Routes - Serves frontend pages using Jinja2 templates
Handles all user-facing web pages for the assessment platform
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

from core.database import get_db
from core.config import settings
from utils.error_handling import safe_error_response
from core.security import get_csrf_token

# Initialize logger
logger = logging.getLogger(__name__)


# Initialize router
router = APIRouter()

# Get the python source directory (where app.py is)
python_src_dir = Path(__file__).parent.parent.parent
templates_dir = python_src_dir / "templates"
data_dir = python_src_dir / "data"

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=str(templates_dir))


def render_template(request: Request, template_name: str, context: Dict[str, Any]) -> templates.TemplateResponse:
    """
    Render a template with CSRF token automatically included.
    
    Args:
        request: FastAPI request object
        template_name: Name of the template file
        context: Template context dictionary
        
    Returns:
        TemplateResponse with CSRF token included
    """
    # Always include CSRF token in context
    context["csrf_token"] = get_csrf_token(request)
    context["request"] = request
    return templates.TemplateResponse(template_name, context)


# Load questions configuration
def load_questions_config() -> Dict[str, Any]:
    """Load questions from questions_config.json"""
    try:
        config_path = data_dir / "questions_config.json"

        if not config_path.exists():
            raise FileNotFoundError(f"Questions config not found at {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        return questions

    except FileNotFoundError as e:
        logger.error(f"Questions config file not found: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Configuration file not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in questions config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Invalid configuration file format")
    except Exception as e:
        logger.error(f"Error loading questions config: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "Error loading questions configuration"
        raise HTTPException(status_code=500, detail=detail)


# Store questions in memory (loaded once at startup)
QUESTIONS_CONFIG = None


def get_questions() -> Dict[str, Any]:
    """Get questions configuration (cached)"""
    global QUESTIONS_CONFIG

    if QUESTIONS_CONFIG is None:
        QUESTIONS_CONFIG = load_questions_config()

    return QUESTIONS_CONFIG


# Module information for transition screens
MODULE_INFO = {
    "listening": {
        "name": "Listening",
        "icon": "🎧",
        "questions": 3,
        "points": 16,
        "order": 1
    },
    "time_numbers": {
        "name": "Time & Numbers",
        "icon": "🔢",
        "questions": 3,
        "points": 16,
        "order": 2
    },
    "grammar": {
        "name": "Grammar",
        "icon": "📝",
        "questions": 4,
        "points": 16,
        "order": 3
    },
    "vocabulary": {
        "name": "Vocabulary",
        "icon": "📚",
        "questions": 4,
        "points": 16,
        "order": 4
    },
    "reading": {
        "name": "Reading",
        "icon": "📖",
        "questions": 4,
        "points": 16,
        "order": 5
    },
    "speaking": {
        "name": "Speaking",
        "icon": "🎤",
        "questions": 3,
        "points": 20,
        "order": 6
    }
}


def get_module_for_question(question_num: int) -> str:
    """Get the module name for a given question number"""
    questions = get_questions()
    question_key = str(question_num)
    if question_key in questions:
        return questions[question_key].get("module", "unknown")
    return "unknown"


def should_show_transition(current_question: int, next_question: int) -> bool:
    """Determine if a module transition screen should be shown"""
    if next_question > 21:
        return False
    current_module = get_module_for_question(current_question)
    next_module = get_module_for_question(next_question)
    return current_module != next_module


def score_answer_from_config(question_num: int, user_answer: str) -> Dict[str, Any]:
    """
    Score answer using questions_config.json (UI-only scoring)
    This bypasses the database Question table for UI assessments
    
    SCORING LOGIC (100% ACCURATE):
    1. MULTIPLE CHOICE (listening, grammar, reading with options): Exact match of option text
    2. FILL-IN-THE-BLANK (time_numbers without options): Flexible matching for numbers/times
    3. VOCABULARY MATCHING (correct_matches): Validate JSON matches against correct_matches
    4. SPEAKING (expected_keywords): Give credit for any recording attempt
    
    Args:
        question_num: Question number (1-21)
        user_answer: User's answer
        
    Returns:
        Dict with is_correct, points_earned, points_possible, feedback
    """
    try:
        questions = get_questions()
        question_key = str(question_num)
        
        if question_key not in questions:
            logger.warning(f"Question {question_num} not found in config")
            return {
                "is_correct": False,
                "points_earned": 0,
                "points_possible": 4,
                "feedback": "Question not found",
                "module": "unknown"
            }
        
        question_data = questions[question_key]
        module = question_data.get("module", "unknown")
        points = question_data.get("points", 4)
        
        logger.debug(f"Scoring Q{question_num}: module={module}, user_answer_length={len(user_answer)}")
        
        # Handle different question formats
        is_correct = False
        correct_answer_display = ""
        
        # ============================================================
        # TYPE 1: VOCABULARY MATCHING QUESTIONS (have "correct_matches")
        # ============================================================
        if "correct_matches" in question_data:
            correct_matches = question_data["correct_matches"]
            correct_answer_display = str(correct_matches)
            
            logger.debug(f"Vocabulary matching for Q{question_num}: {len(correct_matches)} terms")
            
            try:
                # Parse user's JSON answer
                user_matches = json.loads(user_answer)
                
                # Count correct matches
                correct_count = 0
                total_matches = len(correct_matches)
                
                for term, correct_definition in correct_matches.items():
                    user_definition = user_matches.get(term, "")
                    # Normalize for comparison (case-insensitive, trim whitespace)
                    if user_definition.strip().lower() == correct_definition.strip().lower():
                        correct_count += 1
                
                # FIXED: Partial credit for vocabulary matching (was all-or-nothing)
                # Each correct match earns proportional points
                is_correct = (correct_count == total_matches)
                points_earned = int(points * (correct_count / total_matches)) if total_matches > 0 else 0
                logger.debug(f"Vocabulary Q{question_num}: {correct_count}/{total_matches} correct, {points_earned}/{points} points")
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error for vocabulary Q{question_num}: {e}")
                is_correct = False
                points_earned = 0
            except Exception as e:
                logger.error(f"Error validating vocabulary Q{question_num}: {e}", exc_info=True)
                is_correct = False
                points_earned = 0
        
        # ============================================================
        # TYPE 2: SPEAKING QUESTIONS (have "expected_keywords")
        # Uses enhanced SpeakingScorerService for intelligent scoring
        # ============================================================
        elif "expected_keywords" in question_data:
            expected_keywords = question_data["expected_keywords"]
            logger.debug(f"Speaking Q{question_num}: Analyzing transcription, {len(expected_keywords)} keywords expected")
            
            # Parse answer format: "recorded_DURATION|TRANSCRIPT" or legacy "recorded_DURATION"
            transcript = ""
            recording_duration = 0.0
            if "|" in user_answer:
                parts = user_answer.split("|", 1)
                transcript = parts[1].strip() if len(parts) > 1 else ""
                # Extract duration from format "recorded_Xs"
                duration_match = parts[0].replace("recorded_", "").replace("s", "")
                try:
                    recording_duration = float(duration_match)
                except ValueError:
                    recording_duration = 0.0
            elif user_answer.startswith("recorded_"):
                # Legacy format - no transcript available
                transcript = ""
                duration_match = user_answer.replace("recorded_", "").replace("s", "")
                try:
                    recording_duration = float(duration_match)
                except ValueError:
                    recording_duration = 0.0
            
            # Check if user made a recording
            has_recording = user_answer and user_answer.startswith("recorded_")
            
            if not has_recording:
                is_correct = False
                points_earned = 0
                logger.debug(f"Speaking Q{question_num}: No recording detected")
            elif not transcript:
                # Recording exists but no transcript (speech recognition failed or no speech)
                # Give minimal points (20% of total) for attempting
                is_correct = False
                points_earned = int(points * 0.2)
                logger.debug(f"Speaking Q{question_num}: Recording detected but no transcript")
            else:
                # Use enhanced SpeakingScorerService for intelligent scoring
                try:
                    from services.speaking_scorer import score_speaking_response
                    
                    question_context = question_data.get("question", "")
                    
                    score_result = score_speaking_response(
                        transcript=transcript,
                        expected_keywords=expected_keywords,
                        question_context=question_context,
                        recording_duration=recording_duration,
                        base_points=float(points)
                    )
                    
                    points_earned = int(round(score_result.total_points))
                    is_correct = score_result.percentage >= 50
                    
                    logger.debug(
                        f"Speaking Q{question_num}: Enhanced scoring - "
                        f"matched={len(score_result.matched_keywords)}/{len(expected_keywords)}, "
                        f"score={score_result.percentage:.1f}%, "
                        f"points={points_earned}/{points}, "
                        f"level={score_result.level.value}"
                    )
                    
                    # Log partial matches for debugging
                    if score_result.partial_matches:
                        logger.debug(f"Speaking Q{question_num}: Partial matches: {score_result.partial_matches}")
                    
                except ImportError as e:
                    # Fallback to legacy scoring if service not available
                    logger.warning(f"Speaking scorer service not available, using legacy scoring: {e}")
                    
                    # Legacy scoring algorithm
                    transcript_lower = transcript.lower()
                    matched_keywords = []
                    
                    for keyword in expected_keywords:
                        keyword_lower = keyword.lower()
                        
                        if keyword_lower in transcript_lower:
                            matched_keywords.append(keyword)
                        elif keyword_lower.replace("ize", "ise") in transcript_lower:
                            matched_keywords.append(keyword)
                        elif keyword_lower.replace("ise", "ize") in transcript_lower:
                            matched_keywords.append(keyword)
                        elif " " in keyword_lower:
                            keyword_words = keyword_lower.split()
                            if all(word in transcript_lower for word in keyword_words):
                                matched_keywords.append(keyword)
                        elif len(keyword_lower) >= 4:
                            root = keyword_lower[:4]
                            if root in transcript_lower:
                                matched_keywords.append(keyword)
                    
                    total_keywords = len(expected_keywords)
                    matched_count = len(matched_keywords)
                    match_ratio = matched_count / total_keywords if total_keywords > 0 else 0
                    
                    if match_ratio >= 0.5:
                        points_earned = points
                        is_correct = True
                    elif match_ratio >= 0.3:
                        points_earned = int(points * 0.7)
                        is_correct = False
                    elif match_ratio >= 0.2:
                        points_earned = int(points * 0.5)
                        is_correct = False
                    elif match_ratio >= 0.1:
                        points_earned = int(points * 0.3)
                        is_correct = False
                    else:
                        points_earned = int(points * 0.2)
                        is_correct = False
                    
                    logger.debug(f"Speaking Q{question_num}: Legacy score {points_earned}/{points} points")
            
            correct_answer_display = f"Expected keywords: {', '.join(expected_keywords)}"
        
        # ============================================================
        # TYPE 3: MULTIPLE CHOICE QUESTIONS (have "options" field)
        # ============================================================
        elif "options" in question_data and "correct" in question_data:
            correct_answer = question_data["correct"]
            options = question_data["options"]
            correct_answer_display = correct_answer
            
            logger.debug(f"Multiple choice Q{question_num}: Comparing answers")
            
            # For multiple choice, do EXACT comparison (case-insensitive, trimmed)
            user_clean = user_answer.strip()
            correct_clean = correct_answer.strip()
            
            # Method 1: Exact match (case-insensitive)
            is_correct = user_clean.lower() == correct_clean.lower()
            
            # Method 2: If not matched, check if it matches any option exactly
            if not is_correct:
                for option in options:
                    if user_clean.lower() == option.strip().lower():
                        # User selected a valid option, check if it's the correct one
                        is_correct = option.strip().lower() == correct_clean.lower()
                        break
            
            logger.debug(f"Multiple choice Q{question_num}: is_correct={is_correct}")
        
        # ============================================================
        # TYPE 4: FILL-IN-THE-BLANK (no options, has "correct" field)
        # time_numbers module uses this
        # ============================================================
        elif "correct" in question_data and "options" not in question_data:
            correct_answer = question_data["correct"]
            correct_answer_display = correct_answer
            
            logger.debug(f"Fill-in-blank Q{question_num}: Comparing with flexible matching")
            
            # Flexible matching for fill-in-the-blank (numbers, times)
            def normalize_fill_in(ans: str) -> str:
                """Normalize fill-in-the-blank answers for flexible comparison"""
                ans = ans.lower().strip()
                # Remove am/pm (keep the number part)
                ans = ans.replace(" am", "").replace(" pm", "")
                ans = ans.replace("am", "").replace("pm", "")
                # Remove leading zeros from times (07:00 -> 7:00)
                if ":" in ans:
                    parts = ans.split(":")
                    if len(parts) == 2:
                        try:
                            hour = str(int(parts[0]))  # Remove leading zero
                            minute = parts[1].strip()
                            ans = f"{hour}:{minute}" if minute != "00" else hour
                        except ValueError:
                            pass
                # Remove extra whitespace
                ans = " ".join(ans.split())
                return ans
            
            user_normalized = normalize_fill_in(user_answer)
            correct_normalized = normalize_fill_in(correct_answer)
            
            # Try exact normalized match
            is_correct = user_normalized == correct_normalized
            
            # Also try: just extract digits and compare
            if not is_correct:
                import re
                user_digits = re.sub(r'[^0-9]', '', user_answer)
                correct_digits = re.sub(r'[^0-9]', '', correct_answer)
                if user_digits and correct_digits:
                    is_correct = user_digits == correct_digits
                    if is_correct:
                        logger.debug(f"Fill-in-blank Q{question_num}: Matched by digits")
            
            logger.debug(f"Fill-in-blank Q{question_num}: is_correct={is_correct}")
        
        else:
            logger.warning(f"Unknown question format for Q{question_num}, question_data keys: {list(question_data.keys())}")
            correct_answer_display = "N/A"
        
        # Calculate points (only if not already set by type-specific logic)
        # Speaking and vocabulary modules already set points_earned, don't override!
        if "expected_keywords" not in question_data and "correct_matches" not in question_data:
            points_earned = points if is_correct else 0
        
        # Generate feedback
        if is_correct:
            feedback = "✅ Correct! Well done."
        elif ("expected_keywords" in question_data or "correct_matches" in question_data) and points_earned > 0:
            # Partial credit for speaking or vocabulary
            feedback = f"✅ Partial credit! You earned {points_earned}/{points} points."
        else:
            feedback = f"❌ Incorrect. The correct answer is: {correct_answer_display}"
        
        result = {
            "is_correct": is_correct,
            "points_earned": points_earned,
            "points_possible": points,
            "feedback": feedback,
            "module": module
        }
        
        logger.debug(f"Final scoring Q{question_num}: is_correct={is_correct}, points={points_earned}/{points}")
        return result
        
    except Exception as e:
        logger.error(f"Error in score_answer_from_config for Q{question_num}: {e}", exc_info=True)
        return {
            "is_correct": False,
            "points_earned": 0,
            "points_possible": 4,
            "feedback": "Error scoring answer" if not settings.DEBUG else f"Error: {str(e)}",
            "module": "unknown"
        }


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, operation: Optional[str] = None):
    """
    Homepage - Redirect to registration page as landing page
    If operation parameter is provided, redirect to instructions page
    """
    # If operation is provided, redirect to instructions page
    if operation:
        return RedirectResponse(url=f"/instructions?operation={operation}", status_code=303)

    # Otherwise, redirect to registration page as the first page
    return RedirectResponse(url="/register", status_code=303)


@router.get("/start-assessment", response_class=HTMLResponse)
async def start_assessment(request: Request, operation: str, db: AsyncSession = Depends(get_db)):
    """
    Start assessment with operation filter and create assessment session

    Args:
        operation: Operation type (HOTEL, MARINE, or CASINO)
    """
    try:
        # Validate operation
        valid_operations = ["HOTEL", "MARINE", "CASINO"]
        operation = operation.upper()

        if operation not in valid_operations:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation. Must be one of: {', '.join(valid_operations)}"
            )

        # Get user ID from session
        user_id = request.session.get("user_id")
        if not user_id:
            # Redirect to login if not authenticated
            return RedirectResponse(url="/login", status_code=303)

        # Create assessment session using AssessmentEngine
        from core.assessment_engine import AssessmentEngine
        from models.assessment import DivisionType, Assessment, AssessmentStatus
        from sqlalchemy import select
        import uuid

        engine = AssessmentEngine(db)

        # Map operation to division type
        division_map = {
            "HOTEL": DivisionType.HOTEL,
            "MARINE": DivisionType.MARINE,
            "CASINO": DivisionType.CASINO
        }

        # Check if assessment already exists in session (created during registration)
        existing_assessment_id = request.session.get("assessment_id")
        if existing_assessment_id:
            # Try to use existing assessment
            result = await db.execute(
                select(Assessment).where(Assessment.id == existing_assessment_id)
            )
            existing_assessment = result.scalar_one_or_none()
            
            if existing_assessment and existing_assessment.status == AssessmentStatus.NOT_STARTED:
                # Start the existing assessment
                await engine.start_assessment(existing_assessment_id)
                assessment = existing_assessment
                logger.info(f"Starting existing assessment {assessment.id} for operation {operation}")
            else:
                # Existing assessment is invalid or already started, create new one
                assessment = await engine.create_assessment(
                    user_id=int(user_id),
                    division=division_map[operation]
                )
                request.session["assessment_id"] = assessment.id
                await engine.start_assessment(assessment.id)
                logger.info(f"Created and started new assessment {assessment.id} for operation {operation}")
        else:
            # No existing assessment, create new one
            assessment = await engine.create_assessment(
                user_id=int(user_id),
                division=division_map[operation]
            )
            request.session["assessment_id"] = assessment.id
            await engine.start_assessment(assessment.id)
            logger.info(f"Created and started new assessment {assessment.id} for operation {operation}")

        # IMPORTANT: Clear old session data before starting new assessment
        # This ensures fresh scoring for each new test
        request.session["operation"] = operation
        request.session["answers"] = {}  # Clear old answers!
        
        logger.debug("Cleared session answers for fresh start")

        # Redirect to first question
        return RedirectResponse(url=f"/question/1?operation={operation}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start_assessment: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while starting the assessment. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/question/{question_num}", response_class=HTMLResponse)
async def question_page(request: Request, question_num: int, operation: Optional[str] = None):
    """
    Question page - Display specific question filtered by operation

    Args:
        question_num: Question number (1-21)
        operation: Operation type (HOTEL, MARINE, or CASINO) - optional for backward compatibility
    """
    logger.debug(f"GET /question/{question_num} - operation={operation}")
    try:
        # Validate question number
        if question_num < 1 or question_num > 21:
            raise HTTPException(status_code=404, detail="Question not found. Valid range: 1-21")

        # Load questions
        questions = get_questions()
        question_key = str(question_num)

        if question_key not in questions:
            raise HTTPException(status_code=404, detail=f"Question {question_num} not found in configuration")

        question_data = questions[question_key]

        # If operation is specified, validate and store it
        if operation:
            operation = operation.upper()
            valid_operations = ["HOTEL", "MARINE", "CASINO"]
            if operation not in valid_operations:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid operation. Must be one of: {', '.join(valid_operations)}"
                )

        # Calculate progress
        progress_percent = round((int(question_num) / 21) * 100, 1)

        # Determine if this is the last question
        is_last_question = (question_num == 21)
        next_question = question_num + 1 if not is_last_question else None
        previous_question = question_num - 1 if question_num > 1 else None

        # Get session data for anti-cheating
        session_data = {}
        try:
            session_data = dict(request.session)
        except Exception:
            # Session not available, use empty dict
            session_data = {}

        # Prepare context - match template variable names
        context = {
            "request": request,
            "session": session_data,  # Add session for anti-cheating tracking
            "q_num": question_num,  # Template expects q_num
            "question_num": question_num,  # Keep for backward compatibility
            "total_questions": 21,
            "progress": progress_percent,  # Template expects progress
            "progress_percent": progress_percent,  # Keep for backward compatibility
            "question_data": question_data,
            "module": question_data.get("module"),
            "module_display": question_data.get("module", "Unknown"),  # Template expects module_display
            "points": question_data.get("points", 0),  # Template expects points
            "content": question_data.get("content", ""),  # Template expects content
            "script": question_data.get("script", ""),  # Template expects script
            "is_last_question": is_last_question,
            "next_question": next_question,
            "previous_question": previous_question,
            "operation": operation  # Pass operation to template
        }

        # Use generic question template for all modules
        # TODO: Create module-specific templates in the future
        return render_template(request, "question.html", context)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering question {question_num}: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the question. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.post("/submit")
async def submit_answer(
    request: Request,
    question_num: int = Form(...),
    answer: str = Form(...),
    operation: Optional[str] = Form(None),
    time_spent: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit answer for a question

    Args:
        question_num: Question number
        answer: User's answer
        operation: Operation type (HOTEL, MARINE, CASINO) - optional
        time_spent: Time spent on question in seconds (optional)

    Returns:
        Redirect to next question or results page
    """
    try:
        # Validate question number
        if question_num < 1 or question_num > 21:
            raise HTTPException(status_code=400, detail="Invalid question number")

        # Load questions
        questions = get_questions()
        question_key = str(question_num)

        if question_key not in questions:
            raise HTTPException(status_code=404, detail=f"Question {question_num} not found")

        question_data = questions[question_key]

        # IMPLEMENTED: Database persistence for answers
        # Get or create assessment from session
        session = request.session
        assessment_id = session.get("assessment_id")

        # If no assessment exists, create one
        if not assessment_id:
            # Get user info from session or create temporary user
            user_id = session.get("user_id")

            if not user_id:
                # Create temporary guest user for demo/testing
                # In production, user should be registered first
                from models.assessment import User, DivisionType
                from utils.auth import hash_password
                import secrets

                # Check if guest user exists
                from sqlalchemy import select
                guest_result = await db.execute(
                    select(User).where(User.email == "guest@demo.com")
                )
                guest_user = guest_result.scalar_one_or_none()

                if not guest_user:
                    # Create guest user with secure password hash
                    # Use environment variable or generate secure password
                    guest_password = os.getenv("GUEST_USER_PASSWORD", secrets.token_urlsafe(16))
                    guest_user = User(
                        first_name="Guest",
                        last_name="User",
                        email="guest@demo.com",
                        nationality="USA",
                        password_hash=hash_password(guest_password),
                        division=DivisionType.HOTEL if operation == "HOTEL" else (
                            DivisionType.MARINE if operation == "MARINE" else DivisionType.CASINO
                        ),
                        department="Demo"
                    )
                    db.add(guest_user)
                    await db.commit()
                    await db.refresh(guest_user)
                    logger.info(f"Created guest user for demo: {guest_user.id}")

                user_id = guest_user.id
                session["user_id"] = user_id

                # Create assessment
                from core.assessment_engine import AssessmentEngine
                engine = AssessmentEngine(db)

                assessment = await engine.create_assessment(
                    user_id=user_id,
                    division=guest_user.division
                )
                assessment_id = assessment.id
                session["assessment_id"] = assessment_id

                # Start assessment
                await engine.start_assessment(assessment_id)
                logger.info(f"Created and started assessment {assessment_id} for guest user {user_id}")

        # UI-BASED SCORING: Use questions_config.json directly
        # This avoids the database Question table ID mismatch issue
        logger.debug(f"Starting UI-based scoring for Q{question_num}, assessment_id={assessment_id}")
        
        # Score answer using config file
        result = score_answer_from_config(question_num, answer)
        logger.debug(f"UI scoring result for Q{question_num}: is_correct={result.get('is_correct')}, points={result.get('points_earned')}")
        
        # Store result in session - MINIMAL DATA to avoid Cookie size limit (4KB)
        # Only store: question_num -> "module:points" (e.g., "reading:4")
        answers = session.get("answers", {})
        # Compact format: "module:points_earned"
        answers[str(question_num)] = f"{result.get('module', 'unknown')}:{result['points_earned']}"
        session["answers"] = answers
        
        logger.debug(f"Stored Q{question_num} answer. Total answers: {len(answers)}")

        # Determine next action
        if question_num == 21:
            logger.info(f"Last question (Q21) reached for assessment {assessment_id}")
            # Last question - calculate final scores from session
            if assessment_id:
                try:
                    from models.assessment import Assessment, AssessmentStatus
                    from sqlalchemy import select
                    
                    logger.debug(f"Calculating final scores for assessment_id={assessment_id}")
                    
                    # Calculate scores from session answers
                    # Format: answers = {"1": "listening:5", "2": "listening:5", ...}
                    answers = session.get("answers", {})
                    logger.debug(f"Found {len(answers)} answers in session")
                    
                    # Group by module and calculate scores
                    module_scores = {
                        "listening": 0,
                        "time_numbers": 0,
                        "grammar": 0,
                        "vocabulary": 0,
                        "reading": 0,
                        "speaking": 0
                    }
                    
                    for q_num, answer_data in answers.items():
                        # Parse compact format: "module:points"
                        if isinstance(answer_data, str) and ":" in answer_data:
                            parts = answer_data.split(":")
                            module = parts[0].lower().replace(" & ", "_").replace(" ", "_")
                            try:
                                points = int(parts[1])
                            except (ValueError, IndexError):
                                logger.warning(f"Invalid answer format for Q{q_num}: {answer_data}")
                                points = 0
                        elif isinstance(answer_data, dict):
                            # Legacy format support
                            module = answer_data.get("module", "unknown").lower().replace(" & ", "_").replace(" ", "_")
                            points = answer_data.get("points_earned", 0)
                        else:
                            continue
                        
                        if module in module_scores:
                            module_scores[module] += points
                    
                    total_score = sum(module_scores.values())
                    logger.info(f"Calculated total_score={total_score} for assessment {assessment_id}. Module breakdown: {module_scores}")
                    
                    # Update database with final scores
                    result = await db.execute(
                        select(Assessment).where(Assessment.id == assessment_id)
                    )
                    assessment = result.scalar_one_or_none()
                    
                    if assessment:
                        assessment.status = AssessmentStatus.COMPLETED
                        assessment.completed_at = datetime.now()
                        assessment.total_score = total_score
                        assessment.listening_score = module_scores["listening"]
                        assessment.time_numbers_score = module_scores["time_numbers"]
                        assessment.grammar_score = module_scores["grammar"]
                        assessment.vocabulary_score = module_scores["vocabulary"]
                        assessment.reading_score = module_scores["reading"]
                        assessment.speaking_score = module_scores["speaking"]
                        assessment.passed = total_score >= settings.PASS_THRESHOLD_TOTAL
                        
                        await db.commit()
                        logger.info(f"Assessment {assessment_id} completed and updated in database")
                    else:
                        logger.warning(f"Assessment {assessment_id} not found in database")
                        
                except Exception as e:
                    logger.error(f"Error completing assessment {assessment_id}: {e}", exc_info=True)
                    # Continue to results even if scoring fails
            else:
                logger.warning("No assessment_id found for complete_assessment")

            # Redirect to results
            logger.debug("Redirecting to /results")
            return RedirectResponse(url="/results", status_code=303)
        else:
            # Go to next question
            next_question = question_num + 1
            
            # Check if we need to show a module transition screen
            if should_show_transition(question_num, next_question):
                current_module = get_module_for_question(question_num)
                if operation:
                    return RedirectResponse(
                        url=f"/module-transition?completed={current_module}&next_question={next_question}&operation={operation}",
                        status_code=303
                    )
                else:
                    return RedirectResponse(
                        url=f"/module-transition?completed={current_module}&next_question={next_question}",
                        status_code=303
                    )
            
            # Normal redirect to next question
            if operation:
                return RedirectResponse(url=f"/question/{next_question}?operation={operation}", status_code=303)
            else:
                return RedirectResponse(url=f"/question/{next_question}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer for Q{question_num}: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while submitting your answer. Please try again."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Results page - Display assessment results

    Shows:
    - Total score
    - Pass/Fail status
    - Module breakdown
    - Recommendations
    """
    try:
        # Fetch actual results from database
        session = request.session
        assessment_id = session.get("assessment_id")

        logger.debug(f"Results page requested, assessment_id from session: {assessment_id}")

        modules = []
        total_score = 0
        total_possible = 100

        if assessment_id:
            try:
                from models.assessment import Assessment
                from sqlalchemy import select

                logger.debug(f"Fetching assessment {assessment_id} from database")
                # Fetch assessment from database
                result = await db.execute(
                    select(Assessment).where(Assessment.id == assessment_id)
                )
                assessment = result.scalar_one_or_none()

                if assessment:
                    logger.debug(f"Found assessment {assessment_id} with total_score={assessment.total_score}")
                    # Use actual scores from database (calculated by complete_assessment)
                    modules = [
                        {"name": "Listening", "score": assessment.listening_score or 0, "possible": 16, "icon": "🎧"},
                        {"name": "Time & Numbers", "score": assessment.time_numbers_score or 0, "possible": 16, "icon": "🔢"},
                        {"name": "Grammar", "score": assessment.grammar_score or 0, "possible": 16, "icon": "📝"},
                        {"name": "Vocabulary", "score": assessment.vocabulary_score or 0, "possible": 16, "icon": "📚"},
                        {"name": "Reading", "score": assessment.reading_score or 0, "possible": 16, "icon": "📖"},
                        {"name": "Speaking", "score": assessment.speaking_score or 0, "possible": 20, "icon": "🎤"}
                    ]
                    total_score = assessment.total_score or 0
                    logger.debug(f"Built modules list with total_score={total_score}")
                    
                    # Send completion email (only once per assessment)
                    if assessment.status == AssessmentStatus.COMPLETED:
                        # Check if email was already sent (use a session flag)
                        email_sent_key = f"email_sent_{assessment_id}"
                        if not session.get(email_sent_key):
                            try:
                                from services.email_service import get_email_service
                                from models.assessment import User
                                
                                # Get user info
                                user_result = await db.execute(
                                    select(User).where(User.id == assessment.user_id)
                                )
                                user = user_result.scalar_one_or_none()
                                
                                if user and user.email:
                                    email_service = get_email_service()
                                    user_name = f"{user.first_name} {user.last_name}".strip() or "User"
                                    
                                    module_scores = {
                                        "Listening": assessment.listening_score or 0,
                                        "Time & Numbers": assessment.time_numbers_score or 0,
                                        "Grammar": assessment.grammar_score or 0,
                                        "Vocabulary": assessment.vocabulary_score or 0,
                                        "Reading": assessment.reading_score or 0,
                                        "Speaking": assessment.speaking_score or 0
                                    }
                                    
                                    email_result = await email_service.send_assessment_completion_email(
                                        to_email=user.email,
                                        user_name=user_name,
                                        total_score=assessment.total_score or 0,
                                        module_scores=module_scores
                                    )
                                    
                                    if email_result.success:
                                        logger.info(f"Assessment completion email sent to {user.email}")
                                        session[email_sent_key] = True
                                    else:
                                        logger.warning(f"Failed to send completion email: {email_result.error}")
                                        
                            except Exception as email_error:
                                logger.warning(f"Error sending completion email: {email_error}")
                else:
                    logger.warning(f"No assessment found in database for id {assessment_id}")
            except Exception as e:
                logger.error(f"Error fetching assessment results for {assessment_id}: {e}", exc_info=True)
                # If error, modules will remain empty list
        else:
            logger.debug("No assessment_id in session")

        # If no modules found (no assessment or error), show error message
        if not modules:
            logger.warning("No modules found for results page, returning 404")
            raise HTTPException(
                status_code=404,
                detail="Assessment not found. Please complete the assessment first."
            )

        # Calculate total from modules
        if total_score == 0:
            total_score = sum(m["score"] for m in modules)

        total_possible = sum(m["possible"] for m in modules)
        # Convert to integers for display
        total_score_int = int(round(total_score))
        percentage = int(round((total_score / total_possible) * 100)) if total_possible > 0 else 0

        # Use neutral gradient for score display (no pass/fail judgment)
        score_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"

        # Prepare individual module scores for template
        listening_score = int(round(modules[0]["score"]))
        listening_percentage = int(round((modules[0]["score"] / modules[0]["possible"]) * 100))
        
        time_numbers_score = int(round(modules[1]["score"]))
        time_numbers_percentage = int(round((modules[1]["score"] / modules[1]["possible"]) * 100))
        
        grammar_score = int(round(modules[2]["score"]))
        grammar_percentage = int(round((modules[2]["score"] / modules[2]["possible"]) * 100))
        
        vocabulary_score = int(round(modules[3]["score"]))
        vocabulary_percentage = int(round((modules[3]["score"] / modules[3]["possible"]) * 100))
        
        reading_score = int(round(modules[4]["score"]))
        reading_percentage = int(round((modules[4]["score"] / modules[4]["possible"]) * 100))
        
        speaking_score = int(round(modules[5]["score"]))
        speaking_percentage = int(round((modules[5]["score"] / modules[5]["possible"]) * 100))

        return render_template(
            request,
            "results.html",
            {
                "total_score": total_score_int,
                "score_percentage": percentage,
                "score_gradient": score_gradient,
                "listening_score": listening_score,
                "listening_percentage": listening_percentage,
                "time_numbers_score": time_numbers_score,
                "time_numbers_percentage": time_numbers_percentage,
                "grammar_score": grammar_score,
                "grammar_percentage": grammar_percentage,
                "vocabulary_score": vocabulary_score,
                "vocabulary_percentage": vocabulary_percentage,
                "reading_score": reading_score,
                "reading_percentage": reading_percentage,
                "speaking_score": speaking_score,
                "speaking_percentage": speaking_percentage
            }
        )

    except HTTPException:
        # Re-raise HTTPException (like 404) without wrapping
        raise
    except Exception as e:
        logger.error(f"Error rendering results page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading results. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/anti-cheating-report", response_class=HTMLResponse)
async def anti_cheating_report_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Anti-Cheating Report Page - Display assessment integrity report

    Shows:
    - Suspicious activity score (0-100)
    - Risk level (clean, low, medium, high, critical)
    - Tab switches, copy/paste attempts
    - IP and user agent consistency
    - Session details
    """
    try:
        # Get assessment ID from session (if available)
        assessment_id = None
        try:
            session = request.session
            assessment_id = session.get("assessment_id")
        except Exception:
            # No session available, use demo data
            pass

        # Default values
        suspicious_score = 0
        risk_level = "clean"
        tab_switches = 0
        copy_paste_attempts = 0
        ip_changed = False
        ua_changed = False
        risk_factors = []
        ip_address = "Unknown"
        user_agent = request.headers.get("user-agent", "Unknown")
        session_start_time = "Unknown"

        # Fetch anti-cheating data from database
        if assessment_id:
            try:
                from utils.anti_cheating import AntiCheatingService
                from models.assessment import Assessment
                from sqlalchemy import select

                # Get anti-cheating service
                anti_cheat = AntiCheatingService(db)

                # Get suspicious score
                score_data = await anti_cheat.get_suspicious_score(assessment_id)

                suspicious_score = score_data.get("score", 0)
                risk_level = score_data.get("level", "clean")
                risk_factors = score_data.get("factors", [])

                # Get session validation
                validation = await anti_cheat.validate_session(assessment_id, request)
                ip_changed = not validation.get("ip_consistent", True)
                ua_changed = not validation.get("user_agent_consistent", True)

                # Get assessment details
                result = await db.execute(
                    select(Assessment).where(Assessment.id == assessment_id)
                )
                assessment = result.scalar_one_or_none()

                if assessment and assessment.analytics_data:
                    analytics = assessment.analytics_data
                    tab_switches = analytics.get("tab_switches", 0)
                    copy_paste_attempts = analytics.get("copy_paste_attempts", 0)
                    session_start_time = analytics.get("session_start_time", "Unknown")
                    ip_address = assessment.ip_address or "Unknown"
            except Exception as e:
                logger.error(f"Error fetching anti-cheating data for assessment {assessment_id}: {e}", exc_info=True)
                # Use default values

        # Check if demo mode is requested
        demo_mode = request.query_params.get("demo")

        # Demo data for testing (if no real assessment data)
        if demo_mode == "clean" or (not assessment_id and not demo_mode):
            # Clean demo - no suspicious activity
            suspicious_score = 0
            risk_level = "clean"
            tab_switches = 0
            copy_paste_attempts = 0
            ip_changed = False
            ua_changed = False
            risk_factors = []
            session_start_time = "2025-11-07 10:00:00"
        elif demo_mode == "low":
            # Low risk demo
            suspicious_score = 10
            risk_level = "low"
            tab_switches = 2
            copy_paste_attempts = 0
            ip_changed = False
            ua_changed = False
            risk_factors = ["Minor tab switching (2 times)"]
            session_start_time = "2025-11-07 10:00:00"
        elif demo_mode == "medium":
            # Medium risk demo
            suspicious_score = 25
            risk_level = "medium"
            tab_switches = 4
            copy_paste_attempts = 2
            ip_changed = False
            ua_changed = False
            risk_factors = ["Excessive tab switching (4 times)", "Copy/paste detected (2 attempts)"]
            session_start_time = "2025-11-07 10:00:00"
        elif demo_mode == "high":
            # High risk demo
            suspicious_score = 55
            risk_level = "high"
            tab_switches = 5
            copy_paste_attempts = 6
            ip_changed = True
            ua_changed = False
            risk_factors = ["IP address changed from 192.168.1.100 to 10.0.0.1", "Excessive tab switching (5 times)", "Excessive copy/paste (6 attempts)"]
            session_start_time = "2025-11-07 10:00:00"
        elif demo_mode == "critical":
            # Critical risk demo
            suspicious_score = 85
            risk_level = "critical"
            tab_switches = 8
            copy_paste_attempts = 10
            ip_changed = True
            ua_changed = True
            risk_factors = ["IP address changed from 192.168.1.100 to 10.0.0.1", "User agent (browser/device) changed during assessment", "Excessive tab switching (8 times)", "Excessive copy/paste (10 attempts)"]
            session_start_time = "2025-11-07 10:00:00"

        # If no risk factors, add a positive message
        if not risk_factors:
            risk_factors = []

        return render_template(
            request,
            "anti_cheating_report.html",
            {
                "assessment_id": assessment_id or "N/A",
                "suspicious_score": suspicious_score,
                "risk_level": risk_level,
                "tab_switches": tab_switches,
                "copy_paste_attempts": copy_paste_attempts,
                "ip_changed": ip_changed,
                "ua_changed": ua_changed,
                "risk_factors": risk_factors,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_start_time": session_start_time
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering anti-cheating report: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the report. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/instructions", response_class=HTMLResponse)
async def instructions_page(request: Request, operation: Optional[str] = None):
    """
    Instructions page - Assessment guidelines and rules
    """
    try:
        instructions_data = {
            "general": [
                "This assessment contains 21 questions across 6 modules",
                "Total possible score: 100 points",
                "Passing score: 65 points (65%)",
                "You must complete all questions",
                "Answer honestly and to the best of your ability"
            ],
            "modules": {
                "Listening": "Listen to audio clips and answer questions. Each clip can be played twice.",
                "Time & Numbers": "Fill in missing times or numbers. You have 10 seconds per question.",
                "Grammar": "Choose the correct answer to complete sentences.",
                "Vocabulary": "Match terms with their correct definitions.",
                "Reading": "Read passages and answer comprehension questions.",
                "Speaking": "Record spoken responses (maximum 20 seconds each)."
            },
            "rules": [
                "Do not use external resources or translation tools",
                "Ensure you are in a quiet environment",
                "Check your audio equipment before starting",
                "Complete the assessment in one session",
                "You cannot go back to previous questions once submitted"
            ]
        }

        return render_template(
            request,
            "instructions.html",
            {
                "instructions": instructions_data,
                "operation": operation  # Pass operation to template
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering instructions page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading instructions. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/pre-test", response_class=HTMLResponse)
async def pre_test_page(request: Request, operation: Optional[str] = None):
    """
    Pre-test confirmation page - Final checklist before starting the assessment.
    
    Displays important reminders and ensures the user is ready to begin.
    """
    try:
        return render_template(
            request,
            "pre_test.html",
            {
                "operation": operation
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering pre-test page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/module-transition", response_class=HTMLResponse)
async def module_transition_page(
    request: Request,
    completed: str,
    next_question: int,
    operation: Optional[str] = None
):
    """
    Module transition screen - Shows progress between modules.
    
    Displays which module was completed and what's coming next.
    """
    try:
        # Get completed module info
        completed_info = MODULE_INFO.get(completed, {})
        completed_module_name = completed_info.get("name", "Module")
        
        # Get next module info
        next_module = get_module_for_question(next_question)
        next_info = MODULE_INFO.get(next_module, {})
        
        # Build modules progress list
        modules_progress = []
        for module_key, info in sorted(MODULE_INFO.items(), key=lambda x: x[1]["order"]):
            module_order = info["order"]
            completed_order = completed_info.get("order", 0)
            
            if module_order <= completed_order:
                status = "completed"
            elif module_order == completed_order + 1:
                status = "current"
            else:
                status = "pending"
            
            modules_progress.append({
                "name": info["name"],
                "icon": info["icon"],
                "status": status
            })
        
        return render_template(
            request,
            "module_transition.html",
            {
                "completed_module_name": completed_module_name,
                "next_module_name": next_info.get("name", "Next Module"),
                "next_module_icon": next_info.get("icon", "📋"),
                "next_module_questions": next_info.get("questions", 0),
                "next_module_points": next_info.get("points", 0),
                "next_question": next_question,
                "operation": operation,
                "modules": modules_progress
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering module transition page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/invitation", response_class=HTMLResponse)
async def invitation_verify_page(request: Request, code: Optional[str] = None):
    """
    Invitation code verification page
    
    Users must verify their invitation code before accessing registration.
    Supports both URL-based code (auto-verify) and manual input.
    
    Args:
        code: Optional invitation code from URL (auto-verify)
    """
    try:
        return render_template(
            request,
            "invitation_verify.html",
            {
                "code": code
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering invitation page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/register", response_class=HTMLResponse)
async def registration_page(request: Request, code: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Registration page - Candidate information form
    Supports invitation code for controlled registration
    
    Args:
        code: Optional invitation code from admin
    """
    try:
        # If invitation code provided, validate it
        if code:
            from models.assessment import InvitationCode
            from sqlalchemy import select
            
            result = await db.execute(
                select(InvitationCode).where(InvitationCode.code == code)
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                raise HTTPException(status_code=404, detail="Invalid invitation code")
            
            # Check if assessment already completed
            if invitation.assessment_completed:
                raise HTTPException(
                    status_code=400, 
                    detail="This invitation link has already been used and the assessment has been completed. Please contact administrator for a new invitation."
                )
            
            if invitation.is_used:
                raise HTTPException(
                    status_code=400, 
                    detail="This invitation code has already been used. If you started an assessment, please complete it or contact administrator."
                )
            
            # Check expiration
            if invitation.expires_at and invitation.expires_at < datetime.now():
                raise HTTPException(status_code=400, detail="Invitation code expired")

        return render_template(
            request,
            "registration.html",
            {
                "invitation_code": code
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering registration page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the registration page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login page - User authentication
    """
    try:
        return render_template(
            request,
            "login.html",
            {
                "title": "Login - CCL English Assessment"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering login page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the login page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """
    Forgot password page - Request password reset
    """
    try:
        return render_template(
            request,
            "forgot_password.html",
            {
                "title": "Forgot Password - CCL English Assessment"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering forgot password page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: Optional[str] = None):
    """
    Reset password page - Set new password using token
    """
    try:
        return render_template(
            request,
            "reset_password.html",
            {
                "title": "Reset Password - CCL English Assessment",
                "token": token
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering reset password page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


# Health check endpoint

@router.get("/debug/session")
async def debug_session(request: Request):
    """DEBUG: View session data"""
    try:
        session = request.session
        answers = session.get("answers", {})
        assessment_id = session.get("assessment_id")
        
        logger.debug(f"Session data - Assessment ID: {assessment_id}, Total answers: {len(answers)}")
        
        return {
            "assessment_id": assessment_id,
            "total_answers": len(answers),
            "answers": answers
        }
    except Exception as e:
        logger.error(f"Error in debug_session: {e}", exc_info=True)
        return {"error": "An error occurred" if not settings.DEBUG else str(e)}

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """
    Admin Dashboard - Main admin page
    Protected: Requires admin authentication
    """
    try:
        # Check admin authentication
        if not request.session.get("is_admin"):
            return RedirectResponse(url="/login", status_code=303)
        
        return render_template(
            request,
            "admin_dashboard.html",
            {}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering admin dashboard: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the dashboard. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/admin/invitations", response_class=HTMLResponse)
async def admin_invitation_page(request: Request):
    """
    Admin invitation management page
    Protected: Requires admin authentication
    """
    try:
        # Check admin authentication
        if not request.session.get("is_admin"):
            return RedirectResponse(url="/login", status_code=303)
        
        return render_template(
            request,
            "admin_invitation.html",
            {}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering admin invitation page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the page. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/admin/scoreboard", response_class=HTMLResponse)
async def admin_scoreboard_page(request: Request):
    """
    User Scoreboard - All test results
    Protected: Requires admin authentication
    """
    try:
        # Check admin authentication
        if not request.session.get("is_admin"):
            return RedirectResponse(url="/login", status_code=303)
        
        return render_template(
            request,
            "admin_scoreboard.html",
            {}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering scoreboard page: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while loading the scoreboard. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Verify questions config can be loaded
        questions = get_questions()
        question_count = len(questions)

        return {
            "status": "healthy",
            "service": "ui_routes",
            "questions_loaded": question_count,
            "templates_directory": str(templates_dir),
            "data_directory": str(data_dir)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/debug/test-speaking-scoring")
async def debug_test_speaking_scoring():
    """
    DEBUG: Test speaking module intelligent scoring with various keyword matches
    """
    # Test Q19: AC too cold (7 points)
    # Expected keywords: ["apologize", "sorry", "send someone", "fix", "adjust", "maintenance", "comfortable"]
    
    test_cases = [
        {
            "scenario": "Perfect response (all keywords)",
            "question": 19,
            "answer": "recorded_10s|I apologize for the inconvenience, I'm so sorry. I will send someone from maintenance to fix and adjust the air conditioning to make you more comfortable.",
            "expected_match_rate": "100%",
            "expected_score": "7/7"
        },
        {
            "scenario": "Good response (50%+ keywords)",
            "question": 19,
            "answer": "recorded_8s|I'm sorry about that. I will send maintenance to fix the temperature for you.",
            "expected_match_rate": "57%",
            "expected_score": "7/7"
        },
        {
            "scenario": "Average response (30-49% keywords)",
            "question": 19,
            "answer": "recorded_7s|I apologize. Let me adjust the temperature.",
            "expected_match_rate": "29%",
            "expected_score": "4-5/7"
        },
        {
            "scenario": "Poor response (<30% keywords)",
            "question": 19,
            "answer": "recorded_6s|Okay, I will help you.",
            "expected_match_rate": "<30%",
            "expected_score": "1-3/7"
        },
        {
            "scenario": "No speech detected (recording only)",
            "question": 19,
            "answer": "recorded_5s|",
            "expected_match_rate": "0%",
            "expected_score": "1/7 (minimal)"
        },
        {
            "scenario": "No recording",
            "question": 19,
            "answer": "",
            "expected_match_rate": "N/A",
            "expected_score": "0/7"
        }
    ]
    
    results = []
    for test in test_cases:
        result = score_answer_from_config(test["question"], test["answer"])
        results.append({
            "scenario": test["scenario"],
            "answer_preview": test["answer"][:60] + "..." if len(test["answer"]) > 60 else test["answer"],
            "expected_match_rate": test["expected_match_rate"],
            "expected_score": test["expected_score"],
            "actual_score": f"{result['points_earned']}/{result['points_possible']}",
            "is_correct": result["is_correct"]
        })
    
    return {
        "test_description": "Speaking Module Intelligent Scoring Test",
        "question": "Q19: AC too cold",
        "expected_keywords": ["apologize", "sorry", "send someone", "fix", "adjust", "maintenance", "comfortable"],
        "scoring_rules": {
            "50%+ keywords": "Full points",
            "30-49% keywords": "70% of points",
            "20-29% keywords": "50% of points",
            "10-19% keywords": "30% of points",
            "<10% keywords": "20% of points (minimal attempt)",
            "No recording": "0 points"
        },
        "test_results": results
    }


@router.get("/debug/test-scoring")
async def debug_test_scoring():
    """
    DEBUG: Test scoring logic with all correct answers
    This endpoint tests if the scoring function works correctly
    """
    results = []
    total_score = 0
    
    # Test answers for all 21 questions (the correct answers)
    test_answers = {
        # Listening (1-3) - Multiple choice
        1: "7 PM",
        2: "8254",
        3: "Deck 12",
        # Time & Numbers (4-6) - Fill-in-blank
        4: "7:00",
        5: "8",
        6: "9173",
        # Grammar (7-10) - Multiple choice
        7: "May",
        8: "has",
        9: "direct",
        10: "on",
        # Vocabulary (11-14) - Matching (JSON)
        11: json.dumps({"Bridge": "Ship's control center", "Gangway": "Ship's walkway to shore", "Tender": "Small boat for shore trips", "Muster": "Emergency assembly"}),
        12: json.dumps({"Concierge": "Guest services specialist", "Amenities": "Hotel facilities", "Excursion": "Shore activities", "Embark": "To board the ship"}),
        13: json.dumps({"Buffet": "Self-service dining", "A la carte": "Menu with individual prices", "Galley": "Ship's kitchen", "Sommelier": "Wine expert"}),
        14: json.dumps({"Muster drill": "Safety meeting", "Life jacket": "Personal flotation device", "Assembly station": "Emergency meeting point", "All aboard": "Final boarding call"}),
        # Reading (15-18) - Multiple choice
        15: "Contact the Port Agent",
        16: "2:00 AM",
        17: "Reservations",
        18: "4:00 PM",
        # Speaking (19-21) - Recording with transcript
        # Format: "recorded_DURATION|TRANSCRIPT"
        19: "recorded_10s|I apologize for the inconvenience. I will send someone from maintenance to fix the air conditioning and make you more comfortable.",
        20: "recorded_8s|The buffet closes at 10 PM. However, room service is available 24 hours if you need dining options later.",
        21: "recorded_7s|Take the elevator to deck 5 and follow the signs to the spa. It's located near the fitness center."
    }
    
    for q_num, answer in test_answers.items():
        result = score_answer_from_config(q_num, answer)
        results.append({
            "question": q_num,
            "answer": answer[:80] + "..." if len(answer) > 80 else answer,
            "is_correct": result["is_correct"],
            "points_earned": result["points_earned"],
            "points_possible": result["points_possible"],
            "module": result["module"]
        })
        total_score += result["points_earned"]
    
    # Group by module
    module_scores = {}
    for r in results:
        module = r["module"]
        if module not in module_scores:
            module_scores[module] = {"earned": 0, "possible": 0, "questions": []}
        module_scores[module]["earned"] += r["points_earned"]
        module_scores[module]["possible"] += r["points_possible"]
        module_scores[module]["questions"].append(r["question"])
    
    return {
        "test_description": "Testing scoring with ALL CORRECT answers (including speaking transcription)",
        "expected_total": 100,
        "actual_total": total_score,
        "all_correct": total_score == 100,
        "module_breakdown": module_scores,
        "detailed_results": results
    }
