"""
Expense Engine Enums
All enumeration types for type-safe operations.
Extracted from models.py for better organization.
"""

from enum import Enum


class SplitType(Enum):
    """Types of expense splitting"""
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"
    SHARES = "shares"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid"""
        return value in cls.values()


class ExpenseCategory(Enum):
    """Expense categories"""
    FOOD = "food"
    TRANSPORT = "transport"
    BILLS = "bills"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTH = "health"
    SALARY = "salary"
    ACCOMMODATION = "accommodation"
    GROCERIES = "groceries"
    UTILITIES = "utilities"
    OTHER = "other"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid"""
        return value in cls.values()
    
    @classmethod
    def get_display_name(cls, value: str) -> str:
        """Get user-friendly display name"""
        display_names = {
            'food': 'Food & Dining',
            'transport': 'Transportation',
            'bills': 'Bills & Utilities',
            'entertainment': 'Entertainment',
            'shopping': 'Shopping',
            'health': 'Health & Medical',
            'salary': 'Salary & Income',
            'accommodation': 'Accommodation',
            'groceries': 'Groceries',
            'utilities': 'Utilities',
            'other': 'Other'
        }
        return display_names.get(value, value.capitalize())


class InvitationStatus(Enum):
    """Group invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid"""
        return value in cls.values()


class SettlementStatus(Enum):
    """Settlement status"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid"""
        return value in cls.values()


class GroupRole(Enum):
    """Group member roles"""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid"""
        return value in cls.values()


class ActivityType(Enum):
    """Activity/audit log types"""
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    GROUP_CREATED = "group_created"
    GROUP_UPDATED = "group_updated"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    SETTLEMENT_CREATED = "settlement_created"
    SETTLEMENT_COMPLETED = "settlement_completed"
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]


class NotificationType(Enum):
    """Notification types"""
    EXPENSE_ADDED = "expense_added"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    PAYMENT_REQUEST = "payment_request"
    PAYMENT_RECEIVED = "payment_received"
    GROUP_INVITATION = "group_invitation"
    SETTLEMENT_REMINDER = "settlement_reminder"
    
    @classmethod
    def values(cls):
        """Get list of all values"""
        return [e.value for e in cls]


class Currency(Enum):
    """Supported currencies"""
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    INR = "INR"  # Indian Rupee
    JPY = "JPY"  # Japanese Yen
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan
    MXN = "MXN"  # Mexican Peso
    BRL = "BRL"  # Brazilian Real
    ZAR = "ZAR"  # South African Rand
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar
    NZD = "NZD"  # New Zealand Dollar
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    KRW = "KRW"  # South Korean Won
    THB = "THB"  # Thai Baht
    MYR = "MYR"  # Malaysian Ringgit
    PHP = "PHP"  # Philippine Peso
    IDR = "IDR"  # Indonesian Rupiah
    VND = "VND"  # Vietnamese Dong
    
    @classmethod
    def values(cls):
        """Get list of all currency codes"""
        return [e.value for e in cls]
    
    @classmethod
    def is_valid(cls, code: str) -> bool:
        """Check if currency code is valid"""
        return code.upper() in cls.values()


# Export all enums
__all__ = [
    'SplitType',
    'ExpenseCategory',
    'InvitationStatus',
    'SettlementStatus',
    'GroupRole',
    'ActivityType',
    'NotificationType',
    'Currency',
]
