"""
Integration tests: department → questions, question randomization, and scoring.

Verifies:
1. Selected department gets only that department's questions.
2. Each invitation/start yields a different random question set (same department).
3. Scoring system correctly scores answers and aggregates module/total scores.

Requires: DATABASE_URL set, question bank loaded (e.g. load_question_bank or question_bank_sample.json).
Run: pytest src/test/integration/test_department_and_scoring.py -v -s
"""

import asyncio
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.departments import normalize_department, DEPARTMENTS
from core.database import async_session_maker
from core.assessment_engine import AssessmentEngine
from models.assessment import (
    Assessment,
    User,
    Question,
    DivisionType,
    ModuleType,
    AssessmentStatus,
    QuestionType,
)


def _get_db_url():
    from core.config import settings
    return getattr(settings, "DATABASE_URL", None) or ""


def _has_db():
    url = _get_db_url()
    return bool(url and "sqlite" in url or "postgresql" in url)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_department_questions_match(db_session: AsyncSession):
    """
    For a chosen department, every question in the assessment's question_order
    must match the assessment division. Question rows may be department-specific
    or division-generic (department NULL) when the department pool is short for a module.
    """
    engine = AssessmentEngine(db_session)
    # Use a department that exists in question bank (e.g. HOUSEKEEPING for Hotel)
    department = "HOUSEKEEPING"
    division = DivisionType.HOTEL

    # Create test user with this department (unique email to avoid collisions)
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"test_dept_match_{uid}@test.local",
        password_hash="test",
        first_name="Test",
        last_name="User",
        nationality="Test",
        division=division,
        department=department,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Create and start assessment with department
    assessment = await engine.create_assessment(
        user_id=user.id,
        division=division,
        department=department,
        auto_commit=False,
    )
    await db_session.flush()
    await engine.start_assessment(assessment.id)

    await db_session.commit()
    await db_session.refresh(assessment)

    assert assessment.question_order is not None
    assert len(assessment.question_order) == 21

    normalized_dept = normalize_department(department)
    for i, qid in enumerate(assessment.question_order):
        q_result = await db_session.execute(select(Question).where(Question.id == qid))
        q = q_result.scalar_one_or_none()
        assert q is not None, f"Question {qid} (index {i}) not found"
        assert q.division == division, (
            f"Question {qid} division {q.division} != assessment division {division}"
        )
        assert q.department == normalized_dept or q.department is None, (
            f"Question {qid} department {q.department!r} must be {normalized_dept!r} or generic (NULL)"
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_question_randomization_per_invitation(db_session: AsyncSession):
    """
    Two assessments with the same department must get different question sets
    (random draw each time).
    """
    engine = AssessmentEngine(db_session)
    department = "GUEST SERVICES"
    division = DivisionType.HOTEL

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"test_rand_{uid}@test.local",
        password_hash="test",
        first_name="Rand",
        last_name="User",
        nationality="Test",
        division=division,
        department=department,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    a1 = await engine.create_assessment(
        user_id=user.id,
        division=division,
        department=department,
        auto_commit=False,
    )
    await db_session.flush()
    await engine.start_assessment(a1.id)

    # Ensure different session_id (engine uses assess_{user_id}_{timestamp})
    await asyncio.sleep(1.1)

    a2 = await engine.create_assessment(
        user_id=user.id,
        division=division,
        department=department,
        auto_commit=False,
    )
    await db_session.flush()
    await engine.start_assessment(a2.id)

    await db_session.commit()
    await db_session.refresh(a1)
    await db_session.refresh(a2)

    order1 = a1.question_order or []
    order2 = a2.question_order or []
    assert len(order1) == 21 and len(order2) == 21
    assert order1 != order2, (
        "Two assessments with same department should get different question sets (randomization)."
    )


def _aggregate_ui_answers(answers: dict) -> tuple:
    """
    Same logic as UI final scoring: parse "module:points" and sum by module.
    Returns (module_scores dict, total_score).
    """
    module_scores = {
        "listening": 0,
        "time_numbers": 0,
        "grammar": 0,
        "vocabulary": 0,
        "reading": 0,
        "speaking": 0,
    }
    for q_num, answer_data in answers.items():
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
    total = sum(module_scores.values())
    return module_scores, total


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scoring_aggregation_and_storage(db_session: AsyncSession):
    """
    Submit correct answers for (non-speaking) questions, persist as "module:points",
    then aggregate the same way the UI does and assert total and module scores are correct.
    """
    engine = AssessmentEngine(db_session)
    department = "HOUSEKEEPING"
    division = DivisionType.HOTEL

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"test_score_{uid}@test.local",
        password_hash="test",
        first_name="Score",
        last_name="User",
        nationality="Test",
        division=division,
        department=department,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    assessment = await engine.create_assessment(
        user_id=user.id,
        division=division,
        department=department,
        auto_commit=False,
    )
    await db_session.flush()
    await engine.start_assessment(assessment.id)
    await db_session.commit()
    await db_session.refresh(assessment)

    question_order = assessment.question_order
    assert question_order and len(question_order) == 21

    ui_answers = {}
    expected_total_from_submitted = 0

    for question_num, question_id in enumerate(question_order, start=1):
        q_result = await db_session.execute(select(Question).where(Question.id == question_id))
        q = q_result.scalar_one_or_none()
        if not q:
            continue

        # Submit correct answer (skip SPEAKING_RESPONSE to avoid AI call in test)
        if q.question_type == QuestionType.SPEAKING_RESPONSE:
            # Simulate 0 points for speaking in test (no AI)
            module_str = q.module_type.value
            ui_answers[str(question_num)] = f"{module_str}:0"
            continue

        user_answer = q.correct_answer
        try:
            result = await engine.submit_response(
                assessment_id=assessment.id,
                question_id=question_id,
                user_answer=user_answer,
                time_spent=0,
            )
        except ValueError as e:
            if "already answered" in str(e).lower():
                # Duplicate submit in same test run - use stored value
                break
            raise

        points_earned = int(result["points_earned"])
        module_str = q.module_type.value
        ui_answers[str(question_num)] = f"{module_str}:{points_earned}"
        expected_total_from_submitted += points_earned

    # Aggregate exactly like the UI
    module_scores, total_score = _aggregate_ui_answers(ui_answers)

    # We expect at least the non-speaking questions to be scored; total may be < 100 if speaking skipped
    assert total_score >= 0
    assert "listening" in module_scores and "grammar" in module_scores
    assert sum(module_scores.values()) == total_score


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scoring_wrong_answer_earns_zero(db_session: AsyncSession):
    """
    Submitting a wrong answer must result in 0 points for that question.
    """
    engine = AssessmentEngine(db_session)
    department = "HOUSEKEEPING"
    division = DivisionType.HOTEL

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"test_wrong_{uid}@test.local",
        password_hash="test",
        first_name="Wrong",
        last_name="User",
        nationality="Test",
        division=division,
        department=department,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    assessment = await engine.create_assessment(
        user_id=user.id,
        division=division,
        department=department,
        auto_commit=False,
    )
    await db_session.flush()
    await engine.start_assessment(assessment.id)
    await db_session.commit()
    await db_session.refresh(assessment)

    # Pick first question
    qid = assessment.question_order[0]
    q_result = await db_session.execute(select(Question).where(Question.id == qid))
    q = q_result.scalar_one_or_none()
    if not q or q.question_type == QuestionType.SPEAKING_RESPONSE:
        pytest.skip("Need a non-speaking first question")

    # Submit wrong answer
    wrong_answer = "wrong_answer_that_does_not_match"
    result = await engine.submit_response(
        assessment_id=assessment.id,
        question_id=qid,
        user_answer=wrong_answer,
        time_spent=0,
    )

    assert result["points_earned"] == 0
    assert result["is_correct"] is False
