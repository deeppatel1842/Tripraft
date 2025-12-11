"""
Input Validators
Centralized validation logic for expense engine.
Follows DRY principles and makes validation reusable.
"""

import re
from typing import Dict, List, Optional, Tuple
from .constants import ValidationRules, CurrencyConfig
from .enums import SplitType, ExpenseCategory, Currency
from .messages import ValidationMessages


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class UserValidator:
    """User input validation"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, Optional[str]]:
        """Validate username"""
        if not username:
            return False, ValidationMessages.required_field("username")
        
        if len(username) < ValidationRules.MIN_USERNAME_LENGTH:
            return False, ValidationMessages.min_length(
                "username", ValidationRules.MIN_USERNAME_LENGTH
            )
        
        if len(username) > ValidationRules.MAX_USERNAME_LENGTH:
            return False, ValidationMessages.max_length(
                "username", ValidationRules.MAX_USERNAME_LENGTH
            )
        
        # Username pattern: alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        if not email:
            return False, ValidationMessages.required_field("email")
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """Validate password strength"""
        if not password:
            return False, ValidationMessages.required_field("password")
        
        if len(password) < ValidationRules.MIN_PASSWORD_LENGTH:
            return False, ValidationMessages.min_length(
                "password", ValidationRules.MIN_PASSWORD_LENGTH
            )
        
        if len(password) > ValidationRules.MAX_PASSWORD_LENGTH:
            return False, ValidationMessages.max_length(
                "password", ValidationRules.MAX_PASSWORD_LENGTH
            )
        
        # Check password strength
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and numbers"
        
        return True, None


class GroupValidator:
    """Group input validation"""
    
    @staticmethod
    def validate_group_name(name: str) -> Tuple[bool, Optional[str]]:
        """Validate group name"""
        if not name or not name.strip():
            return False, ValidationMessages.required_field("group name")
        
        if len(name) < ValidationRules.MIN_GROUP_NAME_LENGTH:
            return False, ValidationMessages.min_length(
                "group name", ValidationRules.MIN_GROUP_NAME_LENGTH
            )
        
        if len(name) > ValidationRules.MAX_GROUP_NAME_LENGTH:
            return False, ValidationMessages.max_length(
                "group name", ValidationRules.MAX_GROUP_NAME_LENGTH
            )
        
        return True, None
    
    @staticmethod
    def validate_group_description(description: str) -> Tuple[bool, Optional[str]]:
        """Validate group description"""
        if description and len(description) > ValidationRules.MAX_GROUP_DESCRIPTION_LENGTH:
            return False, ValidationMessages.max_length(
                "description", ValidationRules.MAX_GROUP_DESCRIPTION_LENGTH
            )
        
        return True, None
    
    @staticmethod
    def validate_member_count(count: int) -> Tuple[bool, Optional[str]]:
        """Validate group member count"""
        if count < ValidationRules.MIN_GROUP_MEMBERS:
            return False, f"Group must have at least {ValidationRules.MIN_GROUP_MEMBERS} members"
        
        if count > ValidationRules.MAX_GROUP_MEMBERS:
            return False, f"Group cannot exceed {ValidationRules.MAX_GROUP_MEMBERS} members"
        
        return True, None


class ExpenseValidator:
    """Expense input validation"""
    
    @staticmethod
    def validate_amount(amount: float) -> Tuple[bool, Optional[str]]:
        """Validate expense amount"""
        if amount is None:
            return False, ValidationMessages.required_field("amount")
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return False, "Amount must be a valid number"
        
        if amount < ValidationRules.MIN_EXPENSE_AMOUNT:
            return False, ValidationMessages.min_value(
                "amount", ValidationRules.MIN_EXPENSE_AMOUNT
            )
        
        if amount > ValidationRules.MAX_EXPENSE_AMOUNT:
            return False, ValidationMessages.max_value(
                "amount", ValidationRules.MAX_EXPENSE_AMOUNT
            )
        
        return True, None
    
    @staticmethod
    def validate_description(description: str) -> Tuple[bool, Optional[str]]:
        """Validate expense description"""
        if not description or not description.strip():
            return False, ValidationMessages.required_field("description")
        
        if len(description) > ValidationRules.MAX_EXPENSE_DESCRIPTION_LENGTH:
            return False, ValidationMessages.max_length(
                "description", ValidationRules.MAX_EXPENSE_DESCRIPTION_LENGTH
            )
        
        return True, None
    
    @staticmethod
    def validate_category(category: str) -> Tuple[bool, Optional[str]]:
        """Validate expense category"""
        if not category:
            return False, ValidationMessages.required_field("category")
        
        if not ExpenseCategory.is_valid(category):
            return False, ValidationMessages.invalid_choice(
                "category", ExpenseCategory.values()
            )
        
        return True, None
    
    @staticmethod
    def validate_split_type(split_type: str) -> Tuple[bool, Optional[str]]:
        """Validate split type"""
        if not split_type:
            return False, ValidationMessages.required_field("split_type")
        
        if not SplitType.is_valid(split_type):
            return False, ValidationMessages.invalid_choice(
                "split_type", SplitType.values()
            )
        
        return True, None
    
    @staticmethod
    def validate_splits(splits: List[Dict], total_amount_cents: int, 
                       split_type: str) -> Tuple[bool, Optional[str]]:
        """Validate expense splits"""
        if not splits:
            return False, "At least one split is required"
        
        if len(splits) > ValidationRules.MAX_SPLITS_PER_EXPENSE:
            return False, f"Cannot have more than {ValidationRules.MAX_SPLITS_PER_EXPENSE} splits"
        
        # Validate each split
        for split in splits:
            if 'user_id' not in split:
                return False, "Each split must have a user_id"
            
            if 'amount' not in split:
                return False, "Each split must have an amount"
            
            try:
                amount = int(split['amount'])
                if amount < 0:
                    return False, "Split amounts must be non-negative"
            except (ValueError, TypeError):
                return False, "Split amounts must be valid integers"
        
        # Validate split sum equals total (for exact and percentage splits)
        if split_type in ['exact', 'percentage']:
            split_sum = sum(int(s['amount']) for s in splits)
            if split_sum != total_amount_cents:
                return False, f"Split amounts ({split_sum}) don't sum to total ({total_amount_cents})"
        
        return True, None


class CurrencyValidator:
    """Currency validation"""
    
    @staticmethod
    def validate_currency_code(code: str) -> Tuple[bool, Optional[str]]:
        """Validate currency code"""
        if not code:
            return False, ValidationMessages.required_field("currency")
        
        if not Currency.is_valid(code):
            return False, ValidationMessages.invalid_choice(
                "currency", CurrencyConfig.SUPPORTED_CURRENCIES[:10]  # Show first 10
            ) + f" (and {len(CurrencyConfig.SUPPORTED_CURRENCIES) - 10} more)"
        
        return True, None


class SettlementValidator:
    """Settlement validation"""
    
    @staticmethod
    def validate_settlement_amount(amount: float) -> Tuple[bool, Optional[str]]:
        """Validate settlement amount"""
        if amount is None:
            return False, ValidationMessages.required_field("amount")
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return False, "Amount must be a valid number"
        
        if amount < ValidationRules.MIN_SETTLEMENT_AMOUNT:
            return False, ValidationMessages.min_value(
                "amount", ValidationRules.MIN_SETTLEMENT_AMOUNT
            )
        
        if amount > ValidationRules.MAX_SETTLEMENT_AMOUNT:
            return False, ValidationMessages.max_value(
                "amount", ValidationRules.MAX_SETTLEMENT_AMOUNT
            )
        
        return True, None
    
    @staticmethod
    def validate_settlement_parties(from_user: str, to_user: str) -> Tuple[bool, Optional[str]]:
        """Validate settlement parties"""
        if not from_user or not to_user:
            return False, "Both from_user and to_user are required"
        
        if from_user == to_user:
            return False, "Cannot settle with yourself"
        
        return True, None


# Export all validators
__all__ = [
    'ValidationError',
    'UserValidator',
    'GroupValidator',
    'ExpenseValidator',
    'CurrencyValidator',
    'SettlementValidator',
]
