"""
Production Configuration for Expense Engine
All hardcoded values centralized here for easy management
"""

import os
from dataclasses import dataclass


@dataclass
class AuthConfig:
    """Authentication configuration"""
    CLOCK_SKEW_TOLERANCE = int(os.getenv('AUTH_CLOCK_SKEW', '30'))  # Reduced from 60s
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    LOGIN_WINDOW_SECONDS = int(os.getenv('LOGIN_WINDOW_SECONDS', '300'))
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '86400'))  # 24 hours


@dataclass
class CacheConfig:
    """Redis cache TTL configuration (all in seconds)"""
    TTL_USER = int(os.getenv('CACHE_TTL_USER', '3600'))  # 1 hour
    TTL_GROUP = int(os.getenv('CACHE_TTL_GROUP', '600'))  # 10 minutes
    TTL_EXPENSE = int(os.getenv('CACHE_TTL_EXPENSE', '300'))  # 5 minutes
    TTL_BALANCE = int(os.getenv('CACHE_TTL_BALANCE', '60'))  # 1 minute
    TTL_INVITATION = int(os.getenv('CACHE_TTL_INVITATION', '30'))  # 30 seconds
    TTL_INVITATION_DETAILS = int(os.getenv('CACHE_TTL_INVITATION_DETAILS', '30'))  # 30 seconds
    TTL_INVITATION_404 = int(os.getenv('CACHE_TTL_INVITATION_404', '10'))  # 10 seconds
    TTL_SETTLEMENT = int(os.getenv('CACHE_TTL_SETTLEMENT', '300'))  # 5 minutes
    
    # Cache key prefixes
    PREFIX_USER = 'user:'
    PREFIX_GROUP = 'group:'
    PREFIX_EXPENSE = 'expense:'
    PREFIX_BALANCE = 'balance:'
    PREFIX_USER_GROUPS = 'user_groups:'
    PREFIX_GROUP_EXPENSES = 'group_expenses:'
    PREFIX_USER_EXPENSES = 'user_expenses:'
    PREFIX_INVITATIONS = 'invitations:'
    PREFIX_SETTLEMENTS = 'settlements:'
    PREFIX_INVITATION_DETAILS = 'invitation_details:'
    PREFIX_GROUP_FULL = 'group_full:'
    
    # Balance cache configuration
    BALANCE_CACHE_MAX_AGE = int(os.getenv('BALANCE_CACHE_MAX_AGE', '300'))  # 5 minutes


@dataclass
class RedisConfig:
    """Redis connection configuration"""
    DEFAULT_HOST = os.getenv('REDIS_HOST', 'localhost')
    DEFAULT_PORT = int(os.getenv('REDIS_PORT', '6379'))
    DEFAULT_URL = os.getenv('REDIS_URL', f'redis://{DEFAULT_HOST}:{DEFAULT_PORT}/0')
    MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    SOCKET_TIMEOUT = float(os.getenv('REDIS_SOCKET_TIMEOUT', '5.0'))
    SOCKET_CONNECT_TIMEOUT = float(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5.0'))
    SOCKET_KEEPALIVE = os.getenv('REDIS_SOCKET_KEEPALIVE', 'True').lower() == 'true'
    RETRY_ON_TIMEOUT = os.getenv('REDIS_RETRY_ON_TIMEOUT', 'True').lower() == 'true'
    DECODE_RESPONSES = os.getenv('REDIS_DECODE_RESPONSES', 'True').lower() == 'true'
    HEALTH_CHECK_INTERVAL = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))


@dataclass
class IdempotencyConfig:
    """Idempotency configuration"""
    WINDOW_SECONDS = int(os.getenv('IDEMPOTENCY_WINDOW', '2'))  # 2-second window for duplicate detection
    TTL_SECONDS = int(os.getenv('IDEMPOTENCY_TTL', '300'))  # 5-minute TTL for idempotency keys
    LOCK_TIMEOUT = int(os.getenv('IDEMPOTENCY_LOCK_TIMEOUT', '3'))  # 3-second lock timeout


@dataclass
class RetryConfig:
    """Retry logic configuration"""
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '0.5'))  # 500ms
    BACKOFF_MULTIPLIER = float(os.getenv('BACKOFF_MULTIPLIER', '2.0'))
    MAX_RETRY_DELAY = float(os.getenv('MAX_RETRY_DELAY', '5.0'))  # 5 seconds


