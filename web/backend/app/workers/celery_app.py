"""
Celery Application Factory
Configures the Celery worker with Redis as broker and result backend.
"""
import json
import logging
from datetime import datetime, timezone

from app.core.config import Config
from celery import Celery
from celery.signals import task_failure

logger = logging.getLogger(__name__)

celery_app = Celery(
    'tripraft',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=[
        'app.workers.tasks.email_tasks',
        'app.workers.tasks.cleanup_tasks',
        'app.workers.tasks.analytics_tasks',
        'app.workers.tasks.notification_tasks',
        'app.workers.tasks.ai_tasks',
        'app.workers.tasks.chat_tasks',
        'app.workers.tasks.crew_tasks',
    ]
)

celery_app.conf.update(
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timeouts
    task_soft_time_limit=120,
    task_time_limit=180,

    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker recycling
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=2,

    # Result expiry
    result_expires=3600,

    # Beat schedule (imported from schedules module)
    beat_schedule={},
)

# Apply the beat schedule after import to avoid circular deps
from app.workers.schedules import CELERY_BEAT_SCHEDULE  # noqa: E402

celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE


# ---------------------------------------------------------------------------
# Dead Letter Queue — permanently failed tasks
# ---------------------------------------------------------------------------
DLQ_KEY = 'celery:dead_letters'


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, args=None, kwargs=None,
                        exception=None, einfo=None, **kw):
    """
    Called when a task exhausts all retries or raises a non-retryable error.
    Pushes the failed task into a Redis dead-letter list for manual review.
    """
    dead_letter = {
        'task_id': task_id,
        'task_name': sender.name if sender else 'unknown',
        'args': args,
        'kwargs': kwargs,
        'exception': str(exception),
        'traceback': str(einfo) if einfo else None,
        'failed_at': datetime.now(timezone.utc).isoformat(),
    }

    try:
        from app.infrastructure.cache import redis_client
        if redis_client.available:
            redis_client.rpush(DLQ_KEY, json.dumps(dead_letter, default=str))
    except Exception as dlq_err:
        logger.error('Failed to push to DLQ: %s', dlq_err)

    logger.error(
        'Task permanently failed: %s (%s) — %s',
        task_id, dead_letter['task_name'], exception,
    )


logger.info('Celery app configured (broker=%s)', Config.CELERY_BROKER_URL)
logger.info('Celery app configured (broker=%s)', Config.CELERY_BROKER_URL)
logger.info('Celery app configured (broker=%s)', Config.CELERY_BROKER_URL)
logger.info('Celery app configured (broker=%s)', Config.CELERY_BROKER_URL)
