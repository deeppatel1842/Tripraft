"""
Expense Engine Configuration
All values loaded from environment variables or global config
ZERO hardcoded values in business logic

Security: All sensitive values from environment variables
Scalability: Configured for 1000+ concurrent users
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Add backend root to Python path
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Import global backend config
from config import Config as GlobalConfig


@dataclass
class FirestoreCollections:
    """
    Firestore collection names - NO CONFLICTS with Group Planner
    
    Group Planner uses:
    - travel_groups, group_members, group_invitations, travel_places, travel_polls
    
    Expense Engine uses (all prefixed with expense_):
    - expense_groups, expense_group_members, expense_invitations, etc.
    
    DENORMALIZED COLLECTIONS (Key Optimization):
    - expense_group_balances: Pre-computed balances per group
    - expense_group_summaries: Per-user summary (groups, total owed/owing)
    - expense_user_expenses: User expense index for fast lookups
    - user_emails: Email -> userId lookup (Phase 19.2)
    """
    USERS: str = "users"  # Shared collection (read-only for most operations)
    
    # Core Expense Engine collections (all have expense_ prefix)
    GROUPS: str = "expense_groups"
    GROUP_MEMBERS: str = "expense_group_members"
    EXPENSES: str = "expense_expenses"
    SETTLEMENTS: str = "expense_settlements"
    INVITATIONS: str = "expense_invitations"
    ACTIVITIES: str = "expense_activities"  # Audit log
    
    # DENORMALIZED COLLECTIONS (Performance Optimization)
    GROUP_BALANCES: str = "expense_group_balances"     # Pre-computed balances per group
    BALANCES: str = "expense_group_balances"           # Alias for GROUP_BALANCES
    GROUP_SUMMARIES: str = "expense_group_summaries"   # Per-user group stats
    USER_EXPENSES: str = "expense_user_expenses"       # User expense index
    
    # AUDIT TRAIL (Phase 12)
    EXPENSE_HISTORY: str = "expense_history"           # Edit history for expenses
    
    # Phase 19.2: Email lookup collection (direct email -> userId mapping)
    USER_EMAILS: str = "user_emails"                   # Email -> userId lookup
    
    # Phase 20: Bootstrap snapshots (pre-computed view documents)
    BOOTSTRAP_SNAPSHOTS: str = "expense_bootstrap_snapshots"  # Pre-computed bootstrap data
    
    # Phase 20: User dashboards (single-document pattern)
    USER_DASHBOARDS: str = "expense_user_dashboards"   # All user data in one document


@dataclass
class RedisConfig:
    """Redis configuration"""
    HOST: str = os.getenv("REDIS_HOST", "localhost")
    PORT: int = int(os.getenv("REDIS_PORT", 6379))
    DB: int = int(os.getenv("REDIS_DB", 0))
    PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))
    SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", 5))
    
    # Cache TTLs (seconds) - Phase 19.1: Extended TTLs for stable data
    # Goal: Reduce Firestore reads by caching longer, cache is invalidated on writes
    TTL_USER_GROUPS: int = 600  # User's groups list (10 min) - groups rarely change
    TTL_GROUP_SUMMARY: int = 600  # Group summary (10 min) - includes balances
    TTL_GROUP_EXPENSES: int = 300  # Paginated expenses (5 min) - changes on expense ops
    TTL_EXPENSE: int = 600  # Individual expense cache (10 min) - stable after creation
    TTL_USER_INVITES: int = 180  # User invitations (3 min) - need fresher data
    TTL_GROUP_INVITES: int = 180  # Group invitations (3 min) - need fresher data
    TTL_GROUP_SETTLEMENTS: int = 600  # Group settlements (10 min) - rarely change
    TTL_BALANCE: int = 600  # Balance calculations (10 min) - updated via write-through
    TTL_BOOTSTRAP: int = 600  # Bootstrap data (10 min) - mega-bootstrap cache
    TTL_EXPENSE_HISTORY: int = 300  # Expense history (5 min) - rarely changes after view
    TTL_DASHBOARD: int = 3600  # Phase 20: User dashboard (1 hour) - invalidated on writes
    
    # Cache key patterns (all prefixed with expense: for namespace isolation)
    KEY_USER_GROUPS: str = "expense:user_groups:{uid}"
    KEY_GROUP_SUMMARY: str = "expense:group_summary:{gid}"
    KEY_GROUP_EXPENSES: str = "expense:group_expenses:{gid}:p:{page}"
    KEY_EXPENSE: str = "expense:expense:{eid}"  # Individual expense cache
    KEY_USER_INVITES: str = "expense:user_invites:{email}"
    KEY_GROUP_INVITES: str = "expense:group_invites:{gid}"
    KEY_GROUP_SETTLEMENTS: str = "expense:group_settlements:{gid}"
    KEY_GROUP_BALANCES: str = "expense:group_balances:{gid}"
    KEY_EXPENSE_HISTORY: str = "expense:expense_history:{eid}"  # Phase 19.1: Expense edit history
    KEY_BOOTSTRAP_SNAPSHOT: str = "expense:bootstrap_snapshot:{uid}:{gid}"  # Phase 20: Snapshot cache
    KEY_DASHBOARD: str = "expense:dashboard:{uid}"  # Phase 20: User dashboard cache
    
    @property
    def url(self) -> str:
        """Get Redis URL"""
        if self.PASSWORD:
            return f"redis://:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"


@dataclass
class PaginationConfig:
    """Pagination settings"""
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    MIN_PAGE_SIZE: int = 5
    
    # Initial load optimization
    INITIAL_EXPENSE_LOAD: int = 5  # Show only 5 recent expenses initially
    EXPENSE_PAGE_SIZE: int = 20  # Load 20 more on scroll


@dataclass
class RateLimitConfig:
    """Rate limiting for 1000+ concurrent users"""
    # Per-user rate limits (requests per minute)
    READS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_READS", 60))  # 1 read/second
    WRITES_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_WRITES", 30))  # 1 write/2 seconds
    
    # Global rate limits
    GLOBAL_READS_PER_SECOND: int = int(os.getenv("RATE_LIMIT_GLOBAL_READS", 10000))  # For 1000+ users
    GLOBAL_WRITES_PER_SECOND: int = int(os.getenv("RATE_LIMIT_GLOBAL_WRITES", 5000))
    
    # Rate limit window
    WINDOW_SECONDS: int = 60


@dataclass
class BusinessRules:
    """Business rules and constraints"""
    MAX_GROUP_MEMBERS: int = int(os.getenv("MAX_GROUP_MEMBERS", 50))
    MAX_EXPENSE_AMOUNT: float = float(os.getenv("MAX_EXPENSE_AMOUNT", 1000000.0))  # $1M
    MIN_EXPENSE_AMOUNT: float = float(os.getenv("MIN_EXPENSE_AMOUNT", 0.01))  # 1 cent
    MAX_DESCRIPTION_LENGTH: int = int(os.getenv("MAX_DESCRIPTION_LENGTH", 500))
    MAX_GROUP_NAME_LENGTH: int = int(os.getenv("MAX_GROUP_NAME_LENGTH", 100))
    
    # Balance calculation thresholds
    BALANCE_PRECISION: int = 2  # Decimal places
    SETTLEMENT_TOLERANCE: float = 0.01  # $0.01 tolerance for "settled"
    
    # Invitation settings
    INVITATION_EXPIRY_DAYS: int = int(os.getenv("INVITATION_EXPIRY_DAYS", 7))


@dataclass
class CacheStrategy:
    """Cache invalidation strategy"""
    # Invalidate cache on these events
    INVALIDATE_ON_GROUP_CREATE: bool = True
    INVALIDATE_ON_EXPENSE_WRITE: bool = True
    INVALIDATE_ON_SETTLEMENT: bool = True
    INVALIDATE_ON_MEMBER_CHANGE: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""
    # JWT settings
    JWT_ALGORITHM: str = "RS256"
    JWT_CLOCK_SKEW_SECONDS: int = int(os.getenv("JWT_CLOCK_SKEW", 60))
    
    # Session settings
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", 3600))  # 1 hour
    TOKEN_EXPIRY_BUFFER: int = int(os.getenv("TOKEN_EXPIRY_BUFFER", 300))  # 5 minutes
    
    def __post_init__(self):
        # CORS settings (from global config or env)
        self.ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_PERFORMANCE_LOGGING: bool = os.getenv("ENABLE_PERF_LOGGING", "True").lower() == "true"
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "True").lower() == "true"
    
    # Performance targets (for monitoring alerts)
    TARGET_CACHE_HIT_RATE: float = 0.90  # 90%
    TARGET_API_LATENCY_P95: int = 200  # 200ms
    TARGET_BALANCE_READ_LATENCY: int = 50  # 50ms


# Export singleton instances
firestore_collections = FirestoreCollections()
redis_config = RedisConfig()
pagination_config = PaginationConfig()
rate_limit_config = RateLimitConfig()
business_rules = BusinessRules()
cache_strategy = CacheStrategy()
security_config = SecurityConfig()
monitoring_config = MonitoringConfig()


# ============================================================================
# Global Config Access (for Flask integration)
# ============================================================================

class ExpenseEngineConfig:
    """
    Unified config class for Flask integration
    Combines all config sections
    """
    
    # Firebase (from global config)
    FIREBASE_PROJECT_ID = GlobalConfig.FIREBASE_PROJECT_ID if GlobalConfig else os.getenv("FIREBASE_PROJECT_ID")
    FIREBASE_PRIVATE_KEY = GlobalConfig.FIREBASE_PRIVATE_KEY if GlobalConfig else os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n')
    FIREBASE_CLIENT_EMAIL = GlobalConfig.FIREBASE_CLIENT_EMAIL if GlobalConfig else os.getenv("FIREBASE_CLIENT_EMAIL")
    
    # Redis
    REDIS_URL = redis_config.url
    REDIS_MAX_CONNECTIONS = redis_config.MAX_CONNECTIONS
    
    # Collections
    COLLECTIONS = firestore_collections
    
    # Business rules
    BUSINESS_RULES = business_rules
    
    # Rate limiting
    RATE_LIMITS = rate_limit_config
    
    # Security
    SECURITY = security_config
    
    # Monitoring
    MONITORING = monitoring_config
    
    # Cache
    CACHE_STRATEGY = cache_strategy
    CACHE_CONFIG = redis_config
    
    # Pagination
    PAGINATION = pagination_config
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        # Check Firebase config
        if not cls.FIREBASE_PROJECT_ID:
            errors.append("FIREBASE_PROJECT_ID not configured")
        
        # Check Redis config
        if not redis_config.HOST:
            errors.append("REDIS_HOST not configured")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


# Export main config instance
config = ExpenseEngineConfig()

# Validate on import
try:
    ExpenseEngineConfig.validate()
except ValueError as e:
    import logging
    logging.warning(f"Configuration validation failed: {e}")
