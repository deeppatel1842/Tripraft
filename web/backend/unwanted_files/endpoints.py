"""
Phase 4: API Endpoints Helper Functions

Professional REST endpoints for intelligent search and autocomplete.
Response formatting and validation helpers for integration with Phase 3 service.
"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Error Response Handlers
# ============================================================================

def error_response(message: str, code: int, error_type: str = 'error') -> tuple:
    """
    Generate standardized error response
    
    Args:
        message: Error message
        code: HTTP status code
        error_type: Error type for client handling
    
    Returns:
        (JSON response, HTTP status code)
    """
    response = {
        'success': False,
        'error': message,
        'error_type': error_type,
        'timestamp': time.time(),
    }
    logger.warning(f"{error_type}: {message}")
    return jsonify(response), code


def success_response(data: Any, metadata: Optional[Dict] = None) -> tuple:
    """
    Generate standardized success response
    
    Args:
        data: Response data
        metadata: Optional metadata (response_time, firestore_reads, etc.)
    
    Returns:
        (JSON response, HTTP status code)
    """
    response = {
        'success': True,
        'data': data,
        'timestamp': time.time(),
    }
    
    if metadata:
        response['metadata'] = metadata
    
    return jsonify(response), 200


# ============================================================================
# Request Validation
# ============================================================================

def validate_search_request() -> tuple[Optional[Dict], Optional[tuple]]:
    """
    Validate /search request
    
    Returns:
        (request_data, error_response) - If error, returns (None, error_response)
    """
    # Get query from parameters or JSON body
    query = request.args.get('q') or request.json.get('q') if request.json else None
    
    if not query:
        return None, error_response(
            'Query parameter "q" is required',
            400,
            'missing_parameter'
        )
    
    query = query.strip()
    if not query:
        return None, error_response(
            'Query cannot be empty or whitespace only',
            400,
            'invalid_query'
        )
    
    if len(query) > 500:
        return None, error_response(
            'Query is too long (max 500 characters)',
            400,
            'query_too_long'
        )
    
    type_override = request.args.get('type') or (
        request.json.get('type') if request.json else None
    )
    
    return {
        'query': query,
        'type_override': type_override,
    }, None


def validate_autocomplete_request() -> tuple[Optional[Dict], Optional[tuple]]:
    """
    Validate /autocomplete request
    
    Returns:
        (request_data, error_response) - If error, returns (None, error_response)
    """
    query = request.args.get('q') or request.json.get('q') if request.json else None
    
    if not query:
        return None, error_response(
            'Query parameter "q" is required',
            400,
            'missing_parameter'
        )
    
    query = query.strip()
    if not query:
        return None, error_response(
            'Query cannot be empty',
            400,
            'invalid_query'
        )
    
    if len(query) > 100:
        return None, error_response(
            'Query is too long (max 100 characters)',
            400,
            'query_too_long'
        )
    
    try:
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 100:
            return None, error_response(
                'Limit must be between 1 and 100',
                400,
                'invalid_parameter'
            )
    except ValueError:
        return None, error_response(
            'Limit must be an integer',
            400,
            'invalid_parameter'
        )
    
    return {
        'query': query,
        'limit': limit,
    }, None


# ============================================================================
# Response Formatting
# ============================================================================

def format_search_response(service_result: Any) -> Dict:
    """
    Format service search result for API response
    
    Args:
        service_result: SearchResult from IntelligentSearchService
    
    Returns:
        Formatted response dictionary
    """
    if not service_result.success:
        return {
            'success': False,
            'error': service_result.error,
            'query': service_result.query,
        }
    
    # Format location hierarchy
    location_hierarchy = service_result.location_hierarchy or {}
    
    # Base response
    response = {
        'query': service_result.query,
        'query_type': service_result.query_type.value,
        'display_mode': service_result.display_mode,
        'location_hierarchy': location_hierarchy,
        'match': {
            'id': service_result.match_id,
            'name': service_result.match_name,
        } if service_result.match_id else None,
    }
    
    # Add results based on display mode
    if service_result.display_mode == 'country_sections':
        # Show states with embedded places
        response['sections'] = service_result.sections or []
        response['total_places'] = len(service_result.places)
    
    elif service_result.display_mode == 'top_destinations':
        # Show top places for state/city
        response['places'] = service_result.places or []
        response['total_places'] = len(service_result.places)
    
    elif service_result.display_mode == 'single_place':
        # Show single place details
        response['place'] = service_result.places[0] if service_result.places else None
    
    else:  # error mode
        response['error'] = service_result.error
    
    return response


def format_autocomplete_response(service_result: Any) -> Dict:
    """
    Format service autocomplete result for API response
    
    Args:
        service_result: AutocompleteResult from IntelligentSearchService
    
    Returns:
        Formatted response dictionary
    """
    if not service_result.success:
        return {
            'success': False,
            'error': service_result.error,
            'query': service_result.query,
            'suggestions': [],
        }
    
    return {
        'query': service_result.query,
        'suggestions': service_result.suggestions,
        'total': len(service_result.suggestions),
    }


# ============================================================================
# API Endpoints
# ============================================================================

@places_bp.route('/search', methods=['GET', 'POST'])
def search_endpoint():
    """
    Intelligent search endpoint
    
    Query Parameters:
        q (required): Search query string
        type (optional): Force specific query type (country/state/city/place)
    
    Request Body (JSON):
        {
            "q": "query string",
            "type": "optional type override"
        }
    
    Response (Success):
        {
            "success": true,
            "data": {
                "query": "Paris",
                "query_type": "city",
                "display_mode": "top_destinations",
                "location_hierarchy": {"country": "France", "state": "Île-de-France", "city": "Paris"},
                "match": {"id": "paris", "name": "Paris"},
                "places": [...],
                "total_places": 20
            },
            "metadata": {
                "response_time_ms": 45.2,
                "firestore_reads": 1,
                "cache_hit": false
            }
        }
    
    Response (Error):
        {
            "success": false,
            "error": "error message",
            "error_type": "error_type",
            "timestamp": 1702050000.123
        }
    """
    start_time = time.time()
    
    try:
        # Validate request
        request_data, validation_error = validate_search_request()
        if validation_error:
            return validation_error
        
        # Call service
        if not search_service:
            return error_response(
                'Search service not initialized',
                500,
                'service_error'
            )
        
        service_result = search_service.intelligent_search(
            query=request_data['query'],
            type_override=request_data['type_override'],
        )
        
        # Format response
        formatted_data = format_search_response(service_result)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Add metadata
        metadata = {
            'response_time_ms': round(response_time_ms, 2),
            'firestore_reads': service_result.firestore_reads,
            'cache_hit': service_result.cache_hit,
        }
        
        logger.info(
            f"Search: '{request_data['query']}' → {service_result.query_type.value} "
            f"({response_time_ms:.2f}ms, {service_result.firestore_reads} reads)"
        )
        
        return success_response(formatted_data, metadata)
    
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        return error_response(
            f'Internal server error: {str(e)}',
            500,
            'server_error'
        )


@places_bp.route('/autocomplete', methods=['GET', 'POST'])
def autocomplete_endpoint():
    """
    Autocomplete endpoint
    
    Query Parameters:
        q (required): Search prefix
        limit (optional): Max suggestions (default: 10, max: 100)
    
    Request Body (JSON):
        {
            "q": "search prefix",
            "limit": 10
        }
    
    Response (Success):
        {
            "success": true,
            "data": {
                "query": "par",
                "suggestions": [
                    {
                        "id": "paris",
                        "name": "Paris",
                        "type": "city",
                        "display_text": "Paris, France",
                        "rank": 0.95
                    },
                    ...
                ],
                "total": 5
            },
            "metadata": {
                "response_time_ms": 25.5,
                "firestore_reads": 1,
                "cache_hit": true
            }
        }
    
    Response (Error):
        {
            "success": false,
            "error": "error message",
            "error_type": "error_type",
            "timestamp": 1702050000.123
        }
    """
    start_time = time.time()
    
    try:
        # Validate request
        request_data, validation_error = validate_autocomplete_request()
        if validation_error:
            return validation_error
        
        # Call service
        if not search_service:
            return error_response(
                'Search service not initialized',
                500,
                'service_error'
            )
        
        service_result = search_service.autocomplete(
            query=request_data['query'],
            limit=request_data['limit'],
        )
        
        # Format response
        formatted_data = format_autocomplete_response(service_result)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Add metadata
        metadata = {
            'response_time_ms': round(response_time_ms, 2),
            'firestore_reads': service_result.firestore_reads,
            'cache_hit': service_result.cache_hit,
        }
        
        logger.info(
            f"Autocomplete: '{request_data['query']}' → {len(service_result.suggestions)} suggestions "
            f"({response_time_ms:.2f}ms, {service_result.firestore_reads} reads)"
        )
        
        return success_response(formatted_data, metadata)
    
    except Exception as e:
        logger.error(f"Autocomplete endpoint error: {e}", exc_info=True)
        return error_response(
            f'Internal server error: {str(e)}',
            500,
            'server_error'
        )


@places_bp.route('/place/<place_id>', methods=['GET'])
def get_place_endpoint(place_id: str):
    """
    Get detailed information about a specific place
    
    Path Parameters:
        place_id: Unique place identifier
    
    Response (Success):
        {
            "success": true,
            "data": {
                "id": "eiffel-tower",
                "name": "Eiffel Tower",
                "city": "Paris",
                "state": "Île-de-France",
                "country": "France",
                "coordinates": {"lat": 48.8584, "lng": 2.2945},
                "rating": 4.8,
                "ai_summary": "...",
                ... (all place fields)
            },
            "metadata": {
                "response_time_ms": 15.3,
                "firestore_reads": 1,
                "cache_hit": false
            }
        }
    
    Response (Error):
        {
            "success": false,
            "error": "Place not found",
            "error_type": "not_found",
            "timestamp": 1702050000.123
        }
    """
    start_time = time.time()
    
    try:
        if not place_id or not place_id.strip():
            return error_response(
                'Place ID cannot be empty',
                400,
                'missing_parameter'
            )
        
        if not search_service:
            return error_response(
                'Search service not initialized',
                500,
                'service_error'
            )
        
        # Search for place
        result = search_service.intelligent_search(place_id)
        
        if not result.success or result.query_type != QueryType.PLACE or not result.places:
            return error_response(
                f'Place "{place_id}" not found',
                404,
                'not_found'
            )
        
        place_data = result.places[0]
        response_time_ms = (time.time() - start_time) * 1000
        
        metadata = {
            'response_time_ms': round(response_time_ms, 2),
            'firestore_reads': result.firestore_reads,
            'cache_hit': result.cache_hit,
        }
        
        logger.info(f"Get place: {place_id} ({response_time_ms:.2f}ms)")
        
        return success_response(place_data, metadata)
    
    except Exception as e:
        logger.error(f"Get place endpoint error: {e}", exc_info=True)
        return error_response(
            f'Internal server error: {str(e)}',
            500,
            'server_error'
        )


@places_bp.route('/health', methods=['GET'])
def health_endpoint():
    """
    Health check endpoint
    
    Response:
        {
            "success": true,
            "data": {
                "status": "healthy",
                "service": "places-engine",
                "version": "1.0.0"
            }
        }
    """
    if not search_service:
        return error_response(
            'Search service not initialized',
            500,
            'service_error'
        )
    
    response_data = {
        'status': 'healthy',
        'service': 'places-engine',
        'version': '1.0.0',
        'timestamp': time.time(),
    }
    
    return success_response(response_data)


# ============================================================================
# Middleware
# ============================================================================

@places_bp.before_request
def before_request_logging():
    """Log incoming requests"""
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")


@places_bp.after_request
def after_request_cors(response):
    """Add CORS headers"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@places_bp.after_request
def after_request_caching(response):
    """Add caching headers"""
    if request.path == '/api/places/health':
        # Health check: no cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    elif request.path == '/api/places/autocomplete':
        # Autocomplete: cache for 1 hour
        response.headers['Cache-Control'] = 'public, max-age=3600'
    elif request.path == '/api/places/search':
        # Search: cache for 30 minutes
        response.headers['Cache-Control'] = 'public, max-age=1800'
    else:
        # Default: cache for 1 hour
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response
