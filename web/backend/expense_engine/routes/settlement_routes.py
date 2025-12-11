"""
Settlement Routes - Settlement Management API
Handles settlement CRUD operations with balance updates
"""

from flask import Blueprint, request, jsonify
from decimal import Decimal
import logging

from ..services.settlement_service import SettlementService
from ..services.group_service import GroupService
from ..services.balance_service import BalanceService
from ..middleware.auth import require_auth, get_current_user_id
from ..exceptions import (
    ValidationError, NotFoundError, ForbiddenError,
    InsufficientPermissionsError
)
from ..config import pagination_config

logger = logging.getLogger(__name__)

# Create blueprint
settlement_bp = Blueprint('settlements', __name__, url_prefix='/api/expense/groups/<group_id>/settlements')


@settlement_bp.route('', methods=['POST'])
@require_auth
def create_settlement(group_id: str):
    """
    Create new settlement (record payment)
    
    POST /api/expense/groups/:gid/settlements
    Body: {
        "from_user_id": "user123",
        "to_user_id": "user456",
        "amount": 50.00,
        "currency": "USD",
        "method": "cash",
        "notes": "Optional notes",
        "proof_url": "https://..."
    }
    
    Response: {
        "success": true,
        "settlement": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate required fields
        required_fields = ['from_user_id', 'to_user_id', 'amount']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"{field} is required")
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Validate users are members
        if not group_service.is_member(group_id, data['from_user_id']):
            raise ValidationError("from_user_id is not a group member")
        if not group_service.is_member(group_id, data['to_user_id']):
            raise ValidationError("to_user_id is not a group member")
        
        # Validate users are different
        if data['from_user_id'] == data['to_user_id']:
            raise ValidationError("Cannot settle with yourself")
        
        # Create settlement (balance updates handled by service)
        settlement_service = SettlementService()
        
        settlement = settlement_service.create_settlement(
            group_id=group_id,
            payer_id=data['from_user_id'],
            receiver_id=data['to_user_id'],
            amount=Decimal(str(data['amount'])),
            payment_method=data.get('method', 'cash'),
            notes=data.get('notes'),
            created_by=current_user_id
        )
        
        # Phase 17.8: Fetch updated balances to return with response
        balance_service = BalanceService()
        raw_balances = balance_service.get_group_balances(group_id)
        balances = {uid: float(balance) for uid, balance in raw_balances.items()}
        
        logger.info("Settlement created in group %s", group_id)
        
        return jsonify({
            'success': True,
            'settlement': settlement if isinstance(settlement, dict) else {},
            'balances': balances  # Phase 17.8: Return balances for instant UI update
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


@settlement_bp.route('/<settlement_id>', methods=['GET'])
@require_auth
def get_settlement(group_id: str, settlement_id: str):
    """
    Get settlement details
    
    GET /api/expense/groups/:gid/settlements/:sid
    
    Response: {
        "success": true,
        "settlement": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get settlement
        settlement_service = SettlementService()
        settlement = settlement_service.get_settlement(settlement_id)
        
        if not settlement:
            raise NotFoundError("Settlement not found")
        
        settlement_group_id = settlement.get('group_id') if isinstance(settlement, dict) else settlement.group_id
        if settlement_group_id != group_id:
            raise ForbiddenError("Settlement does not belong to this group")
        
        return jsonify({
            'success': True,
            'settlement': settlement if isinstance(settlement, dict) else {}
        })
        
    except (NotFoundError, ForbiddenError) as e:
        logger.warning("Error in get_settlement: %s", e)
        status = 404 if isinstance(e, NotFoundError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error getting settlement: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get settlement'}), 500


@settlement_bp.route('', methods=['GET'])
@require_auth
def list_settlements(group_id: str):
    """
    List settlements with pagination
    
    GET /api/expense/groups/:gid/settlements?page=1&limit=20
    
    Response: {
        "success": true,
        "settlements": [...],
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
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Validate pagination
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if limit < 1 or limit > pagination_config.MAX_PAGE_SIZE:
            raise ValidationError(f"Limit must be between 1 and {pagination_config.MAX_PAGE_SIZE}")
        
        # Get settlements
        settlement_service = SettlementService()
        settlements = settlement_service.get_group_settlements(group_id, status=None, limit=limit)
        
        return jsonify({
            'success': True,
            'settlements': [s.to_dict() for s in settlements],
            'page': page,
            'limit': limit,
            'has_more': len(settlements) == limit
        })
        
    except (ValidationError, ForbiddenError) as e:
        logger.warning("Error in list_settlements: %s", e)
        status = 400 if isinstance(e, ValidationError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error listing settlements: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to list settlements'}), 500


@settlement_bp.route('/user/<user_id>', methods=['GET'])
@require_auth
def get_user_settlements(group_id: str, user_id: str):
    """
    Get settlements for specific user
    
    GET /api/expense/groups/:gid/settlements/user/:uid?page=1&limit=20
    
    Response: {
        "success": true,
        "settlements": [...],
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
        
        # Check user is member
        if not group_service.is_member(group_id, user_id):
            raise ValidationError("User is not a group member")
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', pagination_config.DEFAULT_PAGE_SIZE))
        
        # Get user settlements
        settlement_service = SettlementService()
        settlements = settlement_service.get_user_settlements(user_id, group_id=group_id)
        
        return jsonify({
            'success': True,
            'settlements': [s.to_dict() for s in settlements],
            'page': page,
            'limit': limit,
            'has_more': len(settlements) == limit
        })
        
    except (ValidationError, ForbiddenError) as e:
        logger.warning("Error in get_user_settlements: %s", e)
        status = 400 if isinstance(e, ValidationError) else 403
        return jsonify({'success': False, 'error': str(e)}), status
    except Exception as e:
        logger.error("Error getting user settlements: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get user settlements'}), 500


@settlement_bp.route('/<settlement_id>/proof', methods=['POST'])
@require_auth
def add_payment_proof(group_id: str, settlement_id: str):
    """
    Add payment proof to settlement
    
    POST /api/expense/groups/:gid/settlements/:sid/proof
    Body: {
        "proof_url": "https://...",
        "notes": "Payment receipt"
    }
    
    Response: {
        "success": true,
        "settlement": {...}
    }
    """
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'proof_url' not in data:
            raise ValidationError("proof_url is required")
        
        # Check group membership
        group_service = GroupService()
        if not group_service.is_member(group_id, current_user_id):
            raise ForbiddenError("You are not a member of this group")
        
        # Get settlement
        settlement_service = SettlementService()
        settlement = settlement_service.get_settlement(settlement_id)
        
        if not settlement:
            raise NotFoundError("Settlement not found")
        
        if settlement.group_id != group_id:
            raise ForbiddenError("Settlement does not belong to this group")
        
        # Check permissions (payer, receiver, or admin)
        if current_user_id not in [settlement.from_user_id, settlement.to_user_id]:
            if not group_service.has_permission(group_id, current_user_id, 'manage_settlements'):
                raise InsufficientPermissionsError("You don't have permission to update this settlement")
        
        # Add proof
        settlement_service.add_payment_proof(
            settlement_id=settlement_id,
            proof_type=data.get('proof_type', 'screenshot'),
            proof_url=data['proof_url'],
            uploaded_by=current_user_id,
            notes=data.get('notes')
        )
        
        # Get updated settlement
        updated_settlement = settlement_service.get_settlement(settlement_id)
        
        logger.info("Payment proof added to settlement: %s", settlement_id)
        
        return jsonify({
            'success': True,
            'settlement': updated_settlement if isinstance(updated_settlement, dict) else {}
        })
        
    except (ValidationError, NotFoundError, ForbiddenError, InsufficientPermissionsError) as e:
        logger.warning("Error in add_payment_proof: %s", e)
        status_map = {
            ValidationError: 400,
            NotFoundError: 404,
            ForbiddenError: 403,
            InsufficientPermissionsError: 403
        }
        return jsonify({'success': False, 'error': str(e)}), status_map.get(type(e), 400)
    except Exception as e:
        logger.error("Error adding payment proof: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to add payment proof'}), 500


# Error handlers
@settlement_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'success': False, 'error': str(error)}), 400


@settlement_bp.errorhandler(NotFoundError)
def handle_not_found(error):
    return jsonify({'success': False, 'error': str(error)}), 404


@settlement_bp.errorhandler(ForbiddenError)
def handle_forbidden(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@settlement_bp.errorhandler(InsufficientPermissionsError)
def handle_insufficient_permissions(error):
    return jsonify({'success': False, 'error': str(error)}), 403


@settlement_bp.errorhandler(Exception)
def handle_generic_error(error):
    logger.error("Unexpected error: %s", error, exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
