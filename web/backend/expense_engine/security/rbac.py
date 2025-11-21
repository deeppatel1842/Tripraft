"""
Role-Based Access Control (RBAC)
Manages permissions and access control for resources
"""

import logging
from enum import Enum
from functools import wraps
from flask import g, jsonify

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permission types for different operations"""
    
    # Group permissions
    VIEW_GROUP = "view_group"
    EDIT_GROUP = "edit_group"
    DELETE_GROUP = "delete_group"
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    
    # Expense permissions
    CREATE_EXPENSE = "create_expense"
    EDIT_EXPENSE = "edit_expense"
    DELETE_EXPENSE = "delete_expense"
    VIEW_EXPENSE = "view_expense"
    
    # Settlement permissions
    CREATE_SETTLEMENT = "create_settlement"
    APPROVE_SETTLEMENT = "approve_settlement"
    
    # Admin permissions
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"


class Role(Enum):
    """User roles in the system"""
    
    ADMIN = "admin"              # Full system access
    GROUP_OWNER = "group_owner"  # Full access to owned groups
    GROUP_MEMBER = "member"      # Standard member access
    VIEWER = "viewer"            # Read-only access


# Permission mappings
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        # Admin has ALL permissions
        Permission.VIEW_GROUP,
        Permission.EDIT_GROUP,
        Permission.DELETE_GROUP,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.CREATE_EXPENSE,
        Permission.EDIT_EXPENSE,
        Permission.DELETE_EXPENSE,
        Permission.VIEW_EXPENSE,
        Permission.CREATE_SETTLEMENT,
        Permission.APPROVE_SETTLEMENT,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    Role.GROUP_OWNER: [
        # Group owner can manage their groups
        Permission.VIEW_GROUP,
        Permission.EDIT_GROUP,
        Permission.DELETE_GROUP,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.CREATE_EXPENSE,
        Permission.EDIT_EXPENSE,
        Permission.DELETE_EXPENSE,
        Permission.VIEW_EXPENSE,
        Permission.CREATE_SETTLEMENT,
        Permission.APPROVE_SETTLEMENT,
    ],
    Role.GROUP_MEMBER: [
        # Members can view and create
        Permission.VIEW_GROUP,
        Permission.CREATE_EXPENSE,
        Permission.EDIT_EXPENSE,  # Own expenses only
        Permission.DELETE_EXPENSE,  # Own expenses only
        Permission.VIEW_EXPENSE,
        Permission.CREATE_SETTLEMENT,
    ],
    Role.VIEWER: [
        # Viewers can only read
        Permission.VIEW_GROUP,
        Permission.VIEW_EXPENSE,
    ],
}


def get_user_role(user_id: str, group_id: str = None) -> Role:
    """
    Get user's role for a specific group or system-wide
    
    Args:
        user_id: User ID
        group_id: Optional group ID for group-specific roles
        
    Returns:
        Role enum value
    """
    # TODO: In production, query from database
    # For now, return GROUP_MEMBER by default
    
    # Check if user is admin (from Firebase custom claims or database)
    # if is_admin(user_id):
    #     return Role.ADMIN
    
    # Check if user is group owner
    if group_id:
        # if is_group_owner(user_id, group_id):
        #     return Role.GROUP_OWNER
        pass
    
    # Default to member
    return Role.GROUP_MEMBER


def has_permission(user_id: str, permission: Permission, group_id: str = None) -> bool:
    """
    Check if user has specific permission
    
    Args:
        user_id: User ID
        permission: Permission to check
        group_id: Optional group ID for group-specific checks
        
    Returns:
        True if user has permission, False otherwise
    """
    try:
        role = get_user_role(user_id, group_id)
        allowed_permissions = ROLE_PERMISSIONS.get(role, [])
        
        has_perm = permission in allowed_permissions
        
        if not has_perm:
            logger.warning(f"⚠️ Permission denied: {user_id} lacks {permission.value} (role: {role.value})")
        
        return has_perm
        
    except Exception as e:
        logger.error(f"❌ Error checking permission: {e}")
        return False


def require_permission(permission: Permission):
    """
    Decorator to enforce permission checks on routes
    
    Usage:
        @expense_bp.route('/admin/analytics', methods=['GET'])
        @require_auth
        @require_permission(Permission.VIEW_ANALYTICS)
        def get_analytics():
            return jsonify({'data': 'sensitive'})
    
    Args:
        permission: Required permission
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Check if user is authenticated
            if not hasattr(g, 'user_id') or not g.user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please log in to access this resource'
                }), 401
            
            # Extract group_id from route args if present
            group_id = kwargs.get('group_id', None)
            
            # Check permission
            if not has_permission(g.user_id, permission, group_id):
                return jsonify({
                    'error': 'Permission denied',
                    'message': f'You do not have {permission.value} permission',
                    'required_permission': permission.value
                }), 403
            
            # Permission granted, execute route
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def require_group_membership(f):
    """
    Decorator to check if user is a member of the group
    
    Usage:
        @expense_bp.route('/groups/<group_id>', methods=['GET'])
        @require_auth
        @require_group_membership
        def get_group(group_id):
            return jsonify({'group': 'data'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        group_id = kwargs.get('group_id')
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # TODO: Check if user is member of group
        # For now, allow all authenticated users
        # if not is_group_member(g.user_id, group_id):
        #     return jsonify({'error': 'Not a group member'}), 403
        
        return f(*args, **kwargs)
    
    return wrapper
