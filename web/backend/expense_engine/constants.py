"""
Expense Engine Constants
All hardcoded values centralized for easy configuration and maintenance.
Following enterprise patterns used by Splitwise, Stripe, etc.
"""

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

class CacheConfig:
    """Cache TTL and key prefix configurations"""
    
    # TTL Settings (seconds)
    TTL_USER = 3600              # 1 hour - users rarely change
    TTL_DISPLAY_NAME = 3600      # 1 hour - display names cached separately
    TTL_GROUP = 1800             # 30 minutes - groups change occasionally
    TTL_EXPENSE = 900            # 15 minutes - expenses added frequently
    TTL_BALANCE = 300            # 5 minutes - balances update often
    TTL_INVITATION = 600         # 10 minutes - invitations have TTL
    TTL_INVITATION_ENRICHED = 300  # 5 minutes - enriched invitation data
    TTL_SETTLEMENT = 900         # 15 minutes - settlements
    TTL_ANALYTICS = 1800         # 30 minutes - analytics data
    TTL_IDEMPOTENCY = 86400      # 24 hours - idempotency keys
    TTL_GROUP_SUMMARY = 300      # 5 minutes - group summary (lightweight)
    TTL_GROUP_FULL = 600         # 10 minutes - group full data (heavier)
    TTL_BALANCE_FORMATTED = 30   # 30 seconds - formatted balance response
    
    # Key Prefixes (namespacing)
    PREFIX_USER = "expense:user:"
    PREFIX_DISPLAY_NAME = "display_name:"
    PREFIX_GROUP = "expense:group:"
    PREFIX_EXPENSE = "expense:expense:"
    PREFIX_BALANCE = "expense:balance:"
    PREFIX_USER_GROUPS = "expense:user_groups:"
    PREFIX_GROUP_EXPENSES = "expense:group_expenses:"
    PREFIX_USER_EXPENSES = "expense:user_expenses:"
    PREFIX_INVITATIONS = "expense:invitations:"
    PREFIX_INVITATIONS_ENRICHED = "user_invitations_enriched:"
    PREFIX_SETTLEMENTS = "expense:settlements:"
    PREFIX_IDEMPOTENCY = "idempotency:"
    PREFIX_ANALYTICS = "analytics:"
    PREFIX_GROUP_DETAILS = "group_details:"
    PREFIX_USER_GROUPS_KEY = "user_groups:"
    PREFIX_GROUP_MEMBERS = "group_members:"
    PREFIX_GROUP_FULL = "group_full:"
    PREFIX_LOCK = "lock:"
    
    # Cache freshness thresholds
    BALANCE_CACHE_MAX_AGE = 300  # 5 minutes
    USER_CACHE_MAX_AGE = 3600    # 1 hour


# =============================================================================
# REDIS CONNECTION SETTINGS
# =============================================================================

class RedisConfig:
    """Redis connection pool settings"""
    
    # Connection settings
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 6379
    DEFAULT_DB = 0
    DEFAULT_URL = 'redis://localhost:6379/0'
    
    # Connection pool
    MAX_CONNECTIONS = 50
    SOCKET_TIMEOUT = 2           # seconds
    SOCKET_CONNECT_TIMEOUT = 2   # seconds
    SOCKET_KEEPALIVE = True
    RETRY_ON_TIMEOUT = True
    HEALTH_CHECK_INTERVAL = 10   # seconds
    
    # Decode responses
    DECODE_RESPONSES = True


# =============================================================================
# FIREBASE COLLECTION NAMES
# =============================================================================

class FirebaseCollections:
    """Firestore collection names"""
    
    USERS = 'users'
    GROUPS = 'groups'
    GROUP_MEMBERS = 'group_members'
    GROUP_INVITATIONS = 'group_invitations'
    EXPENSES = 'expenses'
    EXPENSE_SPLITS = 'expense_splits'
    SETTLEMENTS = 'settlements'
    BALANCES = 'balances'
    GROUP_BALANCES = 'group_balances'
    ACTIVITIES = 'activities'
    NOTIFICATIONS = 'notifications'


