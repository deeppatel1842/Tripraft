"""
Group Planner Constants
Professional configuration with environment variable support
No hardcoded values - everything configurable via .env
"""
import os
from pathlib import Path

class GroupPlannerConfig:
    """Main configuration for Group Planner"""
    
    # Authentication
    AUTH_CLOCK_SKEW_SECONDS = int(os.getenv('GP_AUTH_CLOCK_SKEW', '60'))
    SESSION_TIMEOUT = int(os.getenv('GP_SESSION_TIMEOUT', '3600'))
    TOKEN_EXPIRY_BUFFER = int(os.getenv('GP_TOKEN_EXPIRY_BUFFER', '300'))
    
    # Cache Configuration (seconds)
    CACHE_TTL_GROUPS = int(os.getenv('GP_CACHE_TTL_GROUPS', '300'))
    CACHE_TTL_MEMBERS = int(os.getenv('GP_CACHE_TTL_MEMBERS', '600'))
    CACHE_TTL_PLACES = int(os.getenv('GP_CACHE_TTL_PLACES', '900'))
    CACHE_TTL_POLLS = int(os.getenv('GP_CACHE_TTL_POLLS', '600'))
    CACHE_TTL_INVITATIONS = int(os.getenv('GP_CACHE_TTL_INVITATIONS', '300'))
    CACHE_TTL_ITINERARY = int(os.getenv('GP_CACHE_TTL_ITINERARY', '600'))
    
    # Performance
    MAX_CONCURRENT_REQUESTS = int(os.getenv('GP_MAX_CONCURRENT_REQUESTS', '50'))
    REQUEST_TIMEOUT = int(os.getenv('GP_REQUEST_TIMEOUT', '30'))
    DB_QUERY_TIMEOUT = int(os.getenv('GP_DB_QUERY_TIMEOUT', '10'))
    
    # Debug & Logging
    DEBUG_LOGGING = os.getenv('GP_DEBUG_LOGGING', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('GP_LOG_LEVEL', 'INFO')
    ENABLE_PERFORMANCE_LOGGING = os.getenv('GP_ENABLE_PERF_LOGGING', 'False').lower() == 'true'
    
    # Business Rules
    MAX_MEMBERS_PER_GROUP = int(os.getenv('GP_MAX_MEMBERS', '50'))
    MAX_PLACES_PER_GROUP = int(os.getenv('GP_MAX_PLACES', '100'))
    MAX_POLLS_PER_GROUP = int(os.getenv('GP_MAX_POLLS', '50'))
    MAX_CHECKLIST_ITEMS = int(os.getenv('GP_MAX_CHECKLIST_ITEMS', '100'))
    
    # Email Configuration
    EMAIL_ENABLED = os.getenv('GP_EMAIL_ENABLED', 'True').lower() == 'true'
    EMAIL_TIMEOUT = float(os.getenv('GP_EMAIL_TIMEOUT', '5.0'))
    EMAIL_RETRY_ATTEMPTS = int(os.getenv('GP_EMAIL_RETRY_ATTEMPTS', '3'))
    
    # Invitation Settings
    INVITATION_EXPIRY_DAYS = int(os.getenv('GP_INVITATION_EXPIRY_DAYS', '7'))
    MAX_PENDING_INVITATIONS = int(os.getenv('GP_MAX_PENDING_INVITATIONS', '10'))


class HTTPStatus:
    """HTTP status codes"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ErrorCodes:
    """Application error codes"""
    # Group errors
    GROUP_NOT_FOUND = 'GROUP_NOT_FOUND'
    GROUP_ALREADY_EXISTS = 'GROUP_ALREADY_EXISTS'
    GROUP_CREATION_FAILED = 'GROUP_CREATION_FAILED'
    
    # Member errors
    MEMBER_NOT_FOUND = 'MEMBER_NOT_FOUND'
    MEMBER_ALREADY_EXISTS = 'MEMBER_ALREADY_EXISTS'
    MAX_MEMBERS_REACHED = 'MAX_MEMBERS_REACHED'
    
    # Invitation errors
    INVITATION_NOT_FOUND = 'INVITATION_NOT_FOUND'
    INVITATION_EXPIRED = 'INVITATION_EXPIRED'
    INVITATION_ALREADY_ACCEPTED = 'INVITATION_ALREADY_ACCEPTED'
    INVITATION_ALREADY_DECLINED = 'INVITATION_ALREADY_DECLINED'
    
    # Authentication errors
    INVALID_TOKEN = 'INVALID_TOKEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    UNAUTHORIZED = 'UNAUTHORIZED'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    
    # Validation errors
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    INVALID_INPUT = 'INVALID_INPUT'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    
    # Integration errors
    LINK_EXPENSE_ERROR = 'LINK_EXPENSE_ERROR'
    EXPENSE_GROUP_NOT_FOUND = 'EXPENSE_GROUP_NOT_FOUND'
    
    # Database errors
    DATABASE_ERROR = 'DATABASE_ERROR'
    CACHE_ERROR = 'CACHE_ERROR'
    
    # Generic errors
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'


class ErrorMessages:
    """User-friendly error messages"""
    GROUP_NOT_FOUND = "Group not found"
    MEMBER_NOT_FOUND = "Member not found"
    INVITATION_NOT_FOUND = "Invitation not found"
    INVITATION_EXPIRED = "This invitation has expired"
    UNAUTHORIZED = "You are not authorized to perform this action"
    PERMISSION_DENIED = "You don't have permission to access this resource"
    VALIDATION_ERROR = "Invalid input provided"
    INTERNAL_ERROR = "An unexpected error occurred. Please try again."
    SERVICE_UNAVAILABLE = "Service temporarily unavailable. Please try again later."


class ValidationRules:
    """Input validation rules"""
    # Group validation
    MIN_GROUP_NAME_LENGTH = 3
    MAX_GROUP_NAME_LENGTH = 100
    MIN_DESTINATION_LENGTH = 2
    MAX_DESTINATION_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 500
    
    # Member validation
    MIN_USERNAME_LENGTH = 2
    MAX_USERNAME_LENGTH = 50
    
    # Place validation
    MIN_PLACE_NAME_LENGTH = 2
    MAX_PLACE_NAME_LENGTH = 200
    
    # Poll validation
    MIN_POLL_QUESTION_LENGTH = 5
    MAX_POLL_QUESTION_LENGTH = 300
    MIN_POLL_OPTIONS = 2
    MAX_POLL_OPTIONS = 10
    
    # Checklist validation
    MIN_CHECKLIST_ITEM_LENGTH = 2
    MAX_CHECKLIST_ITEM_LENGTH = 200
    
    # Budget validation
    MIN_BUDGET = 0
    MAX_BUDGET = 1000000  # $1 million


class CacheKeys:
    """Cache key templates"""
    USER_GROUPS = "gp:user:{user_id}:groups"
    GROUP_DETAILS = "gp:group:{group_id}"
    GROUP_MEMBERS = "gp:group:{group_id}:members"
    GROUP_PLACES = "gp:group:{group_id}:places"
    GROUP_POLLS = "gp:group:{group_id}:polls"
    USER_INVITATIONS = "gp:user:{user_id}:invitations"
    GROUP_ITINERARY = "gp:group:{group_id}:itinerary"


class FeatureFlags:
    """Feature toggle flags"""
    ENABLE_EMAIL_NOTIFICATIONS = os.getenv('GP_ENABLE_EMAIL', 'True').lower() == 'true'
    ENABLE_CACHE_WARMING = os.getenv('GP_ENABLE_CACHE_WARMING', 'False').lower() == 'true'
    ENABLE_AUTO_MEMBER_SYNC = os.getenv('GP_ENABLE_AUTO_MEMBER_SYNC', 'False').lower() == 'true'
    ENABLE_EXPENSE_INTEGRATION = os.getenv('GP_ENABLE_EXPENSE_INTEGRATION', 'True').lower() == 'true'
    ENABLE_REAL_TIME_UPDATES = os.getenv('GP_ENABLE_REAL_TIME_UPDATES', 'False').lower() == 'true'
