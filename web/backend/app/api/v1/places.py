"""
Place Search API Routes

Flask blueprint for place search endpoints.
"""

import logging

from app.core.config import config
from app.services.place_search_service import PlaceSearchService
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Create blueprint
place_search_bp = Blueprint('place_search', __name__, url_prefix='/api/v1/place-search')

# Service instance
_service: PlaceSearchService = None


def get_service() -> PlaceSearchService:
    """Get or create service instance"""
    global _service
    if _service is None:
        _service = PlaceSearchService()
    return _service


@place_search_bp.route('/search', methods=['GET'])
def search():
    """
    Search for places.
    
    Query Parameters:
        q (required): Search query string
        limit (optional): Number of results (default: 20, max: 100)
        offset (optional): Pagination offset (default: 0)
        sort_by (optional): Sort field (rank_score, name, rating_tourist_priority)
        sort_order (optional): Sort order (asc, desc)
        cost (optional): Cost filter (comma-separated: free,low,medium,high)
        rating (optional): Minimum rating (1-5)
        
    Returns:
        JSON response with search results
    """
    try:
        # Get query parameter
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'query': '',
                'match_type': None,
                'total_count': 0,
                'places': [],
            }), 200
        
        if len(query) < config.MIN_QUERY_LENGTH:
            return jsonify({
                'success': False,
                'error': f'Query must be at least {config.MIN_QUERY_LENGTH} characters',
            }), 400
        
        if len(query) > config.MAX_QUERY_LENGTH:
            return jsonify({
                'success': False,
                'error': f'Query must not exceed {config.MAX_QUERY_LENGTH} characters',
            }), 400
        
        # Parse optional parameters
        limit = min(
            int(request.args.get('limit', config.DEFAULT_LIMIT)),
            config.MAX_LIMIT
        )
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort_by', config.DEFAULT_SORT_BY)
        sort_order = request.args.get('sort_order', config.DEFAULT_SORT_ORDER)
        
        # Parse filters
        cost_param = request.args.get('cost', '')
        cost_filter = [c.strip() for c in cost_param.split(',') if c.strip()] or None
        
        rating_param = request.args.get('rating')
        rating_filter = int(rating_param) if rating_param else None
        
        # Execute search
        service = get_service()
        result = service.search(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            cost_filter=cost_filter,
            rating_filter=rating_filter,
        )
        
        return jsonify(result.to_dict())
        
    except ValueError as e:
        logger.warning(f"Invalid parameter: {e}")
        return jsonify({
            'success': False,
            'error': 'Invalid parameter value',
        }), 400
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while searching',
        }), 500


@place_search_bp.route('/autocomplete', methods=['GET'])
def autocomplete():
    """
    Get autocomplete suggestions.
    
    Query Parameters:
        q (required): Partial search query
        limit (optional): Maximum suggestions (default: 10)
        
    Returns:
        JSON response with suggestions
    """
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < config.AUTOCOMPLETE_MIN_LENGTH:
            return jsonify({
                'success': True,
                'suggestions': [],
            })
        
        limit = min(
            int(request.args.get('limit', config.AUTOCOMPLETE_MAX_RESULTS)),
            config.AUTOCOMPLETE_MAX_RESULTS
        )
        
        service = get_service()
        suggestions = service.get_autocomplete(query, limit)
        
        return jsonify({
            'success': True,
            'query': query,
            'suggestions': [s.to_dict() for s in suggestions],
        })
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching suggestions',
        }), 500


@place_search_bp.route('/place/<int:place_id>', methods=['GET'])
def get_place(place_id: int):
    """
    Get place details by ID.
    
    Path Parameters:
        place_id: Place ID
        
    Returns:
        JSON response with place details
    """
    try:
        service = get_service()
        place = service.get_place_by_id(place_id)
        
        if not place:
            return jsonify({
                'success': False,
                'error': 'Place not found',
            }), 404
        
        return jsonify({
            'success': True,
            'place': place.to_dict(),
        })
        
    except Exception as e:
        logger.error(f"Get place error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching place details',
        }), 500


@place_search_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get database statistics.
    
    Returns:
        JSON response with counts
    """
    try:
        service = get_service()
        db = service.db
        
        stats = {
            'countries': db.execute_single("SELECT COUNT(*) as count FROM countries")['count'],
            'states': db.execute_single("SELECT COUNT(*) as count FROM states")['count'],
            'cities': db.execute_single("SELECT COUNT(*) as count FROM cities")['count'],
            'places': db.execute_single("SELECT COUNT(*) as count FROM places")['count'],
            'photos': db.execute_single("SELECT COUNT(*) as count FROM photos")['count'],
            'tags': db.execute_single("SELECT COUNT(*) as count FROM tags")['count'],
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
        })
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching statistics',
        }), 500
