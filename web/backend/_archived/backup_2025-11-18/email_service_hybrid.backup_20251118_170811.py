"""
Hybrid Email Service - Multi-Provider Fallback System
Automatically switches between providers when limits are reached
Keeps costs at $0 for as long as possible!

Provider Priority:
1. Brevo (9,000/month FREE)
2. Resend (3,000/month FREE)  
3. SendGrid (100/day FREE)
4. Mailgun (5,000/month for 3 months)
5. Gmail SMTP (500/day - last resort)

Total FREE emails: ~15,000/month before any costs!
"""

import logging
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ProviderStats:
    """Track usage stats for each provider"""
    name: str
    emails_sent_today: int = 0
    emails_sent_month: int = 0
    last_reset_date: str = None
    daily_limit: int = 0
    monthly_limit: int = 0
    enabled: bool = True
    priority: int = 0


class HybridEmailService:
    """
    Multi-provider email service with automatic fallback
    
    Features:
    - Automatic provider switching when limits reached
    - Usage tracking and analytics
    - Cost optimization (uses free tiers first)
    - Retry logic with different providers
    - Detailed logging
    """
    
    def __init__(self):
        """Initialize all email providers"""
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        self.app_name = os.getenv('APP_NAME', 'TripRaft')
        
        # Provider configurations
        self.providers = self._init_providers()
        
        # Load usage stats
        self.stats_file = 'email_usage_stats.json'
        self.load_usage_stats()
        
        # logger.info(f"HybridEmailService initialized with {len(self.providers)} providers")
    
    def _init_providers(self) -> Dict[str, Dict]:
        """Initialize all available email providers"""
        providers = {}
        
        # 1. Brevo (Best free tier - 9,000/month)
        if os.getenv('BREVO_API_KEY'):
            providers['brevo'] = {
                'name': 'Brevo',
                'priority': 1,
                'daily_limit': 300,
                'monthly_limit': 9000,
                'cost': 0,
                'api_key': os.getenv('BREVO_API_KEY'),
                'enabled': True
            }
        
        # 2. Resend (Modern - 3,000/month)
        if os.getenv('RESEND_API_KEY'):
            providers['resend'] = {
                'name': 'Resend',
                'priority': 2,
                'daily_limit': 100,
                'monthly_limit': 3000,
                'cost': 0,
                'api_key': os.getenv('RESEND_API_KEY'),
                'enabled': True
            }
        
        # 3. SendGrid (Industry standard - 100/day)
        if os.getenv('SENDGRID_API_KEY'):
            providers['sendgrid'] = {
                'name': 'SendGrid',
                'priority': 3,
                'daily_limit': 100,
                'monthly_limit': 3000,
                'cost': 0,
                'api_key': os.getenv('SENDGRID_API_KEY'),
                'enabled': True
            }
        
        # 4. Mailgun (Good trial - 5,000/month for 3 months)
        if os.getenv('MAILGUN_API_KEY') and os.getenv('MAILGUN_DOMAIN'):
            providers['mailgun'] = {
                'name': 'Mailgun',
                'priority': 4,
                'daily_limit': 166,
                'monthly_limit': 5000,
                'cost': 0,
                'api_key': os.getenv('MAILGUN_API_KEY'),
                'domain': os.getenv('MAILGUN_DOMAIN'),
                'enabled': True
            }
        
        # 5. Gmail SMTP (Fallback - 500/day)
        if os.getenv('SMTP_USER') and os.getenv('SMTP_PASSWORD'):
            providers['gmail'] = {
                'name': 'Gmail',
                'priority': 5,
                'daily_limit': 500,
                'monthly_limit': 15000,
                'cost': 0,
                'smtp_user': os.getenv('SMTP_USER'),
                'smtp_password': os.getenv('SMTP_PASSWORD'),
                'enabled': True
            }
        
        return providers
    
    def load_usage_stats(self):
        """Load usage statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    self.usage_stats = json.load(f)
            else:
                self.usage_stats = self._create_empty_stats()
        except Exception as e:
            logger.error(f"Failed to load usage stats: {e}")
            self.usage_stats = self._create_empty_stats()
        
        # Reset counters if new day/month
        self._check_reset_counters()
    
    def _create_empty_stats(self) -> Dict:
        """Create empty usage statistics"""
        stats = {}
        for provider_id, config in self.providers.items():
            stats[provider_id] = {
                'name': config['name'],
                'emails_sent_today': 0,
                'emails_sent_month': 0,
                'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
                'daily_limit': config['daily_limit'],
                'monthly_limit': config['monthly_limit'],
                'priority': config['priority'],
                'total_sent': 0,
                'total_failed': 0
            }
        return stats
    
    def _check_reset_counters(self):
        """Reset daily/monthly counters if needed"""
        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')
        
        for provider_id, stats in self.usage_stats.items():
            last_reset = stats.get('last_reset_date', '')
            
            # Reset daily counter
            if last_reset != today:
                stats['emails_sent_today'] = 0
            
            # Reset monthly counter
            if not last_reset.startswith(current_month):
                stats['emails_sent_month'] = 0
            
            stats['last_reset_date'] = today
        
        self.save_usage_stats()
    
    def save_usage_stats(self):
        """Save usage statistics to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.usage_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage stats: {e}")
    
    def get_available_provider(self) -> Optional[str]:
        """
        Get next available provider based on limits and priority
        
        Returns:
            Provider ID or None if all exhausted
        """
        # Sort providers by priority
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: x[1]['priority']
        )
        
        for provider_id, config in sorted_providers:
            if not config['enabled']:
                continue
            
            stats = self.usage_stats.get(provider_id, {})
            
            # Check daily limit
            if stats.get('emails_sent_today', 0) >= config['daily_limit']:
                logger.warning(f"{config['name']} daily limit reached ({config['daily_limit']})")
                continue
            
            # Check monthly limit
            if stats.get('emails_sent_month', 0) >= config['monthly_limit']:
                logger.warning(f"{config['name']} monthly limit reached ({config['monthly_limit']})")
                continue
            
            # logger.info(f"Selected provider: {config['name']} (Priority {config['priority']})")
            return provider_id
        
        logger.error("All email providers exhausted!")
        return None
    
    def send_email(self, to_email: str, subject: str, html_content: str,
                   text_content: Optional[str] = None, retry: bool = True) -> bool:
        """
        Send email using best available provider
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (optional)
            retry: Whether to retry with different provider on failure
            
        Returns:
            Success status
        """
        max_retries = len(self.providers) if retry else 1
        
        for attempt in range(max_retries):
            provider_id = self.get_available_provider()
            
            if not provider_id:
                logger.error("No available email providers")
                return False
            
            # Try sending with selected provider
            success = self._send_with_provider(
                provider_id, to_email, subject, html_content, text_content
            )
            
            if success:
                # Update stats
                self._update_stats(provider_id, success=True)
                return True
            else:
                # Update stats and try next provider
                self._update_stats(provider_id, success=False)
                logger.warning(f"Failed with {provider_id}, trying next provider...")
                continue
        
        logger.error(f"Failed to send email after {max_retries} attempts")
        return False
    
    def _send_with_provider(self, provider_id: str, to_email: str, 
                          subject: str, html_content: str,
                          text_content: Optional[str] = None) -> bool:
        """Send email with specific provider"""
        try:
            if provider_id == 'brevo':
                return self._send_brevo(to_email, subject, html_content, text_content)
            elif provider_id == 'resend':
                return self._send_resend(to_email, subject, html_content, text_content)
            elif provider_id == 'sendgrid':
                return self._send_sendgrid(to_email, subject, html_content, text_content)
            elif provider_id == 'mailgun':
                return self._send_mailgun(to_email, subject, html_content, text_content)
            elif provider_id == 'gmail':
                return self._send_gmail(to_email, subject, html_content, text_content)
            else:
                logger.error(f"Unknown provider: {provider_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending with {provider_id}: {e}")
            return False
    
    def _send_brevo(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """Send via Brevo (Sendinblue)"""
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
            
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = self.providers['brevo']['api_key']
            
            api = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            
            email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email}],
                sender={"email": "noreply@tripraft.com", "name": self.app_name},
                subject=subject,
                html_content=html,
                text_content=text
            )
            
            api.send_transac_email(email)
            # logger.info(f"Email sent via Brevo to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Brevo send failed: {e}")
            return False
    
    def _send_resend(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """Send via Resend"""
        try:
            import resend
            
            resend.api_key = self.providers['resend']['api_key']
            
            resend.Emails.send({
                "from": f"{self.app_name} <noreply@tripraft.com>",
                "to": to_email,
                "subject": subject,
                "html": html,
                "text": text
            })
            
            # logger.info(f"Email sent via Resend to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Resend send failed: {e}")
            return False
    
    def _send_sendgrid(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """Send via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=f"noreply@tripraft.com",
                to_emails=to_email,
                subject=subject,
                html_content=html,
                plain_text_content=text
            )
            
            sg = SendGridAPIClient(self.providers['sendgrid']['api_key'])
            sg.send(message)
            
            # logger.info(f"Email sent via SendGrid to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False
    
    def _send_mailgun(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """Send via Mailgun"""
        try:
            import requests
            
            domain = self.providers['mailgun']['domain']
            api_key = self.providers['mailgun']['api_key']
            
            response = requests.post(
                f"https://api.mailgun.net/v3/{domain}/messages",
                auth=("api", api_key),
                data={
                    "from": f"{self.app_name} <noreply@{domain}>",
                    "to": to_email,
                    "subject": subject,
                    "html": html,
                    "text": text
                }
            )
            
            response.raise_for_status()
            # logger.info(f"Email sent via Mailgun to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Mailgun send failed: {e}")
            return False
    
    def _send_gmail(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """Send via Gmail SMTP (fallback)"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.providers['gmail']['smtp_user']
            msg['To'] = to_email
            
            if text:
                msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(
                    self.providers['gmail']['smtp_user'],
                    self.providers['gmail']['smtp_password']
                )
                server.send_message(msg)
            
            # logger.info(f"Email sent via Gmail to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return False
    
    def _update_stats(self, provider_id: str, success: bool):
        """Update usage statistics"""
        if provider_id not in self.usage_stats:
            return
        
        stats = self.usage_stats[provider_id]
        
        if success:
            stats['emails_sent_today'] = stats.get('emails_sent_today', 0) + 1
            stats['emails_sent_month'] = stats.get('emails_sent_month', 0) + 1
            stats['total_sent'] = stats.get('total_sent', 0) + 1
        else:
            stats['total_failed'] = stats.get('total_failed', 0) + 1
        
        self.save_usage_stats()
    
    def get_usage_report(self) -> Dict:
        """
        Get detailed usage report
        
        Returns:
            Usage statistics for all providers
        """
        report = {
            'total_providers': len(self.providers),
            'enabled_providers': sum(1 for p in self.providers.values() if p['enabled']),
            'providers': []
        }
        
        for provider_id, stats in self.usage_stats.items():
            config = self.providers.get(provider_id, {})
            
            daily_remaining = config.get('daily_limit', 0) - stats.get('emails_sent_today', 0)
            monthly_remaining = config.get('monthly_limit', 0) - stats.get('emails_sent_month', 0)
            
            report['providers'].append({
                'name': stats['name'],
                'priority': stats['priority'],
                'today': {
                    'sent': stats.get('emails_sent_today', 0),
                    'limit': config.get('daily_limit', 0),
                    'remaining': max(0, daily_remaining),
                    'percentage': round(stats.get('emails_sent_today', 0) / config.get('daily_limit', 1) * 100, 1)
                },
                'month': {
                    'sent': stats.get('emails_sent_month', 0),
                    'limit': config.get('monthly_limit', 0),
                    'remaining': max(0, monthly_remaining),
                    'percentage': round(stats.get('emails_sent_month', 0) / config.get('monthly_limit', 1) * 100, 1)
                },
                'total_sent': stats.get('total_sent', 0),
                'total_failed': stats.get('total_failed', 0),
                'success_rate': round(
                    stats.get('total_sent', 0) / max(1, stats.get('total_sent', 0) + stats.get('total_failed', 0)) * 100,
                    1
                )
            })
        
        return report
    
    def send_group_invitation(self, to_email: str, inviter_name: str,
                            group_name: str, invitation_id: str) -> bool:
        """Send group invitation email"""
        subject = f"{inviter_name} invited you to join '{group_name}' on {self.app_name}"
        
        invitation_link = f"{self.frontend_url}/login?redirect=invitation&invitationId={invitation_id}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #007bff; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>You've been invited!</h2>
                    <p><strong>{inviter_name}</strong> invited you to join the group <strong>"{group_name}"</strong>.</p>
                    <p>Click the button below to accept the invitation:</p>
                    <a href="{invitation_link}" class="button">Accept Invitation</a>
                    <p>Or copy this link: {invitation_link}</p>
                </div>
                <div class="footer">
                    <p>This email was sent by {self.app_name}. If you didn't expect this, please ignore it.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {self.app_name}
        
        You've been invited!
        
        {inviter_name} invited you to join the group "{group_name}".
        
        Accept invitation: {invitation_link}
        
        ---
        This email was sent by {self.app_name}.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
_email_service = None

def get_email_service() -> HybridEmailService:
    """Get singleton email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = HybridEmailService()
    return _email_service
