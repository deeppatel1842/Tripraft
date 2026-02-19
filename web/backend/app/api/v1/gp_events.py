"""
Events Routes for Group Planner
Flask API routes for Ticketmaster events integration
"""

import logging

from app.infrastructure.auth.decorators import require_auth
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

# Create Blueprint
events_bp = Blueprint(
    'gp_events',  # Unique name for Group Planner Events
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# EVENTS ENDPOINTS
# =========================================================================

@events_bp.route('/events', methods=['GET'])
@events_bp.route('/groups/<int:group_id>/events', methods=['GET'])
@require_auth
def get_events(group_id=None):
    """
    Get events for a destination from Ticketmaster API
    
    Request:
        GET /api/v2/group-planner/events?destination=Seattle&limit=20
        Headers: Authorization: Bearer <token>
        
    Query Parameters:
        destination: City or location name (required)
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        category: Optional category (music, sports, arts, family)
        limit: Maximum events to return (default 20, max 50)
        
    Response:
        {
            "success": true,
            "data": [
                {
                    "id": "tm_abc123",
                    "name": "Concert Name",
                    "date": "2026-02-15",
                    "time": "19:00:00",
                    "venue": "Climate Pledge Arena",
                    "address": "123 Main St, Seattle",
                    "image_url": "https://...",
                    "category": "event",
                    "event_type": "Music",
                    "min_price": 50,
                    "max_price": 150
                }
            ],
            "total": 25,
            "destination": "Seattle"
        }
    """
    try:
        from app.services.events_service import events_service
        
        destination = request.args.get('destination')
        if not destination and group_id:
            # Look up destination from the group
            try:
                from app.services.travel_group_service import group_service
                ok, grp = group_service.get_group(group_id=group_id, user_id=g.user_id)
                if ok:
                    grp_data = grp.get('group', {})
                    destination = grp_data.get('destination') or grp_data.get('name', '')
            except Exception:
                pass
        if not destination:
            return jsonify({
                'success': False,
                'error': 'destination parameter is required'
            }), 400
        
        # Get optional parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        limit = request.args.get('limit', 20, type=int)
        
        # Fetch events
        success, result = events_service.get_destination_events(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': result.get('events', []),
                'total': result.get('total', 0),
                'destination': result.get('destination', destination),
                'message': result.get('message')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to fetch events')
            }), 400
            
    except Exception as e:
        logger.error(f"Get events error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch events'
        }), 500


@events_bp.route('/events/categories', methods=['GET'])
@require_auth
def get_event_categories():
    """
    Get available event categories
    
    Request:
        GET /api/v2/group-planner/events/categories
        
    Response:
        {
            "success": true,
            "data": [
                {"id": "music", "name": "Music"},
                {"id": "sports", "name": "Sports"},
                ...
            ]
        }
    """
    categories = [
        {'id': 'music', 'name': 'Music', 'icon': 'music'},
        {'id': 'sports', 'name': 'Sports', 'icon': 'trophy'},
        {'id': 'arts', 'name': 'Arts & Theatre', 'icon': 'theater'},
        {'id': 'family', 'name': 'Family', 'icon': 'users'},
        {'id': 'film', 'name': 'Film', 'icon': 'film'}
    ]
    
    return jsonify({
        'success': True,
        'data': categories
    }), 200
