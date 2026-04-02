"""
Celery Beat Schedule
Periodic tasks for maintenance, cache warming, and analytics.
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Every 30 minutes: warm popular search cache
    'warmup-search-cache': {
        'task': 'app.workers.tasks.analytics_tasks.warmup_search_cache',
        'schedule': 1800.0,
    },

    # Daily 02:00 UTC: clean expired sessions and tokens
    'cleanup-sessions': {
        'task': 'app.workers.tasks.cleanup_tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=2, minute=0),
    },

    # Weekly Sunday 03:00 UTC: archive 90-day-old soft-deleted records
    'archive-deleted': {
        'task': 'app.workers.tasks.cleanup_tasks.archive_soft_deleted_records',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },

    # Daily 04:00 UTC: aggregate analytics metrics
    'aggregate-analytics': {
        'task': 'app.workers.tasks.analytics_tasks.aggregate_daily_metrics',
        'schedule': crontab(hour=4, minute=0),
    },

    # Daily 05:00 UTC: purge expired AI agent logs
    'cleanup-agent-logs': {
        'task': 'app.workers.tasks.ai_tasks.cleanup_agent_logs',
        'schedule': crontab(hour=5, minute=0),
    },
}
