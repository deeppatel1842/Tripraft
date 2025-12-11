"""
Custom Exceptions for Expense Engine

All application-specific exceptions with proper HTTP status codes
for Flask error handling.
"""

from typing import Optional, Dict, Any


class ExpenseEngineError(Exception):
    """Base exception for all expense engine errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            'success': False,
            'error': {
                'message': self.message,
                'code': self.error_code,
                'details': self.details
            }
        }


# ============================================================================
# Authentication & Authorization Errors (4xx)
# ============================================================================

class UnauthorizedError(ExpenseEngineError):
    """User is not authenticated"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenError(ExpenseEngineError):
    """User is authenticated but lacks permission"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class InvalidTokenError(ExpenseEngineError):
    """Invalid or expired authentication token"""
    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message, status_code=401, error_code="INVALID_TOKEN")


# ============================================================================
# Validation Errors (4xx)
# ============================================================================

class ValidationError(ExpenseEngineError):
    """Input validation failed"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message, 
            status_code=400, 
            error_code="VALIDATION_ERROR",
            details=details
        )


class DuplicateEntryError(ExpenseEngineError):
    """Resource already exists"""
    def __init__(self, message: str, resource_type: str, resource_id: str):
        super().__init__(
            message,
            status_code=409,
            error_code="DUPLICATE_ENTRY",
            details={'resource_type': resource_type, 'resource_id': resource_id}
        )


# ============================================================================
# Resource Errors (4xx)
# ============================================================================

class NotFoundError(ExpenseEngineError):
    """Resource not found"""
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            message,
            status_code=404,
            error_code="NOT_FOUND",
            details={'resource_type': resource_type} if resource_type else {}
        )


# Alias for consistency
ResourceNotFoundError = NotFoundError


class GroupNotFoundError(NotFoundError):
    """Group not found"""
    def __init__(self, group_id: str):
        super().__init__(
            f"Group not found: {group_id}",
            resource_type="group"
        )


class ExpenseNotFoundError(NotFoundError):
    """Expense not found"""
    def __init__(self, expense_id: str):
        super().__init__(
            f"Expense not found: {expense_id}",
            resource_type="expense"
        )


class UserNotMemberError(ForbiddenError):
    """User is not a member of the group"""
    def __init__(self, user_id: str, group_id: str):
        super().__init__(
            f"User {user_id} is not a member of group {group_id}"
        )
        self.error_code = "USER_NOT_MEMBER"


class InsufficientPermissionsError(ForbiddenError):
    """User lacks required permissions for this action"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message)
        self.error_code = "INSUFFICIENT_PERMISSIONS"


# ============================================================================
# Business Logic Errors (4xx)
# ============================================================================

class InsufficientBalanceError(ExpenseEngineError):
    """User has insufficient balance for settlement"""
    def __init__(self, user_id: str, required: float, available: float):
        super().__init__(
            f"Insufficient balance: required {required}, available {available}",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={
                'user_id': user_id,
                'required': required,
                'available': available
            }
        )


class InvalidSplitError(ValidationError):
    """Expense splits don't sum to total amount"""
    def __init__(self, total: float, split_sum: float):
        super().__init__(
            f"Splits ({split_sum}) don't sum to total amount ({total})",
            details={'total': total, 'split_sum': split_sum}
        )


class MaxMembersReachedError(ExpenseEngineError):
    """Group has reached maximum member limit"""
    def __init__(self, group_id: str, max_members: int):
        super().__init__(
            f"Group {group_id} has reached maximum member limit ({max_members})",
            status_code=400,
            error_code="MAX_MEMBERS_REACHED",
            details={'group_id': group_id, 'max_members': max_members}
        )


# ============================================================================
# System Errors (5xx)
# ============================================================================

class DatabaseError(ExpenseEngineError):
    """Database operation failed"""
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={'operation': operation} if operation else {}
        )


class CacheError(ExpenseEngineError):
    """Cache operation failed"""
    def __init__(self, message: str):
        super().__init__(
            message,
            status_code=500,
            error_code="CACHE_ERROR"
        )


class ServiceUnavailableError(ExpenseEngineError):
    """Service temporarily unavailable"""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503, error_code="SERVICE_UNAVAILABLE")


# ============================================================================
# Rate Limiting Errors (429)
# ============================================================================

class RateLimitExceededError(ExpenseEngineError):
    """Rate limit exceeded"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={'retry_after_seconds': retry_after} if retry_after else {}
        )


# ============================================================================
# Error Handler for Flask
# ============================================================================

def register_error_handlers(app):
    """
    Register error handlers with Flask app
    
    Usage:
        from expense_engine.exceptions import register_error_handlers
        register_error_handlers(app)
    """
    from flask import jsonify
    import logging
    
    logger = logging.getLogger(__name__)
    
    @app.errorhandler(ExpenseEngineError)
    def handle_expense_engine_error(error: ExpenseEngineError):
        """Handle all expense engine errors"""
        logger.warning(f"{error.error_code}: {error.message}")
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': {
                'message': 'Endpoint not found',
                'code': 'NOT_FOUND'
            }
        }), 404
    
    @app.errorhandler(500)
    def handle_500(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'success': False,
            'error': {
                'message': 'Internal server error',
                'code': 'INTERNAL_ERROR'
            }
        }), 500
