"""
Rate Limiting Configuration
Implements rate limiting for API endpoints to prevent abuse and ensure fair usage.
"""

import os
from functools import wraps
from flask import request, jsonify
import time
from collections import defaultdict
import threading

# =============================================================================
# RATE LIMITING SETTINGS
# =============================================================================

class RateLimitConfig:
    """Configuration for rate limiting"""
    
    # Global rate limits (requests per minute)
    GLOBAL_RATE_LIMIT = int(os.getenv('GLOBAL_RATE_LIMIT', 60))
    
    # Per-endpoint rate limits (requests per minute)
    ENDPOINT_LIMITS = {
        '/api/places/search': int(os.getenv('PLACES_SEARCH_RATE_LIMIT', 20)),
        '/api/auth/verify': int(os.getenv('AUTH_VERIFY_RATE_LIMIT', 30)),
        '/api/profile': int(os.getenv('PROFILE_RATE_LIMIT', 30)),
    }
    
    # Rate limit window (seconds)
    WINDOW_SIZE = int(os.getenv('RATE_LIMIT_WINDOW', 60))
    
    # Google API rate limits
    GOOGLE_PLACES_API_LIMIT = int(os.getenv('PLACES_API_RATE_LIMIT', 10))
    GOOGLE_API_WINDOW = 1  # 1 second
    
    # Block duration for exceeding limits (seconds)
    BLOCK_DURATION = int(os.getenv('RATE_LIMIT_BLOCK_DURATION', 300))  # 5 minutes


# =============================================================================
# IN-MEMORY RATE LIMITER (for single-server deployments)
# =============================================================================

class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (IP, user_id, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            (is_allowed, info_dict)
        """
        current_time = time.time()
        
        with self.lock:
            # Check if blocked
            if key in self.blocked:
                unblock_time = self.blocked[key]
                if current_time < unblock_time:
                    remaining = int(unblock_time - current_time)
                    return False, {
                        'allowed': False,
                        'reason': 'rate_limit_exceeded',
                        'retry_after': remaining
                    }
                else:
                    del self.blocked[key]
            
            # Clean old requests
            cutoff_time = current_time - window
            self.requests[key] = [t for t in self.requests[key] if t > cutoff_time]
            
            # Check limit
            request_count = len(self.requests[key])
            
            if request_count >= limit:
                # Block user
                self.blocked[key] = current_time + RateLimitConfig.BLOCK_DURATION
                return False, {
                    'allowed': False,
                    'reason': 'rate_limit_exceeded',
                    'limit': limit,
                    'window': window,
                    'retry_after': RateLimitConfig.BLOCK_DURATION
                }
            
            # Allow request
            self.requests[key].append(current_time)
            
            return True, {
                'allowed': True,
                'remaining': limit - request_count - 1,
                'limit': limit,
                'window': window
            }
    
    def reset(self, key: str):
        """Reset rate limit for a key"""
        with self.lock:
            if key in self.requests:
                del self.requests[key]
            if key in self.blocked:
                del self.blocked[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


# =============================================================================
# DECORATORS
# =============================================================================

def rate_limit(limit: int = None, per: int = None, key_func=None):
    """
    Rate limiting decorator for Flask routes.
    
    Args:
        limit: Maximum requests (default: from config)
        per: Time window in seconds (default: from config)
        key_func: Function to generate rate limit key (default: IP address)
    
    Example:
        @app.route('/api/search')
        @rate_limit(limit=20, per=60)
        def search():
            return {'results': []}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limit key (default: IP address)
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or 'unknown'
            
            # Get endpoint-specific limit or use default
            endpoint = request.endpoint
            endpoint_limit = limit or RateLimitConfig.ENDPOINT_LIMITS.get(
                request.path, 
                RateLimitConfig.GLOBAL_RATE_LIMIT
            )
            window = per or RateLimitConfig.WINDOW_SIZE
            
            # Check rate limit
            allowed, info = rate_limiter.is_allowed(key, endpoint_limit, window)
            
            if not allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {info["retry_after"]} seconds.',
                    'retry_after': info['retry_after']
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(info['retry_after'])
                return response
            
            # Add rate limit headers
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                response.headers['X-RateLimit-Window'] = str(info['window'])
            
            return response
        
        return decorated_function
    return decorator


def google_api_rate_limit(f):
    """
    Special rate limiter for Google API calls.
    More restrictive to avoid hitting Google's limits.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = 'google_api'
        limit = RateLimitConfig.GOOGLE_PLACES_API_LIMIT
        window = RateLimitConfig.GOOGLE_API_WINDOW
        
        allowed, info = rate_limiter.is_allowed(key, limit, window)
        
        if not allowed:
            # Wait instead of rejecting (for internal API calls)
            time.sleep(info.get('retry_after', 1))
        
        return f(*args, **kwargs)
    
    return decorated_function
