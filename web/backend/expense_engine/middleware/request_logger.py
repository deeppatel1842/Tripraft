"""
Request Logger Middleware
Initializes operation tracking for each request and logs summary

Phase 6: Enhanced Observability
"""

import uuid
import time
from functools import wraps
from flask import g, request, has_request_context

# Import operation logger
try:
    from ..utils.operation_logger import (
        init_request_tracker,
        finalize_request_tracker,
        get_request_tracker,
        Colors
    )
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False
    def init_request_tracker(request_id=None): pass
    def finalize_request_tracker(): return None
    def get_request_tracker(): return None
    class Colors:
        RESET = GREEN = YELLOW = RED = CYAN = MAGENTA = BOLD = ''


def init_request_logging(app):
    """
    Initialize request logging middleware for Flask app
    
    Usage:
        from expense_engine.middleware.request_logger import init_request_logging
        init_request_logging(app)
    """
    
    @app.before_request
    def before_request():
        """Initialize request tracking"""
        # Generate request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
        g.request_id = request_id
        g.request_start_time = time.time()
        
        # Initialize operation tracker
        if LOGGING_ENABLED:
            init_request_tracker(request_id)
        
        # Print request start
        method = request.method
        path = request.path
        
        # Color code by method
        if method == 'GET':
            method_color = Colors.GREEN
        elif method in ('POST', 'PUT', 'PATCH'):
            method_color = Colors.YELLOW
        elif method == 'DELETE':
            method_color = Colors.RED
        else:
            method_color = Colors.CYAN
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{method_color}[{method}]{Colors.RESET} {path} {Colors.CYAN}[{request_id}]{Colors.RESET}")
        print(f"{'='*60}")
    
    @app.after_request
    def after_request(response):
        """Log request summary"""
        # Calculate duration
        duration_ms = 0
        if hasattr(g, 'request_start_time'):
            duration_ms = (time.time() - g.request_start_time) * 1000
        
        # Finalize operation tracker
        if LOGGING_ENABLED:
            finalize_request_tracker()
        
        # Color code status
        status = response.status_code
        if status < 300:
            status_color = Colors.GREEN
        elif status < 400:
            status_color = Colors.YELLOW
        elif status < 500:
            status_color = Colors.RED
        else:
            status_color = Colors.BOLD_RED if hasattr(Colors, 'BOLD_RED') else Colors.RED
        
        request_id = getattr(g, 'request_id', 'unknown')
        print(f"\n{status_color}[{status}]{Colors.RESET} Completed in {duration_ms:.1f}ms [{request_id}]")
        print(f"{'='*60}\n")
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Response-Time'] = f"{duration_ms:.1f}ms"
        
        return response
    
    return app


def log_operation_summary():
    """
    Decorator to log operation summary after function execution
    Use for specific routes that need detailed logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Get operation summary
            if LOGGING_ENABLED:
                tracker = get_request_tracker()
                if tracker:
                    summary = tracker.get_summary()
                    
                    # Log to console
                    print(f"\n{Colors.BOLD}Operation Summary:{Colors.RESET}")
                    print(f"  Firestore: R={summary['firestore']['reads']} "
                          f"W={summary['firestore']['writes']} "
                          f"D={summary['firestore']['deletes']}")
                    print(f"  Cache: Hits={summary['cache']['hits']} "
                          f"Misses={summary['cache']['misses']} "
                          f"Rate={summary['cache']['hit_rate']*100:.1f}%")
            
            return result
        return wrapper
    return decorator
