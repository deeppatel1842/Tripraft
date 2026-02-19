"""
SQL-based Group Routes
API endpoints for group operations using local SQL database
"""

import logging

from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth)
from app.schemas.common import (CreateExpenseGroupSchema, InviteMemberSchema,
                                validate_request)
from app.services.expense_group_service import group_service_sql
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Use /api/expense/groups to match frontend expectations
groups_sql_bp = Blueprint('groups_sql', __name__, url_prefix='/api/expense/groups')


def parse_group_id(group_id):
    """Parse group ID - handles both int and string"""
    try:
        return int(group_id)
    except (ValueError, TypeError):
        return None


@groups_sql_bp.route('', methods=['POST'])
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
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400
    
    validated, errors = validate_request(CreateExpenseGroupSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.create_group(
        user_id=user_id,
        name=validated['name'],
        description=validated.get('description'),
        currency=validated.get('currency', 'INR'),
        category=validated.get('category')
    )
    
    if success:
        # Get all user groups to return the complete updated list
        all_groups_success, all_groups_result = group_service_sql.get_user_groups(user_id)
        
        response = {
            'success': True,
            'group': result.get('group'),  # The newly created group
            'groups': all_groups_result.get('groups', []) if all_groups_success else []  # All groups
        }
        
        if 'group' in result and 'id' in result['group']:
            response['group_id'] = result['group']['id']
            
        return jsonify(response), 201
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('', methods=['GET'])
@require_auth
def get_my_groups():
    """Get all groups for the current user"""
    user_id = get_current_user_id()
    
    success, result = group_service_sql.get_user_groups(user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>', methods=['GET'])
@require_auth
def get_group(group_id):
    """Get group details"""
    user_id = get_current_user_id()
    gid = parse_group_id(group_id)
    
    if gid is None:
        return jsonify({
            'success': False, 
            'error': 'Invalid group ID'
        }), 400
    
    success, result = group_service_sql.get_group(gid, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 404


@groups_sql_bp.route('/<group_id>/full', methods=['GET'])
@require_auth
def get_group_full(group_id):
    """
    Get complete group details including members, expenses, balances, and invitations
    For frontend compatibility - returns all data needed for group view
    """
    from app.services.expense_invite_service import invitation_service_sql
    from app.services.expense_service import expense_service_sql
    from app.services.settlement_service import settlement_service_sql
    
    user_id = get_current_user_id()
    gid = parse_group_id(group_id)
    
    if gid is None:
        return jsonify({
            'success': False, 
            'error': 'Invalid group ID'
        }), 400
    
    # Get group details
    success, result = group_service_sql.get_group(gid, user_id)
    if not success:
        return jsonify({'success': False, **result}), 404
    
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
    
    return jsonify({'success': True, 'group': group_data}), 200


@groups_sql_bp.route('/<group_id>', methods=['PUT'])
@require_auth
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
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    data = request.get_json() or {}
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
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>', methods=['DELETE'])
@require_auth
def delete_group(group_id):
    """Delete a group (admin only)"""
    gid = parse_group_id(group_id)
    if gid is None:
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.delete_group(gid, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower() or 'admin' in error_msg.lower():
            return jsonify({'success': False, **result}), 403
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id):
    """Get all members of a group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.get_group_members(gid, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>/members', methods=['POST'])
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
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    validated, errors = validate_request(InviteMemberSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Valid email is required'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.add_member(
        group_id=gid,
        user_id=user_id,
        member_email=validated['email'],
        role=data.get('role', 'member')
    )
    
    if success:
        return jsonify({'success': True, **result}), 201
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>/members/<int:member_id>', methods=['DELETE'])
@require_auth
def remove_member(group_id, member_id):
    """Remove a member from the group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.remove_member(gid, user_id, member_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower() or 'admin' in error_msg.lower():
            return jsonify({'success': False, **result}), 403
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/<group_id>/leave', methods=['POST'])
@require_auth
def leave_group(group_id):
    """Leave a group"""
    gid = parse_group_id(group_id)
    if gid is None:
        return jsonify({'success': False, 'error': 'Invalid group ID'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.remove_member(gid, user_id, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@groups_sql_bp.route('/join', methods=['POST'])
@require_auth
def join_group():
    """
    Join a group using invitation code
    
    Request body:
    {
        "code": "ABC12345"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('code'):
        return jsonify({'success': False, 'error': 'Group code is required'}), 400
    
    user_id = get_current_user_id()
    
    success, result = group_service_sql.join_by_code(user_id, data['code'])
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


# Route for invitations by group (for frontend compatibility)
# Note: This is under /api/expense/groups but we need /api/expense/invitations/group/<id>
# We'll add a separate route in auth_routes for this
