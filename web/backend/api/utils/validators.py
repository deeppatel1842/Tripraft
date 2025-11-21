"""
Input validation utilities
Provides validation and sanitization for API inputs.
"""
import re
from typing import Tuple, Any
from flask import request


def validate_pagination(max_limit: int = 100) -> Tuple[int, int]:
    """
    Validate and extract pagination parameters
    
    Args:
        max_limit: Maximum allowed limit
        
    Returns:
        Tuple of (limit, offset)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        limit, offset = 50, 0
    
    # Enforce constraints
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    
    return limit, offset


def validate_search_query(min_length: int = 2, max_length: int = 100) -> str:
    """
    Validate search query parameter
    
    Args:
        min_length: Minimum query length
        max_length: Maximum query length
        
    Returns:
        Validated and sanitized query string
        
    Raises:
        ValueError: If query is invalid
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        raise ValueError("Search query is required")
    
    if len(query) < min_length:
        raise ValueError(f"Query must be at least {min_length} characters")
    
    if len(query) > max_length:
        raise ValueError(f"Query must not exceed {max_length} characters")
    
    # Sanitize query
    return sanitize_input(query)


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent SQL injection and XSS
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text
    """
    # Remove potentially dangerous characters
    # Note: We use parameterized queries, so this is additional protection
    sanitized = text.strip()
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    # Limit special characters for search
    # Allow: letters, numbers, spaces, and common punctuation
    sanitized = re.sub(r'[^\w\s\-.,!?\'"()]', '', sanitized)
    
    return sanitized


def validate_id(id_value: str, field_name: str = "id") -> str:
    """
    Validate ID format (slug or numeric)
    
    Args:
        id_value: ID to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated ID
        
    Raises:
        ValueError: If ID format is invalid
    """
    if not id_value:
        raise ValueError(f"{field_name} is required")
    
    # Allow slugs (lowercase, hyphens) or numeric IDs
    if not re.match(r'^[a-z0-9\-]+$', id_value):
        raise ValueError(f"Invalid {field_name} format")
    
    return id_value


def validate_sort_params(allowed_fields: list) -> Tuple[str, str]:
    """
    Validate sorting parameters
    
    Args:
        allowed_fields: List of allowed field names for sorting
        
    Returns:
        Tuple of (sort_by, sort_order)
    """
    sort_by = request.args.get('sort_by', 'rating')
    sort_order = request.args.get('sort_order', 'desc').lower()
    
    # Validate sort field
    if sort_by not in allowed_fields:
        sort_by = allowed_fields[0] if allowed_fields else 'rating'
    
    # Validate sort order
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    return sort_by, sort_order


def validate_filters(allowed_filters: dict) -> dict:
    """
    Validate and extract filter parameters
    
    Args:
        allowed_filters: Dict of {param_name: validation_function}
        
    Returns:
        Dictionary of validated filters
    """
    filters = {}
    
    for param, validator in allowed_filters.items():
        value = request.args.get(param)
        if value is not None:
            try:
                filters[param] = validator(value)
            except (ValueError, TypeError):
                # Skip invalid filters
                continue
    
    return filters
