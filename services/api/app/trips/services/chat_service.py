# Purpose: Chat Service — Core group messaging logic. Handles message CRUD, read receipts, unread counts.
"""
Chat Service — Core group messaging logic.

Handles message CRUD, read receipts, unread counts.
No AI logic here (deferred to Phase 5).
"""
import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import bleach
from app.trips.models import (ChatMessage, ChatSummary,
                                             MessageRead)
from app.core.db.connection import get_db_session
from sqlalchemy import func

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
        parent_message_id: Optional[UUID] = None,
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
                    from app.trips.realtime.events import \
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
        before_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> Tuple[bool, List[Dict]]:
        try:
            limit = min(max(limit, 1), 100)
            with get_db_session() as session:
                q = session.query(ChatMessage).filter(
                    ChatMessage.group_id == group_id,
                    ChatMessage.is_deleted.is_(False),
                    ChatMessage.is_archived.is_(False),
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
            from app.trips.models import TripMember

            with get_db_session() as session:
                msg = session.get(ChatMessage, message_id)
                if not msg:
                    return False, {'error': 'Message not found'}
                membership = session.query(TripMember).filter(
                    TripMember.group_id == msg.group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if membership is None:
                    return False, {'error': 'Not a member of this group'}
                can_delete_others = (
                    is_admin and membership.role in {'admin', 'creator'}
                )
                if msg.sender_id != user_id and not can_delete_others:
                    return False, {'error': 'Not authorized to delete this message'}
                msg.is_deleted = True
                group_id = msg.group_id
                session.commit()

                try:
                    from app.trips.realtime.events import \
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
    def mark_read(group_id: str, user_id: str, message_id: UUID) -> Tuple[bool, Dict]:
        try:
            with get_db_session() as session:
                try:
                    message_id = UUID(str(message_id))
                except (AttributeError, TypeError, ValueError):
                    return False, {'error': 'last_read_message_id must be a UUID'}

                # A receipt must refer to a real message in this group. This
                # also avoids comparing UUIDs as if they were legacy integer
                # cursors and prevents cross-group read markers.
                target = session.query(ChatMessage).filter(
                    ChatMessage.id == message_id,
                    ChatMessage.group_id == group_id,
                    ChatMessage.is_deleted.is_(False),
                    ChatMessage.is_archived.is_(False),
                ).first()
                if target is None:
                    return False, {'error': 'Message not found in this group'}

                existing = session.query(MessageRead).filter_by(
                    group_id=group_id, user_id=user_id,
                ).first()
                if existing:
                    # Use the same UUID ordering as pagination and unread
                    # counts. Delayed receipts must never move the cursor
                    # backward, including messages with equal timestamps.
                    session.query(MessageRead).filter(
                        MessageRead.group_id == group_id,
                        MessageRead.user_id == user_id,
                        MessageRead.last_read_message_id < message_id,
                    ).update(
                        {'last_read_message_id': message_id},
                        synchronize_session=False,
                    )
                    session.refresh(existing)
                    message_id = existing.last_read_message_id
                else:
                    session.add(MessageRead(
                        group_id=group_id,
                        user_id=user_id,
                        last_read_message_id=message_id,
                    ))
                session.commit()

                try:
                    from app.trips.realtime.events import \
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
            # Count the current ledger directly. A cached count becomes
            # stale after sends, reads, deletion or archival, and a reader
            # can repopulate it with stale data during invalidation.
            with get_db_session() as session:
                read_row = session.query(MessageRead).filter_by(
                    group_id=group_id, user_id=user_id,
                ).first()
                unread = session.query(func.count(ChatMessage.id)).filter(
                    ChatMessage.group_id == group_id,
                    ChatMessage.is_deleted.is_(False),
                    ChatMessage.is_archived.is_(False),
                )
                # UUID primary keys cannot be compared with integer zero.
                # With no receipt every non-deleted message is unread.
                if read_row is not None:
                    unread = unread.filter(
                        ChatMessage.id > read_row.last_read_message_id,
                    )
                count = unread.scalar() or 0
            return count
        except Exception as exc:
            logger.error("get_unread_count failed: %s", exc)
            return 0
