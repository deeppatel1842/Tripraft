"""
Application Settings

Centralizes all application settings and provides a singleton instance.
"""

from dataclasses import dataclass
from typing import Optional

from .constants import EnvironmentConfig


@dataclass
class Settings:
    """Application settings."""

    env: str = EnvironmentConfig.ENV
    debug: bool = EnvironmentConfig.DEBUG
    testing: bool = EnvironmentConfig.TESTING

    # Firebase
    firebase_credentials: Optional[str] = EnvironmentConfig.FIREBASE_CREDENTIALS
    firebase_project_id: str = EnvironmentConfig.FIREBASE_PROJECT_ID

    # Redis
    redis_host: str = EnvironmentConfig.REDIS_HOST
    redis_port: int = EnvironmentConfig.REDIS_PORT
    redis_db: int = EnvironmentConfig.REDIS_DB
    redis_password: Optional[str] = EnvironmentConfig.REDIS_PASSWORD

    # API
    api_title: str = EnvironmentConfig.API_TITLE
    api_version: str = EnvironmentConfig.API_VERSION
    api_description: str = EnvironmentConfig.API_DESCRIPTION

    # Cache TTL
    cache_ttl_autocomplete: int = EnvironmentConfig.CACHE_TTL_AUTOCOMPLETE
    cache_ttl_search: int = EnvironmentConfig.CACHE_TTL_SEARCH
    cache_ttl_places: int = EnvironmentConfig.CACHE_TTL_PLACES

    # Search limits
    search_limit_default: int = EnvironmentConfig.SEARCH_LIMIT_DEFAULT
    search_limit_max: int = EnvironmentConfig.SEARCH_LIMIT_MAX
    autocomplete_limit_default: int = EnvironmentConfig.AUTOCOMPLETE_LIMIT_DEFAULT
    autocomplete_limit_max: int = EnvironmentConfig.AUTOCOMPLETE_LIMIT_MAX

    # Logging
    log_level: str = EnvironmentConfig.LOG_LEVEL
    log_format: str = EnvironmentConfig.LOG_FORMAT


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings instance.

    Returns:
        Settings: Singleton settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings) -> None:
    """
    Set application settings instance (for testing).

    Args:
        settings: Settings instance to use
    """
    global _settings
    _settings = settings
