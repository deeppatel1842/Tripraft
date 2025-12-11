"""
Environment Configuration Constants

Defines configuration values based on environment.
"""

import os
from enum import Enum


class Environment(str, Enum):
    """Supported environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentConfig:
    """Environment configuration."""

    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    TESTING = os.getenv('FLASK_TESTING', 'False').lower() == 'true'

    # Firebase
    FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'tripraft-23fe7')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    # API Configuration
    API_TITLE = 'TripRaft Places Engine API'
    API_VERSION = '1.0.0'
    API_DESCRIPTION = 'RESTful API for places discovery and search'

    # Cache TTL (Time To Live)
    CACHE_TTL_AUTOCOMPLETE = 3600  # 1 hour
    CACHE_TTL_SEARCH = 1800  # 30 minutes
    CACHE_TTL_PLACES = 3600  # 1 hour

    # Search limits
    SEARCH_LIMIT_DEFAULT = 20
    SEARCH_LIMIT_MAX = 100
    AUTOCOMPLETE_LIMIT_DEFAULT = 10
    AUTOCOMPLETE_LIMIT_MAX = 20

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
