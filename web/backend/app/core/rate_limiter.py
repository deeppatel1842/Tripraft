"""
Rate Limiter Configuration
Centralized rate limiting using Flask-Limiter.
"""
import logging
from typing import Callable, Optional, TypeVar

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable)


def _get_rate_limit_key() -> str:
    """
    Get the key for rate limiting.
    Uses X-Forwarded-For header if behind proxy, otherwise remote address.
    """
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return get_remote_address()


# Limiter instance (configured at app init time)
limiter: Optional[Limiter] = None


def init_rate_limiter(app: Flask, redis_url: Optional[str] = None) -> None:
    """
    Initialize rate limiter with Flask app.
    
    Args:
        app: Flask application instance
        redis_url: Redis URL for distributed rate limiting (optional)
    """
    global limiter
    
    if not app.config.get('RATELIMIT_ENABLED', False):
        logger.info('Rate limiting disabled')
        return

    storage_uri = redis_url if redis_url else 'memory://'
    default_limit = app.config.get('RATELIMIT_DEFAULT', '100 per hour')

    limiter = Limiter(
        key_func=_get_rate_limit_key,
        app=app,
        default_limits=[default_limit],
        storage_uri=storage_uri,
        strategy='fixed-window',
    )

    logger.info('Rate limiter initialized: %s (storage: %s)',
                default_limit, 'redis' if redis_url else 'memory')


def limit_api(limit_string: str) -> Callable[[F], F]:
    """Decorator to apply rate limit to an endpoint."""
    if limiter:
        return limiter.limit(limit_string)
    # No-op decorator when limiter is disabled
    def decorator(f: F) -> F:
        return f
    return decorator


def limit_auth() -> Callable[[F], F]:
    """Rate limit for authentication endpoints (stricter)."""
    return limit_api('5 per minute')


def limit_search() -> Callable[[F], F]:
    """Rate limit for search endpoints."""
    return limit_api('30 per minute')


def limit_write() -> Callable[[F], F]:
    """Rate limit for write operations."""
    return limit_api('20 per minute')


# Per-operation rate limits (used via @limiter.limit(get_rate_limit('create')))
RATE_LIMITS = {
    'read_light':  '100 per minute',
    'read_heavy':  '30 per minute',
    'create':      '20 per minute',
    'update':      '30 per minute',
    'delete':      '10 per minute',
    'settle':      '10 per minute',
    'invitation':  '10 per minute',
    'auth':        '5 per minute',
}


def get_rate_limit(operation_type: str) -> str:
    """Get the rate limit string for a given operation type."""
    return RATE_LIMITS.get(operation_type, '50 per minute')
