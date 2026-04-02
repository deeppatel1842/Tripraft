"""
Chat Service — Core group messaging logic.

Handles message CRUD, read receipts, unread counts.
No AI logic here (deferred to Phase 5).
"""
import logging
from typing import Dict, List, Optional, Tuple

import bleach
from app.domain.group_planner.models import (ChatMessage, ChatSummary,
                                             MessageRead)
from app.infrastructure.db.connection import get_db_session
from sqlalchemy import and_, func

logger = logging.getLogger(__name__)


class ChatService:

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------
    @staticmethod
    def send_message(
        group_id: str,
        sender_id: str,
        content: str,
        msg_type: str = 'text',
        metadata_json: Optional[dict] = None,
        parent_message_id: Optional[int] = None,
        sender_type: str = 'user',
    ) -> Tuple[bool, Dict]:
        try:
            sanitized = bleach.clean(content, tags=[], strip=True).strip()
            if not sanitized:
                return False, {'error': 'Message content is empty'}

            with get_db_session() as session:
                msg = ChatMessage(
                    group_id=group_id,
                    sender_id=sender_id,
                    sender_type=sender_type,
                    type=msg_type,
                    content=sanitized,
                    metadata_json=metadata_json or {},
                    parent_message_id=parent_message_id,
                )
                session.add(msg)
                session.flush()
                result = msg.to_dict()
                session.commit()

                # Broadcast via WebSocket (best-effort)
                try:
                    from app.infrastructure.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'chat:message', result)
                except Exception:
                    pass

                return True, result
        except Exception as exc:
            logger.error("send_message failed: %s", exc)
            return False, {'error': 'Failed to send message'}

    # ------------------------------------------------------------------
    # List (cursor pagination)
    # ------------------------------------------------------------------
    @staticmethod
    def get_messages(
        group_id: str,
        before_id: Optional[int] = None,
        limit: int = 50,
    ) -> Tuple[bool, List[Dict]]:
        try:
            limit = min(max(limit, 1), 100)
            with get_db_session() as session:
                q = session.query(ChatMessage).filter(
                    ChatMessage.group_id == group_id,
                    ChatMessage.is_deleted == False,
                )
                if before_id:
                    q = q.filter(ChatMessage.id < before_id)
                messages = q.order_by(ChatMessage.id.desc()).limit(limit).all()
                return True, [m.to_dict() for m in messages]
        except Exception as exc:
            logger.error("get_messages failed: %s", exc)
            return False, []

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------
    @staticmethod
    def delete_message(
        message_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> Tuple[bool, Dict]:
        try:
            with get_db_session() as session:
                msg = session.query(ChatMessage).get(message_id)
                if not msg:
                    return False, {'error': 'Message not found'}
                if msg.sender_id != user_id and not is_admin:
                    return False, {'error': 'Not authorized to delete this message'}
                msg.is_deleted = True
                group_id = msg.group_id
                session.commit()

                try:
                    from app.infrastructure.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'chat:deleted', {'message_id': message_id})
                except Exception:
                    pass

                return True, {'message_id': message_id}
        except Exception as exc:
            logger.error("delete_message failed: %s", exc)
            return False, {'error': 'Failed to delete message'}

    # ------------------------------------------------------------------
    # Read receipts
    # ------------------------------------------------------------------
    @staticmethod
    def mark_read(group_id: str, user_id: str, message_id: str) -> Tuple[bool, Dict]:
        try:
            with get_db_session() as session:
                existing = session.query(MessageRead).filter_by(
                    group_id=group_id, user_id=user_id,
                ).first()
                if existing:
                    if message_id > existing.last_read_message_id:
                        existing.last_read_message_id = message_id
                else:
                    session.add(MessageRead(
                        group_id=group_id,
                        user_id=user_id,
                        last_read_message_id=message_id,
                    ))
                session.commit()

                try:
                    from app.infrastructure.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'chat:read', {
                        'user_id': user_id,
                        'last_read_message_id': message_id,
                    })
                except Exception:
                    pass

                return True, {'last_read_message_id': message_id}
        except Exception as exc:
            logger.error("mark_read failed: %s", exc)
            return False, {'error': 'Failed to mark as read'}

    # ------------------------------------------------------------------
    # Unread count
    # ------------------------------------------------------------------
    @staticmethod
    def get_unread_count(group_id: str, user_id: str) -> int:
        try:
            # Check Redis cache first
            cache_key = f"chat:unread:{group_id}:{user_id}"
            try:
                from app.infrastructure.cache.redis import redis_client
                cached = redis_client.get(cache_key)
                if cached is not None:
                    return int(cached)
            except Exception:
                pass

            with get_db_session() as session:
                read_row = session.query(MessageRead).filter_by(
                    group_id=group_id, user_id=user_id,
                ).first()
                last_read = read_row.last_read_message_id if read_row else 0

                count = session.query(func.count(ChatMessage.id)).filter(
                    ChatMessage.group_id == group_id,
                    ChatMessage.id > last_read,
                    ChatMessage.is_deleted == False,
                ).scalar() or 0

            # Cache for 30 seconds
            try:
                from app.infrastructure.cache.redis import redis_client
                redis_client.set(cache_key, count, ex=30)
            except Exception:
                pass

            return count
        except Exception as exc:
            logger.error("get_unread_count failed: %s", exc)
            return 0
        except Exception as exc:
            logger.error("get_unread_count failed: %s", exc)
            return 0
        except Exception as exc:
            logger.error("get_unread_count failed: %s", exc)
            return 0
        except Exception as exc:
            logger.error("get_unread_count failed: %s", exc)
            return 0
