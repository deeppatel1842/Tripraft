# Purpose: Cache Infrastructure Package Provides Redis-based caching with graceful fallback.
"""
Cache Infrastructure Package

Provides Redis-based caching with graceful fallback.
"""
from .redis import (RedisClient, cache_response, check_lockout, clear_lockout,
                    invalidate_cache, mark_device_trusted, record_failed_login,
                    redis_client)

__all__ = [
    'RedisClient',
    'cache_response',
    'check_lockout',
    'clear_lockout',
    'invalidate_cache',
    'mark_device_trusted',
    'record_failed_login',
    'redis_client',
]
