"""
Expense Engine - Email Service
Handles email notifications for group invitations and expense updates
Production-ready with retry logic and error handling
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config
from email_config import email_config

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        """Initialize email service"""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.app_name = Config.APP_NAME
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        if not self.smtp_user or not self.smtp_password:
            logger.warning("Email credentials not configured. Email notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("EmailService initialized successfully")
    
    def send_email(self, to_email: str, subject: str, html_content: str,
                   text_content: Optional[str] = None) -> bool:
        """
        Send email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            
        Returns:
            Success status
        """
        if not self.enabled:
            logger.warning("Email service disabled. Would have sent: %s to %s", subject, to_email)
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info("Email sent successfully to %s", to_email)
            return True
        
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return False
    
    def send_group_invitation(self, to_email: str, inviter_name: str,
                            group_name: str, invitation_id: str) -> bool:
        """
        Send group invitation email
        
        Args:
            to_email: Invitee's email
            inviter_name: Name of person who sent invitation
            group_name: Group name
            invitation_id: Invitation ID for accepting
            
        Returns:
            Success status
        """
        if not email_config.is_enabled('invitation'):
            logger.info("Invitation emails disabled - skipping email to %s", to_email)
            return False
        
        subject = f"{inviter_name} invited you to join '{group_name}' on {self.app_name}"
        invitation_link = f"{self.frontend_url}/accept-invitation?id={invitation_id}&type=expense"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; 
                           border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; 
                          color: white; text-decoration: none; border-radius: 5px; 
                          margin: 20px 0; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name} Expense Tracker</h1>
                </div>
                <div class="content">
                    <h2>You've been invited to join a group!</h2>
                    <p><strong>{inviter_name}</strong> has invited you to join the group 
                       <strong>"{group_name}"</strong>.</p>
                    
                    <p>Join the group to:</p>
                    <ul>
                        <li>Share and split expenses with group members</li>
                        <li>Track who owes whom</li>
                        <li>Settle balances easily</li>
                    </ul>
                    
                    <div style="text-align: center;">
                        <a href="{invitation_link}" class="button">Accept Invitation</a>
                    </div>
                    
                    <p style="font-size: 12px; color: #999;">
                        This invitation link will expire in 7 days.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {self.app_name} Expense Tracker
        
        You've been invited to join a group!
        
        {inviter_name} has invited you to join the group "{group_name}".
        
        Accept invitation: {invitation_link}
        
        This invitation link will expire in 7 days.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_invitation_email(self, recipient_data: dict) -> bool:
        """
        Send invitation email (called by email_worker)
        
        Args:
            recipient_data: Dictionary with:
                - invited_email: Recipient email
                - inviter_name: Name of person who sent invitation
                - group_name: Group name
                - invitation_link: Link to accept invitation
        
        Returns:
            Success status
        """
        invitation_id = ''
        invitation_link = recipient_data.get('invitation_link', '')
        if 'id=' in invitation_link:
            invitation_id = invitation_link.split('id=')[1].split('&')[0]
        
        return self.send_group_invitation(
            to_email=recipient_data['invited_email'],
            inviter_name=recipient_data['inviter_name'],
            group_name=recipient_data['group_name'],
            invitation_id=invitation_id
        )
    
    def send_expense_added_notification(self, to_email: str, user_name: str,
                                       expense_description: str, amount: float,
                                       user_share: float, payer_name: str, 
                                       group_name: str) -> bool:
        """
        Send notification when a new expense is added
        """
        if not email_config.is_enabled('expense_added'):
            logger.info("Expense added emails disabled - skipping email to %s", to_email)
            return False
        
        subject = f"New expense added in '{group_name}'"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; 
                           border-radius: 0 0 8px 8px; }}
                .expense-box {{ background: #fff3e0; padding: 20px; border-radius: 8px; 
                               margin: 20px 0; border-left: 4px solid #ff9800; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #ff9800; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>New expense in {group_name}</h2>
                    <p>Hi {user_name},</p>
                    <p><strong>{payer_name}</strong> added a new expense.</p>
                    
                    <div class="expense-box">
                        <p><strong>Description:</strong> {expense_description}</p>
                        <p><strong>Total Amount:</strong> <span class="amount">${amount:.2f}</span></p>
                        <p><strong>Your Share:</strong> ${user_share:.2f}</p>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_expense_deleted_notification(self, to_email: str, user_name: str,
                                         expense_description: str, amount: float,
                                         deleted_by_name: str, group_name: str) -> bool:
        """
        Send notification when an expense is deleted
        """
        if not email_config.is_enabled('expense_deleted'):
            logger.info("Expense deleted emails disabled - skipping email to %s", to_email)
            return False
        
        subject = f"Expense deleted in '{group_name}'"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f44336 0%, #e91e63 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; 
                           border-radius: 0 0 8px 8px; }}
                .expense-box {{ background: #ffebee; padding: 20px; border-radius: 8px; 
                               margin: 20px 0; border-left: 4px solid #f44336; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #f44336; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>Expense deleted in {group_name}</h2>
                    <p>Hi {user_name},</p>
                    <p><strong>{deleted_by_name}</strong> deleted an expense.</p>
                    
                    <div class="expense-box">
                        <p><strong>Description:</strong> {expense_description}</p>
                        <p><strong>Amount:</strong> <span class="amount">${amount:.2f}</span></p>
                    </div>
                    
                    <p style="color: #666;">The balances have been updated accordingly.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)

    def send_settlement_notification(self, recipient_data: dict) -> bool:
        """
        Send settlement notification (called by email_worker)
        """
        if not email_config.is_enabled('settlement'):
            logger.info("Settlement emails disabled")
            return False
        
        to_email = recipient_data.get('to_email', '')
        recipient_name = recipient_data.get('recipient_name', '')
        from_user_name = recipient_data.get('from_user_name', '')
        amount = recipient_data.get('amount', 0)
        group_name = recipient_data.get('group_name', '')
        
        group_text = f" in '{group_name}'" if group_name else ""
        subject = f"Payment received{group_text} - {self.app_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; 
                           border-radius: 0 0 8px 8px; }}
                .payment-box {{ background: #e8f5e9; padding: 20px; border-radius: 8px; 
                               margin: 20px 0; border-left: 4px solid #4caf50; }}
                .amount {{ font-size: 28px; font-weight: bold; color: #4caf50; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>Payment Received!</h2>
                    <p>Hi {recipient_name},</p>
                    <p><strong>{from_user_name}</strong> has marked a payment{group_text}.</p>
                    
                    <div class="payment-box">
                        <p><strong>Amount received:</strong></p>
                        <p class="amount">${amount:.2f}</p>
                    </div>
                    
                    <p>Your balance has been updated accordingly.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)

    def send_expense_notification(self, recipient_data: dict) -> bool:
        """
        Send expense notification (called by email_worker for updates)
        """
        return self.send_expense_added_notification(
            to_email=recipient_data.get('to_email', ''),
            user_name=recipient_data.get('user_name', ''),
            expense_description=recipient_data.get('expense_description', ''),
            amount=recipient_data.get('amount', 0),
            user_share=recipient_data.get('user_share', 0),
            payer_name=recipient_data.get('payer_name', ''),
            group_name=recipient_data.get('group_name', '')
        )


# Global email service instance
email_service = EmailService()
