# Purpose: SQL-based Group Routes API endpoints for group operations using local SQL database.
"""
SQL-based Group Routes
API endpoints for group operations using local SQL database
"""

import logging

from app.core.apiutils.responses import (created_response, error_response,
                                     success_response,
                                     validation_error_response)
from app.core.apiutils.validators import validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import (get_current_user_id,
                                                require_auth)
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import (CreateExpenseGroupSchema, InviteMemberSchema,
                                validate_request)
from app.core.schemas.expense_groups import (JoinGroupSchema,
                                        UpdateExpenseGroupSchema)
from app.expenses.services.expense_group_service import group_service_sql
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Use /api/expense/groups to match frontend expectations
groups_sql_bp = Blueprint('groups_sql', __name__, url_prefix='/api/v1/expenses/groups')


def parse_group_id(group_id):
    """Parse group ID - validates non-empty string"""
    if group_id:
        return str(group_id)
    return None


def _invalidate_group_caches():
    """Invalidate all expense-group-related caches."""
    invalidate_cache('exp_groups:*')
    invalidate_cache('expenses:*')
    invalidate_cache('settlements:*')
    invalidate_cache('auth:bootstrap:*')


@groups_sql_bp.route('', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def create_group():
    """
    Create a new group
    
    Request body:
    {
        "name": "Trip to Goa",
        "description": "Expenses for Goa trip",  // optional
        "currency": "INR",  // optional, defaults to INR
        "category": "trip"  // optional
    }
    """
    data = request.get_json(silent=True)
    
    if not data:
        return error_response('Request body required')
    
    validated, errors = validate_request(CreateExpenseGroupSchema, data)
    if errors:
        return validation_error_response(errors)
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.create_group(
        user_id=user_id,
        name=validated['name'],
        description=validated.get('description'),
        currency=validated.get('currency', Config.DEFAULT_CURRENCY),
        category=validated.get('category')
    )
    
    if success:
        # Get all user groups to return the complete updated list
        all_groups_success, all_groups_result = group_service_sql.get_user_groups(user_id)
        
        data_payload = {
            'group': result.get('group'),
            'groups': all_groups_result.get('groups', []) if all_groups_success else []
        }
        
        if 'group' in result and 'id' in result['group']:
            data_payload['group_id'] = result['group']['id']
            
        _invalidate_group_caches()
        return created_response(data=data_payload)
    else:
        return error_response(result.get('error', 'Failed to create group'))


@groups_sql_bp.route('', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='exp_groups:list', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_my_groups():
    """Get all groups for the current user"""
    user_id = get_current_user_id()
    
    success, result = group_service_sql.get_user_groups(user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get groups'))


@groups_sql_bp.route('/<group_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='exp_groups:detail', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_group(group_id):
    """Get group details"""
    user_id = get_current_user_id()
    gid = parse_group_id(group_id)
    
    if gid is None:
        return error_response('Invalid group ID')
    
    success, result = group_service_sql.get_group(gid, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Group not found'), 404)


@groups_sql_bp.route('/<group_id>/full', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
@cache_response(key_prefix='exp_groups:full', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_group_full(group_id):
    """
    Get complete group details including members, expenses, balances, and invitations
    For frontend compatibility - returns all data needed for group view
    """
    from app.expenses.services.expense_invite_service import invitation_service_sql
    from app.expenses.services.expense_service import expense_service_sql
    from app.expenses.services.settlement_service import settlement_service_sql
    
    user_id = get_current_user_id()
    gid = parse_group_id(group_id)
    
    if gid is None:
        return error_response('Invalid group ID')
    
    # Get group details
    success, result = group_service_sql.get_group(gid, user_id)
    if not success:
        return error_response(result.get('error', 'Group not found'), 404)
    
    group_data = result.get('group', {})
    
    # Get members
    members_success, members_result = group_service_sql.get_group_members(gid, user_id)
    if members_success:
        group_data['members'] = members_result.get('members', [])
    
    # Get expenses
    expenses_success, expenses_result = expense_service_sql.get_group_expenses(gid, user_id)
    if expenses_success:
        group_data['expenses'] = expenses_result.get('expenses', [])
    
    # Get balances
    balances_success, balances_result = settlement_service_sql.get_group_balances(gid, user_id)
    if balances_success:
        group_data['balances'] = balances_result.get('balances', [])
    
    # Get simplified debts (for simplified UI display)
    debts_success, debts_result = settlement_service_sql.get_simplified_debts(gid, user_id)
    if debts_success:
        group_data['simplified_debts'] = debts_result.get('debts', [])
    
    # Get actual settlements (payment records)
    settlements_success, settlements_result = settlement_service_sql.get_group_settlements(gid, user_id)
    if settlements_success:
        group_data['settlements'] = settlements_result.get('settlements', [])
    
    # Get pending invitations for this group (for the "Pending" tab in GroupManager)
    invitations_success, invitations_result = invitation_service_sql.get_group_invitations(gid, user_id)
    if invitations_success:
        group_data['invitations'] = invitations_result.get('invitations', [])
    
    return success_response(data={'group': group_data})


@groups_sql_bp.route('/<group_id>', methods=['PUT'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdateExpenseGroupSchema)
def update_group(group_id):
    """
    Update group details (admin only)
    
    Request body:
    {
        "name": "New Name",
        "description": "New description",
        "currency": "USD",
        "category": "home"
    }
    """
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    data = g.validated_data
    user_id = get_current_user_id()
    
    success, result = group_service_sql.update_group(
        group_id=gid,
        user_id=user_id,
        name=data.get('name'),
        description=data.get('description'),
        currency=data.get('currency'),
        category=data.get('category')
    )
    
    if success:
        _invalidate_group_caches()
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to update group'))


@groups_sql_bp.route('/<group_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
def delete_group(group_id):
    """Delete a group (admin only)"""
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.delete_group(gid, user_id)
    
    if success:
        _invalidate_group_caches()
        return success_response(data=result)
    else:
        error_msg = result.get('error', '')
        if 'only' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower() or 'admin' in error_msg.lower():
            return error_response(error_msg, 403)
        return error_response(error_msg or 'Failed to delete group')


@groups_sql_bp.route('/<group_id>/members', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='exp_groups:members', ttl=Config.CACHE_TTLS['members'], vary_on_user=True)
def get_group_members(group_id):
    """Get all members of a group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.get_group_members(gid, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get members'))


@groups_sql_bp.route('/<group_id>/members', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def add_member(group_id):
    """
    Add a member to the group (admin only)
    
    Request body:
    {
        "email": "user@example.com",
        "role": "member"  // optional, defaults to "member"
    }
    """
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    data = request.get_json(silent=True)
    
    if not data:
        return error_response('Email is required')
    
    validated, errors = validate_request(InviteMemberSchema, data)
    if errors:
        return error_response('Valid email is required')
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.add_member(
        group_id=gid,
        user_id=user_id,
        member_email=validated['email'],
        role=data.get('role', 'member')
    )
    
    if success:
        return created_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to add member'))


@groups_sql_bp.route('/<group_id>/members/<member_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
def remove_member(group_id, member_id):
    """Remove a member from the group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.remove_member(gid, user_id, member_id)
    
    if success:
        return success_response(data=result)
    else:
        error_msg = result.get('error', '')
        if 'only' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower() or 'admin' in error_msg.lower():
            return error_response(error_msg, 403)
        return error_response(error_msg or 'Failed to remove member')


@groups_sql_bp.route('/<group_id>/leave', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def leave_group(group_id):
    """Leave a group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.remove_member(gid, user_id, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to leave group'))


@groups_sql_bp.route('/join', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@validate_schema(JoinGroupSchema)
def join_group():
    """
    Join a group using invitation code
    
    Request body:
    {
        "code": "ABC12345"
    }
    """
    data = g.validated_data
    user_id = get_current_user_id()
    
    success, result = group_service_sql.join_by_code(user_id, data['code'])
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to join group'))


# Route for invitations by group (for frontend compatibility)
# Note: This is under /api/expense/groups but we need /api/expense/invitations/group/<id>
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
# We'll add a separate route in auth_routes for this