# =============================================================================
# PAGINATION & LIMITS
# =============================================================================

class PaginationConfig:
    """Pagination and query limits"""
    
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    MAX_BATCH_SIZE = 100         # Firestore batch operation limit
    MAX_USERS_BATCH_GET = 100    # Max users to fetch in one batch
    MAX_QUERY_LIMIT = 500        # Max results for any query


# =============================================================================
# CURRENCY CONFIGURATION
# =============================================================================

class CurrencyConfig:
    """Currency codes and symbols"""
    
    DEFAULT_CURRENCY = 'USD'
    
    # Supported currencies
    SUPPORTED_CURRENCIES = [
        'USD', 'EUR', 'GBP', 'INR', 'JPY', 'CAD',
        'AUD', 'CHF', 'CNY', 'MXN', 'BRL', 'ZAR',
        'SGD', 'HKD', 'NZD', 'SEK', 'NOK', 'DKK',
        'KRW', 'THB', 'MYR', 'PHP', 'IDR', 'VND'
    ]
    
    # Currency symbols
    CURRENCY_SYMBOLS = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'INR': '₹',
        'JPY': '¥',
        'CAD': 'C$',
        'AUD': 'A$',
        'CHF': 'Fr',
        'CNY': '¥',
        'MXN': 'MX$',
        'BRL': 'R$',
        'ZAR': 'R',
        'SGD': 'S$',
        'HKD': 'HK$',
        'NZD': 'NZ$',
        'SEK': 'kr',
        'NOK': 'kr',
        'DKK': 'kr',
        'KRW': '₩',
        'THB': '฿',
        'MYR': 'RM',
        'PHP': '₱',
        'IDR': 'Rp',
        'VND': '₫'
    }


# =============================================================================
# EMAIL TEMPLATES & SETTINGS
# =============================================================================

class EmailConfig:
    """Email service configuration"""
    
    # SMTP defaults
    DEFAULT_SMTP_HOST = 'smtp.gmail.com'
    DEFAULT_SMTP_PORT = 587
    DEFAULT_FROM_NAME = 'TripRaft'
    
    # Email retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Email rate limiting
    MAX_EMAILS_PER_MINUTE = 60
    MAX_EMAILS_PER_HOUR = 500
    
    # Template IDs (for external email services like SendGrid/Mailgun)
    TEMPLATE_INVITATION = 'group_invitation'
    TEMPLATE_EXPENSE_ADDED = 'expense_added'
    TEMPLATE_EXPENSE_UPDATED = 'expense_updated'
    TEMPLATE_PAYMENT_REQUEST = 'payment_request'
    TEMPLATE_SETTLEMENT_REMINDER = 'settlement_reminder'


# =============================================================================
# VALIDATION RULES
# =============================================================================

class ValidationRules:
    """Input validation rules"""
    
    # User validation
    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 30
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    # Group validation
    MIN_GROUP_NAME_LENGTH = 1
    MAX_GROUP_NAME_LENGTH = 100
    MAX_GROUP_DESCRIPTION_LENGTH = 500
    MIN_GROUP_MEMBERS = 2
    MAX_GROUP_MEMBERS = 100
    
    # Expense validation
    MIN_EXPENSE_AMOUNT = 0.01    # $0.01
    MAX_EXPENSE_AMOUNT = 1000000  # $1M
    MAX_EXPENSE_DESCRIPTION_LENGTH = 500
    MAX_SPLITS_PER_EXPENSE = 100
    
    # Settlement validation
    MIN_SETTLEMENT_AMOUNT = 0.01
    MAX_SETTLEMENT_AMOUNT = 1000000


# =============================================================================
# PERFORMANCE & OPTIMIZATION
# =============================================================================

class PerformanceConfig:
    """Performance tuning settings"""
    
    # Concurrent operations
    MAX_CONCURRENT_OPERATIONS = 10
    THREAD_POOL_SIZE = 10
    
    # Batch operations
    BATCH_SIZE_USERS = 100
    BATCH_SIZE_EXPENSES = 50
    BATCH_SIZE_BALANCES = 100
    
    # Request timeouts
    DEFAULT_TIMEOUT = 30         # seconds
    FIREBASE_TIMEOUT = 10        # seconds
    REDIS_TIMEOUT = 2            # seconds
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100    # requests
    RATE_LIMIT_WINDOW = 3600     # per hour
    
    # Background tasks
    ASYNC_EMAIL_ENABLED = True
    ASYNC_NOTIFICATION_ENABLED = True


