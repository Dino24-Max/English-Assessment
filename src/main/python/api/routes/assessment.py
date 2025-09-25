"""
Assessment API endpoints
Handles all assessment-related operations
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from core.database import get_db
from core.assessment_engine import AssessmentEngine
from models.assessment import User, Assessment, DivisionType, AssessmentStatus
from data.question_bank_loader import QuestionBankLoader
from services.ai_service import AIService
from utils.anti_cheating import AntiCheatingService


router = APIRouter()


@router.post("/register")
async def register_candidate(
    candidate_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Register a new candidate for assessment"""

    try:
        # Validate required fields
        required_fields = ["first_name", "last_name", "email", "nationality", "division", "department"]
        for field in required_fields:
            if field not in candidate_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Check if email already exists
        existing_user = await db.execute(
            select(User).where(User.email == candidate_data["email"])
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create new user
        user = User(
            first_name=candidate_data["first_name"],
            last_name=candidate_data["last_name"],
            email=candidate_data["email"],
            nationality=candidate_data["nationality"],
            division=DivisionType(candidate_data["division"]),
            department=candidate_data["department"]
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return {
            "user_id": user.id,
            "message": "Candidate registered successfully",
            "next_step": "create_assessment"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_assessment(
    user_id: int,
    division: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create new assessment session"""

    try:
        # Validate division
        try:
            division_enum = DivisionType(division.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid division")

        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for existing incomplete assessments
        existing = await db.execute(
            select(Assessment).where(
                and_(
                    Assessment.user_id == user_id,
                    Assessment.status.in_([AssessmentStatus.NOT_STARTED, AssessmentStatus.IN_PROGRESS])
                )
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User has incomplete assessment")

        # Create assessment using engine
        engine = AssessmentEngine(db)
        assessment = await engine.create_assessment(user_id, division_enum)

        # Record anti-cheating data
        anti_cheat = AntiCheatingService()
        await anti_cheat.record_session_start(assessment.id, request)

        return {
            "assessment_id": assessment.id,
            "session_id": assessment.session_id,
            "division": assessment.division,
            "expires_at": assessment.expires_at,
            "status": "created",
            "next_step": "start_assessment"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assessment_id}/start")
async def start_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Start assessment and get questions"""

    try:
        engine = AssessmentEngine(db)
        result = await engine.start_assessment(assessment_id)

        return {
            "status": "started",
            "assessment_data": result,
            "instructions": {
                "listening": "Listen carefully to each dialogue. You can replay each audio twice maximum.",
                "time_numbers": "Fill in the missing time or number. You have 10 seconds per question.",
                "grammar": "Choose the correct answer to complete the sentence.",
                "vocabulary": "Match words to their correct categories.",
                "reading": "Read the text and choose the best title.",
                "speaking": "Speak your response clearly. Maximum 20 seconds per question."
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assessment_id}/answer")
async def submit_answer(
    assessment_id: int,
    answer_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Submit answer for a question"""

    try:
        required_fields = ["question_id", "user_answer"]
        for field in required_fields:
            if field not in answer_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        engine = AssessmentEngine(db)
        result = await engine.submit_response(
            assessment_id=assessment_id,
            question_id=answer_data["question_id"],
            user_answer=answer_data["user_answer"],
            time_spent=answer_data.get("time_spent")
        )

        return {
            "status": "answer_recorded",
            "result": result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assessment_id}/speaking")
async def submit_speaking_response(
    assessment_id: int,
    question_id: int,
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Submit speaking module audio response"""

    try:
        # Validate file type
        if not audio_file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Invalid audio file")

        # Save audio file
        import os
        audio_dir = "data/audio/responses"
        os.makedirs(audio_dir, exist_ok=True)

        file_path = f"{audio_dir}/assessment_{assessment_id}_q_{question_id}_{int(datetime.now().timestamp())}.wav"

        with open(file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)

        # Process with AI service
        ai_service = AIService()

        # Get question details for analysis
        question = await db.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Analyze speech
        analysis = await ai_service.analyze_speech_response(
            file_path, question.correct_answer, question.question_text
        )

        # Submit response through engine
        engine = AssessmentEngine(db)
        result = await engine.submit_response(
            assessment_id=assessment_id,
            question_id=question_id,
            user_answer=analysis.get("transcript", ""),
            time_spent=None
        )

        # Update response with speech analysis
        response_record = await db.execute(
            select(AssessmentResponse).where(
                and_(
                    AssessmentResponse.assessment_id == assessment_id,
                    AssessmentResponse.question_id == question_id
                )
            )
        )

        response = response_record.scalar_one_or_none()
        if response:
            response.audio_file_path = file_path
            response.speech_analysis = analysis
            response.points_earned = analysis.get("total_points", 0)
            await db.commit()

        return {
            "status": "speaking_response_processed",
            "transcript": analysis.get("transcript"),
            "points_earned": analysis.get("total_points"),
            "feedback": analysis.get("feedback")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assessment_id}/complete")
async def complete_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Complete assessment and get final results"""

    try:
        engine = AssessmentEngine(db)
        result = await engine.complete_assessment(assessment_id)

        return {
            "status": "completed",
            "results": result,
            "certificate": {
                "issued": result["passed"],
                "score": result["total_score"],
                "grade": "PASS" if result["passed"] else "FAIL",
                "valid_until": "2026-12-31"  # Would calculate based on policy
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assessment_id}/status")
async def get_assessment_status(
    assessment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get current assessment status"""

    try:
        assessment = await db.get(Assessment, assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Get progress info
        responses = await db.execute(
            select(AssessmentResponse).where(AssessmentResponse.assessment_id == assessment_id)
        )

        responses_count = len(responses.scalars().all())

        return {
            "assessment_id": assessment.id,
            "status": assessment.status,
            "started_at": assessment.started_at,
            "completed_at": assessment.completed_at,
            "expires_at": assessment.expires_at,
            "total_score": assessment.total_score,
            "progress": {
                "questions_answered": responses_count,
                "total_questions": 21  # 4 per module × 5 + 1 speaking
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load-questions")
async def load_question_bank(
    admin_key: str,
    db: AsyncSession = Depends(get_db)
):
    """Load question bank (admin only)"""

    if admin_key != "admin123":  # In production, use proper authentication
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        loader = QuestionBankLoader(db)
        await loader.load_all_questions()

        return {
            "status": "success",
            "message": "Question bank loaded successfully",
            "divisions": ["hotel", "marine", "casino"],
            "modules": ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import required modules for the endpoints
from sqlalchemy import select, and_
from models.assessment import AssessmentResponse, Question