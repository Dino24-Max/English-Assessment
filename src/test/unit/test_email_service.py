"""
Unit tests for Email Service

Tests:
- Email configuration loading
- Console mode email logging
- Email template generation
- Password reset emails
- Invitation emails
- Assessment completion emails
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Add src/main/python to path BEFORE any other imports
project_root = Path(__file__).parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))

import pytest
from services.email_service import (
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailResult,
    get_email_service
)


# ============================================
# Email Configuration Tests
# ============================================

class TestEmailConfig:
    """Tests for EmailConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = EmailConfig()
        
        assert config.provider == EmailProvider.CONSOLE
        assert config.smtp_port == 587
        assert config.smtp_use_tls == True
        assert config.from_email == "noreply@cruise-assessment.com"
    
    def test_config_from_environment(self):
        """Test loading config from environment"""
        with patch.dict('os.environ', {
            'EMAIL_PROVIDER': 'smtp',
            'SMTP_HOST': 'smtp.example.com',
            'SMTP_PORT': '465',
            'SMTP_USERNAME': 'user@example.com',
            'SMTP_PASSWORD': 'secret',
            'EMAIL_FROM': 'test@example.com'
        }):
            config = EmailConfig.from_environment()
            
            assert config.provider == EmailProvider.SMTP
            assert config.smtp_host == 'smtp.example.com'
            assert config.smtp_port == 465
            assert config.smtp_username == 'user@example.com'
            assert config.from_email == 'test@example.com'
    
    def test_invalid_provider_fallback(self):
        """Test fallback to console for invalid provider"""
        with patch.dict('os.environ', {'EMAIL_PROVIDER': 'invalid_provider'}):
            config = EmailConfig.from_environment()
            assert config.provider == EmailProvider.CONSOLE


# ============================================
# Email Service Tests
# ============================================

class TestEmailService:
    """Tests for EmailService"""
    
    @pytest.fixture
    def console_service(self):
        """Create email service in console mode"""
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.fixture
    def smtp_service_no_host(self):
        """Create SMTP service without host (should fallback to console)"""
        config = EmailConfig(
            provider=EmailProvider.SMTP,
            smtp_host=""  # Empty host
        )
        return EmailService(config)
    
    def test_console_mode_initialization(self, console_service):
        """Test console mode service initialization"""
        assert console_service.config.provider == EmailProvider.CONSOLE
    
    def test_smtp_fallback_to_console(self, smtp_service_no_host):
        """Test SMTP falls back to console when host not configured"""
        assert smtp_service_no_host.config.provider == EmailProvider.CONSOLE
    
    @pytest.mark.asyncio
    async def test_send_email_console_mode(self, console_service):
        """Test sending email in console mode"""
        result = await console_service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<p>Test content</p>"
        )
        
        assert result.success == True
        assert result.message_id is not None
        assert result.message_id.startswith("console-")
    
    @pytest.mark.asyncio
    async def test_send_email_with_cc_bcc(self, console_service):
        """Test sending email with CC and BCC"""
        result = await console_service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<p>Test content</p>",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )
        
        assert result.success == True


# ============================================
# Password Reset Email Tests
# ============================================

