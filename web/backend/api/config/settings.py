"""
Application Configuration
Loads environment variables and provides centralized config management.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    # Application
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Server
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Database
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATABASE_DIR = BASE_DIR / 'places_database'
    DATABASE_PATH = DATABASE_DIR / 'tripraft.db'
    SEARCH_INDEX_PATH = DATABASE_DIR / 'search-index.json'
    UNIVERSAL_SEARCH_INDEX_PATH = DATABASE_DIR / 'universal-search-index.json'
    
    # CORS - Allow both common dev ports
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    
    # API Settings
    API_PREFIX = '/api/v1'
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    
    # Redis Cache Settings
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', 50))
    REDIS_SOCKET_TIMEOUT = int(os.getenv('REDIS_SOCKET_TIMEOUT', 5))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 5))
    REDIS_RETRY_ON_TIMEOUT = os.getenv('REDIS_RETRY_ON_TIMEOUT', 'True').lower() == 'true'
    
    # Cache Settings
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_USER_TIMEOUT = 3600  # 1 hour
    CACHE_GROUP_TIMEOUT = 1800  # 30 minutes
    CACHE_BALANCE_TIMEOUT = 300  # 5 minutes
    
    # Rate Limiting (for future use)
    RATELIMIT_ENABLED = False
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        # Database validation removed - not required for expense/group features
        return True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    # In production, ensure SECRET_KEY is set
    if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        raise ValueError("SECRET_KEY must be set in production!")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
