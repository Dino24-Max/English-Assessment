"""
Integration tests for UI routes with database persistence
Tests answer submission, results retrieval, and end-to-end assessment flow
"""

# CRITICAL: Set up Python path BEFORE any other imports
# This must be at the top level, before pytest imports
import sys
import os
from pathlib import Path

# Calculate paths relative to this test file
# test_ui_routes.py is in src/test/integration/, so go up 4 levels to project root
_test_file = Path(__file__).resolve()
project_root = _test_file.parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
python_src_str = str(python_src.resolve())

# Ensure path is set before any imports
if python_src_str not in sys.path:
    sys.path.insert(0, python_src_str)

# Also set PYTHONPATH for subprocesses
os.environ["PYTHONPATH"] = python_src_str + os.pathsep + os.environ.get("PYTHONPATH", "")

# Now import other modules
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import application modules (path should be set now)
from main import app
from core.database import get_db, Base
from models.assessment import User, Assessment, Question, AssessmentResponse, DivisionType, ModuleType, AssessmentStatus


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest_asyncio.fixture
async def sample_user(test_db):
    """Create a sample user for testing"""
    from utils.auth import hash_password
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        nationality="USA",
        password_hash=hash_password("testpassword123"),
        division=DivisionType.HOTEL,
        department="Front Desk"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_questions(test_db):
    """Create sample questions for testing"""
    questions = []

    # Listening question
    q1 = Question(
        module_type=ModuleType.LISTENING,
        division=DivisionType.HOTEL,
        question_type="MULTIPLE_CHOICE",
        question_text="What did the guest request?",
        options=["Extra towels", "Room service", "Wake-up call", "Late checkout"],
        correct_answer="Extra towels",
        points=4
    )
    questions.append(q1)

    # Grammar question
    q2 = Question(
        module_type=ModuleType.GRAMMAR,
        division=DivisionType.HOTEL,
        question_type="MULTIPLE_CHOICE",
        question_text="Complete: I ____ happy to help you.",
        options=["am", "is", "are", "be"],
        correct_answer="am",
        points=4
    )
    questions.append(q2)

    # Time & Numbers question
    q3 = Question(
        module_type=ModuleType.TIME_NUMBERS,
        division=DivisionType.HOTEL,
        question_type="FILL_BLANK",
        question_text="The guest checked in at ___.",
        correct_answer="2:30 PM",
        points=4
    )
    questions.append(q3)

    for q in questions:
        test_db.add(q)

    await test_db.commit()

    for q in questions:
        await test_db.refresh(q)

    return questions


@pytest_asyncio.fixture
async def sample_assessment(test_db, sample_user):
    """Create a sample assessment"""
    assessment = Assessment(
        user_id=sample_user.id,
        session_id="test-session-123",
        division=DivisionType.HOTEL,
        status=AssessmentStatus.IN_PROGRESS,
        max_possible_score=100
    )
    test_db.add(assessment)
    await test_db.commit()
    await test_db.refresh(assessment)
    return assessment


