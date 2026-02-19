"""
Redis Cache Client — Singleton with graceful fallback.

Provides get/set/delete/exists with JSON serialization and
a route-level caching decorator for Flask views.
"""
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from flask import Flask, make_response, request

logger = logging.getLogger(__name__)

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])

# Redis client type (loaded dynamically)
_redis_module = None


def _get_redis_module():
    """Lazy import redis module."""
    global _redis_module
    if _redis_module is None:
        try:
            import redis as redis_pkg
            _redis_module = redis_pkg
        except ImportError:
            _redis_module = False
    return _redis_module if _redis_module else None


class RedisClient:
    """Thread-safe Redis wrapper with automatic JSON serialization."""

    def __init__(self) -> None:
        self._client = None
        self._available = False

    def init_app(self, app: Flask) -> None:
        """Connect to Redis using the app's REDIS_URL config."""
        redis_pkg = _get_redis_module()
        if not redis_pkg:
            logger.warning('redis package not installed — cache disabled')
            return

        url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        max_connections = app.config.get('REDIS_MAX_CONNECTIONS', 50)
        socket_timeout = app.config.get('REDIS_SOCKET_TIMEOUT', 5)
        
        try:
            self._client = redis_pkg.from_url(
                url,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )
            self._client.ping()
            self._available = True
            # Log without sensitive parts
            safe_url = url.split('@')[-1] if '@' in url else url
            logger.info('Redis connected: %s', safe_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Redis unavailable — cache disabled: %s', exc)
            self._client = None
            self._available = False

    @property
    def available(self) -> bool:
        """Check if Redis is available."""
        return self._available and self._client is not None

    def get(self, key: str) -> Optional[str]:
        """Get raw string value. Returns None when Redis is down."""
        if not self.available:
            return None
        try:
            return self._client.get(key)
        except Exception:  # noqa: BLE001
            return None

    def set(
        self, key: str, value: str, ex: Optional[int] = None
    ) -> bool:
        """Set raw string value with optional TTL (seconds)."""
        if not self.available:
            return False
        try:
            return bool(self._client.set(key, value, ex=ex))
        except Exception:  # noqa: BLE001
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        if not self.available or not keys:
            return 0
        try:
            return self._client.delete(*keys)
        except Exception:  # noqa: BLE001
            return 0

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.available:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception:  # noqa: BLE001
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern (e.g. 'locations:*')."""
        if not self.available:
            return 0
        try:
            keys = list(self._client.keys(pattern))
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception:  # noqa: BLE001
            return 0

    def get_json(self, key: str) -> Optional[Any]:
        """Get and deserialize a JSON value."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_json(
        self, key: str, value: Any, ex: Optional[int] = None
    ) -> bool:
        """Serialize value to JSON and store with optional TTL."""
        try:
            return self.set(key, json.dumps(value, default=str), ex=ex)
        except (TypeError, ValueError):
            return False

    def info(self) -> dict:
        """Return Redis server info dict, or empty dict if unavailable."""
        if not self.available:
            return {}
        try:
            return self._client.info()
        except Exception:  # noqa: BLE001
            return {}


# Singleton instance
redis_client = RedisClient()


def cache_response(
    key_prefix: str = 'route',
    ttl: int = 300,
    vary_on_query: bool = True
) -> Callable[[F], F]:
    """
    Decorator to cache Flask route responses in Redis.
    
    Args:
        key_prefix: Prefix for cache keys
        ttl: Time-to-live in seconds (default: 5 minutes)
        vary_on_query: Include query string in cache key
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if Redis unavailable
            if not redis_client.available:
                return func(*args, **kwargs)

            # Build cache key
            path = request.path
            query = request.query_string.decode() if vary_on_query else ''
            key_data = f'{path}:{query}'
            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
            cache_key = f'{key_prefix}:{key_hash}'

            # Try cache hit
            cached = redis_client.get(cache_key)
            if cached is not None:
                response = make_response(cached)
                response.headers['X-Cache'] = 'HIT'
                response.headers['Content-Type'] = 'application/json'
                return response

            # Cache miss — execute function
            result = func(*args, **kwargs)

            # Cache the response
            if hasattr(result, 'get_data'):
                data = result.get_data(as_text=True)
                redis_client.set(cache_key, data, ex=ttl)

            return result
        return wrapper  # type: ignore
    return decorator


def invalidate_cache(pattern: str) -> int:
    """Invalidate all cache keys matching a pattern."""
    return redis_client.delete_pattern(pattern)
