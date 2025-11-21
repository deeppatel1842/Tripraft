"""
Group Planner Routes - Phase 1: Authentication Verification
Professional implementation with proper logging and error handling
"""

import logging
import sys
import time
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
import firebase_admin
from firebase_admin import auth as firebase_auth, firestore

# Configure logging
logger = logging.getLogger(__name__)

# Function to flush output immediately
def flush_output():
    sys.stdout.flush()
    sys.stderr.flush()

# Create Blueprint
group_planner_bp = Blueprint(
    'group_planner',
    __name__,
    url_prefix='/api/group-planner'
)


def verify_firebase_token(f):
    """
    Decorator to verify Firebase authentication token
    Validates token and sets g.user_id, g.user_email, g.token in request context
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip token verification for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 200
        
        start_time = time.time()
        
        # logger.debug('🔐 Token verification started')
        
        auth_header = request.headers.get('Authorization', '')
        
        # Check if Authorization header exists
        if not auth_header:
            logger.warning("❌ Auth verification failed: Missing Authorization header")
            return jsonify({
                'success': False,
                'error': 'Missing Authorization header',
                'code': 'NO_AUTH_HEADER'
            }), 401
        
        # logger.debug('✅ Authorization header present: %d chars', len(auth_header))
        
        # Extract token (format: "Bearer <token>")
        try:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0] != 'Bearer':
                logger.warning("❌ Auth verification failed: Invalid Authorization format")
                return jsonify({
                    'success': False,
                    'error': 'Invalid Authorization format. Use: Bearer <token>',
                    'code': 'INVALID_AUTH_FORMAT'
                }), 401
            
            token = parts[1]
            # logger.debug('✅ Token extracted: %d chars', len(token))
        except Exception as e:
            logger.error("❌ Error parsing Authorization header: %s", e)
            return jsonify({
                'success': False,
                'error': 'Error parsing Authorization header',
                'code': 'AUTH_PARSE_ERROR'
            }), 401
        
        # Verify token with Firebase
        try:
            # logger.debug('📍 Step 1: Verifying token with Firebase Admin SDK...')
            verify_start = time.time()
            
            decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=60)
            verify_time = (time.time() - verify_start) * 1000  # Convert to ms
            
            # logger.debug('✅ Token verified successfully (%.2fms)', verify_time)
            
            # Extract user information
            user_id = decoded_token.get('uid')
            user_email = decoded_token.get('email', '')
            
            # logger.debug('📍 Step 2: Extracting user info - UID: %s, Email: %s', user_id, user_email)
            
            # Validate user_id exists
            if not user_id:
                logger.warning("❌ Auth verification failed: No UID in token")
                return jsonify({
                    'success': False,
                    'error': 'Invalid token: No UID found',
                    'code': 'NO_UID_IN_TOKEN'
                }), 401
            
            # Set request context variables
            g.user_id = user_id
            g.user_email = user_email
            g.token = token
            
            total_time = (time.time() - start_time) * 1000
            # logger.info("✅ Auth verification successful: %s (%s) in %.2fms", user_id, user_email, total_time)
            
            return f(*args, **kwargs)
        
        except firebase_auth.RevokedIdTokenError:
            logger.warning("❌ Auth verification failed: Token revoked")
            return jsonify({
                'success': False,
                'error': 'Token has been revoked',
                'code': 'TOKEN_REVOKED'
            }), 401
        
        except firebase_auth.ExpiredIdTokenError:
            logger.warning("❌ Auth verification failed: Token expired")
            return jsonify({
                'success': False,
                'error': 'Token has expired',
                'code': 'TOKEN_EXPIRED'
            }), 401
        
        except firebase_auth.InvalidIdTokenError as e:
            logger.warning("❌ Auth verification failed: Invalid token - %s", e)
            return jsonify({
                'success': False,
                'error': 'Invalid authentication token',
                'code': 'INVALID_TOKEN'
            }), 401
        
        except Exception as e:
            logger.error("❌ Unexpected error during token verification: %s", e)
            return jsonify({
                'success': False,
                'error': 'Authentication error: ' + str(e),
                'code': 'AUTH_ERROR'
            }), 500
    
    return decorated_function


# =========================================================================
# PHASE 1: AUTHENTICATION ENDPOINTS
# =========================================================================

@group_planner_bp.route('/auth/verify', methods=['POST'])
@verify_firebase_token
def verify_auth():
    """
    Phase 1 Test Endpoint: Verify authentication
    
    Tests:
    - Authorization header is present
    - Token is valid Firebase ID token
    - currentUser.uid can be extracted from token
    - Token can be used in API calls
    
    Request:
        POST /api/group-planner/auth/verify
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "message": "Authentication verified successfully",
            "user": {
                "uid": "firebase-uid-here",
                "email": "user@example.com"
            },
            "token": {
                "status": "valid",
                "present": true,
                "passed_to_endpoint": true
            }
        }
    """
    try:
        # logger.info("🔐 verify_auth() called by user: %s", g.user_id)
        # logger.debug('User ID: %s, Email: %s, Token present: %s', g.user_id, g.user_email, bool(g.token))
        
        response = {
            'success': True,
            'message': 'Authentication verified successfully',
            'data': {
                'user': {
                    'uid': g.user_id,
                    'email': g.user_email
                },
                'token': {
                    'status': 'valid',
                    'present': bool(g.token),
                    'passed_to_endpoint': True
                },
                'verification': {
                    'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
                    'verified_by': 'Firebase Admin SDK'
                }
            }
        }
        
        # logger.debug("✅ Auth verification response sent")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error("❌ Error in verify_auth: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'VERIFY_ERROR'
        }), 500


@group_planner_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no auth required)
    Verify backend is running and Firebase is configured
    """
    try:
        # logger.info("🏥 health check called")
        
        # Check Firebase connection
        firebase_ok = True
        firebase_error = None
        try:
            # Try to get Firebase app instance
            firebase_admin.get_app()
        except Exception as e:
            firebase_ok = False
            firebase_error = str(e)
        
        # Phase 4: Check Redis cache health
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_health = cache_ops.health_check()
        
        response = {
            'success': True,
            'service': 'Group Planner API',
            'version': '1.0.0-phase-4',
            'status': 'healthy',
            'components': {
                'firebase': 'connected' if firebase_ok else f'error: {firebase_error}',
                'redis_cache': cache_health,
                'auth_verification': 'available',
                'endpoints': {
                    'auth_verify': '/api/group-planner/auth/verify (POST) - requires auth',
                    'health': '/api/group-planner/health (GET) - no auth required',
                    'cache_metrics': '/api/group-planner/cache/metrics (GET) - requires auth'
                }
            },
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }
        
        # logger.info("✅ Health check passed")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error("❌ Health check failed: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'HEALTH_CHECK_ERROR'
        }), 500


