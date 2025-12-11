# pylint: disable=broad-exception-caught,global-statement
"""
TripRaft Places API Routes

RESTful API endpoints for places discovery and search.

Endpoints:
    GET  /api/places/search           - Search places with filters
    GET  /api/places/<id>             - Get place details by ID
    GET  /api/places/location         - Search by city/state name (20 places)
    GET  /api/places/country/<name>   - Country overview with states
    GET  /api/places/nearby           - Nearby places with fallback
    GET  /api/places/autocomplete     - Autocomplete suggestions
    GET  /api/places/popular          - Popular places
    GET  /api/places/countries        - List all countries
    GET  /api/places/cities           - Get cities by country
"""

import json
import logging
from typing import Optional

from flask import Blueprint, jsonify, request

from ..services.places_service import PlacesService

logger = logging.getLogger(__name__)

# Create blueprint
places_bp = Blueprint('places_engine', __name__)

# Service instance (lazy initialization)
_service: Optional[PlacesService] = None


def get_service() -> PlacesService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = PlacesService()
    return _service


def init_service(db=None):
    """Initialize service with Firestore client and cache."""
    global _service
    
    # Initialize cache with Redis client
    cache = None
    try:
        from cache.redis_client import get_redis_client

        from ..cache.places_cache import PlacesCache

        # Try to get Redis client
        try:
            redis_client = get_redis_client()
            cache = PlacesCache(redis_client)
            logger.info("Places Engine cache initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis not available for Places Engine: {e}")
            cache = PlacesCache()  # Will use lazy loading fallback
    except ImportError as e:
        logger.warning(f"Could not import cache modules: {e}")
        pass
    
    _service = PlacesService(db, cache)


# ==================== SEARCH ENDPOINTS ====================

# ==================== SEARCH ENDPOINTS ====================

