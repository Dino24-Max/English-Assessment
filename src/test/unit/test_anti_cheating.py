"""
Unit tests for anti-cheating service
Tests IP tracking, user agent validation, and suspicious behavior detection
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from utils.anti_cheating import AntiCheatingService
from models.assessment import Assessment


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_request():
    """Mock FastAPI request"""
    request = Mock(spec=Request)
    request.headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "X-Forwarded-For": "192.168.1.100"
    }
    request.client = Mock()
    request.client.host = "192.168.1.100"
    return request


@pytest.fixture
def mock_assessment():
    """Mock assessment object"""
    assessment = Mock(spec=Assessment)
    assessment.id = 1
    assessment.ip_address = "192.168.1.100"
    assessment.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    assessment.analytics_data = {
        "session_start_time": datetime.utcnow().isoformat(),
        "initial_ip": "192.168.1.100",
        "initial_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "suspicious_events": [],
        "tab_switches": 0,
        "copy_paste_attempts": 0
    }
    return assessment


@pytest.fixture
def anti_cheating_service(mock_db):
    """Create anti-cheating service instance"""
    return AntiCheatingService(mock_db)


class TestIPTracking:
    """Test IP address tracking and validation"""

    @pytest.mark.asyncio
    async def test_get_client_ip_from_forwarded_header(self, anti_cheating_service, mock_request):
        """Test extracting IP from X-Forwarded-For header"""
        ip = anti_cheating_service._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_get_client_ip_with_multiple_proxies(self, anti_cheating_service):
        """Test extracting first IP from proxy chain"""
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        ip = anti_cheating_service._get_client_ip(request)
        assert ip == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_get_client_ip_from_real_ip_header(self, anti_cheating_service):
        """Test extracting IP from X-Real-IP header"""
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "10.20.30.40"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        ip = anti_cheating_service._get_client_ip(request)
        assert ip == "10.20.30.40"

    @pytest.mark.asyncio
    async def test_get_client_ip_fallback_to_client(self, anti_cheating_service):
        """Test fallback to direct client IP"""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.200"

        ip = anti_cheating_service._get_client_ip(request)
        assert ip == "192.168.1.200"

    @pytest.mark.asyncio
    async def test_get_client_ip_no_client_info(self, anti_cheating_service):
        """Test handling missing client info"""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        ip = anti_cheating_service._get_client_ip(request)
        assert ip == "Unknown"


class TestSessionRecording:
    """Test session start recording"""

    @pytest.mark.asyncio
    async def test_record_session_start_success(self, anti_cheating_service, mock_db,
                                               mock_request, mock_assessment):
        """Test successful session start recording"""
        # Setup mock
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        # Execute
        result = await anti_cheating_service.record_session_start(1, mock_request)

        # Verify
        assert result["recorded"] is True
        assert result["ip_address"] == "192.168.1.100"
        assert "user_agent" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_session_start_stores_analytics(self, anti_cheating_service,
                                                        mock_db, mock_request, mock_assessment):
        """Test that analytics data is properly initialized"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        await anti_cheating_service.record_session_start(1, mock_request)

        # Verify analytics data structure
        assert "session_start_time" in mock_assessment.analytics_data
        assert "initial_ip" in mock_assessment.analytics_data
        assert "initial_user_agent" in mock_assessment.analytics_data
        assert "suspicious_events" in mock_assessment.analytics_data
        assert mock_assessment.analytics_data["tab_switches"] == 0
        assert mock_assessment.analytics_data["copy_paste_attempts"] == 0


