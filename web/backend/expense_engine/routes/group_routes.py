"""
Group Routes - Expense Group Management API
Handles group CRUD operations and member management
"""

from flask import Blueprint, request, jsonify
import logging
import json

from ..services.group_service import GroupService
from ..middleware.auth import require_auth, get_current_user_id, get_current_user
from ..exceptions import (
    ValidationError, NotFoundError, ForbiddenError,
    DuplicateEntryError, InsufficientPermissionsError
)
from ..models.group import GroupCreate
from ..config import redis_config

# Import cache manager
try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager(): return None

logger = logging.getLogger(__name__)

# Create blueprint
group_bp = Blueprint('expense_groups', __name__, url_prefix='/api/expense/groups')


@group_bp.route('', methods=['POST'])
@require_auth
def create_group():
    """
    Create new expense group
    
    POST /api/expense/groups
    Body: {
        "name": "Trip to Paris",
        "description": "Summer vacation expenses",
        "currency": "EUR",
        "category": "travel"
    }
    
    Response: {
        "success": true,
        "group": {...}
    }
    """
    try:
        current_user = get_current_user()
        current_user_id = current_user['uid']
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        if 'name' not in data:
            raise ValidationError("Group name is required")
        
        # Create group model
        group_data = GroupCreate(**data)
        
        # Get creator display name from auth or data
        creator_display_name = (
            data.get('creator_display_name') or 
            current_user.get('name') or 
            current_user.get('email', '').split('@')[0] or 
            'User'
        )
        
        # Create group
        service = GroupService()
        group = service.create_group(
            name=group_data.name,
            created_by=current_user_id,
            creator_display_name=creator_display_name,
            description=group_data.description,
            currency=group_data.currency
        )
        
        logger.info("Group created by user %s", current_user_id)
        
        return jsonify({
            'success': True,
            'group': group if isinstance(group, dict) else {}
        }), 201
        
    except ValidationError as e:
        logger.warning("Validation error in create_group: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error creating group: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to create group'}), 500


@group_bp.route('/<group_id>', methods=['GET'])
@group_bp.route('/<group_id>/full', methods=['GET'])
@require_auth
def get_group_full(group_id: str):
    """
    Get group details with members, balances, and expenses
    
    GET /api/expense/groups/:gid
    GET /api/expense/groups/:gid/full
    
    Response: {
        "success": true,
        "group": {...},
        "members": [...],
        "balances": [...],
        "expenses": [...],
        "expenses_pagination": {...}
    }
    
    Performance: Uses Redis caching (TTL=30s) to reduce Firestore reads
    """
    try:
        current_user_id = get_current_user_id()
        service = GroupService()
        
        # Check membership first (must always verify)
        if not service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Check for bypass_cache query param
        bypass_cache = request.args.get('bypass_cache', 'false').lower() == 'true'
        
        # Try to get from cache first
        cache_key = redis_config.KEY_GROUP_SUMMARY.format(gid=group_id)
        cache = get_cache_manager() if CACHE_ENABLED else None
        
        # Debug cache status (using print for direct stdout output)
        print(f"\n🔑 CACHE CHECK for group {group_id}")
        print(f"   Cache key: {cache_key}")
        print(f"   CACHE_ENABLED: {CACHE_ENABLED}")
        print(f"   Cache manager: {'available' if cache else 'None'}")
        
        if cache:
            logger.info("Cache manager available for group %s, checking key: %s", group_id, cache_key)
            is_available = cache.is_available()
            print(f"   Redis available: {is_available}")
            if is_available:
                logger.info("Redis connection is available")
            else:
                logger.warning("Redis connection NOT available")
        else:
            logger.warning("Cache manager is None (CACHE_ENABLED=%s)", CACHE_ENABLED)
        
        if cache and not bypass_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                print(f"   ✅ CACHE HIT for group {group_id}")
                logger.info("Cache HIT for group %s", group_id)
                return jsonify(cached_data)
            else:
                print(f"   ❌ CACHE MISS for group {group_id}")
                logger.info("Cache MISS for group %s", group_id)
        
        # Get group
        group = service.get_group(group_id)
        if not group:
            raise NotFoundError("Group not found")
        
        # Check if group is deleted/inactive
        if group.get('is_active') is False:
            raise NotFoundError("Group has been deleted")
        
        # Get members from expense_group_members collection
        members = service.get_group_members(group_id)
        
        # Get balances and convert dict to array format
        from expense_engine.services.balance_service import BalanceService
        balance_service = BalanceService()
        balances_dict = balance_service.get_group_balances(group_id)
        
        # Convert dict to array format for frontend
        # IMPORTANT: Include ALL members even if balance is 0
        balances_array = []
        for member in members:
            uid = member.get('user_id')
            balance_value = balances_dict.get(uid, 0)
            balances_array.append({
                'user_id': uid,
                'display_name': member.get('display_name', 'Unknown'),
                'balance': float(balance_value) if balance_value else 0.0,
                'net_balance': float(balance_value) if balance_value else 0.0,
                'is_active': member.get('is_active', True)
            })
        
        # Get expenses for the group (include deleted for transaction history)
        from expense_engine.services.expense_service import ExpenseService
        expense_service = ExpenseService()
        expenses_result = expense_service.get_group_expenses(
            group_id, 
            limit=50, 
            offset=0,
            include_deleted=True  # Phase 12: Show deleted expenses faded in transaction history
        )
        raw_expenses = expenses_result.get('expenses', [])
        
        # Normalize expense data for frontend compatibility
        expenses = []
        for exp in raw_expenses:
            normalized = dict(exp)
            # Add type field for frontend filtering
            normalized['type'] = 'expense'
            # Add date field (frontend expects 'date', backend sends 'expense_date')
            if 'expense_date' in normalized and 'date' not in normalized:
                normalized['date'] = normalized['expense_date']
            expenses.append(normalized)
        
        expenses_pagination = {
            'total': expenses_result.get('total', 0),
            'returned_count': len(expenses),
            'has_more': expenses_result.get('has_more', False)
        }
        
        logger.info("Returning group %s with %d members, %d balances, %d expenses", 
                    group_id, len(members), len(balances_array), len(expenses))
        
        # Build response
        response_data = {
            'success': True,
            'group': group if isinstance(group, dict) else {},
            'members': members,
            'balances': balances_array,
            'expenses': expenses,
            'expenses_pagination': expenses_pagination
        }
        
        # Cache the response
        if cache:
            try:
                cache.set(cache_key, response_data, ttl=redis_config.TTL_GROUP_SUMMARY)
                logger.info("Cache SET for group %s (TTL=%ds)", group_id, redis_config.TTL_GROUP_SUMMARY)
            except Exception as cache_err:  # pylint: disable=broad-except
                logger.warning("Failed to cache group data: %s", cache_err)
        
        return jsonify(response_data)
        
    except (NotFoundError, ForbiddenError) as e:
        logger.warning("Error in get_group: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 404 if isinstance(e, NotFoundError) else 403
    except Exception as e:
        logger.error("Error getting group: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get group'}), 500


@group_bp.route('/<group_id>', methods=['PATCH'])
@require_auth
def update_group(group_id: str):
    """
    Update group details
    
    PATCH /api/expense/groups/:gid
    Body: {
        "name"?: "Updated name",
        "description"?: "New description",
        "category"?: "travel"
    }
    
    Response: {
        "success": true,
        "group": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        service = GroupService()
        
        # Check permissions (admin or owner)
        if not service.has_permission(group_id, current_user_id, 'edit_group'):
            raise InsufficientPermissionsError("You don't have permission to edit this group")
        
        # Update group via repository
        service.group_repo.update(group_id, data)
        updated_group = service.get_group(group_id)
        
        logger.info("Group updated: %s by user %s", group_id, current_user_id)
        
        return jsonify({
            'success': True,
            'group': updated_group if isinstance(updated_group, dict) else {}
        })
        
    except (ValidationError, InsufficientPermissionsError) as e:
        logger.warning("Error in update_group: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400 if isinstance(e, ValidationError) else 403
    except Exception as e:
        logger.error("Error updating group: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update group'}), 500


@group_bp.route('/<group_id>', methods=['DELETE'])
@require_auth
def delete_group(group_id: str):
    """
    Delete group (soft delete)
    
    DELETE /api/expense/groups/:gid
    
    Response: {
        "success": true,
        "message": "Group deleted successfully"
    }
    """
    try:
        current_user_id = get_current_user_id()
        service = GroupService()
        
        # Check permissions (owner only)
        if not service.has_permission(group_id, current_user_id, 'delete_group'):
            raise InsufficientPermissionsError("Only the group owner can delete the group")
        
        # Delete group (soft delete via repository update)
        service.group_repo.update(group_id, {'is_active': False})
        
        # Also deactivate all memberships so users don't see this group
        members = service.get_group_members(group_id)
        for member in members:
            # Use remove_member which sets is_active: False (Phase 15 soft-delete)
            service.group_repo.remove_member(group_id, member.get('user_id'), current_user_id, 'group_deleted')
        
        logger.info("Group deleted: %s by user %s", group_id, current_user_id)
        
        return jsonify({
            'success': True,
            'message': 'Group deleted successfully'
        })
        
    except InsufficientPermissionsError as e:
        logger.warning("Error in delete_group: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error deleting group: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to delete group'}), 500


@group_bp.route('/<group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id: str):
    """
    Get all group members
    
    GET /api/expense/groups/:gid/members
    
    Response: {
        "success": true,
        "members": [...]
    }
    """
    try:
        current_user_id = get_current_user_id()
        service = GroupService()
        
        # Check membership
        if not service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get group and extract members
        group = service.get_group(group_id)
        members = group.get('member_details', {})
        
        return jsonify({
            'success': True,
            'members': list(members.values()) if isinstance(members, dict) else members
        })
        
    except ForbiddenError as e:
        logger.warning("Error in get_group_members: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting group members: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get members'}), 500


@group_bp.route('/<group_id>/members', methods=['POST'])
@require_auth
def add_group_member(group_id: str):
    """
    Add member to group directly (without invitation)
    
    POST /api/expense/groups/:gid/members
    Body: {
        "user_id": "user123",
        "role": "member"
    }
    
    Response: {
        "success": true,
        "member": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            raise ValidationError("user_id is required")
        
        service = GroupService()
        
        # Check permissions
        if not service.has_permission(group_id, current_user_id, 'add_member'):
            raise InsufficientPermissionsError("You don't have permission to add members")
        
        # Add member
        service.add_member(
            group_id=group_id,
            user_id=data['user_id'],
            display_name=data.get('display_name', 'User'),
            added_by=current_user_id
        )
        
        # Get updated group to return member
        group = service.get_group(group_id)
        member = group.get('member_details', {}).get(data['user_id'])
        
        logger.info("Member added to group %s: %s", group_id, data['user_id'])
        
        return jsonify({
            'success': True,
            'member': member if isinstance(member, dict) else {}
        }), 201
        
    except (ValidationError, InsufficientPermissionsError, DuplicateEntryError) as e:
        logger.warning("Error in add_group_member: %s", e)
        status = 400 if isinstance(e, ValidationError) else (403 if isinstance(e, InsufficientPermissionsError) else 409)
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error adding member: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to add member'}), 500


@group_bp.route('/<group_id>/members/<user_id>', methods=['DELETE'])
@require_auth
def remove_group_member(group_id: str, user_id: str):
    """
    Remove member from group
    
    DELETE /api/expense/groups/:gid/members/:uid
    
    Response: {
        "success": true,
        "message": "Member removed successfully"
    }
    """
    try:
        current_user_id = get_current_user_id()
        service = GroupService()
        
        # Check permissions (admin/owner or removing self)
        if user_id != current_user_id:
            if not service.has_permission(group_id, current_user_id, 'remove_member'):
                raise InsufficientPermissionsError("You don't have permission to remove members")
        
        # Remove member
        service.remove_member(group_id, user_id, current_user_id)
        
        logger.info("Member removed from group %s: %s", group_id, user_id)
        
        return jsonify({
            'success': True,
            'message': 'Member removed successfully'
        })
        
    except (InsufficientPermissionsError, ForbiddenError) as e:
        logger.warning("Error in remove_group_member: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error removing member: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to remove member'}), 500


@group_bp.route('/<group_id>/members/<user_id>/role', methods=['PATCH'])
@require_auth
def update_member_role(group_id: str, user_id: str):
    """
    Update member role
    
    PATCH /api/expense/groups/:gid/members/:uid/role
    Body: {
        "role": "admin"
    }
    
    Response: {
        "success": true,
        "member": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'role' not in data:
            raise ValidationError("role is required")
        
        service = GroupService()
        
        # Check permissions (owner only)
        if not service.has_permission(group_id, current_user_id, 'change_roles'):
            raise InsufficientPermissionsError("Only the owner can change member roles")
        
        # Update role
        service.update_member_role(group_id, user_id, data['role'], current_user_id)
        
        # Get updated member
        group = service.get_group(group_id)
        updated_member = group.get('member_details', {}).get(user_id)
        
        logger.info("Member role updated in group %s: %s -> %s", group_id, user_id, data['role'])
        
        return jsonify({
            'success': True,
            'member': updated_member if isinstance(updated_member, dict) else {}
        })
        
    except (ValidationError, InsufficientPermissionsError) as e:
        logger.warning("Error in update_member_role: %s", e)
        status = 400 if isinstance(e, ValidationError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error updating member role: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update role'}), 500


@group_bp.route('/<group_id>/summary', methods=['GET'])
@require_auth
def get_group_summary(group_id: str):
    """
    Get comprehensive group summary
    
    GET /api/expense/groups/:gid/summary
    
    Response: {
        "success": true,
        "group": {...},
        "members": [...],
        "balances": [...],
        "recent_expenses": [...],
        "stats": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        service = GroupService()
        
        # Check membership
        if not service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get summary
        summary = service.get_group_summary(group_id)
        
        return jsonify({
            'success': True,
            **summary
        })
        
    except ForbiddenError as e:
        logger.warning("Error in get_group_summary: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting group summary: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get summary'}), 500


# Error handlers
@group_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle validation errors"""
    return jsonify({'success': False, 'error': str(error)}), 400


@group_bp.errorhandler(NotFoundError)
def handle_not_found(error):
    """Handle not found errors"""
    return jsonify({'success': False, 'error': str(error)}), 404


@group_bp.errorhandler(ForbiddenError)
def handle_forbidden(error):
    """Handle forbidden errors"""
    return jsonify({'success': False, 'error': str(error)}), 403


@group_bp.errorhandler(InsufficientPermissionsError)
def handle_insufficient_permissions(error):
    """Handle permission errors"""
    return jsonify({'success': False, 'error': str(error)}), 403


@group_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors"""
    logger.error("Unexpected error: %s", error, exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
