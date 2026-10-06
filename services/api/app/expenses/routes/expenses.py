# Purpose: SQL-based Expense Routes API endpoints for expense operations using local SQL database.
"""
SQL-based Expense Routes
API endpoints for expense operations using local SQL database
"""

import logging

from app.core.apiutils.responses import (created_response, error_response,
                                     success_response)
from app.core.apiutils.validators import parse_query_int, validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import (get_current_user_id,
                                                require_auth)
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import CreateExpenseSchema, validate_request
from app.core.schemas.expenses import UpdateExpenseSchema
from app.expenses.services.expense_service import expense_service_sql
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Use /api/expense/expenses to match frontend expectations  
expenses_sql_bp = Blueprint('expenses_sql', __name__, url_prefix='/api/v1/expenses')


@expenses_sql_bp.route('', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:list', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
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
    group_id = request.args.get('group_id')
    limit = parse_query_int('limit', Config.EXPENSE_DEFAULT_LIMIT, minimum=1, maximum=100)
    offset = parse_query_int('offset', 0, minimum=0)
    
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
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to fetch expenses'))


@expenses_sql_bp.route('', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
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
    data = request.get_json(silent=True)
    
    if not data:
        return error_response('Request body required')
    
    validated, errors = validate_request(CreateExpenseSchema, data)
    if errors:
        return error_response('Validation failed', 400, errors={'details': errors})
    
    user_id = get_current_user_id()
    group_id = validated.get('group_id')  # Can be None for personal expenses
    
    # paid_by is a UUID string validated by the schema; the service checks
    # that the payer is a member of the group. Defaults to the caller.
    paid_by = validated.get('paid_by') or user_id
    
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
        amount=validated['amount'],
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
        
        response_data = {
            'expense': result.get('expense'),
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else [],
            'group_id': group_id
        }
        
        # If group expense, include updated balances
        if group_id and 'balances' in result:
            response_data['group_balances'] = result.get('balances', [])
        
        _invalidate_expense_caches()
        return created_response(data=response_data, message='Expense created')
    else:
        return error_response(result.get('error', 'Failed to create expense'))


def _invalidate_expense_caches():
    """Invalidate all expense-related caches."""
    invalidate_cache('expenses:*')
    invalidate_cache('settlements:*')
    invalidate_cache('auth:bootstrap:*')


@expenses_sql_bp.route('/<expense_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:detail', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_expense(expense_id):
    """Get expense details"""
    user_id = get_current_user_id()
    
    success, result = expense_service_sql.get_expense(expense_id, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Expense not found'), 404)


@expenses_sql_bp.route('/<expense_id>', methods=['PUT'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdateExpenseSchema)
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
    data = g.validated_data
    user_id = get_current_user_id()
    
    logger.info("UPDATE EXPENSE %s - Request data: %s", expense_id, data)
    
    # UUID string straight through; int() here raised ValueError on every
    # real payer id and surfaced as an unhandled 500.
    paid_by_value = data.get('paid_by')
    
    success, result = expense_service_sql.update_expense(
        expense_id=expense_id,
        user_id=user_id,
        description=data.get('description'),
        amount=data.get('amount'),
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
        
        response_data = {
            'expense': result.get('expense'),
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else []
        }
        
        # Include updated balances if available
        if 'balances' in result:
            response_data['group_balances'] = result.get('balances', [])
        
        _invalidate_expense_caches()
        return success_response(data=response_data, message='Expense updated')
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only edit' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower():
            return error_response(error_msg, 403)
        return error_response(error_msg or 'Failed to update expense')


@expenses_sql_bp.route('/<expense_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
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
        
        response_data = {
            'expenses': all_expenses_result.get('expenses', []) if all_expenses_success else []
        }
        
        # Include updated balances if available
        if 'balances' in result:
            response_data['group_balances'] = result.get('balances', [])
        
        _invalidate_expense_caches()
        return success_response(data=response_data, message=result.get('message', 'Expense deleted'))
    else:
        # Return 403 for permission errors
        error_msg = result.get('error', '')
        if 'only delete' in error_msg.lower() or 'permission' in error_msg.lower() or 'not authorized' in error_msg.lower():
            return error_response(error_msg, 403)
        return error_response(error_msg or 'Failed to delete expense')


@expenses_sql_bp.route('/group/<group_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:group', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_group_expenses(group_id):
    """
    Get expenses for a group
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    - include_deleted: Include deleted expenses (default false)
    """
    user_id = get_current_user_id()
    limit = parse_query_int('limit', Config.EXPENSE_DEFAULT_LIMIT, minimum=1, maximum=100)
    offset = parse_query_int('offset', 0, minimum=0)
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    
    success, result = expense_service_sql.get_group_expenses(
        group_id=group_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
        include_deleted=include_deleted
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get group expenses'))


@expenses_sql_bp.route('/personal', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:personal', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_personal_expenses():
    """
    Get personal expenses (not associated with any group)
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    user_id = get_current_user_id()
    limit = parse_query_int('limit', Config.EXPENSE_DEFAULT_LIMIT, minimum=1, maximum=100)
    offset = parse_query_int('offset', 0, minimum=0)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset,
        personal_only=True
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get personal expenses'))


@expenses_sql_bp.route('/user', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:user', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
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
    limit = parse_query_int('limit', Config.EXPENSE_DEFAULT_LIMIT, minimum=1, maximum=100)
    offset = parse_query_int('offset', 0, minimum=0)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset,
        personal_only=personal_only
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get user expenses'))


@expenses_sql_bp.route('/<expense_id>/history', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:history', ttl=Config.CACHE_TTLS['expense_summary'], vary_on_user=True)
def get_expense_history(expense_id):
    """
    Get expense edit history
    
    Returns list of all changes made to this expense
    """
    user_id = get_current_user_id()
    
    success, result = expense_service_sql.get_expense_history(expense_id, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get expense history'), 404)


@expenses_sql_bp.route('/me', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='expenses:me', ttl=Config.CACHE_TTLS['expense_list'], vary_on_user=True)
def get_my_expenses():
    """
    Get all expenses involving the current user (personal + group)
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    user_id = get_current_user_id()
    limit = parse_query_int('limit', Config.EXPENSE_DEFAULT_LIMIT, minimum=1, maximum=100)
    offset = parse_query_int('offset', 0, minimum=0)
    
    success, result = expense_service_sql.get_user_expenses(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get expenses'))
