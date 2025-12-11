"""
Business Constants for Expense Engine
Enums, status codes, and immutable business rules

No hardcoded values - only type-safe constants
"""

from enum import Enum
from typing import Dict


# ============================================================================
# Enums
# ============================================================================

class SplitType(str, Enum):
    """Expense split types"""
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    SHARES = "shares"
    EXACT = "exact"
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]


class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]


class GroupStatus(str, Enum):
    """Group lifecycle states"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    
    @classmethod
    def is_active(cls, status: str) -> bool:
        return status == cls.ACTIVE.value


class GroupRole(str, Enum):
    """Group member roles (RBAC)"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    
    @classmethod
    def has_admin_privileges(cls, role: str) -> bool:
        return role in [cls.OWNER.value, cls.ADMIN.value]


class InvitationStatus(str, Enum):
    """Invitation states"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    
    @classmethod
    def is_active(cls, status: str) -> bool:
        return status == cls.PENDING.value


class SettlementMethod(str, Enum):
    """Settlement payment methods"""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    ZELLE = "zelle"
    VENMO = "venmo"
    PAYPAL = "paypal"
    OTHER = "other"


class SettlementStatus(str, Enum):
    """Settlement status"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExpenseCategory(str, Enum):
    """Expense categories (for analytics)"""
    FOOD = "food"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    UTILITIES = "utilities"
    BILLS = "bills"
    GROCERIES = "groceries"
    HEALTHCARE = "healthcare"
    HEALTH = "health"
    SALARY = "salary"
    OTHER = "other"


class ActivityType(str, Enum):
    """Activity log types (audit trail)"""
    GROUP_CREATED = "group_created"
    GROUP_UPDATED = "group_updated"
    GROUP_DELETED = "group_deleted"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    SETTLEMENT_CREATED = "settlement_created"
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_DECLINED = "invitation_declined"


# ============================================================================
# Currency Symbols and Info
# ============================================================================

CURRENCY_SYMBOLS: Dict[Currency, str] = {
    Currency.USD: "$",
    Currency.EUR: "€",
    Currency.GBP: "£",
    Currency.INR: "₹",
    Currency.JPY: "¥",
    Currency.CAD: "C$",
    Currency.AUD: "A$",
    Currency.CHF: "CHF",
    Currency.CNY: "¥"
}

CURRENCY_NAMES: Dict[Currency, str] = {
    Currency.USD: "US Dollar",
    Currency.EUR: "Euro",
    Currency.GBP: "British Pound",
    Currency.INR: "Indian Rupee",
    Currency.JPY: "Japanese Yen",
    Currency.CAD: "Canadian Dollar",
    Currency.AUD: "Australian Dollar",
    Currency.CHF: "Swiss Franc",
    Currency.CNY: "Chinese Yuan"
}

# Currency precision (decimal places)
CURRENCY_PRECISION: Dict[Currency, int] = {
    Currency.USD: 2,
    Currency.EUR: 2,
    Currency.GBP: 2,
    Currency.INR: 2,
    Currency.JPY: 0,  # Yen has no decimal
    Currency.CAD: 2,
    Currency.AUD: 2,
    Currency.CHF: 2,
    Currency.CNY: 2
}


# ============================================================================
# HTTP Status Codes
# ============================================================================

class HTTPStatus:
    """HTTP status codes for consistency"""
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


# ============================================================================
# Error Codes (for consistent error handling)
# ============================================================================

class ErrorCode(str, Enum):
    """Application error codes"""
    # Authentication
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Validation
    INVALID_INPUT = "INVALID_INPUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    INVALID_SPLIT = "INVALID_SPLIT"
    
    # Business logic
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    EXPENSE_NOT_FOUND = "EXPENSE_NOT_FOUND"
    USER_NOT_MEMBER = "USER_NOT_MEMBER"
    MAX_MEMBERS_REACHED = "MAX_MEMBERS_REACHED"
    INVITATION_EXPIRED = "INVITATION_EXPIRED"
    
    # System
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# ============================================================================
# Permissions (for RBAC)
# ============================================================================

class Permission(str, Enum):
    """Group permissions"""
    # Group management
    DELETE_GROUP = "delete_group"
    EDIT_GROUP = "edit_group"
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    
    # Expense management
    CREATE_EXPENSE = "create_expense"
    EDIT_OWN_EXPENSE = "edit_own_expense"
    EDIT_ANY_EXPENSE = "edit_any_expense"
    DELETE_OWN_EXPENSE = "delete_own_expense"
    DELETE_ANY_EXPENSE = "delete_any_expense"
    
    # Settlement management
    CREATE_SETTLEMENT = "create_settlement"
    EDIT_SETTLEMENT = "edit_settlement"
    
    # View permissions
    VIEW_BALANCES = "view_balances"
    VIEW_EXPENSES = "view_expenses"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[GroupRole, list[Permission]] = {
    GroupRole.OWNER: [
        Permission.DELETE_GROUP,
        Permission.EDIT_GROUP,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.CREATE_EXPENSE,
        Permission.EDIT_ANY_EXPENSE,
        Permission.DELETE_ANY_EXPENSE,
        Permission.CREATE_SETTLEMENT,
        Permission.EDIT_SETTLEMENT,
        Permission.VIEW_BALANCES,
        Permission.VIEW_EXPENSES
    ],
    GroupRole.ADMIN: [
        Permission.EDIT_GROUP,
        Permission.INVITE_MEMBERS,
        Permission.CREATE_EXPENSE,
        Permission.EDIT_ANY_EXPENSE,
        Permission.DELETE_OWN_EXPENSE,
        Permission.CREATE_SETTLEMENT,
        Permission.VIEW_BALANCES,
        Permission.VIEW_EXPENSES
    ],
    GroupRole.MEMBER: [
        Permission.CREATE_EXPENSE,
        Permission.EDIT_OWN_EXPENSE,
        Permission.DELETE_OWN_EXPENSE,
        Permission.CREATE_SETTLEMENT,
        Permission.VIEW_BALANCES,
        Permission.VIEW_EXPENSES
    ]
}


# ============================================================================
# Default Values
# ============================================================================

class Defaults:
    """Default values for entities"""
    GROUP_CURRENCY = Currency.USD
    GROUP_ROLE = GroupRole.MEMBER
    SPLIT_TYPE = SplitType.EQUAL
    EXPENSE_CATEGORY = ExpenseCategory.OTHER
    SETTLEMENT_METHOD = SettlementMethod.CASH
    PAGE_SIZE = 20


# ============================================================================
# Validation Patterns
# ============================================================================

# Email regex (basic)
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Group ID pattern (alphanumeric + hyphens)
GROUP_ID_PATTERN = r'^[a-zA-Z0-9_-]{10,50}$'

# User ID pattern (Firebase UID format)
USER_ID_PATTERN = r'^[a-zA-Z0-9]{10,128}$'


# ============================================================================
# Helper Functions
# ============================================================================

def get_currency_symbol(currency: Currency) -> str:
    """Get currency symbol"""
    return CURRENCY_SYMBOLS.get(currency, currency.value)


def get_currency_precision(currency: Currency) -> int:
    """Get decimal precision for currency"""
    return CURRENCY_PRECISION.get(currency, 2)


def check_permission(role: GroupRole, permission: Permission) -> bool:
    """Check if role has permission"""
    return permission in ROLE_PERMISSIONS.get(role, [])
