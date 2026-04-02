"""
AI Crew Confirm Routes — REST API for confirming @crew destructive actions.

Endpoints:
  POST /groups/<group_id>/ai/confirm  — Confirm or cancel a pending @crew action
"""
import json
import logging

from app.api.utils.responses import error_response, success_response
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth, require_group_role
from app.infrastructure.cache.redis import redis_client
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

ai_confirm_bp = Blueprint(
    'ai_confirm',
    __name__,
    url_prefix='/api/v1/group-planner',
)


@ai_confirm_bp.route('/groups/<group_id>/ai/confirm', methods=['POST'])
@require_auth
@require_group_role('member')
@limit_api('create')
def confirm_crew_action(group_id):
    """
    Confirm or cancel a pending @crew destructive action (e.g. delete).

    Body:
        action: "confirm" or "cancel"
    """
    body = request.json or {}
    action = body.get('action')

    if action not in ('confirm', 'cancel'):
        return error_response('Invalid action. Must be "confirm" or "cancel".', 400)

    pending_key = f'crew:confirm:{group_id}:{g.user_id}'

    if not redis_client.available:
        return error_response('Service temporarily unavailable.', 503)

    raw = redis_client.get(pending_key)
    if not raw:
        return error_response(
            'No pending action found. It may have expired (60s window).', 404,
        )

    try:
        pending = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        redis_client.delete(pending_key)
        return error_response('Corrupted pending state. Try again.', 400)

    entity_type = pending.get('entity_type')
    entity_id = pending.get('entity_id')
    entity_name = pending.get('entity_name', '')

    # Always clear the pending state
    redis_client.delete(pending_key)

    if action == 'cancel':
        return success_response({'message': 'Action cancelled.'})

    # Execute the delete
    try:
        deleted = _execute_delete(group_id, str(g.user_id), entity_type, entity_id)
        if not deleted:
            return error_response(f'Failed to delete {entity_type} "{entity_name}".', 400)

        # Post confirmation in group chat
        from app.services.chat_service import ChatService
        ChatService.send_message(
            group_id=group_id,
            sender_id=None,
            sender_type='ai',
            content=f'Done! Removed the {entity_type} \"{entity_name}\" from the plan.',
            msg_type='text',
            metadata_json={'agent': 'crew', 'intent': 'delete_item', 'entity_type': entity_type},
        )

        return success_response({
            'message': f'Removed {entity_type} \"{entity_name}\".',
            'entity_type': entity_type,
            'entity_id': entity_id,
        })

    except Exception as exc:
        logger.error('Crew confirm delete failed: %s', exc)
        return error_response('Delete operation failed.', 500)


def _execute_delete(group_id: str, user_id: str, entity_type: str, entity_id: str) -> bool:
    """Execute the actual delete operation on the matched entity."""
    try:
        if entity_type == 'poll':
            from app.services.poll_service import PollService
            success, _ = PollService.delete_poll(group_id, entity_id, user_id)
            return success

        if entity_type == 'checklist':
            from app.services.checklist_service import ChecklistService
            success, _ = ChecklistService.delete_item(group_id, entity_id, user_id)
            return success

        if entity_type == 'place':
            from app.services.travel_place_service import PlaceService
            success, _ = PlaceService.delete_place(group_id, entity_id, user_id)
            return success

        logger.warning('Unsupported delete entity_type: %s', entity_type)
        return False

    except Exception as exc:
        logger.error('_execute_delete failed: type=%s id=%s error=%s', entity_type, entity_id, exc)
        return False
