"""
Flask Application Factory

Creates and configures the Flask application with all blueprints,
error handlers, and services.

Professional layered architecture with dependency injection.
"""

import logging
from typing import Optional

from flask import Flask, jsonify

from .api import admin_bp, init_service, places_bp
from .config.settings import Settings, get_settings
from .database import init_db


def configure_logging(app: Flask, settings: Settings) -> None:
    """
    Configure application logging.

    Args:
        app: Flask application instance
        settings: Application settings
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {settings.env} environment")


def register_blueprints(app: Flask) -> None:
    """
    Register all blueprints with the application.

    Args:
        app: Flask application instance
    """
    # Places API routes with v2 version
    app.register_blueprint(places_bp, url_prefix='/api/v2/places')

    # Admin routes
    app.register_blueprint(admin_bp, url_prefix='/api/v2/admin')

    logger.info("Blueprints registered successfully")


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            'success': False,
            'error': 'Resource not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        return jsonify({
            'success': False,
            'error': 'Bad request'
        }), 400

    logger.info("Error handlers registered")


def configure_cors(app: Flask) -> None:
    """
    Configure CORS if flask-cors is available.

    Args:
        app: Flask application instance
    """
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/api/*": {"origins": "*"}})
        logger.info("CORS configured")
    except ImportError:
        logger.warning("flask-cors not installed, CORS not configured")


def create_app(settings: Optional[Settings] = None) -> Flask:
    """
    Create and configure Flask application.

    Uses dependency injection with settings to configure all services,
    blueprints, and middleware.

    Args:
        settings: Application settings (uses default if None)

    Returns:
        Configured Flask application instance
    """
    # Use provided settings or get global instance
    if settings is None:
        settings = get_settings()

    # Create Flask app
    app = Flask(__name__)

    # Configure logging first
    configure_logging(app, settings)
    logger = logging.getLogger(__name__)

    # Configure CORS
    configure_cors(app)

    # Initialize database and services
    logger.info("Initializing database and services...")
    db = init_db(settings)
    init_service(db)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Add health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'places-engine',
            'version': settings.api_version
        }), 200

    logger.info(f"Flask application created successfully in {settings.env} environment")

    return app


logger = logging.getLogger(__name__)
