"""
Email Service for Cruise Employee English Assessment Platform

Provides email functionality for:
- Password reset emails
- Invitation emails with assessment links
- Assessment completion notifications
- Admin notifications

Supports multiple email providers:
- SMTP (default, works with any SMTP server)
- SendGrid (optional, for production)
- AWS SES (optional, for production)
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class EmailProvider(Enum):
    """Supported email providers"""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    CONSOLE = "console"  # For development - logs to console


@dataclass
class EmailConfig:
    """Email configuration"""
    provider: EmailProvider = EmailProvider.CONSOLE
    
    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    
    # SendGrid settings
    sendgrid_api_key: str = ""
    
    # AWS SES settings
    aws_region: str = "us-east-1"
    aws_access_key: str = ""
    aws_secret_key: str = ""
    
    # Common settings
    from_email: str = "noreply@cruise-assessment.com"
    from_name: str = "Cruise Employee Assessment"
    reply_to: str = ""
    
    @classmethod
    def from_environment(cls) -> "EmailConfig":
        """Load configuration from environment variables"""
        provider_str = os.getenv("EMAIL_PROVIDER", "console").lower()
        
        try:
            provider = EmailProvider(provider_str)
        except ValueError:
            provider = EmailProvider.CONSOLE
        
        return cls(
            provider=provider,
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            from_email=os.getenv("EMAIL_FROM", "noreply@cruise-assessment.com"),
            from_name=os.getenv("EMAIL_FROM_NAME", "Cruise Employee Assessment"),
            reply_to=os.getenv("EMAIL_REPLY_TO", "")
        )


@dataclass
class EmailResult:
    """Result of email sending operation"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailService:
    """
    Email service for sending various types of emails.
    
    Supports multiple providers and graceful fallback to console logging
    when email is not configured.
    """
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Initialize email service.
        
        Args:
            config: Email configuration. If None, loads from environment.
        """
        self.config = config or EmailConfig.from_environment()
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration and log warnings for missing settings"""
        if self.config.provider == EmailProvider.SMTP:
            if not self.config.smtp_host:
                logger.warning("SMTP host not configured, falling back to console")
                self.config.provider = EmailProvider.CONSOLE
        elif self.config.provider == EmailProvider.SENDGRID:
            if not self.config.sendgrid_api_key:
                logger.warning("SendGrid API key not configured, falling back to console")
                self.config.provider = EmailProvider.CONSOLE
        elif self.config.provider == EmailProvider.AWS_SES:
            if not self.config.aws_access_key:
                logger.warning("AWS credentials not configured, falling back to console")
                self.config.provider = EmailProvider.CONSOLE
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> EmailResult:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, derived from HTML if not provided)
            cc: CC recipients
            bcc: BCC recipients
            
        Returns:
            EmailResult with success status and any errors
        """
        if self.config.provider == EmailProvider.CONSOLE:
            return self._send_console(to_email, subject, html_content)
        elif self.config.provider == EmailProvider.SMTP:
            return await self._send_smtp(to_email, subject, html_content, text_content, cc, bcc)
        elif self.config.provider == EmailProvider.SENDGRID:
            return await self._send_sendgrid(to_email, subject, html_content, text_content, cc, bcc)
        elif self.config.provider == EmailProvider.AWS_SES:
            return await self._send_ses(to_email, subject, html_content, text_content, cc, bcc)
        else:
            return EmailResult(success=False, error="Unknown email provider")
    
    def _send_console(self, to_email: str, subject: str, html_content: str) -> EmailResult:
        """Log email to console (development mode)"""
        logger.info("=" * 60)
        logger.info("EMAIL (Console Mode - Not Actually Sent)")
        logger.info("=" * 60)
        logger.info(f"To: {to_email}")
        logger.info(f"From: {self.config.from_name} <{self.config.from_email}>")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 60)
        logger.info(f"Content Preview: {html_content[:500]}...")
        logger.info("=" * 60)
        
        return EmailResult(success=True, message_id="console-" + str(datetime.now().timestamp()))
    
    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]]
    ) -> EmailResult:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = to_email
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            if self.config.reply_to:
                msg["Reply-To"] = self.config.reply_to
            
            # Add text and HTML parts
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Send email
            context = ssl.create_default_context()
            
            if self.config.smtp_use_tls:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls(context=context)
                    if self.config.smtp_username:
                        server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(self.config.from_email, recipients, msg.as_string())
            else:
                with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, context=context) as server:
                    if self.config.smtp_username:
                        server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(self.config.from_email, recipients, msg.as_string())
            
            logger.info(f"Email sent via SMTP to {to_email}")
            return EmailResult(success=True, message_id=f"smtp-{datetime.now().timestamp()}")
            
        except Exception as e:
            logger.error(f"SMTP email failed: {e}")
            return EmailResult(success=False, error=str(e))
    
    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]]
    ) -> EmailResult:
        """Send email via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content, Cc, Bcc
            
            message = Mail(
                from_email=Email(self.config.from_email, self.config.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            if cc:
                for email in cc:
                    message.add_cc(Cc(email))
            
            if bcc:
                for email in bcc:
                    message.add_bcc(Bcc(email))
            
            sg = SendGridAPIClient(self.config.sendgrid_api_key)
            response = sg.send(message)
            
            logger.info(f"Email sent via SendGrid to {to_email}, status: {response.status_code}")
            return EmailResult(
                success=response.status_code in [200, 201, 202],
                message_id=response.headers.get("X-Message-Id")
            )
            
        except ImportError:
            logger.error("SendGrid library not installed. Run: pip install sendgrid")
            return EmailResult(success=False, error="SendGrid library not installed")
        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
            return EmailResult(success=False, error=str(e))
    
    async def _send_ses(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]]
    ) -> EmailResult:
        """Send email via AWS SES"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            client = boto3.client(
                'ses',
                region_name=self.config.aws_region,
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key
            )
            
            destination = {"ToAddresses": [to_email]}
            if cc:
                destination["CcAddresses"] = cc
            if bcc:
                destination["BccAddresses"] = bcc
            
            body = {"Html": {"Charset": "UTF-8", "Data": html_content}}
            if text_content:
                body["Text"] = {"Charset": "UTF-8", "Data": text_content}
            
            response = client.send_email(
                Source=f"{self.config.from_name} <{self.config.from_email}>",
                Destination=destination,
                Message={
                    "Subject": {"Charset": "UTF-8", "Data": subject},
                    "Body": body
                }
            )
            
            logger.info(f"Email sent via AWS SES to {to_email}")
            return EmailResult(success=True, message_id=response["MessageId"])
            
        except ImportError:
            logger.error("boto3 library not installed. Run: pip install boto3")
            return EmailResult(success=False, error="boto3 library not installed")
        except Exception as e:
            logger.error(f"AWS SES email failed: {e}")
            return EmailResult(success=False, error=str(e))
    
    # ========================================
    # Template Methods for Common Emails
    # ========================================
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: str = "User"
    ) -> EmailResult:
        """
        Send password reset email.
        
        Args:
            to_email: Recipient email
            reset_link: Password reset URL
            user_name: User's name for personalization
            
        Returns:
            EmailResult
        """
        subject = "Reset Your Password - Cruise Employee Assessment"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #B61B38 0%, #014E8F 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #B61B38; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>We received a request to reset your password for your Cruise Employee Assessment account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <div class="warning">
                        <strong>Important:</strong> This link will expire in 1 hour for security reasons.
                    </div>
                    <p>If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                    <p>If you're having trouble clicking the button, copy and paste this URL into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_link}</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from Cruise Employee Assessment Platform.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {user_name},
        
        We received a request to reset your password for your Cruise Employee Assessment account.
        
        Click the link below to reset your password:
        {reset_link}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request this password reset, you can safely ignore this email.
        
        - Cruise Employee Assessment Platform
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_invitation_email(
        self,
        to_email: str,
        invitation_code: str,
        invitation_link: str,
        invited_by: str = "Administrator",
        expires_at: Optional[datetime] = None
    ) -> EmailResult:
        """
        Send assessment invitation email.
        
        Args:
            to_email: Recipient email
            invitation_code: Unique invitation code
            invitation_link: Full URL to start assessment
            invited_by: Name of person who sent invitation
            expires_at: When the invitation expires
            
        Returns:
            EmailResult
        """
        subject = "You're Invited - Cruise Employee English Assessment"
        
        expiry_text = ""
        if expires_at:
            expiry_text = f"<p><strong>Note:</strong> This invitation expires on {expires_at.strftime('%B %d, %Y at %I:%M %p')}.</p>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #B61B38 0%, #014E8F 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #014E8F; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 16px; }}
                .code-box {{ background: #fff; border: 2px dashed #014E8F; padding: 15px; text-align: center; margin: 20px 0; border-radius: 5px; }}
                .code {{ font-size: 24px; font-weight: bold; color: #014E8F; letter-spacing: 2px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                .info-box {{ background: #e7f3ff; border-left: 4px solid #014E8F; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚢 Assessment Invitation</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You have been invited by <strong>{invited_by}</strong> to complete the Cruise Employee English Assessment.</p>
                    
                    <div class="info-box">
                        <h3>Assessment Overview:</h3>
                        <ul>
                            <li><strong>Duration:</strong> Approximately 30 minutes</li>
                            <li><strong>Modules:</strong> Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking</li>
                            <li><strong>Total Points:</strong> 100</li>
                        </ul>
                    </div>
                    
                    <p style="text-align: center;">
                        <a href="{invitation_link}" class="button">Start Assessment</a>
                    </p>
                    
                    <div class="code-box">
                        <p>Your Invitation Code:</p>
                        <p class="code">{invitation_code}</p>
                    </div>
                    
                    {expiry_text}
                    
                    <p><strong>Tips for Success:</strong></p>
                    <ul>
                        <li>Find a quiet place with stable internet connection</li>
                        <li>Use headphones for the listening section</li>
                        <li>Ensure your microphone works for the speaking section</li>
                        <li>Complete the assessment in one sitting</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Good luck with your assessment!</p>
                    <p>Cruise Employee Assessment Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello,
        
        You have been invited by {invited_by} to complete the Cruise Employee English Assessment.
        
        ASSESSMENT OVERVIEW:
        - Duration: Approximately 30 minutes
        - Modules: Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking
        - Total Points: 100
        
        START YOUR ASSESSMENT:
        {invitation_link}
        
        YOUR INVITATION CODE: {invitation_code}
        
        TIPS FOR SUCCESS:
        - Find a quiet place with stable internet connection
        - Use headphones for the listening section
        - Ensure your microphone works for the speaking section
        - Complete the assessment in one sitting
        
        Good luck!
        - Cruise Employee Assessment Platform
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_assessment_completion_email(
        self,
        to_email: str,
        user_name: str,
        total_score: float,
        module_scores: Dict[str, float]
    ) -> EmailResult:
        """
        Send assessment completion notification.
        
        Args:
            to_email: Recipient email
            user_name: User's name
            total_score: Total score achieved
            module_scores: Scores for each module
            
        Returns:
            EmailResult
        """
        subject = "Your Assessment Results - Cruise Employee English Assessment"
        
        # Build module scores HTML
        module_rows = ""
        for module, score in module_scores.items():
            module_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{module}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{score:.1f}</td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #B61B38 0%, #014E8F 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .score-box {{ background: white; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .score {{ font-size: 48px; font-weight: bold; color: #014E8F; }}
                .button {{ display: inline-block; background: #014E8F; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #014E8F; color: white; padding: 12px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Assessment Complete</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Thank you for completing the Cruise Employee English Assessment. Here are your results:</p>
                    
                    <div class="score-box">
                        <div class="score">{total_score:.1f}/100</div>
                    </div>
                    
                    <h3>Module Breakdown:</h3>
                    <table>
                        <tr>
                            <th>Module</th>
                            <th style="text-align: center;">Score</th>
                        </tr>
                        {module_rows}
                    </table>
                    
                    <p>Your results have been recorded and will be reviewed by our team. Thank you for your participation.</p>
                </div>
                <div class="footer">
                    <p>Thank you for using Cruise Employee Assessment Platform.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {user_name},
        
        Thank you for completing the Cruise Employee English Assessment.
        
        YOUR RESULTS:
        Total Score: {total_score:.1f}/100
        
        MODULE BREAKDOWN:
        {chr(10).join([f"- {module}: {score:.1f}" for module, score in module_scores.items()])}
        
        Your results have been recorded and will be reviewed by our team.
        
        - Cruise Employee Assessment Platform
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_admin_notification(
        self,
        to_email: str,
        subject: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> EmailResult:
        """
        Send admin notification email.
        
        Args:
            to_email: Admin email
            subject: Email subject
            message: Notification message
            data: Additional data to include
            
        Returns:
            EmailResult
        """
        data_rows = ""
        if data:
            for key, value in data.items():
                data_rows += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'><strong>{key}</strong></td><td style='padding: 8px; border: 1px solid #ddd;'>{value}</td></tr>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #333; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Admin Notification</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                    {f"<table>{data_rows}</table>" if data_rows else ""}
                    <p style="color: #666; font-size: 12px;">Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, f"[Admin] {subject}", html_content)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