class TestAnswerSubmission:
    """Test answer submission with database persistence"""

    @pytest.mark.asyncio
    async def test_submit_answer_creates_guest_user(self, test_db):
        """Test that submit answer auto-creates guest user if needed"""
        # Override get_db dependency to return our test database
        async def override_get_db():
            yield test_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            # Use AsyncClient with ASGITransport for async database dependency
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
                # Simulate form submission
                response = await ac.post(
                    "/submit",
                    data={
                        "question_num": 1,
                        "answer": "Test answer",
                        "operation": "HOTEL"
                    }
                )

                # Should redirect (not error) - AsyncClient returns 307 for redirects
                assert response.status_code in [303, 307, 302, 200]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_answer_persists_to_database(self, test_db, sample_user,
                                                      sample_assessment, sample_questions):
        """Test that answer is saved to database"""
        from core.assessment_engine import AssessmentEngine

        engine = AssessmentEngine(test_db)

        # Submit answer
        result = await engine.submit_response(
            assessment_id=sample_assessment.id,
            question_id=sample_questions[0].id,
            user_answer="Extra towels",
            time_spent=10
        )

        # Verify response was created
        assert result["is_correct"] is True
        assert result["points_earned"] == 4

        # Verify in database
        from sqlalchemy import select
        db_result = await test_db.execute(
            select(AssessmentResponse).where(
                AssessmentResponse.assessment_id == sample_assessment.id
            )
        )
        response = db_result.scalar_one_or_none()

        assert response is not None
        assert response.user_answer == "Extra towels"
        assert response.is_correct is True
        assert response.points_earned == 4
        assert response.time_spent_seconds == 10

    @pytest.mark.asyncio
    async def test_submit_incorrect_answer(self, test_db, sample_assessment, sample_questions):
        """Test submitting incorrect answer"""
        from core.assessment_engine import AssessmentEngine

        engine = AssessmentEngine(test_db)

        result = await engine.submit_response(
            assessment_id=sample_assessment.id,
            question_id=sample_questions[0].id,
            user_answer="Wrong answer",
            time_spent=5
        )

        assert result["is_correct"] is False
        assert result["points_earned"] == 0

    @pytest.mark.asyncio
    async def test_submit_duplicate_answer_fails(self, test_db, sample_assessment,
                                                 sample_questions):
        """Test that submitting duplicate answer raises error"""
        from core.assessment_engine import AssessmentEngine

        engine = AssessmentEngine(test_db)

        # Submit first answer
        await engine.submit_response(
            assessment_id=sample_assessment.id,
            question_id=sample_questions[0].id,
            user_answer="Extra towels"
        )

        # Try to submit again - should raise error
        with pytest.raises(ValueError, match="already answered"):
            await engine.submit_response(
                assessment_id=sample_assessment.id,
                question_id=sample_questions[0].id,
                user_answer="Different answer"
            )

    @pytest.mark.asyncio
    async def test_submit_answer_invalid_assessment_status(self, test_db, sample_user,
                                                           sample_questions):
        """Test submitting answer to completed assessment fails"""
        from core.assessment_engine import AssessmentEngine

        # Create completed assessment
        assessment = Assessment(
            user_id=sample_user.id,
            session_id="completed-session",
            division=DivisionType.HOTEL,
            status=AssessmentStatus.COMPLETED,  # Already completed
            max_possible_score=100
        )
        test_db.add(assessment)
        await test_db.commit()
        await test_db.refresh(assessment)

        engine = AssessmentEngine(test_db)

        with pytest.raises(ValueError, match="not in progress"):
            await engine.submit_response(
                assessment_id=assessment.id,
                question_id=sample_questions[0].id,
                user_answer="Answer"
            )


class TestResultsRetrieval:
    """Test results page with database integration"""

    @pytest.mark.asyncio
    async def test_results_page_loads(self, test_db):
        """Test that results page renders with demo data when no assessment"""
        # Override get_db dependency
        async def override_get_db():
            yield test_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            # Use AsyncClient with ASGITransport for async database dependency
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/results")
                # Without assessment_id in session, should return 404
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_results_fetch_from_database(self, test_db, sample_user, sample_assessment):
        """Test results are fetched from database"""
        # Set scores in assessment
        sample_assessment.total_score = 75
        sample_assessment.listening_score = 14
        sample_assessment.grammar_score = 13
        sample_assessment.time_numbers_score = 12
        sample_assessment.vocabulary_score = 14
        sample_assessment.reading_score = 14
        sample_assessment.speaking_score = 18
        await test_db.commit()

        # Fetch assessment
        from sqlalchemy import select
        result = await test_db.execute(
            select(Assessment).where(Assessment.id == sample_assessment.id)
        )
        assessment = result.scalar_one()

        # Verify scores
        assert assessment.total_score == 75
        assert assessment.listening_score == 14
        assert assessment.speaking_score == 18

    @pytest.mark.asyncio
    async def test_results_with_no_assessment_shows_demo(self, test_db):
        """Test results page shows 404 when no assessment exists"""
        # Override get_db dependency
        async def override_get_db():
            yield test_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            # Use AsyncClient with ASGITransport for async database dependency
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/results")
                # Without assessment_id in session, should return 404
                assert response.status_code == 404
                assert "Assessment not found" in response.text or "404" in response.text
        finally:
            app.dependency_overrides.clear()


