# Purpose: Standardized API response utilities. Provides consistent response formatting across all endpoints.
"""Standardized API response utilities.
Provides consistent response formatting across all endpoints.
Every route MUST return responses through these helpers.

Response Envelope:
{
  "success": true/false,
  "data": ...,           // null on errors
  "error": {...},        // only on errors
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "version": "v1",
    "response_time_ms": 12.34,
    "pagination": {...}  // only on paginated responses
  }
}
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import g, jsonify


def _response_time_ms() -> Optional[float]:
    """Calculate request duration from g.start_time if available."""
    start = getattr(g, 'start_time', None)
    if start is not None:
        return round((time.time() - start) * 1000, 2)
    return None


def _build_meta(pagination: Optional[Dict] = None) -> dict:
    """Build the standard meta block."""
    meta = {
        "request_id": getattr(g, 'request_id', None),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "v1",
    }
    rt = _response_time_ms()
    if rt is not None:
        meta["response_time_ms"] = rt
    if pagination:
        meta["pagination"] = pagination
    return meta


def _build_envelope(success: bool, data: Any, **extras) -> dict:
    """Build the standard response envelope."""
    envelope = {
        "success": success,
        "data": data,
        "meta": _build_meta(extras.get('pagination')),
    }
    if not success and 'error' in extras:
        envelope["error"] = extras["error"]
    return envelope


def success_response(data: Any = None, message: str = "Success", status_code: int = 200,
                     pagination: Optional[Dict] = None, meta: Optional[Dict] = None):
    """Create a standardized success response."""
    envelope = _build_envelope(True, data, pagination=pagination)
    envelope["message"] = message
    # Merge extra meta if provided
    if meta:
        envelope["meta"].update(meta)
    return jsonify(envelope), status_code


def created_response(data: Any, message: str = "Created"):
    """201 Created -- use for POST that creates a new resource."""
    envelope = _build_envelope(True, data)
    envelope["message"] = message
    return jsonify(envelope), 201


def no_content_response():
    """204 No Content -- use for DELETE that removes a resource."""
    return '', 204


def error_response(message: str, status_code: int = 400, errors: Optional[Dict] = None,
                   code: Optional[str] = None):
    """Create a standardized error response."""
    error_obj = {"code": code or _status_to_code(status_code), "message": message}
    if errors:
        error_obj["details"] = errors
    envelope = _build_envelope(False, None, error=error_obj)
    return jsonify(envelope), status_code


def paginated_response(
    data: list,
    total: int,
    limit: int,
    offset: int,
    message: str = "Success"
):
    """Create a paginated response with standard pagination meta."""
    page = (offset // limit) + 1 if limit > 0 else 1
    total_pages = -(-total // limit) if limit > 0 else 1  # ceiling division
    pagination = {
        "page": page,
        "per_page": limit,
        "total": total,
        "total_pages": total_pages,
        "has_next": (offset + limit) < total,
        "has_prev": page > 1,
    }
    envelope = _build_envelope(True, data, pagination=pagination)
    return jsonify(envelope), 200


def not_found_response(resource: str = "Resource"):
    """Create a 404 not found response."""
    return error_response(
        message=f"{resource} not found",
        status_code=404,
        code="NOT_FOUND",
    )


def validation_error_response(errors: Dict, message: str = "Validation failed"):
    """422 Unprocessable Entity -- use for schema validation failures."""
    return error_response(message=message, status_code=422, errors=errors,
                          code="VALIDATION_ERROR")


# HTTP status → error code mapping
_STATUS_CODES = {
    400: 'VALIDATION_ERROR',
    401: 'AUTH_REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT_FOUND',
    409: 'CONFLICT',
    410: 'EXPIRED',
    422: 'UNPROCESSABLE',
    429: 'RATE_LIMITED',
    500: 'INTERNAL_ERROR',
    502: 'EXTERNAL_SERVICE_ERROR',
    503: 'SERVICE_UNAVAILABLE',
}


def _status_to_code(status_code: int) -> str:
    """Map HTTP status code to standard error code."""
    return _STATUS_CODES.get(status_code, 'INTERNAL_ERROR')
