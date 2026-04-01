"""
Group Planner SQL-Only Routes
Pure SQL backend - NO FIREBASE

Destination/Places endpoints for group planning
Uses shared_db unified authentication
"""

import logging

from app.api.utils.responses import error_response, success_response
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth
from app.infrastructure.cache.redis import cache_response
from flask import Blueprint, after_this_request, g, request

logger = logging.getLogger(__name__)


def _set_deprecation(response):
    """Add standard deprecation headers per RFC 8594."""
    response.headers['Deprecation'] = 'true'
    response.headers['Sunset'] = Config.API_SUNSET_DATE
    response.headers['Link'] = '</api/v1/place-search/search>; rel="successor-version"'
    return response


# Create blueprint for v1 API (consistent with other Group Planner blueprints)
group_planner_v2 = Blueprint('group_planner_v2', __name__, url_prefix='/api/v1/group-planner')

# Alias for backward compatibility
group_planner_bp = group_planner_v2


# ============================================================
# HEALTH CHECK - No auth required
# ============================================================

@group_planner_v2.route('/health', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
def health_check():
    """Health check endpoint - no auth required."""
    return success_response(data={
        'status': 'healthy',
        'version': '3.0',
        'backend': 'SQL',
        'firebase': 'disabled'
    })


# ============================================================
# AUTHENTICATION VERIFICATION
# ============================================================

@group_planner_v2.route('/auth/verify', methods=['POST'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
def verify_auth():
    """
    Verify user authentication.
    Returns user info from JWT token.
    """
    return success_response(data={
        'user_id': g.user_id,
        'email': g.user_email,
        'display_name': g.current_user.get('name', '')
    }, message='Token valid')


# ============================================================
# DESTINATION SEARCH ENDPOINTS
# ============================================================

@group_planner_v2.route('/destinations/autocomplete', methods=['GET'])
@limit_api(Config.RATE_LIMITS['search'])
@cache_response(key_prefix='gp_dest:autocomplete', ttl=Config.CACHE_TTLS['search'])
def autocomplete_destinations():
    """DEPRECATED — Use /api/v1/place-search/search instead."""
    after_this_request(lambda resp: _set_deprecation(resp))
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return success_response(data=[], message='Query too short')
        
        limit = min(int(request.args.get('limit', 10)), 20)
        
        # Direct query using TravelDatabase
        try:
            from app.infrastructure.db.travel_db import travel_db

            results = []
            query_lower = query.lower()
            query_pattern = f'%{query_lower}%'
            
            with travel_db.get_connection() as conn:
                cursor = conn.cursor()
            
                # Search cities
                cursor.execute("""
                    SELECT c.id, c.city_name as name, c.latitude, c.longitude,
                           s.state_name, co.country_name
                    FROM cities c
                    LEFT JOIN states s ON c.state_id = s.id
                    LEFT JOIN countries co ON s.country_id = co.id
                    WHERE c.city_name LIKE ? COLLATE NOCASE
                    LIMIT ?
                """, (query_pattern, limit))
                
                for row in cursor.fetchall():
                    # Build display name, avoiding duplicate city/state names
                    display = row['name']
                    if row['state_name'] and row['state_name'].lower() != row['name'].lower():
                        display += f", {row['state_name']}"
                    if row['country_name']:
                        display += f", {row['country_name']}"
                        
                    results.append({
                        'id': row['id'],
                        'name': row['name'],
                        'display_name': display,
                        'type': 'city',
                        'lat': row['latitude'],
                        'lng': row['longitude'],
                        'country': row['country_name']
                    })
                
                # Search states if we have room
                if len(results) < limit:
                    remaining = limit - len(results)
                    cursor.execute("""
                        SELECT s.id, s.state_name as name, s.latitude, s.longitude,
                               co.country_name
                        FROM states s
                        LEFT JOIN countries co ON s.country_id = co.id
                        WHERE s.state_name LIKE ? COLLATE NOCASE
                        LIMIT ?
                    """, (query_pattern, remaining))
                    
                    for row in cursor.fetchall():
                        display = row['name']
                        if row['country_name']:
                            display += f", {row['country_name']}"
                            
                        results.append({
                            'id': row['id'],
                            'name': row['name'],
                            'display_name': display,
                            'type': 'state',
                            'lat': row['latitude'],
                            'lng': row['longitude'],
                            'country': row['country_name']
                        })
                
                # Search countries if we have room
                if len(results) < limit:
                    remaining = limit - len(results)
                    cursor.execute("""
                        SELECT co.id, co.country_name as name,
                               (SELECT c.latitude FROM cities c 
                                JOIN states s ON c.state_id = s.id 
                                WHERE s.country_id = co.id LIMIT 1) as latitude,
                               (SELECT c.longitude FROM cities c 
                                JOIN states s ON c.state_id = s.id 
                                WHERE s.country_id = co.id LIMIT 1) as longitude
                        FROM countries co
                        WHERE co.country_name LIKE ? COLLATE NOCASE
                        LIMIT ?
                    """, (query_pattern, remaining))
                    
                    for row in cursor.fetchall():
                        results.append({
                            'id': row['id'],
                            'name': row['name'],
                            'display_name': row['name'],
                            'type': 'country',
                            'lat': row['latitude'] or 0,
                            'lng': row['longitude'] or 0,
                            'country': row['name']
                        })
            
            return success_response(data=results)
            
        except Exception as e:
            logger.exception("SQLite autocomplete error: %s", e)
        
        return success_response(data=[], message='Search service not available')
    
    except Exception as e:
        logger.error("Autocomplete error: %s", e)
        return error_response(str(e), 500)


@group_planner_v2.route('/destinations/<destination>/places', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@cache_response(key_prefix='gp_dest:places', ttl=Config.CACHE_TTLS['autocomplete'])
def get_destination_places(destination: str):
    """
    Get places for a destination.
    Uses local database for place data.
    """
    try:
        category = request.args.get('category', 'all')
        limit = min(int(request.args.get('limit', Config.GP_DEFAULT_LIMIT)), 100)
        
        try:
            from app.services.destination_service import PlacesService
            service = PlacesService()
            result = service.get_destination_places(
                destination=destination,
                category=category,
                limit=limit
            )
            
            return success_response(data={
                'count': result.get('count', 0),
                'attractions': result.get('attractions', 0),
                'restaurants': result.get('restaurants', 0),
                'places': result.get('places', []),
                'coordinates': result.get('coordinates', None)
            })
        except Exception as e:
            logger.warning("PlacesService not available: %s", e)
        
        return success_response(data={'count': 0, 'places': []}, message='Places service not available')
    
    except Exception as e:
        logger.error("Get places error: %s", e)
        return error_response(str(e), 500)


@group_planner_v2.route('/destinations/<destination>/top-places', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@cache_response(key_prefix='gp_dest:top', ttl=Config.CACHE_TTLS['autocomplete'])
def get_top_places(destination: str):
    """
    Get top-rated places for a destination.
    Subset of places with highest ratings.
    """
    try:
        limit = min(int(request.args.get('limit', 10)), 20)
        
        try:
            from app.services.destination_service import PlacesService
            service = PlacesService()
            result = service.get_top_places(
                destination=destination,
                limit=limit
            )
            
            return success_response(data=result.get('places', []))
        except Exception as e:
            logger.warning("Top places service not available: %s", e)
        
        return success_response(data=[])
    
    except Exception as e:
        logger.error("Top places error: %s", e)
        return error_response(str(e), 500)


# ============================================================
# DASHBOARD (SQL-based)
# ============================================================

@group_planner_v2.route('/dashboard', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
@cache_response(key_prefix='gp_dest:dashboard', ttl=Config.CACHE_TTLS['dashboard'], vary_on_user=True)
def get_dashboard():
    """
    Get complete dashboard data from SQL database.
    Replaces Firebase single-read dashboard pattern.
    """
    try:
        user_id = g.user_id
        
        from Group_planner.services import group_service, invitation_service

        # Get user's groups
        success, groups_result = group_service.get_user_groups(user_id)
        groups = groups_result.get('groups', []) if success else []
        
        # Get pending invitations
        success, invites_result = invitation_service.get_user_invitations(user_id, g.user_email)
        invitations = invites_result.get('invitations', []) if success else []
        
        return success_response(data={
            'groups': groups,
            'invitations': invitations,
            'user': {
                'user_id': g.user_id,
                'email': g.user_email,
                'display_name': g.current_user.get('name', '')
            }
        })
    
    except Exception as e:
        logger.error("Dashboard error: %s", e)
        return error_response(str(e), 500)


# ============================================================
# REAL-TIME UPDATES (Polling-based for SQL)
# ============================================================

@group_planner_v2.route('/activities/<group_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_dest:activities', ttl=Config.CACHE_TTLS['activities'], vary_on_user=True)
def get_group_activities(group_id: str):
    """
    Get recent activities for a group.
    Used for polling-based updates (alternative to Firebase real-time).
    """
    try:
        since = request.args.get('since')  # ISO timestamp
        limit = min(int(request.args.get('limit', 20)), 50)
        
        from app.domain.group_planner.models import GroupActivity, TripMember
        from Group_planner.database import get_db_session
        
        with get_db_session() as session:
            # Verify user is a member
            member = session.query(TripMember).filter(
                TripMember.group_id == group_id,
                TripMember.user_id == g.user_id,
                TripMember.is_active == True
            ).first()
            
            if not member:
                return error_response('Not a member of this group', 403)
            
            # Get activities
            query = session.query(GroupActivity).filter(
                GroupActivity.group_id == group_id
            ).order_by(GroupActivity.created_at.desc()).limit(limit)
            
            activities = [a.to_dict() for a in query.all()]
            
            return success_response(data=activities)
    
    except Exception as e:
        logger.error("Get activities error: %s", e)
        return error_response(str(e), 500)


# ============================================================
# METRICS (For monitoring)
# ============================================================

@group_planner_v2.route('/metrics', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@cache_response(key_prefix='gp_dest:metrics', ttl=Config.CACHE_TTLS['user_detail'])
def get_metrics():
    """
    Get API performance metrics.
    No authentication required for monitoring.
    """
    return success_response(data={
        'backend': 'SQL',
        'database': 'tripraft',
        'firebase': 'disabled',
        'realtime': 'polling'
    })
