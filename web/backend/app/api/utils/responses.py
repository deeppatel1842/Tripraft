"""
Standardized API response utilities
Provides consistent response formatting across all endpoints.
"""
from typing import Any, Dict, Optional

from flask import jsonify


def success_response(data: Any, message: str = "Success", status_code: int = 200, pagination: Optional[Dict] = None):
    """
    Create a standardized success response
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        pagination: Optional pagination metadata
        
    Returns:
        Flask JSON response
    """
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    if pagination:
        response["pagination"] = pagination
    return jsonify(response), status_code


def error_response(message: str, status_code: int = 400, errors: Optional[Dict] = None):
    """
    Create a standardized error response
    
    Args:
        message: Error message
        status_code: HTTP status code
        errors: Additional error details
        
    Returns:
        Flask JSON response
    """
    response = {
        "success": False,
        "message": message,
        "data": None
    }
    
    if errors:
        response["errors"] = errors
    
    return jsonify(response), status_code


def paginated_response(
    data: list,
    total: int,
    limit: int,
    offset: int,
    message: str = "Success"
):
    """
    Create a paginated response
    
    Args:
        data: List of items for current page
        total: Total number of items
        limit: Items per page
        offset: Current offset
        message: Success message
        
    Returns:
        Flask JSON response
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(data),
            "has_more": (offset + limit) < total
        }
    }
    return jsonify(response), 200


def not_found_response(resource: str = "Resource"):
    """
    Create a 404 not found response
    
    Args:
        resource: Name of the resource that wasn't found
        
    Returns:
        Flask JSON response
    """
    return error_response(
        message=f"{resource} not found",
        status_code=404
    )
