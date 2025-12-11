"""
Expense Flat Routes - Expense Management API (Frontend Compatible)
Handles expense CRUD operations with flat URL structure matching frontend expectations
"""

from flask import Blueprint, request, jsonify
from decimal import Decimal
import logging

from ..services.expense_service import ExpenseService
from ..services.group_service import GroupService
from ..services.balance_service import BalanceService
from ..middleware.auth import require_auth, get_current_user_id
from ..exceptions import (
    ValidationError, NotFoundError, ForbiddenError,
    InsufficientPermissionsError
)
from ..config import pagination_config

logger = logging.getLogger(__name__)

# Create blueprint - matches frontend API expectations
expense_flat_bp = Blueprint('expenses_flat', __name__, url_prefix='/api/expense/expenses')


@expense_flat_bp.route('', methods=['POST'])
@require_auth
def create_expense():
    """
    Create new expense
    
    POST /api/expense/expenses
    Body: {
        "group_id": "group123",
        "description": "Dinner at restaurant",
        "amount": 150.00,
        "currency": "USD",
        "paid_by": "user123",
        "split_type": "EQUAL",
        "splits": [
            {"user_id": "user123", "amount": 50.00},
            {"user_id": "user456", "amount": 50.00}
        ],
        "category": "food",
        "date": "2025-01-15",
        "notes": "Optional notes"
    }
    
    Response: {
        "success": true,
        "expense": {...},
        "balances": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        required_fields = ['group_id', 'description', 'amount', 'paid_by', 'split_type', 'splits']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"{field} is required")
        
        group_id = data['group_id']
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Create expense (balance updates handled internally)
        expense_service = ExpenseService()
        
        # Normalize split_type to lowercase
        split_type = data['split_type'].lower() if data.get('split_type') else 'equal'
        
        # Normalize category to lowercase (enum expects lowercase values)
        category = data.get('category')
        if category:
            category = category.lower()
        
        expense = expense_service.create_expense(
            group_id=group_id,
            description=data['description'],
            amount=Decimal(str(data['amount'])),
            paid_by=data['paid_by'],
            split_type=split_type,
            splits=data['splits'],
            created_by=current_user_id,
            currency=data.get('currency', 'USD'),
            category=category,
            notes=data.get('notes'),
            expense_date=data.get('date')
        )
        
        logger.info("Expense created: %s in group %s", expense.get('expense_id'), group_id)
        
        # Normalize expense for frontend compatibility
        normalized_expense = dict(expense) if isinstance(expense, dict) else expense
        normalized_expense['type'] = 'expense'
        if 'expense_date' in normalized_expense and 'date' not in normalized_expense:
            normalized_expense['date'] = normalized_expense['expense_date']
        
        # Get updated balances for optimistic UI - convert dict to array format
        balance_service = BalanceService()
        balances_dict = balance_service.get_group_balances(group_id)
        balances_array = [
            {
                'user_id': user_id,
                'balance': float(balance),
                'net_balance': float(balance)
            }
            for user_id, balance in balances_dict.items()
        ]
        
        return jsonify({
            'success': True,
            'expense': normalized_expense,
            'balances': balances_array
        }), 201
        
    except ValidationError as e:
        logger.warning("Validation error in create_expense: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except ForbiddenError as e:
        logger.warning("Permission error in create_expense: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error creating expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to create expense'}), 500


@expense_flat_bp.route('/<expense_id>', methods=['GET'])
@require_auth
def get_expense(expense_id: str):
    """
    Get expense details
    
    GET /api/expense/expenses/:eid
    
    Response: {
        "success": true,
        "expense": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        expense_service = ExpenseService()
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        # Check group membership
        group_id = expense.get('group_id')
        if group_id:
            group_service = GroupService()
            if not group_service.is_member(group_id, current_user_id):
                raise ForbiddenError("You are not a member of this group")
        
        return jsonify({
            'success': True,
            'expense': expense
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ForbiddenError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get expense'}), 500


@expense_flat_bp.route('/<expense_id>', methods=['PUT'])
@require_auth
def update_expense(expense_id: str):
    """
    Update expense
    
    PUT /api/expense/expenses/:eid
    Body: Partial expense data
    
    Response: {
        "success": true,
        "expense": {...},
        "balances": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        expense_service = ExpenseService()
        
        # Get existing expense to check permissions
        existing = expense_service.get_expense(expense_id)
        if not existing:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        group_id = existing.get('group_id')
        
        # Check permissions
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Permission check:
        # - Group owner can edit ANY expense
        # - Members can only edit their OWN expenses (created_by matches)
        is_owner = group_service.has_permission(group_id, current_user_id, 'edit_expense')
        is_creator = existing.get('created_by') == current_user_id
        
        if not is_owner and not is_creator:
            raise InsufficientPermissionsError("You can only edit your own expenses")
        
        # Normalize split_type if provided
        if 'split_type' in data:
            data['split_type'] = data['split_type'].lower()
        
        # Normalize category if provided
        if 'category' in data and data['category']:
            data['category'] = data['category'].lower()
        
        # Transform frontend field names to backend format
        if 'paidBy' in data:
            data['paid_by'] = data.pop('paidBy')
        
        # Transform splitWith array to splits format
        if 'splitWith' in data:
            split_with = data.pop('splitWith')
            amount = Decimal(str(data.get('amount', existing.get('amount', 0))))
            split_amount = amount / len(split_with) if split_with else amount
            data['splits'] = [
                {'user_id': uid, 'amount': float(split_amount)}
                for uid in split_with
            ]
        
        # Handle date field - frontend sends 'date', backend uses 'expense_date'
        if 'date' in data:
            data['expense_date'] = data.pop('date')
        
        # Remove fields that update_expense doesn't accept
        allowed_fields = {'description', 'amount', 'splits', 'category', 'notes', 'expense_date'}
        data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Update expense
        updated = expense_service.update_expense(
            expense_id=expense_id,
            updated_by=current_user_id,
            **data
        )
        
        # Get updated balances - convert dict to array format
        balance_service = BalanceService()
        balances_dict = balance_service.get_group_balances(group_id)
        balances_array = [
            {
                'user_id': user_id,
                'balance': float(balance),
                'net_balance': float(balance)
            }
            for user_id, balance in balances_dict.items()
        ]
        
        # Normalize expense for frontend compatibility
        normalized_expense = dict(updated) if isinstance(updated, dict) else updated
        normalized_expense['type'] = 'expense'
        if 'expense_date' in normalized_expense and 'date' not in normalized_expense:
            normalized_expense['date'] = normalized_expense['expense_date']
        
        logger.info("Expense updated: %s by %s", expense_id, current_user_id)
        
        return jsonify({
            'success': True,
            'expense': normalized_expense,
            'balances': balances_array
        })
        
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except (ForbiddenError, InsufficientPermissionsError) as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error updating expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update expense'}), 500


@expense_flat_bp.route('/<expense_id>', methods=['DELETE'])
@require_auth
def delete_expense(expense_id: str):
    """
    Delete expense (soft delete)
    
    DELETE /api/expense/expenses/:eid
    
    Response: {
        "success": true,
        "message": "Expense deleted"
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        expense_service = ExpenseService()
        
        # Get existing expense to check permissions
        existing = expense_service.get_expense(expense_id)
        if not existing:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        group_id = existing.get('group_id')
        
        # Check permissions
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Permission check:
        # - Group owner can delete ANY expense
        # - Members can only delete their OWN expenses (created_by matches)
        is_owner = group_service.has_permission(group_id, current_user_id, 'delete_expense')
        is_creator = existing.get('created_by') == current_user_id
        
        if not is_owner and not is_creator:
            raise InsufficientPermissionsError("You can only delete your own expenses")
        
        # Phase 17.5: Use delete_expense_with_deltas for instant UI update
        # Returns balance_deltas and history_entry for frontend cache update
        result = expense_service.delete_expense_with_deltas(expense_id, deleted_by=current_user_id)
        
        logger.info("Expense deleted: %s by %s", expense_id, current_user_id)
        
        # Phase 17.5: Return deltas and history for instant frontend update
        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully',
            'group_id': group_id,
            'balance_deltas': result.get('balance_deltas', {}),
            'history_entry': result.get('history_entry'),
            'deleted_expense': result.get('deleted_expense'),
            # Also include full balances for backward compatibility
            'balances': result.get('balance_deltas', {})
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except (ForbiddenError, InsufficientPermissionsError) as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error deleting expense: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to delete expense'}), 500


@expense_flat_bp.route('/<expense_id>/history', methods=['GET'])
@require_auth
def get_expense_history(expense_id: str):
    """
    Get edit history for an expense (Phase 12)
    
    GET /api/expense/expenses/:eid/history
    
    Response: {
        "success": true,
        "expense_id": "expense123",
        "history": [
            {
                "id": "history123",
                "action": "updated",
                "changed_by": "user123",
                "changed_by_name": "John Doe",
                "changed_at": "2025-11-26T10:30:00Z",
                "changes": [
                    {"field_name": "amount", "old_value": 100, "new_value": 150}
                ]
            }
        ],
        "edit_count": 2
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        expense_service = ExpenseService()
        
        # Get expense to check permissions
        expense = expense_service.get_expense(expense_id)
        if not expense:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        group_id = expense.get('group_id')
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get expense history (single query - no separate edit_count call)
        # Phase 19.5: Removed duplicate get_expense_edit_count call
        history = expense_service.get_expense_history(expense_id)
        
        # Calculate edit_count from history (no extra query needed)
        edit_count = sum(1 for h in history if h.get('action') == 'updated')
        
        return jsonify({
            'success': True,
            'expense_id': expense_id,
            'history': history,
            'edit_count': edit_count
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ForbiddenError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting expense history: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get expense history'}), 500


@expense_flat_bp.route('/group/<group_id>', methods=['GET'])
@require_auth
def get_group_expenses(group_id: str):
    """
    Get expenses for a group with pagination
    
    GET /api/expense/expenses/group/:gid?page=1&limit=20&include_deleted=true
    
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
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get pagination params
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit
        # Get include_deleted param (default: true to show deleted expenses faded)
        include_deleted = request.args.get('include_deleted', 'true').lower() == 'true'
        
        expense_service = ExpenseService()
        result = expense_service.get_group_expenses(
            group_id=group_id,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )
        
        # Handle both dict and list return types
        if isinstance(result, dict):
            expenses = result.get('expenses', [])
        else:
            expenses = result if result else []
        
        return jsonify({
            'success': True,
            'expenses': expenses,
            'page': page,
            'limit': limit,
            'has_more': len(expenses) == limit
        })
        
    except ForbiddenError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting group expenses: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get expenses'}), 500


@expense_flat_bp.route('/<expense_id>/splits', methods=['GET'])
@require_auth
def get_expense_splits(expense_id: str):
    """
    Get splits for an expense
    
    GET /api/expense/expenses/:eid/splits
    
    Response: {
        "success": true,
        "splits": [...]
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        expense_service = ExpenseService()
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            raise NotFoundError(f"Expense {expense_id} not found")
        
        # Check group membership
        group_id = expense.get('group_id')
        if group_id:
            group_service = GroupService()
            if not group_service.is_member(group_id, current_user_id):
                raise ForbiddenError("You are not a member of this group")
        
        splits = expense.get('splits', [])
        
        return jsonify({
            'success': True,
            'splits': splits
        })
        
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ForbiddenError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error getting expense splits: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get splits'}), 500