@group_planner_bp.route('/cache/metrics', methods=['GET'])
@verify_firebase_token
def get_cache_metrics():
    """
    Phase 4: Get Redis cache metrics and statistics
    Returns detailed cache performance metrics for monitoring
    
    Request:
        GET /api/group-planner/cache/metrics
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": {
                "available": true,
                "hit_rate": 85.5,
                "total_keys": 127,
                "keys_by_type": {...},
                "memory_usage": "2.5 MB",
                ...
            }
        }
    """
    try:
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        
        stats = cache_ops.get_cache_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error("Error fetching cache metrics: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CACHE_METRICS_ERROR'
        }), 500


@group_planner_bp.route('/cache/clear', methods=['POST'])
@verify_firebase_token
def clear_user_cache():
    """
    Phase 4: Clear cache for current user (for debugging/testing)
    Useful when cache has stale data
    
    Request:
        POST /api/group-planner/cache/clear
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "message": "Cache cleared for user"
        }
    """
    try:
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        
        # Clear user's caches
        cache_ops.invalidate_user_groups(g.user_id)
        cache_ops.invalidate_user_invitations(g.user_id)
        
        # logger.info("🗑️ [CACHE] Cleared cache for user: %s", g.user_id)
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        }), 200
        
    except Exception as e:
        logger.error("Error clearing cache: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CACHE_CLEAR_ERROR'
        }), 500


# =========================================================================
# PHASE 2: GROUP OPERATIONS (Firestore backed)
# =========================================================================

@group_planner_bp.route('/groups', methods=['POST'])
@verify_firebase_token
def create_group():
    """
    Phase 2: Create a new group
    
    Request:
        POST /api/group-planner/groups
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Bali Trip",
            "destination": "Bali, Indonesia",
            "description": "Summer vacation"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "group_id": "generated-id",
                "name": "Bali Trip",
                "destination": "Bali, Indonesia",
                "created_by": "user-uid",
                "created_at": "2025-11-12T10:30:00Z"
            }
        }
    """
    try:
        # logger.info('📍 CREATE GROUP by user: %s', g.user_id)
        
        # Get JSON data
        data = request.get_json()
        # logger.debug('Request data: %s', data)
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Use firebase_operations for shared collection access
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Get user's display name from Firebase Auth
        try:
            user_record = firebase_auth.get_user(g.user_id)
            display_name = user_record.display_name or g.user_email.split('@')[0]
        except Exception as e:
            # logger.debug('⚠️ Could not fetch user display name: %s', e)
            display_name = g.user_email.split('@')[0]
        
        # Create or update user profile in shared users collection
        firebase_ops.create_or_update_user(
            uid=g.user_id,
            email=g.user_email,
            display_name=display_name
        )
        
        # logger.debug('💾 Creating group in shared collection...')
        
        # Create group in shared travel_groups collection
        group_id = firebase_ops.create_group(
            name=data.get('name'),
            description=data.get('description', ''),
            created_by=g.user_id,
            destination=data.get('destination', '')
        )
        
        # Retrieve created group for response
        group_data = firebase_ops.get_group(group_id)
        if not group_data:
            raise ValueError('Failed to retrieve created group')
        
        # logger.info("✅ Group created: %s by %s", group_id, g.user_id)
        
        # Phase 4: Invalidate user groups cache (new group added to user's list)
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_user_groups(g.user_id)
        
        response = {
            'success': True,
            'data': {
                'group_id': group_id,
                **group_data
            }
        }
        return jsonify(response), 201
    
    except Exception as e:
        logger.error("❌ Error creating group: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CREATE_GROUP_ERROR'
        }), 500


@group_planner_bp.route('/user/groups', methods=['GET'])
@verify_firebase_token
def get_user_groups():
    """
    Phase 2: Get all groups for current user
    
    Request:
        GET /api/group-planner/user/groups
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": [
                {
                    "group_id": "id1",
                    "name": "Bali Trip",
                    "destination": "Bali",
                    ...
                }
            ]
        }
    """
    try:
        # logger.info('📍 GET USER GROUPS for user: %s', g.user_id)
        
        # Try to get from cache first
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cached_groups = cache_ops.get_cached_user_groups(g.user_id)
            if cached_groups is not None:
                # logger.debug('✅ Cache HIT: Found %d groups', len(cached_groups))
                return jsonify({
                    'success': True,
                    'data': cached_groups
                }), 200
            # logger.debug('📖 Cache MISS: Fetching from Firestore...')
        except Exception as e:
            # logger.debug('⚠️ Cache error: %s, falling back to Firestore', e)
        
        # Use firebase_operations for shared collection access
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Get all groups for this user from shared collections
        groups_list = firebase_ops.get_user_groups(g.user_id)
        
        # Validate expense_group_id - check if expense group actually exists
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from expense_engine.firebase_operations import ExpenseFirebaseOperations
            expense_db = ExpenseFirebaseOperations()
            
            for group in groups_list:
                expense_group_id = group.get('expense_group_id')
                if expense_group_id:
                    # Check if expense group still exists
                    try:
                        expense_group = expense_db.get_group(expense_group_id)
                        if not expense_group:
                            # Expense group was deleted, remove the link
                            logger.warning("⚠️ Expense group %s no longer exists, removing link from group %s", 
                                         expense_group_id, group.get('group_id'))
                            group['expense_group_id'] = None
                            # Update Firestore to remove stale link
                            firebase_ops.update_group(group.get('group_id'), {'expense_group_id': None})
                    except Exception as check_err:
                        # logger.debug("⚠️ Could not verify expense group %s: %s", expense_group_id, check_err)
        except Exception as e:
            # logger.debug("⚠️ Could not validate expense groups: %s", e)
        
        # Cache the result
        try:
            cache_ops.cache_user_groups(g.user_id, groups_list)
            # logger.debug('💾 Groups cached for user %s', g.user_id)
        except Exception as e:
            # logger.debug('⚠️ Failed to cache groups: %s', e)
        
        # logger.info("✅ Retrieved %d groups for user %s (shared collections)", len(groups_list), g.user_id)
        
        response = {
            'success': True,
            'data': groups_list
        }
        return jsonify(response), 200
    
    except Exception as e:
        logger.error("❌ Error fetching groups: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'GET_GROUPS_ERROR'
        }), 500


# =========================================================================
# PHASE 2B: INVITATION ENDPOINTS
# =========================================================================

from Group_planner.invitation_service import InvitationService
from Group_planner.email_service import GroupPlannerEmailService

invitation_service = InvitationService()
email_service = GroupPlannerEmailService()


