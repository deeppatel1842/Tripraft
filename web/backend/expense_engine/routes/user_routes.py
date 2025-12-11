"""
User Routes - User-Specific API
Handles user groups, balances, and statistics
"""

from flask import Blueprint, request, jsonify
import logging

from ..services.group_service import GroupService
from ..services.balance_service import BalanceService
from ..services.invitation_service import InvitationService
from ..middleware.auth import require_auth, get_current_user_id, get_current_user
from ..exceptions import ValidationError, NotFoundError, ForbiddenError
from ..config import pagination_config

logger = logging.getLogger(__name__)

# Create blueprint
user_bp = Blueprint('expense_users', __name__, url_prefix='/api/expense/user')


@user_bp.route('/groups', methods=['GET'])
@require_auth
def get_user_groups():
    """
    Get all groups for current user
    
    GET /api/expense/user/groups?page=1&limit=20
    
    Response: {
        "success": true,
        "groups": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Validate pagination
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if limit < 1 or limit > pagination_config.MAX_PAGE_SIZE:
            raise ValidationError(f"Limit must be between 1 and {pagination_config.MAX_PAGE_SIZE}")
        
        # Get user groups
        group_service = GroupService()
        groups = group_service.get_user_groups(current_user_id)
        
        return jsonify({
            'success': True,
            'groups': groups if isinstance(groups, list) else [],
            'page': page,
            'limit': limit,
            'has_more': len(groups) == limit if groups else False
        })
        
    except ValidationError as e:
        logger.warning("Error in get_user_groups: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error getting user groups: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get groups'}), 500


@user_bp.route('/groups/<group_id>/balance', methods=['GET'])
@require_auth
def get_user_balance(group_id: str):
    """
    Get user's balance in a specific group
    
    GET /api/expense/user/groups/:gid/balance
    
    Response: {
        "success": true,
        "balance": 50.00,
        "currency": "USD",
        "owed_to": [...],  # List of {user_id, amount, name}
        "owes": [...]      # List of {user_id, amount, name}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get balance
        balance_service = BalanceService()
        balance_data = balance_service.get_user_balance(group_id, current_user_id)
        
        return jsonify({
            'success': True,
            **balance_data
        })
        
    except ForbiddenError as e:
        logger.warning("Error in get_user_balance: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting user balance: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get balance'}), 500


@user_bp.route('/balances', methods=['GET'])
@require_auth
def get_all_user_balances():
    """
    Get user's balances across all groups
    
    GET /api/expense/user/balances
    
    Response: {
        "success": true,
        "balances": [
            {
                "group_id": "group123",
                "group_name": "Trip to Paris",
                "balance": 50.00,
                "currency": "USD"
            },
            ...
        ],
        "total_owed_to_you": 150.00,
        "total_you_owe": 100.00,
        "net_balance": 50.00
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get all user balances
        balance_service = BalanceService()
        balances_data = balance_service.get_all_user_balances(current_user_id)
        
        return jsonify({
            'success': True,
            **balances_data
        })
        
    except Exception as e:
        logger.error("Error getting all user balances: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get balances'}), 500


@user_bp.route('/invitations', methods=['GET'])
@require_auth
def get_user_invitations():
    """
    Get pending invitations for current user
    
    GET /api/expense/user/invitations?page=1&limit=20
    
    Response: {
        "success": true,
        "invitations": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user = get_current_user()
        user_email = current_user.get('email', '')
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Get invitations
        invitation_service = InvitationService()
        invitations = invitation_service.get_user_invitations(
            email=user_email,
            status='pending'
        )
        
        return jsonify({
            'success': True,
            'invitations': invitations if isinstance(invitations, list) else [],
            'page': page,
            'limit': limit,
            'has_more': len(invitations) == limit if invitations else False
        })
        
    except Exception as e:
        logger.error("Error getting user invitations: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get invitations'}), 500


@user_bp.route('/stats', methods=['GET'])
@require_auth
def get_user_stats():
    """
    Get user statistics
    
    GET /api/expense/user/stats
    
    Response: {
        "success": true,
        "stats": {
            "total_groups": 5,
            "total_expenses": 42,
            "total_spent": 1500.00,
            "total_paid": 800.00,
            "pending_invitations": 2,
            "active_settlements": 3
        }
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get user statistics
        group_service = GroupService()
        stats = group_service.get_user_statistics(current_user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error("Error getting user stats: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get statistics'}), 500


@user_bp.route('/recent-activity', methods=['GET'])
@require_auth
def get_recent_activity():
    """
    Get recent activity (expenses, settlements, invitations)
    
    GET /api/expense/user/recent-activity?limit=10
    
    Response: {
        "success": true,
        "activity": [
            {
                "type": "expense",
                "id": "exp123",
                "group_id": "group456",
                "group_name": "Trip to Paris",
                "description": "Dinner",
                "amount": 50.00,
                "timestamp": "2025-11-24T10:30:00Z"
            },
            ...
        ]
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get limit parameter
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            raise ValidationError("Limit must be between 1 and 50")
        
        # Get recent activity
        group_service = GroupService()
        activity = group_service.get_user_recent_activity(current_user_id, limit=limit)
        
        return jsonify({
            'success': True,
            'activity': activity
        })
        
    except ValidationError as e:
        logger.warning("Error in get_recent_activity: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error getting recent activity: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get activity'}), 500


@user_bp.route('/search', methods=['GET'])
@require_auth
def search_user_expenses():
    """
    Search user's expenses across all groups
    
    GET /api/expense/user/search?q=dinner&page=1&limit=20
    
    Response: {
        "success": true,
        "results": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Get search parameters
        query = request.args.get('q', '').strip()
        if not query:
            raise ValidationError("Search query is required")
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Validate pagination
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if limit < 1 or limit > pagination_config.MAX_PAGE_SIZE:
            raise ValidationError(f"Limit must be between 1 and {pagination_config.MAX_PAGE_SIZE}")
        
        # Search expenses
        group_service = GroupService()
        results = group_service.search_user_expenses(
            user_id=current_user_id,
            query=query,
            page=page,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'page': page,
            'limit': limit,
            'has_more': len(results) == limit
        })
        
    except ValidationError as e:
        logger.warning("Error in search_user_expenses: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Error searching expenses: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to search expenses'}), 500


# Error handlers
@user_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'success': False, 'error': str(error)}), 400


@user_bp.errorhandler(NotFoundError)
def handle_not_found(error):
    return jsonify({'success': False, 'error': str(error)}), 404


@user_bp.errorhandler(ForbiddenError)
def handle_forbidden(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@user_bp.errorhandler(Exception)
def handle_generic_error(error):
    logger.error("Unexpected error: %s", error, exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
