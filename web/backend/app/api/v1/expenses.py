"""
SQL-based Expense Routes
API endpoints for expense operations using local SQL database
"""

import logging

from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth)
from app.schemas.common import CreateExpenseSchema, validate_request
from app.services.expense_service import expense_service_sql
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Use /api/expense/expenses to match frontend expectations  
expenses_sql_bp = Blueprint('expenses_sql', __name__, url_prefix='/api/expense/expenses')


@expenses_sql_bp.route('', methods=['GET'])
@require_auth
def list_expenses():
    """
    List all expenses for the current user
    Includes both personal expenses and group expenses
    
    Query params:
    - group_id: optional filter by group
    - limit: number of results (default 50)
    - offset: pagination offset (default 0)
    """
    user_id = get_current_user_id()
    group_id = request.args.get('group_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    if group_id:
        # Get group expenses
        success, result = expense_service_sql.get_group_expenses(
            group_id=group_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
    else:
        # Get all user expenses (personal + group)
        success, result = expense_service_sql.get_user_expenses(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('', methods=['POST'])
@require_auth
def create_expense():
    """
    Create a new expense (TripRaft Model - returns complete state)
    
    Request body:
    {
        "group_id": 1,  // optional - null for personal expenses
        "description": "Dinner at restaurant",
        "amount": 1500.00,
        "paid_by": 1,  // user_id who paid (optional for personal, defaults to current user)
        "split_type": "equal",  // "equal", "exact", "percentage", "shares"
        "splits": [  // optional for equal split
            {"user_id": 1, "amount": 500},  // for exact
            {"user_id": 2, "amount": 500},
            {"user_id": 3, "amount": 500}
        ],
        "category": "food",  // optional
        "expense_date": "2024-01-15T12:00:00Z",  // optional (also accepts "date")
        "notes": "Birthday dinner"  // optional
    }
    
    Response includes:
    - expense: newly created expense
    - expenses: ALL user's expenses (personal + group)
    - group_balances: updated balances if group expense
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400
    
    validated, errors = validate_request(CreateExpenseSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400
    
    user_id = get_current_user_id()
    group_id = validated.get('group_id')  # Can be None for personal expenses
    
    # For personal expenses, paid_by defaults to current user
    paid_by = validated.get('paid_by') or user_id
    if isinstance(paid_by, str) and not paid_by.isdigit():
        paid_by = user_id
    elif isinstance(paid_by, str):
        paid_by = int(paid_by)
    
    # Handle date field (frontend sends "date", backend expects "expense_date")
    expense_date = validated.get('expense_date') or validated.get('date')
    
    # Normalize split_type to lowercase
    split_type = (validated.get('split_type') or 'equal').lower()
    if split_type not in ('equal', 'exact', 'percentage', 'shares', 'none'):
        split_type = 'equal'
    
    success, result = expense_service_sql.create_expense(
        user_id=user_id,
        group_id=group_id,  # Can be None
        description=validated['description'],
        amount=float(validated['amount']),
        paid_by=paid_by,
        split_type=split_type,
        splits=validated.get('splits'),
        category=validated.get('category'),
        expense_date=expense_date,
        notes=validated.get('notes'),
        receipt_url=validated.get('receipt_url'),
        currency=validated.get('currency', 'USD')
    )
    
    if success:
        # Get ALL user expenses to return complete state
        all_expenses_success, all_expenses_result = expense_service_sql.get_user_expenses(
            user_id=user_id,
            limit=100,
            offset=0
        )
        
        response = {
            'success': True,
            'expense': result.get('expense'),
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else [],
            'group_id': group_id
        }
        
        # If group expense, include updated balances
        if group_id and 'balances' in result:
            response['group_balances'] = result.get('balances', [])
        
        return jsonify(response), 201
    else:
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/<int:expense_id>', methods=['GET'])
@require_auth
def get_expense(expense_id):
    """Get expense details"""
    user_id = get_current_user_id()
    
    success, result = expense_service_sql.get_expense(expense_id, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 404


@expenses_sql_bp.route('/<int:expense_id>', methods=['PUT'])
@require_auth
def update_expense(expense_id):
    """
    Update an expense (TripRaft Model - returns complete state)
    
    Request body: (all fields optional)
    {
        "description": "Updated description",
        "amount": 2000.00,
        "paid_by": 2,
        "split_type": "exact",
        "splits": [...],
        "category": "entertainment",
        "expense_date": "2024-01-16T12:00:00Z",
        "notes": "Updated notes"
    }
    
    Response includes:
    - expense: updated expense
    - expenses: ALL user's expenses
    - group_balances: updated balances if group expense
    """
    data = request.get_json() or {}
    user_id = get_current_user_id()
    
    logger.info("UPDATE EXPENSE %s - Request data: %s", expense_id, data)
    
    # Convert paid_by to int if provided
    paid_by_value = int(data['paid_by']) if 'paid_by' in data and data['paid_by'] is not None else None
    
    success, result = expense_service_sql.update_expense(
        expense_id=expense_id,
        user_id=user_id,
        description=data.get('description'),
        amount=float(data['amount']) if 'amount' in data else None,
        paid_by=paid_by_value,
        split_type=data.get('split_type'),
        splits=data.get('splits'),
        category=data.get('category'),
        expense_date=data.get('expense_date'),
        notes=data.get('notes')
    )
    
    if success:
        # Get ALL user expenses to return complete state
        all_expenses_success, all_expenses_result = expense_service_sql.get_user_expenses(
            user_id=user_id,
            limit=100,
            offset=0
        )
        
        response = {
            'success': True,
            'expense': result.get('expense'),
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else []
        }
        
        # Include updated balances if available
        if 'balances' in result:
            response['group_balances'] = result.get('balances', [])
        
        return jsonify(response), 200
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only edit' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower():
            return jsonify({'success': False, **result}), 403
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/<int:expense_id>', methods=['DELETE'])
@require_auth
def delete_expense(expense_id):
    """
    Delete an expense (TripRaft Model - returns complete state)
    
    Response includes:
    - message: confirmation message
    - expenses: remaining expenses (ALL user's expenses)
    - group_balances: updated balances if group expense
    """
    user_id = get_current_user_id()
    
    success, result = expense_service_sql.delete_expense(expense_id, user_id)
    
    if success:
        # Get remaining expenses to return complete state
        all_expenses_success, all_expenses_result = expense_service_sql.get_user_expenses(
            user_id=user_id,
            limit=100,
            offset=0
        )
        
        response = {
            'success': True,
            'message': result.get('message', 'Expense deleted successfully'),
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else []
        }
        
        # Include updated balances if available
        if 'balances' in result:
            response['group_balances'] = result.get('balances', [])
        
        return jsonify(response), 200
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only delete' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower():
            return jsonify({'success': False, **result}), 403
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/group/<int:group_id>', methods=['GET'])
@require_auth
def get_group_expenses(group_id):
    """
    Get expenses for a group
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    - include_deleted: Include deleted expenses (default false)
    """
    user_id = get_current_user_id()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    
    success, result = expense_service_sql.get_group_expenses(
        group_id=group_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
        include_deleted=include_deleted
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/personal', methods=['GET'])
@require_auth
def get_personal_expenses():
    """
    Get personal expenses (not associated with any group)
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    user_id = get_current_user_id()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset,
        personal_only=True
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/user', methods=['GET'])
@require_auth
def get_user_expenses_flexible():
    """
    Get user expenses with flexible filtering
    
    Query params:
    - personal_only: If true, return only personal expenses (default: false)
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    user_id = get_current_user_id()
    personal_only = request.args.get('personal_only', 'false').lower() == 'true'
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset,
        personal_only=personal_only
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@expenses_sql_bp.route('/<int:expense_id>/history', methods=['GET'])
@require_auth
def get_expense_history(expense_id):
    """
    Get expense edit history
    
    Returns list of all changes made to this expense
    """
    user_id = get_current_user_id()
    
    success, result = expense_service_sql.get_expense_history(expense_id, user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 404


@expenses_sql_bp.route('/me', methods=['GET'])
@require_auth
def get_my_expenses():
    """
    Get all expenses involving the current user (personal + group)
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    user_id = get_current_user_id()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400
