"""
Invitation Routes for Group Planner
Flask API routes for invitation operations
"""

import logging

from app.infrastructure.auth.decorators import require_auth
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

# Create Blueprint
invitations_bp = Blueprint(
    'gp_invitations',  # Unique name to avoid conflict with expense_engine
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# INVITATION ENDPOINTS
# =========================================================================

@invitations_bp.route('/invitations', methods=['POST'])
@require_auth
def create_invitation():
    """
    Create a group invitation
    
    Request:
        POST /api/v2/group-planner/invitations
        Headers: Authorization: Bearer <token>
        Body: {
            "group_id": 1,
            "email": "friend@example.com"
        }
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        data = request.get_json()
        group_id = data.get('group_id')
        email = data.get('email')
        
        if not group_id:
            return jsonify({
                'success': False,
                'error': 'group_id is required'
            }), 400
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'email is required'
            }), 400
        
        success, result = invitation_service.create_invitation(
            group_id=int(group_id),
            invited_email=email,
            inviter_id=g.user_id,
            inviter_email=g.user_email
        )
        
        if success:
            logger.info(f"Invitation created for {email}")
            
            # Send email notification (optional)
            try:
                from ..email_service import GroupPlannerEmailService
                email_service = GroupPlannerEmailService()
                email_service.send_group_invitation(
                    invited_email=email,
                    inviter_name=result.get('invited_by_name', 'Someone'),
                    group_name=result.get('group_name', 'a group'),
                    invitation_id=result.get('invitation_id')
                )
            except Exception as email_error:
                logger.warning(f"Failed to send invitation email: {email_error}")
            
            return jsonify({
                'success': True,
                'data': result.get('invitation', result)
            }), 201
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Create invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create invitation'
        }), 500


@invitations_bp.route('/invitations/<int:invitation_id>', methods=['GET'])
def get_invitation(invitation_id):
    """
    Get invitation details (public - no auth required)
    Used when user clicks invitation link
    
    Request:
        GET /api/v2/group-planner/invitations/<invitation_id>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.get_invitation(invitation_id)
        
        if success:
            invitation = result.get('invitation', {})
            return jsonify({
                'success': True,
                'invitation_id': str(invitation_id),
                'group_id': invitation.get('group_id'),
                'group_name': invitation.get('group_name'),
                'invited_email': invitation.get('invitee_email'),
                'invited_by_name': invitation.get('invited_by_name'),
                'status': invitation.get('status'),
                'expires_at': invitation.get('expires_at'),
                'created_at': invitation.get('created_at')
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 404
            
    except Exception as e:
        logger.error(f"Get invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get invitation'
        }), 500


@invitations_bp.route('/invitations/<int:invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id):
    """
    Accept a group invitation
    
    Request:
        POST /api/v2/group-planner/invitations/<invitation_id>/accept
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.accept_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id,
            user_email=g.user_email
        )
        
        if success:
            logger.info(f"Invitation {invitation_id} accepted by user {g.user_id}")
            return jsonify({
                'success': True,
                'message': 'Invitation accepted',
                'data': result
            }), 200
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error(f"Accept invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to accept invitation'
        }), 500


@invitations_bp.route('/invitations/<int:invitation_id>/decline', methods=['POST'])
@require_auth
def decline_invitation(invitation_id):
    """
    Decline a group invitation
    
    Request:
        POST /api/v2/group-planner/invitations/<invitation_id>/decline
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.decline_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Decline invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to decline invitation'
        }), 500


@invitations_bp.route('/user/invitations', methods=['GET'])
@require_auth
def get_user_invitations():
    """
    Get all invitations for current user
    
    Request:
        GET /api/v2/group-planner/user/invitations
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.get_user_invitations(
            user_email=g.user_email,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('invitations', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get user invitations error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get invitations'
        }), 500


@invitations_bp.route('/groups/<int:group_id>/invitations', methods=['GET'])
@require_auth
def get_group_invitations(group_id):
    """
    Get all pending invitations for a specific group
    Only group creator/admin can view this
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/invitations
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        from app.services.trip_invite_service import invitation_service

        # Check if user is group member
        success, group_data = group_service.get_group(group_id, g.user_id)
        if not success:
            return jsonify({'success': False, 'error': 'Group not found or access denied'}), 404
        
        # Get pending invitations for this group
        success, result = invitation_service.get_group_pending_invitations(group_id)
        
        if success:
            return jsonify({'success': True, 'data': result.get('invitations', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get group invitations error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get group invitations'
        }), 500


@invitations_bp.route('/invitations/<int:invitation_id>/resend', methods=['POST'])
@require_auth
def resend_invitation(invitation_id):
    """
    Resend an invitation
    
    Request:
        POST /api/v2/group-planner/invitations/<invitation_id>/resend
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.resend_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id
        )
        
        if success:
            # Send email notification
            try:
                from ..email_service import GroupPlannerEmailService
                email_service = GroupPlannerEmailService()
                email_service.send_group_invitation(
                    invited_email=result.get('invited_email'),
                    inviter_name=result.get('invited_by_name', 'Someone'),
                    group_name=result.get('group_name', 'a group'),
                    invitation_id=str(invitation_id)
                )
            except Exception as email_error:
                logger.warning(f"Failed to send invitation email: {email_error}")
            
            return jsonify({
                'success': True,
                'data': result.get('invitation', result)
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Resend invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to resend invitation'
        }), 500


@invitations_bp.route('/invitations/<int:invitation_id>', methods=['DELETE'])
@require_auth
def cancel_invitation(invitation_id):
    """
    Cancel a pending invitation
    
    Request:
        DELETE /api/v2/group-planner/invitations/<invitation_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.cancel_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Cancel invitation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to cancel invitation'
        }), 500
