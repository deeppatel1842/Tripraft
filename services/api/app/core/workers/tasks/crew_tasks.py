# Purpose: Crew Background Tasks — Celery tasks for @crew agent processing. Tasks:.
"""
Crew Background Tasks — Celery tasks for @crew agent processing.

Tasks:
  - process_crew_mention: Handle @crew mentions asynchronously
"""
import logging

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Response type constants (must be at module level for _map_response_to_message)
_RESPONSE_QUESTION_CARD = 'question_card'
_RESPONSE_CONFIRMATION_CARD = 'confirmation_card'
_RESPONSE_PLACE_CARD = 'place_card'
_RESPONSE_ERROR_TEXT = 'error_text'


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.crew_tasks.process_crew_mention',
    max_retries=1,
    soft_time_limit=30,
    default_retry_delay=5,
)
def process_crew_mention(self, group_id: str, sender_id: str, message_content: str):
    """
    Process a @crew mention detected in group chat.

    Called asynchronously from chat_tasks.process_ai_mention when @crew
    is detected. Posts the response as an AI-type message back to the group.
    """
    from app.core.config import Config
    from app.core.cache.redis import redis_client
    from app.core.db.connection import get_db
    from app.trips.services.chat_service import ChatService
    from app.scout.services.crew_agent_service import CrewAgentService

    if not Config.FF_CREW_AGENT:
        logger.info('Crew agent disabled, skipping mention in group=%s', group_id)
        return {'status': 'disabled'}

    redis = redis_client if redis_client.available else None

    # Rate limit check
    if redis and not _check_rate_limit(redis, group_id, sender_id):
        ChatService.send_message(
            group_id=group_id,
            sender_id=None,
            sender_type='ai',
            content="You're sending commands too fast. Try again in a minute.",
            msg_type='text',
            metadata_json={
                'agent': 'crew',
                'intent': 'rate_limited',
                'target_user_id': sender_id,
            },
        )
        return {'status': 'rate_limited'}

    try:
        with get_db() as session:
            success, result = CrewAgentService.process(
                session=session,
                group_id=group_id,
                sender_id=sender_id,
                message_content=message_content,
                redis_client=redis,
            )

            response_type = result.get('response_type', '')
            content = result.get('content', '')
            metadata = result.get('metadata', {})

            # Map response_type to chat message type and metadata
            msg_type, msg_metadata = _map_response_to_message(
                response_type, content, metadata, sender_id,
            )

            ChatService.send_message(
                group_id=group_id,
                sender_id=None,
                sender_type='ai',
                content=content,
                msg_type=msg_type,
                metadata_json=msg_metadata,
            )

            session.commit()
            return {
                'status': 'processed',
                'response_type': response_type,
                'intent': metadata.get('intent', 'unknown'),
            }

    except Exception as exc:
        logger.error('process_crew_mention failed: group=%s error=%s', group_id, exc)
        raise self.retry(exc=exc)
    finally:
        try:
            from app.trips.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {'user_id': 'crew'})
        except Exception:
            logger.debug('Could not clear Crew typing indicator', exc_info=True)


def _map_response_to_message(
    response_type: str,
    content: str,
    metadata: dict,
    sender_id: str,
) -> tuple:
    """
    Map CrewAgentService response_type to chat message type + metadata.

    Private cards (question_card, confirmation_card, error_text) include
    target_user_id so the frontend filters them to the triggering user only.
    """
    base_meta = {'agent': 'crew'}
    base_meta.update(metadata)

    if response_type == _RESPONSE_QUESTION_CARD:
        base_meta['target_user_id'] = sender_id
        return 'crew_question', base_meta

    if response_type == _RESPONSE_CONFIRMATION_CARD:
        base_meta['target_user_id'] = sender_id
        return 'crew_confirm', base_meta

    if response_type == _RESPONSE_PLACE_CARD:
        return 'crew_place', base_meta

    if response_type == _RESPONSE_ERROR_TEXT:
        base_meta['target_user_id'] = sender_id
        return 'crew_error', base_meta

    # RESPONSE_SUCCESS_TEXT — public to whole group
    return 'text', base_meta


def _check_rate_limit(redis_client, group_id: str, sender_id: str) -> bool:
    """
    Redis-based rate limiting for @crew commands.

    Per-user: CREW_RATE_USER_PER_MIN per minute
    Per-group: CREW_RATE_GROUP_PER_DAY per day
    """
    from app.core.config import Config

    user_key = f'crew:rate:user:{group_id}:{sender_id}'
    group_key = f'crew:rate:group:{group_id}'

    try:
        pipe = redis_client._client.pipeline(transaction=False)

        # Increment user counter (1 min window)
        pipe.incr(user_key)
        pipe.expire(user_key, 60)

        # Increment group counter (24h window)
        pipe.incr(group_key)
        pipe.expire(group_key, 86400)

        results = pipe.execute()
        user_count = results[0]
        group_count = results[2]

        if user_count > Config.CREW_RATE_USER_PER_MIN:
            logger.info(
                'Crew rate limit hit: user=%s group=%s count=%d',
                sender_id, group_id, user_count,
            )
            return False

        if group_count > Config.CREW_RATE_GROUP_PER_DAY:
            logger.info(
                'Crew rate limit hit: group=%s day_count=%d',
                group_id, group_count,
            )
            return False

        return True

    except Exception as exc:
        logger.warning('Crew rate limit check failed, allowing: %s', exc)
        return True
