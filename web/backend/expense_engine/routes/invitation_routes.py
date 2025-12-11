"""
Invitation Routes - Invitation Management API
Handles invitation lifecycle (create, accept, decline, revoke)
"""

from flask import Blueprint, request, jsonify
import logging

from ..services.invitation_service import InvitationService
from ..services.group_service import GroupService
from ..middleware.auth import require_auth, get_current_user_id, get_current_user
from ..exceptions import (
    ValidationError, NotFoundError, ForbiddenError,
    InsufficientPermissionsError, DuplicateEntryError
)
from ..config import pagination_config
from ..constants import InvitationStatus

logger = logging.getLogger(__name__)

# Create blueprint
invitation_bp = Blueprint('invitations', __name__, url_prefix='/api/expense/invitations')


@invitation_bp.route('', methods=['POST'])
@require_auth
def create_invitation():
    """
    Create new invitation
    
    POST /api/expense/invitations
    Body: {
        "group_id": "group123",
        "invited_email": "user@example.com",
        "invited_user_id": "user456",  # optional if email is known
        "message": "Join our expense group!"
    }
    
    Response: {
        "success": true,
        "invitation": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        if 'group_id' not in data:
            raise ValidationError("group_id is required")
        
        # Accept both 'email' and 'invited_email' for backward compatibility
        invited_email = data.get('invited_email') or data.get('email')
        invited_user_id = data.get('invited_user_id')
        
        if not invited_email and not invited_user_id:
            raise ValidationError("Either invited_email or invited_user_id is required")
        
        group_id = data['group_id']
        
        # Check group membership and permissions
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        if not group_service.has_permission(group_id, current_user_id, 'invite_members'):
            raise InsufficientPermissionsError("You don't have permission to invite members")
        
        # Create invitation using invitation service
        # Map frontend field names to backend service parameters
        invitation_service = InvitationService()
        invitation = invitation_service.create_invitation(
            group_id=group_id,
            invitee_email=invited_email,  # Use the resolved email
            invited_by=current_user_id,
            role=data.get('role', 'member')
        )
        
        # Get invitation_id from result
        invitation_id = None
        if isinstance(invitation, dict):
            invitation_id = invitation.get('invitation_id') or invitation.get('id')
        
        # Generate invitation link
        import os
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        invitation_link = f"{frontend_url}/accept-invitation?id={invitation_id}&type=expense"
        
        # NOTE: Email is already sent by InvitationService.create_invitation()
        # Do NOT send here to avoid duplicate emails (Phase 17 Bug Fix)
        
        logger.info("Invitation created for group %s", group_id)
        
        return jsonify({
            'success': True,
            'invitation': invitation if isinstance(invitation, dict) else {},
            'invitation_link': invitation_link,
            'email_status': 'sent'  # Email already sent by service layer
        }), 201
        
    except (ValidationError, ForbiddenError, InsufficientPermissionsError, DuplicateEntryError) as e:
        logger.warning("Error in create_invitation: %s", e)
        status_map = {
            ValidationError: 400,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403,
            DuplicateEntryError: 409
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 400)
    except Exception as e:
        logger.error("Error creating invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to create invitation'}), 500


@invitation_bp.route('/<invitation_id>/details', methods=['GET'])
def get_invitation_details(invitation_id: str):
    """
    Get invitation details (PUBLIC - no auth required)
    
    Returns invitation details for display on invitation acceptance page.
    No authentication required to allow new users to view invitation.
    
    GET /api/expense/invitations/:iid/details
    
    Response: {
        "success": true,
        "invitation": {
            "invitation_id": "...",
            "group_id": "...",
            "group_name": "...",
            "invited_email": "...",
            "invited_by_name": "...",
            "status": "pending"
        }
    }
    """
    try:
        logger.info("Getting details for invitation %s", invitation_id)
        
        invitation_service = InvitationService()
        invitation = invitation_service.get_invitation(invitation_id)
        
        if not invitation:
            logger.error("Invitation not found: %s", invitation_id)
            return jsonify({'success': False, 'error': 'Invitation not found'}), 404
        
        # Get invitation data
        inv_data = invitation if isinstance(invitation, dict) else invitation.to_dict()
        
        # Check if invitation is still valid
        if inv_data.get('status') != 'pending':
            logger.warning("Invitation is not pending: %s", inv_data.get('status'))
            return jsonify({'success': False, 'error': 'Invitation is no longer valid'}), 400
        
        # Get group details
        group_service = GroupService()
        group = group_service.get_group(inv_data.get('group_id'))
        if not group:
            logger.error("Group not found: %s", inv_data.get('group_id'))
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # Get inviter details
        from ..repositories.user_repository import UserRepository
        user_repo = UserRepository()
        inviter = user_repo.get_by_id(inv_data.get('invited_by'))
        inviter_name = 'Someone'
        if inviter:
            inviter_name = inviter.get('display_name') or inviter.get('email', 'Someone')
        
        return jsonify({
            'success': True,
            'invitation': {
                'invitation_id': invitation_id,
                'group_id': inv_data.get('group_id'),
                'group_name': group.get('name'),
                'invited_email': inv_data.get('invitee_email') or inv_data.get('email'),
                'invited_by_name': inviter_name,
                'status': inv_data.get('status')
            }
        }), 200
        
    except Exception as e:
        logger.error("Error getting invitation details: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get invitation details'}), 500


@invitation_bp.route('/<invitation_id>', methods=['GET'])
@require_auth
def get_invitation(invitation_id: str):
    """
    Get invitation details
    
    GET /api/expense/invitations/:iid
    
    Response: {
        "success": true,
        "invitation": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get invitation
        invitation_service = InvitationService()
        invitation = invitation_service.get_invitation(invitation_id)
        
        if not invitation:
            raise NotFoundError("Invitation not found")
        
        # Check permissions (inviter, invitee, or group member)
        group_service = GroupService()
        invited_user_id = invitation.get('invited_user_id') if isinstance(invitation, dict) else invitation.invited_user_id
        inviter_id = invitation.get('inviter_id') if isinstance(invitation, dict) else invitation.inviter_id
        group_id = invitation.get('group_id') if isinstance(invitation, dict) else invitation.group_id
        
        if (invited_user_id != current_user_id and 
            inviter_id != current_user_id and
            not group_service.is_member(group_id, current_user_id)):
            raise ForbiddenError("You don't have permission to view this invitation")
        
        return jsonify({
            'success': True,
            'invitation': invitation.to_dict()
        })
        
    except (NotFoundError, ForbiddenError) as e:
        logger.warning("Error in get_invitation: %s", e)
        status = 404 if isinstance(e, NotFoundError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error getting invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get invitation'}), 500


@invitation_bp.route('/user', methods=['GET'])
@require_auth
def get_user_invitations():
    """
    Get invitations for current user
    
    GET /api/expense/invitations/user?status=pending&page=1&limit=20
    
    Response: {
        "success": true,
        "invitations": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user = get_current_user()
        user_email = current_user.get('email', '')
        
        # Get query parameters
        status = request.args.get('status', InvitationStatus.PENDING.value)
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Validate pagination
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if limit < 1 or limit > pagination_config.MAX_PAGE_SIZE:
            raise ValidationError(f"Limit must be between 1 and {pagination_config.MAX_PAGE_SIZE}")
        
        # Get invitations
        invitation_service = InvitationService()
        invitations = invitation_service.get_user_invitations(
            email=user_email,
            status=status
        )
        
        return jsonify({
            'success': True,
            'invitations': invitations if isinstance(invitations, list) else [],
            'page': page,
            'limit': limit,
            'has_more': len(invitations) == limit if invitations else False
        })
        
    except ValidationError as e:
        logger.warning("Error in get_user_invitations: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error getting user invitations: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get invitations'}), 500


@invitation_bp.route('/group/<group_id>', methods=['GET'])
@require_auth
def get_group_invitations(group_id: str):
    """
    Get invitations for a group
    
    GET /api/expense/invitations/group/:gid?status=pending&page=1&limit=20
    
    Response: {
        "success": true,
        "invitations": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get query parameters
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Get invitations
        invitation_service = InvitationService()
        invitations = invitation_service.get_group_invitations(
            group_id=group_id,
            status=status
        )
        
        return jsonify({
            'success': True,
            'invitations': invitations if isinstance(invitations, list) else [],
            'page': page,
            'limit': limit,
            'has_more': len(invitations) == limit if invitations else False
        })
        
    except ForbiddenError as e:
        logger.warning("Error in get_group_invitations: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting group invitations: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get group invitations'}), 500


@invitation_bp.route('/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id: str):
    """
    Accept invitation
    
    POST /api/expense/invitations/:iid/accept
    Body (optional): {
        "token": "..."  // Phase 20.1: JWT token for zero-read acceptance
    }
    
    Response: {
        "success": true,
        "message": "Invitation accepted",
        "group": {...},
        "redirect_url": "/expenses?group=xxx"
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Phase 20.1: Check for invitation token in request body
        invitation_token = None
        data = request.get_json(silent=True)
        if data:
            invitation_token = data.get('token')
        
        # Accept invitation (this adds user to group)
        # Phase 20.1: Pass token if available for zero-read acceptance
        invitation_service = InvitationService()
        group = invitation_service.accept_invitation(
            invitation_id=invitation_id,
            accepted_by_user_id=current_user_id,
            invitation_token=invitation_token
        )
        
        group_id = group.get('group_id') or group.get('id') if group else None
        group_name = group.get('name', 'Unknown') if group else 'Unknown'
        
        logger.info("Invitation accepted: %s by user %s, added to group %s%s", 
                    invitation_id, current_user_id, group_id,
                    " (via token)" if invitation_token else "")
        
        return jsonify({
            'success': True,
            'message': 'Invitation accepted successfully',
            'group': group if isinstance(group, dict) else None,
            'group_id': group_id,
            'group_name': group_name,
            'redirect_url': f'/expenses?group={group_id}' if group_id else '/expenses',
            'refresh_required': True,
            'clear_invitation_cache': True
        })
        
    except (NotFoundError, ForbiddenError, ValidationError) as e:
        logger.warning("Error in accept_invitation: %s", e)
        status_map = {
            NotFoundError: 404,
            ForbiddenError: 403,
            ValidationError: 400
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 400)
    except Exception as e:
        logger.error("Error accepting invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to accept invitation'}), 500


@invitation_bp.route('/accept-by-token', methods=['POST'])
@require_auth
def accept_invitation_by_token():
    """
    Accept invitation using JWT token (Phase 20.1)
    
    This endpoint eliminates the need to read the invitation document,
    as all necessary data is encoded in the signed token.
    
    POST /api/expense/invitations/accept-by-token
    Body: {
        "token": "eyJ..."  // Required: JWT invitation token
    }
    
    Response: {
        "success": true,
        "message": "Invitation accepted",
        "group": {...},
        "redirect_url": "/expenses?group=xxx"
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'token' not in data:
            raise ValidationError("Invitation token is required")
        
        invitation_token = data['token']
        
        # Decode token to get invitation_id (for logging and status update)
        try:
            from ..utils.invitation_token import decode_invitation_token
            token_data = decode_invitation_token(invitation_token)
            invitation_id = token_data['invitation_id']
        except Exception as decode_err:
            logger.warning("Token decode failed: %s", decode_err)
            raise ValidationError(f"Invalid invitation token: {str(decode_err)}")
        
        # Accept invitation using token (0 Firestore reads for invitation data)
        invitation_service = InvitationService()
        group = invitation_service.accept_invitation(
            invitation_id=invitation_id,
            accepted_by_user_id=current_user_id,
            invitation_token=invitation_token
        )
        
        group_id = group.get('group_id') or group.get('id') if group else None
        group_name = group.get('name', 'Unknown') if group else 'Unknown'
        
        logger.info("Invitation accepted via token: %s by user %s, added to group %s", 
                    invitation_id, current_user_id, group_id)
        
        return jsonify({
            'success': True,
            'message': 'Invitation accepted successfully',
            'group': group if isinstance(group, dict) else None,
            'group_id': group_id,
            'group_name': group_name,
            'redirect_url': f'/expenses?group={group_id}' if group_id else '/expenses',
            'refresh_required': True,
            'clear_invitation_cache': True,
            'accepted_via': 'token'  # Indicates token-based acceptance
        })
        
    except ValidationError as e:
        logger.warning("Error in accept_invitation_by_token: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error accepting invitation by token: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to accept invitation'}), 500


@invitation_bp.route('/<invitation_id>/decline', methods=['POST'])
@invitation_bp.route('/<invitation_id>/reject', methods=['POST'])  # Alias for frontend compatibility
@require_auth
def decline_invitation(invitation_id: str):
    """
    Decline/Reject invitation
    
    POST /api/expense/invitations/:iid/decline
    POST /api/expense/invitations/:iid/reject (alias)
    Body: {
        "reason": "Optional decline reason"
    }
    
    Response: {
        "success": true,
        "message": "Invitation declined"
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Decline invitation
        invitation_service = InvitationService()
        invitation_service.decline_invitation(
            invitation_id=invitation_id,
            declined_by_user_id=current_user_id
        )
        
        logger.info("Invitation declined: %s by user %s", invitation_id, current_user_id)
        
        return jsonify({
            'success': True,
            'message': 'Invitation declined'
        })
        
    except (NotFoundError, ForbiddenError) as e:
        logger.warning("Error in decline_invitation: %s", e)
        status = 404 if isinstance(e, NotFoundError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error declining invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to decline invitation'}), 500


@invitation_bp.route('/<invitation_id>/revoke', methods=['POST'])
@require_auth
def revoke_invitation(invitation_id: str):
    """
    Revoke invitation (admin/inviter only)
    
    POST /api/expense/invitations/:iid/revoke
    
    Response: {
        "success": true,
        "message": "Invitation revoked"
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Revoke invitation
        invitation_service = InvitationService()
        invitation_service.revoke_invitation(invitation_id, revoked_by_user_id=current_user_id)
        
        logger.info("Invitation revoked: %s by user %s", invitation_id, current_user_id)
        
        return jsonify({
            'success': True,
            'message': 'Invitation revoked'
        })
        
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError) as e:
        logger.warning("Error in revoke_invitation: %s", e)
        status_map = {
            NotFoundError: 404,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 404)
    except Exception as e:
        logger.error("Error revoking invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to revoke invitation'}), 500


@invitation_bp.route('/<invitation_id>/resend', methods=['POST'])
@require_auth
def resend_invitation(invitation_id: str):
    """
    Resend invitation (extends expiry)
    
    POST /api/expense/invitations/:iid/resend
    
    Response: {
        "success": true,
        "invitation": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Resend invitation
        invitation_service = InvitationService()
        invitation = invitation_service.resend_invitation(invitation_id, resent_by_user_id=current_user_id)
        
        logger.info("Invitation resent: %s by user %s", invitation_id, current_user_id)
        
        return jsonify({
            'success': True,
            'invitation': invitation.to_dict()
        })
        
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError) as e:
        logger.warning("Error in resend_invitation: %s", e)
        status_map = {
            NotFoundError: 404,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 404)
    except Exception as e:
        logger.error("Error resending invitation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to resend invitation'}), 500


# Error handlers
@invitation_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'success': False, 'error': str(error)}), 400


@invitation_bp.errorhandler(NotFoundError)
def handle_not_found(error):
    return jsonify({'success': False, 'error': str(error)}), 404


@invitation_bp.errorhandler(ForbiddenError)
def handle_forbidden(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@invitation_bp.errorhandler(InsufficientPermissionsError)
def handle_insufficient_permissions(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@invitation_bp.errorhandler(DuplicateEntryError)
def handle_duplicate_entry(error):
    return jsonify({'success': False, 'error': str(error)}), 409


@invitation_bp.errorhandler(Exception)
def handle_generic_error(error):
    logger.error("Unexpected error: %s", error, exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