class TestPasswordResetEmail:
    """Tests for password reset email functionality"""
    
    @pytest.fixture
    def service(self):
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, service):
        """Test sending password reset email"""
        result = await service.send_password_reset_email(
            to_email="user@example.com",
            reset_link="https://example.com/reset?token=abc123",
            user_name="John Doe"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_password_reset_email_default_name(self, service):
        """Test password reset email with default user name"""
        result = await service.send_password_reset_email(
            to_email="user@example.com",
            reset_link="https://example.com/reset?token=abc123"
        )
        
        assert result.success == True


# ============================================
# Invitation Email Tests
# ============================================

class TestInvitationEmail:
    """Tests for invitation email functionality"""
    
    @pytest.fixture
    def service(self):
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_send_invitation_email(self, service):
        """Test sending invitation email"""
        result = await service.send_invitation_email(
            to_email="candidate@example.com",
            invitation_code="ABC123XYZ",
            invitation_link="https://example.com/register?code=ABC123XYZ",
            invited_by="HR Manager"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_invitation_email_with_expiry(self, service):
        """Test invitation email with expiration date"""
        expires_at = datetime.now() + timedelta(days=7)
        
        result = await service.send_invitation_email(
            to_email="candidate@example.com",
            invitation_code="ABC123XYZ",
            invitation_link="https://example.com/register?code=ABC123XYZ",
            expires_at=expires_at
        )
        
        assert result.success == True


# ============================================
# Assessment Completion Email Tests
# ============================================

class TestAssessmentCompletionEmail:
    """Tests for assessment completion email functionality"""
    
    @pytest.fixture
    def service(self):
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_send_completion_email_passed(self, service):
        """Test sending completion email for passed assessment"""
        module_scores = {
            "Listening": 14,
            "Time & Numbers": 12,
            "Grammar": 13,
            "Vocabulary": 14,
            "Reading": 12,
            "Speaking": 16
        }
        
        result = await service.send_assessment_completion_email(
            to_email="user@example.com",
            user_name="John Doe",
            total_score=81,
            passed=True,
            module_scores=module_scores,
            certificate_url="https://example.com/certificate/123"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_send_completion_email_failed(self, service):
        """Test sending completion email for failed assessment"""
        module_scores = {
            "Listening": 8,
            "Time & Numbers": 6,
            "Grammar": 7,
            "Vocabulary": 8,
            "Reading": 6,
            "Speaking": 10
        }
        
        result = await service.send_assessment_completion_email(
            to_email="user@example.com",
            user_name="Jane Doe",
            total_score=45,
            passed=False,
            module_scores=module_scores
        )
        
        assert result.success == True


# ============================================
# Admin Notification Email Tests
# ============================================

class TestAdminNotificationEmail:
    """Tests for admin notification email functionality"""
    
    @pytest.fixture
    def service(self):
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_send_admin_notification(self, service):
        """Test sending admin notification"""
        result = await service.send_admin_notification(
            to_email="admin@example.com",
            subject="New Assessment Completed",
            message="A new assessment has been completed.",
            data={
                "User": "John Doe",
                "Score": "85/100",
                "Status": "PASSED"
            }
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_send_admin_notification_no_data(self, service):
        """Test sending admin notification without extra data"""
        result = await service.send_admin_notification(
            to_email="admin@example.com",
            subject="System Alert",
            message="This is a system alert message."
        )
        
        assert result.success == True


# ============================================
# Singleton Pattern Tests
# ============================================

class TestEmailServiceSingleton:
    """Tests for email service singleton pattern"""
    
    def test_get_email_service_singleton(self):
        """Test that get_email_service returns singleton"""
        # Reset singleton
        import services.email_service as email_module
        email_module._email_service = None
        
        service1 = get_email_service()
        service2 = get_email_service()
        
        assert service1 is service2


# ============================================
# Email Result Tests
# ============================================

class TestEmailResult:
    """Tests for EmailResult dataclass"""
    
    def test_success_result(self):
        """Test successful email result"""
        result = EmailResult(success=True, message_id="msg-123")
        
        assert result.success == True
        assert result.message_id == "msg-123"
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed email result"""
        result = EmailResult(success=False, error="Connection refused")
        
        assert result.success == False
        assert result.message_id is None
        assert result.error == "Connection refused"


# ============================================
# SMTP Email Tests (Mocked)
# ============================================

class TestSMTPEmail:
    """Tests for SMTP email sending (mocked)"""
    
    @pytest.fixture
    def smtp_service(self):
        """Create SMTP service with valid config"""
        config = EmailConfig(
            provider=EmailProvider.SMTP,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            smtp_use_tls=True
        )
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_smtp_send_success(self, smtp_service):
        """Test successful SMTP send (mocked)"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            
            result = await smtp_service._send_smtp(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
                text_content=None,
                cc=None,
                bcc=None
            )
            
            assert result.success == True
    
    @pytest.mark.asyncio
    async def test_smtp_send_failure(self, smtp_service):
        """Test SMTP send failure (mocked)"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("Connection failed")
            
            result = await smtp_service._send_smtp(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
                text_content=None,
                cc=None,
                bcc=None
            )
            
            assert result.success == False
            assert "Connection failed" in result.error


# ============================================
# Edge Cases
# ============================================

class TestEdgeCases:
    """Tests for edge cases"""
    
    @pytest.fixture
    def service(self):
        config = EmailConfig(provider=EmailProvider.CONSOLE)
        return EmailService(config)
    
    @pytest.mark.asyncio
    async def test_empty_html_content(self, service):
        """Test sending email with empty HTML content"""
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content=""
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_special_characters_in_subject(self, service):
        """Test email with special characters in subject"""
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test <Subject> with 'special' \"characters\" & symbols!",
            html_content="<p>Test</p>"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, service):
        """Test email with unicode content"""
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test with émojis 🚢 and ünïcödé",
            html_content="<p>Content with 中文 and العربية</p>"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_long_email_content(self, service):
        """Test email with very long content"""
        long_content = "<p>" + "A" * 10000 + "</p>"
        
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content=long_content
        )
        
        assert result.success == True
