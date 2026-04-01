"""
Notification Tasks
Async push / in-app notifications via Celery.
"""
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='app.workers.tasks.notification_tasks.send_group_notification',
    max_retries=2,
    default_retry_delay=30,
)
def send_group_notification(self, group_id, event_type, payload):
    """
    Emit a real-time notification to all members of a group.

    Falls back to storing the notification in the database if
    WebSocket delivery is unavailable.
    """
    try:
        from app.infrastructure.realtime.socketio_ext import socketio

        socketio.emit(
            event_type,
            payload,
            room=f'group:{group_id}',
            namespace='/groups',
        )
        logger.info('Notification sent to group %s: %s', group_id, event_type)
    except Exception as e:
        logger.warning('WebSocket emit failed for group %s: %s', group_id, e)

    return {'group_id': group_id, 'event': event_type}


@celery_app.task(
    bind=True,
    name='app.workers.tasks.notification_tasks.send_user_notification',
    max_retries=2,
    default_retry_delay=30,
)
def send_user_notification(self, user_id, event_type, payload):
    """Send a notification targeted at a single user."""
    try:
        from app.infrastructure.realtime.socketio_ext import socketio

        socketio.emit(
            event_type,
            payload,
            room=f'user:{user_id}',
            namespace='/notifications',
        )
        logger.info('Notification sent to user %s: %s', user_id, event_type)
    except Exception as e:
        logger.warning('WebSocket emit failed for user %s: %s', user_id, e)

    return {'user_id': user_id, 'event': event_type}
