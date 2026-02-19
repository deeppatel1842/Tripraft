"""
Email Service — SMTP-based email sending.

Provides methods for sending various notification emails
with HTML templates and plain text fallbacks.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import Config

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP email service for sending notifications."""

    def __init__(self) -> None:
        """Initialize with configuration from Config."""
        self._smtp_host = Config.SMTP_HOST
        self._smtp_port = Config.SMTP_PORT
        self._smtp_user = Config.SMTP_USER
        self._smtp_password = Config.SMTP_PASSWORD
        self._from_email = Config.FROM_EMAIL or self._smtp_user
        self._from_name = Config.APP_NAME
        self._frontend_url = Config.FRONTEND_URL

    @property
    def enabled(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self._smtp_user and self._smtp_password)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug('Email to %s not sent (service disabled)', to_email)
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f'{self._from_name} <{self._from_email}>'
            msg['To'] = to_email
            msg['Subject'] = subject

            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)

            logger.info('Email sent to %s: %s', to_email, subject)
            return True

        except smtplib.SMTPException as exc:
            logger.error('SMTP error sending to %s: %s', to_email, exc)
            return False
        except Exception as exc:
            logger.error('Failed to send email to %s: %s', to_email, exc)
            return False

    def send_invitation(
        self,
        to_email: str,
        inviter_name: str,
        group_name: str,
        invitation_token: str,
        invitation_type: str = 'expense'
    ) -> bool:
        """
        Send group invitation email.
        
        Args:
            to_email: Recipient email
            inviter_name: Name of person who sent invitation
            group_name: Name of the group
            invitation_token: Unique invitation token
            invitation_type: Type of invitation ('expense' or 'trip')
        """
        base_path = 'expenses' if invitation_type == 'expense' else 'trips'
        invite_url = f'{self._frontend_url}/{base_path}/invite/{invitation_token}'

        subject = f'{inviter_name} invited you to join {group_name}'
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">You're Invited!</h2>
            <p><strong>{inviter_name}</strong> has invited you to join 
               <strong>{group_name}</strong> on {self._from_name}.</p>
            <p style="margin: 30px 0;">
                <a href="{invite_url}" 
                   style="background-color: #4CAF50; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Accept Invitation
                </a>
            </p>
            <p style="color: #666; font-size: 12px;">
                If you didn't expect this invitation, you can safely ignore this email.
            </p>
        </div>
        '''
        text_body = (
            f'{inviter_name} invited you to join {group_name}.\n\n'
            f'Accept here: {invite_url}'
        )

        return self.send_email(to_email, subject, html_body, text_body)

    def send_password_reset(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email."""
        reset_url = f'{self._frontend_url}/reset-password/{reset_token}'

        subject = f'Reset your {self._from_name} password'
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Password Reset</h2>
            <p>You requested to reset your password. Click the button below:</p>
            <p style="margin: 30px 0;">
                <a href="{reset_url}"
                   style="background-color: #2196F3; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #666; font-size: 12px;">
                This link expires in 1 hour. If you didn't request this, ignore this email.
            </p>
        </div>
        '''
        text_body = f'Reset your password here: {reset_url}'

        return self.send_email(to_email, subject, html_body, text_body)

    def send_verification(self, to_email: str, verification_token: str) -> bool:
        """Send email verification."""
        verify_url = f'{self._frontend_url}/verify-email/{verification_token}'

        subject = f'Verify your {self._from_name} email'
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Welcome to {self._from_name}!</h2>
            <p>Please verify your email address to get started:</p>
            <p style="margin: 30px 0;">
                <a href="{verify_url}"
                   style="background-color: #4CAF50; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Verify Email
                </a>
            </p>
        </div>
        '''
        text_body = f'Verify your email: {verify_url}'

        return self.send_email(to_email, subject, html_body, text_body)


# Singleton instance
email_service = EmailService()
