"""
Main Flask Application
Initializes and configures the Flask app with all routes and middleware.
Integrates:
- Places API (countries, states, cities, places)
- Expense Management System (with Firebase authentication)
"""
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_compress import Compress
import logging
import sys
import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from .config import get_config
from .utils import init_database, error_response
from .routes import countries_bp, states_bp, cities_bp, places_bp
from .middleware import init_request_logger


def create_app(config_name=None):
    """
    Application factory pattern
    
    Args:
        config_name: Configuration name (development/production/testing)
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()  # Returns config class, not instance
    app.config.from_object(config)
    
    # Initialize Firebase Admin SDK
    initialize_firebase(app)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize request logger (colored logs for requests/responses)
    init_request_logger(app)
    
    # Initialize CORS with proper configuration
    CORS(app, 
         resources={r"/api/*": {"origins": config.CORS_ORIGINS}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    
    # Enable response compression (gzip)
    # Compresses responses > 500 bytes by 60-80%
    Compress(app)
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Balanced compression (1=fast, 9=best)
    app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses > 500 bytes
    # app.logger.info("✅ Response compression enabled (gzip, level 6)")
    
    # Initialize database (optional - only if places_database exists)
    try:
        if hasattr(config, 'DATABASE_PATH') and config.DATABASE_PATH and config.DATABASE_PATH.exists():
            init_database(config.DATABASE_PATH)
            # app.logger.info(f"✅ Places database initialized: {config.DATABASE_PATH}")
        else:
            app.logger.warning("⚠️  Places database not found - Places API will not be available")
    except Exception as e:
        app.logger.warning(f"⚠️  Database initialization skipped: {e}")
    
    # Register blueprints
    register_blueprints(app, config.API_PREFIX)
    
    # Register middleware
    register_middleware(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'TripRaft Backend',
            'version': '1.0.0',
            'features': ['expense_management', 'group_planner']
        }), 200
    
    # 🗺️  API Routes Viewer Endpoint
    @app.route('/api/routes', methods=['GET'])
    def list_routes():
        """📋 List all API routes with methods and descriptions"""
        routes = []
        for rule in app.url_map.iter_rules():
            # Skip static files and internal Flask routes
            if rule.endpoint == 'static' or rule.endpoint.startswith('_'):
                continue
            
            # Get the view function
            try:
                view_func = app.view_functions.get(rule.endpoint)
                docstring = view_func.__doc__ if view_func and view_func.__doc__ else 'No description'
                docstring = docstring.strip()
            except:
                docstring = 'No description'
            
            # Parse blueprint info
            blueprint = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
            
            routes.append({
                'endpoint': rule.endpoint,
                'path': str(rule),
                'methods': sorted([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]),
                'description': docstring,
                'blueprint': blueprint
            })
        
        # Sort by path
        routes.sort(key=lambda x: x['path'])
        
        # Group by blueprint
        grouped_routes = {}
        for route in routes:
            bp = route['blueprint']
            if bp not in grouped_routes:
                grouped_routes[bp] = []
            grouped_routes[bp].append(route)
        
        # Return as HTML or JSON based on Accept header
        if 'text/html' in request.headers.get('Accept', ''):
            # HTML response with styled UI
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>TripRaft API Routes</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
        .route {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #95a5a6; }}
        .route:hover {{ background: #e9ecef; }}
        .path {{ font-family: 'Courier New', monospace; font-weight: bold; color: #2c3e50; font-size: 14px; }}
        .methods {{ display: inline-block; margin-left: 10px; }}
        .method {{ display: inline-block; padding: 3px 8px; margin: 0 3px; border-radius: 3px; font-size: 11px; font-weight: bold; }}
        .GET {{ background: #28a745; color: white; }}
        .POST {{ background: #007bff; color: white; }}
        .PUT {{ background: #ffc107; color: #000; }}
        .PATCH {{ background: #17a2b8; color: white; }}
        .DELETE {{ background: #dc3545; color: white; }}
        .description {{ color: #6c757d; margin-top: 8px; font-size: 13px; line-height: 1.5; }}
        .endpoint {{ color: #7f8c8d; font-size: 11px; font-family: monospace; }}
        .stats {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .stat {{ display: inline-block; margin-right: 20px; }}
        .stat-label {{ color: #666; font-size: 12px; }}
        .stat-value {{ font-weight: bold; font-size: 18px; color: #1976d2; }}
        .blueprint-expense {{ border-left-color: #e74c3c; }}
        .blueprint-group_planner {{ border-left-color: #9b59b6; }}
        .blueprint-countries {{ border-left-color: #3498db; }}
        .blueprint-states {{ border-left-color: #1abc9c; }}
        .blueprint-cities {{ border-left-color: #f39c12; }}
        .blueprint-places {{ border-left-color: #16a085; }}
        .blueprint-health {{ border-left-color: #27ae60; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️  TripRaft API Routes</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Total Endpoints</div>
                <div class="stat-value">{len(routes)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Blueprints</div>
                <div class="stat-value">{len(grouped_routes)}</div>
            </div>
        </div>
"""
            for blueprint, bp_routes in sorted(grouped_routes.items()):
                blueprint_emoji = {
                    'expense': '💰',
                    'group_planner': '📅',
                    'countries': '🌍',
                    'states': '🗺️',
                    'cities': '🏙️',
                    'places': '📍',
                    'health': '❤️',
                    'main': '🏠'
                }.get(blueprint, '📦')
                
                html += f'<h2>{blueprint_emoji} {blueprint.replace("_", " ").title()} ({len(bp_routes)} routes)</h2>'
                
                for route in bp_routes:
                    methods_html = ''.join([f'<span class="method {m}">{m}</span>' for m in route['methods']])
                    html += f"""
        <div class="route blueprint-{blueprint}">
            <div class="path">{route['path']}</div>
            <div class="methods">{methods_html}</div>
            <div class="description">{route['description']}</div>
            <div class="endpoint">Endpoint: {route['endpoint']}</div>
        </div>
"""
            
            html += """
    </div>
</body>
</html>
"""
            return html
        else:
            # JSON response
            return jsonify({
                'total_routes': len(routes),
                'blueprints': list(grouped_routes.keys()),
                'routes': grouped_routes
            }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """API root endpoint"""
        return jsonify({
            'message': 'TripRaft Backend API',
            'version': '1.0.0',
            'status': 'operational',
            'endpoints': {
                'health': '/health',
                'routes': '/api/routes',
                'expense_api': {
                    'users': '/api/expense/user',
                    'groups': '/api/expense/groups',
                    'expenses': '/api/expense/expenses',
                    'invitations': '/api/expense/invitations',
                    'settlements': '/api/expense/settlements',
                    'balances': '/api/expense/balances'
                },
                'group_planner': {
                    'groups': '/api/groups',
                    'places': '/api/groups/<group_id>/places',
                    'polls': '/api/groups/<group_id>/polls',
                    'invitations': '/api/groups/<group_id>/invite',
                    'itinerary': '/api/groups/<group_id>/generate-itinerary'
                }
            },
            'documentation': 'https://github.com/tripraft/api-docs'
        }), 200
    
    # app.logger.info("Flask application created successfully")
    return app


def setup_logging(app):
    """Configure application logging"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    log_format = app.config.get('LOG_FORMAT')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)
    
    # Set werkzeug logger to warning only
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def initialize_firebase(app):
    """Initialize Firebase Admin SDK with optional emulator support"""
    try:
        if not firebase_admin._apps:
            service_account_info = {
                "type": os.getenv("FIREBASE_TYPE"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
            }
            
            cred = credentials.Certificate(service_account_info)
            
            # Initialize with clock skew tolerance (industry standard: 5 minutes)
            # Prevents "Token used too early" errors in distributed systems
            firebase_admin.initialize_app(cred, {
                'clock_skew_seconds': 300  # 5 minutes (was 60)
            })
            
            # Check if Firebase Emulator should be used
            use_emulator = os.getenv("USE_FIREBASE_EMULATOR", "false").lower() == "true"
            
            if use_emulator:
                # Set emulator environment variables for Firestore
                os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
                os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = "127.0.0.1:9099"
                # app.logger.info("🔧 Firebase Emulator Mode ENABLED")
                # app.logger.info("   Firestore: http://127.0.0.1:8080")
                # app.logger.info("   Auth: http://127.0.0.1:9099")
                # app.logger.info("   UI: http://127.0.0.1:4000")
                # app.logger.info("   ⚡ Expected latency: <10ms (vs 200ms cloud)")
            else:
                # app.logger.info("Firebase Admin SDK initialized successfully")
                # app.logger.info("   Using production Firestore (~200ms latency)")
        else:
            # app.logger.info("Firebase Admin SDK already initialized")
    except Exception as e:
        app.logger.error(f"Firebase Admin initialization error: {e}")
        app.logger.warning("Continuing without Firebase - some features may not work")


def register_middleware(app):
    """Register request/response middleware"""
    
    @app.before_request
    def before_request():
        """Initialize request context"""
        # Initialize Firestore operation counter if expense engine available
        try:
            from expense_engine.firestore_counter import init_operation_counter
            init_operation_counter()
        except ImportError:
            pass
        
        # Log request (skip OPTIONS for CORS)
        if request.method != 'OPTIONS':
            # app.logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Add CORS headers and log operations"""
        # Ensure CORS headers on all responses
        origin = request.headers.get('Origin')
        allowed_origins = app.config.get('CORS_ORIGINS', [])
        
        if origin and origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Type'
        
        # Log Firestore operations if available
        try:
            from expense_engine.firestore_counter import log_firestore_operations
            log_firestore_operations()
        except ImportError:
            pass
        
        return response


def register_blueprints(app, api_prefix):
    """Register all API blueprints"""
    # Health & Performance Monitoring (global)
    try:
        from .health import health_bp
        app.register_blueprint(health_bp, url_prefix='/api/health')
        # app.logger.info("Health & Performance Monitoring registered at /api/health")
    except ImportError as e:
        app.logger.warning(f"Health monitoring not available: {e}")
    except Exception as e:
        app.logger.error(f"Failed to register health monitoring: {e}")
    
    # Places API blueprints
    app.register_blueprint(countries_bp, url_prefix=f'{api_prefix}/countries')
    app.register_blueprint(states_bp, url_prefix=f'{api_prefix}/states')
    app.register_blueprint(cities_bp, url_prefix=f'{api_prefix}/cities')
    app.register_blueprint(places_bp, url_prefix=f'{api_prefix}/places')
    
    # app.logger.info(f"Places API blueprints registered with prefix: {api_prefix}")
    
    # Register Expense Management System blueprint
    try:
        # Import from parent directory
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from expense_engine.routes import expense_bp
        app.register_blueprint(expense_bp)
        # app.logger.info("Expense Management System blueprint registered at /api/expense")
    except ImportError as e:
        app.logger.warning(f"Expense Management System not available: {e}")
    except Exception as e:
        app.logger.error(f"Failed to register Expense Management System: {e}")
    
    # Register Group Planner blueprint
    try:
        from Group_planner.routes import group_planner_bp
        app.register_blueprint(group_planner_bp)
        # app.logger.info("✅ Group Planner blueprint registered at /api/group-planner (Phase 1)")
    except ImportError as e:
        app.logger.warning(f"Group Planner not available: {e}")
    except Exception as e:
        app.logger.error(f"Failed to register Group Planner: {e}")


def register_error_handlers(app):
    """Register custom error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return error_response(
            message="Endpoint not found",
            status_code=404
        )
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return error_response(
            message="Method not allowed",
            status_code=405
        )
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        app.logger.error(f"Internal server error: {error}", exc_info=True)
        return error_response(
            message="Internal server error",
            status_code=500
        )
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions"""
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )
