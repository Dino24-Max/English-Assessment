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
from models.assessment import DivisionType


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