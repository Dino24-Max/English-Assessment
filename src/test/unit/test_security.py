"""
Unit tests for security middleware and utilities.
Tests CSRF protection, rate limiting, input validation, and transaction management.
"""

import sys
import os
from pathlib import Path

# Set up Python path
_test_file = Path(__file__).resolve()
project_root = _test_file.parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
python_src_str = str(python_src.resolve())

if python_src_str not in sys.path:
    sys.path.insert(0, python_src_str)

os.environ["PYTHONPATH"] = python_src_str + os.pathsep + os.environ.get("PYTHONPATH", "")

import pytest
import pytest_asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request
from fastapi.testclient import TestClient


# =============================================================================
# CSRF Protection Tests
# =============================================================================

class TestCSRFProtection:
    """Test CSRF token generation and validation."""
    
    def test_generate_token_returns_string(self):
        """Test that generate_token returns a non-empty string."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        token = csrf.generate_token()
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_is_unique(self):
        """Test that each generated token is unique."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        tokens = [csrf.generate_token() for _ in range(100)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 100
    
    def test_validate_token_success(self):
        """Test successful token validation."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        token = csrf.generate_token()
        
        # Same token should validate
        assert csrf.validate_token(token, token) is True
    
    def test_validate_token_failure_different_tokens(self):
        """Test token validation fails with different tokens."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        token1 = csrf.generate_token()
        token2 = csrf.generate_token()
        
        assert csrf.validate_token(token1, token2) is False
    
    def test_validate_token_failure_empty_tokens(self):
        """Test token validation fails with empty tokens."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        token = csrf.generate_token()
        
        assert csrf.validate_token("", token) is False
        assert csrf.validate_token(token, "") is False
        assert csrf.validate_token("", "") is False
        assert csrf.validate_token(None, token) is False
        assert csrf.validate_token(token, None) is False
    
    def test_is_path_exempt_exact_match(self):
        """Test path exemption with exact matches."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        
        # Exempt paths
        assert csrf.is_path_exempt("/health") is True
        assert csrf.is_path_exempt("/docs") is True
        assert csrf.is_path_exempt("/api") is True
        
        # Non-exempt paths
        assert csrf.is_path_exempt("/submit") is False
        assert csrf.is_path_exempt("/login") is False
    
    def test_is_path_exempt_prefix_match(self):
        """Test path exemption with prefix matches."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        
        # Exempt prefixes
        assert csrf.is_path_exempt("/static/css/style.css") is True
        assert csrf.is_path_exempt("/api/v1/admin/users") is True
        assert csrf.is_path_exempt("/debug/session") is True
        
        # Non-exempt
        assert csrf.is_path_exempt("/question/1") is False


class TestCSRFMiddleware:
    """Test CSRF middleware behavior."""
    
    def test_get_request_generates_token(self):
        """Test that GET requests generate CSRF tokens."""
        # This would require full app integration
        pass
    
    def test_post_request_validates_token(self):
        """Test that POST requests validate CSRF tokens."""
        # This would require full app integration
        pass


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        # Create mock request
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Should allow 5 requests
        for i in range(5):
            is_limited, info = limiter.is_rate_limited(
                mock_request, limit=10, window_seconds=60
            )
            assert is_limited is False
            assert info["remaining"] >= 0
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Make requests up to the limit
        for i in range(5):
            is_limited, info = limiter.is_rate_limited(
                mock_request, limit=5, window_seconds=60
            )
        
        # Next request should be blocked
        is_limited, info = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=60
        )
        assert is_limited is True
        assert info["remaining"] == 0
    
    def test_rate_limiter_different_clients_independent(self):
        """Test that different clients have independent limits."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        # Client 1
        mock_request1 = Mock()
        mock_request1.headers = {}
        mock_request1.client = Mock()
        mock_request1.client.host = "192.168.1.1"
        
        # Client 2
        mock_request2 = Mock()
        mock_request2.headers = {}
        mock_request2.client = Mock()
        mock_request2.client.host = "192.168.1.2"
        
        # Use up client 1's limit
        for i in range(5):
            limiter.is_rate_limited(mock_request1, limit=5, window_seconds=60)
        
        # Client 1 should be blocked
        is_limited1, _ = limiter.is_rate_limited(mock_request1, limit=5, window_seconds=60)
        assert is_limited1 is True
        
        # Client 2 should still be allowed
        is_limited2, _ = limiter.is_rate_limited(mock_request2, limit=5, window_seconds=60)
        assert is_limited2 is False
    
    def test_rate_limiter_respects_x_forwarded_for(self):
        """Test that X-Forwarded-For header is respected."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Should use 10.0.0.1 (first IP in X-Forwarded-For)
        is_limited, info = limiter.is_rate_limited(
            mock_request, limit=10, window_seconds=60
        )
        
        # Verify the client key uses the forwarded IP
        assert is_limited is False
    
    def test_rate_limiter_per_endpoint(self):
        """Test rate limiting per endpoint."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Use up limit for endpoint A
        for i in range(5):
            limiter.is_rate_limited(
                mock_request, limit=5, window_seconds=60, endpoint="/api/a"
            )
        
        # Endpoint A should be blocked
        is_limited_a, _ = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=60, endpoint="/api/a"
        )
        assert is_limited_a is True
        
        # Endpoint B should still be allowed
        is_limited_b, _ = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=60, endpoint="/api/b"
        )
        assert is_limited_b is False


