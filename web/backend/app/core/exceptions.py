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

    def __init__(self, message=None, status_code=None, payload=None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        super().__init__(self.message)

    def to_dict(self):
        rv = {'success': False, 'message': self.message}
        if self.payload:
            rv['errors'] = self.payload
        return rv


class ValidationError(AppError):
    """Invalid input data (400)."""
    status_code = 400
    default_message = 'Validation failed'


class AuthenticationError(AppError):
    """Missing or invalid credentials (401)."""
    status_code = 401
    default_message = 'Authentication required'


class AuthorizationError(AppError):
    """Authenticated but insufficient permissions (403)."""
    status_code = 403
    default_message = 'Permission denied'


class NotFoundError(AppError):
    """Requested resource does not exist (404)."""
    status_code = 404
    default_message = 'Resource not found'


class ConflictError(AppError):
    """Duplicate or conflicting state (409)."""
    status_code = 409
    default_message = 'Resource conflict'


class RateLimitError(AppError):
    """Too many requests (429)."""
    status_code = 429
    default_message = 'Rate limit exceeded'


class ExternalServiceError(AppError):
    """Third-party service failure (502)."""
    status_code = 502
    default_message = 'External service unavailable'
