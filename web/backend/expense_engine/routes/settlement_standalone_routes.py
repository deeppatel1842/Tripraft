"""
Settlement Standalone Routes - For direct /api/expense/settlements access
Provides backward compatibility with frontend calling /settlements/group/{id}
"""

from flask import Blueprint, request, jsonify
from decimal import Decimal
import logging

from ..services.settlement_service import SettlementService
from ..services.group_service import GroupService
from ..services.balance_service import BalanceService
from ..middleware.auth import require_auth, get_current_user_id
from ..exceptions import ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Create standalone blueprint for /api/expense/settlements
settlement_standalone_bp = Blueprint(
    'settlements_standalone', 
    __name__, 
    url_prefix='/api/expense/settlements'
)


@settlement_standalone_bp.route('', methods=['POST'])
@require_auth
def create_settlement():
    """
    Create new settlement (record payment)
    
    POST /api/expense/settlements
    Body: {
        "group_id": "group123",
        "from_user_id": "user123",  # Person paying
        "to_user_id": "user456",    # Person receiving
        "amount": 50.00,
        "currency": "USD",
        "method": "cash",
        "notes": "Optional notes"
    }
    
    Response: {
        "success": true,
        "settlement": {...},
        "balances": [...]
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        if not data.get('group_id'):
            raise ValidationError("group_id is required")
        
        # Support both frontend formats: from_user/to_user OR from_user_id/to_user_id
        from_user_id = data.get('from_user_id') or data.get('from_user')
        to_user_id = data.get('to_user_id') or data.get('to_user')
        
        if not from_user_id:
            raise ValidationError("from_user_id is required")
        if not to_user_id:
            raise ValidationError("to_user_id is required")
        if not data.get('amount'):
            raise ValidationError("amount is required")
        
        group_id = data['group_id']
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Validate users are members
        if not group_service.is_member(group_id, from_user_id):
            raise ValidationError("from_user_id is not a group member")
        if not group_service.is_member(group_id, to_user_id):
            raise ValidationError("to_user_id is not a group member")
        
        # Validate users are different
        if from_user_id == to_user_id:
            raise ValidationError("Cannot settle with yourself")
        
        # Create settlement
        settlement_service = SettlementService()
        
        settlement = settlement_service.create_settlement(
            group_id=group_id,
            payer_id=from_user_id,
            receiver_id=to_user_id,
            amount=Decimal(str(data['amount'])),
            payment_method=data.get('method', 'cash'),
            notes=data.get('notes'),
            created_by=current_user_id
        )
        
        # Get updated balances
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
        
        logger.info("Settlement created in group %s by %s", group_id, current_user_id)
        
        return jsonify({
            'success': True,
            'settlement': settlement if isinstance(settlement, dict) else {},
            'balances': balances_array
        }), 201
        
    except ValidationError as e:
        logger.warning("Validation error in create_settlement: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 400
    except ForbiddenError as e:
        logger.warning("Permission error in create_settlement: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error("Error creating settlement: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to create settlement'}), 500


@settlement_standalone_bp.route('/group/<group_id>', methods=['GET'])
@require_auth
def get_group_settlements(group_id: str):
    """
    Get all settlements for a group
    
    GET /api/expense/settlements/group/:gid
    Query params: status (optional)
    
    Response: {
        "success": true,
        "settlements": [...]
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get settlements
        settlement_service = SettlementService()
        status = request.args.get('status')
        
        # Get group settlements
        settlements = settlement_service.get_group_settlements(group_id, status=status)
        
        return jsonify({
            'success': True,
            'settlements': settlements if isinstance(settlements, list) else []
        }), 200
        
    except ForbiddenError as e:
        logger.warning("Forbidden access to group settlements: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 403
    except NotFoundError as e:
        logger.warning("Group not found for settlements: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting group settlements: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get settlements'}), 500
