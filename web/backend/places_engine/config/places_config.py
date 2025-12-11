"""
Places Engine Configuration

Configuration class for the places engine with paths and constants.
"""

import os
from pathlib import Path

from .constants import EnvironmentConfig


class PlacesEngineConfig:
    """Configuration for Places Engine."""

    # Base paths
    BACKEND_DIR = Path(__file__).parent.parent.parent  # web/backend
    ENGINE_DIR = BACKEND_DIR / 'places_engine'
    PIPELINE_DIR = ENGINE_DIR / 'pipeline'
    DATA_DIR = ENGINE_DIR / 'data'
    REPORTS_DIR = ENGINE_DIR / 'reports'
    AGGREGATED_DIR = PIPELINE_DIR / 'aggregated_data'
    PREPARED_DIR = PIPELINE_DIR / 'prepared_data'

    # Data files
    PLACES_JSON = AGGREGATED_DIR / 'places.json'
    CITIES_JSON = PREPARED_DIR / 'cities.json'
    COUNTRIES_JSON = PREPARED_DIR / 'countries.json'
    STATES_JSON = PREPARED_DIR / 'states.json'
    SEARCH_INDEX_JSON = AGGREGATED_DIR / 'search_index_documents.json'

    # Reports
    ANALYSIS_REPORT = REPORTS_DIR / 'analysis_report.json'
    ANALYSIS_REPORT_TXT = REPORTS_DIR / 'analysis_report.txt'
    PHOTO_VALIDATION_REPORT = REPORTS_DIR / 'photo_validation_report.json'

    # Environment config
    ENV = EnvironmentConfig.ENV
    DEBUG = EnvironmentConfig.DEBUG
    TESTING = EnvironmentConfig.TESTING

    # Firebase
    FIREBASE_CREDENTIALS = EnvironmentConfig.FIREBASE_CREDENTIALS
    FIREBASE_PROJECT_ID = EnvironmentConfig.FIREBASE_PROJECT_ID

    # Redis
    REDIS_HOST = EnvironmentConfig.REDIS_HOST
    REDIS_PORT = EnvironmentConfig.REDIS_PORT
    REDIS_DB = EnvironmentConfig.REDIS_DB
    REDIS_PASSWORD = EnvironmentConfig.REDIS_PASSWORD

    # Cache TTL
    CACHE_TTL_AUTOCOMPLETE = EnvironmentConfig.CACHE_TTL_AUTOCOMPLETE
    CACHE_TTL_SEARCH = EnvironmentConfig.CACHE_TTL_SEARCH
    CACHE_TTL_PLACES = EnvironmentConfig.CACHE_TTL_PLACES

    # Search limits
    SEARCH_LIMIT_DEFAULT = EnvironmentConfig.SEARCH_LIMIT_DEFAULT
    SEARCH_LIMIT_MAX = EnvironmentConfig.SEARCH_LIMIT_MAX
    AUTOCOMPLETE_LIMIT_DEFAULT = EnvironmentConfig.AUTOCOMPLETE_LIMIT_DEFAULT
    AUTOCOMPLETE_LIMIT_MAX = EnvironmentConfig.AUTOCOMPLETE_LIMIT_MAX

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        for dir_path in [cls.DATA_DIR, cls.REPORTS_DIR, cls.AGGREGATED_DIR, cls.PREPARED_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
