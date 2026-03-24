"""
UI Routes - Serves frontend pages using Jinja2 templates
Handles all user-facing web pages for the assessment platform
"""

import logging
import traceback
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import re
from pathlib import Path

import sqlalchemy

from core.database import get_db
from core.config import settings
from core.security import get_csrf_token
from utils.cefr import get_cefr_display
from utils.scoring import compute_overall_pass
from models.assessment import AssessmentStatus, Question, User, DivisionType
import models.assessment as _models_assessment

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


def _normalize_options(options) -> Optional[List[str]]:
    """Normalize options to list of strings for templates. Handles plain strings or dicts with text/value."""
    if options is None:
        return None
    if not isinstance(options, (list, tuple)):
        return None
    out = []
    for o in options:
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, dict):
            out.append(o.get("text") or o.get("value") or o.get("label") or str(o))
        else:
            out.append(str(o))
    return out if out else None


def _normalize_time_numbers_audio(text: str) -> str:
    """Clean common artifacts after filling Time & Numbers blanks."""
    cleaned = (text or "").replace("$$", "$")
    cleaned = re.sub(r"\b(AM|PM)\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def _time_numbers_audio_sentence(question_text: str, correct_answer: Optional[str], context: Optional[str]) -> str:
    """
    Build answer-bearing sentence for Time & Numbers audio.
    Prefer correct_answer; context can include extra units/suffixes.
    """
    fill = (correct_answer or context or "").strip()
    if not fill:
        return question_text or ""
    return _normalize_time_numbers_audio((question_text or "").replace("___", fill))


def _map_db_question_to_template_data(q) -> Dict[str, Any]:
    """
    Map DB Question model to template question_data format.
    Template expects: module, question, correct, points, options, audio_text, audio_file_path,
    passage, terms, definitions, correct_matches, speaking_type, min_duration, expected_keywords.
    """
    meta = q.question_metadata or {}
    audio_text = meta.get("audio_text") or meta.get("audio")  # generator may use "audio"
    audio_file_path = getattr(q, "audio_file_path", None) or meta.get("audio_file_path")
    # Listening: TTS must play the DIALOGUE (guest request, scenario), NOT the instruction. Never fall back to
    # question_text for listening—that is the instruction ("Listen to the guest request and choose the best response").
    # If audio_text/audio_file_path are missing, leave audio_text unset so we don't play wrong content.
    # Time & Numbers: always synthesize from prompt + answer to avoid stale/odd
    # metadata audio_text values and duplicated units like "PM PM" or "$$5000".
    module_val = getattr(q.module_type, "value", None) or str(q.module_type)
    if module_val == "time_numbers":
        audio_text = _time_numbers_audio_sentence(
            q.question_text,
            q.correct_answer,
            meta.get("context"),
        )
    elif module_val == "speaking":
        st = (meta.get("speaking_type") or "").lower()
        if st == "repeat" and not audio_text and not audio_file_path:
            ref = (meta.get("reference_text") or meta.get("repeat_phrase") or "").strip()
            ca = (q.correct_answer or "").strip()
            if ref:
                audio_text = ref
            elif ca and not ca.startswith("["):
                audio_text = ca
    return {
        "module": q.module_type.value,
        "question": q.question_text,
        "correct": q.correct_answer,
        "points": q.points or 4,
        "options": _normalize_options(q.options) if q.options else None,
        "audio_text": audio_text,
        "audio_file_path": audio_file_path,
        "passage": meta.get("passage"),
        "terms": meta.get("terms"),
        "definitions": meta.get("definitions"),
        "correct_matches": meta.get("correct_matches"),
        "speaking_type": meta.get("speaking_type"),
        "min_duration": meta.get("min_duration"),
        "expected_keywords": meta.get("expected_keywords"),
    }


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
    """Get the module name for a given question number (from static questions_config.json)."""
    questions = get_questions()
    question_key = str(question_num)
    if question_key in questions:
        return questions[question_key].get("module", "unknown")
    return "unknown"


async def get_module_for_question_from_assessment(db: AsyncSession, assessment, question_num: int) -> Optional[str]:
    """
    Get the module for a question position using the assessment's question_order and DB.
    Use this when the assessment is department-based so transition is based on actual module boundaries.
    Returns None if assessment has no question_order or index is out of range.
    """
    if not assessment or not getattr(assessment, "question_order", None):
        return None
    order = assessment.question_order
    if question_num < 1 or question_num > len(order):
        return None
    question_id = order[question_num - 1]
    q_result = await db.execute(
        sqlalchemy.select(_models_assessment.Question).where(_models_assessment.Question.id == question_id)
    )
    q = q_result.scalar_one_or_none()
    if not q or not getattr(q, "module_type", None):
        return None
    return q.module_type.value


def should_show_transition(current_question: int, next_question: int) -> bool:
    """Determine if a module transition screen should be shown (uses static config only)."""
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
        points_earned = 0

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
        # TYPE 2A: SPEAKING REPEAT QUESTIONS (have "audio_text" for repeat)
        # Word-matching scoring - compare transcript against audio text
        # ============================================================
        elif question_data.get("speaking_type") == "repeat" and "audio_text" in question_data:
            audio_text = question_data["audio_text"]
            logger.debug(f"Speaking Repeat Q{question_num}: Analyzing word match against audio text")
            
            # Parse answer format: "recorded_DURATION|TRANSCRIPT"
            transcript = ""
            recording_duration = 0.0
            if "|" in user_answer:
                parts = user_answer.split("|", 1)
                transcript = parts[1].strip() if len(parts) > 1 else ""
                duration_match = parts[0].replace("recorded_", "").replace("s", "")
                try:
                    recording_duration = float(duration_match)
                except ValueError:
                    recording_duration = 0.0
            elif user_answer.startswith("recorded_"):
                transcript = ""
                duration_match = user_answer.replace("recorded_", "").replace("s", "")
                try:
                    recording_duration = float(duration_match)
                except ValueError:
                    recording_duration = 0.0
            
            has_recording = user_answer and user_answer.startswith("recorded_")
            
            if not has_recording:
                is_correct = False
                points_earned = 0
                logger.debug(f"Speaking Repeat Q{question_num}: No recording detected")
            elif not transcript:
                is_correct = False
                points_earned = 0
                logger.debug(f"Speaking Repeat Q{question_num}: Recording detected but no speech - 0 points")
            else:
                # Word-matching scoring for repeat questions
                import re
                
                # Normalize and extract words from both texts
                def normalize_text(text):
                    # Remove punctuation and convert to lowercase
                    text = re.sub(r'[^\w\s]', '', text.lower())
                    return text.split()
                
                expected_words = normalize_text(audio_text)
                spoken_words = normalize_text(transcript)
                
                # Count how many expected words appear in the spoken text
                matched_count = 0
                for word in expected_words:
                    if word in spoken_words:
                        matched_count += 1
                        # Remove matched word to prevent double counting
                        spoken_words.remove(word)
                
                total_expected = len(expected_words)
                match_ratio = matched_count / total_expected if total_expected > 0 else 0
                
                # Award points based on match percentage
                points_earned = int(round(points * match_ratio))
                is_correct = match_ratio >= 0.7  # 70% accuracy considered correct
                
                logger.debug(
                    f"Speaking Repeat Q{question_num}: Word matching - "
                    f"matched={matched_count}/{total_expected}, "
                    f"ratio={match_ratio:.1%}, "
                    f"points={points_earned}/{points}"
                )
        
        # ============================================================
        # TYPE 2B: SPEAKING SCENARIO QUESTIONS (have "expected_keywords")
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
                # Recording exists but no transcript (no speech detected)
                # Give 0 points - user must speak to earn points
                is_correct = False
                points_earned = 0
                logger.debug(f"Speaking Q{question_num}: Recording detected but no speech - 0 points")
            else:
                # Guardrail: very short/noise transcripts should not score points.
                spoken_words = re.findall(r"\b[a-zA-Z]{2,}\b", transcript)
                if len(spoken_words) < 2:
                    is_correct = False
                    points_earned = 0
                    logger.debug(
                        f"Speaking Q{question_num}: Transcript too short/noisy ({len(spoken_words)} words) - 0 points"
                    )
                    correct_answer_display = f"Expected keywords: {', '.join(expected_keywords)}"
                    result = {
                        "is_correct": is_correct,
                        "points_earned": points_earned,
                        "points_possible": points,
                        "feedback": "❌ No clear speech detected. Please record a clear spoken response.",
                        "module": module
                    }
                    logger.debug(f"Final scoring Q{question_num}: is_correct={is_correct}, points={points_earned}/{points}")
                    return result

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
                    
                    points_earned = min(points, int(round(score_result.total_points)))
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
        # Speaking repeat (word-match), vocabulary, and keyword speaking already set points_earned — do not overwrite.
        is_speaking_repeat_config = (
            question_data.get("speaking_type") == "repeat" and "audio_text" in question_data
        )
        if (
            "expected_keywords" not in question_data
            and "correct_matches" not in question_data
            and not is_speaking_repeat_config
        ):
            points_earned = points if is_correct else 0
        
        # Generate feedback
        if is_correct:
            feedback = "✅ Correct! Well done."
        elif (
            ("expected_keywords" in question_data or "correct_matches" in question_data or is_speaking_repeat_config)
            and points_earned > 0
        ):
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
    Homepage - Redirect to admin login page as landing page
    Admin creates invitation links that go directly to registration
    """
    # If operation is provided, redirect to instructions page
    if operation:
        return RedirectResponse(url=f"/instructions?operation={operation}", status_code=303)

    # Redirect to admin login - invitation links will go directly to /register
    return RedirectResponse(url="/login", status_code=303)


@router.get("/start-assessment", response_class=HTMLResponse)
async def start_assessment(
    request: Request,
    operation: str,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Start assessment with operation filter and create assessment session

    Args:
        operation: Operation type (HOTEL, MARINE, or CASINO)
        department: Optional department for question variety (Hotel/Marine only)
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
        from models.assessment import DivisionType
        import uuid

        engine = AssessmentEngine(db)

        # Map operation to division type
        division_map = {
            "HOTEL": DivisionType.HOTEL,
            "MARINE": DivisionType.MARINE,
            "CASINO": DivisionType.CASINO
        }
        target_division = division_map[operation]

        # #region agent log
        try:
            _lp = Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
            _d = {"raw_department": department, "operation": operation}
            with open(_lp, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:start_assessment","message":"query params","data":_d,"hypothesisId":"H1","timestamp":int(__import__("time").time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion

        # When user came from an invitation, always use the invitation's department (set at registration).
        # Otherwise: prefer department from query param (pre-test dropdown), then session, then user profile.
        department_for_questions = None
        if request.session.get("invitation_code") and request.session.get("department"):
            from config.departments import normalize_department
            department_for_questions = normalize_department(str(request.session["department"]).strip()) or None
        if not department_for_questions and department and str(department).strip():
            from config.departments import normalize_department
            department_for_questions = normalize_department(str(department).strip())
        if not department_for_questions:
            department_for_questions = request.session.get("department")
        if not department_for_questions and user_id:
            result_user = await db.execute(
                sqlalchemy.select(_models_assessment.User).where(_models_assessment.User.id == int(user_id))
            )
            user = result_user.scalar_one_or_none()
            if user and getattr(user, "division", None) == target_division and getattr(user, "department", None):
                from config.departments import normalize_department
                department_for_questions = normalize_department(user.department)
        if department_for_questions:
            department_for_questions = str(department_for_questions).strip() or None
        request.session["department"] = department_for_questions

        # #region agent log
        try:
            _lp = Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
            _d = {"department_for_questions": department_for_questions, "session_dept": request.session.get("department")}
            with open(_lp, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:start_assessment","message":"department resolved","data":_d,"hypothesisId":"H2","timestamp":int(__import__("time").time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion

        # Check if assessment already exists in session (created during registration)
        existing_assessment_id = request.session.get("assessment_id")
        if existing_assessment_id:
            # Try to use existing assessment only if it matches the selected operation
            result = await db.execute(
                sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == existing_assessment_id)
            )
            existing_assessment = result.scalar_one_or_none()
            # Reuse only when NOT_STARTED, same division, AND same department (so question set matches selection)
            existing_dept = getattr(existing_assessment, "department", None) or None
            req_dept = department_for_questions or None
            _reuse = bool(existing_assessment
                    and existing_assessment.status == _models_assessment.AssessmentStatus.NOT_STARTED
                    and getattr(existing_assessment, "division", None) == target_division
                    and existing_dept == req_dept)
            # #region agent log
            try:
                _lp = Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
                _st = getattr(existing_assessment, "status", None) if existing_assessment else None
                _d = {"existing_assessment_id": existing_assessment_id, "existing_dept": existing_dept, "req_dept": req_dept, "reuse": _reuse, "existing_status": _st.value if _st else None}
                with open(_lp, "a", encoding="utf-8") as _f:
                    _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:start_assessment","message":"reuse decision","data":_d,"hypothesisId":"H3","timestamp":int(__import__("time").time()*1000)}) + "\n")
            except Exception:
                pass
            # #endregion
            if _reuse:
                await engine.start_assessment(existing_assessment_id)
                assessment = existing_assessment
                logger.info(f"Starting existing assessment {assessment.id} for operation {operation}")
            else:
                # Existing assessment is invalid or wrong division, create new one (division-only)
                assessment = await engine.create_assessment(
                    user_id=int(user_id),
                    division=division_map[operation],
                    department=department_for_questions
                )
                request.session["assessment_id"] = assessment.id
                await engine.start_assessment(assessment.id)
                logger.info(f"Created and started new assessment {assessment.id} for operation {operation}")
        else:
            # No existing assessment, create new one (division-only for question pool)
            assessment = await engine.create_assessment(
                user_id=int(user_id),
                division=division_map[operation],
                department=department_for_questions
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
    except ValueError as e:
        if "No questions available for department" in str(e):
            raise HTTPException(status_code=503, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in start_assessment: {e}", exc_info=True)
        if settings.DEBUG:
            detail = f"Error: {str(e)}"
        else:
            detail = "An error occurred while starting the assessment. Please try again later."
        raise HTTPException(status_code=500, detail=detail)


@router.get("/question/{question_num}", response_class=HTMLResponse)
async def question_page(request: Request, question_num: int, operation: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Question page - Display specific question filtered by operation

    Args:
        question_num: Question number (1-21)
        operation: Operation type (HOTEL, MARINE, or CASINO) - optional for backward compatibility
    """
    logger.debug(f"GET /question/{question_num} - operation={operation}")
    try:
        # When landing on Q1 with NOT_STARTED assessment (from instructions->pre-test flow), start it now
        # Also fix corrupted state: IN_PROGRESS but empty question_order (e.g. column was missing at start)
        session = request.session
        assessment_id = session.get("assessment_id")
        if question_num == 1 and assessment_id:
            from core.assessment_engine import AssessmentEngine
            result = await db.execute(sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id))
            a = result.scalar_one_or_none()
            if a:
                if a.status == _models_assessment.AssessmentStatus.NOT_STARTED:
                    engine = AssessmentEngine(db)
                    await engine.start_assessment(assessment_id)
                    session["answers"] = {}
                    logger.info(f"Started assessment {assessment_id} on first question load")
                elif a.status == _models_assessment.AssessmentStatus.IN_PROGRESS and (not a.question_order or len(a.question_order or []) < 21):
                    # Corrupted: started but question_order empty (e.g. DB column was missing). Create fresh assessment.
                    user_id = int(session.get("user_id", 0))
                    user_result = await db.execute(sqlalchemy.select(_models_assessment.User).where(_models_assessment.User.id == user_id))
                    user = user_result.scalar_one_or_none()
                    department = (a.department or (user.department if user else None))
                    division = a.division or (_models_assessment.DivisionType.HOTEL if user and user.division else _models_assessment.DivisionType.HOTEL)
                    engine = AssessmentEngine(db)
                    new_assessment = await engine.create_assessment(user_id=user_id, division=division, department=department)
                    session["assessment_id"] = new_assessment.id
                    session["answers"] = {}
                    await engine.start_assessment(new_assessment.id)
                    logger.info(f"Recreated assessment {new_assessment.id} (replacing corrupted {assessment_id}), department={department}")

        # Validate question number
        if question_num < 1 or question_num > 21:
            raise HTTPException(status_code=404, detail="Question not found. Valid range: 1-21")

        # Enforce question sequence - must answer previous questions first
        session = request.session
        answers = session.get("answers", {})
        
        # For question N (where N > 1), check that questions 1 to N-1 have been answered
        if question_num > 1:
            for prev_q in range(1, question_num):
                if str(prev_q) not in answers:
                    # Redirect to the first unanswered question
                    first_unanswered = prev_q
                    for q in range(1, question_num):
                        if str(q) not in answers:
                            first_unanswered = q
                            break
                    logger.warning(f"User tried to access question {question_num} without answering question {first_unanswered}")
                    return RedirectResponse(
                        url=f"/question/{first_unanswered}?operation={operation or session.get('operation', 'HOTEL')}",
                        status_code=303
                    )

        # Load question: prefer assessment.question_order (department-specific) over static config
        question_data = None
        assessment = None
        assessment_id = session.get("assessment_id")
        if assessment_id:
            result = await db.execute(sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id))
            assessment = result.scalar_one_or_none()
            if assessment and assessment.question_order and question_num > len(assessment.question_order):
                raise HTTPException(status_code=404, detail=f"Question {question_num} not found. This assessment has {len(assessment.question_order)} questions.")
            if assessment and assessment.question_order and len(assessment.question_order) >= question_num:
                question_id = assessment.question_order[question_num - 1]
                q_result = await db.execute(sqlalchemy.select(_models_assessment.Question).where(_models_assessment.Question.id == question_id))
                q = q_result.scalar_one_or_none()
                if q:
                    question_data = _map_db_question_to_template_data(q)
                    # #region agent log
                    if question_num == 1:
                        try:
                            _p = Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
                            _d = {"assessment_id": assessment_id, "question_id": question_id, "assessment_dept": getattr(assessment, "department", None), "first_3_ids": (assessment.question_order or [])[:3], "source": "db", "question_text": (q.question_text or "")[:120]}
                            with open(_p, "a", encoding="utf-8") as _f:
                                _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:question_page","message":"Q1 loaded from assessment","data":_d,"hypothesisId":"H5","timestamp":int(__import__("time").time()*1000)}) + "\n")
                        except Exception:
                            pass
                    # #endregion
        if question_data is None:
            # When assessment is department-based, never show generic (config) questions
            if assessment and getattr(assessment, "department", None):
                from fastapi.responses import HTMLResponse
                dept = assessment.department or "your department"
                html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>No questions available</title></head><body style='font-family:sans-serif;max-width:520px;margin:2rem auto;padding:1rem;'>"
                    "<h1>No questions available</h1>"
                    f"<p>There are no questions configured for department <strong>{dept}</strong>.</p>"
                    "<p>Please contact the administrator to load the full question bank (30 departments × 100 questions) and try again.</p>"
                    "<p><a href='/instructions'>← Back to Instructions</a></p>"
                    "</body></html>"
                )
                return HTMLResponse(content=html, status_code=503)
            # #region agent log
            if question_num == 1:
                try:
                    import json
                    _p = __import__("pathlib").Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
                    _d = {"assessment_id": assessment_id, "source": "config_fallback", "reason": "no DB question"}
                    with open(_p, "a", encoding="utf-8") as _f:
                        _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:793","message":"Q1 using config fallback","data":_d,"hypothesisId":"H3","timestamp":int(__import__("time").time()*1000)}) + "\n")
                except Exception:
                    pass
            # #endregion
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

        # Total questions: use assessment length when department-based, else 21
        total_questions = len(assessment.question_order) if (assessment and getattr(assessment, "question_order", None)) else 21
        # Calculate progress
        progress_percent = round((int(question_num) / total_questions) * 100, 1)

        # Determine if this is the last question
        is_last_question = (question_num == total_questions)
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
            "total_questions": total_questions,
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
            "operation": operation,  # Pass operation to template
            "debug_mode": settings.DEBUG,
        }

        # Use module-specific template when available, fall back to generic question.html
        _MODULE_TEMPLATE_MAP = {
            "listening": "question_listening.html",
            "time_numbers": "question_time_numbers.html",
            "grammar": "question_grammar.html",
            "vocabulary": "question_vocabulary.html",
            "reading": "question_reading.html",
            "speaking": "question_speaking.html",
        }
        module = question_data.get("module")
        template_name = _MODULE_TEMPLATE_MAP.get(module, "question.html")
        # #region agent log
        try:
            _lp = Path(__file__).resolve().parents[5] / "debug-ccd1fc.log"
            _opts = question_data.get("options")
            _d = {"question_num": question_num, "module": module, "template": template_name, "opts_len": len(_opts) if isinstance(_opts, (list, tuple)) else 0, "has_terms": bool(question_data.get("terms")), "has_defs": bool(question_data.get("definitions")), "source": "db" if assessment_id and assessment and assessment.question_order else "config"}
            with open(_lp, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"sessionId":"ccd1fc","location":"ui.py:question_page","message":"render question","data":_d,"hypothesisId":"H4","timestamp":int(__import__("time").time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion
        return render_template(request, template_name, context)

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error rendering question {question_num}: {e}\n{tb}", exc_info=True)
        # Write traceback to file for debugging
        for candidate in [Path(__file__).resolve().parents[5], Path(__file__).resolve().parents[4], Path.cwd()]:
            try:
                f = candidate / "question_error_traceback.txt"
                f.write_text(f"Error: {e}\n\n{tb}", encoding="utf-8")
                break
            except Exception:
                pass
        detail = f"Error: {str(e)}\n\nTraceback:\n{tb}"
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

        # Prevent duplicate submissions - if question already answered, redirect to next
        answers = session.get("answers", {})
        if str(question_num) in answers:
            logger.warning(f"Duplicate submission attempt for question {question_num}")
            # Redirect to next question or results
            if question_num == 21:
                return RedirectResponse(url="/results", status_code=303)
            next_q = question_num + 1
            op = operation or session.get("operation", "HOTEL")
            return RedirectResponse(url=f"/question/{next_q}?operation={op}", status_code=303)
        
        assessment_id = session.get("assessment_id")

        # If no assessment exists, create one
        if not assessment_id:
            # Get user info from session or create temporary user
            user_id = session.get("user_id")

            if not user_id:
                # Create temporary guest user for demo/testing
                # In production, user should be registered first
                from utils.auth import hash_password
                import secrets

                # Check if guest user exists
                guest_result = await db.execute(
                    sqlalchemy.select(_models_assessment.User).where(_models_assessment.User.email == "guest@demo.com")
                )
                guest_user = guest_result.scalar_one_or_none()

                if not guest_user:
                    # Create guest user with secure password hash
                    # Use environment variable or generate secure password
                    guest_password = os.getenv("GUEST_USER_PASSWORD", secrets.token_urlsafe(16))
                    guest_user = _models_assessment.User(
                        first_name="Guest",
                        last_name="User",
                        email="guest@demo.com",
                        nationality="USA",
                        password_hash=hash_password(guest_password),
                        division=_models_assessment.DivisionType.HOTEL if operation == "HOTEL" else (
                            _models_assessment.DivisionType.MARINE if operation == "MARINE" else _models_assessment.DivisionType.CASINO
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

        # SCORING: Use engine.submit_response when assessment has question_order (department-specific);
        # otherwise fall back to questions_config.json
        logger.debug(f"Starting scoring for Q{question_num}, assessment_id={assessment_id}")
        
        result = None
        question_order = None
        if assessment_id:
            assess_result = await db.execute(sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id))
            assessment = assess_result.scalar_one_or_none()
            if assessment and assessment.question_order and len(assessment.question_order) >= question_num:
                question_order = assessment.question_order
                question_id = question_order[question_num - 1]
                from core.assessment_engine import AssessmentEngine
                engine = AssessmentEngine(db)
                try:
                    result = await engine.submit_response(
                        assessment_id, question_id, answer,
                        time_spent=time_spent or 0
                    )
                except ValueError as e:
                    if "already answered" in str(e).lower():
                        logger.warning(f"Duplicate submission for Q{question_num}: {e}")
                        if question_num == 21:
                            return RedirectResponse(url="/results", status_code=303)
                        next_q = question_num + 1
                        op = operation or session.get("operation", "HOTEL")
                        return RedirectResponse(url=f"/question/{next_q}?operation={op}", status_code=303)
                    raise
                # Map engine result to expected format; need module for answer_entry
                q_result = await db.execute(sqlalchemy.select(_models_assessment.Question).where(_models_assessment.Question.id == question_id))
                q = q_result.scalar_one_or_none()
                module_str = q.module_type.value if q and q.module_type else "unknown"
                result = {
                    "is_correct": result["is_correct"],
                    "points_earned": int(result["points_earned"]),
                    "module": module_str
                }
                logger.debug(f"Engine scoring for Q{question_num}: is_correct={result['is_correct']}, points={result['points_earned']}")
        
        if result is None:
            result = score_answer_from_config(question_num, answer)
            logger.debug(f"Config scoring for Q{question_num}: is_correct={result.get('is_correct')}, points={result.get('points_earned')}")
        
        # Store result in session AND database - session can be unreliable (cookie size limits)
        answers = session.get("answers", {})
        answer_entry = f"{result.get('module', 'unknown')}:{result['points_earned']}"
        answers[str(question_num)] = answer_entry
        session["answers"] = answers
        
        # PERSIST TO DATABASE - primary source of truth (session cookie may fail)
        if assessment_id:
            try:
                assess_result = await db.execute(sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id))
                assessment = assess_result.scalar_one_or_none()
                if assessment:
                    data = dict(assessment.analytics_data or {})
                    ui_answers = dict(data.get("ui_answers") or {})
                    ui_answers[str(question_num)] = answer_entry
                    data["ui_answers"] = ui_answers
                    assessment.analytics_data = data  # Reassign triggers SQLAlchemy persistence
                    await db.commit()
                    logger.debug(f"Persisted Q{question_num} to DB. Total in DB: {len(ui_answers)}")
            except Exception as e:
                logger.warning(f"Failed to persist answer to DB: {e}")
        
        logger.debug(f"Stored Q{question_num} answer. Total answers: {len(answers)}")

        # Determine next action: last question is 21 (static) or last position in assessment.question_order (DB)
        is_last_question = (
            question_num == 21
            or (assessment_id and assessment and question_order and question_num == len(question_order))
        )
        if is_last_question:
            logger.info(f"Last question (Q21) reached for assessment {assessment_id}")
            # Last question - calculate final scores from session
            if assessment_id:
                try:
                    logger.debug(f"Calculating final scores for assessment_id={assessment_id}")
                    
                    # Calculate scores - prefer DB (ui_answers) over session (session cookie may fail)
                    answers = {}
                    assess_result = await db.execute(
                        sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id)
                    )
                    db_assessment = assess_result.scalar_one_or_none()
                    if db_assessment and db_assessment.analytics_data:
                        answers = db_assessment.analytics_data.get("ui_answers") or {}
                        logger.debug(f"Loaded {len(answers)} answers from DB for final scoring")
                    if not answers:
                        answers = session.get("answers", {})
                        logger.debug(f"Fallback: {len(answers)} answers from session")

                    # Prefer engine completion when per-question rows exist (matches speaking/safety rules)
                    n_resp = (
                        await db.execute(
                            sqlalchemy.select(sqlalchemy.func.count())
                            .select_from(_models_assessment.AssessmentResponse)
                            .where(_models_assessment.AssessmentResponse.assessment_id == assessment_id)
                        )
                    ).scalar_one() or 0
                    engine_done = False
                    if n_resp > 0:
                        try:
                            from core.assessment_engine import AssessmentEngine

                            completion = await AssessmentEngine(db).complete_assessment(assessment_id)
                            sc = completion["scores"]
                            session["computed_scores"] = {
                                "listening": sc.get("listening", 0),
                                "time_numbers": sc.get("time_numbers", 0),
                                "grammar": sc.get("grammar", 0),
                                "vocabulary": sc.get("vocabulary", 0),
                                "reading": sc.get("reading", 0),
                                "speaking": sc.get("speaking", 0),
                                "total": completion["total_score"],
                            }
                            logger.info(
                                "Assessment %s completed via engine; passed=%s total=%s",
                                assessment_id,
                                completion["passed"],
                                completion["total_score"],
                            )
                            engine_done = True
                        except Exception as eng_err:
                            logger.warning(
                                "complete_assessment failed for %s, using manual aggregation: %s",
                                assessment_id,
                                eng_err,
                                exc_info=True,
                            )

                    if not engine_done:
                        # Group by module and calculate scores (legacy ui_answers path — no response rows)
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

                        module_max = {
                            "listening": 16,
                            "time_numbers": 16,
                            "grammar": 16,
                            "vocabulary": 16,
                            "reading": 16,
                            "speaking": 20,
                        }
                        for m in module_scores:
                            module_scores[m] = min(module_scores[m], module_max[m])
                        total_score = min(100, sum(module_scores.values()))
                        logger.info(f"Calculated total_score={total_score} for assessment {assessment_id}. Module breakdown: {module_scores}")

                        # Update database with final scores
                        result = await db.execute(
                            sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id)
                        )
                        assessment = result.scalar_one_or_none()

                        if assessment:
                            assessment.status = _models_assessment.AssessmentStatus.COMPLETED
                            assessment.completed_at = datetime.now()
                            assessment.total_score = total_score
                            assessment.listening_score = module_scores["listening"]
                            assessment.time_numbers_score = module_scores["time_numbers"]
                            assessment.grammar_score = module_scores["grammar"]
                            assessment.vocabulary_score = module_scores["vocabulary"]
                            assessment.reading_score = module_scores["reading"]
                            assessment.speaking_score = module_scores["speaking"]
                            # Legacy path: no per-question safety flags — treat as no dedicated safety items (same as engine default)
                            _, safety_ok, speaking_ok, final_pass = compute_overall_pass(
                                float(total_score),
                                float(module_scores["speaking"]),
                                1.0,
                            )
                            assessment.passed = final_pass
                            assessment.safety_questions_passed = safety_ok
                            assessment.speaking_threshold_passed = speaking_ok

                            await db.commit()
                            logger.info(f"Assessment {assessment_id} completed and updated in database")
                            # Store in session as fallback for results page (session survives redirect)
                            session["computed_scores"] = {
                                "listening": module_scores["listening"],
                                "time_numbers": module_scores["time_numbers"],
                                "grammar": module_scores["grammar"],
                                "vocabulary": module_scores["vocabulary"],
                                "reading": module_scores["reading"],
                                "speaking": module_scores["speaking"],
                                "total": total_score,
                            }
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

            if assessment and question_order and next_question > len(question_order):
                # No more questions in this assessment; complete and go to results
                logger.info(f"Next question {next_question} exceeds assessment length {len(question_order)}; redirecting to results")
                return RedirectResponse(url="/results", status_code=303)

            # When assessment has question_order, use DB-based module so transition shows before next module (not after)
            if assessment and question_order and next_question <= len(question_order):
                next_module = await get_module_for_question_from_assessment(db, assessment, next_question)
                current_module = result.get("module") if result else None
                if current_module and next_module and current_module != next_module:
                    if operation:
                        return RedirectResponse(
                            url=f"/module-transition?completed={current_module}&next_question={next_question}&operation={operation}",
                            status_code=303
                        )
                    return RedirectResponse(
                        url=f"/module-transition?completed={current_module}&next_question={next_question}",
                        status_code=303
                    )
                if operation:
                    return RedirectResponse(url=f"/question/{next_question}?operation={operation}", status_code=303)
                return RedirectResponse(url=f"/question/{next_question}", status_code=303)

            # Static config flow: transition from questions_config.json
            if should_show_transition(question_num, next_question):
                current_module = get_module_for_question(question_num)
                if operation:
                    return RedirectResponse(
                        url=f"/module-transition?completed={current_module}&next_question={next_question}&operation={operation}",
                        status_code=303
                    )
                return RedirectResponse(
                    url=f"/module-transition?completed={current_module}&next_question={next_question}",
                    status_code=303
                )

            # Normal redirect to next question
            if operation:
                return RedirectResponse(url=f"/question/{next_question}?operation={operation}", status_code=303)
            return RedirectResponse(url=f"/question/{next_question}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error submitting answer for Q%d: %s", question_num, e)
        detail = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/api/results/scores")