@group_planner_bp.route('/invitations', methods=['POST'])
@verify_firebase_token
def create_invitation():
    """
    Create a group invitation via email
    
    Request:
        POST /api/group-planner/invitations
        Headers: Authorization: Bearer <token>
        Body: {
            "group_id": "group-id-here",
            "email": "friend@example.com"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "invitation_id": "inv-id",
                "group_id": "group-id",
                "invited_email": "friend@example.com",
                "status": "pending",
                "created_at": "2025-11-13T10:30:00Z",
                "expires_at": "2025-11-20T10:30:00Z"
            }
        }
    """
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        invited_email = data.get('email')

        # logger.info("[Invitation] Create request from %s (%s) to invite %s to group %s", g.user_id, g.user_email, invited_email, group_id)
        
        # Create invitation using service
        invitation_data = invitation_service.create_invitation(
            group_id=group_id,
            invited_email=invited_email,
            inviter_id=g.user_id,
            inviter_email=g.user_email
        )

        # logger.info('✅ Invitation created: %s for email: %s', invitation_data["invitation_id"], invitation_data.get("invited_email"))

        # Phase 4: Invalidate invitation caches for both inviter and invitee
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_user_invitations(g.user_id)  # Inviter's cache
        # Note: We can't invalidate invitee's cache by email, only by user_id when they log in

        # Send invitation email
        email_sent = email_service.send_group_invitation(
            invited_email=invited_email,
            inviter_name=invitation_data['invited_by_name'],
            group_name=invitation_data['group_name'],
            invitation_id=invitation_data['invitation_id']
        )

        if not email_sent:
            logger.warning("Failed to send invitation email to %s", invited_email)

        response = {
            'success': True,
            'data': invitation_data,
            'email_sent': email_sent
        }

        # logger.debug("✅ Invitation response prepared")
        return jsonify(response), 201

    except ValueError as e:
        logger.warning("Validation error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error creating invitation: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CREATE_INVITATION_ERROR'
        }), 500


@group_planner_bp.route('/invitations/<invitation_id>', methods=['GET'])
def get_invitation_details(invitation_id):
    """
    Get invitation details (public endpoint - no auth required)
    Used when user clicks invitation link in email before logging in
    
    Request:
        GET /api/group-planner/invitations/<invitation_id>
    
    Response:
        {
            "success": true,
            "invitation_id": "inv-id",
            "group_id": "group-id",
            "group_name": "Trip to Hawaii",
            "invited_email": "user@example.com",
            "invited_by_name": "John Doe",
            "created_at": "2025-01-01T00:00:00",
            "expires_at": "2025-01-08T00:00:00",
            "status": "pending"
        }
    """
    try:
        # logger.info("[Invitation] Getting details for invitation %s", invitation_id)
        
        # Get invitation
        invitation = invitation_service.get_invitation(invitation_id)
        if not invitation:
            logger.error("Invitation not found: %s", invitation_id)
            return jsonify({'success': False, 'error': 'Invitation not found'}), 404
        
        # Check if invitation is still valid
        if invitation.get('status') != 'pending':
            logger.warning("Invitation is not pending: %s", invitation.get('status'))
            return jsonify({
                'success': False, 
                'error': f'Invitation is {invitation.get("status")}'
            }), 400
        
        # Check if expired
        expires_at = invitation.get('expires_at')
        if expires_at and datetime.fromisoformat(expires_at.replace('Z', '+00:00')) < datetime.now():
            logger.warning("Invitation has expired: %s", invitation_id)
            return jsonify({'success': False, 'error': 'Invitation has expired'}), 400
        
        # Return invitation details
        response = {
            'success': True,
            'invitation_id': invitation_id,
            'group_id': invitation.get('group_id'),
            'group_name': invitation.get('group_name'),
            'invited_email': invitation.get('invited_email'),
            'invited_by_name': invitation.get('created_by_name', 'Someone'),
            'created_at': invitation.get('created_at'),
            'expires_at': invitation.get('expires_at'),
            'status': invitation.get('status')
        }
        
        # logger.info("✅ Invitation details retrieved: %s", invitation_id)
        return jsonify(response), 200

    except Exception as e:
        logger.error("Error getting invitation details: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get invitation',
            'code': 'GET_INVITATION_ERROR'
        }), 500


@group_planner_bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@verify_firebase_token
def accept_invitation(invitation_id):
    """
    Accept a group invitation
    
    Request:
        POST /api/group-planner/invitations/<invitation_id>/accept
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "message": "Invitation accepted",
            "data": {
                "group_id": "group-id",
                "invitation_id": "inv-id"
            }
        }
    """
    try:
        # logger.info("[Invitation] Accept request from %s", g.user_id)

        # Accept invitation using service
        result = invitation_service.accept_invitation(
            invitation_id=invitation_id,
            user_id=g.user_id,
            user_email=g.user_email
        )

        # Phase 4: Invalidate caches after accepting invitation
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_user_invitations(g.user_id)  # User's invitations cache
        cache_ops.invalidate_user_groups(g.user_id)  # User's groups cache (new group added)
        cache_ops.invalidate_group(result.get('group_id'))  # Group cache (new member added)

        response = {
            'success': True,
            'message': 'Invitation accepted successfully',
            'data': result
        }

        # logger.info("✅ Invitation accepted: %s", invitation_id)
        return jsonify(response), 200

    except ValueError as e:
        logger.warning("Validation error: %s", e)
        error_code = 404 if 'not found' in str(e).lower() else 400
        return jsonify({'success': False, 'error': str(e)}), error_code
    except Exception as e:
        logger.error("Error accepting invitation: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'ACCEPT_INVITATION_ERROR'
        }), 500


@group_planner_bp.route('/user/invitations', methods=['GET'])
@verify_firebase_token
def get_user_invitations():
    """
    Get all pending invitations for current user
    Phase 4: Added Redis caching for performance
    
    Request:
        GET /api/group-planner/user/invitations
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": [
                {
                    "invitation_id": "inv-id",
                    "group_name": "Bali Trip",
                    "invited_by_name": "John",
                    "status": "pending",
                    "created_at": "2025-11-13T10:30:00Z",
                    "expires_at": "2025-11-20T10:30:00Z"
                }
            ]
        }
    """
    try:
        # logger.info("[Invitation] Get invitations request from %s (%s)", g.user_id, g.user_email)

        # Phase 4: Check cache first
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        
        cached_invitations = cache_ops.get_cached_user_invitations(g.user_id)
        if cached_invitations is not None:
            # logger.info("📦 Cache HIT: Returning %d cached invitations for %s", len(cached_invitations), g.user_email)
            return jsonify({'success': True, 'data': cached_invitations}), 200
        
        # logger.debug("📦 Cache MISS: Fetching invitations from Firestore for %s", g.user_email)

        # Get user invitations using service (both received and sent)
        invitations = invitation_service.get_user_invitations(g.user_email, g.user_id)

        # logger.info("✅ Retrieved %d invitations for %s", len(invitations), g.user_email)
        if invitations and logger.isEnabledFor(logging.DEBUG):
            for inv in invitations:
                # logger.debug('  - ID: %s | Email: %s | Group: %s', inv.get("invitation_id"), inv.get("invited_email"), inv.get("group_name"))

        # Phase 4: Cache the result
        cache_ops.cache_user_invitations(g.user_id, invitations)

        response = {
            'success': True,
            'data': invitations
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error("Error fetching invitations: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'GET_INVITATIONS_ERROR'
        }), 500


