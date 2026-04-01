"""
Place Search API Routes

Flask blueprint for place search endpoints.
"""

import hashlib
import logging

from app.api.utils.responses import success_response
from app.core.config import Config, config
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rate_limiter import limit_api
from app.infrastructure.cache.redis import cache_response
from app.services.place_search_service import PlaceSearchService
from flask import Blueprint, jsonify, make_response, request

logger = logging.getLogger(__name__)

# Create blueprint
place_search_bp = Blueprint('place_search', __name__, url_prefix='/api/v1/places')

# Service instance
_service: PlaceSearchService = None


def get_service() -> PlaceSearchService:
    """Get or create service instance"""
    global _service
    if _service is None:
        _service = PlaceSearchService()
    return _service


def _add_pagination_headers(response, total_count, limit, offset):
    """Add standard pagination headers to a response."""
    page = (offset // limit) + 1 if limit > 0 else 1
    response.headers['X-Total-Count'] = str(total_count)
    response.headers['X-Page'] = str(page)
    response.headers['X-Per-Page'] = str(limit)
    return response


def _add_etag(response):
    """Add ETag header based on response body for conditional caching."""
    data = response.get_data(as_text=True)
    etag = hashlib.md5(data.encode()).hexdigest()[:16]
    response.headers['ETag'] = f'"{etag}"'

    # Check If-None-Match from client
    client_etag = request.headers.get('If-None-Match')
    if client_etag and client_etag.strip('"') == etag:
        return make_response('', 304)
    return response


@place_search_bp.route('/search', methods=['GET'])
@cache_response(key_prefix='place_search:search', ttl=Config.CACHE_TTLS['search'], vary_on_query=True)
@limit_api(Config.RATE_LIMITS['search'])
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
    # Get query parameter
    query = request.args.get('q', '').strip()

    if not query:
        return success_response(
            data=[],
            message='Success',
            meta={'query': '', 'match_type': None, 'total_count': 0}
        )

    if len(query) < config.MIN_QUERY_LENGTH:
        raise ValidationError(
            f'Query must be at least {config.MIN_QUERY_LENGTH} characters'
        )

    if len(query) > config.MAX_QUERY_LENGTH:
        raise ValidationError(
            f'Query must not exceed {config.MAX_QUERY_LENGTH} characters'
        )

    # Parse optional parameters
    try:
        limit = min(
            int(request.args.get('limit', config.DEFAULT_LIMIT)),
            config.MAX_LIMIT
        )
        offset = int(request.args.get('offset', 0))
    except ValueError:
        raise ValidationError('limit and offset must be integers')

    sort_by = request.args.get('sort_by', config.DEFAULT_SORT_BY)
    sort_order = request.args.get('sort_order', config.DEFAULT_SORT_ORDER)

    # Parse filters
    cost_param = request.args.get('cost', '')
    cost_filter = [c.strip() for c in cost_param.split(',') if c.strip()] or None

    rating_param = request.args.get('rating')
    try:
        rating_filter = int(rating_param) if rating_param else None
    except ValueError:
        raise ValidationError('rating must be an integer')

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

    response = jsonify(result.to_dict())
    _add_pagination_headers(response, result.total_count, limit, offset)
    return _add_etag(response)


@place_search_bp.route('/autocomplete', methods=['GET'])
@cache_response(key_prefix='place_search:autocomplete', ttl=Config.CACHE_TTLS['autocomplete'], vary_on_query=True)
@limit_api(Config.RATE_LIMITS['read_light'])
def autocomplete():
    """
    Get autocomplete suggestions.
    
    Query Parameters:
        q (required): Partial search query
        limit (optional): Maximum suggestions (default: 10)
        
    Returns:
        JSON response with suggestions
    """
    query = request.args.get('q', '').strip()

    if len(query) < config.AUTOCOMPLETE_MIN_LENGTH:
        return success_response(data=[], message='Success')

    limit = min(
        int(request.args.get('limit', config.AUTOCOMPLETE_MAX_RESULTS)),
        config.AUTOCOMPLETE_MAX_RESULTS
    )

    service = get_service()
    suggestions = service.get_autocomplete(query, limit)

    return success_response(
        data=[s.to_dict() for s in suggestions],
        meta={'query': query}
    )


@place_search_bp.route('/place/<int:place_id>', methods=['GET'])
@cache_response(key_prefix='place_search:place', ttl=Config.CACHE_TTLS['place_detail'], vary_on_query=False)
@limit_api(Config.RATE_LIMITS['read_light'])
def get_place(place_id: int):
    """
    Get place details by ID.
    
    Path Parameters:
        place_id: Place ID
        
    Returns:
        JSON response with place details
    """
    service = get_service()
    place = service.get_place_by_id(place_id)

    if not place:
        raise NotFoundError(f'Place {place_id} not found')

    response = jsonify({
        'success': True,
        'message': 'Success',
        'data': place.to_dict(),
    })
    return _add_etag(response)


@place_search_bp.route('/stats', methods=['GET'])
@cache_response(key_prefix='place_search:stats', ttl=Config.CACHE_TTLS['stats'], vary_on_query=False)
def get_stats():
    """
    Get database statistics.
    
    Returns:
        JSON response with counts
    """
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

    return success_response(data=stats, message='Success')