class TestSessionValidation:
    """Test session integrity validation"""

    @pytest.mark.asyncio
    async def test_validate_session_consistent_ip_and_ua(self, anti_cheating_service,
                                                         mock_db, mock_request, mock_assessment):
        """Test validation with consistent IP and user agent"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.validate_session(1, mock_request)

        assert result["valid"] is True
        assert result["suspicious"] is False
        assert result["ip_consistent"] is True
        assert result["user_agent_consistent"] is True
        assert len(result["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_validate_session_ip_changed(self, anti_cheating_service, mock_db,
                                               mock_assessment):
        """Test validation detects IP change"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        # Create request with different IP
        request = Mock(spec=Request)
        request.headers = {
            "user-agent": mock_assessment.user_agent,
            "X-Forwarded-For": "10.0.0.1"  # Different IP
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"

        result = await anti_cheating_service.validate_session(1, request)

        assert result["valid"] is False
        assert result["suspicious"] is True
        assert result["ip_consistent"] is False
        assert len(result["warnings"]) > 0
        assert "IP address changed" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_validate_session_user_agent_changed(self, anti_cheating_service,
                                                       mock_db, mock_assessment):
        """Test validation detects user agent change"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        # Create request with different user agent
        request = Mock(spec=Request)
        request.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Safari/605.1.15",
            "X-Forwarded-For": mock_assessment.ip_address
        }
        request.client = Mock()
        request.client.host = mock_assessment.ip_address

        result = await anti_cheating_service.validate_session(1, request)

        assert result["valid"] is False
        assert result["suspicious"] is True
        assert result["user_agent_consistent"] is False
        assert any("User agent" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_session_assessment_not_found(self, anti_cheating_service,
                                                        mock_db, mock_request):
        """Test validation with non-existent assessment"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.validate_session(999, mock_request)

        assert result["valid"] is False
        assert result["suspicious"] is True
        assert "not found" in result["reason"]


class TestTabSwitchRecording:
    """Test tab switching detection"""

    @pytest.mark.asyncio
    async def test_record_tab_switch_first_time(self, anti_cheating_service, mock_db,
                                               mock_assessment):
        """Test recording first tab switch"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.record_tab_switch(1)

        assert result["recorded"] is True
        assert result["total_switches"] == 1
        assert result["warning"] is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_tab_switch_warning_threshold(self, anti_cheating_service,
                                                       mock_db, mock_assessment):
        """Test warning triggered after multiple switches"""
        mock_assessment.analytics_data["tab_switches"] = 3
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.record_tab_switch(1)

        assert result["recorded"] is True
        assert result["total_switches"] == 4
        assert result["warning"] is True  # Threshold exceeded

    @pytest.mark.asyncio
    async def test_record_tab_switch_no_assessment(self, anti_cheating_service, mock_db):
        """Test tab switch recording with missing assessment"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.record_tab_switch(999)

        assert result["recorded"] is False


class TestCopyPasteRecording:
    """Test copy/paste detection"""

    @pytest.mark.asyncio
    async def test_record_copy_paste(self, anti_cheating_service, mock_db, mock_assessment):
        """Test recording copy/paste attempt"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.record_copy_paste(1, "paste")

        assert result["recorded"] is True
        assert result["total_attempts"] == 1
        assert result["warning"] is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_copy_paste_warning_threshold(self, anti_cheating_service,
                                                       mock_db, mock_assessment):
        """Test warning after multiple copy/paste attempts"""
        mock_assessment.analytics_data["copy_paste_attempts"] = 5
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.record_copy_paste(1, "copy")

        assert result["recorded"] is True
        assert result["total_attempts"] == 6
        assert result["warning"] is True  # Threshold exceeded


class TestSuspiciousScoring:
    """Test suspicious behavior scoring algorithm"""

    @pytest.mark.asyncio
    async def test_get_suspicious_score_clean(self, anti_cheating_service, mock_db,
                                              mock_assessment):
        """Test clean session (no suspicious behavior)"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        # Mock validate_session to return clean
        anti_cheating_service.validate_session = AsyncMock(return_value={
            "ip_consistent": True,
            "user_agent_consistent": True
        })

        result = await anti_cheating_service.get_suspicious_score(1)

        assert result["score"] == 0
        assert result["level"] == "clean"
        assert result["requires_review"] is False
        assert len(result["factors"]) == 0

    @pytest.mark.asyncio
    async def test_get_suspicious_score_ip_change(self, anti_cheating_service, mock_db,
                                                   mock_assessment):
        """Test score calculation with IP change"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        anti_cheating_service.validate_session = AsyncMock(return_value={
            "ip_consistent": False,
            "user_agent_consistent": True
        })

        result = await anti_cheating_service.get_suspicious_score(1)

        assert result["score"] >= 40  # IP change adds 40 points
        assert result["level"] in ["high", "critical"]
        assert result["requires_review"] is True
        assert "IP address changed" in result["factors"]

    @pytest.mark.asyncio
    async def test_get_suspicious_score_multiple_violations(self, anti_cheating_service,
                                                            mock_db, mock_assessment):
        """Test score with multiple violations"""
        mock_assessment.analytics_data["tab_switches"] = 5
        mock_assessment.analytics_data["copy_paste_attempts"] = 6
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        anti_cheating_service.validate_session = AsyncMock(return_value={
            "ip_consistent": False,
            "user_agent_consistent": False
        })

        result = await anti_cheating_service.get_suspicious_score(1)

        # 40 (IP) + 30 (UA) + 20 (tab switches max) + 15 (copy/paste max) = 105 capped
        assert result["score"] >= 70
        assert result["level"] == "critical"
        assert result["requires_review"] is True
        assert len(result["factors"]) > 0

    @pytest.mark.asyncio
    async def test_get_suspicious_score_levels(self, anti_cheating_service, mock_db,
                                               mock_assessment):
        """Test different risk level classifications"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        # Test low level (1-19)
        mock_assessment.analytics_data["tab_switches"] = 1
        anti_cheating_service.validate_session = AsyncMock(return_value={
            "ip_consistent": True, "user_agent_consistent": True
        })
        result = await anti_cheating_service.get_suspicious_score(1)
        assert result["level"] == "low"

        # Test medium level (20-39)
        mock_assessment.analytics_data["tab_switches"] = 4
        result = await anti_cheating_service.get_suspicious_score(1)
        assert result["level"] == "medium"


class TestFlagging:
    """Test manual flagging for review"""

    @pytest.mark.asyncio
    async def test_flag_for_review(self, anti_cheating_service, mock_db, mock_assessment):
        """Test flagging an assessment"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.flag_for_review(1, "Suspicious activity detected")

        assert result["flagged"] is True
        assert result["reason"] == "Suspicious activity detected"
        assert mock_assessment.analytics_data["flagged_for_review"] is True
        assert "flag_timestamp" in mock_assessment.analytics_data
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_flag_for_review_not_found(self, anti_cheating_service, mock_db):
        """Test flagging non-existent assessment"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await anti_cheating_service.flag_for_review(999, "Test")

        assert result["flagged"] is False
        assert "error" in result


class TestSuspiciousEventLogging:
    """Test logging of suspicious events"""

    @pytest.mark.asyncio
    async def test_log_suspicious_event(self, anti_cheating_service, mock_db, mock_assessment):
        """Test logging a suspicious event"""
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = mock_assessment
        mock_db.execute.return_value = result_mock

        await anti_cheating_service._log_suspicious_event(
            1,
            "test_event",
            {"detail": "test detail"}
        )

        # Verify event was added
        events = mock_assessment.analytics_data["suspicious_events"]
        assert len(events) > 0
        assert events[-1]["type"] == "test_event"
        assert "timestamp" in events[-1]
        mock_db.commit.assert_called_once()


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