@group_planner_bp.route('/invitations/<invitation_id>/resend', methods=['POST'])
@verify_firebase_token
def resend_invitation(invitation_id):
    """
    Resend an existing pending invitation
    Updates timestamp and recalculates expiry
    
    Request:
        POST /api/group-planner/invitations/<invitation_id>/resend
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": {
                "invitation_id": "inv-id",
                "invited_email": "friend@example.com",
                "group_name": "Bali Trip",
                "status": "pending",
                "created_at": "2025-11-13T10:35:00Z",
                "expires_at": "2025-11-20T10:35:00Z"
            }
        }
    """
    try:
        # logger.info(f"[Invitation] Resend invitation request: {invitation_id}")

        # Resend invitation using service
        invitation = invitation_service.resend_invitation(invitation_id)

        # Send email via email service (using module-level instance)
        email_service.send_group_invitation(
            invited_email=invitation['invited_email'],
            inviter_name=invitation['invited_by_name'],
            group_name=invitation['group_name'],
            invitation_id=invitation_id
        )

        response = {
            'success': True,
            'data': invitation
        }

        # logger.info(f"✅ Invitation resent: {invitation_id} to {invitation['invited_email']}")
        return jsonify(response), 200

    except ValueError as e:
        logger.warning(f"[Invitation] Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'INVALID_RESEND_REQUEST'
        }), 400

    except Exception as e:
        logger.error(f"Error resending invitation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'RESEND_INVITATION_ERROR'
        }), 500



