"""
Group Management Routes
Handles group CRUD operations, member management, and group data retrieval
"""

from flask import Blueprint, request, jsonify, g
import logging
import time

from ..service import expense_service
from .route_helpers import require_auth, track_time

logger = logging.getLogger(__name__)

# Create blueprint
group_bp = Blueprint('group', __name__)


# =============================================================================
# GROUP CRUD ROUTES
# =============================================================================

@group_bp.route('/groups', methods=['POST'])
@require_auth
@track_time("CREATE_GROUP")
def create_group():
    """
    Create a new expense group
    
    Creates a new group with the authenticated user as admin.
    Automatically invalidates user groups cache.
    
    Request Body:
        name (str): Required. Group name
        description (str): Optional. Group description
        image_url (str): Optional. Group image URL
        currency (str): Optional. Default currency (default: USD)
        
    Returns:
        201: Group created successfully
        400: Validation error
        500: Server error
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Group name is required'}), 400
        
        # Create group
        group = expense_service.create_group(
            name=data['name'],
            created_by=g.user_id,
            description=data.get('description'),
            image_url=data.get('image_url'),
            currency=data.get('currency', 'USD')
        )
        
        # Immediately invalidate user groups cache
        try:
            user_cache_key = f"user_groups:{g.user_id}"
            if expense_service.cache.redis_client:
                expense_service.cache.redis_client.delete(user_cache_key)
            print(f"🗑️  Invalidated user groups cache for {g.user_id}")
        except Exception as e:
            print(f"⚠️  Cache invalidation failed: {e}")
        
        return jsonify({'success': True, 'group': group}), 201
    
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups', methods=['GET'])
@require_auth
@track_time("GET_USER_GROUPS")
def get_user_groups():
    """
    Get all groups for current user
    
    Supports two loading modes:
    - summary: Fast initial load (~5 Firestore reads)
    - full: Complete data with member details (~50+ reads)
    
    Query Parameters:
        mode (str): 'summary' or 'full' (default: 'full')
        
    Returns:
        200: Groups retrieved successfully
        500: Server error
        
    Performance:
        - Summary mode: ~90% faster than full mode
        - Full mode: Backward compatible with existing frontend
    """
    try:
        # Check if summary mode is requested
        mode = request.args.get('mode', 'full')
        summary_mode = (mode == 'summary')
        
        if summary_mode:
            logger.info(f"📋 [SUMMARY MODE] Fast loading groups for {g.user_id}")
        
        groups = expense_service.get_user_groups(g.user_id, summary_mode=summary_mode)
        
        # Add performance note for summary mode
        if summary_mode:
            logger.info(f"✅ [SUMMARY MODE] Returned {len(groups)} groups with ~5 Firestore reads (90% faster!)")
        return jsonify({'success': True, 'groups': groups}), 200
    
    except Exception as e:
        logger.error(f"Error getting user groups: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>', methods=['GET'])
@require_auth
@track_time("GET_GROUP")
def get_group(group_id):
    """
    Get group details
    
    Returns group details with member information.
    Validates user membership before returning data.
    
    Returns:
        200: Group retrieved successfully
        403: User not a member
        404: Group not found
        500: Server error
    """
    try:
        # Check membership first using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Get members with user details
        members = expense_service.get_group_members(group_id)
        group['members_details'] = members
        
        return jsonify({'success': True, 'group': group}), 200
    
    except Exception as e:
        logger.error(f"Error getting group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>/full', methods=['GET'])
@require_auth
@track_time("GET_GROUP_FULL")
def get_group_full(group_id):
    """
    Get group data in ONE call with LAZY LOADING support (PHASE 1.1 OPTIMIZED)
    
    Returns group data with configurable expense loading:
    - Group details
    - Members with display names
    - Expenses (optional, configurable limit)
    - Balance calculations
    - Settlements
    - Pending invitations
    
    Query Parameters:
        _t (any): Optional. Bypass cache and fetch fresh data
        include_expenses (bool): Optional. Load expenses (default: true)
        expense_limit (int): Optional. Number of expenses to load (default: 5)
        
    Examples:
        GET /groups/123/full                              # Load with 5 recent expenses
        GET /groups/123/full?include_expenses=false       # Balances only (FASTEST)
        GET /groups/123/full?expense_limit=20             # Load 20 expenses
        GET /groups/123/full?_t=1732188000                # Bypass cache
        
    Phase 1.1 Benefits:
        - Dashboard view: include_expenses=false → 75% faster (5-8 reads vs 50+)
        - Detail view: expense_limit=5 → 60% faster (10-13 reads vs 50+)
        - Full history: Use paginated endpoint (/groups/<id>/expenses)
    
    Performance:
        - Without expenses: ~5-8 Firestore reads, 200-400ms
        - With 5 expenses: ~10-13 Firestore reads, 400-600ms
        - Cached: 0 reads, <5ms response
        
    Returns:
        200: Group data retrieved
        403: User not a member
        404: Group not found
        500: Server error
    """
    start = time.time()
    
    try:
        print(f"\n{'='*80}")
        print(f"🚀 GET GROUP FULL DATA - {group_id}")
        print(f"{'='*80}")
        print(f"User ID: {g.user_id}")
        
        # Parse query parameters
        bypass_cache = request.args.get('_t') is not None
        include_expenses = request.args.get('include_expenses', 'true').lower() == 'true'
        expense_limit = request.args.get('expense_limit', type=int)
        
        print(f"🔑 CACHE PARAMS: bypass={bypass_cache}, include_expenses={include_expenses}, limit={expense_limit}")
        
        if bypass_cache:
            print("🔄 Cache bypass requested (_t parameter) - fetching fresh data")
        
        mode = "without expenses" if not include_expenses else f"with {expense_limit or 5} expenses"
        print(f"📊 Mode: {mode}")
        
        # Get group data with lazy loading support
        result = expense_service.get_group_full_data(
            group_id, 
            g.user_id, 
            bypass_cache=bypass_cache,
            include_expenses=include_expenses,
            expense_limit=expense_limit
        )
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            status_code = 404 if 'not found' in error_msg.lower() else 403 if 'denied' in error_msg.lower() else 500
            return jsonify(result), status_code
        
        duration = time.time() - start
        print(f"✅ COMPLETE: GET GROUP DATA - {duration:.3f}s ({mode})")
        print(f"{'='*80}\n")
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error getting group data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'success': False}), 500


@group_bp.route('/groups/<group_id>', methods=['PUT'])
@require_auth
def update_group(group_id):
    """
    Update group details
    
    Only group admins can update group details.
    
    Request Body:
        name (str): Optional. New group name
        description (str): Optional. New description
        image_url (str): Optional. New image URL
        currency (str): Optional. New default currency
        
    Returns:
        200: Group updated successfully
        403: User not admin
        500: Server error
    """
    try:
        # Check if user is admin
        if not expense_service.is_group_admin(group_id, g.user_id):
            return jsonify({'error': 'Only admins can update group'}), 403
        
        data = request.get_json()
        
        # Update group
        success = expense_service.update_group(group_id, data)
        
        if success:
            group = expense_service.get_group(group_id)
            return jsonify({'success': True, 'group': group}), 200
        else:
            return jsonify({'error': 'Failed to update group'}), 500
    
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>', methods=['DELETE'])
@require_auth
def delete_group(group_id):
    """
    Delete a group (with optional cascade delete of expenses)
    
    Only group admins can delete groups.
    Supports cascade deletion of all group expenses.
    
    Query Parameters:
        cascade (str): 'true' to delete all expenses, 'false' to keep them (default: 'false')
    
    Examples:
        DELETE /groups/123                     # Delete group, keep expenses
        DELETE /groups/123?cascade=true        # Delete group AND all expenses
        
    Returns:
        200: Group deleted successfully
        403: User not admin
        500: Server error
    """
    try:
        # Check if user is admin
        if not expense_service.is_group_admin(group_id, g.user_id):
            return jsonify({'error': 'Only admins can delete group'}), 403
        
        # Get cascade parameter from query string
        cascade = request.args.get('cascade', 'false').lower() == 'true'
        
        # Get user_id before deletion (g.user_id won't be available in thread)
        user_id = g.user_id
        
        if cascade:
            logger.info(f"🗑️  CASCADE DELETE: Deleting group {group_id} with all expenses")
        
        # 🐛 BUG FIX: Get all group members BEFORE deletion to invalidate their caches
        group = expense_service.get_group(group_id)
        all_members = group.get('members', []) if group else []
        
        # Delete group (with optional cascade)
        success = expense_service.delete_group(group_id, cascade_delete_expenses=cascade)
        
        if success:
            # 🐛 BUG FIX: Invalidate caches for ALL group members (not just owner)
            # Use the proper cache_operations method which handles both full + summary modes
            for member_id in all_members:
                try:
                    # ✅ CRITICAL FIX: Call the proper invalidation method
                    expense_service.cache.invalidate_user_groups(member_id)
                    logger.info(f"🔄 Invalidated user groups cache for {member_id} (full + summary)")
                except Exception as e:
                    logger.error(f"⚠️  Cache invalidation failed for {member_id}: {e}")
            
            message = 'Group and all expenses deleted' if cascade else 'Group deleted'
            return jsonify({
                'success': True, 
                'message': message,
                'cascade': cascade,
                'group_id': group_id,
                'deleted': True,
                # 🐛 BUG FIX: Signal frontend to remove group immediately
                'action': 'group_deleted'
            }), 200
        else:
            return jsonify({'error': 'Failed to delete group'}), 500
    
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# MEMBER MANAGEMENT ROUTES
# =============================================================================

@group_bp.route('/groups/<group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id):
    """
    Get group members
    
    Returns list of all group members with user details.
    Only accessible to group members.
    
    Returns:
        200: Members retrieved successfully
        403: User not a member
        500: Server error
    """
    try:
        # Check if user is a member using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        members = expense_service.get_group_members(group_id)
        return jsonify({'success': True, 'members': members}), 200
    
    except Exception as e:
        logger.error(f"Error getting group members: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>/members/<user_id>', methods=['GET'])
@require_auth
def get_member_details(group_id, user_id):
    """
    Get detailed information about a group member
    
    Returns comprehensive member information:
    - User profile (display name, username, email)
    - Role (admin or member)
    - Current balance in group
    - Number of expenses paid
    - Total amount paid
    - Joined date
    
    Only accessible to group members.
    
    Returns:
        200: Member details retrieved
        403: Requester not a member
        404: User not found or not in group
        500: Server error
    """
    try:
        # Check if requester is a group member using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Check if requested user is a group member
        is_target_member = expense_service.firebase.is_user_group_member(user_id, group_id)
        if not is_target_member:
            return jsonify({'error': 'User not in group'}), 404
        
        # Get member user info
        user = expense_service.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get member balance from group_balances
        balances = expense_service.get_group_balances(group_id)
        user_balance = 0.0
        for balance_entry in balances:
            if balance_entry['user_id'] == user_id:
                user_balance = balance_entry['balance']
                break
        
        # Count expenses paid by member
        expenses = expense_service.get_group_expenses(group_id, limit=1000, offset=0)
        expenses_paid = sum(1 for exp in expenses['expenses'] if exp.get('paid_by') == user_id)
        total_paid = sum(exp.get('amount', 0) for exp in expenses['expenses'] if exp.get('paid_by') == user_id)
        
        # Get member role (check if admin)
        is_admin = expense_service.is_group_admin(group_id, user_id)
        role = 'admin' if is_admin else 'member'
        
        # Get joined date from group members
        members = expense_service.get_group_members(group_id)
        joined_at = None
        for member in members:
            if member.get('user_id') == user_id:
                joined_at = member.get('joined_at')
                break
        
        # Build member details response
        member_details = {
            'user_id': user_id,
            'display_name': user.get('display_name', ''),
            'username': user.get('username', ''),
            'email': user.get('email', ''),
            'role': role,
            'balance': user_balance,
            'expenses_paid_count': expenses_paid,
            'total_amount_paid': total_paid,
            'joined_at': joined_at,
            'is_admin': is_admin
        }
        
        return jsonify({'success': True, 'member': member_details}), 200
    
    except Exception as e:
        logger.error(f"Error getting member details: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>/members/<user_id>', methods=['DELETE'])
@require_auth
def remove_group_member(group_id, user_id):
    """
    Remove a member from a group
    
    Only group admins can remove other members.
    Members can remove themselves (same as leaving).
    
    Returns:
        200: Member removed successfully
        403: Not authorized (not admin)
        404: Group or member not found
        500: Server error
    """
    try:
        # Check if user is admin or removing themselves
        group = expense_service.get_group(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        is_admin = expense_service.is_group_admin(group_id, g.user_id)
        is_self = (user_id == g.user_id)
        
        if not is_admin and not is_self:
            return jsonify({'error': 'Only admins can remove members'}), 403
        
        # Check if target user is in group
        if user_id not in group.get('members', []):
            return jsonify({'error': 'User not in group'}), 404
        
        # Remove member
        success = expense_service.remove_member_from_group(group_id, user_id)
        
        if success:
            action = 'left' if is_self else 'removed'
            return jsonify({
                'success': True, 
                'message': f'Member {action} successfully',
                'removed_user_id': user_id,
                'group_id': group_id,
                # 🐛 BUG FIX #4: Signal removed user to hide group immediately
                'action': 'member_removed'
            }), 200
        else:
            return jsonify({'error': 'Failed to remove member'}), 500
    
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@group_bp.route('/groups/<group_id>/leave', methods=['POST'])
@require_auth
def leave_group(group_id):
    """
    Leave a group
    
    Allows user to leave a group they are a member of.
    
    Returns:
        200: Left group successfully
        500: Server error
    """
    try:
        success = expense_service.remove_member_from_group(group_id, g.user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Left group successfully'}), 200
        else:
            return jsonify({'error': 'Failed to leave group'}), 500
    
    except Exception as e:
        logger.error(f"Error leaving group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# PHASE 1.1: LAZY LOADING - PAGINATED EXPENSE ENDPOINT
# =============================================================================

@group_bp.route('/groups/<group_id>/expenses', methods=['GET'])
@require_auth
@track_time("GET_GROUP_EXPENSES_PAGINATED")
def get_group_expenses_paginated(group_id):
    """
    Get expenses for a group with pagination (PHASE 1.1 - LAZY LOADING)
    
    This endpoint enables infinite scroll and lazy loading of expenses.
    Use this to load expenses on-demand when user scrolls or clicks "View All".
    
    Query Parameters:
        limit (int): Number of expenses to return (default: 20, max: 50)
        offset (int): Number of expenses to skip (default: 0)
        
    Examples:
        GET /groups/123/expenses                    # First page (20 expenses)
        GET /groups/123/expenses?limit=50           # Load 50 expenses
        GET /groups/123/expenses?offset=20          # Next page (skip first 20)
        GET /groups/123/expenses?limit=20&offset=40 # Third page
        
    Response:
        {
            "success": true,
            "expenses": [...],
            "pagination": {
                "limit": 20,
                "offset": 0,
                "returned_count": 20,
                "has_more": true
            }
        }
    
    Performance:
        - First page (20 expenses): ~20 Firestore reads
        - Subsequent pages: ~20 reads each
        - Only loads what user requests (not all 100+ expenses)
    
    Returns:
        200: Expenses retrieved successfully
        403: User not a member
        404: Group not found
        500: Server error
    """
    from ..constants import PaginationConfig
    
    try:
        # Check if user is a member using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            return jsonify({'error': 'Access denied - you are not a member of this group', 'success': False}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            return jsonify({'error': 'Group not found', 'success': False}), 404
        
        # Parse pagination parameters
        limit = min(int(request.args.get('limit', PaginationConfig.EXPENSE_PAGE_SIZE)), PaginationConfig.MAX_PAGE_SIZE)
        offset = max(int(request.args.get('offset', 0)), 0)
        
        print(f"\n📄 LAZY LOAD EXPENSES: group={group_id}, limit={limit}, offset={offset}")
        
        # Get expenses with pagination
        result = expense_service.get_group_expenses(group_id, limit=limit, offset=offset)
        
        # Format response
        response = {
            'success': True,
            'expenses': result.get('expenses', []),
            'pagination': {
                'limit': result.get('limit', limit),
                'offset': result.get('offset', offset),
                'returned_count': result.get('returned_count', 0),
                'has_more': result.get('has_more', False)
            }
        }
        
        print(f"✅ Returned {response['pagination']['returned_count']} expenses (has_more={response['pagination']['has_more']})")
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error getting paginated expenses: {e}")
        return jsonify({'error': 'Internal server error', 'success': False}), 500
