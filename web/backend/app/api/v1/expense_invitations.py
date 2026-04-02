"""
SQL-based Invitation Routes
API endpoints for managing group invitations
"""

import logging

from app.api.utils.responses import (created_response, error_response,
                                     success_response)
from app.api.utils.validators import validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth)
from app.infrastructure.cache.redis import cache_response, invalidate_cache
from app.schemas.invitations import CreateExpenseInvitationSchema
from app.services.expense_invite_service import invitation_service_sql
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Use /api/expense/invitations to match frontend expectations
invitations_sql_bp = Blueprint('invitations_sql', __name__, url_prefix='/api/v1/expenses/invitations')


@invitations_sql_bp.route('', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
@require_auth
@validate_schema(CreateExpenseInvitationSchema)
def send_invitation():
    """
    Send invitation to join a group (TripRaft Model - returns complete state)
    
    Request body:
    {
        "group_id": 1,
        "invitee_email": "friend@example.com"  # or "invited_email" for compatibility
    }
    
    Response includes:
    - invitation: the created invitation
    - invitations: ALL pending invitations sent by this user
    """
    data = g.validated_data
    
    group_id = data['group_id']
    invitee_email = data.get('invitee_email') or data.get('invited_email') or data.get('email')
    
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.send_invitation(
        group_id=group_id,
        invitee_email=invitee_email,
        invited_by_user_id=user_id
    )
    
    if success:
        # TripRaft Model: Get all invitations for this group after sending
        all_invitations_success, all_invitations_result = invitation_service_sql.get_group_invitations(
            group_id=group_id,
            user_id=user_id
        )
        
        response = {
            **result,
            'invitations': all_invitations_result.get('invitations', []) if all_invitations_success else []
        }
        invalidate_cache('exp_invitations:*')
        invalidate_cache('auth:bootstrap:*')
        return created_response(data=response)
    else:
        return error_response(result.get('error', 'Failed to send invitation'))


@invitations_sql_bp.route('', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='exp_invitations:list', ttl=Config.CACHE_TTLS['invitations'], vary_on_user=True)
def get_user_invitations():
    """Get pending invitations for the current user (for homepage popup)"""
    from flask import g

    # Get user_id from helper function
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.get_pending_invitations_for_user(user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get invitations'))
    """Get all invitations for the current user"""
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.get_invitations(user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get invitations'))
    """Get all invitations for a specific group"""
    user_id = get_current_user_id()
    
    try:
        gid = group_id
    except (ValueError, TypeError):
        return error_response('Invalid group ID')
    
    success, result = invitation_service_sql.get_group_invitations(gid, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Access denied'), 403)


@invitations_sql_bp.route('/<invitation_id>/accept', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
@require_auth
def accept_invitation(invitation_id):
    """Accept a group invitation and return full group details"""
    from app.services.expense_group_service import group_service_sql
    
    user_id = get_current_user_id()
    
    try:
        iid = invitation_id
    except (ValueError, TypeError):
        return error_response('Invalid invitation ID')
    
    success, result = invitation_service_sql.accept_invitation(iid, user_id)
    
    if success:
        # Get all user groups to return the complete updated list
        all_groups_success, all_groups_result = group_service_sql.get_user_groups(user_id)
        
        response_data = {
            **result,
            'groups': all_groups_result.get('groups', []) if all_groups_success else []
        }
        
        invalidate_cache('exp_invitations:*')
        invalidate_cache('exp_groups:*')
        invalidate_cache('auth:bootstrap:*')
        return success_response(data=response_data)
    else:
        return error_response(result.get('error', 'Failed to accept invitation'))


@invitations_sql_bp.route('/<invitation_id>/decline', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
@require_auth
def decline_invitation(invitation_id):
    """Decline a group invitation"""
    user_id = get_current_user_id()
    
    try:
        iid = invitation_id
    except (ValueError, TypeError):
        return error_response('Invalid invitation ID')
    
    success, result = invitation_service_sql.decline_invitation(iid, user_id)
    
    if success:
        invalidate_cache('exp_invitations:*')
        invalidate_cache('auth:bootstrap:*')
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to decline invitation'))
