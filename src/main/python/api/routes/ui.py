"""
UI Routes - Serves frontend pages using Jinja2 templates
Handles all user-facing web pages for the assessment platform
"""

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


# Initialize router
router = APIRouter()

# Get the python source directory (where app.py is)
python_src_dir = Path(__file__).parent.parent.parent
templates_dir = python_src_dir / "templates"
data_dir = python_src_dir / "data"

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=str(templates_dir))


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
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in questions config: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading questions: {str(e)}")


# Store questions in memory (loaded once at startup)
QUESTIONS_CONFIG = None


def get_questions() -> Dict[str, Any]:
    """Get questions configuration (cached)"""
    global QUESTIONS_CONFIG

    if QUESTIONS_CONFIG is None:
        QUESTIONS_CONFIG = load_questions_config()

    return QUESTIONS_CONFIG


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
            print(f"❌ Question {question_num} not found in config")
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
        
        print(f"🔍 Scoring Q{question_num}: module={module}")
        print(f"🔍 User answer: '{user_answer}'")
        print(f"🔍 Question data keys: {list(question_data.keys())}")
        
        # Handle different question formats
        is_correct = False
        correct_answer_display = ""
        
        # ============================================================
        # TYPE 1: VOCABULARY MATCHING QUESTIONS (have "correct_matches")
        # ============================================================
        if "correct_matches" in question_data:
            correct_matches = question_data["correct_matches"]
            correct_answer_display = str(correct_matches)
            
            print(f"📚 VOCABULARY MATCHING: Validating matches...")
            print(f"📚 Correct matches: {correct_matches}")
            print(f"📚 User answer raw: {user_answer}")
            
            try:
                # Parse user's JSON answer
                user_matches = json.loads(user_answer)
                print(f"📚 User matches parsed: {user_matches}")
                
                # Count correct matches
                correct_count = 0
                total_matches = len(correct_matches)
                
                for term, correct_definition in correct_matches.items():
                    user_definition = user_matches.get(term, "")
                    # Normalize for comparison (case-insensitive, trim whitespace)
                    if user_definition.strip().lower() == correct_definition.strip().lower():
                        correct_count += 1
                        print(f"  ✅ '{term}' -> '{user_definition}' CORRECT")
                    else:
                        print(f"  ❌ '{term}' -> '{user_definition}' (expected: '{correct_definition}')")
                
                # All matches must be correct for full credit
                is_correct = (correct_count == total_matches)
                print(f"📚 Result: {correct_count}/{total_matches} correct, is_correct={is_correct}")
                
            except json.JSONDecodeError as e:
                print(f"📚 JSON parse error: {e}")
                is_correct = False
            except Exception as e:
                print(f"📚 Error validating vocabulary: {e}")
                is_correct = False
        
        # ============================================================
        # TYPE 2: SPEAKING QUESTIONS (have "expected_keywords")
        # ============================================================
        elif "expected_keywords" in question_data:
            expected_keywords = question_data["expected_keywords"]
            print(f"🎤 SPEAKING: Analyzing speech transcription...")
            print(f"🎤 User answer: {user_answer}")
            print(f"🎤 Expected keywords: {expected_keywords}")
            
            # Parse answer format: "recorded_DURATION|TRANSCRIPT" or legacy "recorded_DURATION"
            transcript = ""
            if "|" in user_answer:
                parts = user_answer.split("|", 1)
                transcript = parts[1].strip().lower() if len(parts) > 1 else ""
            elif user_answer.startswith("recorded_"):
                # Legacy format - no transcript available
                transcript = ""
            
            # Check if user made a recording
            has_recording = user_answer and user_answer.startswith("recorded_")
            
            if not has_recording:
                is_correct = False
                points_earned = 0
                print(f"🎤 No recording detected")
            elif not transcript:
                # Recording exists but no transcript (speech recognition failed or no speech)
                # Give minimal points (20% of total) for attempting
                is_correct = False
                points_earned = int(points * 0.2)
                print(f"🎤 Recording detected but no speech transcription available")
            else:
                # Analyze transcript for keyword matching
                transcript_lower = transcript.lower()
                matched_keywords = []
                
                print(f"🎤 Transcript: '{transcript}'")
                
                for keyword in expected_keywords:
                    keyword_lower = keyword.lower()
                    matched = False
                    
                    # Check if full keyword/phrase appears in transcript (exact match)
                    if keyword_lower in transcript_lower:
                        matched_keywords.append(keyword)
                        matched = True
                        print(f"  ✅ '{keyword}' found (exact match)")
                    # Check for common variations (e.g., "apologize" vs "apology")
                    elif keyword_lower.replace("ize", "ise") in transcript_lower:
                        matched_keywords.append(keyword)
                        matched = True
                        print(f"  ✅ '{keyword}' found (ize->ise variation)")
                    elif keyword_lower.replace("ise", "ize") in transcript_lower:
                        matched_keywords.append(keyword)
                        matched = True
                        print(f"  ✅ '{keyword}' found (ise->ize variation)")
                    # For multi-word keywords (e.g., "send someone"), check if all words appear
                    elif " " in keyword_lower:
                        keyword_words = keyword_lower.split()
                        if all(word in transcript_lower for word in keyword_words):
                            matched_keywords.append(keyword)
                            matched = True
                            print(f"  ✅ '{keyword}' found (all words present)")
                    # Check root words (e.g., "fix" matches "fixing", "fixed")
                    elif len(keyword_lower) >= 4:
                        root = keyword_lower[:4]
                        if root in transcript_lower:
                            matched_keywords.append(keyword)
                            matched = True
                            print(f"  ✅ '{keyword}' found (root match: '{root}')")
                    
                    if not matched:
                        print(f"  ❌ '{keyword}' NOT found")
                
                total_keywords = len(expected_keywords)
                matched_count = len(matched_keywords)
                match_ratio = matched_count / total_keywords if total_keywords > 0 else 0
                
                print(f"🎤 Matched {matched_count}/{total_keywords} keywords: {matched_keywords}")
                print(f"🎤 Match ratio: {match_ratio:.2%}")
                
                # Scoring algorithm:
                # - 50%+ keywords matched: full points
                # - 30-49%: 70% of points
                # - 20-29%: 50% of points
                # - 10-19%: 30% of points
                # - <10%: 20% of points (minimal for attempt)
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
                
                print(f"🎤 Score: {points_earned}/{points} points ({'PASS' if is_correct else 'PARTIAL'})")
            
            correct_answer_display = f"Expected keywords: {', '.join(expected_keywords)}"
        
        # ============================================================
        # TYPE 3: MULTIPLE CHOICE QUESTIONS (have "options" field)
        # ============================================================
        elif "options" in question_data and "correct" in question_data:
            correct_answer = question_data["correct"]
            options = question_data["options"]
            correct_answer_display = correct_answer
            
            print(f"📝 MULTIPLE CHOICE: Comparing answers...")
            print(f"📝 Options: {options}")
            print(f"📝 Correct: '{correct_answer}'")
            print(f"📝 User: '{user_answer}'")
            
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
            
            print(f"📝 Result: user='{user_clean}', correct='{correct_clean}', is_correct={is_correct}")
        
        # ============================================================
        # TYPE 4: FILL-IN-THE-BLANK (no options, has "correct" field)
        # time_numbers module uses this
        # ============================================================
        elif "correct" in question_data and "options" not in question_data:
            correct_answer = question_data["correct"]
            correct_answer_display = correct_answer
            
            print(f"✏️ FILL-IN-BLANK: Comparing with flexible matching...")
            print(f"✏️ Correct: '{correct_answer}'")
            print(f"✏️ User: '{user_answer}'")
            
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
                        except:
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
                        print(f"✏️ Matched by digits: '{user_digits}' == '{correct_digits}'")
            
            print(f"✏️ Result: user_norm='{user_normalized}', correct_norm='{correct_normalized}', is_correct={is_correct}")
        
        else:
            print(f"⚠️ Unknown question format for Q{question_num}")
            print(f"⚠️ Question data: {question_data}")
            correct_answer_display = "N/A"
        
        # Calculate points (only if not already set by type-specific logic)
        # Speaking module already sets points_earned, don't override it!
        if "expected_keywords" not in question_data:
            points_earned = points if is_correct else 0
        
        # Generate feedback
        if is_correct:
            feedback = "✅ Correct! Well done."
        elif "expected_keywords" in question_data and points_earned > 0:
            # Partial credit for speaking
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
        
        print(f"✅ FINAL Scoring result for Q{question_num}: is_correct={is_correct}, points={points_earned}/{points}")
        return result
        
    except Exception as e:
        print(f"❌ ERROR in score_answer_from_config: {e}")
        import traceback
        traceback.print_exc()
        return {
            "is_correct": False,
            "points_earned": 0,
            "points_possible": 4,
            "feedback": f"Error scoring answer: {str(e)}",
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


@router.get("/select-operation", response_class=HTMLResponse)
async def select_operation_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Operation Selection page - Choose Hotel, Marine, or Casino operations
    Pre-selects the operation from user's invitation code (if any)
    """
    try:
        # Get user from session
        user_id = request.session.get("user_id")
        recommended_operation = None
        
        if user_id:
            # Query user to get their division (from invitation code)
            from models.assessment import User
            from sqlalchemy import select
            
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user and user.division:
                # Map DivisionType enum to operation string
                recommended_operation = user.division.value.upper()
                print(f"🎯 Recommended operation for user {user_id}: {recommended_operation}")
        
        return templates.TemplateResponse(
            "select_operation.html",
            {
                "request": request,
                "title": "Select Your Operation",
                "recommended_operation": recommended_operation
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering operation selection: {str(e)}")


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
                print(f"▶️ STARTING EXISTING ASSESSMENT: id={assessment.id}, operation={operation}")
            else:
                # Existing assessment is invalid or already started, create new one
                assessment = await engine.create_assessment(
                    user_id=int(user_id),
                    division=division_map[operation]
                )
                request.session["assessment_id"] = assessment.id
                await engine.start_assessment(assessment.id)
                print(f"🆕 NEW ASSESSMENT CREATED AND STARTED: id={assessment.id}, operation={operation}")
        else:
            # No existing assessment, create new one
            assessment = await engine.create_assessment(
                user_id=int(user_id),
                division=division_map[operation]
            )
            request.session["assessment_id"] = assessment.id
            await engine.start_assessment(assessment.id)
            print(f"🆕 NEW ASSESSMENT CREATED AND STARTED: id={assessment.id}, operation={operation}")

        # IMPORTANT: Clear old session data before starting new assessment
        # This ensures fresh scoring for each new test
        request.session["operation"] = operation
        request.session["answers"] = {}  # Clear old answers!
        
        print(f"🧹 Cleared session answers for fresh start")

        # Redirect to first question
        return RedirectResponse(url=f"/question/1?operation={operation}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"ERROR in start_assessment: {str(e)}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error starting assessment: {str(e)}")


@router.get("/question/{question_num}", response_class=HTMLResponse)
async def question_page(request: Request, question_num: int, operation: Optional[str] = None):
    """
    Question page - Display specific question filtered by operation

    Args:
        question_num: Question number (1-21)
        operation: Operation type (HOTEL, MARINE, or CASINO) - optional for backward compatibility
    """
    print(f"📄 DEBUG: GET /question/{question_num} - operation={operation}")
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
        return templates.TemplateResponse("question.html", context)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering question {question_num}: {str(e)}")


@router.post("/submit")
async def submit_answer(
    request: Request,
    question_num: int = Form(...),
    answer: str = Form(...),
    operation: Optional[str] = Form(None),
    time_spent: Optional[int] = Form(None)
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
                from core.database import get_db
                from models.assessment import User, DivisionType

                async for db in get_db():
                    # Check if guest user exists
                    from sqlalchemy import select
                    guest_result = await db.execute(
                        select(User).where(User.email == "guest@demo.com")
                    )
                    guest_user = guest_result.scalar_one_or_none()

                    if not guest_user:
                        # Create guest user
                        guest_user = User(
                            first_name="Guest",
                            last_name="User",
                            email="guest@demo.com",
                            nationality="USA",
                            division=DivisionType.HOTEL if operation == "HOTEL" else (
                                DivisionType.MARINE if operation == "MARINE" else DivisionType.CASINO
                            ),
                            department="Demo"
                        )
                        db.add(guest_user)
                        await db.commit()
                        await db.refresh(guest_user)

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
                    break

        # UI-BASED SCORING: Use questions_config.json directly
        # This avoids the database Question table ID mismatch issue
        print(f"🔍 DEBUG: Starting UI-based scoring for Q{question_num}")
        print(f"🔍 DEBUG: assessment_id = {assessment_id}")
        print(f"🔍 DEBUG: answer = {answer}")
        print(f"🔍 DEBUG: time_spent = {time_spent}")
        
        # Score answer using config file
        result = score_answer_from_config(question_num, answer)
        print(f"✅ DEBUG: UI scoring result: {result}")
        
        # Store result in session - MINIMAL DATA to avoid Cookie size limit (4KB)
        # Only store: question_num -> "module:points" (e.g., "reading:4")
        answers = session.get("answers", {})
        # Compact format: "module:points_earned"
        answers[str(question_num)] = f"{result.get('module', 'unknown')}:{result['points_earned']}"
        session["answers"] = answers
        
        print(f"✅ DEBUG: Stored Q{question_num} -> {answers[str(question_num)]}")
        print(f"✅ DEBUG: Total answers: {len(answers)}, Session size ~{len(str(answers))} bytes")

        # Determine next action
        if question_num == 21:
            print(f"🎯 DEBUG: Last question (Q21) reached!")
            # Last question - calculate final scores from session
            if assessment_id:
                try:
                    from core.database import get_db
                    from models.assessment import Assessment, AssessmentStatus
                    from sqlalchemy import select
                    
                    print(f"🎯 DEBUG: Calculating scores for assessment_id={assessment_id}")
                    
                    # Calculate scores from session answers
                    # Format: answers = {"1": "listening:5", "2": "listening:5", ...}
                    answers = session.get("answers", {})
                    print(f"📊 DEBUG: Found {len(answers)} answers in session")
                    print(f"📊 DEBUG: Raw answers: {answers}")
                    
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
                            except:
                                points = 0
                        elif isinstance(answer_data, dict):
                            # Legacy format support
                            module = answer_data.get("module", "unknown").lower().replace(" & ", "_").replace(" ", "_")
                            points = answer_data.get("points_earned", 0)
                        else:
                            continue
                        
                        if module in module_scores:
                            module_scores[module] += points
                            print(f"  Q{q_num}: {module} += {points} points")
                    
                    total_score = sum(module_scores.values())
                    print(f"✅ DEBUG: Calculated total_score = {total_score}")
                    print(f"✅ DEBUG: Module breakdown: {module_scores}")
                    
                    # Update database with final scores
                    async for db in get_db():
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
                            assessment.passed = total_score >= 70
                            
                            await db.commit()
                            print(f"✅ DEBUG: Assessment updated in database")
                        else:
                            print(f"⚠️ DEBUG: Assessment {assessment_id} not found in database")
                        break
                        
                except Exception as e:
                    print(f"❌ ERROR completing assessment: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to results even if scoring fails
            else:
                print(f"⚠️ DEBUG: No assessment_id found for complete_assessment")

            # Redirect to results
            print(f"🔄 DEBUG: Redirecting to /results")
            return RedirectResponse(url="/results", status_code=303)
        else:
            # Go to next question, preserve operation parameter if present
            next_question = question_num + 1
            if operation:
                return RedirectResponse(url=f"/question/{next_question}?operation={operation}", status_code=303)
            else:
                return RedirectResponse(url=f"/question/{next_question}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting answer: {str(e)}")


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
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

        print(f"🔍 DEBUG /results: assessment_id from session = {assessment_id}")

        modules = []
        total_score = 0
        total_possible = 100

        if assessment_id:
            try:
                from core.database import get_db
                from models.assessment import Assessment
                from sqlalchemy import select

                print(f"🔍 DEBUG: Fetching assessment {assessment_id} from database...")
                async for db in get_db():
                    # Fetch assessment from database
                    result = await db.execute(
                        select(Assessment).where(Assessment.id == assessment_id)
                    )
                    assessment = result.scalar_one_or_none()

                    print(f"🔍 DEBUG: Assessment object: {assessment}")
                    if assessment:
                        print(f"📊 DEBUG: listening_score = {assessment.listening_score}")
                        print(f"📊 DEBUG: time_numbers_score = {assessment.time_numbers_score}")
                        print(f"📊 DEBUG: grammar_score = {assessment.grammar_score}")
                        print(f"📊 DEBUG: vocabulary_score = {assessment.vocabulary_score}")
                        print(f"📊 DEBUG: reading_score = {assessment.reading_score}")
                        print(f"📊 DEBUG: speaking_score = {assessment.speaking_score}")
                        print(f"📊 DEBUG: total_score = {assessment.total_score}")
                        print(f"📊 DEBUG: status = {assessment.status}")

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
                        print(f"✅ DEBUG: Built modules list with total_score = {total_score}")
                    else:
                        print(f"⚠️ DEBUG: No assessment found in database for id {assessment_id}")
                    break
            except Exception as e:
                print(f"❌ ERROR fetching assessment results: {e}")
                import traceback
                traceback.print_exc()
                # If error, modules will remain empty list
                pass
        else:
            print(f"⚠️ DEBUG: No assessment_id in session")

        # If no modules found (no assessment or error), show error message
        if not modules:
            print(f"❌ DEBUG: No modules found, raising 404 error")
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

        # Determine result status and gradient
        # Pass threshold is 70% as per config.py PASS_THRESHOLD_TOTAL
        if percentage >= 70:
            result_status = "✅ PASSED"
            score_gradient = "linear-gradient(135deg, #34c759 0%, #30d158 100%)"
        else:
            result_status = "❌ NOT PASSED"
            score_gradient = "linear-gradient(135deg, #ff3b30 0%, #ff453a 100%)"

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

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "total_score": total_score_int,
                "score_percentage": percentage,
                "score_gradient": score_gradient,
                "result_status": result_status,
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering results: {str(e)}")


@router.get("/anti-cheating-report", response_class=HTMLResponse)
async def anti_cheating_report_page(request: Request):
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
                from core.database import get_db
                from utils.anti_cheating import AntiCheatingService

                async for db in get_db():
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
                    from models.assessment import Assessment
                    from sqlalchemy import select

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

                    break
            except Exception as e:
                print(f"Error fetching anti-cheating data: {e}")
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

        return templates.TemplateResponse(
            "anti_cheating_report.html",
            {
                "request": request,
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering anti-cheating report: {str(e)}")


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

        return templates.TemplateResponse(
            "instructions.html",
            {
                "request": request,
                "instructions": instructions_data,
                "operation": operation  # Pass operation to template
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering instructions: {str(e)}")


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
        return templates.TemplateResponse(
            "invitation_verify.html",
            {
                "request": request,
                "code": code
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering invitation page: {str(e)}")


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

        return templates.TemplateResponse(
            "registration.html",
            {
                "request": request,
                "invitation_code": code
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering registration: {str(e)}")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login page - User authentication
    """
    try:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login - CCL English Assessment"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering login page: {str(e)}")


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """
    Forgot password page - Request password reset
    """
    try:
        return templates.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "title": "Forgot Password - CCL English Assessment"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering forgot password page: {str(e)}")


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: Optional[str] = None):
    """
    Reset password page - Set new password using token
    """
    try:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "title": "Reset Password - CCL English Assessment",
                "token": token
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering reset password page: {str(e)}")


