"""
Role-Based Access Control (RBAC) Middleware
Enforces permissions based on group roles

Phase 3: Complete implementation with actual group membership checks
"""

from functools import wraps
from flask import request, g
from typing import Optional, Dict, Any
import logging

from ..exceptions import ForbiddenError, ResourceNotFoundError
from ..constants import GroupRole, Permission, check_permission
from .auth import get_current_user

logger = logging.getLogger(__name__)


def _get_user_role_in_group(group_id: str, user_id: str) -> Optional[GroupRole]:
    """
    Get user's role in a group from Firestore
    
    Args:
        group_id: Group ID
        user_id: User ID
        
    Returns:
        GroupRole if user is a member, None otherwise
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        # Check expense_group_members collection for membership
        member_doc_id = f"{group_id}_{user_id}"
        member_ref = db.collection('expense_group_members').document(member_doc_id)
        member_doc = member_ref.get()
        
        if member_doc.exists:
            member_data = member_doc.to_dict()
            if member_data.get('is_active', False):
                role_str = member_data.get('role', 'member')
                return GroupRole(role_str)
        
        # Fallback: Check group document's members array
        group_ref = db.collection('expense_groups').document(group_id)
        group_doc = group_ref.get()
        
        if group_doc.exists:
            group_data = group_doc.to_dict()
            members = group_data.get('members', [])
            
            if user_id in members:
                # Get role from member_details if available
                member_details = group_data.get('member_details', {})
                user_details = member_details.get(user_id, {})
                role_str = user_details.get('role', 'member')
                return GroupRole(role_str)
        
        return None
        
    except Exception as exc:
        logger.error("Error getting user role: %s", str(exc))
        return None


def _get_group_id_from_request(group_id_param: str, kwargs: Dict[str, Any]) -> Optional[str]:
    """
    Extract group_id from request arguments, view args, or JSON body
    
    Args:
        group_id_param: Parameter name to look for
        kwargs: Function keyword arguments
        
    Returns:
        Group ID if found, None otherwise
    """
    # Check function kwargs
    group_id = kwargs.get(group_id_param)
    if group_id:
        return group_id
    
    # Check URL route parameters
    if request.view_args:
        group_id = request.view_args.get(group_id_param)
        if group_id:
            return group_id
    
    # Check query parameters
    group_id = request.args.get(group_id_param)
    if group_id:
        return group_id
    
    # Check JSON body
    if request.is_json and request.json:
        group_id = request.json.get(group_id_param)
        if group_id:
            return group_id
    
    return None


def require_permission(permission: Permission, group_id_param: str = 'group_id'):
    """
    Decorator to require specific permission in a group
    
    Args:
        permission: Required permission from Permission enum
        group_id_param: Name of parameter containing group_id
    
    Usage:
        @require_auth
        @require_permission(Permission.DELETE_GROUP, 'group_id')
        def delete_group(group_id):
            # User has delete_group permission
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            user_id = current_user['uid']
            
            group_id = _get_group_id_from_request(group_id_param, kwargs)
            if not group_id:
                raise ForbiddenError("Group ID required for permission check")
            
            # Get user's role in the group
            user_role = _get_user_role_in_group(group_id, user_id)
            
            if not user_role:
                logger.warning(
                    "User %s is not a member of group %s",
                    user_id, group_id
                )
                raise ForbiddenError("You are not a member of this group")
            
            # Check permission
            if not check_permission(user_role, permission):
                logger.warning(
                    "User %s (role: %s) lacks permission %s in group %s",
                    user_id, user_role.value, permission.value, group_id
                )
                raise ForbiddenError(f"You don't have permission: {permission.value}")
            
            # Store role in context for potential use
            g.user_role = user_role
            g.group_id = group_id
            
            logger.debug(
                "Permission granted: user=%s, role=%s, permission=%s, group=%s",
                user_id, user_role.value, permission.value, group_id
            )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_role(role: GroupRole, group_id_param: str = 'group_id'):
    """
    Decorator to require minimum role level
    
    Args:
        role: Minimum required role
        group_id_param: Name of parameter containing group_id
    
    Usage:
        @require_auth
        @require_role(GroupRole.ADMIN, 'group_id')
        def admin_function(group_id):
            # User is admin or owner
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            user_id = current_user['uid']
            
            group_id = _get_group_id_from_request(group_id_param, kwargs)
            if not group_id:
                raise ForbiddenError("Group ID required for role check")
            
            # Get user's role in the group
            user_role = _get_user_role_in_group(group_id, user_id)
            
            if not user_role:
                logger.warning(
                    "User %s is not a member of group %s",
                    user_id, group_id
                )
                raise ForbiddenError("You are not a member of this group")
            
            # Role hierarchy: owner > admin > member
            role_hierarchy = {
                GroupRole.OWNER: 3,
                GroupRole.ADMIN: 2,
                GroupRole.MEMBER: 1
            }
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(role, 0):
                logger.warning(
                    "User %s (role: %s) requires role %s for group %s",
                    user_id, user_role.value, role.value, group_id
                )
                raise ForbiddenError(f"This action requires {role.value} role")
            
            # Store role in context
            g.user_role = user_role
            g.group_id = group_id
            
            logger.debug(
                "Role check passed: user=%s, user_role=%s, required=%s, group=%s",
                user_id, user_role.value, role.value, group_id
            )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_group_member(group_id_param: str = 'group_id'):
    """
    Decorator to require user to be a member of the group (any role)
    
    Usage:
        @require_auth
        @require_group_member('group_id')
        def view_group(group_id):
            # User is a member
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            user_id = current_user['uid']
            
            group_id = _get_group_id_from_request(group_id_param, kwargs)
            if not group_id:
                raise ForbiddenError("Group ID required")
            
            # Get user's role in the group
            user_role = _get_user_role_in_group(group_id, user_id)
            
            if not user_role:
                logger.warning(
                    "User %s is not a member of group %s",
                    user_id, group_id
                )
                raise ForbiddenError("You are not a member of this group")
            
            # Store role in context
            g.user_role = user_role
            g.group_id = group_id
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_owner(group_id_param: str = 'group_id'):
    """
    Decorator to require owner role
    
    Usage:
        @require_auth
        @require_owner('group_id')
        def delete_group(group_id):
            # Only group owner can execute this
            pass
    """
    return require_role(GroupRole.OWNER, group_id_param)


