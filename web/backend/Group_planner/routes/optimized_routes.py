"""
Group Planner Phase 20 Optimized Routes
Target: 10 total Firestore operations per session
"""

from flask import Blueprint, request, jsonify
import logging
from functools import wraps

from firebase_admin import auth

try:
    from Group_planner.repositories.trip_dashboard_repository import TripDashboardRepository
    from Group_planner.services.batched_write_service import GroupPlannerBatchedService
    from Group_planner.services.places_integration import PlacesIntegrationService
except ImportError:
    TripDashboardRepository = None
    GroupPlannerBatchedService = None
    PlacesIntegrationService = None

logger = logging.getLogger(__name__)

# Create blueprint
group_planner_v2 = Blueprint('group_planner_v2', __name__)


def verify_token():
    """Verify Firebase token and return user info."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split('Bearer ')[1]
    try:
        decoded = auth.verify_id_token(token)
        return {
            'user_id': decoded.get('uid'),
            'email': decoded.get('email', ''),
            'display_name': decoded.get('name', decoded.get('email', 'Unknown'))
        }
    except Exception as e:
        logger.error("Token verification failed: %s", e)
        return None


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = verify_token()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated


# ============================================================
# DASHBOARD ENDPOINT - 1 READ for EVERYTHING
# ============================================================

@group_planner_v2.route('/dashboard', methods=['GET'])
@require_auth
def get_full_dashboard():
    """
    Get COMPLETE dashboard in 1 Firestore read.
    
    Returns:
    - All groups (with members, places, polls)
    - All pending invitations
    - Cached places for destinations
    
    Firestore: 1 READ
    """
    try:
        user_id = request.user['user_id']
        
        repo = TripDashboardRepository()
        dashboard = repo.get_full_dashboard(user_id)
        
        if not dashboard:
            # First time user - initialize empty dashboard
            dashboard = repo.get_or_create_dashboard(user_id)
        
        logger.info("[V2] Dashboard loaded for %s - 1 READ", user_id)
        
        return jsonify({
            'success': True,
            'data': dashboard,
            'operations': {'reads': 1, 'writes': 0}
        })
    
    except Exception as e:
        logger.error("Dashboard error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/dashboard/initialize', methods=['POST'])
@require_auth
def initialize_dashboard():
    """
    Initialize or refresh dashboard from existing data.
    Use this once during migration or first login.
    
    This may use more operations but is only called once.
    """
    try:
        user_id = request.user['user_id']
        
        repo = TripDashboardRepository()
        dashboard = repo.build_dashboard_from_existing(user_id)
        
        logger.info("[V2] Dashboard initialized for %s", user_id)
        
        return jsonify({
            'success': True,
            'data': dashboard,
            'message': 'Dashboard initialized from existing data'
        })
    
    except Exception as e:
        logger.error("Dashboard init error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# GROUP ENDPOINTS - 1 WRITE each
# ============================================================

@group_planner_v2.route('/groups', methods=['POST'])
@require_auth
def create_group():
    """
    Create trip group with SINGLE batch write.
    
    Firestore: 1 WRITE (batch)
    """
    try:
        user = request.user
        data = request.get_json()
        
        service = GroupPlannerBatchedService()
        result = service.create_group_batched(
            name=data.get('name'),
            created_by=user['user_id'],
            creator_display_name=user['display_name'],
            creator_email=user.get('email', ''),
            destination=data.get('destination', ''),
            destination_coordinates=data.get('destinationCoordinates'),
            trip_dates=data.get('tripDates'),
            budget_range=data.get('budgetRange'),
            description=data.get('description', '')
        )
        
        logger.info("[V2] Group created: %s - 1 WRITE", result['group_id'])
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 0, 'writes': 1}
        }), 201
    
    except Exception as e:
        logger.error("Create group error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/groups/<group_id>', methods=['PUT'])
@require_auth
def update_group(group_id: str):
    """
    Update group details with SINGLE write.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        data = request.get_json()
        
        repo = TripDashboardRepository()
        repo.update_group_in_dashboard(
            user_id=user['user_id'],
            group_id=group_id,
            updates={
                'name': data.get('name'),
                'destination': data.get('destination'),
                'destinationCoordinates': data.get('destinationCoordinates'),
                'tripDates': data.get('tripDates'),
                'budgetRange': data.get('budgetRange'),
                'description': data.get('description')
            }
        )
        
        logger.info("[V2] Group updated: %s - 1 WRITE", group_id)
        
        return jsonify({
            'success': True,
            'message': 'Group updated',
            'operations': {'reads': 0, 'writes': 1}
        })
    
    except Exception as e:
        logger.error("Update group error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# INVITATION ENDPOINTS - 1 WRITE each
# ============================================================

@group_planner_v2.route('/invitations', methods=['POST'])
@require_auth
def send_invitation():
    """
    Send invitation with SINGLE write.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        data = request.get_json()
        
        service = GroupPlannerBatchedService()
        result = service.send_invitation_batched(
            group_id=data.get('groupId'),
            group_name=data.get('groupName'),
            destination=data.get('destination', ''),
            inviter_id=user['user_id'],
            inviter_name=user['display_name'],
            invitee_email=data.get('inviteeEmail'),
            invitee_user_id=data.get('inviteeUserId')
        )
        
        logger.info("[V2] Invitation sent: %s - 1 WRITE", result['invitation_id'])
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 0, 'writes': 1}
        }), 201
    
    except Exception as e:
        logger.error("Send invitation error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/invitations/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id: str):
    """
    Accept invitation with SINGLE batch write.
    
    Firestore: 1 WRITE (batch of 3 updates)
    """
    try:
        user = request.user
        data = request.get_json() or {}
        
        # Invitation data should come from frontend (from cached dashboard)
        invitation_data = {
            'group_id': data.get('groupId'),
            'group_name': data.get('groupName'),
            'destination': data.get('destination'),
            'created_by': data.get('createdBy'),
            'member_count': data.get('memberCount', 1),
            'existing_members': data.get('existingMembers', [])
        }
        
        service = GroupPlannerBatchedService()
        result = service.accept_invitation_batched(
            invitation_id=invitation_id,
            invitation_data=invitation_data,
            accepter_id=user['user_id'],
            accepter_display_name=user['display_name'],
            accepter_email=user.get('email', '')
        )
        
        logger.info("[V2] Invitation accepted: %s - 1 WRITE", invitation_id)
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 0, 'writes': 1}
        })
    
    except Exception as e:
        logger.error("Accept invitation error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/invitations/<invitation_id>/decline', methods=['POST'])
@require_auth
def decline_invitation(invitation_id: str):
    """
    Decline invitation with SINGLE write.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        
        repo = TripDashboardRepository()
        repo.decline_invitation(user['user_id'], invitation_id)
        
        logger.info("[V2] Invitation declined: %s - 1 WRITE", invitation_id)
        
        return jsonify({
            'success': True,
            'message': 'Invitation declined',
            'operations': {'reads': 0, 'writes': 1}
        })
    
    except Exception as e:
        logger.error("Decline invitation error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# PLACES ENDPOINTS - 0 READS (cached) or 1 READ
# ============================================================

@group_planner_v2.route('/places/search', methods=['GET'])
@require_auth
def search_places():
    """
    Search places for destination.
    
    First call: 1 READ + cache for 24 hours
    Subsequent: 0 READS (from Redis)
    """
    try:
        destination = request.args.get('destination', '')
        category = request.args.get('category')
        
        if not destination:
            return jsonify({'error': 'Destination required'}), 400
        
        service = PlacesIntegrationService()
        result = service.get_places_for_destination(
            destination=destination,
            category=category
        )
        
        from_cache = result.get('from_cache', False)
        ops = 0 if from_cache else 1
        
        logger.info("[V2] Places search for %s - %d READ", destination, ops)
        
        return jsonify({
            'success': True,
            'data': result.get('places', []),
            'coordinates': result.get('coordinates'),
            'from_cache': from_cache,
            'operations': {'reads': ops, 'writes': 0}
        })
    
    except Exception as e:
        logger.error("Places search error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/places/nearby', methods=['GET'])
@require_auth
def nearby_places():
    """
    Get nearby places from coordinates.
    
    First call: 1 READ + cache for 24 hours
    Subsequent: 0 READS (from Redis)
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 10, type=float)
        category = request.args.get('category')
        
        if lat is None or lng is None:
            return jsonify({'error': 'Coordinates required'}), 400
        
        service = PlacesIntegrationService()
        result = service.get_places_near_coordinates(
            lat=lat,
            lng=lng,
            radius_km=radius,
            category=category
        )
        
        from_cache = result.get('from_cache', False)
        ops = 0 if from_cache else 1
        
        logger.info("[V2] Nearby places at (%.4f, %.4f) - %d READ", lat, lng, ops)
        
        return jsonify({
            'success': True,
            'data': result.get('places', []),
            'from_cache': from_cache,
            'operations': {'reads': ops, 'writes': 0}
        })
    
    except Exception as e:
        logger.error("Nearby places error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/groups/<group_id>/places', methods=['POST'])
@require_auth
def add_place_to_group(group_id: str):
    """
    Add place to trip group with SINGLE write.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        data = request.get_json()
        
        service = GroupPlannerBatchedService()
        result = service.add_place_batched(
            group_id=group_id,
            place_data={
                'id': data.get('placeId'),
                'name': data.get('name'),
                'coordinates': data.get('coordinates'),
                'category': data.get('category', 'attraction'),
                'notes': data.get('notes', ''),
                'photos': data.get('photos')
            },
            added_by=user['user_id'],
            group_members=data.get('groupMembers', [user['user_id']])
        )
        
        logger.info("[V2] Place added: %s - 1 WRITE", result['place_id'])
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 0, 'writes': 1}
        }), 201
    
    except Exception as e:
        logger.error("Add place error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# POLL ENDPOINTS - 1 WRITE each
# ============================================================

@group_planner_v2.route('/groups/<group_id>/polls', methods=['POST'])
@require_auth
def create_poll(group_id: str):
    """
    Create poll with SINGLE write.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        data = request.get_json()
        
        service = GroupPlannerBatchedService()
        result = service.create_poll_batched(
            group_id=group_id,
            question=data.get('question'),
            options=data.get('options', []),
            created_by=user['user_id'],
            group_members=data.get('groupMembers', [user['user_id']])
        )
        
        logger.info("[V2] Poll created: %s - 1 WRITE", result['poll_id'])
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 0, 'writes': 1}
        }), 201
    
    except Exception as e:
        logger.error("Create poll error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/polls/<poll_id>/vote', methods=['POST'])
@require_auth
def vote_on_poll(poll_id: str):
    """
    Vote on poll.
    
    Firestore: 1 READ + 1 WRITE
    Note: This requires a read to get current votes
    """
    try:
        user = request.user
        data = request.get_json()
        
        service = GroupPlannerBatchedService()
        result = service.vote_on_poll_batched(
            poll_id=poll_id,
            group_id=data.get('groupId'),
            option_id=data.get('optionId'),
            voter_id=user['user_id']
        )
        
        logger.info("[V2] Vote recorded: %s - 1 READ + 1 WRITE", poll_id)
        
        return jsonify({
            'success': True,
            'data': result,
            'operations': {'reads': 1, 'writes': 1}
        })
    
    except Exception as e:
        logger.error("Vote error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# UTILITY ENDPOINTS
# ============================================================

@group_planner_v2.route('/sync', methods=['POST'])
@require_auth
def sync_from_frontend():
    """
    Sync optimistic updates from frontend to dashboard.
    
    Frontend can batch multiple changes and sync periodically.
    This reduces writes by batching UI changes.
    
    Firestore: 1 WRITE
    """
    try:
        user = request.user
        data = request.get_json()
        
        repo = TripDashboardRepository()
        repo.sync_dashboard_updates(
            user_id=user['user_id'],
            updates=data.get('updates', {})
        )
        
        logger.info("[V2] Dashboard synced for %s - 1 WRITE", user['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'Dashboard synced',
            'operations': {'reads': 0, 'writes': 1}
        })
    
    except Exception as e:
        logger.error("Sync error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - no auth required."""
    return jsonify({
        'status': 'healthy',
        'version': '2.0',
        'optimization': 'Phase 20 - 10 ops target'
    })
