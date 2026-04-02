"""
Chat Routes for Group Planner
REST API endpoints for group messaging.
"""
import logging

from app.api.utils.responses import (created_response, error_response,
                                     success_response,
                                     validation_error_response)
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth, require_group_role
from app.schemas.gp_chat import ReadReceiptSchema, SendMessageSchema
from app.services.chat_service import ChatService
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

chat_bp = Blueprint(
    'gp_chat',
    __name__,
    url_prefix='/api/v1/group-planner',
)

chat_service = ChatService()


def _maybe_trigger_summary(group_id: str):
    """Run chat summary extraction if enough new messages since last summary."""
    try:
        from app.core.config import Config
        if not Config.FF_SCOUT_AGENT:
            return

        from app.domain.ai.models import AIConsent
        from app.domain.group_planner.models import ChatMessage, ChatSummary
        from app.infrastructure.db.connection import get_db

        with get_db() as session:
            last_summary = session.query(ChatSummary).filter_by(
                group_id=group_id,
            ).order_by(ChatSummary.created_at.desc()).first()

            from_id = last_summary.to_message_id if last_summary else None

            query = session.query(ChatMessage.id).filter(
                ChatMessage.group_id == group_id,
                ChatMessage.is_deleted.is_(False),
                ChatMessage.sender_type == 'user',
            )
            if from_id:
                query = query.filter(ChatMessage.id > from_id)

            count = query.count()
            if count < Config.CHAT_SUMMARY_TRIGGER:
                return

            from app.workers.tasks.ai_tasks import generate_chat_summary
            generate_chat_summary.apply(args=[group_id])

    except Exception as exc:
        logger.debug('Summary trigger skipped: %s', exc)


def _maybe_trigger_scout(group_id: str, sender_id: str, content: str):
    """Process @scout mention synchronously and post the reply as an AI message."""
    from app.core.config import Config
    if not Config.FF_SCOUT_AGENT:
        return
    mention = Config.SCOUT_AGENT_MENTION
    if not mention or mention.lower() not in content.lower():
        return

    # Emit typing indicator so the frontend shows "Scout is thinking..."
    try:
        from app.infrastructure.realtime.events import emit_to_group
        emit_to_group(group_id, 'chat:typing', {
            'user_id': 'scout',
            'email': 'Scout',
            'is_ai': True,
        })
    except Exception:
        pass

    try:
        from app.infrastructure.cache.redis import redis_client
        from app.infrastructure.db.connection import get_db
        from app.services.scout_agent_service import ScoutAgentService

        scout = ScoutAgentService()
        redis = redis_client if redis_client.available else None

        with get_db() as session:
            success, result = scout.process(
                session=session,
                group_id=group_id,
                sender_id=sender_id,
                message_content=content,
                redis_client=redis,
            )

            if success and result.get('response'):
                response_type = result.get('response_type', 'text')
                msg_type = 'text'
                if response_type == 'place_suggestion':
                    msg_type = 'place_suggestion'
                elif response_type == 'consent_card':
                    msg_type = 'system'

                chat_service.send_message(
                    group_id=group_id,
                    sender_id=None,
                    sender_type='ai',
                    content=result['response'],
                    msg_type=msg_type,
                    metadata_json={
                        'agent': 'scout',
                        'intent': result.get('intent', 'unknown'),
                        'needs_consent': result.get('response_type') == 'consent_card',
                        'original_query': content if result.get('response_type') == 'consent_card' else None,
                    },
                )

            session.commit()

        # Clear typing indicator after response is sent
        try:
            from app.infrastructure.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {
                'user_id': 'scout',
            })
        except Exception:
            pass

    except Exception as exc:
        logger.warning('Scout processing failed: %s', exc)
        # Always send a fallback response so user is never left waiting
        try:
            chat_service.send_message(
                group_id=group_id,
                sender_id=None,
                sender_type='ai',
                content="Something went wrong on my end. Try again or rephrase your question.",
                msg_type='text',
                metadata_json={'agent': 'scout', 'intent': 'error'},
            )
        except Exception:
            pass
        # Clear typing on error too
        try:
            from app.infrastructure.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {
                'user_id': 'scout',
            })
        except Exception:
            pass


