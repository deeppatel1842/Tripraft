"""
SQL-based Invitation Routes
API endpoints for managing group invitations
"""

import logging

from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth)
from app.services.expense_invite_service import invitation_service_sql
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Use /api/expense/invitations to match frontend expectations
invitations_sql_bp = Blueprint('invitations_sql', __name__, url_prefix='/api/expense/invitations')


@invitations_sql_bp.route('', methods=['POST'])
@require_auth
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
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400
    
    group_id = data.get('group_id')
    # Accept both 'invitee_email' and 'invited_email' for compatibility
    invitee_email = data.get('invitee_email') or data.get('invited_email') or data.get('email')
    
    if not group_id:
        return jsonify({'success': False, 'error': 'group_id is required'}), 400
    if not invitee_email:
        return jsonify({'success': False, 'error': 'invitee_email is required'}), 400
    
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.send_invitation(
        group_id=int(group_id),
        invitee_email=invitee_email,
        invited_by_user_id=user_id
    )
    
    if success:
        # TripRaft Model: Get all invitations for this group after sending
        all_invitations_success, all_invitations_result = invitation_service_sql.get_group_invitations(
            group_id=int(group_id),
            user_id=user_id
        )
        
        response = {
            'success': True,
            **result,
            'invitations': all_invitations_result.get('invitations', []) if all_invitations_success else []
        }
        return jsonify(response), 201
    else:
        return jsonify({'success': False, **result}), 400


@invitations_sql_bp.route('', methods=['GET'])
@require_auth
def get_user_invitations():
    """Get pending invitations for the current user (for homepage popup)"""
    from flask import g

    # Get user_id from helper function
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.get_pending_invitations_for_user(user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@invitations_sql_bp.route('/my', methods=['GET'])
@require_auth
def get_my_invitations():
    """Get all invitations for the current user"""
    user_id = get_current_user_id()
    
    success, result = invitation_service_sql.get_invitations(user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@invitations_sql_bp.route('/group/<group_id>', methods=['GET'])
@require_auth
def get_group_invitations(group_id):
    """Get all invitations for a specific group"""
    user_id = get_current_user_id()
    
    try:
        gid = int(group_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    success, result = invitation_service_sql.get_group_invitations(gid, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 403


@invitations_sql_bp.route('/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id):
    """Accept a group invitation and return full group details"""
    from app.services.expense_group_service import group_service_sql
    
    user_id = get_current_user_id()
    
    try:
        iid = int(invitation_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid invitation ID'}), 400
    
    success, result = invitation_service_sql.accept_invitation(iid, user_id)
    
    if success:
        # Get all user groups to return the complete updated list
        all_groups_success, all_groups_result = group_service_sql.get_user_groups(user_id)
        
        response = {
            'success': True,
            **result,  # Includes 'group' (full details), 'message', 'invitation'
            'groups': all_groups_result.get('groups', []) if all_groups_success else []
        }
        
        return jsonify(response), 200
    else:
        return jsonify({'success': False, **result}), 400


@invitations_sql_bp.route('/<invitation_id>/decline', methods=['POST'])
@require_auth
def decline_invitation(invitation_id):
    """Decline a group invitation"""
    user_id = get_current_user_id()
    
    try:
        iid = int(invitation_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid invitation ID'}), 400
    
    success, result = invitation_service_sql.decline_invitation(iid, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400
