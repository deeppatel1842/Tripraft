# Purpose: Email Tasks Async email delivery via Celery.  Retries with exponential backoff.
"""
Email Tasks
Async email delivery via Celery.  Retries with exponential backoff.
"""
import logging

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.email_tasks.send_invitation_email',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_invitation_email(self, to_email, inviter_name, group_name, invitation_id):
    """Send a group invitation email asynchronously."""
    from app.notifications.services.email_service import email_service

    success = email_service.send_group_invitation(
        to_email=to_email,
        inviter_name=inviter_name,
        group_name=group_name,
        invitation_id=str(invitation_id),
    )
    if not success:
        raise self.retry(exc=Exception('Email delivery failed'))
    logger.info('Invitation email sent to %s for group %s', to_email, group_name)
    return {'sent_to': to_email, 'type': 'invitation'}


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.email_tasks.send_verification_email',
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_verification_email(self, to_email, display_name, verification_token):
    """Send email verification link."""
    from app.notifications.services.email_service import email_service

    success = email_service.send_email(
        to_email=to_email,
        subject='Verify your TripRaft email',
        html_body=(
            f'<p>Hi {display_name},</p>'
            f'<p>Please verify your email by clicking '
            f'<a href="{verification_token}">here</a>.</p>'
        ),
    )
    if not success:
        raise self.retry(exc=Exception('Email delivery failed'))
    return {'sent_to': to_email, 'type': 'verification'}


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.email_tasks.send_password_reset_email',
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_password_reset_email(self, to_email, reset_link):
    """Send password reset link."""
    from app.notifications.services.email_service import email_service

    success = email_service.send_email(
        to_email=to_email,
        subject='Reset your TripRaft password',
        html_body=(
            f'<p>You requested a password reset.</p>'
            f'<p>Click <a href="{reset_link}">here</a> to reset your password.</p>'
            f'<p>This link expires in 1 hour.</p>'
        ),
    )
    if not success:
        raise self.retry(exc=Exception('Email delivery failed'))
    return {'sent_to': to_email, 'type': 'password_reset'}


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.email_tasks.send_expense_notification',
    max_retries=2,
    default_retry_delay=60,
)
def send_expense_notification(self, to_email, group_name, expense_desc, amount, paid_by_name):
    """Notify group members about a new expense."""
    from app.notifications.services.email_service import email_service

    success = email_service.send_email(
        to_email=to_email,
        subject=f'New expense in {group_name}',
        html_body=(
            f'<p>{paid_by_name} added <strong>{expense_desc}</strong> '
            f'(${amount}) to {group_name}.</p>'
        ),
    )
    if not success:
        raise self.retry(exc=Exception('Email delivery failed'))
    return {'sent_to': to_email, 'type': 'expense_notification'}