def _maybe_trigger_crew(group_id: str, sender_id: str, content: str):
    """Process @crew mention or multi-turn reply synchronously and post the reply."""
    from app.core.config import Config
    if not Config.FF_CREW_AGENT:
        return

    # Check for an active multi-turn conversation first (no @crew mention needed)
    has_active_conversation = False
    try:
        from app.infrastructure.cache.redis import redis_client
        from app.services.crew_conversation import CrewConversation
        redis = redis_client if redis_client.available else None
        if redis:
            conv = CrewConversation(redis)
            if conv.get(group_id, str(sender_id)):
                has_active_conversation = True
    except Exception:
        pass

    # If no active conversation, require explicit @crew mention
    if not has_active_conversation:
        mention = Config.CREW_AGENT_MENTION
        if not mention or mention.lower() not in content.lower():
            return

    # Emit typing indicator so the frontend shows "Crew is thinking..."
    try:
        from app.infrastructure.realtime.events import emit_to_group
        emit_to_group(group_id, 'chat:typing', {
            'user_id': 'crew',
            'email': 'Crew',
            'is_ai': True,
        })
    except Exception:
        pass

    try:
        from app.infrastructure.cache.redis import redis_client
        from app.infrastructure.db.connection import get_db
        from app.services.crew_agent_service import CrewAgentService

        redis = redis_client if redis_client.available else None

        with get_db() as session:
            success, result = CrewAgentService.process(
                session=session,
                group_id=group_id,
                sender_id=sender_id,
                message_content=content,
                redis_client=redis,
            )

            if result:
                response_type = result.get('response_type', '')
                content_text = result.get('content', '')
                metadata = result.get('metadata', {})

                msg_type, msg_metadata = _crew_map_response(
                    response_type, metadata, sender_id,
                )

                chat_service.send_message(
                    group_id=group_id,
                    sender_id=None,
                    sender_type='ai',
                    content=content_text,
                    msg_type=msg_type,
                    metadata_json=msg_metadata,
                )

            session.commit()

        # Clear typing indicator after response is sent
        try:
            from app.infrastructure.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {
                'user_id': 'crew',
            })
        except Exception:
            pass

    except Exception as exc:
        logger.warning('Crew processing failed: %s', exc)
        try:
            chat_service.send_message(
                group_id=group_id,
                sender_id=None,
                sender_type='ai',
                content="Something went wrong processing your request. Try again.",
                msg_type='text',
                metadata_json={'agent': 'crew', 'intent': 'error'},
            )
        except Exception:
            pass
        try:
            from app.infrastructure.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {
                'user_id': 'crew',
            })
        except Exception:
            pass


def _crew_map_response(response_type: str, metadata: dict, sender_id: str) -> tuple:
    """Map CrewAgentService response_type to chat msg_type + metadata."""
    base_meta = {'agent': 'crew'}
    base_meta.update(metadata)

    # sender_id may be a UUID object — always cast to str for JSON serialization
    safe_sender = str(sender_id) if sender_id is not None else None

    if response_type == 'question_card':
        base_meta['target_user_id'] = safe_sender
        return 'crew_question', base_meta

    if response_type == 'confirmation_card':
        base_meta['target_user_id'] = safe_sender
        return 'crew_confirm', base_meta

    if response_type == 'place_card':
        return 'crew_place', base_meta

    if response_type == 'poll_created':
        return 'crew_poll_created', base_meta

    if response_type == 'error_text':
        base_meta['target_user_id'] = safe_sender
        return 'crew_error', base_meta

    # success_text — public to whole group
    return 'text', base_meta


@chat_bp.route('/groups/<group_id>/messages', methods=['POST'])
@require_auth
@require_group_role('member')
@limit_api('create')
def send_message(group_id):
    """Send a message to a group chat."""
    schema = SendMessageSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return validation_error_response(errors)

    data = schema.load(request.json)
    success, result = chat_service.send_message(
        group_id=group_id,
        sender_id=g.user_id,
        content=data['content'],
        msg_type=data.get('type', 'text'),
        metadata_json=data.get('metadata_json'),
        parent_message_id=data.get('parent_message_id'),
    )

    if success:
        _maybe_trigger_scout(group_id, g.user_id, data['content'])
        _maybe_trigger_crew(group_id, g.user_id, data['content'])
        _maybe_trigger_summary(group_id)
        return created_response(result)
    return error_response(result.get('error', 'Failed to send message'))


@chat_bp.route('/groups/<group_id>/messages', methods=['GET'])
@require_auth
@require_group_role('viewer')
@limit_api('read_light')
def get_messages(group_id):
    """Get messages for a group with cursor pagination."""
    before_id = request.args.get('before_id', type=int)
    limit = request.args.get('limit', 50, type=int)

    success, messages = chat_service.get_messages(
        group_id=group_id,
        before_id=before_id,
        limit=limit,
    )

    if success:
        return success_response({
            'messages': messages,
            'has_more': len(messages) == min(max(limit, 1), 100),
        })
    return error_response('Failed to load messages')


@chat_bp.route('/messages/<message_id>', methods=['DELETE'])
@require_auth
@limit_api('delete')
def delete_message(message_id):
    """Soft-delete a message (owner or group admin)."""
    success, result = chat_service.delete_message(
        message_id=message_id,
        user_id=g.user_id,
    )

    if success:
        return success_response(result)
    status = 404 if result.get('error') == 'Message not found' else 403
    return error_response(result.get('error', 'Failed to delete'), status)


@chat_bp.route('/groups/<group_id>/messages/read', methods=['POST'])
@require_auth
@require_group_role('viewer')
@limit_api('read_light')
def mark_read(group_id):
    """Update read receipt for the current user."""
    schema = ReadReceiptSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return validation_error_response(errors)

    data = schema.load(request.json)
    success, result = chat_service.mark_read(
        group_id=group_id,
        user_id=g.user_id,
        message_id=data['last_read_message_id'],
    )

    if success:
        return success_response(result)
    return error_response(result.get('error', 'Failed to mark as read'))


@chat_bp.route('/groups/<group_id>/unread-count', methods=['GET'])
@require_auth
@require_group_role('viewer')
@limit_api('read_light')
def get_unread_count(group_id):
    """Get unread message count for the current user in a group."""
    count = chat_service.get_unread_count(group_id, g.user_id)
    return success_response({'unread_count': count})
