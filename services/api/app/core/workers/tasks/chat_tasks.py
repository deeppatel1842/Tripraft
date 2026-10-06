# Purpose: Chat Background Tasks Scheduled maintenance for group chat messages.
"""
Chat Background Tasks
Scheduled maintenance for group chat messages.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.chat_tasks.archive_old_messages',
    max_retries=2,
    default_retry_delay=60,
)
def archive_old_messages(self):
    """Reversibly archive old chat messages instead of deleting them.

    The scheduled job only marks rows archived, preserving auditability and
    allowing a later restore workflow.  Normal chat reads and AI summaries
    exclude archived rows.
    """
    from app.core.config import get_config
    from app.core.db.connection import get_db_session

    config = get_config()
    retention_days = getattr(config, 'CHAT_MESSAGE_RETENTION_DAYS', 180)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    try:
        with get_db_session() as session:
            from app.trips.models import ChatMessage
            count = session.query(ChatMessage).filter(
                ChatMessage.created_at < cutoff,
                ChatMessage.is_deleted.is_(False),
                ChatMessage.is_archived.is_(False),
            ).update(
                {ChatMessage.is_archived: True},
                synchronize_session=False,
            )
            session.commit()
            logger.info('Archived %d chat messages older than %d days', count, retention_days)
            return {'archived': count}
    except Exception as exc:
        logger.error('archive_old_messages failed: %s', exc)
        raise self.retry(exc=exc)


@celery_app.task(name='app.core.workers.tasks.chat_tasks.process_ai_mention')
def process_ai_mention(group_id: str, sender_id: str, message_content: str):
    """Route AI mentions to the appropriate Celery task.
    Delegates to ai_tasks.process_scout_mention for @scout,
    and crew_tasks.process_crew_mention for @crew.
    """
    content_lower = message_content.lower()

    if '@crew' in content_lower:
        from app.core.workers.tasks.crew_tasks import process_crew_mention
        return process_crew_mention.delay(group_id, sender_id, message_content)

    # Default: @scout
    from app.core.workers.tasks.ai_tasks import process_scout_mention
    return process_scout_mention.delay(group_id, sender_id, message_content)