@group_planner_bp.route('/groups/<group_id>', methods=['GET'])
@verify_firebase_token
def get_group(group_id):
    """
    Phase 2: Get a specific group
    Phase 4: Added Redis caching for performance
    
    Request:
        GET /api/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": {...group data...}
        }
    """
    try:
        # Use firebase_operations for shared collection access
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # IMPORTANT: Always verify membership from database, not cache
        # Cache can be stale and cause permission issues
        # logger.debug("🔐 [GET_GROUP] Checking membership for user %s in group %s", g.user_id, group_id)
        is_member = firebase_ops.is_group_member(group_id, g.user_id)
        # logger.debug("🔐 [GET_GROUP] Membership check result: %s", is_member)
        
        if not is_member:
            logger.warning("🚫 [GET_GROUP] Access denied for user %s to group %s", g.user_id, group_id)
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Phase 4: Check cache AFTER permission check
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        
        cached_group = cache_ops.get_cached_group(group_id)
        if cached_group:
            # logger.debug("📦 Cache HIT: Returning cached group %s", group_id)
            return jsonify({'success': True, 'data': cached_group}), 200
        
        # logger.debug("📦 Cache MISS: Fetching group %s from Firestore", group_id)
        
        # Get group from shared collection
        group_data = firebase_ops.get_group(group_id)
        
        if not group_data:
            logger.warning("❌ [GET_GROUP] Group %s not found in Firestore", group_id)
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # Phase 4: Cache the result
        cache_ops.cache_group(group_id, group_data)
        
        response = {
            'success': True,
            'data': group_data
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error fetching group: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'GET_GROUP_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>', methods=['PUT'])
@verify_firebase_token
def update_group(group_id):
    """
    Phase 2: Update a group
    
    Request:
        PUT /api/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Updated Name",
            "destination": "Updated Destination"
        }
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        # Use firebase_operations for shared collection access
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        data = request.get_json()
        # Removed print statement
        
        # Verify user is a member
        if not firebase_ops.is_group_member(group_id, g.user_id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Update group in shared collection
        success = firebase_ops.update_group(group_id, data)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update group'}), 500
        
        # Phase 4: Invalidate group cache after update
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': data
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error updating group: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UPDATE_GROUP_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>', methods=['DELETE'])
@verify_firebase_token
def delete_group(group_id):
    """
    Phase 2: Delete a group
    
    Request:
        DELETE /api/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        # Use firebase_operations for shared collection access
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Delete group from shared collection (only creator can delete)
        success = firebase_ops.delete_group(group_id, g.user_id)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to delete group or access denied'}), 403
        
        # Phase 4: Invalidate caches after group deletion
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)  # Group cache
        cache_ops.invalidate_user_groups(g.user_id)  # Creator's groups cache
        
        response = {
            'success': True,
            'message': 'Group deleted successfully'
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error deleting group: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'DELETE_GROUP_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/members/<member_id>', methods=['DELETE'])
@verify_firebase_token
def remove_member(group_id, member_id):
    """
    Remove a member from a group
    
    Request:
        DELETE /api/group-planner/groups/<group_id>/members/<member_id>
        Headers: Authorization: Bearer <token>
    
    Only the group creator can remove members.
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .invitation_service import InvitationService
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Get group to check if requester is the creator
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        group_data = firebase_ops.get_group(group_id)
        creator_id = group_data.get('created_by')
        
        # Only the creator can remove members
        if g.user_id != creator_id:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Only the group creator can remove members'}), 403
        
        # Cannot remove yourself (creator)
        if member_id == g.user_id:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Creator cannot remove themselves'}), 400
        
        # Use invitation service to remove member
        invitation_service = InvitationService()
        success = invitation_service.remove_member_from_group(group_id, member_id, creator_id)
        
        if success:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': True, 'message': 'Member removed successfully'}), 200
        else:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Failed to remove member'}), 500
    
    except Exception as e:
        logger.error(f"❌ Error removing member: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'REMOVE_MEMBER_ERROR'
        }), 500


# =========================================================================
# PHASE 2C: POLL ENDPOINTS
# =========================================================================

@group_planner_bp.route('/groups/<group_id>/polls', methods=['POST'])
@verify_firebase_token
def create_poll(group_id):
    """
    Create a poll in a group
    
    Request:
        POST /api/group-planner/groups/<group_id>/polls
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "When should we go?",
            "options": ["Spring", "Summer", "Fall"]
        }
    
    Response:
        {
            "success": true,
            "data": {
                "poll_id": "poll-id",
                "name": "When should we go?",
                "options": ["Spring", "Summer", "Fall"],
                "votes": {},
                "voted_by": [],
                "created_by": "user-id",
                "created_at": "2025-11-13T10:30:00Z"
            }
        }
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        required_fields = ['name', 'options']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        poll_name = data.get('name')
        options = data.get('options')
        
        if not isinstance(options, list) or len(options) < 2:
            return jsonify({'success': False, 'error': 'Poll must have at least 2 options'}), 400
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Create poll data
        import uuid
        poll_id = str(uuid.uuid4())
        poll_data = {
            'id': poll_id,
            'name': poll_name,
            'options': options,
            'votes': {option: 0 for option in options},
            'votes_detail': {},  # {option: [user_ids]}
            'voted_by': [],
            'created_by': g.user_id,
            'created_at': __import__('datetime').datetime.utcnow().isoformat()
        }
        
        # Get current polls from shared group document
        group_data = firebase_ops.get_group(group_id)
        current_polls = group_data.get('polls', [])
        current_polls.append(poll_data)
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'polls': current_polls})
        
        # Phase 4: Invalidate group cache after adding poll
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': poll_data
        }
        
        # logger.info(f"✅ Poll created: {poll_id} in group {group_id}")
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"❌ Error creating poll: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CREATE_POLL_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/polls/<poll_id>/vote', methods=['POST'])
@verify_firebase_token
def vote_on_poll(group_id, poll_id):
    """
    Vote on a poll option
    
    Request:
        POST /api/group-planner/groups/<group_id>/polls/<poll_id>/vote
        Headers: Authorization: Bearer <token>
        Body: {
            "option": "Spring"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "poll_id": "poll-id",
                "votes": {"Spring": 2, "Summer": 1},
                "user_vote": "Spring"
            }
        }
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        option = data.get('option')
        
        if not option:
            return jsonify({'success': False, 'error': 'Missing option'}), 400
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the poll
        group_data = firebase_ops.get_group(group_id)
        polls = group_data.get('polls', [])
        poll_index = None
        poll_data = None
        for i, poll in enumerate(polls):
            if poll.get('id') == poll_id:
                poll_index = i
                poll_data = poll
                break
        
        if poll_data is None:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Poll not found'}), 404
        
        # Check if option is valid
        if option not in poll_data.get('options', []):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Invalid poll option'}), 400
        
        # Remove previous vote if exists
        votes = poll_data.get('votes', {})
        votes_detail = poll_data.get('votes_detail', {})
        voted_by = poll_data.get('voted_by', [])
        
        # Initialize votes_detail for all options if needed
        for opt in poll_data.get('options', []):
            if opt not in votes_detail:
                votes_detail[opt] = []
        
        # Remove user's previous vote
        for opt, voters in votes_detail.items():
            if g.user_id in voters:
                voters.remove(g.user_id)
                votes[opt] = max(0, votes.get(opt, 0) - 1)
        
        # Add new vote
        if option not in votes_detail:
            votes_detail[option] = []
        
        if g.user_id not in votes_detail[option]:
            votes_detail[option].append(g.user_id)
            votes[option] = votes.get(option, 0) + 1
        
        # Update voted_by list
        if g.user_id not in voted_by:
            voted_by.append(g.user_id)
        
        # Update poll data
        polls[poll_index]['votes'] = votes
        polls[poll_index]['votes_detail'] = votes_detail
        polls[poll_index]['voted_by'] = voted_by
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'polls': polls})
        
        # Phase 4: Invalidate group cache after voting on poll
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': {
                'poll_id': poll_id,
                'votes': votes,
                'user_vote': option
            }
        }
        
        # logger.info(f"✅ Vote recorded for poll {poll_id} by {g.user_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error voting on poll: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'VOTE_POLL_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/polls/<poll_id>', methods=['DELETE'])
@verify_firebase_token
def delete_poll(group_id, poll_id):
    """
    Delete a poll from a group
    
    Request:
        DELETE /api/group-planner/groups/<group_id>/polls/<poll_id>
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "message": "Poll deleted successfully"
        }
    """
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the poll to delete
        group_data = firebase_ops.get_group(group_id)
        polls = group_data.get('polls', [])
        poll_found = False
        updated_polls = []
        for poll in polls:
            if poll.get('id') == poll_id:
                # Check if user created the poll
                if poll.get('created_by') != g.user_id:
                    # Removed print statement
                    # Removed print statement
                    return jsonify({'success': False, 'error': 'Only the poll creator can delete it'}), 403
                poll_found = True
            else:
                updated_polls.append(poll)
        
        if not poll_found:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Poll not found'}), 404
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'polls': updated_polls})
        
        # Phase 4: Invalidate group cache after deleting poll
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'message': 'Poll deleted successfully'
        }
        
        # logger.info(f"✅ Poll deleted: {poll_id} from group {group_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error deleting poll: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'DELETE_POLL_ERROR'
        }), 500


# =========================================================================
# PHASE 2D: PLACE ENDPOINTS
# =========================================================================

@group_planner_bp.route('/groups/<group_id>/places', methods=['POST', 'OPTIONS'])
@verify_firebase_token
def add_place(group_id):
    """
    Add a place to the group's trip plan
    
    Request:
        POST /api/group-planner/groups/<group_id>/places
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Tokyo Tower"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "place_id": "place-id",
                "name": "Tokyo Tower",
                "votes": [],
                "remarks": "",
                "added_by": "user-id",
                "added_at": "2025-11-13T10:30:00Z"
            }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        place_name = data.get('name')
        
        if not place_name or not place_name.strip():
            return jsonify({'success': False, 'error': 'Missing place name'}), 400
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and check if place already exists (case-insensitive)
        group_data = firebase_ops.get_group(group_id)
        current_places = group_data.get('places', [])
        place_name_lower = place_name.strip().lower()
        for existing_place in current_places:
            if existing_place.get('name', '').lower() == place_name_lower:
                # Removed print statement
                # Removed print statement
                return jsonify({
                    'success': False,
                    'error': 'This place is already added to your list',
                    'code': 'PLACE_ALREADY_EXISTS'
                }), 409
        
        # Create place data
        import uuid
        place_id = str(uuid.uuid4())
        place_data = {
            'id': place_id,
            'name': place_name.strip(),
            'votes': [],
            'remarks': '',
            'added_by': g.user_id,
            'added_at': __import__('datetime').datetime.utcnow().isoformat()
        }
        
        # Add place to group's places array
        current_places.append(place_data)
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'places': current_places})
        
        # Phase 4: Invalidate group cache after adding place
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': place_data
        }
        
        # logger.info(f"✅ Place added: {place_id} to group {group_id}")
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"❌ Error adding place: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'ADD_PLACE_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/places/<place_id>/vote', methods=['POST', 'OPTIONS'])
@verify_firebase_token
def vote_on_place(group_id, place_id):
    """
    Vote on a place (toggle vote)
    
    Request:
        POST /api/group-planner/groups/<group_id>/places/<place_id>/vote
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "data": {
                "place_id": "place-id",
                "votes": ["user-id-1", "user-id-2"],
                "user_voted": true
            }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the place
        group_data = firebase_ops.get_group(group_id)
        places = group_data.get('places', [])
        place_index = None
        place_data = None
        for i, place in enumerate(places):
            if place.get('id') == place_id:
                place_index = i
                place_data = place
                break
        
        if place_data is None:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Place not found'}), 404
        
        # Toggle vote - handle both array and integer formats (legacy data)
        votes_data = place_data.get('votes', [])
        
        # Convert to array if it's an integer (old format)
        if isinstance(votes_data, int):
            votes = []
        elif isinstance(votes_data, list):
            votes = votes_data
        else:
            votes = []
        
        # Toggle vote
        if g.user_id in votes:
            votes.remove(g.user_id)
            user_voted = False
            action = 'removed'
        else:
            votes.append(g.user_id)
            user_voted = True
            action = 'added'
        
        # Update place data
        places[place_index]['votes'] = votes
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'places': places})
        
        # Phase 4: Invalidate group cache after voting on place
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': {
                'place_id': place_id,
                'votes': votes,
                'user_voted': user_voted
            }
        }
        
        # logger.info(f"✅ Vote {action} for place {place_id} by {g.user_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error voting on place: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'VOTE_PLACE_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/places/<place_id>', methods=['DELETE', 'OPTIONS'])
@verify_firebase_token
def delete_place(group_id, place_id):
    """
    Delete a place from the group
    
    Request:
        DELETE /api/group-planner/groups/<group_id>/places/<place_id>
        Headers: Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "message": "Place deleted successfully"
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the place to delete
        group_data = firebase_ops.get_group(group_id)
        places = group_data.get('places', [])
        place_found = False
        updated_places = []
        for place in places:
            if place.get('id') == place_id:
                place_found = True
            else:
                updated_places.append(place)
        
        if not place_found:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Place not found'}), 404
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'places': updated_places})
        
        # Phase 4: Invalidate group cache after deleting place
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'message': 'Place deleted successfully'
        }
        
        # logger.info(f"✅ Place deleted: {place_id} from group {group_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error deleting place: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'DELETE_PLACE_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/places/<place_id>/remarks', methods=['PUT', 'OPTIONS'])
