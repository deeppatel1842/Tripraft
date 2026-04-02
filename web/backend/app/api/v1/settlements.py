"""
SQL-based Settlement Routes
API endpoints for settlement operations using local SQL database
"""

import logging

from app.api.utils.responses import (created_response, error_response,
                                     success_response,
                                     validation_error_response)
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth)
from app.infrastructure.cache.redis import cache_response, invalidate_cache
from app.schemas.common import CreateSettlementSchema, validate_request
from app.services.settlement_service import settlement_service_sql
from flask import Blueprint, request

logger = logging.getLogger(__name__)

# Use /api/expense/settlements to match frontend expectations
settlements_sql_bp = Blueprint('settlements_sql', __name__, url_prefix='/api/v1/expenses/settlements')


def parse_id(id_value):
    """Parse ID - handles both int and string"""
    try:
        return int(id_value)
    except (ValueError, TypeError):
        return None


@settlements_sql_bp.route('', methods=['POST'])
@limit_api(Config.RATE_LIMITS['settle'])
@require_auth
def create_settlement():
    """
    Create a settlement (record a payment) - TripRaft Model
    
    Request body:
    {
        "group_id": 1,
        "from_user_id": 2,  // who is paying (owes money) - also accepts "from_user"
        "to_user_id": 1,    // who is receiving (is owed money) - also accepts "to_user"
        "amount": 500.00,
        "method": "upi",    // optional: "cash", "upi", "bank_transfer"
        "notes": "UPI payment"  // optional
    }
    
    Response includes:
    - settlement: newly created settlement
    - balances: updated group balances (complete state)
    - debts: updated simplified debts
    """
    data = request.get_json()
    
    if not data:
        return error_response('Request body required')
    
    validated, errors = validate_request(CreateSettlementSchema, data)
    if errors:
        return validation_error_response(errors)
    
    # Accept both from_user/to_user and from_user_id/to_user_id for compatibility
    from_user_id = validated.get('from_user_id') or validated.get('from_user')
    to_user_id = validated.get('to_user_id') or validated.get('to_user')
    
    if not from_user_id:
        return error_response('from_user_id (or from_user) is required')
    if not to_user_id:
        return error_response('to_user_id (or to_user) is required')
    
    user_id = get_current_user_id()
    group_id = validated['group_id']
    
    success, result = settlement_service_sql.create_settlement(
        user_id=user_id,
        group_id=group_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        amount=float(validated['amount']),
        method=validated.get('method', 'cash'),
        notes=validated.get('notes')
    )
    
    if success:
        # Get updated balances and debts (complete state)
        balances_success, balances_result = settlement_service_sql.get_group_balances(group_id, user_id)
        debts_success, debts_result = settlement_service_sql.get_simplified_debts(group_id, user_id)
        
        # TripRaft Model: Also get all settlements for the group
        settlements_success, settlements_result = settlement_service_sql.get_group_settlements(group_id, user_id)
        
        data_payload = {
            'settlement': result.get('settlement'),
            'settlements': settlements_result.get('settlements', []) if settlements_success else [],
            'balances': balances_result.get('balances', []) if balances_success else [],
            'debts': debts_result.get('debts', []) if debts_success else []
        }
        
        _invalidate_settlement_caches()
        return created_response(data=data_payload)
    else:
        return error_response(result.get('error', 'Failed to create settlement'))


def _invalidate_settlement_caches():
    """Invalidate settlement and related caches."""
    invalidate_cache('settlements:*')
    invalidate_cache('expenses:*')
    invalidate_cache('exp_groups:*')
    invalidate_cache('auth:bootstrap:*')


@settlements_sql_bp.route('/<settlement_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='settlements:detail', ttl=Config.CACHE_TTLS['settlements'], vary_on_user=True)
def get_settlement(settlement_id):
    """Get settlement details"""
    user_id = get_current_user_id()
    
    success, result = settlement_service_sql.get_settlement(settlement_id, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Settlement not found'), 404)


@settlements_sql_bp.route('/<settlement_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
def delete_settlement(settlement_id):
    """
    Delete a settlement - TripRaft Model
    
    Response includes:
    - message: confirmation message
    - balances: updated group balances (complete state)
    - debts: updated simplified debts
    """
    user_id = get_current_user_id()
    
    success, result = settlement_service_sql.delete_settlement(settlement_id, user_id)
    
    if success:
        group_id = result.get('group_id')
        
        # Get updated balances and debts (complete state)
        balances_success, balances_result = settlement_service_sql.get_group_balances(group_id, user_id)
        debts_success, debts_result = settlement_service_sql.get_simplified_debts(group_id, user_id)
        
        data_payload = {
            'message': result.get('message', 'Settlement deleted successfully'),
            'balances': balances_result.get('balances', []) if balances_success else [],
            'debts': debts_result.get('debts', []) if debts_success else []
        }
        
        _invalidate_settlement_caches()
        return success_response(data=data_payload)
    else:
        return error_response(result.get('error', 'Failed to delete settlement'))


@settlements_sql_bp.route('/group/<group_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='settlements:group', ttl=Config.CACHE_TTLS['settlements'], vary_on_user=True)
def get_group_settlements(group_id):
    """
    Get settlements for a group
    
    Query params:
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    gid = parse_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    limit = request.args.get('limit', Config.EXPENSE_DEFAULT_LIMIT, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    success, result = settlement_service_sql.get_group_settlements(
        group_id=gid,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get settlements'))


@settlements_sql_bp.route('/group/<group_id>/balances', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='settlements:balances', ttl=Config.CACHE_TTLS['settlements'], vary_on_user=True)
def get_group_balances(group_id):
    """Get all balances for a group"""
    gid = parse_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = settlement_service_sql.get_group_balances(gid, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get balances'))


@settlements_sql_bp.route('/group/<group_id>/simplified', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='settlements:simplified', ttl=Config.CACHE_TTLS['settlements'], vary_on_user=True)
def get_simplified_debts(group_id):
    """
    Get simplified debts for a group
    Returns who owes whom with minimized transactions
    """
    gid = parse_id(group_id)
    if gid is None:
        return error_response('Invalid group ID')
    
    user_id = get_current_user_id()
    
    success, result = settlement_service_sql.get_simplified_debts(gid, user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get simplified debts'))


@settlements_sql_bp.route('/me/balance', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='settlements:my_balance', ttl=Config.CACHE_TTLS['expense_summary'], vary_on_user=True)
def get_my_balance():
    """
    Get current user's total balance across all groups
    Returns total owed, total owes, and net balance
    """
    user_id = get_current_user_id()
    
    success, result = settlement_service_sql.get_user_total_balance(user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to get balance'))
