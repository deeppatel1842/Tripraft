# Purpose: Cleanup Tasks Scheduled maintenance: session expiry, soft-delete archival.
"""
Cleanup Tasks
Scheduled maintenance: session expiry, soft-delete archival.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='app.core.workers.tasks.cleanup_tasks.cleanup_expired_sessions')
def cleanup_expired_sessions():
    """Remove expired refresh tokens and inactive sessions."""
    from app.core.db.connection import get_db

    with get_db() as session:
        from app.auth.models import UserSession
        from sqlalchemy import text

        now = datetime.now(timezone.utc)
        deleted = session.query(UserSession).filter(
            UserSession.expires_at < now
        ).delete(synchronize_session='fetch')
        session.commit()
        logger.info('Cleaned up %d expired sessions', deleted)
        return {'deleted_sessions': deleted}


@celery_app.task(name='app.core.workers.tasks.cleanup_tasks.archive_soft_deleted_records')
def archive_soft_deleted_records():
    """Permanently remove records soft-deleted more than 90 days ago."""
    from app.expenses.models import Expense, Settlement
    from app.core.db.connection import get_db

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    with get_db() as session:
        expenses_deleted = session.query(Expense).filter(
            Expense.is_deleted == True,
            Expense.updated_at < cutoff
        ).delete(synchronize_session='fetch')

        settlements_deleted = session.query(Settlement).filter(
            Settlement.is_deleted == True,
            # A settlement can be old but newly deleted. Retention begins at
            # deletion time, not at the time it was recorded.
            Settlement.deleted_at < cutoff
        ).delete(synchronize_session='fetch')

        session.commit()
        logger.info(
            'Archived soft-deleted records: %d expenses, %d settlements',
            expenses_deleted, settlements_deleted,
        )
        return {
            'archived_expenses': expenses_deleted,
            'archived_settlements': settlements_deleted,
        }