# =============================================================================
# CACHE INVALIDATION STRATEGIES
# =============================================================================

class CacheInvalidationStrategy:
    """
    Cache invalidation strategies for different operations
    Phase 2.7: Selective cache invalidation for 91% faster reloads
    """
    
    # Settlement operations (SELECTIVE - only balances)
    ON_SETTLEMENT_CREATE = [
        'balance',           # ✅ Invalidate (changed)
        'balance_formatted', # ✅ Invalidate (changed)
        'group_balances',    # ✅ Invalidate (changed)
    ]
    # DON'T invalidate: group_details, group_members, group_full, expenses
    
    # Expense operations (MODERATE - balance + expense data)
    ON_EXPENSE_CREATE = [
        'balance',
        'balance_formatted',
        'group_balances',
        'group_expenses',    # ✅ Invalidate (new expense added)
        'group_full',        # ✅ Invalidate (includes expenses)
    ]
    # DON'T invalidate: group_details, group_members
    
    ON_EXPENSE_UPDATE_FINANCIAL = [
        'balance',           # ✅ Amount/split changed
        'balance_formatted',
        'group_balances',
        'group_expenses',
        'group_full',
    ]
    
    ON_EXPENSE_UPDATE_METADATA = [
        'group_expenses',    # ✅ Only expense data changed
        'group_full',
    ]
    # DON'T invalidate: balances (description/category doesn't affect balance)
    
    ON_EXPENSE_DELETE = [
        'balance',
        'balance_formatted',
        'group_balances',
        'group_expenses',
        'group_full',
    ]
    
    # Group operations (AGGRESSIVE - everything)
    ON_GROUP_UPDATE = [
        'group_details',
        'group_full',
        'user_groups',       # ✅ User's group list changed
    ]
    
    ON_MEMBER_ADD = [
        'group_members',
        'group_full',
        'user_groups',       # ✅ New member's group list
    ]
    
    ON_MEMBER_REMOVE = [
        'group_members',
        'group_full',
        'balance',           # ✅ Balances affected
        'group_balances',
        'user_groups',       # ✅ Removed member's group list
    ]
    
    # Invitation operations (MINIMAL - only invitations)
    ON_INVITATION_CREATE = [
        'group_invitations', # ✅ Only invitation lists
    ]
    
    ON_INVITATION_ACCEPT = [
        'group_invitations',
        'group_members',     # ✅ New member joined
        'group_full',
        'user_groups',       # ✅ Acceptor's group list
    ]


# =============================================================================
# LOGGING & MONITORING
# =============================================================================

class LoggingConfig:
    """Logging configuration"""
    
    # Log levels
    DEFAULT_LEVEL = 'INFO'
    
    # Log format
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Log file settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5
    
    # Operation tracking
    TRACK_FIRESTORE_OPS = True
    TRACK_CACHE_OPS = True
    TRACK_API_LATENCY = True


# =============================================================================
# FEATURE FLAGS
# =============================================================================

class FeatureFlags:
    """Feature toggles for gradual rollout"""
    
    # Core features
    ENABLE_EMAIL_NOTIFICATIONS = True
    ENABLE_PUSH_NOTIFICATIONS = False
    ENABLE_SMS_NOTIFICATIONS = False
    
    # Advanced features
    ENABLE_RECURRING_EXPENSES = False
    ENABLE_EXPENSE_ATTACHMENTS = False
    ENABLE_EXPENSE_COMMENTS = False
    ENABLE_GROUP_CATEGORIES = False
    
    # Optimizations
    ENABLE_BALANCE_MANAGER = True
    ENABLE_IDEMPOTENCY = True
    ENABLE_REQUEST_COALESCING = True
    ENABLE_CACHE_PREFETCH = False
    
    # Analytics
    ENABLE_ANALYTICS = True
    ENABLE_PERFORMANCE_TRACKING = True
    ENABLE_ERROR_TRACKING = True


