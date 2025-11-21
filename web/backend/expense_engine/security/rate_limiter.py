"""
Rate Limiting Configuration
Protects API endpoints from abuse and DDoS attacks
"""

import logging
from flask import request, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def get_rate_limit_key():
    """
    Custom key function for rate limiting
    Uses user_id if authenticated, otherwise IP address
    """
    if hasattr(g, 'user_id') and g.user_id:
        return f"user:{g.user_id}"
    return f"ip:{get_remote_address()}"


# Global limiter instance (will be initialized with app)
limiter = None


def init_limiter(app, redis_client):
    """
    Initialize Flask-Limiter with Redis storage
    
    Args:
        app: Flask application instance
        redis_client: Redis client for distributed rate limiting
    """
    global limiter
    
    try:
        # Configure limiter with Redis storage
        limiter = Limiter(
            app=app,
            key_func=get_rate_limit_key,
            storage_uri=f"redis://{redis_client.connection_pool.connection_kwargs.get('host', 'localhost')}:"
                       f"{redis_client.connection_pool.connection_kwargs.get('port', 6379)}",
            default_limits=["200 per hour", "50 per minute"],
            storage_options={"socket_connect_timeout": 30},
            strategy="fixed-window"
        )
        
        logger.info("✅ Rate limiter initialized with Redis storage")
        
        # Add rate limit exceeded handler
        @app.errorhandler(429)
        def ratelimit_handler(e):
            return {
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': e.description
            }, 429
        
        return limiter
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize rate limiter: {e}")
        
        # Fallback: In-memory limiter
        limiter = Limiter(
            app=app,
            key_func=get_rate_limit_key,
            default_limits=["200 per hour", "50 per minute"],
            strategy="fixed-window"
        )
        
        logger.warning("⚠️ Using in-memory rate limiter (not suitable for production)")
        return limiter


# Rate limit decorators for common patterns
class RateLimits:
    """Predefined rate limits for different operation types"""
    
    # Read operations (can be more frequent)
    READ_HEAVY = "100 per minute"
    READ_NORMAL = "60 per minute"
    READ_LIGHT = "30 per minute"
    
    # Write operations (more restrictive)
    WRITE_HEAVY = "20 per minute"
    WRITE_NORMAL = "10 per minute"
    WRITE_LIGHT = "5 per minute"
    
    # Expensive operations (very restrictive)
    EXPENSIVE = "5 per minute"
    CRITICAL = "3 per minute"
    
    # Authentication
    AUTH = "10 per minute"
    
    # Admin operations
    ADMIN = "30 per minute"
