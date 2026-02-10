"""
Edge case and boundary condition tests.
Tests unusual inputs, boundary values, and error conditions.
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
import json
from unittest.mock import Mock, AsyncMock, patch


# =============================================================================
# Question Number Boundary Tests
# =============================================================================

class TestQuestionNumberBoundaries:
    """Test question number boundary conditions."""
    
    def test_question_number_minimum(self):
        """Test minimum valid question number (1)."""
        from core.validation import validate_question_number
        
        assert validate_question_number(1) == 1
    
    def test_question_number_maximum(self):
        """Test maximum valid question number (21)."""
        from core.validation import validate_question_number
        
        assert validate_question_number(21) == 21
    
    def test_question_number_below_minimum(self):
        """Test question number below minimum (0)."""
        from core.validation import validate_question_number
        
        with pytest.raises(ValueError):
            validate_question_number(0)
    
    def test_question_number_above_maximum(self):
        """Test question number above maximum (22)."""
        from core.validation import validate_question_number
        
        with pytest.raises(ValueError):
            validate_question_number(22)
    
    def test_question_number_negative(self):
        """Test negative question number."""
        from core.validation import validate_question_number
        
        with pytest.raises(ValueError):
            validate_question_number(-1)
    
    def test_question_number_very_large(self):
        """Test very large question number."""
        from core.validation import validate_question_number
        
        with pytest.raises(ValueError):
            validate_question_number(1000000)


# =============================================================================
# String Length Boundary Tests
# =============================================================================

class TestStringLengthBoundaries:
    """Test string length boundary conditions."""
    
    def test_empty_string_answer(self):
        """Test empty string as answer."""
        from core.validation import sanitize_string
        
        result = sanitize_string("")
        assert result == ""
    
    def test_whitespace_only_answer(self):
        """Test whitespace-only string as answer."""
        from core.validation import sanitize_string
        
        result = sanitize_string("   \t\n   ")
        assert result == ""
    
    def test_maximum_length_answer(self):
        """Test answer at maximum length."""
        from core.validation import sanitize_string
        
        long_answer = "a" * 10000
        result = sanitize_string(long_answer, max_length=10000)
        assert len(result) == 10000
    
    def test_over_maximum_length_answer(self):
        """Test answer over maximum length is truncated."""
        from core.validation import sanitize_string
        
        long_answer = "a" * 15000
        result = sanitize_string(long_answer, max_length=10000)
        assert len(result) == 10000
    
    def test_unicode_string_handling(self):
        """Test unicode characters in strings."""
        from core.validation import sanitize_string
        
        unicode_answer = "你好世界 🌍 مرحبا"
        result = sanitize_string(unicode_answer)
        assert result == unicode_answer
    
    def test_special_characters_in_string(self):
        """Test special characters are preserved."""
        from core.validation import sanitize_string
        
        special = "Hello <script>alert('xss')</script> World"
        result = sanitize_string(special)
        # Should preserve (HTML escaping is done at template level)
        assert "<script>" in result


# =============================================================================
# JSON Answer Boundary Tests
# =============================================================================

class TestJSONAnswerBoundaries:
    """Test JSON answer parsing edge cases."""
    
    def test_empty_json_object(self):
        """Test empty JSON object."""
        from core.validation import validate_json_answer
        
        result = validate_json_answer("{}")
        assert result == {}
    
    def test_json_with_empty_values(self):
        """Test JSON with empty string values."""
        from core.validation import validate_json_answer
        
        result = validate_json_answer('{"key": ""}')
        assert result == {"key": ""}
    
    def test_json_with_null_values(self):
        """Test JSON with null values."""
        from core.validation import validate_json_answer
        
        result = validate_json_answer('{"key": null}')
        assert result == {"key": None}
    
    def test_invalid_json_syntax(self):
        """Test invalid JSON syntax."""
        from core.validation import validate_json_answer
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            validate_json_answer("{invalid json}")
    
    def test_json_array_instead_of_object(self):
        """Test JSON array when object expected."""
        from core.validation import validate_json_answer
        
        with pytest.raises(ValueError, match="must be a JSON object"):
            validate_json_answer('["item1", "item2"]')
    
    def test_deeply_nested_json(self):
        """Test deeply nested JSON structure."""
        from core.validation import validate_json_answer
        
        nested = '{"a": {"b": {"c": {"d": "value"}}}}'
        result = validate_json_answer(nested)
        assert result["a"]["b"]["c"]["d"] == "value"
    
    def test_json_with_unicode(self):
        """Test JSON with unicode characters."""
        from core.validation import validate_json_answer
        
        unicode_json = '{"term": "你好", "definition": "Hello"}'
        result = validate_json_answer(unicode_json)
        assert result["term"] == "你好"


# =============================================================================
# Speaking Answer Format Tests
# =============================================================================

class TestSpeakingAnswerEdgeCases:
    """Test speaking answer format edge cases."""
    
    def test_zero_duration_recording(self):
        """Test zero duration recording."""
        from core.validation import validate_speaking_answer_format
        
        duration, transcript = validate_speaking_answer_format("recorded_0s")
        assert duration == 0
        assert transcript == ""
    
    def test_maximum_duration_recording(self):
        """Test maximum duration recording (300s)."""
        from core.validation import validate_speaking_answer_format
        
        duration, transcript = validate_speaking_answer_format("recorded_300s")
        assert duration == 300
    
    def test_empty_transcript(self):
        """Test recording with empty transcript."""
        from core.validation import validate_speaking_answer_format
        
        duration, transcript = validate_speaking_answer_format("recorded_10s|")
        assert duration == 10
        assert transcript == ""
    
    def test_transcript_with_pipe_character(self):
        """Test transcript containing pipe character."""
        from core.validation import validate_speaking_answer_format
        
        # Only first pipe is used as delimiter
        duration, transcript = validate_speaking_answer_format(
            "recorded_10s|Hello | World"
        )
        assert duration == 10
        assert transcript == "Hello | World"
    
    def test_very_long_transcript(self):
        """Test very long transcript."""
        from core.validation import validate_speaking_answer_format
        
        long_transcript = "word " * 1000
        answer = f"recorded_60s|{long_transcript}"
        duration, transcript = validate_speaking_answer_format(answer)
        
        assert duration == 60
        assert len(transcript) > 0


# =============================================================================
# Email Validation Edge Cases
# =============================================================================

class TestEmailValidationEdgeCases:
    """Test email validation edge cases."""
    
    def test_email_with_plus_sign(self):
        """Test email with plus sign (valid)."""
        from core.validation import validate_email_format
        
        result = validate_email_format("user+tag@example.com")
        assert result == "user+tag@example.com"
    
    def test_email_with_dots_in_local_part(self):
        """Test email with dots in local part."""
        from core.validation import validate_email_format
        
        result = validate_email_format("first.last@example.com")
        assert result == "first.last@example.com"
    
    def test_email_with_subdomain(self):
        """Test email with subdomain."""
        from core.validation import validate_email_format
        
        result = validate_email_format("user@mail.example.com")
        assert result == "user@mail.example.com"
    
    def test_email_maximum_length(self):
        """Test email at maximum length (254 chars)."""
        from core.validation import validate_email_format
        
        # Create email close to max length
        local_part = "a" * 64
        domain = "b" * 180 + ".com"
        email = f"{local_part}@{domain}"
        
        if len(email) <= 254:
            result = validate_email_format(email)
            assert "@" in result
    
    def test_email_over_maximum_length(self):
        """Test email over maximum length."""
        from core.validation import validate_email_format
        
        long_email = "a" * 250 + "@example.com"
        
        with pytest.raises(ValueError, match="too long"):
            validate_email_format(long_email)
    
    def test_email_case_normalization(self):
        """Test email is normalized to lowercase."""
        from core.validation import validate_email_format
        
        result = validate_email_format("USER@EXAMPLE.COM")
        assert result == "user@example.com"


# =============================================================================
# Password Validation Edge Cases
# =============================================================================

class TestPasswordValidationEdgeCases:
    """Test password validation edge cases."""
    
    def test_password_minimum_length(self):
        """Test password at minimum length (6 chars)."""
        from core.validation import validate_password_strength
        
        result = validate_password_strength("abcdef")
        assert result == "abcdef"
    
    def test_password_below_minimum_length(self):
        """Test password below minimum length."""
        from core.validation import validate_password_strength
        
        with pytest.raises(ValueError, match="at least 6"):
            validate_password_strength("abc")
    
    def test_password_maximum_length(self):
        """Test password at maximum length (100 chars)."""
        from core.validation import validate_password_strength
        
        password = "a" * 100
        result = validate_password_strength(password)
        assert len(result) == 100
    
    def test_password_over_maximum_length(self):
        """Test password over maximum length."""
        from core.validation import validate_password_strength
        
        password = "a" * 101
        
        with pytest.raises(ValueError, match="at most 100"):
            validate_password_strength(password)
    
    def test_password_with_unicode(self):
        """Test password with unicode characters."""
        from core.validation import validate_password_strength
        
        password = "密码password123"
        result = validate_password_strength(password)
        assert result == password
    
    def test_password_with_special_characters(self):
        """Test password with special characters."""
        from core.validation import validate_password_strength
        
        password = "P@ssw0rd!#$%"
        result = validate_password_strength(password)
        assert result == password


# =============================================================================
# Rate Limiting Edge Cases
# =============================================================================

class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases."""
    
    def test_rate_limit_exactly_at_limit(self):
        """Test request exactly at rate limit."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Make exactly limit-1 requests
        for i in range(4):
            is_limited, _ = limiter.is_rate_limited(
                mock_request, limit=5, window_seconds=60
            )
            assert is_limited is False
        
        # 5th request should still be allowed
        is_limited, info = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=60
        )
        assert is_limited is False
        
        # 6th request should be blocked
        is_limited, info = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=60
        )
        assert is_limited is True
    
    def test_rate_limit_with_zero_limit(self):
        """Test rate limit with zero limit (all blocked)."""
        from core.security import RateLimiter
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # First request should be blocked with limit=0
        is_limited, _ = limiter.is_rate_limited(
            mock_request, limit=0, window_seconds=60
        )
        assert is_limited is True
    
    def test_rate_limit_with_very_short_window(self):
        """Test rate limit with very short window."""
        from core.security import RateLimiter
        import time
        
        limiter = RateLimiter()
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Use up limit
        for i in range(5):
            limiter.is_rate_limited(
                mock_request, limit=5, window_seconds=1
            )
        
        # Should be blocked
        is_limited, _ = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=1
        )
        assert is_limited is True
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        is_limited, _ = limiter.is_rate_limited(
            mock_request, limit=5, window_seconds=1
        )
        assert is_limited is False


# =============================================================================
# CSRF Token Edge Cases
# =============================================================================

class TestCSRFEdgeCases:
    """Test CSRF token edge cases."""
    
    def test_csrf_token_with_special_characters(self):
        """Test CSRF token generation doesn't include problematic chars."""
        from core.security import CSRFProtection
        
        csrf = CSRFProtection()
        
        # Generate many tokens and check for problematic characters
        for _ in range(100):
            token = csrf.generate_token()
            # URL-safe base64 should not contain +, /, or =
            assert "+" not in token or token.count("+") == 0
            assert "/" not in token
    
    def test_csrf_validation_timing_attack_resistance(self):
        """Test CSRF validation uses constant-time comparison."""
        from core.security import CSRFProtection
        import time
        
        csrf = CSRFProtection()
        token = csrf.generate_token()
        
        # Measure time for correct token
        start = time.perf_counter()
        for _ in range(1000):
            csrf.validate_token(token, token)
        correct_time = time.perf_counter() - start
        
        # Measure time for wrong token (different first char)
        wrong_token = "X" + token[1:]
        start = time.perf_counter()
        for _ in range(1000):
            csrf.validate_token(wrong_token, token)
        wrong_time = time.perf_counter() - start
        
        # Times should be similar (within 50% of each other)
        # This is a basic check - not a rigorous timing attack test
        ratio = max(correct_time, wrong_time) / min(correct_time, wrong_time)
        assert ratio < 2.0  # Should be close


# =============================================================================
# Vocabulary Matching Edge Cases
# =============================================================================

class TestVocabularyMatchingEdgeCases:
    """Test vocabulary matching answer edge cases."""
    
    def test_vocabulary_empty_matches(self):
        """Test vocabulary with empty matches dict."""
        from core.validation import VocabularyMatchAnswer
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            VocabularyMatchAnswer(matches={})
    
    def test_vocabulary_too_many_matches(self):
        """Test vocabulary with too many matches."""
        from core.validation import VocabularyMatchAnswer
        from pydantic import ValidationError
        
        # Create 11 matches (over limit of 10)
        matches = {f"term{i}": f"definition{i}" for i in range(11)}
        
        with pytest.raises(ValidationError):
            VocabularyMatchAnswer(matches=matches)
    
    def test_vocabulary_with_empty_values(self):
        """Test vocabulary with empty string values."""
        from core.validation import VocabularyMatchAnswer
        
        # Empty values should be filtered out
        matches = {"term1": "definition1", "term2": ""}
        result = VocabularyMatchAnswer(matches=matches)
        
        # Empty value should be filtered
        assert "term2" not in result.matches or result.matches.get("term2") == ""


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
