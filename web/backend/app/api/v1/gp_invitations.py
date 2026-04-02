"""
Invitation Routes for Group Planner
Flask API routes for invitation operations
"""

import logging

from app.api.utils.responses import (created_response, error_response,
                                     not_found_response, success_response)
from app.api.utils.validators import validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth
from app.infrastructure.cache.redis import cache_response, invalidate_cache
from app.schemas.invitations import CreateGPInvitationSchema
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
invitations_bp = Blueprint(
    'gp_invitations',  # Unique name to avoid conflict with expense_engine
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# INVITATION ENDPOINTS
# =========================================================================

@invitations_bp.route('/invitations', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
@require_auth
@validate_schema(CreateGPInvitationSchema)
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
        
        data = g.validated_data
        group_id = data['group_id']
        email = data['email']
        
        success, result = invitation_service.create_invitation(
            group_id=group_id,
            invited_email=email,
            inviter_id=g.user_id,
            inviter_email=g.user_email
        )
        
        if success:
            logger.info(f"Invitation created for {email}")
            invalidate_cache('gp_invitations:*')
            
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
            
            return created_response(data=result.get('invitation', result))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Create invitation error: {str(e)}")
        return error_response('Failed to create invitation', 500)


@invitations_bp.route('/invitations/<invitation_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_invitations:detail', ttl=Config.CACHE_TTLS['invitations'], vary_on_user=True)
def get_invitation(invitation_id):
    """
    Get invitation details.
    Requires authentication to prevent enumeration of invitation data.
    
    Request:
        GET /api/v2/group-planner/invitations/<invitation_id>
    """
    try:
        from app.services.trip_invite_service import invitation_service
        
        success, result = invitation_service.get_invitation(invitation_id)
        
        if success:
            invitation = result.get('invitation', {})
            return success_response(data={
                'invitation_id': str(invitation_id),
                'group_id': invitation.get('group_id'),
                'group_name': invitation.get('group_name'),
                'invited_email': invitation.get('invitee_email'),
                'invited_by_name': invitation.get('invited_by_name'),
                'status': invitation.get('status'),
                'expires_at': invitation.get('expires_at'),
                'created_at': invitation.get('created_at')
            })
        else:
            return not_found_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Get invitation error: {str(e)}")
        return error_response('Failed to get invitation', 500)


@invitations_bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
@require_auth
def accept_invitation(invitation_id):
    """
    Accept a group invitation.
    Only the invitation recipient (matching email) can accept.
    
    Request:
        POST /api/v2/group-planner/invitations/<invitation_id>/accept
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.trip_invite_service import invitation_service

        # The service validates that g.user_email matches invitation.invitee_email
        success, result = invitation_service.accept_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id,
            user_email=g.user_email
        )
        
        if success:
            logger.info(f"Invitation {invitation_id} accepted by user {g.user_id}")
            invalidate_cache('gp_invitations:*')
            invalidate_cache('gp_groups:*')
            return success_response(data=result, message='Invitation accepted')
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Accept invitation error: {str(e)}")
        return error_response('Failed to accept invitation', 500)


@invitations_bp.route('/invitations/<invitation_id>/decline', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
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
            invalidate_cache('gp_invitations:*')
            return success_response(message=result.get('message'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Decline invitation error: {str(e)}")
        return error_response('Failed to decline invitation', 500)


@invitations_bp.route('/user/invitations', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_invitations:user', ttl=Config.CACHE_TTLS['invitations'], vary_on_user=True)
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
            return success_response(data=result.get('invitations', []))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Get user invitations error: {str(e)}")
        return error_response('Failed to get invitations', 500)


@invitations_bp.route('/groups/<group_id>/invitations', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_invitations:group', ttl=Config.CACHE_TTLS['invitations'], vary_on_user=True)
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
            return not_found_response('Group not found or access denied')
        
        # Get pending invitations for this group
        success, result = invitation_service.get_group_pending_invitations(group_id)
        
        if success:
            return success_response(data=result.get('invitations', []))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Get group invitations error: {str(e)}")
        return error_response('Failed to get group invitations', 500)


@invitations_bp.route('/invitations/<invitation_id>/resend', methods=['POST'])
@limit_api(Config.RATE_LIMITS['invitation'])
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
            
            return success_response(data=result.get('invitation', result))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Resend invitation error: {str(e)}")
        return error_response('Failed to resend invitation', 500)


@invitations_bp.route('/invitations/<invitation_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
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
            invalidate_cache('gp_invitations:*')
            return success_response(message=result.get('message'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Cancel invitation error: {str(e)}")
        return error_response('Failed to cancel invitation', 500)
