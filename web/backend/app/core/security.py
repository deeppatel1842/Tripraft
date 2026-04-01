"""
Security Utilities
CORS configuration, security headers, CSRF protection, and related utilities.
"""
import logging
import secrets

from flask import abort, request

logger = logging.getLogger(__name__)

_CSRF_SAFE_METHODS = frozenset(('GET', 'HEAD', 'OPTIONS'))
_CSRF_COOKIE = 'csrf_token'
_CSRF_HEADER = 'X-CSRF-Token'

# Auth endpoints that must be reachable before a valid session exists.
# CSRF protection is meaningless here: there is no authenticated state to hijack.
_CSRF_EXEMPT_PREFIXES = (
    '/api/v1/auth/',
    '/api/v1/group-planner/invitations/',   # accept-invitation is pre-auth
)


def add_security_headers(response):
    """Add security headers to every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https://*.tile.openstreetmap.org https://*.googleapis.com; "
        "connect-src 'self' https://app.ticketmaster.com; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    return response


def add_cors_fallback(response, allowed_origins):
    """CORS fallback for origins not handled by flask-cors."""
    origin = request.headers.get('Origin')
    if origin and origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = (
            'Content-Type, Authorization, Accept, Origin, X-CSRF-Token'
        )
        response.headers['Access-Control-Expose-Headers'] = 'Content-Type'
    return response


# ---------------------------------------------------------------------------
# CSRF — Double-Submit Cookie Pattern
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_hex(32)


def set_csrf_cookie(response, token: str) -> None:
    """Set the CSRF token as a readable (non-httpOnly) cookie."""
    from app.core.config import Config
    response.set_cookie(
        _CSRF_COOKIE,
        token,
        max_age=Config.JWT_ACCESS_TOKEN_EXPIRES,
        httponly=False,
        secure=Config.COOKIE_SECURE,
        samesite=Config.COOKIE_SAMESITE,
        path=Config.COOKIE_PATH,
    )


def validate_csrf() -> None:
    """
    Before-request hook: validate CSRF on state-changing methods.
    Compares the csrf_token cookie with the X-CSRF-Token header.
    Skips safe methods, pre-auth endpoints, and unauthenticated requests.
    """
    if request.method in _CSRF_SAFE_METHODS:
        return

    # Auth endpoints are pre-authentication — no authenticated state to protect.
    path = request.path
    if any(path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES):
        return

    if not request.cookies.get('access_token'):
        return

    cookie_token = request.cookies.get(_CSRF_COOKIE, '')
    header_token = request.headers.get(_CSRF_HEADER, '')

    if not cookie_token or not header_token:
        logger.warning('CSRF token missing: cookie=%s header=%s path=%s',
                       bool(cookie_token), bool(header_token), request.path)
        abort(403, description='CSRF token missing')

    # Ensure both values are non-empty strings before constant-time comparison
    if len(cookie_token) == 0 or len(header_token) == 0:
        abort(403, description='CSRF token empty')

    if not secrets.compare_digest(cookie_token, header_token):
        logger.warning('CSRF token mismatch for %s %s', request.method, request.path)
        abort(403, description='CSRF validation failed')
