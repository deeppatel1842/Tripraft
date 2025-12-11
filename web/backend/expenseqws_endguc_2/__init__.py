"""
Expense Engine Module
Complete expense management system with Firebase and Redis
Supports multiple currencies: USD, EUR, INR, GBP, JPY, CAD, AUD, CHF, CNY
"""

# Core models
from .models import (
    User, Group, GroupMember, GroupInvitation,
    Expense, ExpenseSplit, Settlement, Balance
)

# Enums (extracted from models for better organization)
from .enums import (
    SplitType, ExpenseCategory, InvitationStatus, SettlementStatus,
    Currency, GroupRole, ActivityType, NotificationType
)

# Constants and configuration
from .constants import (
    CacheConfig, RedisConfig, FirebaseCollections, PaginationConfig,
    CurrencyConfig, EmailConfig, ValidationRules, PerformanceConfig,
    LoggingConfig, FeatureFlags, BusinessRules, HTTPStatus, ErrorCodes,
    APIMetadata
)

# Messages
from .messages import (
    SuccessMessages, ErrorMessages, EmailTemplates, ValidationMessages
)

# Database Operations
from .firebase_operations import ExpenseDatabaseOperations
from .cache_operations import ExpenseCacheOperations

# Services
from .service import ExpenseService, expense_service
from .email_service import EmailService, email_service

# Workers
from .workers import EmailWorker, get_email_worker

# Routes
from .routes import expense_bp

__all__ = [
    # Models
    'User', 'Group', 'GroupMember', 'GroupInvitation',
    'Expense', 'ExpenseSplit', 'Settlement', 'Balance',
    
    # Enums
    'SplitType', 'ExpenseCategory', 'InvitationStatus', 'SettlementStatus',
    'Currency', 'GroupRole', 'ActivityType', 'NotificationType',
    
    # Constants & Configuration
    'CacheConfig', 'RedisConfig', 'FirebaseCollections', 'PaginationConfig',
    'CurrencyConfig', 'EmailConfig', 'ValidationRules', 'PerformanceConfig',
    'LoggingConfig', 'FeatureFlags', 'BusinessRules', 'HTTPStatus', 'ErrorCodes',
    'APIMetadata',
    
    # Messages
    'SuccessMessages', 'ErrorMessages', 'EmailTemplates', 'ValidationMessages',
    
    # Database Operations
    'ExpenseDatabaseOperations', 'ExpenseCacheOperations',
    
    # Services
    'ExpenseService', 'expense_service',
    'EmailService', 'email_service',
    
    # Workers
    'EmailWorker', 'get_email_worker',
    
    # Routes
    'expense_bp'
]

__version__ = '2.0.0'
__description__ = 'Production-ready expense management system with multi-currency support'
