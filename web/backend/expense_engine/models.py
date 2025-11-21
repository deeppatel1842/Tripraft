"""
Expense Engine - Models
Data models for expense management system
Supports multiple currencies (USD, EUR, INR, GBP, etc.)
"""

from datetime import datetime
from typing import List, Dict, Optional
from .enums import SplitType, ExpenseCategory, InvitationStatus, SettlementStatus, Currency as CurrencyEnum
from .constants import CurrencyConfig


class Currency:
    """Currency helper class for backward compatibility"""
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
    def get_symbol(cls, currency_code: str) -> str:
        """Get currency symbol from constants"""
        return CurrencyConfig.CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)
    
    @classmethod
    def is_valid(cls, currency_code: str) -> bool:
        """Check if currency code is valid using constants"""
        return currency_code.upper() in CurrencyConfig.SUPPORTED_CURRENCIES


class User:
    """User model"""
    def __init__(self, uid: str, email: str, username: str, 
                 display_name: Optional[str] = None,
                 profile_picture: Optional[str] = None,
                 default_currency: str = "USD",
                 created_at: Optional[datetime] = None):
        self.uid = uid
        self.email = email
        self.username = username
        self.display_name = display_name or username
        self.profile_picture = profile_picture
        self.default_currency = default_currency
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'uid': self.uid,
            'email': self.email,
            'username': self.username,
            'display_name': self.display_name,
            'profile_picture': self.profile_picture,
            'default_currency': self.default_currency,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }


class Group:
    """Group model for managing shared expenses"""
    def __init__(self, group_id: str, name: str, created_by: str,
                 description: Optional[str] = None,
                 image_url: Optional[str] = None,
                 currency: str = "USD",
                 created_at: Optional[datetime] = None):
        self.group_id = group_id
        self.name = name
        self.description = description
        self.created_by = created_by
        self.image_url = image_url
        self.currency = currency.upper()
        self.members = []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.is_active = True
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.group_id,  # Add 'id' as alias for frontend compatibility
            'group_id': self.group_id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'image_url': self.image_url,
            'currency': self.currency,
            'members': self.members,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'is_active': self.is_active
        }


class GroupMember:
    """Group membership details"""
    def __init__(self, group_id: str, user_id: str, role: str = "member",
                 joined_at: Optional[datetime] = None):
        self.group_id = group_id
        self.user_id = user_id
        self.role = role
        self.joined_at = joined_at or datetime.utcnow()
        self.is_active = True
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if isinstance(self.joined_at, datetime) else self.joined_at,
            'is_active': self.is_active
        }


class GroupInvitation:
    """Group invitation model"""
    def __init__(self, invitation_id: str, group_id: str, 
                 invited_by: str, invited_user: Optional[str] = None,
                 invited_email: Optional[str] = None,
                 invited_username: Optional[str] = None,
                 status: InvitationStatus = InvitationStatus.PENDING,
                 created_at: Optional[datetime] = None,
                 expires_at: Optional[datetime] = None):
        self.invitation_id = invitation_id
        self.group_id = group_id
        self.invited_by = invited_by
        self.invited_user = invited_user
        self.invited_email = invited_email
        self.invited_username = invited_username
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at
        self.responded_at = None
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'invitation_id': self.invitation_id,
            'group_id': self.group_id,
            'invited_by': self.invited_by,
            'invited_user': self.invited_user,
            'invited_email': self.invited_email,
            'invited_username': self.invited_username,
            'status': self.status.value if isinstance(self.status, InvitationStatus) else self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'expires_at': self.expires_at.isoformat() if isinstance(self.expires_at, datetime) and self.expires_at else self.expires_at,
            'responded_at': self.responded_at.isoformat() if isinstance(self.responded_at, datetime) and self.responded_at else self.responded_at
        }


class Expense:
    """Expense model - supports both personal and group expenses with multi-currency"""
    def __init__(self, expense_id: str, description: str, amount: float,
                 paid_by: str, category: ExpenseCategory,
                 group_id: Optional[str] = None,
                 split_type: SplitType = SplitType.EQUAL,
                 currency: str = "USD",
                 date: Optional[datetime] = None,
                 notes: Optional[str] = None,
                 image_url: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.expense_id = expense_id
        self.description = description
        self.amount = amount
        self.paid_by = paid_by
        self.group_id = group_id
        self.category = category
        self.split_type = split_type
        self.currency = currency.upper()
        self.date = date or datetime.utcnow()
        self.notes = notes
        self.image_url = image_url
        self.splits = []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.is_deleted = False
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.expense_id,  # Add 'id' as alias for frontend compatibility
            'expense_id': self.expense_id,
            'type': 'expense',  # Add type field for frontend filtering
            'description': self.description,
            'amount': self.amount,
            'paid_by': self.paid_by,
            'group_id': self.group_id,
            'category': self.category.value if isinstance(self.category, ExpenseCategory) else self.category,
            'split_type': self.split_type.value if isinstance(self.split_type, SplitType) else self.split_type,
            'currency': self.currency,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            'notes': self.notes,
            'image_url': self.image_url,
            'splits': [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.splits],
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'is_deleted': self.is_deleted
        }


class ExpenseSplit:
    """Individual split for an expense"""
    def __init__(self, expense_id: str, user_id: str, amount: float,
                 share: Optional[float] = None,
                 percentage: Optional[float] = None):
        self.expense_id = expense_id
        self.user_id = user_id
        self.amount = amount
        self.share = share
        self.percentage = percentage
        self.is_settled = False
        self.settled_at = None
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'expense_id': self.expense_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'share': self.share,
            'percentage': self.percentage,
            'is_settled': self.is_settled,
            'settled_at': self.settled_at.isoformat() if isinstance(self.settled_at, datetime) and self.settled_at else self.settled_at
        }


class Settlement:
    """Settlement/Payment between users with multi-currency support"""
    def __init__(self, settlement_id: str, from_user: str, to_user: str,
                 amount: float, group_id: Optional[str] = None,
                 currency: str = "USD",
                 notes: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.settlement_id = settlement_id
        self.from_user = from_user
        self.to_user = to_user
        self.amount = amount
        self.group_id = group_id
        self.currency = currency.upper()
        self.notes = notes
        self.status = SettlementStatus.COMPLETED
        self.created_at = created_at or datetime.utcnow()
        self.completed_at = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'settlement_id': self.settlement_id,
            'type': 'settlement',  # Add type field for frontend filtering
            'from_user': self.from_user,
            'to_user': self.to_user,
            'amount': self.amount,
            'group_id': self.group_id,
            'currency': self.currency,
            'notes': self.notes,
            'status': self.status.value if isinstance(self.status, SettlementStatus) else self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'completed_at': self.completed_at.isoformat() if isinstance(self.completed_at, datetime) and self.completed_at else self.completed_at
        }


class Balance:
    """User balance in a group or overall with currency support"""
    def __init__(self, user_id: str, group_id: Optional[str] = None, currency: str = "USD"):
        self.user_id = user_id
        self.group_id = group_id
        self.total_owed = 0.0
        self.total_lent = 0.0
        self.net_balance = 0.0
        self.currency = currency.upper()
        self.updated_at = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'group_id': self.group_id,
            'total_owed': round(self.total_owed, 2),
            'total_lent': round(self.total_lent, 2),
            'net_balance': round(self.net_balance, 2),
            'currency': self.currency,
            'currency_symbol': Currency.get_symbol(self.currency),
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
