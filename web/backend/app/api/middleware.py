"""
API Request Logger Middleware
Logs incoming requests and outgoing responses via the standard logging module.
Controlled by the DISABLE_REQUEST_LOGS environment variable (default: true).
"""
import logging
import os
import time

from flask import g, request

logger = logging.getLogger('tripraft.requests')

# Enable/disable request logging via environment variable
DISABLE_REQUEST_LOGS = os.environ.get('DISABLE_REQUEST_LOGS', 'true').lower() == 'true'


def log_request():
    """Log incoming request details"""
    g.start_time = time.time()

    if DISABLE_REQUEST_LOGS:
        return

    # Skip health check spam
    if request.path in ('/health', '/api/health'):
        return

    query = request.query_string.decode('utf-8') if request.query_string else ''
    logger.info(
        "=> %s %s %s origin=%s",
        request.method,
        request.path,
        ('?' + query) if query else '',
        request.headers.get('Origin', '-'),
    )


def log_response(response):
    """Log outgoing response details"""
    if DISABLE_REQUEST_LOGS:
        return response

    if request.path in ('/health', '/api/health'):
        return response

    start = getattr(g, 'start_time', None)
    duration = (time.time() - start) * 1000 if start else 0

    logger.info(
        "<= %s %s %d %.1fms",
        request.method,
        request.path,
        response.status_code,
        duration,
    )

    return response


def init_request_logger(app):
    """Initialize request logging"""
    app.before_request(log_request)
    app.after_request(log_response)
    
    logger.info("Request logger initialized")
