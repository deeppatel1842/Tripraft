# Purpose: Email Infrastructure Package Provides SMTP-based email sending for notifications.
"""
Email Infrastructure Package

Provides SMTP-based email sending for notifications.
"""
from .smtp import EmailService, email_service

__all__ = [
    'EmailService',
    'email_service',
]
