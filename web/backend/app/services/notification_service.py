"""
Notification Service for Group Planner
Handles creating, querying, and managing in-app notifications.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.group_planner.models import Notification, TripMember
from app.infrastructure.db.connection import get_db_session
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def notify_group_members(
        group_id: str,
        exclude_user_id: str,
        type: str,
        title: str,
        body: Optional[str] = None,
        data: Optional[dict] = None
    ) -> None:
        """Send a notification to all active members of a group except the actor."""
        try:
            with get_db_session() as session:
                members = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.is_active == True,
                    TripMember.user_id != exclude_user_id
                ).all()

                for m in members:
                    session.add(Notification(
                        user_id=m.user_id,
                        group_id=group_id,
                        type=type,
                        title=title,
                        body=body,
                        data=data,
                    ))
                session.commit()
        except Exception as e:
            logger.error(f"notify_group_members error: {e}")

    @staticmethod
    def notify_user(
        user_id: str,
        type: str,
        title: str,
        body: Optional[str] = None,
        group_id: Optional[int] = None,
        data: Optional[dict] = None
    ) -> None:
        """Send a notification to a single user."""
        try:
            with get_db_session() as session:
                session.add(Notification(
                    user_id=user_id,
                    group_id=group_id,
                    type=type,
                    title=title,
                    body=body,
                    data=data,
                ))
                session.commit()
        except Exception as e:
            logger.error(f"notify_user error: {e}")

    @staticmethod
    def get_notifications(
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get paginated notifications for a user."""
        try:
            with get_db_session() as session:
                base_query = session.query(Notification).filter(
                    Notification.user_id == user_id
                )
                if unread_only:
                    base_query = base_query.filter(Notification.is_read == False)

                total = base_query.count()
                items = base_query.order_by(
                    Notification.created_at.desc()
                ).offset((page - 1) * per_page).limit(per_page).all()

                unread_count = session.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ).count()

                return True, {
                    'notifications': [n.to_dict() for n in items],
                    'unread_count': unread_count,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': max(1, -(-total // per_page))
                    }
                }
        except Exception as e:
            logger.error(f"get_notifications error: {e}")
            return False, {'error': 'Failed to get notifications'}

    @staticmethod
    def mark_read(notification_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Mark a single notification as read."""
        try:
            with get_db_session() as session:
                notif = session.query(Notification).filter(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                ).first()
                if not notif:
                    return False, {'error': 'Notification not found'}
                notif.is_read = True
                session.commit()
                return True, {'notification': notif.to_dict()}
        except Exception as e:
            logger.error(f"mark_read error: {e}")
            return False, {'error': 'Failed to mark notification as read'}

    @staticmethod
    def mark_all_read(user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Mark all notifications as read for a user."""
        try:
            with get_db_session() as session:
                count = session.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ).update({'is_read': True})
                session.commit()
                return True, {'marked': count}
        except Exception as e:
            logger.error(f"mark_all_read error: {e}")
            return False, {'error': 'Failed to mark notifications as read'}


notification_service = NotificationService()
