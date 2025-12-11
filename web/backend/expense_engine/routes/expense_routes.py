"""
Expense Routes - Expense Management API
Handles expense CRUD operations with balance updates
"""

from flask import Blueprint, request, jsonify
from decimal import Decimal
import logging

from ..services.expense_service import ExpenseService
from ..services.group_service import GroupService
from ..middleware.auth import require_auth, get_current_user_id
from ..exceptions import (
    ValidationError, NotFoundError, ForbiddenError,
    InsufficientPermissionsError
)
from ..config import pagination_config, redis_config

# Import cache manager
try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager(): return None

logger = logging.getLogger(__name__)


def invalidate_group_cache(group_id: str):
    """Invalidate cache for a group after expense changes"""
    if not CACHE_ENABLED:
        return
    try:
        cache = get_cache_manager()
        if cache:
            cache_key = redis_config.KEY_GROUP_SUMMARY.format(gid=group_id)
            cache.delete(cache_key)
            logger.info("Cache invalidated for group %s", group_id)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to invalidate cache: %s", e)


# Create blueprint
expense_bp = Blueprint('expenses', __name__, url_prefix='/api/expense/groups/<group_id>/expenses')


@expense_bp.route('', methods=['POST'])
@require_auth
def create_expense(group_id: str):
    """
    Create new expense
    
    POST /api/expense/groups/:gid/expenses
    Body: {
        "description": "Dinner at restaurant",
        "amount": 150.00,
        "currency": "USD",
        "paid_by": "user123",
        "split_type": "equal",
        "splits": [
            {"user_id": "user123", "amount": 50.00},
            {"user_id": "user456", "amount": 50.00},
            {"user_id": "user789", "amount": 50.00}
        ],
        "category": "food",
        "notes": "Optional notes",
        "receipt_url": "https://..."
    }
    
    Response: {
        "success": true,
        "expense": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        required_fields = ['description', 'amount', 'paid_by', 'split_type', 'splits']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"{field} is required")
        
        # Check group membership
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Create expense with Phase 17 deltas (balance updates handled internally)
        expense_service = ExpenseService()
        
        result = expense_service.create_expense_with_deltas(
            group_id=group_id,
            description=data['description'],
            amount=Decimal(str(data['amount'])),
            paid_by=data['paid_by'],
            split_type=data['split_type'],
            splits=data['splits'],
            created_by=current_user_id,
            currency=data.get('currency', 'USD'),
            category=data.get('category'),
            notes=data.get('notes')
        )
        
        # Invalidate group cache after expense creation
        invalidate_group_cache(group_id)
        
        expense = result['expense']
        logger.info("Expense created: %s in group %s", expense.get('expense_id'), group_id)
        
        # Phase 17: Return expense + balance_deltas + history_entry
        # Frontend applies deltas to existing balances (no refetch needed)
        return jsonify({
            'success': True,
            'expense': expense,
            'balance_deltas': result['balance_deltas'],
            'history_entry': result['history_entry']
        }), 201
        
    except ValidationError as e:
        logger.warning("Validation error in create_expense: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except ForbiddenError as e:
        logger.warning("Permission error in create_expense: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error creating expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to create expense'}), 500


@expense_bp.route('/<expense_id>', methods=['GET'])
@require_auth
def get_expense(group_id: str, expense_id: str):
    """
    Get expense details
    
    GET /api/expense/groups/:gid/expenses/:eid
    
    Response: {
        "success": true,
        "expense": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get expense
        expense_service = ExpenseService()
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            raise NotFoundError("Expense not found")
        
        if expense['group_id'] != group_id:
            raise ForbiddenError("Expense does not belong to this group")
        
        return jsonify({
            'success': True,
            'expense': expense
        })
        
    except (NotFoundError, ForbiddenError) as e:
        logger.warning("Error in get_expense: %s", e)
        status = 404 if isinstance(e, NotFoundError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error getting expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get expense'}), 500


@expense_bp.route('', methods=['GET'])
@require_auth
def list_expenses(group_id: str):
    """
    List expenses with pagination
    
    GET /api/expense/groups/:gid/expenses?page=1&limit=20
    
    Response: {
        "success": true,
        "expenses": [...],
        "page": 1,
        "limit": 20,
        "has_more": true
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Validate pagination
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if limit < 1 or limit > pagination_config.MAX_PAGE_SIZE:
            raise ValidationError(f"Limit must be between 1 and {pagination_config.MAX_PAGE_SIZE}")
        
        # Get expenses (service uses offset, not page)
        offset = (page - 1) * limit
        expense_service = ExpenseService()
        result = expense_service.get_group_expenses(group_id, limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'expenses': result['expenses'],
            'page': page,
            'limit': limit,
            'has_more': result.get('has_more', False)
        })
        
    except (ValidationError, ForbiddenError) as e:
        logger.warning("Error in list_expenses: %s", e)
        status = 400 if isinstance(e, ValidationError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error listing expenses: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to list expenses'}), 500


@expense_bp.route('/<expense_id>', methods=['PATCH'])
@require_auth
def update_expense(group_id: str, expense_id: str):
    """
    Update expense
    
    PATCH /api/expense/groups/:gid/expenses/:eid
    Body: {
        "description"?: "Updated description",
        "amount"?: 200.00,
        "splits"?: [...],
        "category"?: "food",
        "notes"?: "Updated notes"
    }
    
    Response: {
        "success": true,
        "expense": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Check group membership
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get old expense
        expense_service = ExpenseService()
        old_expense = expense_service.get_expense(expense_id)
        
        if not old_expense:
            raise NotFoundError("Expense not found")
        
        if old_expense['group_id'] != group_id:
            raise ForbiddenError("Expense does not belong to this group")
        
        # Check permissions (creator or admin)
        if old_expense['created_by'] != current_user_id:
            if not group_service.has_permission(group_id, current_user_id, 'edit_expense'):
                raise InsufficientPermissionsError("You can only edit your own expenses")
        
        # Update expense with Phase 17 deltas (balance updates handled internally in transaction)
        result = expense_service.update_expense_with_deltas(
            expense_id=expense_id,
            updated_by=current_user_id,
            description=data.get('description'),
            amount=Decimal(str(data['amount'])) if 'amount' in data else None,
            paid_by=data.get('paid_by'),  # Include paid_by in update
            splits=data.get('splits'),
            category=data.get('category'),
            notes=data.get('notes')
        )
        
        # Invalidate group cache after expense update
        invalidate_group_cache(group_id)
        
        logger.info("Expense updated: %s by user %s", expense_id, current_user_id)
        
        # Phase 17: Return expense + balance_deltas + history_entry
        # Frontend applies deltas to existing balances (no refetch needed)
        return jsonify({
            'success': True,
            'expense': result['expense'],
            'balance_deltas': result['balance_deltas'],
            'history_entry': result['history_entry']
        })
        
    except (ValidationError, NotFoundError, ForbiddenError, InsufficientPermissionsError) as e:
        logger.warning("Error in update_expense: %s", e)
        status_map = {
            ValidationError: 400,
            NotFoundError: 404,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 400)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error updating expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update expense'}), 500


@expense_bp.route('/<expense_id>', methods=['DELETE'])
@require_auth
def delete_expense(group_id: str, expense_id: str):
    """
    Delete expense (soft delete)
    
    DELETE /api/expense/groups/:gid/expenses/:eid
    
    Response: {
        "success": true,
        "message": "Expense deleted successfully"
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get expense
        expense_service = ExpenseService()
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            raise NotFoundError("Expense not found")
        
        if expense['group_id'] != group_id:
            raise ForbiddenError("Expense does not belong to this group")
        
        # Check permissions (creator or admin)
        if expense['created_by'] != current_user_id:
            if not group_service.has_permission(group_id, current_user_id, 'delete_expense'):
                raise InsufficientPermissionsError("You can only delete your own expenses")
        
        # Delete expense with Phase 17 deltas (balance reversal handled internally)
        result = expense_service.delete_expense_with_deltas(expense_id, current_user_id)
        
        # Invalidate group cache after expense deletion
        invalidate_group_cache(group_id)
        
        logger.info("Expense deleted: %s by user %s", expense_id, current_user_id)
        
        # Phase 17: Return balance_deltas + history_entry
        # Frontend applies deltas to existing balances (no refetch needed)
        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully',
            'balance_deltas': result['balance_deltas'],
            'history_entry': result['history_entry'],
            'deleted_expense': result['deleted_expense']
        })
        
    except (NotFoundError, ForbiddenError, InsufficientPermissionsError) as e:
        logger.warning("Error in delete_expense: %s", e)
        status_map = {
            NotFoundError: 404,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 404)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error deleting expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to delete expense'}), 500


# =============================================================================
# Phase 12: Expense History Endpoints (Phase 19.1: Added Redis caching)
# =============================================================================

@expense_bp.route('/<expense_id>/history', methods=['GET'])
@require_auth
def get_expense_history(group_id: str, expense_id: str):
    """
    Get edit history for an expense
    
    Phase 19.1: Added Redis caching with 5 minute TTL
    - Reduces Firestore reads from 4R to 0R on cache hit
    - Cache is invalidated when expense is updated
    
    GET /api/expense/groups/:gid/expenses/:expense_id/history
    Query params:
        - limit: Maximum entries (default 50)
        - include_snapshots: Include full before/after data (default false)
    
    Response: {
        "success": true,
        "expense_id": "exp123",
        "is_edited": true,
        "edit_count": 3,
        "history": [
            {
                "id": "hist_123",
                "action": "updated",
                "changed_by": "user456",
                "changed_by_name": "John Doe",
                "changed_at": "2025-11-26T10:30:00Z",
                "summary": "Updated amount, category",
                "changes": [
                    {"field": "amount", "old": "$100.00", "new": "$150.00"},
                    {"field": "category", "old": "Food", "new": "Transport"}
                ]
            },
            {
                "id": "hist_122",
                "action": "created",
                "changed_by": "user123",
                "changed_at": "2025-11-25T14:00:00Z",
                "summary": "Created expense"
            }
        ]
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership (uses cached membership check)
        # pylint: disable=no-value-for-parameter
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get query params
        limit = request.args.get('limit', 50, type=int)
        include_snapshots = request.args.get('include_snapshots', 'false').lower() == 'true'
        
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 50
        
        # Phase 19.1: Try cache first (only for default params without snapshots)
        cache_key = None
        if CACHE_ENABLED and not include_snapshots and limit == 50:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_EXPENSE_HISTORY.format(eid=expense_id)
                cached_response = cache.get(cache_key)
                if cached_response:
                    logger.debug("[CACHE][+] Expense history cache hit: %s", expense_id)
                    return jsonify(cached_response)
                logger.debug("[CACHE][-] Expense history cache miss: %s", expense_id)
        
        # Get expense to verify it exists and belongs to group
        expense_service = ExpenseService()
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        if expense.get('group_id') != group_id:
            raise ForbiddenError("Expense does not belong to this group")
        
        # Get history from Firestore
        history = expense_service.get_expense_history(
            expense_id=expense_id,
            limit=limit,
            include_snapshots=include_snapshots
        )
        
        # Format for frontend
        formatted_history = []
        for entry in history:
            formatted = {
                'id': entry.get('id'),
                'action': entry.get('action'),
                'changed_by': entry.get('changed_by'),
                'changed_by_name': entry.get('changed_by_name'),
                'changed_at': entry.get('changed_at'),
                'summary': _format_history_summary(entry),
                'changes': _format_changes(entry.get('changes', []))
            }
            if include_snapshots:
                formatted['before_snapshot'] = entry.get('before_snapshot')
                formatted['after_snapshot'] = entry.get('after_snapshot')
            formatted_history.append(formatted)
        
        # Calculate edit count (only "updated" actions count as edits)
        edit_count = sum(1 for h in history if h.get('action') == 'updated')
        
        response = {
            'success': True,
            'expense_id': expense_id,
            'is_edited': edit_count > 0,
            'edit_count': edit_count,
            'history': formatted_history
        }
        
        # Phase 19.1: Cache the response (only for default params)
        if cache_key:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, response, ttl=redis_config.TTL_EXPENSE_HISTORY)
                logger.debug("[CACHE] Expense history cached: %s", expense_id)
        
        return jsonify(response)
        
    except (NotFoundError, ForbiddenError) as e:
        status_code = 404 if isinstance(e, NotFoundError) else 403
        return jsonify({'success': False, 'error': str(e)}), status_code
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error getting expense history: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get expense history'}), 500


def _format_history_summary(entry: dict) -> str:
    """Format a human-readable summary of the history entry"""
    action = entry.get('action', 'unknown')
    if action == 'created':
        return 'Created expense'
    elif action == 'deleted':
        return 'Deleted expense'
    elif action == 'restored':
        return 'Restored expense'
    elif action == 'updated':
        changes = entry.get('changes', [])
        if not changes:
            return 'Updated expense'
        field_names = [c.get('field_name', c.get('field', '')) for c in changes]
        if len(field_names) == 1:
            return f"Updated {field_names[0]}"
        elif len(field_names) <= 3:
            return f"Updated {', '.join(field_names)}"
        else:
            return f"Updated {len(field_names)} fields"
    return f"Unknown action: {action}"


def _format_changes(changes: list) -> list:
    """Format changes for frontend display"""
    formatted = []
    for change in changes:
        # Handle both FieldChange objects and dicts
        if hasattr(change, 'to_display_dict'):
            formatted.append(change.to_display_dict())
        else:
            formatted.append({
                'field': change.get('field_name', change.get('field', '')),
                'old': _format_value(change.get('old_value', change.get('old'))),
                'new': _format_value(change.get('new_value', change.get('new')))
            })
    return formatted


def _format_value(value) -> str:
    """Format a value for display"""
    if value is None:
        return 'None'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value == int(value):
            return f"${int(value):.2f}"
        return f"${value:.2f}"
    if isinstance(value, list):
        return f"{len(value)} items"
    return str(value)


# Error handlers
@expense_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'success': False, 'error': str(error)}), 400


@expense_bp.errorhandler(NotFoundError)
def handle_not_found(error):
    return jsonify({'success': False, 'error': str(error)}), 404


@expense_bp.errorhandler(ForbiddenError)
def handle_forbidden(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@expense_bp.errorhandler(InsufficientPermissionsError)
def handle_insufficient_permissions(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@expense_bp.errorhandler(Exception)
def handle_generic_error(error):
    logger.error("Unexpected error: %s", error, exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
