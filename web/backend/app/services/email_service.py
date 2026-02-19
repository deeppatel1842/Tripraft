"""
Email Service
Professional email handling for expense engine
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

# Load environment variables at module import
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        """Initialize email service with configuration"""
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'TripRaft')
        
        if not self.enabled:
            logger.info("Email service is disabled")
        elif not self.smtp_user or not self.smtp_password:
            logger.warning("Email credentials not configured - email service will be disabled")
            self.enabled = False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Email to {to_email} not sent (service disabled)")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text version
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_group_invitation(
        self,
        to_email: str,
        inviter_name: str,
        group_name: str,
        invitation_id: str
    ) -> bool:
        """
        Send group invitation email
        
        Args:
            to_email: Email address of invitee
            inviter_name: Name of person sending invitation
            group_name: Name of the group
            invitation_id: Invitation ID for link
            
        Returns:
            True if sent successfully, False otherwise
        """
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        invitation_link = f"{frontend_url}/invitations?id={invitation_id}"
        
        subject = f"{inviter_name} invited you to join '{group_name}'"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">You've been invited!</h2>
                <p><strong>{inviter_name}</strong> has invited you to join the group <strong>"{group_name}"</strong>.</p>
                <p>Join this group to track and split expenses together.</p>
                <div style="margin: 30px 0;">
                    <a href="{invitation_link}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Accept Invitation
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    Or copy this link: <a href="{invitation_link}">{invitation_link}</a>
                </p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                <p style="color: #9ca3af; font-size: 12px;">
                    This invitation was sent from TripRaft. If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        You've been invited!
        
        {inviter_name} has invited you to join the group "{group_name}".
        
        Join this group to track and split expenses together.
        
        Accept invitation: {invitation_link}
        
        ---
        This invitation was sent from TripRaft. If you didn't expect this invitation, you can safely ignore this email.
        """
        
        return self.send_email(to_email, subject, html_body, text_body)


# Singleton instance
email_service = EmailService()
