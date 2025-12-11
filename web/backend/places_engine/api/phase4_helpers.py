"""
Phase 4: Intelligent Search Integration with Phase 3

Integration of Phase 3 IntelligentSearchService with Flask endpoints.
This module extends existing API with intelligent query detection.

Key additions:
- Intelligent search endpoint using Phase 3 service
- Autocomplete endpoint using Phase 3 service
- Request validation and response formatting
- Performance metrics and error handling
"""

import logging
from typing import Dict, Any, Optional, Tuple
from flask import jsonify
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Response Helpers
# ============================================================================

def create_success_response(data: Any, metadata: Optional[Dict] = None) -> Tuple[Dict, int]:
    """
    Create a standardized success response
    
    Args:
        data: Response data payload
        metadata: Optional metadata (response_time_ms, firestore_reads, etc.)
    
    Returns:
        (response_dict, status_code)
    """
    response = {
        'success': True,
        'data': data,
        'timestamp': time.time(),
    }
    
    if metadata:
        response['metadata'] = metadata
    
    return response, 200


def create_error_response(message: str, code: int, error_type: str = 'error') -> Tuple[Dict, int]:
    """
    Create a standardized error response
    
    Args:
        message: Error message
        code: HTTP status code
        error_type: Error type for client classification
    
    Returns:
        (response_dict, status_code)
    """
    response = {
        'success': False,
        'error': message,
        'error_type': error_type,
        'timestamp': time.time(),
    }
    
    logger.warning(f"{error_type} ({code}): {message}")
    
    return response, code


# ============================================================================
# Request Validation
# ============================================================================

def validate_query_parameter(
    query: Optional[str],
    min_length: int = 1,
    max_length: int = 500,
) -> Tuple[Optional[str], Optional[Tuple[Dict, int]]]:
    """
    Validate a search query parameter
    
    Args:
        query: Query string to validate
        min_length: Minimum query length
        max_length: Maximum query length
    
    Returns:
        (valid_query, error_response) - Returns error_response if validation fails
    """
    if not query:
        return None, create_error_response(
            'Query parameter is required',
            400,
            'missing_query'
        )
    
    query = query.strip()
    
    if len(query) < min_length:
        return None, create_error_response(
            f'Query too short (minimum {min_length} characters)',
            400,
            'query_too_short'
        )
    
    if len(query) > max_length:
        return None, create_error_response(
            f'Query too long (maximum {max_length} characters)',
            400,
            'query_too_long'
        )
    
    return query, None


def validate_limit_parameter(
    limit: Optional[str],
    min_value: int = 1,
    max_value: int = 100,
    default: int = 10,
) -> Tuple[int, Optional[Tuple[Dict, int]]]:
    """
    Validate a limit parameter
    
    Args:
        limit: Limit string to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if not provided
    
    Returns:
        (valid_limit, error_response)
    """
    if not limit:
        return default, None
    
    try:
        limit_int = int(limit)
    except ValueError:
        return None, create_error_response(
            'Limit must be an integer',
            400,
            'invalid_limit'
        )
    
    if limit_int < min_value or limit_int > max_value:
        return None, create_error_response(
            f'Limit must be between {min_value} and {max_value}',
            400,
            'limit_out_of_range'
        )
    
    return limit_int, None


# ============================================================================
# Response Formatting for Phase 3 Results
# ============================================================================

def format_search_result(service_result: Any) -> Dict:
    """
    Format Phase 3 SearchResult for API response
    
    Args:
        service_result: SearchResult from IntelligentSearchService
    
    Returns:
        Formatted response dictionary
    """
    if not service_result.success:
        return {
            'success': False,
            'query': service_result.query,
            'error': service_result.error,
        }
    
    # Base response structure
    response = {
        'query': service_result.query,
        'query_type': service_result.query_type.value,
        'display_mode': service_result.display_mode,
        'match': {
            'id': service_result.match_id,
            'name': service_result.match_name,
        } if service_result.match_id else None,
        'location_hierarchy': service_result.location_hierarchy or {},
    }
    
    # Format results based on display mode
    if service_result.display_mode == 'country_sections':
        response['sections'] = service_result.sections or []
        response['total_places'] = len(service_result.places)
    
    elif service_result.display_mode == 'top_destinations':
        response['places'] = service_result.places or []
        response['total_places'] = len(service_result.places)
    
    elif service_result.display_mode == 'single_place':
        response['place'] = service_result.places[0] if service_result.places else None
    
    return response


def format_autocomplete_result(service_result: Any) -> Dict:
    """
    Format Phase 3 AutocompleteResult for API response
    
    Args:
        service_result: AutocompleteResult from IntelligentSearchService
    
    Returns:
        Formatted response dictionary
    """
    if not service_result.success:
        return {
            'query': service_result.query,
            'suggestions': [],
            'total': 0,
            'error': service_result.error,
        }
    
    return {
        'query': service_result.query,
        'suggestions': service_result.suggestions,
        'total': len(service_result.suggestions),
    }


# ============================================================================
# Endpoint Response Creation
# ============================================================================

def create_search_response(
    service_result: Any,
    response_time_ms: float,
) -> Tuple[Dict, int]:
    """
    Create search endpoint response
    
    Args:
        service_result: SearchResult from Phase 3 service
        response_time_ms: API response time in milliseconds
    
    Returns:
        (response_dict, status_code)
    """
    formatted = format_search_result(service_result)
    
    metadata = {
        'response_time_ms': round(response_time_ms, 2),
        'firestore_reads': service_result.firestore_reads,
        'cache_hit': service_result.cache_hit,
    }
    
    # Log search
    logger.info(
        f"Search: '{service_result.query}' → {service_result.query_type.value} "
        f"({response_time_ms:.2f}ms, {service_result.firestore_reads} reads)"
    )
    
    return create_success_response(formatted, metadata)


def create_autocomplete_response(
    service_result: Any,
    response_time_ms: float,
) -> Tuple[Dict, int]:
    """
    Create autocomplete endpoint response
    
    Args:
        service_result: AutocompleteResult from Phase 3 service
        response_time_ms: API response time in milliseconds
    
    Returns:
        (response_dict, status_code)
    """
    formatted = format_autocomplete_result(service_result)
    
    metadata = {
        'response_time_ms': round(response_time_ms, 2),
        'firestore_reads': service_result.firestore_reads,
        'cache_hit': service_result.cache_hit,
    }
    
    # Log autocomplete
    logger.info(
        f"Autocomplete: '{service_result.query}' → {len(service_result.suggestions)} suggestions "
        f"({response_time_ms:.2f}ms, {service_result.firestore_reads} reads)"
    )
    
    return create_success_response(formatted, metadata)


# ============================================================================
# Error Response Wrappers
# ============================================================================

def missing_service_error() -> Tuple[Dict, int]:
    """Return error when Phase 3 service not initialized"""
    return create_error_response(
        'Search service not available',
        503,
        'service_unavailable'
    )


def server_error(exception: Exception) -> Tuple[Dict, int]:
    """Return error for server exceptions"""
    logger.error(f"Server error: {exception}", exc_info=True)
    return create_error_response(
        'Internal server error',
        500,
        'server_error'
    )
