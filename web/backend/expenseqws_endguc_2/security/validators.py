"""
Input Validation Middleware
Prevents injection attacks and data corruption
"""

import logging
from functools import wraps
from flask import request, jsonify
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class Validators:
    """Common validation patterns"""
    
    # Regex patterns
    GROUP_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{10,50}$')
    EXPENSE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{10,50}$')
    USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{10,50}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    CURRENCY_PATTERN = re.compile(r'^[A-Z]{3}$')
    
    # Value constraints
    MAX_EXPENSE_AMOUNT = 1_000_000  # $1 million
    MIN_EXPENSE_AMOUNT = 0.01
    MAX_DESCRIPTION_LENGTH = 500
    MAX_GROUP_NAME_LENGTH = 100
    MAX_CATEGORY_LENGTH = 50
    
    @staticmethod
    def is_valid_group_id(group_id: str) -> bool:
        """Validate group ID format"""
        if not group_id or not isinstance(group_id, str):
            return False
        return bool(Validators.GROUP_ID_PATTERN.match(group_id))
    
    @staticmethod
    def is_valid_expense_id(expense_id: str) -> bool:
        """Validate expense ID format"""
        if not expense_id or not isinstance(expense_id, str):
            return False
        return bool(Validators.EXPENSE_ID_PATTERN.match(expense_id))
    
    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        """Validate user ID format"""
        if not user_id or not isinstance(user_id, str):
            return False
        return bool(Validators.USER_ID_PATTERN.match(user_id))
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(Validators.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def is_valid_currency(currency: str) -> bool:
        """Validate currency code (ISO 4217)"""
        if not currency or not isinstance(currency, str):
            return False
        return bool(Validators.CURRENCY_PATTERN.match(currency))
    
    @staticmethod
    def is_valid_amount(amount: float) -> bool:
        """Validate expense amount"""
        try:
            amount = float(amount)
            return Validators.MIN_EXPENSE_AMOUNT <= amount <= Validators.MAX_EXPENSE_AMOUNT
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 500) -> str:
        """
        Sanitize string input
        - Remove leading/trailing whitespace
        - Limit length
        - Remove dangerous characters
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Strip whitespace
        text = text.strip()
        
        # Truncate
        text = text[:max_length]
        
        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text


def validate_group_id(f):
    """
    Decorator to validate group_id parameter
    
    Usage:
        @expense_bp.route('/groups/<group_id>', methods=['GET'])
        @require_auth
        @validate_group_id
        def get_group(group_id):
            return jsonify({'group': 'data'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        group_id = kwargs.get('group_id')
        
        if not group_id:
            return jsonify({
                'error': 'Validation failed',
                'message': 'Group ID is required'
            }), 400
        
        if not Validators.is_valid_group_id(group_id):
            logger.warning(f"⚠️ Invalid group_id format: {group_id}")
            return jsonify({
                'error': 'Validation failed',
                'message': 'Invalid group ID format'
            }), 400
        
        return f(*args, **kwargs)
    
    return wrapper


def validate_expense_data(f):
    """
    Decorator to validate expense creation/update data
    
    Usage:
        @expense_bp.route('/expenses', methods=['POST'])
        @require_auth
        @validate_expense_data
        def create_expense():
            return jsonify({'expense': 'created'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Validation failed',
                'message': 'Request body is required'
            }), 400
        
        errors = []
        
        # Validate required fields (for creation)
        if request.method == 'POST':
            required_fields = ['group_id', 'amount', 'description', 'paid_by']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        
        # Validate group_id
        if 'group_id' in data and not Validators.is_valid_group_id(data['group_id']):
            errors.append("Invalid group_id format")
        
        # Validate amount
        if 'amount' in data:
            if not Validators.is_valid_amount(data['amount']):
                errors.append(f"Amount must be between ${Validators.MIN_EXPENSE_AMOUNT} and ${Validators.MAX_EXPENSE_AMOUNT}")
        
        # Validate currency
        if 'currency' in data and not Validators.is_valid_currency(data['currency']):
            errors.append("Invalid currency code (must be 3-letter ISO code)")
        
        # Validate description
        if 'description' in data:
            if not isinstance(data['description'], str):
                errors.append("Description must be a string")
            elif len(data['description']) > Validators.MAX_DESCRIPTION_LENGTH:
                errors.append(f"Description too long (max {Validators.MAX_DESCRIPTION_LENGTH} chars)")
            else:
                # Sanitize
                data['description'] = Validators.sanitize_string(
                    data['description'],
                    Validators.MAX_DESCRIPTION_LENGTH
                )
        
        # Validate category
        if 'category' in data:
            if len(data['category']) > Validators.MAX_CATEGORY_LENGTH:
                errors.append(f"Category too long (max {Validators.MAX_CATEGORY_LENGTH} chars)")
            else:
                data['category'] = Validators.sanitize_string(
                    data['category'],
                    Validators.MAX_CATEGORY_LENGTH
                )
        
        # Validate paid_by
        if 'paid_by' in data and not Validators.is_valid_user_id(data['paid_by']):
            errors.append("Invalid paid_by user ID")
        
        # Validate split_with (if present)
        if 'split_with' in data:
            if not isinstance(data['split_with'], list):
                errors.append("split_with must be an array")
            else:
                for user_id in data['split_with']:
                    if not Validators.is_valid_user_id(user_id):
                        errors.append(f"Invalid user ID in split_with: {user_id}")
                        break
        
        if errors:
            logger.warning(f"⚠️ Expense validation failed: {errors}")
            return jsonify({
                'error': 'Validation failed',
                'messages': errors
            }), 400
        
        return f(*args, **kwargs)
    
    return wrapper


def validate_settlement_data(f):
    """
    Decorator to validate settlement creation data
    
    Usage:
        @expense_bp.route('/settlements', methods=['POST'])
        @require_auth
        @validate_settlement_data
        def create_settlement():
            return jsonify({'settlement': 'created'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Validation failed',
                'message': 'Request body is required'
            }), 400
        
        errors = []
        
        # Validate required fields
        required_fields = ['group_id', 'from_user', 'to_user', 'amount']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate group_id
        if 'group_id' in data and not Validators.is_valid_group_id(data['group_id']):
            errors.append("Invalid group_id format")
        
        # Validate from_user
        if 'from_user' in data and not Validators.is_valid_user_id(data['from_user']):
            errors.append("Invalid from_user ID")
        
        # Validate to_user
        if 'to_user' in data and not Validators.is_valid_user_id(data['to_user']):
            errors.append("Invalid to_user ID")
        
        # Validate amount
        if 'amount' in data:
            if not Validators.is_valid_amount(data['amount']):
                errors.append(f"Amount must be between ${Validators.MIN_EXPENSE_AMOUNT} and ${Validators.MAX_EXPENSE_AMOUNT}")
        
        # Validate currency
        if 'currency' in data and not Validators.is_valid_currency(data['currency']):
            errors.append("Invalid currency code")
        
        # Validate users are different
        if 'from_user' in data and 'to_user' in data:
            if data['from_user'] == data['to_user']:
                errors.append("from_user and to_user must be different")
        
        if errors:
            logger.warning(f"⚠️ Settlement validation failed: {errors}")
            return jsonify({
                'error': 'Validation failed',
                'messages': errors
            }), 400
        
        return f(*args, **kwargs)
    
    return wrapper


def validate_group_data(f):
    """
    Decorator to validate group creation/update data
    
    Usage:
        @expense_bp.route('/groups', methods=['POST'])
        @require_auth
        @validate_group_data
        def create_group():
            return jsonify({'group': 'created'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Validation failed',
                'message': 'Request body is required'
            }), 400
        
        errors = []
        
        # Validate required fields (for creation)
        if request.method == 'POST':
            required_fields = ['name', 'currency']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        
        # Validate name
        if 'name' in data:
            if not isinstance(data['name'], str):
                errors.append("Group name must be a string")
            elif len(data['name']) > Validators.MAX_GROUP_NAME_LENGTH:
                errors.append(f"Group name too long (max {Validators.MAX_GROUP_NAME_LENGTH} chars)")
            elif len(data['name'].strip()) == 0:
                errors.append("Group name cannot be empty")
            else:
                # Sanitize
                data['name'] = Validators.sanitize_string(
                    data['name'],
                    Validators.MAX_GROUP_NAME_LENGTH
                )
        
        # Validate currency
        if 'currency' in data and not Validators.is_valid_currency(data['currency']):
            errors.append("Invalid currency code (must be 3-letter ISO code)")
        
        if errors:
            logger.warning(f"⚠️ Group validation failed: {errors}")
            return jsonify({
                'error': 'Validation failed',
                'messages': errors
            }), 400
        
        return f(*args, **kwargs)
    
    return wrapper
