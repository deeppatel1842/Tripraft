"""
API Middleware
Request ID injection, structured request/response logging.

Every completed request emits a single structured JSON log entry containing
endpoint, status, duration, user context, cache state, and rate limit info.
"""
import json
import logging
import os
import platform
import time
import uuid

from flask import g, request

logger = logging.getLogger('tripraft.requests')

_SKIP_PATHS = frozenset(('/health', '/api/health', '/api/health/', '/api/health/live', '/api/health/ready'))
_APP_VERSION = None
_HOSTNAME = platform.node()


def _get_app_version():
    global _APP_VERSION
    if _APP_VERSION is None:
        try:
            from app.core.config import Config
            _APP_VERSION = getattr(Config, 'APP_VERSION', '1.0.0')
        except Exception:
            _APP_VERSION = '1.0.0'
    return _APP_VERSION


def _derive_service_name(path):
    """Derive logical service name from the URL path."""
    if '/auth/' in path or '/users/' in path:
        return 'auth-service'
    if '/expenses/' in path:
        if '/groups' in path:
            return 'expense-group-service'
        if '/settlements' in path:
            return 'settlement-service'
        if '/invitations' in path:
            return 'expense-invite-service'
        return 'expense-service'
    if '/group-planner/' in path:
        return 'group-planner-service'
    if '/places/' in path or '/place-search/' in path:
        return 'place-search-service'
    if '/trip-planner/' in path:
        return 'trip-planner-service'
    if '/locations/' in path:
        return 'locations-service'
    if '/admin/' in path:
        return 'admin-service'
    return 'tripraft-api'


# Query param keys that must never appear in logs
_SENSITIVE_PARAMS = frozenset(('token', 'password', 'secret', 'key', 'apikey', 'api_key', 'access_token', 'refresh_token'))


def _parse_query_params():
    """Extract query parameters as a dict for structured logging."""
    args = request.args.to_dict(flat=True)
    # Omit cache-busting timestamps and sensitive values from logs
    args.pop('_t', None)
    for param in _SENSITIVE_PARAMS:
        args.pop(param, None)
    return args if args else None


def inject_request_id():
    """Assign a unique request ID and start the request timer."""
    g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    g.trace_id = request.headers.get('X-Trace-ID') or g.request_id[:12]
    g.span_id = uuid.uuid4().hex[:6]
    g.start_time = time.time()
    g.db_query_count = 0
    g.db_time_ms = 0.0


def add_request_id_header(response):
    """Echo the request ID back in the response for client-side correlation."""
    request_id = getattr(g, 'request_id', None)
    if request_id:
        response.headers['X-Request-ID'] = request_id
    return response


def log_response(response):
    """Emit a single structured JSON log entry for the completed request."""
    if request.path in _SKIP_PATHS:
        return response

    start = getattr(g, 'start_time', None)
    duration_ms = round((time.time() - start) * 1000, 1) if start else 0

    # Strip the /api prefix for cleaner endpoint display
    endpoint_path = request.path
    if endpoint_path.startswith('/api'):
        endpoint_path = endpoint_path[4:]

    entry = {
        'service': _derive_service_name(request.path),
        'endpoint': f'{request.method} {endpoint_path}',
        'status_code': response.status_code,
        'duration_ms': duration_ms,
        'request_id': getattr(g, 'request_id', None),
        'trace_id': getattr(g, 'trace_id', None),
        'span_id': getattr(g, 'span_id', None),
        'version': _get_app_version(),
        'host': _HOSTNAME,
        'ip': request.remote_addr,
    }

    # Query parameters (if any)
    query = _parse_query_params()
    if query:
        entry['query'] = query

    # User context (set by auth decorators)
    user_id = getattr(g, 'user_id', None) or getattr(g, 'current_user_id', None)
    if user_id:
        entry['user_id'] = user_id

    # Auth method detection
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        entry['auth_method'] = 'bearer_token'
    elif request.cookies.get('session'):
        entry['auth_method'] = 'session_cookie'
    else:
        entry['auth_method'] = 'none'

    # Cache info (set by @cache_response decorator)
    cache_status = response.headers.get('X-Cache')
    if cache_status:
        entry['cache'] = cache_status

    # Rate limit info (set by rate_limiter after_request)
    rl_remaining = response.headers.get('X-RateLimit-Remaining')
    if rl_remaining is not None:
        entry['rate_limit_remaining'] = int(rl_remaining)

    # DB metrics (populated by db session tracking)
    db_queries = getattr(g, 'db_query_count', 0)
    if db_queries:
        entry['db_queries'] = db_queries
        entry['db_time_ms'] = round(getattr(g, 'db_time_ms', 0.0), 1)

    # Log level based on status code
    if response.status_code >= 500:
        logger.error("RequestCompleted %s", json.dumps(entry, default=str))
    elif response.status_code >= 400:
        logger.warning("RequestCompleted %s", json.dumps(entry, default=str))
    else:
        logger.info("RequestCompleted %s", json.dumps(entry, default=str))

    return response


def init_request_logger(app):
    """Initialize request ID injection and structured logging middleware."""
    app.before_request(inject_request_id)
    app.after_request(add_request_id_header)
    app.after_request(log_response)
    logger.info("Structured request logging initialized")
