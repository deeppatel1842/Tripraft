# Purpose: Application Configuration Single source of truth for all backend settings.
"""
Application Configuration
Single source of truth for all backend settings.
Loads environment variables and provides centralized config management.
"""
import json
import os
from pathlib import Path
from typing import Dict, List

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

    # Request-level safety caps for admin bulk imports. Flask reads
    # MAX_CONTENT_LENGTH to reject oversized bodies before decoding them.
    MAX_CONTENT_LENGTH: int = _get_int('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    MAX_BULK_INGEST_ITEMS: int = _get_int('MAX_BULK_INGEST_ITEMS', 1000)

    # Application
    APP_NAME: str = 'TripRaft'
    APP_VERSION: str = os.getenv('APP_VERSION', '2.0.0')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')

    @classmethod
    def validate_production(cls):
        """Fail fast if production is misconfigured."""
        if cls.FLASK_ENV == 'production' and cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise RuntimeError('SECRET_KEY must be set in production. Refusing to start.')
    DEBUG: bool = _get_bool('FLASK_DEBUG', False)

    # Server
    HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT: int = _get_int('FLASK_PORT', 5000)

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # services/api/
    REPOSITORY_ROOT: Path = Path(os.getenv('TRIPRAFT_ROOT', str(BASE_DIR.parent.parent)))
    DATA_DIR: Path = REPOSITORY_ROOT / 'data'
    DATABASE_DIR: Path = Path(os.getenv('TRAVEL_DATABASE_DIR', str(DATA_DIR / 'catalog')))

    # Database URLs
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{DATA_DIR / 'runtime' / 'tripraft.db'}"
    )
    TRAVEL_DATABASE_PATH: Path = Path(os.getenv('TRAVEL_DATABASE_PATH', str(DATABASE_DIR / 'travel_data_complete.db')))
    DATABASE_PATH: Path = TRAVEL_DATABASE_PATH  # Alias for backward compatibility
    SEARCH_INDEX_PATH: Path = DATA_DIR / 'search-index.json'

    # Travel Data URL (read replica in production)
    TRAVEL_DATA_URL: str = os.getenv(
        'TRAVEL_DATA_URL',
        f'sqlite:///{DATABASE_DIR}/travel_data_complete.db'
    )

    # PostgreSQL Pool Settings (overridable via env)
    DB_POOL_SIZE: int = _get_int('DB_POOL_SIZE', 20)
    DB_MAX_OVERFLOW: int = _get_int('DB_MAX_OVERFLOW', 10)
    DB_POOL_RECYCLE: int = _get_int('DB_POOL_RECYCLE', 1800)
    DB_POOL_TIMEOUT: int = _get_int('DB_POOL_TIMEOUT', 30)
    SQL_ECHO: bool = _get_bool('SQL_ECHO', False)

    # Travel Data Pool Settings (read replica — lighter pool)
    TRAVEL_POOL_SIZE: int = _get_int('TRAVEL_POOL_SIZE', 10)
    TRAVEL_MAX_OVERFLOW: int = _get_int('TRAVEL_MAX_OVERFLOW', 5)

    # Admin
    ADMIN_EMAILS: List[str] = _get_list('ADMIN_EMAILS', '')

    # A proxy may supply X-Forwarded-For only when its direct address is
    # explicitly trusted.  Empty by default: a public client must never be
    # able to choose its own rate-limit identity.
    TRUSTED_PROXY_IPS: List[str] = _get_list('TRUSTED_PROXY_IPS', '')

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

    # Deprecated endpoint sunset date (RFC 8594)
    API_SUNSET_DATE: str = os.getenv('API_SUNSET_DATE', 'Fri, 17 Sep 2027 00:00:00 GMT')

    # Redis Cache Settings
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_MAX_CONNECTIONS: int = _get_int('REDIS_MAX_CONNECTIONS', 50)
    REDIS_SOCKET_TIMEOUT: int = _get_int('REDIS_SOCKET_TIMEOUT', 5)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = _get_int('REDIS_SOCKET_CONNECT_TIMEOUT', 5)
    REDIS_RETRY_ON_TIMEOUT: bool = _get_bool('REDIS_RETRY_ON_TIMEOUT', True)

    # Celery (async task queue)
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    # Cache TTL Settings (seconds)
    CACHE_TYPE: str = 'redis'
    CACHE_DEFAULT_TIMEOUT: int = 300   # 5 minutes
    CACHE_USER_TIMEOUT: int = 3600     # 1 hour
    CACHE_GROUP_TIMEOUT: int = 1800    # 30 minutes
    CACHE_BALANCE_TIMEOUT: int = 300   # 5 minutes

    # --- Centralized Cache TTLs (used by @cache_response decorators) ---
    CACHE_TTLS: Dict[str, int] = {
        'user_list':       _get_int('CACHE_TTL_USER_LIST', 30),
        'user_detail':     _get_int('CACHE_TTL_USER_DETAIL', 60),
        'search':          _get_int('CACHE_TTL_SEARCH', 300),
        'autocomplete':    _get_int('CACHE_TTL_AUTOCOMPLETE', 600),
        'place_detail':    _get_int('CACHE_TTL_PLACE_DETAIL', 3600),
        'expense_list':    _get_int('CACHE_TTL_EXPENSE_LIST', 30),
        'expense_summary': _get_int('CACHE_TTL_EXPENSE_SUMMARY', 60),
        'group_list':      _get_int('CACHE_TTL_GROUP_LIST', 30),
        'group_detail':    _get_int('CACHE_TTL_GROUP_DETAIL', 30),
        'events':          _get_int('CACHE_TTL_EVENTS', 3600),
        'categories':      _get_int('CACHE_TTL_CATEGORIES', 86400),
        'countries':       _get_int('CACHE_TTL_COUNTRIES', 3600),
        'dashboard':       _get_int('CACHE_TTL_DASHBOARD', 30),
        'activities':      _get_int('CACHE_TTL_ACTIVITIES', 30),
        'members':         _get_int('CACHE_TTL_MEMBERS', 30),
        'stats':           _get_int('CACHE_TTL_STATS', 3600),
        'settlements':     _get_int('CACHE_TTL_SETTLEMENTS', 30),
        'invitations':     _get_int('CACHE_TTL_INVITATIONS', 30),
        'city_search':     _get_int('CACHE_TTL_CITY_SEARCH', 600),
        'location_detail': _get_int('CACHE_TTL_LOCATION_DETAIL', 1800),
        'destinations':    _get_int('CACHE_TTL_DESTINATIONS', 600),
        'cities':          _get_int('CACHE_TTL_CITIES', 86400),
        'chat_unread':     _get_int('CACHE_TTL_CHAT_UNREAD', 30),
    }

    # --- Cache Invalidation Patterns ---
    # Maps write operations to cache key patterns that should be invalidated.
    CACHE_INVALIDATION_PATTERNS: Dict[str, List[str]] = {
        'expense_create':    ['expenses:*', 'expense_list:*', 'expense_summary:*', 'group_detail:*'],
        'expense_update':    ['expenses:*', 'expense_list:*', 'expense_summary:*', 'group_detail:*'],
        'expense_delete':    ['expenses:*', 'expense_list:*', 'expense_summary:*', 'group_detail:*'],
        'group_create':      ['group_list:*'],
        'group_update':      ['group_list:*', 'group_detail:*'],
        'settlement_create': ['settlements:*', 'expense_summary:*', 'group_detail:*'],
        'settlement_delete': ['settlements:*', 'expense_summary:*', 'group_detail:*'],
        'place_update':      ['search:*', 'autocomplete:*', 'place_detail:*'],
        'profile_update':    ['user_detail:*'],
        'gp_group_mutate':   ['gp:*'],
    }

    # --- Centralized Rate Limits (used by @limit_api decorators) ---
    RATE_LIMITS: Dict[str, str] = {
        'auth':         os.getenv('RATE_LIMIT_AUTH', '5 per minute'),
        'read_light':   os.getenv('RATE_LIMIT_READ_LIGHT', '200 per minute'),
        'read_heavy':   os.getenv('RATE_LIMIT_READ_HEAVY', '60 per minute'),
        'create':       os.getenv('RATE_LIMIT_CREATE', '30 per minute'),
        'update':       os.getenv('RATE_LIMIT_UPDATE', '30 per minute'),
        'delete':       os.getenv('RATE_LIMIT_DELETE', '10 per minute'),
        'search':       os.getenv('RATE_LIMIT_SEARCH', '60 per minute'),
        'autocomplete': os.getenv('RATE_LIMIT_AUTOCOMPLETE', '120 per minute'),
        'settle':       os.getenv('RATE_LIMIT_SETTLE', '10 per minute'),
        'invitation':   os.getenv('RATE_LIMIT_INVITATION', '10 per minute'),
        'events':       os.getenv('RATE_LIMIT_EVENTS', '30 per minute'),
        'geocode':      os.getenv('RATE_LIMIT_GEOCODE', '10 per minute'),
        'external':     os.getenv('RATE_LIMIT_EXTERNAL', '10 per minute'),
        'chat_send':    os.getenv('RATE_LIMIT_CHAT_SEND', '30 per minute'),
        'chat_ai':      os.getenv('RATE_LIMIT_CHAT_AI', '10 per minute'),
        'export':       os.getenv('RATE_LIMIT_EXPORT', '5 per minute'),
    }

    # --- Pagination ---
    GP_DEFAULT_LIMIT: int = _get_int('GP_DEFAULT_LIMIT', 50)
    GP_MAX_LIMIT: int = _get_int('GP_MAX_LIMIT', 100)
    EXPENSE_DEFAULT_LIMIT: int = _get_int('EXPENSE_DEFAULT_LIMIT', 50)
    EXPENSE_MAX_LIMIT: int = _get_int('EXPENSE_MAX_LIMIT', 100)
    SEARCH_DEFAULT_LIMIT: int = _get_int('SEARCH_DEFAULT_LIMIT', 20)
    SEARCH_MAX_LIMIT: int = _get_int('SEARCH_MAX_LIMIT', 100)
    AUTOCOMPLETE_LIMIT: int = _get_int('AUTOCOMPLETE_LIMIT', 10)
    AUTOCOMPLETE_MAX_LIMIT: int = _get_int('AUTOCOMPLETE_MAX_LIMIT', 20)

    # --- Auth & Security ---
    BCRYPT_ROUNDS: int = _get_int('BCRYPT_ROUNDS', 12)
    PASSWORD_MIN_LENGTH: int = _get_int('PASSWORD_MIN_LENGTH', 8)
    PASSWORD_MAX_LENGTH: int = _get_int('PASSWORD_MAX_LENGTH', 128)
    PASSWORD_SPECIAL_CHARS: str = os.getenv(
        'PASSWORD_SPECIAL_CHARS', '!@#$%^&*()_+-=[]{}|;:,./<>?'
    )
    COOKIE_SAMESITE: str = os.getenv('COOKIE_SAMESITE', 'Lax')
    COOKIE_PATH: str = os.getenv('COOKIE_PATH', '/')
    COOKIE_SECURE: bool = _get_bool('COOKIE_SECURE', os.getenv('FLASK_ENV', 'development') == 'production')
    COOKIE_HTTPONLY: bool = _get_bool('COOKIE_HTTPONLY', True)
    INVITATION_EXPIRY_DAYS: int = _get_int('INVITATION_EXPIRY_DAYS', 7)
    TOKEN_REFRESH_THRESHOLD: int = _get_int('TOKEN_REFRESH_THRESHOLD', 60)

    # --- External Services ---
    TICKETMASTER_BASE_URL: str = os.getenv(
        'TICKETMASTER_BASE_URL',
        'https://app.ticketmaster.com/discovery/v2'
    )
    TICKETMASTER_SEGMENT_IDS: Dict[str, str] = json.loads(os.getenv(
        'TICKETMASTER_SEGMENT_IDS',
        json.dumps({
            'Music': 'KZFzniwnSyZfZ7v7nJ',
            'Sports': 'KZFzniwnSyZfZ7v7nE',
            'Arts & Theatre': 'KZFzniwnSyZfZ7v7na',
            'Film': 'KZFzniwnSyZfZ7v7nn',
            'Miscellaneous': 'KZFzniwnSyZfZ7v7n1',
        })
    ))
    NOMINATIM_BASE_URL: str = os.getenv(
        'NOMINATIM_BASE_URL', 'https://nominatim.openstreetmap.org/search'
    )
    NOMINATIM_USER_AGENT: str = os.getenv(
        'NOMINATIM_USER_AGENT', 'TripRaft/1.0 (contact@tripraft.com)'
    )
    NOMINATIM_TIMEOUT: int = _get_int('NOMINATIM_TIMEOUT', 5)
    TICKETMASTER_TIMEOUT: int = _get_int('TICKETMASTER_TIMEOUT', 10)
    SMTP_TIMEOUT: int = _get_int('SMTP_TIMEOUT', 10)

    # --- Circuit Breaker ---
    CIRCUIT_BREAKER_FAIL_MAX: int = _get_int('CIRCUIT_BREAKER_FAIL_MAX', 5)
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = _get_int('CIRCUIT_BREAKER_RESET_TIMEOUT', 30)

    # --- Request Size Limits ---
    MAX_ITINERARY_SIZE: int = _get_int('MAX_ITINERARY_SIZE', 102400)  # 100KB
    MAX_PLACE_REMARKS_SIZE: int = _get_int('MAX_PLACE_REMARKS_SIZE', 5120)  # 5KB
    MAX_POLL_OPTIONS: int = _get_int('MAX_POLL_OPTIONS', 20)
    MAX_POLL_OPTION_LENGTH: int = _get_int('MAX_POLL_OPTION_LENGTH', 200)
    MAX_CHECKLIST_ITEM_LENGTH: int = _get_int('MAX_CHECKLIST_ITEM_LENGTH', 500)

    # --- Chat ---
    CHAT_MESSAGE_MAX_LENGTH: int = _get_int('CHAT_MESSAGE_MAX_LENGTH', 5000)
    CHAT_SUMMARY_TRIGGER: int = _get_int('CHAT_SUMMARY_TRIGGER', 50)
    CHAT_MESSAGE_RETENTION_DAYS: int = _get_int('CHAT_MESSAGE_RETENTION_DAYS', 180)
    FF_GROUP_CHAT: bool = _get_bool('FF_GROUP_CHAT', True)
    FF_AI_CHATBOT: bool = _get_bool('FF_AI_CHATBOT', True)

    # --- AI Scout Agent (Phase 31) ---
    FF_SCOUT_AGENT: bool = _get_bool('FF_SCOUT_AGENT', True)
    SCOUT_AGENT_MENTION: str = '@scout'

    # Ollama LLM
    OLLAMA_BASE_URL: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL_LIGHT: str = os.getenv('OLLAMA_MODEL_LIGHT', 'gemma3:latest')
    OLLAMA_MODEL_HEAVY: str = os.getenv('OLLAMA_MODEL_HEAVY', 'gemma3:latest')
    OLLAMA_REQUEST_TIMEOUT: int = _get_int('OLLAMA_REQUEST_TIMEOUT', 30)
    OLLAMA_MAX_TOKENS: int = _get_int('OLLAMA_MAX_TOKENS', 400)
    OLLAMA_TEMPERATURE: float = float(os.getenv('OLLAMA_TEMPERATURE', '0.3'))

    # Scout rate limits
    SCOUT_RATE_USER_PER_MIN: int = _get_int('SCOUT_RATE_USER_PER_MIN', 5)
    SCOUT_RATE_GROUP_PER_DAY: int = _get_int('SCOUT_RATE_GROUP_PER_DAY', 150)
    SCOUT_RATE_LLM_PER_GROUP_DAY: int = _get_int('SCOUT_RATE_LLM_PER_GROUP_DAY', 50)

    # Scout output
    SCOUT_MAX_RESPONSE_CHARS: int = _get_int('SCOUT_MAX_RESPONSE_CHARS', 1500)
    SCOUT_CONSENT_VERSION: str = os.getenv('SCOUT_CONSENT_VERSION', '1.0')

    # Scout circuit breaker (overrides global defaults for Ollama)
    SCOUT_CB_FAIL_MAX: int = _get_int('SCOUT_CB_FAIL_MAX', 3)
    SCOUT_CB_RECOVERY_TIMEOUT: int = _get_int('SCOUT_CB_RECOVERY_TIMEOUT', 300)

    # SearXNG self-hosted search
    SEARXNG_BASE_URL: str = os.getenv('SEARXNG_BASE_URL', 'http://searxng:8080')
    SEARXNG_TIMEOUT: int = _get_int('SEARXNG_TIMEOUT', 3)

    # Agent log retention
    AGENT_LOG_RETENTION_DAYS: int = _get_int('AGENT_LOG_RETENTION_DAYS', 90)

    # --- AI Crew Agent (Phase 32) ---
    FF_CREW_AGENT: bool = _get_bool('FF_CREW_AGENT', True)
    CREW_AGENT_MENTION: str = '@crew'
    CREW_SYSTEM_USER_ID: str = os.getenv('CREW_SYSTEM_USER_ID', 'ai-crew')
    OLLAMA_MODEL_CREW: str = os.getenv('OLLAMA_MODEL_CREW', 'gemma3:latest')

    # Crew rate limits
    CREW_RATE_USER_PER_MIN: int = _get_int('CREW_RATE_USER_PER_MIN', 10)
    CREW_RATE_GROUP_PER_DAY: int = _get_int('CREW_RATE_GROUP_PER_DAY', 300)

    # Crew conversation TTL (seconds) — how long a multi-turn Q&A stays alive
    CREW_CONV_TTL: int = _get_int('CREW_CONV_TTL', 60)

    # Crew input limits (ReDoS prevention)
    CREW_MAX_INPUT_CHARS: int = _get_int('CREW_MAX_INPUT_CHARS', 500)

    # Crew output
    CREW_MAX_RESPONSE_CHARS: int = _get_int('CREW_MAX_RESPONSE_CHARS', 1500)

    # --- Business Logic ---
    DEFAULT_CURRENCY: str = os.getenv('DEFAULT_CURRENCY', 'USD')
    BALANCE_THRESHOLD: float = float(os.getenv('BALANCE_THRESHOLD', '0.01'))
    GROUP_CODE_LENGTH: int = _get_int('GROUP_CODE_LENGTH', 8)
    GROUP_CODE_CHARSET: str = os.getenv(
        'GROUP_CODE_CHARSET', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    )
    PLACES_COUNT_THRESHOLD: int = _get_int('PLACES_COUNT_THRESHOLD', 30)
    PLACES_CITY_LIMIT: int = _get_int('PLACES_CITY_LIMIT', 500)
    PLACES_TOP_PER_PARTITION: int = _get_int('PLACES_TOP_PER_PARTITION', 5)
    TRIP_START_HOUR: int = _get_int('TRIP_START_HOUR', 9)
    TRIP_HOURS_BETWEEN_STOPS: int = _get_int('TRIP_HOURS_BETWEEN_STOPS', 2)
    TRIP_LUNCH_AFTER_STOP: int = _get_int('TRIP_LUNCH_AFTER_STOP', 2)
    PAYMENT_METHODS: List[str] = _get_list(
        'PAYMENT_METHODS', 'cash,bank_transfer,upi,paypal,other'
    )
    DEFAULT_PAYMENT_METHOD: str = os.getenv('DEFAULT_PAYMENT_METHOD', 'cash')
    SPLIT_TYPES: List[str] = _get_list(
        'SPLIT_TYPES', 'equal,exact,percentage,shares,none'
    )
    PRIORITY_LEVELS: List[str] = _get_list('PRIORITY_LEVELS', 'low,medium,high')
    DEFAULT_PRIORITY: str = os.getenv('DEFAULT_PRIORITY', 'medium')
    PLACE_CATEGORIES: List[str] = _get_list(
        'PLACE_CATEGORIES', 'attraction,restaurant,hotel,event,other'
    )
    DEFAULT_PLACE_CATEGORY: str = os.getenv('DEFAULT_PLACE_CATEGORY', 'attraction')
    MAX_EXPENSE_AMOUNT: float = float(os.getenv('MAX_EXPENSE_AMOUNT', '1000000'))
    MAX_BUDGET_AMOUNT: float = float(os.getenv('MAX_BUDGET_AMOUNT', '100000000'))
    TRIP_DEFAULT_DAYS: int = _get_int('TRIP_DEFAULT_DAYS', 3)
    TRIP_MIN_DAYS: int = _get_int('TRIP_MIN_DAYS', 1)
    TRIP_MAX_DAYS: int = _get_int('TRIP_MAX_DAYS', 14)
    TRIP_DEFAULT_PACING: str = os.getenv('TRIP_DEFAULT_PACING', 'M')
    TRIP_PACING: Dict[str, Dict] = json.loads(os.getenv(
        'TRIP_PACING',
        json.dumps({
            'R': {'stops_per_day': 3, 'name': 'Relaxed'},
            'M': {'stops_per_day': 4, 'name': 'Moderate'},
            'P': {'stops_per_day': 6, 'name': 'Packed'},
        })
    ))
    TRIP_EXTRA_PLACES_BUFFER: int = _get_int('TRIP_EXTRA_PLACES_BUFFER', 10)

    # Email / SMTP
    SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT: int = _get_int('SMTP_PORT', 587)
    SMTP_USER: str = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL: str = os.getenv('FROM_EMAIL', os.getenv('SMTP_USER', ''))

    # --- SocketIO ---
    SOCKETIO_ENABLED: bool = _get_bool('SOCKETIO_ENABLED', True)
    SOCKETIO_PING_TIMEOUT: int = _get_int('SOCKETIO_PING_TIMEOUT', 60)
    SOCKETIO_PING_INTERVAL: int = _get_int('SOCKETIO_PING_INTERVAL', 25)
    SOCKETIO_MAX_HTTP_BUFFER_SIZE: int = _get_int('SOCKETIO_MAX_HTTP_BUFFER_SIZE', 1_000_000)

    # --- Account Lockout ---
    LOCKOUT_MAX_ATTEMPTS: int = _get_int('LOCKOUT_MAX_ATTEMPTS', 5)
    LOCKOUT_BASE_TTL: int = _get_int('LOCKOUT_BASE_TTL', 900)  # 15 minutes
    LOCKOUT_TTL_JITTER_PERCENT: float = float(os.getenv('LOCKOUT_TTL_JITTER_PERCENT', '0.10'))
    LOCKOUT_IP_MAX_ATTEMPTS: int = _get_int('LOCKOUT_IP_MAX_ATTEMPTS', 20)
    LOCKOUT_IP_TTL: int = _get_int('LOCKOUT_IP_TTL', 900)
    LOCKOUT_GLOBAL_MAX_PER_MINUTE: int = _get_int('LOCKOUT_GLOBAL_MAX_PER_MINUTE', 1000)
    LOCKOUT_GLOBAL_TTL: int = _get_int('LOCKOUT_GLOBAL_TTL', 60)
    LOCKOUT_CYCLE_WINDOW: int = _get_int('LOCKOUT_CYCLE_WINDOW', 86400)  # 24 hours
    LOCKOUT_TRUSTED_MULTIPLIER: int = _get_int('LOCKOUT_TRUSTED_MULTIPLIER', 3)

    # --- Country Mappings (Ticketmaster) ---
    COUNTRY_MAPPINGS: Dict[str, str] = json.loads(os.getenv(
        'COUNTRY_MAPPINGS',
        json.dumps({
            'japan': 'JP', 'jp': 'JP', 'france': 'FR', 'fr': 'FR',
            'uk': 'GB', 'united kingdom': 'GB', 'gb': 'GB',
            'usa': 'US', 'united states': 'US', 'us': 'US',
            'canada': 'CA', 'ca': 'CA', 'australia': 'AU', 'au': 'AU',
            'germany': 'DE', 'de': 'DE', 'italy': 'IT', 'it': 'IT',
            'spain': 'ES', 'es': 'ES',
        })
    ))

    # Rate Limiting
    RATELIMIT_ENABLED: bool = False
    RATELIMIT_DEFAULT: str = '100 per hour'
    RATELIMIT_STORAGE_URL: str = 'memory://'

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES: int = _get_int('JWT_ACCESS_TOKEN_EXPIRES', 3600)  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = _get_int('JWT_REFRESH_TOKEN_EXPIRES', 2592000)  # 30 days
    JWT_ALGORITHM: str = 'HS256'
    MAX_SESSIONS_PER_USER: int = _get_int('MAX_SESSIONS_PER_USER', 5)

    # JWT Key Rotation — sign with current version, verify with any known version
    JWT_SIGNING_KEYS: Dict[str, str] = {
        'v1': os.getenv('JWT_SECRET_KEY_V1', os.getenv('JWT_SECRET_KEY', SECRET_KEY)),
        'v2': os.getenv('JWT_SECRET_KEY_V2', ''),
    }
    JWT_CURRENT_KEY_VERSION: str = os.getenv('JWT_CURRENT_KEY_VERSION', 'v1')

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
        if not cls.ADMIN_EMAILS:
            errors.append('ADMIN_EMAILS must be set in production')
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
        'rank_score', 'place_name',
        'rating_tourist_priority', 'rating_traveler_experience',
    ]
    VALID_COST_VALUES: list = ['free', 'low', 'medium', 'high']
    VALID_RATING_VALUES: list = [1, 2, 3, 4, 5]


# Backward-compatible config instance used by place_search routes/services
config = PlaceSearchConfig()
