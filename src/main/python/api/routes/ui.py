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
            return {
                "is_correct": False,
                "points_earned": 0,
                "points_possible": 4,
                "feedback": "Question not found"
            }
        
        question_data = questions[question_key]
        correct_answer = question_data.get("correct_answer", "")
        points = question_data.get("points", 4)
        question_type = question_data.get("type", "multiple_choice")
        module = question_data.get("module", "unknown")
        
        # Normalize answers for comparison
        user_clean = user_answer.strip().lower()
        correct_clean = correct_answer.strip().lower()
        
        # Score based on question type
        if question_type in ["multiple_choice", "fill_blank", "title_selection"]:
            # Exact match (case-insensitive)
            is_correct = user_clean == correct_clean
        elif question_type == "category_match":
            # For category matching, allow flexible matching
            # User might answer in different order
            user_items = set(user_clean.replace(" ", "").split(","))
            correct_items = set(correct_clean.replace(" ", "").split(","))
            is_correct = user_items == correct_items
        else:
            # Default: exact match
            is_correct = user_clean == correct_clean
        
        points_earned = points if is_correct else 0
        
        # Generate feedback
        if is_correct:
            feedback = "✅ Correct! Well done."
        else:
            feedback = f"❌ Incorrect. The correct answer is: {correct_answer}"
        
        return {
            "is_correct": is_correct,
            "points_earned": points_earned,
            "points_possible": points,
            "feedback": feedback,
            "module": module
        }
        
    except Exception as e:
        print(f"❌ ERROR in score_answer_from_config: {e}")
        return {
            "is_correct": False,
            "points_earned": 0,
            "points_possible": 4,
            "feedback": f"Error scoring answer: {str(e)}"
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
async def select_operation_page(request: Request):
    """
    Operation Selection page - Choose Hotel, Marine, or Casino operations
    """
    try:
        return templates.TemplateResponse(
            "select_operation.html",
            {
                "request": request,
                "title": "Select Your Operation"
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
        from models.assessment import DivisionType
        import uuid

        engine = AssessmentEngine(db)

        # Map operation to division type
        division_map = {
            "HOTEL": DivisionType.HOTEL,
            "MARINE": DivisionType.MARINE,
            "CASINO": DivisionType.CASINO
        }

        # Create assessment
        assessment = await engine.create_assessment(
            user_id=int(user_id),
            division=division_map[operation]
        )

        # Store assessment_id in session for anti-cheating tracking
        request.session["assessment_id"] = assessment.id
        request.session["operation"] = operation

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
        
        # Store result in session
        if "answers" not in session:
            session["answers"] = {}
        
        session["answers"][str(question_num)] = {
            "answer": answer,
            "is_correct": result["is_correct"],
            "points_earned": result["points_earned"],
            "points_possible": result["points_possible"],
            "feedback": result["feedback"],
            "module": result.get("module", "unknown"),
            "time_spent": time_spent,
            "question_id": question_num
        }
        print(f"✅ DEBUG: Stored answer in session for Q{question_num}")

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
                    answers = session.get("answers", {})
                    print(f"📊 DEBUG: Found {len(answers)} answers in session")
                    
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
                        module = answer_data.get("module", "unknown").lower().replace(" & ", "_").replace(" ", "_")
                        points = answer_data.get("points_earned", 0)
                        
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
        percentage = round((total_score / total_possible) * 100, 1) if total_possible > 0 else 0

        # Determine result status and gradient
        if percentage >= 65:
            result_status = "✅ PASSED"
            score_gradient = "linear-gradient(135deg, #34c759 0%, #30d158 100%)"
        else:
            result_status = "❌ NOT PASSED"
            score_gradient = "linear-gradient(135deg, #ff3b30 0%, #ff453a 100%)"

        # Generate module HTML
        module_results = []
        for module in modules:
            module_percentage = round((module["score"] / module["possible"]) * 100, 1) if module["possible"] > 0 else 0
            module_html = f'''
            <div class="module-card">
                <div class="module-header">
                    <span class="module-icon">{module["icon"]}</span>
                    <span class="module-name">{module["name"]}</span>
                </div>
                <div class="module-score">{module["score"]}/{module["possible"]}</div>
                <div class="module-percentage">{module_percentage}%</div>
            </div>
            '''
            module_results.append(module_html)

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "total_score": total_score,
                "total_possible": total_possible,
                "percentage": percentage,
                "score_gradient": score_gradient,
                "result_status": result_status,
                "module_results": module_results
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


@router.get("/register", response_class=HTMLResponse)
async def registration_page(request: Request):
    """
    Registration page - Candidate information form
    """
    try:
        divisions_data = {
            "hotel": {
                "name": "Hotel Operations",
                "departments": [
                    "Front Desk / Guest Services",
                    "Housekeeping",
                    "Food & Beverage Service",
                    "Kitchen / Culinary",
                    "Bar Service",
                    "Entertainment",
                    "Spa & Wellness",
                    "Youth Staff"
                ]
            },
            "marine": {
                "name": "Marine Operations",
                "departments": [
                    "Deck Department",
                    "Engine Department",
                    "Technical Services"
                ]
            },
            "casino": {
                "name": "Casino Operations",
                "departments": [
                    "Gaming Tables",
                    "Slot Machines",
                    "Casino Administration"
                ]
            }
        }

        return templates.TemplateResponse(
            "registration.html",
            {
                "request": request,
                "divisions": divisions_data
            }
        )

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


# Health check endpoint
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
