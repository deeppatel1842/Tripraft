"""
Phase 4: Flask Application Initialization

Main Flask app setup with API endpoints and middleware.
"""

import logging
import os
from flask import Flask
from flask_cors import CORS

from api.endpoints import places_bp, initialize_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config: dict = None, data_store: dict = None) -> Flask:
    """
    Create and configure Flask application
    
    Args:
        config: Optional Flask configuration dictionary
        data_store: Optional pre-loaded data store for testing
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Apply configuration
    if config:
        app.config.update(config)
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(places_bp)
    
    # Initialize search service
    initialize_service(data_store=data_store)
    
    # Register health check
    @app.route('/health', methods=['GET'])
    def health():
        from flask import jsonify
        return jsonify({
            'status': 'healthy',
            'service': 'places-api',
            'version': '1.0.0',
        }), 200
    
    logger.info("Flask app created successfully")
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
