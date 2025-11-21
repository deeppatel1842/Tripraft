"""
Rate Limiting Middleware
Provides per-user rate limits to prevent abuse and control costs
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, g
import logging

logger = logging.getLogger(__name__)

def get_user_identifier():
    """
    Get user identifier for rate limiting
    Uses Firebase UID if authenticated, otherwise IP address
    """
    try:
        # Check if user is authenticated (set by auth middleware)
        if hasattr(g, 'user_data') and g.user_data:
            return g.user_data.get('uid', get_remote_address())
        return get_remote_address()
    except Exception as e:
        logger.error(f"Error getting user identifier: {e}")
        return get_remote_address()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["200 per hour"],  # Global limit for all routes
    storage_uri="memory://",  # Use Redis in production: redis://localhost:6379
    strategy="fixed-window"
)

# Rate limit configurations for different operation types
rate_limit_config = {
    # Read operations - more lenient
    'read_light': "100 per minute",      # Simple GET requests
    'read_heavy': "30 per minute",       # Complex queries with joins
    
    # Write operations - more restrictive
    'create': "20 per minute",           # Create expense/group
    'update': "30 per minute",           # Update expense
    'delete': "10 per minute",           # Delete operations
    'settle': "10 per minute",           # Settlement creation
    
    # Special operations
    'invitation': "10 per minute",       # Send/accept invitations
    'auth': "5 per minute",              # Login/signup attempts
}

def get_rate_limit(operation_type):
    """
    Get rate limit string for a specific operation type
    
    Args:
        operation_type: Type of operation (read_light, create, etc.)
    
    Returns:
        Rate limit string (e.g., "20 per minute")
    """
    return rate_limit_config.get(operation_type, "50 per minute")

def rate_limit_exempt():
    """
    Check if current request should be exempt from rate limiting
    Useful for admin users or internal services
    """
    try:
        # Exempt admin users (add your admin check logic here)
        if hasattr(g, 'user_data') and g.user_data:
            # Example: if g.user_data.get('is_admin'):
            #     return True
            pass
        return False
    except Exception:
        return False
