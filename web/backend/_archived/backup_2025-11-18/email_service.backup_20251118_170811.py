"""
Group Planner Email Service
SMTP configuration and email templates for group planner system
Handles invitation emails and notifications
"""

import logging
import smtplib
import os
import sys
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Add parent directory to path for email_config import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from email_config import email_config

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration from environment"""

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds


class EmailTemplates:
    """HTML email templates"""

    @staticmethod
    def invitation_email(inviter_name: str, group_name: str, invitation_link: str) -> str:
        """
        Group invitation email template
        
        Args:
            inviter_name: Name of person inviting
            group_name: Name of the travel group
            invitation_link: Link to accept invitation
            
        Returns:
            HTML email body
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f1f1f1; padding: 20px; text-align: center; 
                          font-size: 12px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; 
                          padding: 12px 30px; text-decoration: none; border-radius: 5px; 
                          margin: 20px 0; font-weight: bold; }}
                .button:hover {{ background: #764ba2; }}
                .info-box {{ background: #e3f2fd; padding: 15px; border-left: 4px solid #667eea; 
                           margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌍 You're Invited to Travel!</h1>
                </div>
                
                <div class="content">
                    <h2>Hello!</h2>
                    
                    <p><strong>{inviter_name}</strong> has invited you to join a travel group:</p>
                    
                    <div class="info-box">
                        <h3 style="margin: 0 0 10px 0;">📍 {group_name}</h3>
                        <p style="margin: 0;">Plan your trip together with collaborative tools for places, 
                           polls, budget tracking, and more!</p>
                    </div>
                    
                    <p>Click the button below to accept the invitation and start planning:</p>
                    
                    <center>
                        <a href="{invitation_link}" class="button">Accept Invitation</a>
                    </center>
                    
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; background: #fff; padding: 10px; 
                              border: 1px solid #ddd; border-radius: 4px;">
                        {invitation_link}
                    </p>
                    
                    <p><strong>This invitation expires in 7 days.</strong></p>
                </div>
                
                <div class="footer">
                    <p>© 2025 TripRaft - Collaborative Travel Planning</p>
                    <p>If you didn't expect this invitation, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def member_joined_email(
        new_member_name: str, group_name: str, group_link: str
    ) -> str:
        """
        Member joined group notification email
        
        Args:
            new_member_name: Name of new member
            group_name: Name of the travel group
            group_link: Link to view group
            
        Returns:
            HTML email body
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f1f1f1; padding: 20px; text-align: center; 
                          font-size: 12px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; 
                          padding: 12px 30px; text-decoration: none; border-radius: 5px; 
                          margin: 20px 0; font-weight: bold; }}
                .button:hover {{ background: #764ba2; }}
                .notification {{ background: #f0f9ff; padding: 15px; border-left: 4px solid #667eea; 
                               margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 New Member Joined!</h1>
                </div>
                
                <div class="content">
                    <h2>Great news!</h2>
                    
                    <div class="notification">
                        <p style="margin: 0; font-size: 16px;">
                            <strong>{new_member_name}</strong> has joined the group <strong>{group_name}</strong>
                        </p>
                    </div>
                    
                    <p>You can now start collaborating on:</p>
                    <ul>
                        <li>📍 Adding and voting on places to visit</li>
                        <li>🗳️ Creating polls for group decisions</li>
                        <li>💬 Adding remarks and recommendations</li>
                        <li>📊 Tracking shared expenses</li>
                    </ul>
                    
                    <center>
                        <a href="{group_link}" class="button">View Group</a>
                    </center>
                </div>
                
                <div class="footer">
                    <p>© 2025 TripRaft - Collaborative Travel Planning</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def poll_created_email(
        creator_name: str, group_name: str, poll_question: str, poll_link: str
    ) -> str:
        """
        Poll created notification email
        
        Args:
            creator_name: Name of person creating poll
            group_name: Name of the travel group
            poll_question: The poll question
            poll_link: Link to view/vote on poll
            
        Returns:
            HTML email body
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f1f1f1; padding: 20px; text-align: center; 
                          font-size: 12px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; 
                          padding: 12px 30px; text-decoration: none; border-radius: 5px; 
                          margin: 20px 0; font-weight: bold; }}
                .button:hover {{ background: #764ba2; }}
                .poll-box {{ background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; 
                           margin: 20px 0; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🗳️ New Poll in {group_name}</h1>
                </div>
                
                <div class="content">
                    <h2>A group decision needs your input!</h2>
                    
                    <p><strong>{creator_name}</strong> has created a new poll in <strong>{group_name}</strong>:</p>
                    
                    <div class="poll-box">
                        <h3 style="margin: 0 0 10px 0;">❓ {poll_question}</h3>
                        <p style="margin: 0; color: #666;">Your vote will help the group decide together!</p>
                    </div>
                    
                    <p>Click the link below to view and vote on this poll:</p>
                    
                    <center>
                        <a href="{poll_link}" class="button">Vote Now</a>
                    </center>
                </div>
                
                <div class="footer">
                    <p>© 2025 TripRaft - Collaborative Travel Planning</p>
                </div>
            </div>
        </body>
        </html>
        """


class GroupPlannerEmailService:
    """Email service for group planner notifications"""

    def __init__(self):
        """Initialize email service"""
        self.config = EmailConfig()
        # logger.info("GroupPlannerEmailService initialized")

    def _send_email(
        self, to_email: str, subject: str, html_body: str
    ) -> bool:
        """
        Send email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate email configuration
            if not self.config.SMTP_USER or not self.config.SMTP_PASSWORD:
                logger.warning("SMTP credentials not configured, email not sent to %s", to_email)
                return False

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.FROM_EMAIL
            msg["To"] = to_email

            # Attach HTML
            msg.attach(MIMEText(html_body, "html"))

            # Send with retry logic
            for attempt in range(1, self.config.RETRY_ATTEMPTS + 1):
                try:
                    # logger.info("Sending email to %s (attempt %d/%d)", 
                              to_email, attempt, self.config.RETRY_ATTEMPTS)
                    
                    # Create SMTP connection
                    with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
                        server.starttls()
                        server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                        server.send_message(msg)
                    
                    # logger.info("Email sent successfully to %s", to_email)
                    return True

                except smtplib.SMTPAuthenticationError as e:
                    logger.error("SMTP authentication failed: %s", e)
                    return False
                except smtplib.SMTPException as e:
                    if attempt < self.config.RETRY_ATTEMPTS:
                        logger.warning("SMTP error on attempt %d: %s, retrying...", 
                                     attempt, e)
                        continue
                    logger.error("SMTP error after %d attempts: %s", 
                               self.config.RETRY_ATTEMPTS, e)
                    return False

            return False

        except Exception as e:
            logger.error("Error sending email to %s: %s", to_email, e)
            return False

    def send_group_invitation(
        self,
        invited_email: str,
        inviter_name: str,
        group_name: str,
        invitation_id: str,
    ) -> bool:
        """
        Send group invitation email
        
        Args:
            invited_email: Email of invited person
            inviter_name: Name of person inviting
            group_name: Name of travel group
            invitation_id: Invitation ID for link
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Check if invitation emails are enabled
            if not email_config.is_enabled('invitation'):
                # logger.info(f"📧 Invitation emails disabled - skipping email to {invited_email}")
                # logger.info(f"💡 Group: {group_name} | Inviter: {inviter_name} | Invitation ID: {invitation_id}")
                return False
            
            # Build invitation link with type parameter for proper routing
            invitation_link = f"{self.config.FRONTEND_URL}/accept-invitation?id={invitation_id}&type=group"

            # Get email template
            html_body = EmailTemplates.invitation_email(
                inviter_name=inviter_name,
                group_name=group_name,
                invitation_link=invitation_link,
            )

            # Send email
            success = self._send_email(
                to_email=invited_email,
                subject=f"You're invited to join '{group_name}' on TripRaft!",
                html_body=html_body,
            )

            if success:
                # logger.info("Sent invitation email to %s for group %s", 
                # invited_email, group_name)
            else:
                logger.warning("Failed to send invitation email to %s", invited_email)

            return success

        except Exception as e:
            logger.error("Error sending invitation email: %s", e)
            return False

    def send_member_joined_notification(
        self,
        group_member_emails: List[str],
        new_member_name: str,
        group_name: str,
        group_id: str,
    ) -> bool:
        """
        Send notification when member joins group
        
        Args:
            group_member_emails: List of group member emails to notify
            new_member_name: Name of new member
            group_name: Name of travel group
            group_id: ID of group
            
        Returns:
            True if all emails sent successfully
        """
        try:
            if not group_member_emails:
                # logger.debug("No group members to notify")
                return True

            # Build group link
            group_link = f"{self.config.FRONTEND_URL}/groups/{group_id}"

            # Get email template
            html_body = EmailTemplates.member_joined_email(
                new_member_name=new_member_name,
                group_name=group_name,
                group_link=group_link,
            )

            # Send to all members
            all_successful = True
            for email in group_member_emails:
                success = self._send_email(
                    to_email=email,
                    subject=f"{new_member_name} joined '{group_name}' on TripRaft!",
                    html_body=html_body,
                )
                if not success:
                    all_successful = False

            if all_successful:
                # logger.info("Sent member joined notification to %d members", 
                # len(group_member_emails))
            else:
                logger.warning("Failed to send member joined notification to all members")

            return all_successful

        except Exception as e:
            logger.error("Error sending member joined notifications: %s", e)
            return False

    def send_poll_created_notification(
        self,
        group_member_emails: List[str],
        creator_name: str,
        group_name: str,
        group_id: str,
        poll_question: str,
        poll_id: str,
    ) -> bool:
        """
        Send notification when poll is created
        
        Args:
            group_member_emails: List of group member emails to notify
            creator_name: Name of poll creator
            group_name: Name of travel group
            group_id: ID of group
            poll_question: The poll question
            poll_id: ID of poll
            
        Returns:
            True if all emails sent successfully
        """
        try:
            if not group_member_emails:
                # logger.debug("No group members to notify")
                return True

            # Build poll link
            poll_link = f"{self.config.FRONTEND_URL}/groups/{group_id}/polls/{poll_id}"

            # Get email template
            html_body = EmailTemplates.poll_created_email(
                creator_name=creator_name,
                group_name=group_name,
                poll_question=poll_question,
                poll_link=poll_link,
            )

            # Send to all members
            all_successful = True
            for email in group_member_emails:
                success = self._send_email(
                    to_email=email,
                    subject=f"New poll in '{group_name}': {poll_question}",
                    html_body=html_body,
                )
                if not success:
                    all_successful = False

            if all_successful:
                # logger.info("Sent poll created notification to %d members", 
                # len(group_member_emails))
            else:
                logger.warning("Failed to send poll created notification to all members")

            return all_successful

        except Exception as e:
            logger.error("Error sending poll created notifications: %s", e)
            return False

    def test_email_configuration(self, test_email: str = None) -> bool:
        """
        Test email configuration by sending test email
        
        Args:
            test_email: Email to send test to (uses FROM_EMAIL if not provided)
            
        Returns:
            True if test email sent successfully
        """
        try:
            test_email = test_email or self.config.FROM_EMAIL

            html_body = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>✅ Email Configuration Test Successful</h2>
                    <p>This is a test email from TripRaft Group Planner.</p>
                    <p>Email configuration is working correctly!</p>
                    <p><small>Sent at: """ + datetime.utcnow().isoformat() + """</small></p>
                </div>
            </body>
            </html>
            """

            success = self._send_email(
                to_email=test_email,
                subject="TripRaft Email Configuration Test",
                html_body=html_body,
            )

            if success:
                # logger.info("Test email sent successfully to %s", test_email)
            else:
                logger.error("Failed to send test email to %s", test_email)

            return success

        except Exception as e:
            logger.error("Error sending test email: %s", e)
            return False
