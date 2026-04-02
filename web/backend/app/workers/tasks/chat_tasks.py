"""
Chat Background Tasks
Scheduled maintenance for group chat messages.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='app.workers.tasks.chat_tasks.archive_old_messages')
def archive_old_messages():
    """Move messages older than CHAT_MESSAGE_RETENTION_DAYS to archive.
    Scheduled via Celery Beat daily at 3 AM UTC.
    """
    from app.core.config import get_config
    from app.infrastructure.db.connection import get_db_session

    config = get_config()
    retention_days = getattr(config, 'CHAT_MESSAGE_RETENTION_DAYS', 180)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    try:
        with get_db_session() as session:
            from app.domain.group_planner.models import ChatMessage
            count = session.query(ChatMessage).filter(
                ChatMessage.created_at < cutoff,
            ).delete(synchronize_session='fetch')
            session.commit()
            logger.info('Archived %d chat messages older than %d days', count, retention_days)
            return {'archived': count}
    except Exception as exc:
        logger.error('archive_old_messages failed: %s', exc)
        return {'error': str(exc)}


@celery_app.task(name='app.workers.tasks.chat_tasks.process_ai_mention')
def process_ai_mention(group_id: str, sender_id: str, message_content: str):
    """Route AI mentions to the appropriate Celery task.
    Delegates to ai_tasks.process_scout_mention for @scout,
    and crew_tasks.process_crew_mention for @crew.
    """
    content_lower = message_content.lower()

    if '@crew' in content_lower:
        from app.workers.tasks.crew_tasks import process_crew_mention
        return process_crew_mention.delay(group_id, sender_id, message_content)

    # Default: @scout
    from app.workers.tasks.ai_tasks import process_scout_mention
    return process_scout_mention.delay(group_id, sender_id, message_content)
