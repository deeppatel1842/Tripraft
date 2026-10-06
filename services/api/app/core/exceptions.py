# Purpose: Custom Exception Hierarchy Framework-agnostic exception classes for the entire backend.
"""
Custom Exception Hierarchy
Framework-agnostic exception classes for the entire backend.
Each exception carries an HTTP status code and optional error payload
so the API layer can translate them into proper responses.
"""


class AppError(Exception):
    """Base application error. All custom exceptions inherit from this."""
    status_code = 500
    default_message = 'An unexpected error occurred'
    error_code = 'INTERNAL_ERROR'

    def __init__(self, message=None, status_code=None, payload=None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        super().__init__(self.message)

    def to_dict(self):
        rv = {
            'success': False,
            'data': None,
            'error': {
                'code': self.error_code,
                'message': self.message,
            },
        }
        if self.payload:
            rv['error']['details'] = self.payload
        return rv


class ValidationError(AppError):
    """Invalid input data (400)."""
    status_code = 400
    default_message = 'Validation failed'
    error_code = 'VALIDATION_ERROR'


class AuthenticationError(AppError):
    """Missing or invalid credentials (401)."""
    status_code = 401
    default_message = 'Authentication required'
    error_code = 'AUTH_REQUIRED'


class AuthorizationError(AppError):
    """Authenticated but insufficient permissions (403)."""
    status_code = 403
    default_message = 'Permission denied'
    error_code = 'FORBIDDEN'


class NotFoundError(AppError):
    """Requested resource does not exist (404)."""
    status_code = 404
    default_message = 'Resource not found'
    error_code = 'NOT_FOUND'


class ConflictError(AppError):
    """Duplicate or conflicting state (409)."""
    status_code = 409
    default_message = 'Resource conflict'
    error_code = 'CONFLICT'


class RateLimitError(AppError):
    """Too many requests (429)."""
    status_code = 429
    default_message = 'Rate limit exceeded'
    error_code = 'RATE_LIMITED'


class UnprocessableError(AppError):
    """Schema / payload validation failure (422)."""
    status_code = 422
    default_message = 'Validation failed'
    error_code = 'UNPROCESSABLE'


class GoneError(AppError):
    """Resource has expired or been permanently removed (410)."""
    status_code = 410
    default_message = 'Resource is no longer available'
    error_code = 'EXPIRED'


class ExternalServiceError(AppError):
    """External service (Ticketmaster, Nominatim, etc.) failed (502)."""
    status_code = 502
    default_message = 'External service unavailable'
    error_code = 'EXTERNAL_SERVICE_ERROR'


class ServiceUnavailableError(AppError):
    """Database/Redis unavailable (503)."""
    status_code = 503
    default_message = 'Service temporarily unavailable'
    error_code = 'SERVICE_UNAVAILABLE'
