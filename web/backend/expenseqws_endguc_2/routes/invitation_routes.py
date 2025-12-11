"""
Invitation Management Routes
Handles group invitation creation, retrieval, acceptance, and rejection
"""

from flask import Blueprint, request, jsonify, g
import logging
import time

from ..service import expense_service
from .route_helpers import require_auth, track_time
from ..performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

# Create blueprint
invitation_bp = Blueprint('invitation', __name__)

# Get performance monitor
performance_monitor = get_performance_monitor()


# =============================================================================
# INVITATION CRUD ROUTES
# =============================================================================

@invitation_bp.route('/invitations', methods=['POST'])
@require_auth
def create_invitation():
    """
    Create group invitation
    
    Creates invitation for new member to join group.
    Sends email notification asynchronously if email provided.
    Only group members can send invitations.
    
    Request Body:
        group_id (str): Required. Group ID
        email (str): Optional. Invitee email
        username (str): Optional. Invitee username
        
    Note: Either email or username must be provided.
    
    Returns:
        201: Invitation created successfully
        400: Validation error
        403: User not authorized
        404: Group not found
        500: Server error
    """
    try:
        data = request.get_json()
        
        group_id = data.get('group_id')
        invited_email = data.get('email')
        invited_username = data.get('username')
        
        logger.info(f"Creating invitation for group_id={group_id}, email={invited_email}, username={invited_username}")
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        if not invited_email and not invited_username:
            return jsonify({'error': 'Email or username is required'}), 400
        
        # Check if user is admin or member using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            logger.error(f"Access denied: User {g.user_id} not a member of group {group_id}")
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
            
        group = expense_service.get_group(group_id)
        if not group:
            logger.error(f"Group not found: {group_id}")
            return jsonify({'error': 'Group not found'}), 404
        
        logger.info(f"Group found: {group.get('name')} (ID: {group_id})")
        
        # Create invitation
        invitation = expense_service.create_invitation(
            group_id=group_id,
            invited_by=g.user_id,
            invited_email=invited_email,
            invited_username=invited_username
        )
        
        logger.info(f"Invitation created: {invitation.get('invitation_id')} for group {group_id}")
        
        # Generate invitation link with proper type parameter
        invitation_link = f"http://localhost:5173/accept-invitation?id={invitation['invitation_id']}&type=expense"
        
        # Send email asynchronously if email provided (non-blocking)
        email_status = 'not_sent'
        if invited_email:
            try:
                from ..workers import get_email_worker
                email_worker = get_email_worker()
                
                inviter = expense_service.get_user(g.user_id)
                inviter_name = inviter.get('display_name', inviter.get('username', 'Someone'))
                
                # Queue invitation email
                email_worker.queue_email(
                    email_type='invitation_sent',
                    recipients=[invited_email],
                    data={
                        'inviter_name': inviter_name,
                        'group_name': group['name'],
                        'invitation_link': invitation_link
                    }
                )
                email_status = 'sending'
                logger.info(f"📧 Invitation email queued for {invited_email}")
            except Exception as e:
                email_status = 'error'
                logger.error(f"❌ Failed to queue invitation email: {e}")
                logger.info(f"📧 Manual invitation link: {invitation_link}")
        
        return jsonify({
            'success': True, 
            'invitation': invitation,
            'group_name': group['name'],
            'group_id': group_id,
            'invitation_link': invitation_link,
            'email_status': email_status  # 'sending', 'not_sent', or 'error'
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating invitation: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@invitation_bp.route('/invitations', methods=['GET'])
@require_auth
@track_time("GET_USER_INVITATIONS")
def get_user_invitations():
    """
    Get pending invitations for current user
    
    Returns pending invitations for authenticated user.
    Supports pagination for better performance.
    
    Query Parameters:
        limit (int): Maximum number of invitations to return (default: 20, max: 100)
        offset (int): Number of invitations to skip (default: 0)
    
    Returns:
        200: Invitations retrieved successfully
        500: Server error
    """
    start_time = time.time()
    firestore_reads = 0
    
    try:
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Get pending invitations for user with pagination
        # NOTE: New users with no groups NEED to see invitations!
        invitations = expense_service.get_user_invitations(
            g.user_id,
            limit=limit,
            offset=offset
        )
        firestore_reads = len(invitations)  # Approximate
        
        logger.info(f"✅ Fetched {len(invitations)} pending invitations for user {g.user_id} (limit={limit}, offset={offset})")
        
        # Track performance
        duration_ms = (time.time() - start_time) * 1000
        performance_monitor.track_api_call(
            endpoint='/invitations',
            method='GET',
            duration_ms=duration_ms,
            status_code=200,
            user_id=g.user_id,
            firestore_reads=firestore_reads
        )
        
        return jsonify({
            'success': True, 
            'invitations': invitations,
            'limit': limit,
            'offset': offset,
            'has_more': len(invitations) == limit
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting invitations: {e}")
        duration_ms = (time.time() - start_time) * 1000
        performance_monitor.track_api_call(
            endpoint='/invitations',
            method='GET',
            duration_ms=duration_ms,
            status_code=500,
            user_id=g.user_id,
            firestore_reads=firestore_reads
        )
        return jsonify({'error': 'Internal server error'}), 500


@invitation_bp.route('/invitations/group/<group_id>', methods=['GET'])
@require_auth
def get_group_invitations(group_id):
    """
    Get invitations for a group
    
    Returns invitations for specified group.
    Only accessible to group members.
    
    Query Parameters:
        include_all (bool): If true, include pending, declined, and accepted invitations.
                           If false (default), only return pending invitations.
    
    Returns:
        200: Invitations retrieved successfully
        403: User not a member
        500: Server error
    """
    try:
        # Check if user is member of the group using group_members collection (authoritative source)
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            logger.warning(f"Access denied: User {g.user_id} not a member of group {group_id}")
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return jsonify({'error': 'Group not found'}), 404
        
        # Check if include_all is requested
        include_all = request.args.get('include_all', 'false').lower() == 'true'
        
        invitations = expense_service.get_group_invitations(group_id, include_all=include_all)
        return jsonify({'success': True, 'invitations': invitations}), 200
    
    except Exception as e:
        logger.error(f"Error getting group invitations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@invitation_bp.route('/invitations/<invitation_id>/details', methods=['GET'])
def get_invitation_details(invitation_id):
    """
    Get invitation details (PUBLIC - no auth required)
    
    Returns invitation details for display on invitation acceptance page.
    No authentication required to allow new users to view invitation.
    
    Returns:
        200: Invitation details retrieved
        400: Invitation not valid (already accepted/rejected)
        404: Invitation not found
        500: Server error
    """
    try:
        logger.info(f"Getting details for invitation {invitation_id}")
        
        invitation = expense_service.get_invitation_by_id(invitation_id)
        if not invitation:
            logger.error(f"Invitation not found: {invitation_id}")
            return jsonify({'success': False, 'error': 'Invitation not found'}), 404
        
        # Check if invitation is still valid
        if invitation.get('status') != 'pending':
            logger.error(f"Invitation is not pending: {invitation.get('status')}")
            return jsonify({'success': False, 'error': 'Invitation is no longer valid'}), 400
        
        # Get group details
        group = expense_service.get_group(invitation['group_id'])
        if not group:
            logger.error(f"Group not found: {invitation['group_id']}")
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # Get inviter details
        inviter = expense_service.get_user(invitation['invited_by'])
        inviter_name = inviter.get('display_name', inviter.get('username', 'Someone')) if inviter else 'Someone'
        
        return jsonify({
            'success': True,
            'invitation': {
                'invitation_id': invitation_id,
                'group_id': invitation['group_id'],
                'group_name': group.get('name'),
                'invited_email': invitation.get('invited_email'),
                'invited_by_name': inviter_name,
                'status': invitation.get('status')
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting invitation details: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# INVITATION RESPONSE ROUTES
# =============================================================================

@invitation_bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id):
    """
    Accept group invitation
    
    Accepts invitation and adds user to group.
    Validates invitation is for authenticated user.
    
    Returns:
        200: Invitation accepted, user added to group
        400: Invitation already responded to
        403: Invitation not for authenticated user
        404: Invitation not found
        500: Server error
        
    Response includes:
        - group_details: Group information
        - redirect_url: Frontend URL to navigate to
    """
    try:
        logger.info(f"User {g.user_id} ({g.user_email}) attempting to accept invitation {invitation_id}")
        
        # Get invitation details first
        invitation = expense_service.get_invitation_by_id(invitation_id)
        if not invitation:
            logger.error(f"Invitation not found: {invitation_id}")
            return jsonify({
                'success': False,
                'error': 'Invitation not found',
                'code': 'INVITATION_NOT_FOUND'
            }), 404
        
        group_id = invitation.get('group_id')
        logger.info(f"Invitation details: group_id={group_id}, invited_email={invitation.get('invited_email')}, status={invitation.get('status')}")
        
        # Check if invitation is for the current user
        if invitation.get('invited_email') != g.user_email:
            logger.error(f"Invitation email mismatch: {invitation.get('invited_email')} != {g.user_email}")
            return jsonify({
                'success': False,
                'error': 'This invitation is not for you',
                'code': 'UNAUTHORIZED'
            }), 403
        
        # Check if invitation is still pending
        if invitation.get('status') != 'pending':
            logger.error(f"Invitation status is not pending: {invitation.get('status')}")
            return jsonify({
                'success': False,
                'error': 'Invitation has already been responded to',
                'code': 'ALREADY_RESPONDED'
            }), 400
        
        success = expense_service.respond_to_invitation(invitation_id, g.user_id, True)
        
        if success:
            # Get fresh group details after adding member
            group = expense_service.get_group(group_id)
            logger.info(f"✅ Invitation accepted successfully. User {g.user_id} added to group {group_id} ({group.get('name') if group else 'Unknown'})")
            
            # 🔔 Send real-time notification to group members (for future WebSocket)
            # For now, client will poll/refetch
            
            # Return proper redirect URL for frontend
            return jsonify({
                'success': True, 
                'message': 'Invitation accepted successfully',
                'group_name': group.get('name') if group else 'Unknown',
                'group_id': group_id,
                'redirect_url': f'/expenses?group={group_id}',
                'group_details': {
                    'id': group_id,
                    'name': group.get('name'),
                    'currency': group.get('currency', 'USD'),
                    'member_count': len(group.get('members', []))
                } if group else None,
                # 🔔 BUG FIX: Signal frontend to immediately refresh all data
                'refresh_required': True,
                'clear_invitation_cache': True
            }), 200
        else:
            logger.error(f"Failed to accept invitation {invitation_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to accept invitation',
                'code': 'ACCEPTANCE_FAILED'
            }), 500
    
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


@invitation_bp.route('/invitations/<invitation_id>/reject', methods=['POST'])
@require_auth
def reject_invitation(invitation_id):
    """
    Reject group invitation
    
    Rejects invitation without adding user to group.
    
    Returns:
        200: Invitation rejected successfully
        500: Server error
    """
    try:
        success = expense_service.respond_to_invitation(invitation_id, g.user_id, False)
        
        if success:
            return jsonify({'success': True, 'message': 'Invitation rejected'}), 200
        else:
            return jsonify({'error': 'Failed to reject invitation'}), 500
    
    except Exception as e:
        logger.error(f"Error rejecting invitation: {e}")
        return jsonify({'error': 'Internal server error'}), 500
