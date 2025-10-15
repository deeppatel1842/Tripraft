import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
_env_path = os.path.join(basedir, '..', '..', '.env')
load_dotenv(_env_path)


class Config:
    """
    Centralized configuration for the application.
    All values are loaded from environment variables with sensible defaults.
    """
    
    # =============================================================================
    # BRAND CONFIGURATION
    # =============================================================================
    APP_NAME = os.environ.get('APP_NAME', 'TravelApp')
    APP_DESCRIPTION = os.environ.get('APP_DESCRIPTION', 'AI-powered travel planning platform')
    APP_TAGLINE = os.environ.get('APP_TAGLINE', 'Discover. Plan. Explore.')
    
    # =============================================================================
    # FLASK CONFIGURATION
    # =============================================================================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # =============================================================================
    # API CONFIGURATION
    # =============================================================================
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    API_PREFIX = '/api'
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_MAX_CONNECTIONS = int(os.environ.get('REDIS_MAX_CONNECTIONS', 50))
    REDIS_SOCKET_TIMEOUT = int(os.environ.get('REDIS_SOCKET_TIMEOUT', 5))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.environ.get('REDIS_SOCKET_CONNECT_TIMEOUT', 5))
    REDIS_HEALTH_CHECK_INTERVAL = int(os.environ.get('REDIS_HEALTH_CHECK_INTERVAL', 30))
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./database/app.db')
    
    # =============================================================================
    # API RATE LIMITING
    # =============================================================================
    PLACES_API_RATE_LIMIT = int(os.environ.get('PLACES_API_RATE_LIMIT', 10))
    MAX_CONCURRENT_REQUESTS = int(os.environ.get('MAX_CONCURRENT_REQUESTS', 5))
    API_REQUEST_TIMEOUT = int(os.environ.get('API_REQUEST_TIMEOUT', 30))
    
    # =============================================================================
    # CACHING STRATEGY
    # =============================================================================
    CACHE_TTL = int(os.environ.get('CACHE_TTL', 604800))  # 7 days default
    ENABLE_AGGRESSIVE_CACHING = os.environ.get('ENABLE_AGGRESSIVE_CACHING', 'True').lower() == 'true'
    CACHE_WARMING_ENABLED = os.environ.get('CACHE_WARMING_ENABLED', 'False').lower() == 'true'
    
    # =============================================================================
    # PERFORMANCE & SCALABILITY
    # =============================================================================
    WORKERS = int(os.environ.get('WORKERS', 4))
    WORKER_TIMEOUT = int(os.environ.get('WORKER_TIMEOUT', 120))
    MAX_REQUESTS_PER_WORKER = int(os.environ.get('MAX_REQUESTS_PER_WORKER', 1000))
    WORKER_THREADS = int(os.environ.get('WORKER_THREADS', 2))
    
    # =============================================================================
    # CORS CONFIGURATION
    # =============================================================================
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
    
    # =============================================================================
    # LOGGING
    # =============================================================================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # =============================================================================
    # SECURITY
    # =============================================================================
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    TOKEN_EXPIRY = int(os.environ.get('TOKEN_EXPIRY', 3600))  # 1 hour
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    ENABLE_ANALYTICS = os.environ.get('ENABLE_ANALYTICS', 'False').lower() == 'true'
    ENABLE_DEBUG_MODE = os.environ.get('ENABLE_DEBUG_MODE', 'False').lower() == 'true'
    ENABLE_API_MONITORING = os.environ.get('ENABLE_API_MONITORING', 'True').lower() == 'true'
    
    @classmethod
    def get_brand_config(cls):
        """Returns brand configuration as a dictionary."""
        return {
            'app_name': cls.APP_NAME,
            'app_description': cls.APP_DESCRIPTION,
            'app_tagline': cls.APP_TAGLINE
        }
    
    @classmethod
    def get_public_config(cls):
        """Returns public configuration safe for frontend."""
        return {
            'app_name': cls.APP_NAME,
            'app_description': cls.APP_DESCRIPTION,
            'app_tagline': cls.APP_TAGLINE,
            'api_prefix': cls.API_PREFIX,
            'cors_origins': cls.CORS_ORIGINS,
        }

