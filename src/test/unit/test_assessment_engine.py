"""
Unit tests for assessment engine
"""

import sys
from pathlib import Path

# Add src/main/python to path BEFORE any other imports
project_root = Path(__file__).parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))

import pytest
from unittest.mock import Mock, AsyncMock
from core.assessment_engine import AssessmentEngine
from models.assessment import DivisionType, ModuleType


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def assessment_engine(mock_db):
    return AssessmentEngine(mock_db)


@pytest.mark.asyncio
async def test_create_assessment(assessment_engine, mock_db):
    """Test assessment creation"""

    # Mock database operations
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Test
    result = await assessment_engine.create_assessment(1, DivisionType.HOTEL)

    # Assertions
    assert result.user_id == 1
    assert result.division == DivisionType.HOTEL
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_flexible_text_match(assessment_engine):
    """Test flexible text matching for fill-in-the-blank"""

    # Test cases
    assert assessment_engine._flexible_text_match("7:00", "7:00 AM") == True
    assert assessment_engine._flexible_text_match("seven", "7") == False
    assert assessment_engine._flexible_text_match("25", "25 knots") == True


def test_transcript_invalid_speaking_rejects_test_bypass():
    assert AssessmentEngine._transcript_is_invalid_speaking("") is True
    empty, _dur = AssessmentEngine._parse_speaking_user_answer("recorded_0s|")
    assert empty == ""
    assert AssessmentEngine._transcript_is_invalid_speaking(empty) is True
    assert (
        AssessmentEngine._transcript_is_invalid_speaking(
            "Test mode response - automated testing bypass"
        )
        is True
    )
    assert AssessmentEngine._transcript_is_invalid_speaking("The guest needs help with luggage") is False


def test_select_speaking_questions_prefers_repeat_with_audio():
    class Q:
        def __init__(self, name, speaking_type, audio_text=None, path=None):
            self.id = name
            self.question_metadata = {"speaking_type": speaking_type}
            if audio_text:
                self.question_metadata["audio_text"] = audio_text
            self.audio_file_path = path

    scenario = Q("s", "scenario")
    repeat_no = Q("r1", "repeat")
    repeat_ok = Q("r2", "repeat", audio_text="Please wait here.")
    pool = [scenario, repeat_no, repeat_ok]
    picked = AssessmentEngine._select_speaking_questions(pool, 2)
    assert repeat_ok in picked
    assert len(picked) == 2


def test_question_content_key_normalizes_grammar_stem():
    class Q:
        module_type = ModuleType.GRAMMAR
        question_metadata = {}

        def __init__(self, text):
            self.question_text = text

    eng = AssessmentEngine(Mock())
    k1 = eng._question_content_key(Q("Could you please ___ me to the spa?"))
    k2 = eng._question_content_key(Q("Could you please ___ me to the Spa?"))
    assert k1 == k2