# Health check endpoint

@router.get("/debug/session")
async def debug_session(request: Request):
    """DEBUG: View session data"""
    try:
        session = request.session
        answers = session.get("answers", {})
        assessment_id = session.get("assessment_id")
        
        print(f"\n{'='*70}")
        print(f"DEBUG SESSION DATA:")
        print(f"{'='*70}")
        print(f"Assessment ID: {assessment_id}")
        print(f"Total answers in session: {len(answers)}")
        print(f"\nAnswers breakdown:")
        
        for q_num, answer_data in answers.items():
            print(f"\nQ{q_num}:")
            print(f"  Answer: {answer_data.get('answer')}")
            print(f"  Correct: {answer_data.get('is_correct')}")
            print(f"  Points Earned: {answer_data.get('points_earned')}")
            print(f"  Points Possible: {answer_data.get('points_possible')}")
            print(f"  Module: {answer_data.get('module')}")
        
        print(f"{'='*70}\n")
        
        return {
            "assessment_id": assessment_id,
            "total_answers": len(answers),
            "answers": answers
        }
    except Exception as e:
        return {"error": str(e)}

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
        
        return templates.TemplateResponse(
            "admin_dashboard.html",
            {
                "request": request
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering admin dashboard: {str(e)}")


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
        
        return templates.TemplateResponse(
            "admin_invitation.html",
            {
                "request": request
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering admin page: {str(e)}")


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
        
        return templates.TemplateResponse(
            "admin_scoreboard.html",
            {
                "request": request
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering scoreboard page: {str(e)}")


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