@verify_firebase_token
def update_place_remarks(group_id, place_id):
    """
    Update remarks for a place
    
    Request:
        PUT /api/group-planner/groups/<group_id>/places/<place_id>/remarks
        Headers: Authorization: Bearer <token>
        Body: {
            "remarks": "Great place to visit in the morning!"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "place_id": "place-id",
                "remarks": "Great place to visit in the morning!"
            }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        remarks = data.get('remarks', '')
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the place
        group_data = firebase_ops.get_group(group_id)
        places = group_data.get('places', [])
        place_index = None
        place_data = None
        for i, place in enumerate(places):
            if place.get('id') == place_id:
                place_index = i
                place_data = place
                break
        
        if place_data is None:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Place not found'}), 404
        
        # Update remarks
        places[place_index]['remarks'] = remarks
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'places': places})
        
        # Phase 4: Invalidate group cache after updating remarks
        from .cache_operations import GroupPlannerCacheOperations
        cache_ops = GroupPlannerCacheOperations()
        cache_ops.invalidate_group(group_id)
        
        response = {
            'success': True,
            'data': {
                'place_id': place_id,
                'remarks': remarks
            }
        }
        
        # logger.info(f"✅ Remarks updated for place {place_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error updating remarks: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UPDATE_REMARKS_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/places/<place_id>', methods=['PATCH', 'OPTIONS'])
@verify_firebase_token
def update_place_details(group_id, place_id):
    """
    Update place details (date, duration, notes)
    
    Request:
        PATCH /api/group-planner/groups/<group_id>/places/<place_id>
        Headers: Authorization: Bearer <token>
        Body: {
            "visit_date": "2025-12-15",
            "suggested_duration": "2 hours",
            "remarks": "Great place!"
        }
    
    Response:
        {
            "success": true,
            "data": { updated place object }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the place
        group_data = firebase_ops.get_group(group_id)
        places = group_data.get('places', [])
        place_index = None
        place_data = None
        for i, place in enumerate(places):
            if place.get('id') == place_id:
                place_index = i
                place_data = place
                break
        
        if place_data is None:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Place not found'}), 404
        
        # Update place fields
        if 'visit_date' in data:
            places[place_index]['visit_date'] = data['visit_date']
        if 'suggested_duration' in data:
            places[place_index]['suggested_duration'] = data['suggested_duration']
        if 'remarks' in data:
            places[place_index]['remarks'] = data['remarks']
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'places': places})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
            # Removed print statement
        except Exception as e:
            pass
        
        response = {
            'success': True,
            'data': places[place_index]
        }
        
        # logger.info(f"✅ Place details updated for {place_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error updating place details: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UPDATE_PLACE_DETAILS_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/itinerary-document', methods=['PUT', 'OPTIONS'])
