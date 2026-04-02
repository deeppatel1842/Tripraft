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
    vary_on_query: bool = True,
    vary_on_user: bool = False
) -> Callable[[F], F]:
    """
    Decorator to cache Flask route responses in Redis.
    
    Adds Cache-Control, ETag, and X-Cache headers automatically.
    Supports If-None-Match conditional requests (304 Not Modified).
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
            user_part = ''
            if vary_on_user:
                from flask import g
                user_part = str(getattr(g, 'user_id', 'anon'))
            key_data = f'{path}:{query}:{user_part}'
            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
            cache_key = f'{key_prefix}:{key_hash}'

            # Cache-Control: private for user-specific, public otherwise
            cache_control = f'private, max-age={ttl}' if vary_on_user else f'public, max-age={ttl}'

            # Try cache hit
            cached = redis_client.get(cache_key)
            if cached is not None:
                cached_str = cached if isinstance(cached, str) else cached.decode()

                try:
                    envelope = json.loads(cached_str)
                    if isinstance(envelope, dict) and '_body' in envelope:
                        body = envelope['_body']
                        extra_headers = envelope.get('_headers', {})
                    else:
                        body = cached_str
                        extra_headers = {}
                except (json.JSONDecodeError, TypeError):
                    body = cached_str
                    extra_headers = {}

                etag = hashlib.md5(body.encode()).hexdigest()[:16]

                # Support If-None-Match -> 304
                client_etag = request.headers.get('If-None-Match')
                if client_etag and client_etag.strip('"') == etag:
                    resp = make_response('', 304)
                    resp.headers['X-Cache'] = 'HIT'
                    resp.headers['Cache-Control'] = cache_control
                    resp.headers['ETag'] = f'"{etag}"'
                    return resp

                response = make_response(body)
                response.headers['X-Cache'] = 'HIT'
                response.headers['Content-Type'] = 'application/json'
                response.headers['ETag'] = f'"{etag}"'
                response.headers['Cache-Control'] = cache_control
                for k, v in extra_headers.items():
                    response.headers[k] = v
                return response

            # Cache miss -- execute function
            result = func(*args, **kwargs)

            # Cache the response (body + custom headers)
            if hasattr(result, 'get_data'):
                body = result.get_data(as_text=True)
                _cacheable_headers = (
                    'X-Total-Count', 'X-Page', 'X-Per-Page', 'ETag',
                )
                hdrs = {
                    k: result.headers[k]
                    for k in _cacheable_headers
                    if k in result.headers
                }
                cache_envelope = json.dumps({'_body': body, '_headers': hdrs})
                redis_client.set(cache_key, cache_envelope, ex=ttl)

                # Add cache headers to miss response
                etag = hashlib.md5(body.encode()).hexdigest()[:16]
                result.headers['X-Cache'] = 'MISS'
                result.headers['ETag'] = f'"{etag}"'
                result.headers['Cache-Control'] = cache_control

            return result
        return wrapper  # type: ignore
    return decorator


def invalidate_cache(pattern: str) -> int:
    """Invalidate all cache keys matching a pattern."""
    return redis_client.delete_pattern(pattern)


# ---------------------------------------------------------------------------
# Account lockout — production-grade brute-force protection
# ---------------------------------------------------------------------------

import random
import time

from app.core.config import Config as _Cfg

_LOCKOUT_PREFIX = 'lockout:'
_LOCKOUT_IP_PREFIX = 'lockout:ip:'
_LOCKOUT_CYCLE_PREFIX = 'lockout:cycle:'
_LOCKOUT_GLOBAL_KEY = 'lockout:global:counter'
_LOCKOUT_TRUSTED_PREFIX = 'lockout:trusted:'

_BASE_MAX_ATTEMPTS = _Cfg.LOCKOUT_MAX_ATTEMPTS
_BASE_TTL = _Cfg.LOCKOUT_BASE_TTL
_TTL_JITTER_PERCENT = _Cfg.LOCKOUT_TTL_JITTER_PERCENT
_BACKOFF_MULTIPLIERS = [1, 2, 4]  # 15m, 30m, 60m
_CYCLE_WINDOW = _Cfg.LOCKOUT_CYCLE_WINDOW
_IP_MAX_ATTEMPTS = _Cfg.LOCKOUT_IP_MAX_ATTEMPTS
_IP_TTL = _Cfg.LOCKOUT_IP_TTL
_GLOBAL_MAX_PER_MINUTE = _Cfg.LOCKOUT_GLOBAL_MAX_PER_MINUTE
_GLOBAL_TTL = _Cfg.LOCKOUT_GLOBAL_TTL
_TRUSTED_THRESHOLD_MULTIPLIER = _Cfg.LOCKOUT_TRUSTED_MULTIPLIER

_lockout_logger = logging.getLogger('lockout')


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def _ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _jittered_ttl(base: int) -> int:
    """Add +-10% jitter to avoid synchronized expiry storms."""
    jitter = int(base * _TTL_JITTER_PERCENT)
    return base + random.randint(-jitter, jitter)


def _lockout_ttl_for_cycle(cycle_count: int) -> int:
    """Exponential backoff: 15m -> 30m -> 60m based on lockout cycles in 24h."""
    idx = min(cycle_count, len(_BACKOFF_MULTIPLIERS) - 1)
    return _jittered_ttl(_BASE_TTL * _BACKOFF_MULTIPLIERS[idx])


def _get_max_attempts(email: str, device_id: Optional[str] = None) -> int:
    """Trusted devices get a higher threshold."""
    if device_id and redis_client.available:
        key = f'{_LOCKOUT_TRUSTED_PREFIX}{_email_hash(email)}:{device_id}'
        if redis_client.exists(key):
            return _BASE_MAX_ATTEMPTS * _TRUSTED_THRESHOLD_MULTIPLIER
    return _BASE_MAX_ATTEMPTS


def mark_device_trusted(email: str, device_id: str, ttl: int = 2592000) -> None:
    """Mark a device as trusted for 30 days (called after MFA or known-device login)."""
    if not redis_client.available or not device_id:
        return
    key = f'{_LOCKOUT_TRUSTED_PREFIX}{_email_hash(email)}:{device_id}'
    redis_client.set(key, '1', ex=ttl)


# ---- core lockout operations (atomic) ----

def check_lockout(email: str, ip: Optional[str] = None, device_id: Optional[str] = None) -> Optional[int]:
    """
    Return remaining lockout seconds if the account or IP is locked, else None.
    Uses atomic reads only.
    """
    if not redis_client.available:
        return None

    client = redis_client._client

    # 1. Global flood check
    try:
        global_count = client.get(_LOCKOUT_GLOBAL_KEY)
        if global_count and int(global_count) >= _GLOBAL_MAX_PER_MINUTE:
            _lockout_logger.critical(
                'GLOBAL_FLOOD_DETECTED count=%s', global_count,
            )
            ttl = client.ttl(_LOCKOUT_GLOBAL_KEY)
            return max(ttl, 1)
    except Exception:
        pass

    # 2. IP-based throttle
    if ip:
        ip_key = f'{_LOCKOUT_IP_PREFIX}{_ip_hash(ip)}'
        try:
            ip_count = client.get(ip_key)
            if ip_count and int(ip_count) >= _IP_MAX_ATTEMPTS:
                ttl = client.ttl(ip_key)
                _lockout_logger.warning(
                    'IP_LOCKED ip_hash=%s count=%s ttl=%s',
                    _ip_hash(ip), ip_count, ttl,
                )
                return max(ttl, 1)
        except Exception:
            pass

    # 3. Per-email lockout
    email_key = f'{_LOCKOUT_PREFIX}{_email_hash(email)}'
    max_attempts = _get_max_attempts(email, device_id)
    try:
        count = client.get(email_key)
        if count and int(count) >= max_attempts:
            ttl = client.ttl(email_key)
            _lockout_logger.warning(
                'ACCOUNT_LOCKED email_hash=%s count=%s ttl=%s',
                _email_hash(email), count, ttl,
            )
            return max(ttl, 1)
    except Exception:
        pass

    return None


def record_failed_login(email: str, ip: Optional[str] = None) -> int:
    """
    Atomically increment failed-login counters (email + IP + global).
    Returns the new per-email count.
    """
    if not redis_client.available:
        return 0

    client = redis_client._client
    eh = _email_hash(email)

    # Get current cycle count for backoff calculation
    cycle_key = f'{_LOCKOUT_CYCLE_PREFIX}{eh}'
    try:
        cycle_count = int(client.get(cycle_key) or 0)
    except Exception:
        cycle_count = 0

    email_key = f'{_LOCKOUT_PREFIX}{eh}'
    ttl = _lockout_ttl_for_cycle(cycle_count)

    # Atomic INCR + EXPIRE via Lua script (no race between INCR and EXPIRE)
    _LUA_INCR_EXPIRE = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """
    try:
        count = client.eval(_LUA_INCR_EXPIRE, 1, email_key, ttl)
    except Exception:
        count = 0

    # If the account just became locked, increment the 24h cycle counter
    max_attempts = _get_max_attempts(email)
    if count == max_attempts:
        try:
            client.eval(_LUA_INCR_EXPIRE, 1, cycle_key, _CYCLE_WINDOW)
        except Exception:
            pass

    # Atomic INCR for IP counter
    if ip:
        ip_key = f'{_LOCKOUT_IP_PREFIX}{_ip_hash(ip)}'
        try:
            client.eval(_LUA_INCR_EXPIRE, 1, ip_key, _IP_TTL)
        except Exception:
            pass

    # Atomic INCR for global counter
    try:
        client.eval(_LUA_INCR_EXPIRE, 1, _LOCKOUT_GLOBAL_KEY, _GLOBAL_TTL)
    except Exception:
        pass

    # Structured log
    _lockout_logger.info(
        'LOGIN_FAILED email_hash=%s ip_hash=%s count=%d cycle=%d reason=bruteforce',
        eh,
        _ip_hash(ip) if ip else 'none',
        count,
        cycle_count,
    )

    return count


def clear_lockout(email: str) -> None:
    """Reset the per-email lockout counter after a successful login."""
    redis_client.delete(f'{_LOCKOUT_PREFIX}{_email_hash(email)}')
