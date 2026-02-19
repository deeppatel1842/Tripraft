"""
Group Planner SQL-Only Routes
Pure SQL backend - NO FIREBASE

Destination/Places endpoints for group planning
Uses shared_db unified authentication
"""

import logging

from app.infrastructure.auth.decorators import require_auth
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

# Create blueprint for v2 API (consistent with other Group Planner blueprints)
group_planner_v2 = Blueprint('group_planner_v2', __name__, url_prefix='/api/v2/group-planner')

# Alias for backward compatibility
group_planner_bp = group_planner_v2


# ============================================================
# HEALTH CHECK - No auth required
# ============================================================

@group_planner_v2.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - no auth required."""
    return jsonify({
        'status': 'healthy',
        'version': '3.0',
        'backend': 'SQL',
        'firebase': 'disabled'
    })


# ============================================================
# AUTHENTICATION VERIFICATION
# ============================================================

@group_planner_v2.route('/auth/verify', methods=['POST'])
@require_auth
def verify_auth():
    """
    Verify user authentication.
    Returns user info from JWT token.
    """
    return jsonify({
        'success': True,
        'user': {
            'user_id': g.user_id,
            'email': g.user_email,
            'display_name': g.current_user.get('name', '')
        },
        'message': 'Token valid'
    })


# ============================================================
# DESTINATION SEARCH ENDPOINTS
# ============================================================

@group_planner_v2.route('/destinations/autocomplete', methods=['GET'])
def autocomplete_destinations():
    """
    Autocomplete for destination search when creating a group.
    Uses local SQLite locations database directly.
    """
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Query too short'
            })
        
        limit = min(int(request.args.get('limit', 10)), 20)
        
        # Direct SQLite query for cities/states/countries
        try:
            import os
            import sqlite3
            
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(backend_dir, 'database', 'travel_data_complete.db')
            
            if not os.path.exists(db_path):
                logger.warning("Travel database not found: %s", db_path)
                return jsonify({'success': True, 'data': []})
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            results = []
            query_lower = query.lower()
            query_pattern = f'%{query_lower}%'
            
            # Search cities
            cursor.execute("""
                SELECT c.id, c.city_name as name, c.latitude, c.longitude,
                       s.state_name, co.country_name
                FROM cities c
                LEFT JOIN states s ON c.state_id = s.id
                LEFT JOIN countries co ON s.country_id = co.id
                WHERE LOWER(c.city_name) LIKE ?
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
                    WHERE LOWER(s.state_name) LIKE ?
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
            # Note: countries table doesn't have lat/lng, so we get coords from first city
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
                    WHERE LOWER(co.country_name) LIKE ?
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
            
            conn.close()
            
            return jsonify({
                'success': True,
                'data': results
            })
            
        except Exception as e:
            logger.exception("SQLite autocomplete error: %s", e)
        
        return jsonify({
            'success': True,
            'data': [],
            'message': 'Search service not available'
        })
    
    except Exception as e:
        logger.error("Autocomplete error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/destinations/<destination>/places', methods=['GET'])
def get_destination_places(destination: str):
    """
    Get places for a destination.
    Uses local database for place data.
    """
    try:
        category = request.args.get('category', 'all')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        try:
            from app.services.destination_service import PlacesService
            service = PlacesService()
            result = service.get_destination_places(
                destination=destination,
                category=category,
                limit=limit
            )
            
            return jsonify({
                'success': True,
                'count': result.get('count', 0),
                'attractions': result.get('attractions', 0),
                'restaurants': result.get('restaurants', 0),
                'places': result.get('places', []),
                'coordinates': result.get('coordinates', None)
            })
        except Exception as e:
            logger.warning("PlacesService not available: %s", e)
        
        return jsonify({
            'success': True,
            'count': 0,
            'data': [],
            'message': 'Places service not available'
        })
    
    except Exception as e:
        logger.error("Get places error: %s", e)
        return jsonify({'error': str(e)}), 500


@group_planner_v2.route('/destinations/<destination>/top-places', methods=['GET'])
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
            
            return jsonify({
                'success': True,
                'data': result.get('places', [])
            })
        except Exception as e:
            logger.warning("Top places service not available: %s", e)
        
        return jsonify({
            'success': True,
            'data': []
        })
    
    except Exception as e:
        logger.error("Top places error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# DASHBOARD (SQL-based)
# ============================================================

@group_planner_v2.route('/dashboard', methods=['GET'])
@require_auth
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
        
        return jsonify({
            'success': True,
            'data': {
                'groups': groups,
                'invitations': invitations,
                'user': {
                    'user_id': g.user_id,
                    'email': g.user_email,
                    'display_name': g.current_user.get('name', '')
                }
            }
        })
    
    except Exception as e:
        logger.error("Dashboard error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# REAL-TIME UPDATES (Polling-based for SQL)
# ============================================================

@group_planner_v2.route('/activities/<int:group_id>', methods=['GET'])
@require_auth
def get_group_activities(group_id: int):
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
                return jsonify({'error': 'Not a member of this group'}), 403
            
            # Get activities
            query = session.query(GroupActivity).filter(
                GroupActivity.group_id == group_id
            ).order_by(GroupActivity.created_at.desc()).limit(limit)
            
            activities = [a.to_dict() for a in query.all()]
            
            return jsonify({
                'success': True,
                'data': activities
            })
    
    except Exception as e:
        logger.error("Get activities error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# METRICS (For monitoring)
# ============================================================

@group_planner_v2.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Get API performance metrics.
    No authentication required for monitoring.
    """
    return jsonify({
        'success': True,
        'data': {
            'backend': 'SQL',
            'database': 'tripraft',
            'firebase': 'disabled',
            'realtime': 'polling'
        }
    })
