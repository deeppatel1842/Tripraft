# Purpose: Rate Limiter Configuration Centralized rate limiting using Flask-Limiter with tiered limits and response headers.
"""
Rate Limiter Configuration
Centralized rate limiting using Flask-Limiter with tiered limits and response headers.

Every response includes:
  X-RateLimit-Limit: max requests in window
  X-RateLimit-Remaining: requests left
  X-RateLimit-Reset: unix timestamp when window resets
  Retry-After: seconds until next allowed request (only on 429)
"""
import logging
import ipaddress
import time
from functools import wraps
from typing import Callable, Optional, TypeVar

from flask import Flask, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable)


def _get_rate_limit_key() -> str:
    """
    Get the key for rate limiting.
    Authenticated users: keyed by user_id (more generous limits).
    Unauthenticated: keyed by IP address.
    """
    user_id = getattr(g, 'user_id', None)
    if user_id:
        return f'user:{user_id}'
    # X-Forwarded-For is client-controlled unless the immediate peer is a
    # configured proxy.  Do not merely validate its length: that lets a
    # caller rotate arbitrary values to evade an IP rate limit.
    remote_address = get_remote_address()
    if _is_trusted_proxy(remote_address):
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        client_ip = forwarded_for.split(',', 1)[0].strip()
        try:
            return f'ip:{ipaddress.ip_address(client_ip)}'
        except ValueError:
            logger.warning('Ignoring malformed X-Forwarded-For from trusted proxy')
    return f'ip:{remote_address}'


def _is_trusted_proxy(address: str | None) -> bool:
    """Whether the direct peer matches a configured proxy IP or CIDR."""
    if not address:
        return False
    try:
        peer = ipaddress.ip_address(address)
    except ValueError:
        return False

    from app.core.config import Config
    for configured_address in Config.TRUSTED_PROXY_IPS:
        try:
            if peer in ipaddress.ip_network(configured_address, strict=False):
                return True
        except ValueError:
            logger.warning('Ignoring invalid TRUSTED_PROXY_IPS entry')
    return False


# Limiter instance (configured at app init time)
limiter: Optional[Limiter] = None


def init_rate_limiter(app: Flask, redis_url: Optional[str] = None) -> None:
    """Initialize rate limiter with Flask app."""
    global limiter

    if not app.config.get('RATELIMIT_ENABLED', False):
        logger.info('Rate limiting disabled')
        return

    storage_uri = redis_url or app.config.get('REDIS_URL', 'memory://')
    default_limit = app.config.get('RATELIMIT_DEFAULT', '100 per hour')

    limiter = Limiter(
        key_func=_get_rate_limit_key,
        app=app,
        default_limits=[default_limit],
        storage_uri=storage_uri,
        strategy='fixed-window',
    )

    # Add rate limit headers to every response
    @app.after_request
    def _inject_rate_limit_headers(response):
        """Inject X-RateLimit-* headers into every response."""
        # Flask-Limiter sets these attributes when rate limiting is active
        rl_limit = response.headers.get('X-RateLimit-Limit')
        rl_remaining = response.headers.get('X-RateLimit-Remaining')
        rl_reset = response.headers.get('X-RateLimit-Reset')

        if not rl_limit:
            # Flask-Limiter may not set headers on exempt routes;
            # we leave them absent rather than faking values.
            pass

        if response.status_code == 429:
            # Ensure Retry-After is set
            if 'Retry-After' not in response.headers:
                reset = rl_reset
                if reset:
                    try:
                        retry_after = max(int(float(reset)) - int(time.time()), 1)
                    except (ValueError, TypeError):
                        retry_after = 60
                else:
                    retry_after = 60
                response.headers['Retry-After'] = str(retry_after)

        return response

    logger.info('Rate limiter initialized: %s (storage: %s)',
                default_limit, 'redis' if 'redis' in storage_uri else 'memory')


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
    from app.core.config import Config
    return limit_api(Config.RATE_LIMITS['auth'])


def limit_search() -> Callable[[F], F]:
    """Rate limit for search endpoints."""
    from app.core.config import Config
    return limit_api(Config.RATE_LIMITS['search'])


def limit_write() -> Callable[[F], F]:
    """Rate limit for write operations."""
    from app.core.config import Config
    return limit_api(Config.RATE_LIMITS['create'])


def get_rate_limit(operation_type: str) -> str:
    """Get the rate limit string for a given operation type."""
    from app.core.config import Config
    return Config.RATE_LIMITS.get(operation_type, '50 per minute')
