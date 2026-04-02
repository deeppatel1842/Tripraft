"""
TripRaft Application Factory
Creates and configures the Flask application with all routes and middleware.
"""

import logging

from app.core.config import get_config
from app.core.logging import setup_logging
from app.core.security import add_security_headers, validate_csrf
from flask import Flask, g, jsonify, redirect, request
from flask_compress import Compress
from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_app():
    """
    Application factory pattern.

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config()
    config.validate_production()
    app.config.from_object(config)

    # Setup structured logging
    setup_logging(app)

    # Initialize request logger
    _init_request_logger(app)

    # CORS
    cors_origins = config.CORS_ORIGINS if hasattr(config, "CORS_ORIGINS") else ["http://localhost:5173"]
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin",
                      "X-Requested-With", "X-CSRF-Token", "Idempotency-Key",
                      "If-None-Match"],
        expose_headers=["X-Total-Count", "X-Page", "X-Per-Page", "ETag", "Content-Type",
                        "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
                        "X-Request-ID", "X-Cache", "Deprecation", "Sunset", "Link"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    # Explicit OPTIONS handler
    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(path):
        response = app.make_default_options_response()
        origin = request.headers.get("Origin", "")
        allowed_origins = app.config.get("CORS_ORIGINS", [])
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    # Gzip compression
    Compress(app)
    app.config["COMPRESS_MIMETYPES"] = [
        "text/html", "text/css", "text/xml",
        "application/json", "application/javascript", "text/javascript",
    ]
    app.config["COMPRESS_LEVEL"] = 6
    app.config["COMPRESS_MIN_SIZE"] = 500

    # Initialize database
    _init_databases(app)

    # Redis cache
    _init_redis(app)

    # Rate limiter
    _init_rate_limiter(app)

    # Register all blueprints
    _register_blueprints(app)

    # Security middleware
    _register_middleware(app)

    # Idempotency support
    try:
        from app.core.idempotency import init_idempotency
        init_idempotency(app)
    except Exception as exc:
        logger.warning("Idempotency middleware not available: %s", exc)

    # Error handlers
    _register_error_handlers(app)

    # Root endpoints
    _register_root_endpoints(app)

    # Real-time WebSockets
    _init_socketio(app)

    # Log registered routes
    _log_routes(app)

    return app


# ---------------------------------------------------------------------------
# Initialisation helpers
# ---------------------------------------------------------------------------

def _init_databases(app):
    """Initialize SQLAlchemy (tripraft.db) and travel database."""
    try:
        from app.infrastructure.db.connection import init_db
        init_db(app)
        logger.info("TripRaft database initialized")
    except Exception as exc:
        logger.warning("Database initialization issue: %s", exc)

    # Initialize travel_data_complete.db (read-only geographic data)
    try:
        config = get_config()
        if hasattr(config, "DATABASE_PATH") and config.DATABASE_PATH and config.DATABASE_PATH.exists():
            from app.api.utils.database import init_database as init_travel_db
            init_travel_db(config.DATABASE_PATH)

            # Also initialise the location_repository singleton (used by locations.py)
            from app.domain.places.location_repository import \
                init_database as init_loc_db
            init_loc_db(config.DATABASE_PATH)

            logger.info("Travel database initialized: %s", config.DATABASE_PATH.name)
    except Exception as exc:
        logger.warning("Travel database initialization skipped: %s", exc)


def _init_redis(app):
    """Initialize Redis cache with graceful fallback."""
    try:
        from app.infrastructure.cache.redis import redis_client
        redis_client.init_app(app)
        app.extensions["redis"] = redis_client if redis_client.available else None
    except Exception as exc:
        logger.warning("Redis unavailable, running without cache: %s", exc)
        app.extensions["redis"] = None


def _init_rate_limiter(app):
    """Attach rate limiter to the Flask app."""
    try:
        from app.core.rate_limiter import init_rate_limiter
        init_rate_limiter(app)
    except Exception as exc:
        logger.warning("Rate limiter not available: %s", exc)


def _init_request_logger(app):
    """Initialize colored request/response logger."""
    try:
        from app.api.middleware import init_request_logger
        init_request_logger(app)
    except Exception as exc:
        logger.debug("Request logger not available: %s", exc)


def _init_socketio(app):
    """Initialize Flask-SocketIO and register event handlers."""
    try:
        from app.infrastructure.realtime.socketio_ext import init_socketio
        init_socketio(app)

        # Import event handlers so they get registered with the socketio instance
        import app.infrastructure.realtime.events  # noqa: F401

        logger.info("WebSocket event handlers registered")
    except Exception as exc:
        logger.warning("SocketIO not available, running without WebSockets: %s", exc)


# ---------------------------------------------------------------------------
# Blueprint registration
# ---------------------------------------------------------------------------

def _register_blueprints(app):
    """Register all API route blueprints."""
    api_prefix = app.config.get("API_PREFIX", "/api/v1")

    # --- Health ---
    try:
        from app.api.health import health_bp
        app.register_blueprint(health_bp, url_prefix="/api/health")
    except Exception as exc:
        logger.warning("Health blueprint not available: %s", exc)

    # --- Users (new clean auth) ---
    try:
        from app.api.v1.users import users_bp
        app.register_blueprint(users_bp, url_prefix=f"{api_prefix}/users")
    except Exception as exc:
        logger.warning("Users blueprint not available: %s", exc)

    # --- Expense Engine auth (legacy endpoints /api/expense/*) ---
    try:
        from app.api.v1.auth import auth_bp
        app.register_blueprint(auth_bp)
    except Exception as exc:
        logger.warning("Expense auth blueprint not available: %s", exc)

    # --- Expense groups ---
    try:
        from app.api.v1.expense_groups import groups_sql_bp
        app.register_blueprint(groups_sql_bp)
    except Exception as exc:
        logger.warning("Expense groups blueprint not available: %s", exc)

    # --- Expenses ---
    try:
        from app.api.v1.expenses import expenses_sql_bp
        app.register_blueprint(expenses_sql_bp)
    except Exception as exc:
        logger.warning("Expenses blueprint not available: %s", exc)

    # --- Settlements ---
    try:
        from app.api.v1.settlements import settlements_sql_bp
        app.register_blueprint(settlements_sql_bp)
    except Exception as exc:
        logger.warning("Settlements blueprint not available: %s", exc)

    # --- Expense invitations ---
    try:
        from app.api.v1.expense_invitations import invitations_sql_bp
        app.register_blueprint(invitations_sql_bp)
    except Exception as exc:
        logger.warning("Expense invitations blueprint not available: %s", exc)

    # --- Group Planner ---
    try:
        from app.api.v1.gp_groups import groups_bp
        app.register_blueprint(groups_bp)
    except Exception as exc:
        logger.warning("GP groups blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_places import places_bp
        app.register_blueprint(places_bp)
    except Exception as exc:
        logger.warning("GP places blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_polls import polls_bp
        app.register_blueprint(polls_bp)
    except Exception as exc:
        logger.warning("GP polls blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_invitations import invitations_bp
        app.register_blueprint(invitations_bp)
    except Exception as exc:
        logger.warning("GP invitations blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_checklist import checklist_bp
        app.register_blueprint(checklist_bp)
    except Exception as exc:
        logger.warning("GP checklist blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_events import events_bp
        app.register_blueprint(events_bp)
    except Exception as exc:
        logger.warning("GP events blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_notifications import notifications_bp
        app.register_blueprint(notifications_bp)
    except Exception as exc:
        logger.warning("GP notifications blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_destinations import group_planner_v2
        app.register_blueprint(group_planner_v2)
    except Exception as exc:
        logger.warning("GP destinations blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_export import export_bp
        app.register_blueprint(export_bp)
    except Exception as exc:
        logger.warning("GP export blueprint not available: %s", exc)

    # --- Group Planner Vault ---
    try:
        from app.api.v1.gp_vault import vault_bp
        app.register_blueprint(vault_bp)
    except Exception as exc:
        logger.warning("GP vault blueprint not available: %s", exc)

    # --- Group Planner Chat ---
    try:
        from app.api.v1.gp_chat import chat_bp
        app.register_blueprint(chat_bp)
    except Exception as exc:
        logger.warning("GP chat blueprint not available: %s", exc)

    # --- AI Consent ---
    try:
        from app.api.v1.ai_consent import ai_consent_bp
        app.register_blueprint(ai_consent_bp)
    except Exception as exc:
        logger.warning("AI consent blueprint not available: %s", exc)

    # --- AI Crew Confirm ---
    try:
        from app.api.v1.ai_confirm import ai_confirm_bp
        app.register_blueprint(ai_confirm_bp)
    except Exception as exc:
        logger.warning("AI confirm blueprint not available: %s", exc)

    # --- Locations ---
    try:
        from app.api.v1.locations import locations_bp
        app.register_blueprint(locations_bp, url_prefix=f"{api_prefix}/locations")
    except Exception as exc:
        logger.warning("Locations blueprint not available: %s", exc)

    # --- Place Search ---
    try:
        from app.api.v1.places import place_search_bp
        app.register_blueprint(place_search_bp)
    except Exception as exc:
        logger.warning("Place search blueprint not available: %s", exc)

    # --- Admin Places ---
    try:
        from app.api.v1.admin_places import admin_places_bp
        app.register_blueprint(admin_places_bp)
    except Exception as exc:
        logger.warning("Admin places blueprint not available: %s", exc)

    # --- Trip Planner ---
    try:
        from app.api.v1.trips import trip_planner_bp
        app.register_blueprint(trip_planner_bp)
    except Exception as exc:
        logger.warning("Trip planner blueprint not available: %s", exc)

    # --- Route viewer ---
    try:
        from app.api.route_viewer import route_viewer_bp
        app.register_blueprint(route_viewer_bp)
    except Exception as exc:
        logger.warning("Route viewer not available: %s", exc)

    # --- Deprecated aliases (backward compatibility for 6 months) ---
    _register_deprecated_aliases(app)


# ---------------------------------------------------------------------------
# Deprecated route aliases (RFC 8594)
# ---------------------------------------------------------------------------

_DEPRECATED_PREFIX_MAP = {
    # Old prefix -> (new prefix, successor link)
    '/api/expense/signup': '/api/v1/auth/signup',
    '/api/expense/login': '/api/v1/auth/login',
    '/api/expense/refresh': '/api/v1/auth/refresh',
    '/api/expense/logout': '/api/v1/auth/logout',
    '/api/expense/verify-email': '/api/v1/auth/verify-email',
    '/api/expense/resend-verification': '/api/v1/auth/resend-verification',
    '/api/expense/groups': '/api/v1/expenses/groups',
    '/api/expense/expenses': '/api/v1/expenses',
    '/api/expense/settlements': '/api/v1/expenses/settlements',
    '/api/expense/invitations': '/api/v1/expenses/invitations',
    '/api/v2/group-planner': '/api/v1/group-planner',
    '/api/v1/place-search': '/api/v1/places',
    '/api/trip-planner': '/api/v1/trip-planner',
}


def _register_deprecated_aliases(app):
    """Register deprecated route aliases that proxy to new /api/v1/ endpoints."""
    from app.core.config import Config

    def _make_proxy(old_prefix, new_prefix):
        """Create a redirect view that 308-redirects to the new endpoint with deprecation headers."""
        def proxy_view(**kwargs):
            path_suffix = request.path[len(old_prefix):]
            new_path = new_prefix + path_suffix
            if request.query_string:
                new_path += '?' + request.query_string.decode()
            # 308 Permanent Redirect preserves the HTTP method (unlike 301)
            response = redirect(new_path, code=308)
            response.headers['Deprecation'] = 'true'
            response.headers['Sunset'] = Config.API_SUNSET_DATE
            successor = new_prefix + path_suffix
            response.headers['Link'] = f'<{successor}>; rel="successor-version"'
            return response
        return proxy_view

    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    for old_prefix, new_prefix in _DEPRECATED_PREFIX_MAP.items():
        # Register catch-all for the old prefix
        rule_base = old_prefix.rstrip('/')
        endpoint_name = f"deprecated_{old_prefix.replace('/', '_').strip('_')}"

        # Exact match (e.g., /api/expense/groups)
        app.add_url_rule(
            rule_base,
            endpoint=endpoint_name,
            view_func=_make_proxy(old_prefix, new_prefix),
            methods=methods,
        )
        # Sub-path match (e.g., /api/expense/groups/123/full)
        app.add_url_rule(
            f'{rule_base}/<path:_subpath>',
            endpoint=f'{endpoint_name}_sub',
            view_func=_make_proxy(old_prefix, new_prefix),
            methods=methods,
        )

    logger.info("Registered %d deprecated route aliases", len(_DEPRECATED_PREFIX_MAP))


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def _register_middleware(app):
    """Register request/response middleware."""

    @app.before_request
    def before_request():
        validate_csrf()

    @app.after_request
    def after_request(response):
        add_security_headers(response)

        # CORS fallback
        origin = request.headers.get("Origin")
        allowed_origins = app.config.get("CORS_ORIGINS", [])
        if origin and origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-CSRF-Token"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type, X-Total-Count, X-Page, X-Per-Page, ETag, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, X-Request-ID, X-Cache, Deprecation, Sunset, Link"
        return response


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

def _register_error_handlers(app):
    """Register custom error handlers."""

    from app.core.exceptions import AppError

    def _error_envelope(code, message, status_code):
        """Build standard error response envelope with meta."""
        from datetime import datetime, timezone
        body = {
            "success": False,
            "data": None,
            "error": {"code": code, "message": message},
            "meta": {
                "request_id": getattr(g, 'request_id', None),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "v1",
            },
        }
        return jsonify(body), status_code

    @app.errorhandler(AppError)
    def handle_app_error(error):
        resp = error.to_dict()
        from datetime import datetime, timezone
        resp["meta"] = {
            "request_id": getattr(g, 'request_id', None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "v1",
        }
        return jsonify(resp), error.status_code

    @app.errorhandler(400)
    def bad_request(error):
        msg = getattr(error, 'description', 'Bad request')
        return _error_envelope("BAD_REQUEST", msg, 400)

    @app.errorhandler(401)
    def unauthorized(_error):
        return _error_envelope("UNAUTHORIZED", "Authentication required", 401)

    @app.errorhandler(403)
    def forbidden(error):
        msg = getattr(error, 'description', 'Forbidden')
        return _error_envelope("FORBIDDEN", msg, 403)

    @app.errorhandler(404)
    def not_found(_error):
        return _error_envelope("NOT_FOUND", "Endpoint not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return _error_envelope("METHOD_NOT_ALLOWED", "Method not allowed", 405)

    @app.errorhandler(429)
    def rate_limited(_error):
        return _error_envelope("RATE_LIMITED", "Rate limit exceeded", 429)

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Internal server error: %s", error, exc_info=True)
        return _error_envelope("INTERNAL_ERROR", "Internal server error", 500)

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error("Unhandled exception: %s", error, exc_info=True)
        return _error_envelope("INTERNAL_ERROR", "An unexpected error occurred", 500)


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------

def _register_root_endpoints(app):
    """Register root and health check endpoints."""

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "TripRaft Backend",
            "version": "2.0.0",
        }), 200

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "message": "TripRaft Backend API",
            "version": "2.0.0",
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "routes": "/api/routes",
                "auth": "/api/v1/auth",
                "expenses": "/api/v1/expenses",
                "group_planner": "/api/v1/group-planner",
                "locations": "/api/v1/locations",
                "places": "/api/v1/places",
                "trip_planner": "/api/v1/trip-planner",
            },
        }), 200


# ---------------------------------------------------------------------------
# Debug route listing
# ---------------------------------------------------------------------------

def _log_routes(app):
    """Log all registered routes on startup."""
    route_count = 0
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            route_count += 1
    logger.info("Registered %d API routes", route_count)
