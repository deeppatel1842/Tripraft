"""
Rate Limiting Middleware
Token bucket algorithm using Redis for 1000+ concurrent users

Features:
- Per-user rate limiting
- Global rate limiting
- Configurable limits for read/write operations
- Redis-backed (distributed rate limiting)
- Graceful degradation if Redis unavailable
"""

from functools import wraps
from flask import Flask
import time
import logging
from typing import Optional

from ..exceptions import RateLimitExceededError
from ..config import rate_limit_config
from .auth import get_current_user

logger = logging.getLogger(__name__)

# Global rate limiter instance
_rate_limiter = None


class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(self, redis_client):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.enabled = redis_client is not None
        
        if self.enabled:
            logger.info("✅ Rate limiter initialized with Redis")
        else:
            logger.warning("⚠️  Rate limiter disabled (Redis not available)")
    
    def check_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int = 60
    ):
        """
        Check if request is within rate limit using token bucket algorithm
        
        Args:
            key: Rate limit key (e.g., "user:123:reads")
            max_requests: Max requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            tuple: (is_allowed: bool, retry_after: Optional[int])
        """
        if not self.enabled:
            # Fail open - allow request if Redis unavailable
            return True, None
        
        try:
            current_time = int(time.time())
            window_key = f"{key}:{current_time // window_seconds}"
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Increment counter
            pipe.incr(window_key)
            
            # Set expiry on first request
            pipe.expire(window_key, window_seconds)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[0]
            
            # Check limit
            if current_count > max_requests:
                retry_after = window_seconds - (current_time % window_seconds)
                logger.warning(
                    "Rate limit exceeded for %s: %d/%d (retry after %ds)",
                    key, current_count, max_requests, retry_after
                )
                return False, retry_after
            
            return True, None
            
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Rate limit check error (Redis): %s", str(exc))
            # Fail open - allow request if Redis error
            return True, None
    
    def check_user_limit(self, user_id: str, limit_type: str = 'read'):
        """
        Check per-user rate limit
        
        Args:
            user_id: User ID
            limit_type: 'read' or 'write'
        
        Returns:
            tuple: (is_allowed: bool, retry_after: Optional[int])
        """
        if limit_type == 'read':
            max_requests = rate_limit_config.READS_PER_MINUTE
        elif limit_type == 'write':
            max_requests = rate_limit_config.WRITES_PER_MINUTE
        else:
            max_requests = 60  # Default
        
        key = f"expense:ratelimit:user:{user_id}:{limit_type}"
        return self.check_rate_limit(key, max_requests, rate_limit_config.WINDOW_SECONDS)
    
    def check_global_limit(self, limit_type: str = 'read'):
        """
        Check global rate limit (for all users combined)
        
        Args:
            limit_type: 'read' or 'write'
        
        Returns:
            tuple: (is_allowed: bool, retry_after: Optional[int])
        """
        if limit_type == 'read':
            max_requests = rate_limit_config.GLOBAL_READS_PER_SECOND
        elif limit_type == 'write':
            max_requests = rate_limit_config.GLOBAL_WRITES_PER_SECOND
        else:
            max_requests = 1000  # Default
        
        key = f"expense:ratelimit:global:{limit_type}"
        return self.check_rate_limit(key, max_requests, 1)  # Per second


def init_limiter(app: Flask, redis_client):
    """
    Initialize rate limiter with Flask app
    
    Args:
        app: Flask application
        redis_client: Redis client instance
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(redis_client)
    app.extensions['rate_limiter'] = _rate_limiter
    logger.info("Rate limiter registered with Flask app")


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get rate limiter instance"""
    return _rate_limiter


def rate_limit(limit_type: str = 'read', check_global: bool = True):
    """
    Rate limit decorator
    
    Args:
        limit_type: 'read' or 'write'
        check_global: Whether to also check global limit
    
    Usage:
        @require_auth
        @rate_limit('read')
        def my_route():
            pass
        
        @require_auth
        @rate_limit('write')
        def create_expense():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_rate_limiter()
            
            if not limiter or not limiter.enabled:
                # Rate limiting disabled - allow through
                return f(*args, **kwargs)
            
            # Get current user (must have @require_auth before this decorator)
            try:
                current_user = get_current_user()
                user_id = current_user['uid']
            except (KeyError, AttributeError):
                # No authenticated user - skip rate limiting
                return f(*args, **kwargs)
            
            # Check per-user limit
            allowed, retry_after = limiter.check_user_limit(user_id, limit_type)
            if not allowed:
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {rate_limit_config.READS_PER_MINUTE if limit_type == 'read' else rate_limit_config.WRITES_PER_MINUTE} {limit_type} requests per minute",
                    retry_after=retry_after
                )
            
            # Check global limit (optional)
            if check_global:
                allowed, retry_after = limiter.check_global_limit(limit_type)
                if not allowed:
                    raise RateLimitExceededError(
                        f"System capacity exceeded. Please try again in {retry_after} seconds.",
                        retry_after=retry_after
                    )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit_read(f):
    """
    Shorthand decorator for read operations
    
    Usage:
        @require_auth
        @rate_limit_read
        def get_expenses():
            pass
    """
    return rate_limit('read')(f)


def rate_limit_write(f):
    """
    Shorthand decorator for write operations
    
    Usage:
        @require_auth
        @rate_limit_write
        def create_expense():
            pass
    """
    return rate_limit('write')(f)