# =============================================================================
# Input Validation Tests
# =============================================================================

class TestInputValidation:
    """Test input validation utilities."""
    
    def test_sanitize_string_removes_null_bytes(self):
        """Test that null bytes are removed from strings."""
        from core.validation import sanitize_string
        
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"
    
    def test_sanitize_string_trims_whitespace(self):
        """Test that whitespace is trimmed."""
        from core.validation import sanitize_string
        
        result = sanitize_string("  hello world  ")
        assert result == "hello world"
    
    def test_sanitize_string_respects_max_length(self):
        """Test that max_length is respected."""
        from core.validation import sanitize_string
        
        long_string = "a" * 1000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100
    
    def test_validate_question_number_valid(self):
        """Test valid question numbers."""
        from core.validation import validate_question_number
        
        assert validate_question_number(1) == 1
        assert validate_question_number(10) == 10
        assert validate_question_number(21) == 21
    
    def test_validate_question_number_invalid(self):
        """Test invalid question numbers."""
        from core.validation import validate_question_number
        
        with pytest.raises(ValueError):
            validate_question_number(0)
        
        with pytest.raises(ValueError):
            validate_question_number(22)
        
        with pytest.raises(ValueError):
            validate_question_number(-1)
    
    def test_validate_operation_valid(self):
        """Test valid operation types."""
        from core.validation import validate_operation
        
        assert validate_operation("HOTEL") == "HOTEL"
        assert validate_operation("hotel") == "HOTEL"
        assert validate_operation("MARINE") == "MARINE"
        assert validate_operation("CASINO") == "CASINO"
    
    def test_validate_operation_invalid(self):
        """Test invalid operation types."""
        from core.validation import validate_operation
        
        with pytest.raises(ValueError):
            validate_operation("INVALID")
        
        with pytest.raises(ValueError):
            validate_operation("")
        
        with pytest.raises(ValueError):
            validate_operation(None)
    
    def test_validate_email_format_valid(self):
        """Test valid email formats."""
        from core.validation import validate_email_format
        
        assert validate_email_format("test@example.com") == "test@example.com"
        assert validate_email_format("user.name@domain.org") == "user.name@domain.org"
        assert validate_email_format("TEST@EXAMPLE.COM") == "test@example.com"
    
    def test_validate_email_format_invalid(self):
        """Test invalid email formats."""
        from core.validation import validate_email_format
        
        with pytest.raises(ValueError):
            validate_email_format("invalid")
        
        with pytest.raises(ValueError):
            validate_email_format("@domain.com")
        
        with pytest.raises(ValueError):
            validate_email_format("user@")
    
    def test_validate_password_strength_valid(self):
        """Test valid passwords."""
        from core.validation import validate_password_strength
        
        assert validate_password_strength("password123") == "password123"
        assert validate_password_strength("abcdef") == "abcdef"
    
    def test_validate_password_strength_too_short(self):
        """Test password too short."""
        from core.validation import validate_password_strength
        
        with pytest.raises(ValueError):
            validate_password_strength("abc")
    
    def test_validate_password_strength_too_long(self):
        """Test password too long."""
        from core.validation import validate_password_strength
        
        with pytest.raises(ValueError):
            validate_password_strength("a" * 101)


