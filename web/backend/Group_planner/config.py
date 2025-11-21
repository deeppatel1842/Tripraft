"""
Group Planner Configuration
Centralized configuration management for the group planner system
Following enterprise-grade configuration patterns and professional backend standards
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# Collection name constants (centralized - prevents typos, improves maintainability)
_COLLECTIONS = {
    'TRAVEL_GROUPS': 'travel_groups',
    'GROUP_MEMBERS': 'group_members',
    'TRAVEL_PLACES': 'travel_places',
    'TRAVEL_POLLS': 'travel_polls',
    'GROUP_INVITATIONS': 'group_invitations',
    'TRIP_DOCUMENTS': 'trip_documents',
    'USERS': 'users'  # Shared with expense system
}

# Cache TTL (Time To Live) settings - optimized for different data volatility
_CACHE_TTL = {
    'GROUP': 3600,              # 1 hour - stable
    'USER_GROUPS': 1800,        # 30 minutes - medium volatility
    'GROUP_MEMBERS': 3600,      # 1 hour - stable
    'GROUP_PLACES': 1800,       # 30 minutes - volatile
    'GROUP_POLLS': 900,         # 15 minutes - highly volatile
    'USER_INVITATIONS': 300,    # 5 minutes - status changes frequently
    'USER_PROFILE': 7200,       # 2 hours - stable
}

# Cache key patterns - professional naming convention
_CACHE_KEYS = {
    'GROUP': 'groupplanner:group:%s',
    'USER_GROUPS': 'groupplanner:user_groups:%s',
    'GROUP_MEMBERS': 'groupplanner:group_members:%s',
    'GROUP_PLACES': 'groupplanner:group_places:%s',
    'GROUP_POLLS': 'groupplanner:group_polls:%s',
    'USER_INVITATIONS': 'groupplanner:user_invitations:%s',
    'USER_PROFILE': 'groupplanner:user:%s',
}


class FirebaseConfig:
    """Firebase configuration settings - enterprise grade"""
    
    CREDENTIALS_PATH: str = os.getenv('FIREBASE_CREDENTIALS_PATH', '')
    PROJECT_ID: str = os.getenv('FIREBASE_PROJECT_ID', '')
    COLLECTIONS: Dict[str, str] = _COLLECTIONS
    BATCH_OPERATION_LIMIT: int = 500  # Firestore batch write limit

    @staticmethod
    def get_collection(key: str) -> str:
        """Get collection name safely"""
        return FirebaseConfig.COLLECTIONS.get(key, '')




class RedisConfig:
    """Redis cache configuration - optimized for production"""
    
    DEFAULT_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    MAX_CONNECTIONS: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    SOCKET_TIMEOUT: int = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))
    HEALTH_CHECK_INTERVAL: int = 30
    
    # Cache TTL mappings
    TTL: Dict[str, int] = _CACHE_TTL
    CACHE_KEYS: Dict[str, str] = _CACHE_KEYS

    @staticmethod
    def get_ttl(key: str) -> int:
        """Get TTL for resource type - safe access"""
        return RedisConfig.TTL.get(key, 3600)

    @staticmethod
    def get_cache_key(key_type: str, resource_id: str) -> str:
        """Generate cache key following professional conventions"""
        pattern = RedisConfig.CACHE_KEYS.get(key_type, '')
        return pattern % resource_id if pattern else ''





class EmailConfig:
    """Email service configuration"""
    
    SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER: str = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL: str = os.getenv('FROM_EMAIL', '')
    TEMPLATES_DIR: str = 'templates/email'
    DEFAULT_CHARSET: str = 'utf-8'
    MAX_EMAILS_PER_HOUR: int = int(os.getenv('MAX_EMAILS_PER_HOUR', '100'))
    MAX_EMAILS_PER_DAY: int = int(os.getenv('MAX_EMAILS_PER_DAY', '1000'))


class ApplicationConfig:
    """Main application configuration"""
    
    APP_NAME: str = os.getenv('APP_NAME', 'TripRaft Group Planner')
    ENVIRONMENT: str = os.getenv('APP_ENV', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    API_BASE_URL: str = os.getenv('API_BASE_URL', 'http://localhost:5000')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    JWT_EXPIRATION_HOURS: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    MAX_GROUP_MEMBERS: int = int(os.getenv('MAX_GROUP_MEMBERS', '50'))
    MAX_PLACES_PER_GROUP: int = int(os.getenv('MAX_PLACES_PER_GROUP', '100'))
    MAX_POLLS_PER_GROUP: int = int(os.getenv('MAX_POLLS_PER_GROUP', '20'))
    INVITATION_EXPIRY_DAYS: int = int(os.getenv('INVITATION_EXPIRY_DAYS', '7'))


class LoggingConfig:
    """Logging configuration"""
    
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE_MAX_BYTES: int = int(os.getenv('LOG_FILE_MAX_BYTES', '10485760'))
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    MAIN_LOG_FILE: str = os.getenv('MAIN_LOG_FILE', 'logs/groupplanner.log')
    ERROR_LOG_FILE: str = os.getenv('ERROR_LOG_FILE', 'logs/groupplanner_errors.log')


class PerformanceConfig:
    """Performance and optimization settings"""
    
    DEFAULT_PAGE_SIZE: int = int(os.getenv('DEFAULT_PAGE_SIZE', '20'))
    MAX_PAGE_SIZE: int = int(os.getenv('MAX_PAGE_SIZE', '100'))
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '500'))
    DATABASE_TIMEOUT: int = int(os.getenv('DATABASE_TIMEOUT', '30'))
    CACHE_TIMEOUT: int = int(os.getenv('CACHE_TIMEOUT', '5'))
    EMAIL_TIMEOUT: int = int(os.getenv('EMAIL_TIMEOUT', '10'))


class ConfigValidator:
    """Configuration validation utility"""

    @staticmethod
    def validate_required_settings():
        """Validate that all required settings are configured"""
        errors = []

        # Check Firebase credentials
        if not FirebaseConfig.CREDENTIALS_PATH:
            errors.append("FIREBASE_CREDENTIALS_PATH environment variable is required")
        elif not os.path.exists(FirebaseConfig.CREDENTIALS_PATH):
            errors.append(f"Firebase credentials file not found: {FirebaseConfig.CREDENTIALS_PATH}")

        # Check critical app settings
        if ApplicationConfig.ENVIRONMENT == "production":
            if ApplicationConfig.SECRET_KEY == "dev-secret-change-in-production":
                errors.append("SECRET_KEY must be changed for production environment")

            if ApplicationConfig.DEBUG:
                errors.append("DEBUG should be false in production environment")

        return errors

    @staticmethod
    def validate_email_config():
        """Check if email configuration is complete"""
        return bool(
            EmailConfig.SMTP_USER
            and EmailConfig.SMTP_PASSWORD
            and EmailConfig.FROM_EMAIL
        )

    @staticmethod
    def get_config_summary():
        """Get a summary of current configuration (safe for logging)"""
        return {
            "app_name": ApplicationConfig.APP_NAME,
            "environment": ApplicationConfig.ENVIRONMENT,
            "debug_mode": ApplicationConfig.DEBUG,
            "frontend_url": ApplicationConfig.FRONTEND_URL,
            "firebase_configured": bool(FirebaseConfig.CREDENTIALS_PATH),
            "redis_url": RedisConfig.DEFAULT_URL,
            "email_configured": ConfigValidator.validate_email_config(),
            "cache_enabled": PerformanceConfig.CACHE_ENABLED,
        }


# Helper functions for convenience
def get_collection_name(collection_type: str) -> str:
    """Get Firebase collection name by type"""
    return FirebaseConfig.get_collection(collection_type.upper())


def get_cache_key(key_type: str, identifier: str) -> str:
    """Generate standardized cache key"""
    pattern = RedisConfig.CACHE_KEYS.get(key_type.upper())
    if not pattern:
        raise ValueError(f"Unknown cache key type: {key_type}")
    return pattern % identifier


def get_cache_ttl(cache_type: str) -> int:
    """Get cache TTL for specific data type"""
    return RedisConfig.get_ttl(cache_type.upper())


def is_production() -> bool:
    """Check if running in production environment"""
    return ApplicationConfig.ENVIRONMENT == "production"


def is_development() -> bool:
    """Check if running in development environment"""
    return ApplicationConfig.ENVIRONMENT == "development"