@dataclass
class PaginationConfig:
    """Pagination configuration"""
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '100'))
    MIN_PAGE_SIZE = int(os.getenv('MIN_PAGE_SIZE', '10'))
    MAX_USERS_BATCH_GET = int(os.getenv('MAX_USERS_BATCH_GET', '100'))  # Firebase limit


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""
    PARALLEL_QUERY_TIMEOUT = int(os.getenv('PARALLEL_QUERY_TIMEOUT', '30'))  # 30 seconds
    MAX_PARALLEL_WORKERS = int(os.getenv('MAX_PARALLEL_WORKERS', '10'))
    BALANCE_RECALC_BATCH_SIZE = int(os.getenv('BALANCE_RECALC_BATCH_SIZE', '100'))
    OPTIMISTIC_STATE_CLEAR_DELAY = int(os.getenv('OPTIMISTIC_STATE_CLEAR_DELAY', '300'))  # 300ms


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    AUTH_MAX_CALLS = int(os.getenv('RATE_LIMIT_AUTH', '5'))  # 5 calls per window
    AUTH_WINDOW = int(os.getenv('RATE_LIMIT_AUTH_WINDOW', '60'))  # 60 seconds
    
    API_MAX_CALLS = int(os.getenv('RATE_LIMIT_API', '100'))  # 100 calls per window
    API_WINDOW = int(os.getenv('RATE_LIMIT_API_WINDOW', '60'))  # 60 seconds
    
    EMAIL_MAX_CALLS = int(os.getenv('RATE_LIMIT_EMAIL', '10'))  # 10 emails per window
    EMAIL_WINDOW = int(os.getenv('RATE_LIMIT_EMAIL_WINDOW', '60'))  # 60 seconds


@dataclass
class SecurityConfig:
    """Security configuration"""
    HASH_ALGORITHM = 'sha256'
    LOG_USER_ID_PREFIX_LENGTH = 8  # Show only first 8 chars of user ID in logs
    MASK_EMAIL_DOMAIN = True  # Mask email domains in logs
    SANITIZE_ERROR_MESSAGES = True  # Don't expose internal errors to users
    
    # Sensitive fields to never log
    SENSITIVE_FIELDS = [
        'password', 'token', 'api_key', 'secret', 'credential',
        'authorization', 'cookie', 'session_id', 'credit_card'
    ]


@dataclass
class EmailConfig:
    """Email service configuration"""
    RATE_LIMIT_PER_HOUR = int(os.getenv('EMAIL_RATE_LIMIT_HOUR', '100'))
    RETRY_MAX_ATTEMPTS = int(os.getenv('EMAIL_RETRY_ATTEMPTS', '3'))
    RETRY_DELAY = float(os.getenv('EMAIL_RETRY_DELAY', '1.0'))
    TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))  # 10 seconds
    
    # URL templates (moved from hardcoded strings)
    INVITATION_URL_TEMPLATE = "{frontend_url}/expenses?invitation={invitation_id}"
    GROUP_URL_TEMPLATE = "{frontend_url}/expenses?group={group_id}"
    SETTLEMENT_URL_TEMPLATE = "{frontend_url}/expenses?group={group_id}&tab=settlements"


@dataclass
class LoggingConfig:
    """Logging configuration"""
    # Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'True').lower() == 'true'
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/expense_engine.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # What to log in production
    LOG_CACHE_HITS = os.getenv('LOG_CACHE_HITS', 'False').lower() == 'true'
    LOG_FIRESTORE_OPS = os.getenv('LOG_FIRESTORE_OPS', 'False').lower() == 'true'
    LOG_PERFORMANCE_METRICS = os.getenv('LOG_PERFORMANCE_METRICS', 'True').lower() == 'true'
    LOG_USER_ACTIONS = os.getenv('LOG_USER_ACTIONS', 'True').lower() == 'true'
    
    # Debug logging (disable in production)
    DEBUG_ENABLED = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    DEBUG_SAMPLE_RATE = float(os.getenv('DEBUG_SAMPLE_RATE', '0.01'))  # 1% sampling


# Export all configurations
__all__ = [
    'AuthConfig',
    'CacheConfig',
    'RedisConfig',
    'IdempotencyConfig',
    'RetryConfig',
    'PaginationConfig',
    'PerformanceConfig',
    'RateLimitConfig',
    'SecurityConfig',
    'EmailConfig',
    'LoggingConfig'
]
