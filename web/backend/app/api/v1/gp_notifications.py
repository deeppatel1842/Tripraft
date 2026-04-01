"""
Notification Routes for Group Planner
GET  /notifications            — list user's notifications (paginated)
POST /notifications/:id/read   — mark single as read
POST /notifications/read-all   — mark all as read
"""

import logging

from app.api.utils.responses import error_response, success_response
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

notifications_bp = Blueprint(
    'gp_notifications',
    __name__,
    url_prefix='/api/v1/group-planner'
)


@notifications_bp.route('/notifications', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
def get_notifications():
    """Get current user's notifications (paginated)."""
    try:
        from app.services.notification_service import notification_service

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        unread_only = request.args.get('unread_only', '').lower() in ('true', '1', 'yes')

        success, result = notification_service.get_notifications(
            user_id=g.user_id,
            page=page,
            per_page=per_page,
            unread_only=unread_only
        )

        if success:
            return success_response(
                data=result.get('notifications', []),
                pagination=result.get('pagination'),
                message=f"unread_count:{result.get('unread_count', 0)}"
            )
        return error_response(result.get('error'))
    except Exception as e:
        logger.error("Get notifications error: %s", e)
        return error_response('Failed to get notifications', 500)


@notifications_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
def mark_notification_read(notification_id):
    """Mark a single notification as read. Validates ownership."""
    try:
        from app.services.notification_service import notification_service

        success, result = notification_service.mark_read(
            notification_id=notification_id,
            user_id=g.user_id  # service must verify notification belongs to this user
        )

        if success:
            return success_response(data=result.get('notification'))
        return error_response(result.get('error'))
    except Exception as e:
        logger.error("Mark notification read error: %s", e)
        return error_response('Failed to mark notification as read', 500)


@notifications_bp.route('/notifications/read-all', methods=['POST'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
def mark_all_notifications_read():
    """Mark all notifications as read for the current user."""
    try:
        from app.services.notification_service import notification_service

        success, result = notification_service.mark_all_read(user_id=g.user_id)

        if success:
            return success_response(data=result)
        return error_response(result.get('error'))
    except Exception as e:
        logger.error("Mark all notifications read error: %s", e)
        return error_response('Failed to mark notifications as read', 500)
