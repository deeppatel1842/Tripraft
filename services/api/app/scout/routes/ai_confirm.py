# Purpose: AI Crew Confirm Routes — REST API for confirming @crew destructive actions. Endpoints:.
"""
AI Crew Confirm Routes — REST API for confirming @crew destructive actions.

Endpoints:
  POST /groups/<group_id>/ai/confirm  — Confirm or cancel a pending @crew action
"""
import json
import logging
from uuid import UUID

from app.core.apiutils.responses import error_response, success_response
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from app.core.cache.redis import invalidate_cache, redis_client
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
        pending_key: individual key from the card (required for expenses)
    """
    body = request.json or {}
    action = body.get('action')

    if action not in ('confirm', 'cancel'):
        return error_response('Invalid action. Must be "confirm" or "cancel".', 400)

    key_prefix = f'crew:confirm:{group_id}:{g.user_id}'
    pending_key = body.get('pending_key', key_prefix)
    # Legacy non-financial cards used one fixed key. New cards carry an
    # individual UUID key; never allow another user's/group's key here.
    if pending_key != key_prefix:
        try:
            if not isinstance(pending_key, str) or not pending_key.startswith(key_prefix + ':'):
                raise ValueError('Invalid confirmation scope')
            UUID(pending_key[len(key_prefix) + 1:])
        except (ValueError, TypeError):
            return error_response('Invalid confirmation key.', 400)

    if not redis_client.available:
        return error_response('Service temporarily unavailable.', 503)

    # Atomic consumption makes every pending confirmation single-use.  A
    # GET followed by DELETE allowed concurrent confirm requests to execute
    # the same destructive operation twice.
    raw = redis_client.getdel(pending_key)
    if not raw:
        return error_response(
            'No pending action found. It may have expired (60s window).', 404,
        )

    try:
        pending = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return error_response('Corrupted pending state. Try again.', 400)

    entity_type = pending.get('entity_type')
    entity_id = pending.get('entity_id')
    entity_name = pending.get('entity_name', '')

    if entity_type == 'expense' and (
        pending_key == key_prefix or not pending.get('expense_group_id')
    ):
        return error_response('Start a new Crew expense deletion to confirm this action.', 400)

    if action == 'cancel':
        return success_response({'message': 'Action cancelled.'})

    # Execute the delete
    try:
        deleted = _execute_delete(
            group_id, str(g.user_id), entity_type, entity_id,
            pending.get('expense_group_id'),
        )
        if not deleted:
            return error_response(f'Failed to delete {entity_type} "{entity_name}".', 400)

        if entity_type == 'expense':
            for pattern in (
                'expenses:*', 'settlements:*', 'auth:bootstrap:*',
                'exp_groups:*', 'gp_groups:expense_summary:*',
            ):
                invalidate_cache(pattern)

        # Post confirmation in group chat
        from app.trips.services.chat_service import ChatService
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
            'expense_group_id': pending.get('expense_group_id'),
        })

    except Exception as exc:
        logger.error('Crew confirm delete failed: %s', exc)
        return error_response('Delete operation failed.', 500)


def _execute_delete(
    group_id: str, user_id: str, entity_type: str, entity_id: str,
    expected_expense_group_id: str = None,
) -> bool:
    """Execute the actual delete operation on the matched entity."""
    try:
        if entity_type == 'poll':
            from app.trips.services.poll_service import PollService
            success, _ = PollService.delete_poll(group_id, entity_id, user_id)
            return success

        if entity_type == 'checklist':
            from app.itinerary.services.checklist_service import ChecklistService
            success, _ = ChecklistService.delete_item(group_id, entity_id, user_id)
            return success

        if entity_type == 'place':
            from app.itinerary.services.travel_place_service import PlaceService
            success, _ = PlaceService.delete_place(group_id, entity_id, user_id)
            return success

        if entity_type == 'expense':
            from app.expenses.models import Expense
            from app.core.db.connection import get_db_session
            from app.scout.services.crew_agent_service import CrewAgentService
            from app.expenses.services.expense_service import ExpenseServiceSQL

            with get_db_session() as session:
                expense = CrewAgentService._deletable_expenses(
                    session, group_id, user_id,
                ).filter(Expense.id == entity_id).first()
                if not expense or str(expense.group_id) != str(expected_expense_group_id):
                    return False
            success, _ = ExpenseServiceSQL.delete_expense(
                entity_id, UUID(str(user_id)), expected_group_id=expected_expense_group_id,
            )
            return success

        logger.warning('Unsupported delete entity_type: %s', entity_type)
        return False

    except Exception as exc:
        logger.error('_execute_delete failed: type=%s id=%s error=%s', entity_type, entity_id, exc)
        return False