async def get_results_scores_api(request: Request, db: AsyncSession = Depends(get_db)):
    """JSON API: Return current assessment scores. Used by results page to ensure correct display."""
    session = request.session
    assessment_id = session.get("assessment_id")
    if not assessment_id:
        return {"error": "No assessment", "scores": None}
    try:
        result = await db.execute(sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()
        if not assessment:
            return {"error": "Assessment not found", "scores": None}
        answers = {}
        if assessment.analytics_data:
            answers = assessment.analytics_data.get("ui_answers") or {}
        if not answers:
            answers = session.get("answers", {})
        if answers:
            module_scores = {"listening": 0, "time_numbers": 0, "grammar": 0, "vocabulary": 0, "reading": 0, "speaking": 0}
            for _q, answer_data in answers.items():
                if isinstance(answer_data, str) and ":" in answer_data:
                    parts = answer_data.split(":")
                    module = parts[0].lower().replace(" & ", "_").replace(" ", "_")
                    try:
                        points = int(parts[1])
                    except (ValueError, IndexError):
                        points = 0
                elif isinstance(answer_data, dict):
                    module = answer_data.get("module", "unknown").lower().replace(" & ", "_").replace(" ", "_")
                    points = answer_data.get("points_earned", 0)
                else:
                    continue
                if module in module_scores:
                    module_scores[module] += points
            module_max = {
                "listening": 16,
                "time_numbers": 16,
                "grammar": 16,
                "vocabulary": 16,
                "reading": 16,
                "speaking": 20,
            }
            for m in module_scores:
                module_scores[m] = min(module_scores[m], module_max[m])
            total = min(100, sum(module_scores.values()))
            assessment.status = _models_assessment.AssessmentStatus.COMPLETED
            assessment.completed_at = datetime.now()
            assessment.total_score = total
            assessment.listening_score = module_scores["listening"]
            assessment.time_numbers_score = module_scores["time_numbers"]
            assessment.grammar_score = module_scores["grammar"]
            assessment.vocabulary_score = module_scores["vocabulary"]
            assessment.reading_score = module_scores["reading"]
            assessment.speaking_score = module_scores["speaking"]
            _, safety_ok, speaking_ok, final_pass = compute_overall_pass(
                float(total), float(module_scores["speaking"]), 1.0
            )
            assessment.passed = final_pass
            assessment.safety_questions_passed = safety_ok
            assessment.speaking_threshold_passed = speaking_ok
            await db.commit()
        total_possible = 100
        modules = [
            {"name": "Listening", "score": assessment.listening_score or 0, "possible": 16},
            {"name": "Time & Numbers", "score": assessment.time_numbers_score or 0, "possible": 16},
            {"name": "Grammar", "score": assessment.grammar_score or 0, "possible": 16},
            {"name": "Vocabulary", "score": assessment.vocabulary_score or 0, "possible": 16},
            {"name": "Reading", "score": assessment.reading_score or 0, "possible": 16},
            {"name": "Speaking", "score": assessment.speaking_score or 0, "possible": 20}
        ]
        total_score = assessment.total_score or sum(m["score"] for m in modules)
        percentage = int(round((total_score / total_possible) * 100)) if total_possible > 0 else 0
        return {
            "listening_score": int(modules[0]["score"]),
            "time_numbers_score": int(modules[1]["score"]),
            "grammar_score": int(modules[2]["score"]),
            "vocabulary_score": int(modules[3]["score"]),
            "reading_score": int(modules[4]["score"]),
            "speaking_score": int(modules[5]["score"]),
            "total_score": int(total_score),
            "score_percentage": percentage
        }
    except Exception as e:
        logger.error(f"API get_results_scores: {e}", exc_info=True)
        return {"error": str(e), "scores": None}


def _render_results_page(request: Request, modules: list, operation: str = "HOTEL"):
    """Shared render for results template from modules list."""
    total_score = sum(m["score"] for m in modules)
    total_possible = sum(m["possible"] for m in modules)
    total_score_int = int(round(total_score))
    percentage = int(round((total_score / total_possible) * 100)) if total_possible > 0 else 0
    cefr_display = get_cefr_display(percentage)
    cefr_level = cefr_display["cefr_level"]
    cefr_name = cefr_display["cefr_name"]
    cefr_description = cefr_display["cefr_description"]
    score_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
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
            "operation": operation,
            "total_score": total_score_int,
            "score_percentage": percentage,
            "cefr_level": cefr_level,
            "cefr_name": cefr_name,
            "cefr_description": cefr_description,
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


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Results page - Display assessment results

    Shows:
    - Total score
    - Pass/Fail status
    - Module breakdown
    - Recommendations

    Query params:
    - demo=1: Show results page with sample data (no session required).
    """
    try:
        # Demo mode: render with sample data for direct access / screenshots (no session required)
        _demo = (request.query_params.get("demo") or "").strip().lower()
        if _demo in ("1", "true", "yes"):
            sample_modules = [
                {"name": "Listening", "score": 14, "possible": 16, "icon": "🎧"},
                {"name": "Time & Numbers", "score": 15, "possible": 16, "icon": "🔢"},
                {"name": "Grammar", "score": 12, "possible": 16, "icon": "📝"},
                {"name": "Vocabulary", "score": 13, "possible": 16, "icon": "📚"},
                {"name": "Reading", "score": 14, "possible": 16, "icon": "📖"},
                {"name": "Speaking", "score": 16, "possible": 20, "icon": "🎤"}
            ]
            return _render_results_page(request, sample_modules, operation="HOTEL")

        # Fetch actual results from database
        session = request.session
        assessment_id = session.get("assessment_id")

        logger.debug(f"Results page requested, assessment_id from session: {assessment_id}")

        modules = []
        total_score = 0
        total_possible = 100

        if assessment_id:
            try:

                logger.debug(f"Fetching assessment {assessment_id} from database")
                # Fetch assessment from database
                result = await db.execute(
                    sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id)
                )
                assessment = result.scalar_one_or_none()

                if assessment:
                    logger.debug(f"Found assessment {assessment_id} with total_score={assessment.total_score}")

                    # ALWAYS prefer computing from ui_answers when available - ensures current scores
                    # (handles timer redirect, retakes, session loss)
                    answers = {}
                    if assessment.analytics_data:
                        answers = assessment.analytics_data.get("ui_answers") or {}
                    if not answers:
                        answers = session.get("answers", {})
                    # Fallback: use scores stored in session by submit (survives redirect)
                    computed = session.get("computed_scores")
                    if not answers and computed and computed.get("total", 0) > 0:
                        total_score = computed.get("total", 0)
                        assessment.status = _models_assessment.AssessmentStatus.COMPLETED
                        assessment.completed_at = datetime.now()
                        assessment.total_score = total_score
                        assessment.listening_score = computed.get("listening", 0)
                        assessment.time_numbers_score = computed.get("time_numbers", 0)
                        assessment.grammar_score = computed.get("grammar", 0)
                        assessment.vocabulary_score = computed.get("vocabulary", 0)
                        assessment.reading_score = computed.get("reading", 0)
                        assessment.speaking_score = computed.get("speaking", 0)
                        _, safety_ok, speaking_ok, final_pass = compute_overall_pass(
                            float(total_score),
                            float(computed.get("speaking", 0)),
                            1.0,
                        )
                        assessment.passed = final_pass
                        assessment.safety_questions_passed = safety_ok
                        assessment.speaking_threshold_passed = speaking_ok
                        await db.commit()
                        logger.info(f"Results page: used session computed_scores fallback, total={total_score}")
                    elif answers:
                            module_scores = {"listening": 0, "time_numbers": 0, "grammar": 0, "vocabulary": 0, "reading": 0, "speaking": 0}
                            for _q, answer_data in answers.items():
                                if isinstance(answer_data, str) and ":" in answer_data:
                                    parts = answer_data.split(":")
                                    module = parts[0].lower().replace(" & ", "_").replace(" ", "_")
                                    try:
                                        points = int(parts[1])
                                    except (ValueError, IndexError):
                                        points = 0
                                elif isinstance(answer_data, dict):
                                    module = answer_data.get("module", "unknown").lower().replace(" & ", "_").replace(" ", "_")
                                    points = answer_data.get("points_earned", 0)
                                else:
                                    continue
                                if module in module_scores:
                                    module_scores[module] += points
                            module_max = {
                                "listening": 16,
                                "time_numbers": 16,
                                "grammar": 16,
                                "vocabulary": 16,
                                "reading": 16,
                                "speaking": 20,
                            }
                            for m in module_scores:
                                module_scores[m] = min(module_scores[m], module_max[m])
                            total = min(100, sum(module_scores.values()))
                            assessment.status = _models_assessment.AssessmentStatus.COMPLETED
                            assessment.completed_at = datetime.now()
                            assessment.total_score = total
                            assessment.listening_score = module_scores["listening"]
                            assessment.time_numbers_score = module_scores["time_numbers"]
                            assessment.grammar_score = module_scores["grammar"]
                            assessment.vocabulary_score = module_scores["vocabulary"]
                            assessment.reading_score = module_scores["reading"]
                            assessment.speaking_score = module_scores["speaking"]
                            _, safety_ok, speaking_ok, final_pass = compute_overall_pass(
                                float(total), float(module_scores["speaking"]), 1.0
                            )
                            assessment.passed = final_pass
                            assessment.safety_questions_passed = safety_ok
                            assessment.speaking_threshold_passed = speaking_ok
                            await db.commit()
                            logger.info(f"Calculated scores on results page for assessment {assessment_id} (timer/direct): total={total}")

                    # Use actual scores from database (calculated by complete_assessment or above)
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
                    if assessment.status == _models_assessment.AssessmentStatus.COMPLETED:
                        # Check if email was already sent (use a session flag)
                        email_sent_key = f"email_sent_{assessment_id}"
                        if not session.get(email_sent_key):
                            try:
                                from services.email_service import get_email_service
                                # Get user info
                                user_result = await db.execute(
                                    sqlalchemy.select(_models_assessment.User).where(_models_assessment.User.id == assessment.user_id)
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

        # If assessment exists but all scores are 0 (incomplete / never submitted), don't show 0s
        if total_score == 0:
            logger.warning("Results page: assessment has no score (incomplete), returning 404")
            raise HTTPException(
                status_code=404,
                detail="Assessment not complete or no answers recorded. Complete the assessment first, or view sample results: /results?demo=1"
            )

        total_possible = sum(m["possible"] for m in modules)
        operation = session.get("operation", "HOTEL")
        return _render_results_page(request, modules, operation)

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
                    sqlalchemy.select(_models_assessment.Assessment).where(_models_assessment.Assessment.id == assessment_id)
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
    For Hotel and Marine operations, shows department dropdown for question variety.
    """
    try:
        departments = []
        if operation:
            from config.departments import get_departments_by_operation
            op_lower = operation.upper()
            if op_lower == "HOTEL":
                departments = get_departments_by_operation("hotel")
            elif op_lower == "MARINE":
                departments = get_departments_by_operation("marine")
        # When user came from an invitation, we have a fixed department; pass it so template can show it and hide dropdown
        from_invitation = bool(request.session.get("invitation_code"))
        department_from_invitation = request.session.get("department") if from_invitation else None
        return render_template(
            request,
            "pre_test.html",
            {
                "operation": operation,
                "departments": departments,
                "from_invitation": from_invitation,
                "department_from_invitation": department_from_invitation
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
async def invitation_verify_page(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """
    Invitation code verification page
    
    Users must verify their invitation code before accessing registration.
    Supports both URL-based code (auto-verify) and manual input.
    
    Args:
        code: Optional invitation code from URL (auto-verify)
        error: Optional error code from redirect (invalid, completed, used, expired)
    """
    try:
        return render_template(
            request,
            "invitation_verify.html",
            {
                "code": code,
                "error": error
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
    REQUIRES invitation code for access - shows error message if code is invalid/missing
    
    Args:
        code: Required invitation code from admin
    """
    try:
        from models.assessment import InvitationCode
        from sqlalchemy import func
        
        # Prepare error message variable
        error_message = None
        
        # REQUIRE invitation code - show error if not provided
        if not code:
            logger.info("Registration page accessed without invitation code")
            error_message = "No invitation code provided. Please use the link from your invitation email."
            return render_template(
                request,
                "registration.html",
                {
                    "invitation_code": "",
                    "error_message": error_message
                }
            )
        
        # Validate the invitation code (case-insensitive comparison)
        result = await db.execute(
            sqlalchemy.select(InvitationCode).where(func.upper(InvitationCode.code) == code.upper())
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            logger.warning(f"Invalid invitation code attempted: {code[:4]}...")
            error_message = "Invalid invitation code. Please check your invitation link or contact the administrator."
            return render_template(
                request,
                "registration.html",
                {
                    "invitation_code": code,
                    "error_message": error_message
                }
            )
        
        # Check if assessment already completed
        if invitation.assessment_completed:
            logger.info(f"Invitation code {code[:4]}... already completed assessment")
            error_message = "This invitation has already been used and the assessment has been completed."
            return render_template(
                request,
                "registration.html",
                {
                    "invitation_code": code,
                    "error_message": error_message
                }
            )
        
        if invitation.is_used:
            logger.info(f"Invitation code {code[:4]}... already used")
            error_message = "This invitation code has already been used."
            return render_template(
                request,
                "registration.html",
                {
                    "invitation_code": code,
                    "error_message": error_message
                }
            )
        
        # Check expiration
        if invitation.expires_at and invitation.expires_at < datetime.now():
            logger.info(f"Invitation code {code[:4]}... expired")
            error_message = "This invitation code has expired. Please contact the administrator for a new invitation."
            return render_template(
                request,
                "registration.html",
                {
                    "invitation_code": code,
                    "error_message": error_message
                }
            )

        # CRITICAL: Clear session when user accesses a DIFFERENT invitation link
        # This ensures each department gets its own assessment - no reuse of old assessment_id
        session_inv_code = (request.session.get("invitation_code") or "").strip().upper()
        new_code_upper = (code or "").strip().upper()
        if session_inv_code and session_inv_code != new_code_upper:
            # Different invitation - clear session so registration creates fresh assessment
            for key in ("assessment_id", "invitation_code", "operation", "answers"):
                request.session.pop(key, None)
            logger.info(f"Cleared session for new invitation (was {session_inv_code[:4]}..., now {new_code_upper[:4]}...)")

        # Track which invitation link user is viewing (for session-clear detection on next visit)
        request.session["invitation_code"] = code.strip()

        return render_template(
            request,
            "registration.html",
            {
                "invitation_code": code,
                "error_message": None
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
            {"admin_key": settings.ADMIN_API_KEY}
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
            {"admin_key": settings.ADMIN_API_KEY}
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


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """
    User Management - List and manage registered users
    Protected: Requires admin authentication
    """
    try:
        if not request.session.get("is_admin"):
            return RedirectResponse(url="/login", status_code=303)

        return render_template(
            request,
            "admin_users.html",
            {"admin_key": settings.ADMIN_API_KEY}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering admin users page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading user management page")


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
            {"admin_key": settings.ADMIN_API_KEY}
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