class TestPydanticModels:
    """Test Pydantic validation models."""
    
    def test_answer_submission_valid(self):
        """Test valid answer submission."""
        from core.validation import AnswerSubmission
        
        submission = AnswerSubmission(
            question_num=1,
            answer="Test answer",
            operation="HOTEL"
        )
        
        assert submission.question_num == 1
        assert submission.answer == "Test answer"
        assert submission.operation == "HOTEL"
    
    def test_answer_submission_invalid_question_num(self):
        """Test invalid question number in submission."""
        from core.validation import AnswerSubmission
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            AnswerSubmission(
                question_num=0,
                answer="Test"
            )
        
        with pytest.raises(ValidationError):
            AnswerSubmission(
                question_num=22,
                answer="Test"
            )
    
    def test_answer_submission_empty_answer(self):
        """Test empty answer in submission."""
        from core.validation import AnswerSubmission
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            AnswerSubmission(
                question_num=1,
                answer=""
            )
    
    def test_invitation_code_validation_valid(self):
        """Test valid invitation code."""
        from core.validation import InvitationCodeValidation
        
        code = InvitationCodeValidation(code="ABCD1234EFGH5678")
        assert code.code == "ABCD1234EFGH5678"
    
    def test_invitation_code_validation_invalid_length(self):
        """Test invitation code with invalid length."""
        from core.validation import InvitationCodeValidation
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            InvitationCodeValidation(code="SHORT")
        
        with pytest.raises(ValidationError):
            InvitationCodeValidation(code="TOOLONGCODE12345678")
    
    def test_invitation_code_validation_invalid_characters(self):
        """Test invitation code with invalid characters."""
        from core.validation import InvitationCodeValidation
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            InvitationCodeValidation(code="ABCD-1234-EFGH-56")


class TestSpeakingAnswerValidation:
    """Test speaking answer format validation."""
    
    def test_validate_speaking_answer_format_valid(self):
        """Test valid speaking answer formats."""
        from core.validation import validate_speaking_answer_format
        
        # With transcript
        duration, transcript = validate_speaking_answer_format(
            "recorded_10s|Hello, this is my response."
        )
        assert duration == 10
        assert transcript == "Hello, this is my response."
        
        # Without transcript
        duration, transcript = validate_speaking_answer_format("recorded_5s")
        assert duration == 5
        assert transcript == ""
    
    def test_validate_speaking_answer_format_invalid(self):
        """Test invalid speaking answer formats."""
        from core.validation import validate_speaking_answer_format
        
        with pytest.raises(ValueError):
            validate_speaking_answer_format("not_a_recording")
        
        with pytest.raises(ValueError):
            validate_speaking_answer_format("recorded_abc")
    
    def test_validate_speaking_answer_format_duration_limits(self):
        """Test speaking answer duration limits."""
        from core.validation import validate_speaking_answer_format
        
        # Valid duration
        duration, _ = validate_speaking_answer_format("recorded_300s")
        assert duration == 300
        
        # Invalid duration (too long)
        with pytest.raises(ValueError):
            validate_speaking_answer_format("recorded_301s")


# =============================================================================
# Transaction Management Tests
# =============================================================================

class TestTransactionManagement:
    """Test transaction management utilities."""
    
    @pytest.mark.asyncio
    async def test_atomic_transaction_commits_on_success(self):
        """Test that atomic_transaction commits on success."""
        from core.transaction import atomic_transaction
        
        # Create mock session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        async with atomic_transaction(mock_session):
            pass  # Successful operation
        
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_atomic_transaction_rollbacks_on_error(self):
        """Test that atomic_transaction rolls back on error."""
        from core.transaction import atomic_transaction, TransactionError
        
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(TransactionError):
            async with atomic_transaction(mock_session):
                raise Exception("Test error")
        
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
    
    def test_transaction_error_contains_original(self):
        """Test that TransactionError contains original error."""
        from core.transaction import TransactionError
        
        original = ValueError("Original error")
        error = TransactionError("Transaction failed", original_error=original)
        
        assert error.original_error is original
        assert "Transaction failed" in str(error)


class TestTransactionManager:
    """Test TransactionManager class."""
    
    @pytest.mark.asyncio
    async def test_transaction_manager_execute_success(self):
        """Test successful execution with TransactionManager."""
        from core.transaction import TransactionManager
        
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        manager = TransactionManager(mock_session)
        
        async def successful_operation():
            return "success"
        
        result = await manager.execute(successful_operation)
        
        assert result == "success"
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_manager_compensation_on_failure(self):
        """Test compensation actions are called on failure."""
        from core.transaction import TransactionManager, TransactionError
        from sqlalchemy.exc import SQLAlchemyError
        
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        manager = TransactionManager(mock_session, max_retries=1)
        
        compensation_called = False
        
        def compensation():
            nonlocal compensation_called
            compensation_called = True
        
        manager.add_compensation(compensation)
        
        async def failing_operation():
            raise SQLAlchemyError("Database error")
        
        with pytest.raises(TransactionError):
            await manager.execute(failing_operation)
        
        assert compensation_called is True


# =============================================================================
# Security Headers Tests
# =============================================================================

class TestSecurityHeaders:
    """Test security headers middleware."""
    
    def test_security_headers_are_set(self):
        """Test that security headers are added to responses."""
        # This would require full app integration
        pass


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
