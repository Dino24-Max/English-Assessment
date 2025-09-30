"""
UI Routes - Serves frontend pages using Jinja2 templates
Handles all user-facing web pages for the assessment platform
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path


# Initialize router
router = APIRouter()

# Get the project root directory
project_root = Path(__file__).parent.parent.parent.parent.parent
templates_dir = project_root / "templates"
data_dir = project_root / "src" / "main" / "python" / "data"

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


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, operation: Optional[str] = None):
    """
    Homepage - Welcome page with optional operation parameter
    If no operation is provided, redirect to operation selection
    """
    try:
        # If no operation specified, redirect to operation selection
        if not operation:
            return RedirectResponse(url="/select-operation", status_code=303)

        # Validate operation
        operation = operation.upper()
        valid_operations = ["HOTEL", "MARINE", "CASINO"]
        if operation not in valid_operations:
            return RedirectResponse(url="/select-operation", status_code=303)

        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "title": "Cruise Employee English Assessment",
                "operation": operation,
                "total_questions": 21,
                "total_points": 100,
                "passing_score": 65,
                "modules": [
                    {"name": "Listening", "questions": 3, "points": 12},
                    {"name": "Time & Numbers", "questions": 3, "points": 12},
                    {"name": "Grammar", "questions": 4, "points": 16},
                    {"name": "Vocabulary", "questions": 4, "points": 32},
                    {"name": "Reading", "questions": 4, "points": 24},
                    {"name": "Speaking", "questions": 3, "points": 60}
                ]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering homepage: {str(e)}")


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
async def start_assessment(request: Request, operation: str):
    """
    Start assessment with operation filter

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

        # Store operation in session or pass to first question
        # For now, redirect to first question with operation parameter
        return RedirectResponse(url=f"/question/1?operation={operation}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting assessment: {str(e)}")


@router.get("/question/{question_num}", response_class=HTMLResponse)
async def question_page(request: Request, question_num: int, operation: Optional[str] = None):
    """
    Question page - Display specific question filtered by operation

    Args:
        question_num: Question number (1-21)
        operation: Operation type (HOTEL, MARINE, or CASINO) - optional for backward compatibility
    """
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
        progress_percent = round((question_num / 21) * 100, 1)

        # Determine if this is the last question
        is_last_question = (question_num == 21)
        next_question = question_num + 1 if not is_last_question else None
        previous_question = question_num - 1 if question_num > 1 else None

        # Prepare context
        context = {
            "request": request,
            "question_num": question_num,
            "total_questions": 21,
            "progress_percent": progress_percent,
            "question_data": question_data,
            "module": question_data.get("module"),
            "is_last_question": is_last_question,
            "next_question": next_question,
            "previous_question": previous_question,
            "operation": operation  # Pass operation to template
        }

        # Select template based on module type
        module = question_data.get("module")
        template_map = {
            "listening": "question_listening.html",
            "time_numbers": "question_time_numbers.html",
            "grammar": "question_grammar.html",
            "vocabulary": "question_vocabulary.html",
            "reading": "question_reading.html",
            "speaking": "question_speaking.html"
        }

        template_name = template_map.get(module, "question.html")

        return templates.TemplateResponse(template_name, context)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering question {question_num}: {str(e)}")


@router.post("/submit")
async def submit_answer(
    request: Request,
    question_num: int = Form(...),
    answer: str = Form(...),
    time_spent: Optional[int] = Form(None)
):
    """
    Submit answer for a question

    Args:
        question_num: Question number
        answer: User's answer
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

        # Store answer in session or database
        # For now, this is a placeholder - in production, store in database
        # In a real implementation, you would:
        # 1. Get assessment_id from session
        # 2. Store answer in database via AssessmentEngine
        # 3. Calculate score

        # Determine next action
        if question_num == 21:
            # Last question - redirect to results
            return RedirectResponse(url="/results", status_code=303)
        else:
            # Go to next question
            next_question = question_num + 1
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
        # In production, fetch actual results from database
        # For now, return template with placeholder data

        # Placeholder results (would come from database)
        results_data = {
            "candidate_name": "John Doe",
            "assessment_date": "2025-09-30",
            "total_score": 0,
            "total_possible": 100,
            "passing_score": 65,
            "passed": False,
            "grade": "FAIL",
            "module_scores": [
                {"module": "Listening", "score": 0, "possible": 12},
                {"module": "Time & Numbers", "score": 0, "possible": 12},
                {"module": "Grammar", "score": 0, "possible": 16},
                {"module": "Vocabulary", "score": 0, "possible": 32},
                {"module": "Reading", "score": 0, "possible": 24},
                {"module": "Speaking", "score": 0, "possible": 60}
            ],
            "recommendations": [
                "Complete the assessment to see your results",
                "Review all modules for accurate scoring"
            ]
        }

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "results": results_data
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering results: {str(e)}")


@router.get("/instructions", response_class=HTMLResponse)
async def instructions_page(request: Request):
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
                "instructions": instructions_data
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
            "register.html",
            {
                "request": request,
                "divisions": divisions_data
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering registration: {str(e)}")


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