def require_admin(group_id_param: str = 'group_id'):
    """
    Decorator to require admin or owner role
    
    Usage:
        @require_auth
        @require_admin('group_id')
        def manage_members(group_id):
            # Admin or owner can execute this
            pass
    """
    return require_role(GroupRole.ADMIN, group_id_param)


def can_edit_expense(expense: Dict[str, Any], user_id: str, user_role: GroupRole) -> bool:
    """
    Check if user can edit a specific expense
    
    Args:
        expense: Expense dict with created_by field
        user_id: User ID to check
        user_role: User's role in the group
    
    Returns:
        bool: True if user can edit
    """
    # Owner/Admin can edit any expense
    if user_role in [GroupRole.OWNER, GroupRole.ADMIN]:
        return True
    
    # Creator can edit their own expense
    if expense.get('created_by') == user_id:
        return True
    
    return False


def can_delete_expense(expense: Dict[str, Any], user_id: str, user_role: GroupRole) -> bool:
    """
    Check if user can delete a specific expense
    
    Args:
        expense: Expense dict with created_by field
        user_id: User ID to check
        user_role: User's role in the group
    
    Returns:
        bool: True if user can delete
    """
    # Owner/admin can delete any expense
    if user_role in [GroupRole.OWNER, GroupRole.ADMIN]:
        return True
    
    # Creator can delete their own expense
    if expense.get('created_by') == user_id:
        return True
    
    return False


def require_expense_owner_or_admin(expense_id_param: str = 'expense_id'):
    """
    Decorator to require user to be expense creator or group admin/owner
    
    Usage:
        @require_auth
        @require_expense_owner_or_admin('expense_id')
        def edit_expense(expense_id):
            # User can edit this expense
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from firebase_admin import firestore
            
            current_user = get_current_user()
            user_id = current_user['uid']
            
            expense_id = kwargs.get(expense_id_param) or request.view_args.get(expense_id_param)
            if not expense_id:
                raise ForbiddenError("Expense ID required")
            
            # Get expense document
            db = firestore.client()
            expense_ref = db.collection('expense_expenses').document(expense_id)
            expense_doc = expense_ref.get()
            
            if not expense_doc.exists:
                raise ResourceNotFoundError(f"Expense {expense_id} not found")
            
            expense_data = expense_doc.to_dict()
            group_id = expense_data.get('group_id')
            
            # Get user's role in the group
            user_role = _get_user_role_in_group(group_id, user_id)
            
            if not user_role:
                raise ForbiddenError("You are not a member of this group")
            
            # Check permission
            if not can_edit_expense(expense_data, user_id, user_role):
                raise ForbiddenError("You don't have permission to edit this expense")
            
            # Store in context
            g.user_role = user_role
            g.expense_data = expense_data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
