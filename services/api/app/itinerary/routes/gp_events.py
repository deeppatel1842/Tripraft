# Purpose: Events Routes for Group Planner Flask API routes for Ticketmaster events integration.
"""
Events Routes for Group Planner
Flask API routes for Ticketmaster events integration
"""

import logging

from app.core.apiutils.responses import error_response, success_response
from app.core.apiutils.validators import parse_query_int
from app.core.config import Config
from app.core.exceptions import ValidationError as RequestValidationError
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth
from app.core.cache.redis import cache_response
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
events_bp = Blueprint(
    'gp_events',  # Unique name for Group Planner Events
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# EVENTS ENDPOINTS
# =========================================================================

@events_bp.route('/events', methods=['GET'])
@events_bp.route('/groups/<group_id>/events', methods=['GET'])
@limit_api(Config.RATE_LIMITS['events'])
@require_auth
@cache_response(key_prefix='gp_events:list', ttl=Config.CACHE_TTLS['events'])
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
        from app.itinerary.services.events_service import events_service
        
        destination = request.args.get('destination')
        if not destination and group_id:
            # Look up destination from the group
            try:
                from app.trips.services.travel_group_service import group_service
                ok, grp = group_service.get_group(group_id=group_id, user_id=g.user_id)
                if ok:
                    grp_data = grp.get('group', {})
                    destination = grp_data.get('destination') or grp_data.get('name', '')
            except Exception:
                pass
        if not destination:
            return error_response('destination parameter is required')
        
        # Get optional parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        limit = parse_query_int(
            'limit', Config.SEARCH_DEFAULT_LIMIT, minimum=1, maximum=100,
        )
        
        # Fetch events
        success, result = events_service.get_destination_events(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit
        )
        
        if success:
            return success_response(data={
                'events': result.get('events', []),
                'total': result.get('total', 0),
                'destination': result.get('destination', destination),
                'message': result.get('message')
            })
        else:
            return error_response(result.get('error', 'Failed to fetch events'))
            
    except RequestValidationError:
        raise
    except Exception as e:
        logger.error(f"Get events error: {str(e)}")
        return error_response('Failed to fetch events', 500)


@events_bp.route('/events/categories', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_events:categories', ttl=Config.CACHE_TTLS['categories'])
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
    
    return success_response(data=categories)