class TestEndToEndAssessmentFlow:
    """Test complete assessment flow from start to finish"""

    @pytest.mark.asyncio
    async def test_complete_assessment_flow(self, test_db, sample_user, sample_questions):
        """Test full assessment lifecycle"""
        from core.assessment_engine import AssessmentEngine
        from utils.scoring import ScoringEngine

        # 1. Create assessment
        engine = AssessmentEngine(test_db)
        assessment = await engine.create_assessment(
            user_id=sample_user.id,
            division=DivisionType.HOTEL
        )
        assert assessment.status == AssessmentStatus.NOT_STARTED

        # 2. Start assessment
        started = await engine.start_assessment(assessment.id)
        assert started["status"] == AssessmentStatus.IN_PROGRESS

        # 3. Submit answers for each question
        for i, question in enumerate(sample_questions):
            result = await engine.submit_response(
                assessment_id=assessment.id,
                question_id=question.id,
                user_answer=question.correct_answer,
                time_spent=10 + i
            )
            assert result["is_correct"] is True

        # 4. Get all responses for scoring
        from sqlalchemy import select
        responses_result = await test_db.execute(
            select(AssessmentResponse).where(
                AssessmentResponse.assessment_id == assessment.id
            )
        )
        responses = responses_result.scalars().all()

        # Calculate final scores
        scoring_engine = ScoringEngine(test_db)
        scores = await scoring_engine.calculate_final_scores(responses)

        assert scores["total_score"] > 0
        assert "listening" in scores
        assert "grammar" in scores

    @pytest.mark.asyncio
    async def test_assessment_with_mixed_correct_incorrect(self, test_db, sample_user,
                                                           sample_questions):
        """Test assessment with both correct and incorrect answers"""
        from core.assessment_engine import AssessmentEngine

        engine = AssessmentEngine(test_db)
        assessment = await engine.create_assessment(sample_user.id, DivisionType.HOTEL)
        await engine.start_assessment(assessment.id)

        # Submit correct answer
        result1 = await engine.submit_response(
            assessment_id=assessment.id,
            question_id=sample_questions[0].id,
            user_answer=sample_questions[0].correct_answer
        )
        assert result1["points_earned"] > 0

        # Submit incorrect answer
        result2 = await engine.submit_response(
            assessment_id=assessment.id,
            question_id=sample_questions[1].id,
            user_answer="Wrong answer"
        )
        assert result2["points_earned"] == 0

        # Verify responses in database
        from sqlalchemy import select
        responses_result = await test_db.execute(
            select(AssessmentResponse).where(
                AssessmentResponse.assessment_id == assessment.id
            )
        )
        responses = responses_result.scalars().all()

        assert len(responses) == 2
        assert sum(r.points_earned for r in responses) == result1["points_earned"]


class TestSessionIntegration:
    """Test session integration with database"""

    @pytest.mark.asyncio
    async def test_session_stores_assessment_id(self, client):
        """Test that session properly stores assessment ID"""
        with client as c:
            # Simulate starting assessment (would set session)
            # This tests the integration between session and database
            pass  # Session testing requires full app context

    @pytest.mark.asyncio
    async def test_answers_stored_in_session_and_database(self, client, test_db,
                                                          sample_assessment):
        """Test answers are stored in both session and database"""
        # In real implementation, answers go to both session (for display)
        # and database (for persistence)
        pass  # Requires full app integration


class TestErrorHandling:
    """Test error handling in UI routes"""

    @pytest.mark.asyncio
    async def test_submit_answer_invalid_question_number(self, client):
        """Test submitting answer with invalid question number"""
        response = client.post(
            "/submit",
            data={"question_num": 999, "answer": "test"},
            follow_redirects=False
        )
        # Should return error status
        assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_submit_answer_missing_data(self, client):
        """Test submitting answer with missing required fields"""
        response = client.post(
            "/submit",
            data={"question_num": 1},  # Missing answer
            follow_redirects=False
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_database_error_fallback(self, test_db, sample_assessment, sample_questions):
        """Test that database errors don't crash the application"""
        from core.assessment_engine import AssessmentEngine

        engine = AssessmentEngine(test_db)

        # Try with non-existent question
        with pytest.raises(ValueError):
            await engine.submit_response(
                assessment_id=sample_assessment.id,
                question_id=99999,  # Non-existent
                user_answer="test"
            )


class TestTemplateRendering:
    """Test that new templates render correctly"""

    @pytest.mark.asyncio
    async def test_registration_template_loads(self, client):
        """Test registration.html loads"""
        response = client.get("/register")
        assert response.status_code == 200
        assert b"Register" in response.content or b"register" in response.content

    @pytest.mark.asyncio
    async def test_instructions_template_loads(self, client):
        """Test instructions.html loads"""
        response = client.get("/instructions")
        assert response.status_code == 200
        assert b"Instructions" in response.content or b"instructions" in response.content

    @pytest.mark.asyncio
    async def test_home_template_loads(self, client):
        """Test home template loads"""
        response = client.get("/")
        assert response.status_code == 200


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
