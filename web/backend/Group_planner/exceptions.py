"""
Custom exceptions for Group Planner
Professional error handling with specific exception types
"""

class GroupPlannerException(Exception):
    """Base exception for Group Planner"""
    def __init__(self, message: str, code: str = None, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


# Group-related exceptions
class GroupNotFoundException(GroupPlannerException):
    """Raised when group is not found"""
    def __init__(self, group_id: str = None):
        message = f"Group not found: {group_id}" if group_id else "Group not found"
        super().__init__(message, code='GROUP_NOT_FOUND', status_code=404)


class GroupAlreadyExistsException(GroupPlannerException):
    """Raised when attempting to create duplicate group"""
    def __init__(self, group_name: str = None):
        message = f"Group '{group_name}' already exists" if group_name else "Group already exists"
        super().__init__(message, code='GROUP_ALREADY_EXISTS', status_code=409)


class GroupCreationFailedException(GroupPlannerException):
    """Raised when group creation fails"""
    def __init__(self, reason: str = None):
        message = f"Failed to create group: {reason}" if reason else "Failed to create group"
        super().__init__(message, code='GROUP_CREATION_FAILED', status_code=500)


# Member-related exceptions
class MemberNotFoundException(GroupPlannerException):
    """Raised when member is not found"""
    def __init__(self, member_id: str = None):
        message = f"Member not found: {member_id}" if member_id else "Member not found"
        super().__init__(message, code='MEMBER_NOT_FOUND', status_code=404)


class MemberAlreadyExistsException(GroupPlannerException):
    """Raised when member already exists in group"""
    def __init__(self, member_id: str = None):
        message = f"Member {member_id} already exists in group" if member_id else "Member already exists"
        super().__init__(message, code='MEMBER_ALREADY_EXISTS', status_code=409)


class MaxMembersReachedException(GroupPlannerException):
    """Raised when maximum number of members is reached"""
    def __init__(self, max_members: int = None):
        message = f"Maximum number of members ({max_members}) reached" if max_members else "Maximum members reached"
        super().__init__(message, code='MAX_MEMBERS_REACHED', status_code=400)


# Invitation-related exceptions
class InvitationException(GroupPlannerException):
    """Base exception for invitation-related errors"""
    pass


class InvitationNotFoundException(InvitationException):
    """Raised when invitation is not found"""
    def __init__(self, invitation_id: str = None):
        message = f"Invitation not found: {invitation_id}" if invitation_id else "Invitation not found"
        super().__init__(message, code='INVITATION_NOT_FOUND', status_code=404)


class InvitationExpiredException(InvitationException):
    """Raised when invitation has expired"""
    def __init__(self, invitation_id: str = None):
        message = f"Invitation {invitation_id} has expired" if invitation_id else "Invitation has expired"
        super().__init__(message, code='INVITATION_EXPIRED', status_code=400)


class InvitationAlreadyAcceptedException(InvitationException):
    """Raised when invitation has already been accepted"""
    def __init__(self, invitation_id: str = None):
        message = f"Invitation {invitation_id} has already been accepted" if invitation_id else "Invitation already accepted"
        super().__init__(message, code='INVITATION_ALREADY_ACCEPTED', status_code=400)


class InvitationAlreadyDeclinedException(InvitationException):
    """Raised when invitation has already been declined"""
    def __init__(self, invitation_id: str = None):
        message = f"Invitation {invitation_id} has already been declined" if invitation_id else "Invitation already declined"
        super().__init__(message, code='INVITATION_ALREADY_DECLINED', status_code=400)


# Authentication-related exceptions
class AuthenticationException(GroupPlannerException):
    """Base exception for authentication errors"""
    pass


class InvalidTokenException(AuthenticationException):
    """Raised for invalid authentication tokens"""
    def __init__(self, reason: str = None):
        message = f"Invalid token: {reason}" if reason else "Invalid authentication token"
        super().__init__(message, code='INVALID_TOKEN', status_code=401)


class TokenExpiredException(AuthenticationException):
    """Raised when token has expired"""
    def __init__(self):
        super().__init__("Token has expired", code='TOKEN_EXPIRED', status_code=401)


class UnauthorizedException(AuthenticationException):
    """Raised when user is not authenticated"""
    def __init__(self, message: str = None):
        message = message or "Authentication required"
        super().__init__(message, code='UNAUTHORIZED', status_code=401)


class PermissionDeniedException(AuthenticationException):
    """Raised when user lacks required permissions"""
    def __init__(self, resource: str = None, action: str = None):
        if resource and action:
            message = f"Permission denied: Cannot {action} {resource}"
        else:
            message = "You don't have permission to perform this action"
        super().__init__(message, code='PERMISSION_DENIED', status_code=403)


# Validation-related exceptions
class ValidationException(GroupPlannerException):
    """Base exception for validation errors"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, code='VALIDATION_ERROR', status_code=400)


class InvalidInputException(ValidationException):
    """Raised for invalid input data"""
    def __init__(self, field: str, reason: str):
        message = f"Invalid {field}: {reason}"
        super().__init__(message, field=field)


class MissingRequiredFieldException(ValidationException):
    """Raised when required field is missing"""
    def __init__(self, field: str):
        message = f"Missing required field: {field}"
        super().__init__(message, field=field)


# Integration-related exceptions
class IntegrationException(GroupPlannerException):
    """Base exception for integration errors"""
    pass


class LinkExpenseException(IntegrationException):
    """Raised when linking to expense engine fails"""
    def __init__(self, reason: str = None):
        message = f"Failed to link to expense engine: {reason}" if reason else "Failed to link to expense engine"
        super().__init__(message, code='LINK_EXPENSE_ERROR', status_code=500)


class ExpenseGroupNotFoundException(IntegrationException):
    """Raised when linked expense group is not found"""
    def __init__(self, expense_group_id: str = None):
        message = f"Expense group not found: {expense_group_id}" if expense_group_id else "Expense group not found"
        super().__init__(message, code='EXPENSE_GROUP_NOT_FOUND', status_code=404)


# Database-related exceptions
class DatabaseException(GroupPlannerException):
    """Base exception for database errors"""
    pass


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails"""
    def __init__(self, reason: str = None):
        message = f"Database connection failed: {reason}" if reason else "Database connection failed"
        super().__init__(message, code='DATABASE_ERROR', status_code=503)


class DatabaseOperationException(DatabaseException):
    """Raised when database operation fails"""
    def __init__(self, operation: str, reason: str = None):
        message = f"Database {operation} failed: {reason}" if reason else f"Database {operation} failed"
        super().__init__(message, code='DATABASE_ERROR', status_code=500)


# Cache-related exceptions
class CacheException(GroupPlannerException):
    """Base exception for cache errors"""
    def __init__(self, message: str):
        super().__init__(message, code='CACHE_ERROR', status_code=500)


class CacheConnectionException(CacheException):
    """Raised when cache connection fails"""
    def __init__(self, reason: str = None):
        message = f"Cache connection failed: {reason}" if reason else "Cache connection failed"
        super().__init__(message)