@verify_firebase_token
def update_itinerary_document(group_id):
    """
    Update itinerary document content
    
    Request:
        PUT /api/group-planner/groups/<group_id>/itinerary-document
        Headers: Authorization: Bearer <token>
        Body: {
            "content": "Trip overview and details..."
        }
    
    Response:
        {
            "success": true,
            "data": {
                "group_id": "group-id",
                "updated": true
            }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        content = data.get('content', '')
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Update the shared group document with itinerary content (single write for all members)
        firebase_ops.update_group(group_id, {'itinerary_document': content})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
            # Removed print statement
        except Exception as e:
            pass
        
        response = {
            'success': True,
            'data': {
                'group_id': group_id,
                'updated': True
            }
        }
        
        # logger.info(f"✅ Itinerary document updated for group {group_id}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"❌ Error updating itinerary document: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UPDATE_ITINERARY_DOCUMENT_ERROR'
        }), 500


@group_planner_bp.route('/geocode', methods=['POST', 'OPTIONS'])
def geocode_place():
    """
    Proxy geocoding requests to avoid CORS issues
    
    Request:
        POST /api/group-planner/geocode
        Body: {"place_name": "Tokyo Tower"}
    
    Response:
        {
            "success": true,
            "data": {
                "lat": 35.6585805,
                "lon": 139.7454329,
                "display_name": "Tokyo Tower, ..."
            }
        }
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        import requests
        from time import sleep
        
        data = request.get_json()
        place_name = data.get('place_name', '').strip()
        
        if not place_name:
            return jsonify({
                'success': False,
                'error': 'Place name is required'
            }), 400
        
        # Call Nominatim API with proper headers
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'format': 'json',
                'q': place_name,
                'limit': 1,
                'accept-language': 'en'
            },
            headers={
                'User-Agent': 'TripRaft/1.0 (contact@tripraft.com)'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                result = results[0]
                return jsonify({
                    'success': True,
                    'data': {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result['display_name']
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'No results found'
                }), 404
        else:
            logger.error(f"Nominatim API error: {response.status_code}")
            return jsonify({
                'success': False,
                'error': f'Geocoding service error: {response.status_code}'
            }), response.status_code
    
    except Exception as e:
        logger.error(f"Error geocoding place: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =========================================================================
# CHECKLIST OPERATIONS
# =========================================================================

@group_planner_bp.route('/groups/<group_id>/checklist', methods=['POST', 'OPTIONS'])
@verify_firebase_token
def add_checklist_item(group_id):
    """
    Add item to group checklist
    
    Request:
        POST /api/group-planner/groups/<group_id>/checklist
        Headers: Authorization: Bearer <token>
        Body: {"item": "Pack sunscreen"}
    
    Response:
        {"success": true, "data": {"id": "...", "item": "...", "completed": false, ...}}
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        item_text = data.get('item', '').strip()
        
        if not item_text:
            return jsonify({'success': False, 'error': 'Item text is required'}), 400
        
        from firebase_admin import firestore
        import uuid
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and create new checklist item
        group_data = firebase_ops.get_group(group_id)
        checklist = group_data.get('checklist', [])
        new_item = {
            'id': str(uuid.uuid4()),
            'item': item_text,
            'completed': False,
            'authorId': g.user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        checklist.append(new_item)
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'checklist': checklist})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
        except:
            pass
        
        return jsonify({
            'success': True,
            'data': new_item
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error adding checklist item: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'ADD_CHECKLIST_ITEM_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/checklist/<item_id>/toggle', methods=['PATCH', 'OPTIONS'])
@verify_firebase_token
def toggle_checklist_item(group_id, item_id):
    """
    Toggle checklist item completion status
    
    Request:
        PATCH /api/group-planner/groups/<group_id>/checklist/<item_id>/toggle
        Headers: Authorization: Bearer <token>
    
    Response:
        {"success": true, "data": {"completed": true}}
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and find the item to toggle
        group_data = firebase_ops.get_group(group_id)
        checklist = group_data.get('checklist', [])
        item_found = False
        for item in checklist:
            if item.get('id') == item_id:
                item['completed'] = not item.get('completed', False)
                item_found = True
                break
        
        if not item_found:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Checklist item not found'}), 404
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'checklist': checklist})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
        except:
            pass
        
        return jsonify({
            'success': True,
            'data': {'id': item_id, 'completed': item['completed']}
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error toggling checklist item: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'TOGGLE_CHECKLIST_ITEM_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/budget', methods=['PATCH', 'OPTIONS'])
@verify_firebase_token
def update_budget(group_id):
    """
    Update group estimated budget
    
    Request:
        PATCH /api/group-planner/groups/<group_id>/budget
        Headers: Authorization: Bearer <token>
        Body: {"estimated_budget": 5000}
    
    Response:
        {"success": true, "data": {"estimated_budget": 5000}}
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        data = request.get_json()
        estimated_budget = data.get('estimated_budget')
        
        if estimated_budget is None:
            return jsonify({'success': False, 'error': 'estimated_budget is required'}), 400
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'estimated_budget': estimated_budget})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
        except:
            pass
        
        return jsonify({
            'success': True,
            'data': {'estimated_budget': estimated_budget}
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error updating budget: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UPDATE_BUDGET_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/link-expense', methods=['POST', 'OPTIONS'])
def link_expense_group(group_id):
    """
    Link group planner group to expense engine
    Creates expense group with same name and members
    
    Request:
        POST /api/group-planner/groups/<group_id>/link-expense
    
    Response:
        {"success": true, "data": {"expense_group_id": "uuid"}}
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    # Verify token for POST requests
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401
    
    try:
        decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=60)
        g.user_id = decoded_token['uid']
    except Exception as e:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401
    
    try:
        # logger.info("🔗 [LINK_EXPENSE] Linking group %s to expense engine", group_id)
        
        # Phase 1 Migration: Get group from travel_groups collection
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Verify user is a member
        if not firebase_ops.is_group_member(group_id, g.user_id):
            logger.warning("🚫 [LINK_EXPENSE] Access denied for user %s to group %s", g.user_id, group_id)
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get group details from travel_groups collection
        group_data = firebase_ops.get_group(group_id)
        if not group_data:
            logger.warning("❌ [LINK_EXPENSE] Group %s not found", group_id)
            return jsonify({
                'success': False,
                'error': 'Group not found',
                'code': 'GROUP_NOT_FOUND'
            }), 404
        
        # Check if already linked
        if group_data.get('expense_group_id'):
            # logger.info("✅ [LINK_EXPENSE] Group %s already linked to expense group %s", group_id, group_data['expense_group_id'])
            return jsonify({
                'success': True,
                'data': {'expense_group_id': group_data['expense_group_id']},
                'message': 'Already linked to expense group'
            }), 200
        
        # Import expense service
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from expense_engine.service import expense_service
        from expense_engine.firebase_operations import ExpenseDatabaseOperations
        
        expense_db = ExpenseDatabaseOperations()
        
        # Create expense group
        expense_group = expense_service.create_group(
            name=group_data['name'],
            created_by=g.user_id,
            description=f"Linked from Group Planner",
            currency='USD'
        )
        
        expense_group_id = expense_group['group_id']
        # logger.info("✅ [LINK_EXPENSE] Created expense group: %s", expense_group_id)
        
        # Get members from group_members collection (more reliable than group document)
        try:
            members_list = firebase_ops.get_group_members(group_id)
            members = [m.get('user_id') for m in members_list if m.get('user_id')]
            # logger.info("🔗 [LINK_EXPENSE] Fetched %d members from group_members collection: %s", len(members), members)
        except Exception as member_err:
            logger.warning("⚠️ [LINK_EXPENSE] Failed to get members from collection, using group document: %s", member_err)
            members = group_data.get('members', [])
            # logger.info("🔗 [LINK_EXPENSE] Using %d members from group document: %s", len(members), members)
        
        for member_id in members:
            if member_id != g.user_id:  # Creator already added
                try:
                    expense_db.add_member_to_group(expense_group_id, member_id, role='member')
                    # logger.info("✅ [LINK_EXPENSE] Added member %s to expense group", member_id)
                except Exception as e:
                    logger.error("❌ [LINK_EXPENSE] Failed to add member %s: %s", member_id, e)
        
        # Verify all members were added and have balances initialized
        try:
            from firebase_admin import firestore as admin_firestore
            db = admin_firestore.client()
            balance_doc = db.collection('group_balances').document(expense_group_id).get()
            if balance_doc.exists:
                balance_data = balance_doc.to_dict()
                member_balances = balance_data.get('member_balances', {})
                # logger.info("✅ [LINK_EXPENSE] Balance document has %d members: %s", len(member_balances), list(member_balances.keys()))
            else:
                logger.warning("⚠️ [LINK_EXPENSE] Balance document doesn't exist yet")
        except Exception as verify_err:
            logger.warning("⚠️ [LINK_EXPENSE] Could not verify balances: %s", verify_err)
        
        # Phase 1 Migration: Store expense_group_id in travel_groups collection
        firebase_ops.update_group(group_id, {'expense_group_id': expense_group_id})
        # logger.info("✅ [LINK_EXPENSE] Updated group %s with expense_group_id", group_id)
        
        # Phase 4: Invalidate cache after linking expense group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
            cache_ops.invalidate_user_groups(g.user_id)
            # logger.info("✅ [LINK_EXPENSE] Invalidated Group Planner cache")
        except Exception as e:
            logger.error(f"⚠️ [LINK_EXPENSE] Failed to invalidate Group Planner cache: {e}")
        
        # CRITICAL: Also invalidate expense engine cache so new group shows instantly
        try:
            from expense_engine.cache_operations import ExpenseCacheOperations
            expense_cache = ExpenseCacheOperations()
            
            # IMPORTANT: ExpenseService uses direct keys without prefixes!
            # We need to manually delete the correct keys
            if expense_cache._is_available():
                # Invalidate user groups cache for all members (using service's key format)
                all_members = [g.user_id] + [m for m in members if m != g.user_id]
                for member_id in all_members:
                    # ExpenseService uses "user_groups:{user_id}" NOT "expense:user_groups:{user_id}"
                    cache_key = f"user_groups:{member_id}"
                    expense_cache.redis_client.delete(cache_key)
                
                # Also invalidate group details cache (using service's key format)
                group_cache_key = f"group_details:{expense_group_id}"
                expense_cache.redis_client.delete(group_cache_key)
                
                # logger.info("✅ [LINK_EXPENSE] Invalidated Expense Engine cache for %d members", len(all_members))
            else:
                logger.warning("⚠️ [LINK_EXPENSE] Redis not available, skipping cache invalidation")
        except Exception as e:
            logger.error(f"⚠️ [LINK_EXPENSE] Failed to invalidate Expense Engine cache: {e}")
        
        return jsonify({
            'success': True,
            'data': {'expense_group_id': expense_group_id}
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error linking expense group: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'LINK_EXPENSE_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/unlink-expense', methods=['POST', 'OPTIONS'])
def unlink_expense_group(group_id):
    """
    Unlink and delete expense group from Group Planner group
    
    Request:
        POST /api/group-planner/groups/<group_id>/unlink-expense
    
    Response:
        {"success": true, "message": "Expense group unlinked and deleted"}
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    # Verify token for POST requests
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401
    
    try:
        decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=60)
        g.user_id = decoded_token['uid']
    except Exception as e:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401
    
    try:
        # logger.info("🔓 [UNLINK_EXPENSE] Unlinking group %s from expense engine", group_id)
        
        # Get group from travel_groups collection
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Verify user is a member
        if not firebase_ops.is_group_member(group_id, g.user_id):
            logger.warning("🚫 [UNLINK_EXPENSE] Access denied for user %s to group %s", g.user_id, group_id)
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get group details
        group_data = firebase_ops.get_group(group_id)
        if not group_data:
            logger.warning("❌ [UNLINK_EXPENSE] Group %s not found", group_id)
            return jsonify({
                'success': False,
                'error': 'Group not found',
                'code': 'GROUP_NOT_FOUND'
            }), 404
        
        # Check if group is linked
        expense_group_id = group_data.get('expense_group_id')
        if not expense_group_id:
            # logger.info("⚠️ [UNLINK_EXPENSE] Group %s is not linked to any expense group", group_id)
            return jsonify({
                'success': True,
                'message': 'Group is not linked to any expense group'
            }), 200
        
        # Import expense service
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from expense_engine.service import expense_service
        
        # Delete expense group and update travel_groups in parallel for better performance
        from concurrent.futures import ThreadPoolExecutor
        
        delete_success = False
        update_success = False
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Execute both operations in parallel
            delete_future = executor.submit(
                expense_service.delete_group, 
                expense_group_id, 
                cascade_delete_expenses=True
            )
            update_future = executor.submit(
                firebase_ops.update_group, 
                group_id, 
                {'expense_group_id': None}
            )
            
            # Wait for both to complete
            try:
                delete_success = delete_future.result(timeout=3)
                # logger.info("✅ [UNLINK_EXPENSE] Deleted expense group %s", expense_group_id)
            except Exception as delete_err:
                logger.error("❌ [UNLINK_EXPENSE] Error deleting expense group: %s", delete_err)
            
            try:
                update_future.result(timeout=1)
                update_success = True
                # logger.info("✅ [UNLINK_EXPENSE] Removed expense_group_id from group %s", group_id)
            except Exception as update_err:
                logger.error("❌ [UNLINK_EXPENSE] Error updating group: %s", update_err)
        
        # Batch invalidate both caches for better performance
        try:
            from .cache_operations import GroupPlannerCacheOperations
            from expense_engine.cache_operations import ExpenseCacheOperations
            
            cache_ops = GroupPlannerCacheOperations()
            expense_cache = ExpenseCacheOperations()
            
            # Batch all cache deletions
            if expense_cache._is_available():
                cache_keys = [
                    f"user_groups:{g.user_id}",
                    f"group_details:{expense_group_id}"
                ]
                expense_cache.redis_client.delete(*cache_keys)
            
            # Invalidate GP cache
            cache_ops.invalidate_group(group_id)
            cache_ops.invalidate_user_groups(g.user_id)
            
            # logger.info("✅ [UNLINK_EXPENSE] Invalidated all caches")
        except Exception as e:
            logger.error(f"⚠️ [UNLINK_EXPENSE] Failed to invalidate cache: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Expense group unlinked and deleted successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error unlinking expense group: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'UNLINK_EXPENSE_ERROR'
        }), 500


@group_planner_bp.route('/groups/<group_id>/checklist/<item_id>', methods=['DELETE', 'OPTIONS'])
@verify_firebase_token
def delete_checklist_item(group_id, item_id):
    """
    Delete checklist item
    
    Request:
        DELETE /api/group-planner/groups/<group_id>/checklist/<item_id>
        Headers: Authorization: Bearer <token>
    
    Response:
        {"success": true}
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        # Removed print statement
        
        from firebase_admin import firestore
        db = firestore.client()
        from .firebase_operations import GroupPlannerFirebaseOperations
        
        firebase_ops = GroupPlannerFirebaseOperations()
        
        # Check if user is a member of the group
        if not firebase_ops.is_group_member(group_id, g.user_id):
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        # Get group data and remove the item
        group_data = firebase_ops.get_group(group_id)
        checklist = group_data.get('checklist', [])
        initial_length = len(checklist)
        checklist = [item for item in checklist if item.get('id') != item_id]
        
        if len(checklist) == initial_length:
            # Removed print statement
            # Removed print statement
            return jsonify({'success': False, 'error': 'Checklist item not found'}), 404
        
        # Update the shared group document (single write for all members)
        firebase_ops.update_group(group_id, {'checklist': checklist})
        
        # Invalidate cache for the group
        try:
            from .cache_operations import GroupPlannerCacheOperations
            cache_ops = GroupPlannerCacheOperations()
            cache_ops.invalidate_group(group_id)
        except:
            pass
        
        return jsonify({
            'success': True
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error deleting checklist item: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'DELETE_CHECKLIST_ITEM_ERROR'
        }), 500