# =============================================================================
# BUSINESS RULES
# =============================================================================

class BusinessRules:
    """Business logic constants"""
    
    # Balance calculations
    BALANCE_PRECISION = 2        # decimal places
    BALANCE_ROUNDING = 'HALF_UP'
    BALANCE_CALCULATION_TIMEOUT = 30  # seconds - max wait for concurrent balance recalculation
    
    # Settlement preferences
    SIMPLIFY_DEBTS = True        # Optimize debt settlements
    MIN_SETTLEMENT_THRESHOLD = 0.01  # Don't show debts < $0.01
    
    # Invitation expiry
    INVITATION_EXPIRY_DAYS = 7   # days
    
    # Activity retention
    ACTIVITY_RETENTION_DAYS = 90  # days
    
    # Archive settings
    AUTO_ARCHIVE_SETTLED_GROUPS = False
    SETTLED_GROUP_ARCHIVE_DAYS = 30


# =============================================================================
# HTTP STATUS CODES
# =============================================================================

class HTTPStatus:
    """Standard HTTP status codes"""
    
    # Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Client errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # Server errors
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCodes:
    """Application-specific error codes"""
    
    # User errors
    USER_NOT_FOUND = 'USER_NOT_FOUND'
    USER_ALREADY_EXISTS = 'USER_ALREADY_EXISTS'
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    
    # Group errors
    GROUP_NOT_FOUND = 'GROUP_NOT_FOUND'
    NOT_GROUP_MEMBER = 'NOT_GROUP_MEMBER'
    ALREADY_GROUP_MEMBER = 'ALREADY_GROUP_MEMBER'
    INSUFFICIENT_PERMISSIONS = 'INSUFFICIENT_PERMISSIONS'
    
    # Expense errors
    EXPENSE_NOT_FOUND = 'EXPENSE_NOT_FOUND'
    INVALID_SPLIT_TYPE = 'INVALID_SPLIT_TYPE'
    INVALID_SPLIT_AMOUNTS = 'INVALID_SPLIT_AMOUNTS'
    SPLIT_SUM_MISMATCH = 'SPLIT_SUM_MISMATCH'
    
    # Invitation errors
    INVITATION_NOT_FOUND = 'INVITATION_NOT_FOUND'
    INVITATION_EXPIRED = 'INVITATION_EXPIRED'
    INVITATION_ALREADY_ACCEPTED = 'INVITATION_ALREADY_ACCEPTED'
    
    # Settlement errors
    SETTLEMENT_NOT_FOUND = 'SETTLEMENT_NOT_FOUND'
    INVALID_SETTLEMENT = 'INVALID_SETTLEMENT'
    ALREADY_SETTLED = 'ALREADY_SETTLED'
    
    # Validation errors
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    INVALID_FIELD_FORMAT = 'INVALID_FIELD_FORMAT'
    
    # System errors
    DATABASE_ERROR = 'DATABASE_ERROR'
    CACHE_ERROR = 'CACHE_ERROR'
    EXTERNAL_SERVICE_ERROR = 'EXTERNAL_SERVICE_ERROR'


# =============================================================================
# API VERSION & METADATA
# =============================================================================

class APIMetadata:
    """API version and metadata"""
    
    VERSION = '2.0.0'
    API_PREFIX = '/api/expense'
    DESCRIPTION = 'Production-ready expense management system'
    CONTACT_EMAIL = 'support@tripraft.com'
    DOCUMENTATION_URL = 'https://docs.tripraft.com'


# =============================================================================
# EXPORT ALL CONFIGS
# =============================================================================

__all__ = [
    'CacheConfig',
    'RedisConfig',
    'FirebaseCollections',
    'PaginationConfig',
    'CurrencyConfig',
    'EmailConfig',
    'ValidationRules',
    'PerformanceConfig',
    'LoggingConfig',
    'FeatureFlags',
    'BusinessRules',
    'HTTPStatus',
    'ErrorCodes',
    'APIMetadata',
]