@places_bp.route('/search', methods=['GET', 'OPTIONS'])
def search_places():
    """
    Unified search endpoint with intelligent query detection.
    
    HARD LIMIT: Max 10 Firebase reads per request.
    
    Query params:
        q: Search query (required)
        type: Override type detection (optional: country|state|city|place)
        limit: Results per page (default 20, max 100)
        offset: Pagination offset (default 0)
    
    Returns:
        JSON with places array, match info, and read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        query = request.args.get('q', '').strip()
        type_override = request.args.get('type')
        limit = min(request.args.get('limit', 20, type=int), 100)
        offset = request.args.get('offset', 0, type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query "q" is required',
                'firebase_reads': 0
            }), 400
        
        if len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 2 characters',
                'firebase_reads': 0
            }), 400
        
        service = get_service()
        
        # Execute search (service enforces 10-read limit)
        result = service.intelligent_search(
            query=query,
            type_hint=type_override,
            limit=limit,
            offset=offset
        )
        
        # Add response metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/search'
        result['query_type'] = type_override or 'auto-detect'
        
        return jsonify(result), 200 if result.get('success') else 404
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/<place_id>', methods=['GET'])
def get_place_detail(place_id: str):
    """
    Get place details by ID.
    
    Args:
        place_id: Unique place identifier
    
    Returns:
        JSON with full place details
    """
    try:
        service = get_service()
        result = service.get_place_by_id(place_id)
        
        if result:
            return jsonify(result), 200
        
        return jsonify({
            'success': False,
            'error': 'Place not found'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@places_bp.route('/location', methods=['GET', 'OPTIONS'])
def search_by_location():
    """
    Search places by city or state name with pagination.
    Returns top places sorted by rank_score.
    
    HARD LIMIT: Max 10 Firebase reads per request.
    
    Query params:
        q: City or state name (required)
        limit: Max results per page (default 20, max 50)
        page: Page number for pagination (default 1)
    
    Returns:
        JSON with places and match info
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query parameter "q" is required',
                'firebase_reads': 0
            }), 400
        
        if len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 2 characters',
                'firebase_reads': 0
            }), 400
        
        service = get_service()
        result = service.search_by_location(
            query=query,
            limit=min(request.args.get('limit', 20, type=int), 50),
            page=max(request.args.get('page', 1, type=int), 1)
        )
        
        # Add response metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/location'
        
        return jsonify(result), 200 if result.get('success') else 404
        
    except Exception as e:
        logger.error(f"Location search error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/country/<country_name>', methods=['GET', 'OPTIONS'])
def get_country_overview(country_name: str):
    """
    Get country overview with states and top places per state.
    
    HARD LIMIT: Max 1 Firebase read per request (pre-embedded data).
    
    Args:
        country_name: Country name (case-insensitive)
    
    Query params:
        places_per_state: Top places per state (default 5, max 10)
    
    Returns:
        JSON with states array, each containing top places and read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        service = get_service()
        result = service.get_country_overview(
            country=country_name
        )
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/country/<country_name>'
        
        return jsonify(result), 200 if result.get('success') else 404
        
    except Exception as e:
        logger.error(f"Country overview error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/nearby', methods=['GET', 'OPTIONS'])
def get_nearby_places():
    """
    Get nearby places with intelligent fallback.
    If no places found within radius, returns places from nearest city.
    
    HARD LIMIT: Max 10 Firebase reads per request.
    
    Query params:
        lat: Latitude (required)
        lng: Longitude (required)
        radius: Search radius in meters (default 10000)
        limit: Max results (default 20, max 50)
    
    Returns:
        JSON with nearby places and distance info, read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if lat is None or lng is None:
            return jsonify({
                'success': False,
                'error': 'lat and lng parameters are required',
                'firebase_reads': 0
            }), 400
        
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({
                'success': False,
                'error': 'Invalid coordinates',
                'firebase_reads': 0
            }), 400
        
        service = get_service()
        result = service.get_nearby_places(
            latitude=lat,
            longitude=lng,
            radius_meters=request.args.get('radius', 10000, type=int),
            limit=min(request.args.get('limit', 20, type=int), 50)
        )
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/nearby'
        
        return jsonify(result), 200 if result.get('success') else 404
        
    except Exception as e:
        logger.error(f"Nearby places error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/autocomplete', methods=['GET', 'OPTIONS'])
def autocomplete():
    """
    Get autocomplete suggestions for places, cities, states.
    
    HARD LIMIT: Max 1 Firebase read per request (from pre-built index).
    
    Query params:
        q: Search query (required, min 1 char)
        limit: Max suggestions (default 10, max 20)
    
    Returns:
        JSON with suggestions array and read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 10, type=int), 20)
        firebase_reads = 0
        cache_hit = False
        
        if len(query) < 1:
            return jsonify({
                'success': True,
                'suggestions': [],
                'firebase_reads': 0,
                'cache_hit': False
            }), 200
        
        # Try cache first (optional - may not be available)
        cache = None
        cache_key = f"autocomplete:{query.lower()}:{limit}"
        
        try:
            from cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            cached = redis_client.get(cache_key)
            if cached:
                return jsonify({
                    'success': True,
                    'suggestions': json.loads(cached),
                    'query': query,
                    'firebase_reads': 0,
                    'cache_hit': True,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }), 200
            cache = redis_client
        except Exception as e:
            logger.debug(f"Cache not available: {e}")
        
        service = get_service()
        result = service.autocomplete(
            query=query,
            limit=limit
        )
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/autocomplete'
        result['cache_hit'] = cache_hit
        
        # Cache successful results for 1 hour if cache available
        if cache and result.get('success') and result.get('suggestions'):
            try:
                cache.setex(cache_key, 3600, json.dumps(result.get('suggestions')))
            except Exception as e:
                logger.debug(f"Could not cache result: {e}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/popular', methods=['GET', 'OPTIONS'])
def get_popular_places():
    """
    Get popular places globally or by country.
    
    HARD LIMIT: Max 10 Firebase reads per request.
    
    Query params:
        country: Filter by country (optional)
        limit: Max results (default 20, max 100)
    
    Returns:
        JSON with popular places sorted by rank_score
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        service = get_service()
        result = service.get_popular_places(
            country=request.args.get('country'),
            limit=min(request.args.get('limit', 20, type=int), 100)
        )
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/popular'
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Popular places error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/countries', methods=['GET', 'OPTIONS'])
def get_countries():
    """
    Get list of all countries with place counts.
    
    HARD LIMIT: Max 1 Firebase read per request.
    
    Returns:
        JSON with countries array and read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        service = get_service()
        result = service.get_all_countries()
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/countries'
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Countries error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500


@places_bp.route('/cities', methods=['GET', 'OPTIONS'])
def get_cities():
    """
    Get cities for a country or state.
    
    HARD LIMIT: Max 10 Firebase reads per request.
    
    Query params:
        country: Country name (required)
        state: State name (optional)
    
    Returns:
        JSON with cities array and read count
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        import time
        start_time = time.time()
        
        country = request.args.get('country')
        
        if not country:
            return jsonify({
                'success': False,
                'error': 'country parameter is required',
                'firebase_reads': 0
            }), 400
        
        service = get_service()
        result = service.get_cities_by_country(
            country=country
        )
        
        # Add metadata
        result['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        result['endpoint'] = '/cities'
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Cities error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'firebase_reads': 0
        }), 500
