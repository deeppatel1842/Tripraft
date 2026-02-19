"""
Cache Infrastructure Package

Provides Redis-based caching with graceful fallback.
"""
from .redis import RedisClient, cache_response, invalidate_cache, redis_client

__all__ = [
    'RedisClient',
    'cache_response',
    'invalidate_cache',
    'redis_client',
]
