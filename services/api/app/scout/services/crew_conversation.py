# Purpose: Crew Conversation State Manager — Redis-backed multi-turn Q&A state. Each user in a group gets an isolated conversation slot with TTL.
"""
Crew Conversation State Manager — Redis-backed multi-turn Q&A state.

Each user in a group gets an isolated conversation slot with TTL.
State tracks: intent, collected fields, missing fields, retry count.
Automatically expires after CREW_CONV_TTL seconds of inactivity.
"""
import json
import logging
from typing import Any, Dict, Optional

from app.core.config import Config

logger = logging.getLogger(__name__)


class CrewConversation:
    """
    Manages per-user, per-group conversation state in Redis.

    Redis key format: crew:conv:{group_id}:{user_id}
    Value: JSON-serialized dict with TTL = Config.CREW_CONV_TTL.
    """

    _KEY_PREFIX = 'crew:conv'

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def _key(self, group_id: str, user_id: str) -> str:
        return f'{self._KEY_PREFIX}:{group_id}:{user_id}'

    def get(self, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current conversation state, or None if expired/absent."""
        if not self._redis or not self._redis.available:
            return None
        raw = self._redis.get(self._key(group_id, user_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                'Corrupt crew conversation state: group=%s user=%s', group_id, user_id,
            )
            self.clear(group_id, user_id)
            return None

    def set(self, group_id: str, user_id: str, state: Dict[str, Any]) -> bool:
        """
        Persist conversation state with TTL refresh.

        State shape:
            {
                "intent": str,
                "collected_fields": dict,
                "missing_fields": list[str],
                "retry_count": int,
            }
        """
        if not self._redis or not self._redis.available:
            return False
        try:
            serialized = json.dumps(state, default=str)
            return self._redis.set(
                self._key(group_id, user_id),
                serialized,
                ex=Config.CREW_CONV_TTL,
            )
        except (TypeError, ValueError) as exc:
            logger.error('Failed to serialize crew state: %s', exc)
            return False

    def clear(self, group_id: str, user_id: str) -> bool:
        """Explicitly remove conversation state (e.g. after completion or cancel)."""
        if not self._redis or not self._redis.available:
            return False
        return self._redis.delete(self._key(group_id, user_id)) > 0
