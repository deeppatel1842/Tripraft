"""
TripRaft Application Factory
Creates and configures the Flask application with all routes and middleware.
"""

import logging
import sys
from pathlib import Path

from app.core.config import get_config
from app.core.logging import setup_logging
from app.core.security import add_security_headers
from flask import Flask, jsonify, request
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
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    # Explicit OPTIONS handler
    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(_path):
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

    # Error handlers
    _register_error_handlers(app)

    # Root endpoints
    _register_root_endpoints(app)

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
        from app.api.v1.gp_destinations import group_planner_v2
        app.register_blueprint(group_planner_v2)
    except Exception as exc:
        logger.warning("GP destinations blueprint not available: %s", exc)

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


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def _register_middleware(app):
    """Register request/response middleware."""

    @app.before_request
    def before_request():
        if request.method != "OPTIONS":
            app.logger.debug("Request: %s %s", request.method, request.path)

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
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type"
        return response


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

def _register_error_handlers(app):
    """Register custom error handlers."""

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"success": False, "error": "Method not allowed"}), 405

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Internal server error: %s", error, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error("Unhandled exception: %s", error, exc_info=True)
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


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
                "auth": "/api/expense",
                "expenses": "/api/expense/groups",
                "group_planner": "/api/v2/group-planner",
                "locations": "/api/v1/locations",
                "place_search": "/api/v1/place-search",
                "trip_planner": "/api/trip-planner",
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
