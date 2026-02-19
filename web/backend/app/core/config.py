"""
Application Configuration
Single source of truth for all backend settings.
Loads environment variables and provides centralized config management.
"""
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _get_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes')


def _get_int(key: str, default: int = 0) -> int:
    """Parse integer from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_list(key: str, default: str = '') -> List[str]:
    """Parse comma-separated list from environment variable."""
    value = os.getenv(key, default)
    return [item.strip() for item in value.split(',') if item.strip()]


class Config:
    """Base configuration for all backend services."""

    # Application
    APP_NAME: str = 'TripRaft'
    APP_VERSION: str = '1.0.0'
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    DEBUG: bool = _get_bool('FLASK_DEBUG', False)

    # Server
    HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT: int = _get_int('FLASK_PORT', 5000)

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # web/backend/
    DATA_DIR: Path = BASE_DIR / 'data'
    DATABASE_DIR: Path = BASE_DIR.parent / 'database'  # web/database/

    # Database URLs
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{DATABASE_DIR}/tripraft.db'
    )
    TRAVEL_DATABASE_PATH: Path = DATABASE_DIR / 'travel_data_complete.db'
    DATABASE_PATH: Path = TRAVEL_DATABASE_PATH  # Alias for backward compatibility
    SEARCH_INDEX_PATH: Path = DATA_DIR / 'search-index.json'

    # External APIs
    TICKETMASTER_API_KEY: str = os.getenv('TICKETMASTER_API_KEY', '')

    # CORS
    CORS_ORIGINS: List[str] = _get_list(
        'CORS_ORIGINS',
        'http://localhost:5173,http://localhost:5174,http://localhost:3000'
    )

    # Frontend URL (used in invitation emails, etc.)
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    # API Settings
    API_PREFIX: str = '/api/v1'
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100

    # Redis Cache Settings
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_MAX_CONNECTIONS: int = _get_int('REDIS_MAX_CONNECTIONS', 50)
    REDIS_SOCKET_TIMEOUT: int = _get_int('REDIS_SOCKET_TIMEOUT', 5)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = _get_int('REDIS_SOCKET_CONNECT_TIMEOUT', 5)
    REDIS_RETRY_ON_TIMEOUT: bool = _get_bool('REDIS_RETRY_ON_TIMEOUT', True)

    # Cache TTL Settings (seconds)
    CACHE_TYPE: str = 'redis'
    CACHE_DEFAULT_TIMEOUT: int = 300   # 5 minutes
    CACHE_USER_TIMEOUT: int = 3600     # 1 hour
    CACHE_GROUP_TIMEOUT: int = 1800    # 30 minutes
    CACHE_BALANCE_TIMEOUT: int = 300   # 5 minutes

    # Email / SMTP
    SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT: int = _get_int('SMTP_PORT', 587)
    SMTP_USER: str = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL: str = os.getenv('FROM_EMAIL', os.getenv('SMTP_USER', ''))

    # Rate Limiting
    RATELIMIT_ENABLED: bool = False
    RATELIMIT_DEFAULT: str = '100 per hour'
    RATELIMIT_STORAGE_URL: str = 'memory://'

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES: int = _get_int('JWT_ACCESS_TOKEN_EXPIRES', 3600)  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = _get_int('JWT_REFRESH_TOKEN_EXPIRES', 2592000)  # 30 days
    JWT_ALGORITHM: str = 'HS256'

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        errors = []
        if cls.FLASK_ENV == 'production':
            if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
                errors.append('SECRET_KEY must be set in production')
        if errors:
            raise ValueError('; '.join(errors))
        return True

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.DATABASE_DIR.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    FLASK_ENV: str = 'development'
    LOG_LEVEL: str = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    FLASK_ENV: str = 'production'
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_DEFAULT: str = '60 per hour'

    @classmethod
    def validate(cls) -> bool:
        """Validate production configuration."""
        errors = []
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            errors.append('SECRET_KEY must be set in production')
        if not os.getenv('REDIS_URL'):
            errors.append('REDIS_URL must be set in production')
        if errors:
            raise ValueError('; '.join(errors))
        return True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    DATABASE_URL: str = 'sqlite:///:memory:'


# Configuration registry
_config_registry = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config() -> type:
    """Get configuration class based on FLASK_ENV environment variable."""
    env = os.getenv('FLASK_ENV', 'development')
    return _config_registry.get(env, DevelopmentConfig)


class PlaceSearchConfig:
    """Configuration for place search API."""

    MIN_QUERY_LENGTH: int = 2
    MAX_QUERY_LENGTH: int = 100
    DEFAULT_LIMIT: int = 100
    MAX_LIMIT: int = 500

    AUTOCOMPLETE_MIN_LENGTH: int = 2
    AUTOCOMPLETE_MAX_RESULTS: int = 10
    AUTOCOMPLETE_DEBOUNCE_MS: int = 300

    DEFAULT_SORT_BY: str = 'rank_score'
    DEFAULT_SORT_ORDER: str = 'desc'

    VALID_SORT_FIELDS: list = [
        'rank_score', 'name',
        'rating_tourist_priority', 'rating_traveler_experience',
    ]
    VALID_COST_VALUES: list = ['free', 'low', 'medium', 'high']
    VALID_RATING_VALUES: list = [1, 2, 3, 4, 5]


# Backward-compatible config instance used by place_search routes/services
config = PlaceSearchConfig()
