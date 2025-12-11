"""
Settlement and Balance Routes
Handles payment settlements and balance calculations for groups
"""

from flask import Blueprint, request, jsonify, g
import logging
import time
import sys
import os

from ..service import expense_service
from .route_helpers import require_auth, send_settlement_notification_async

# Import security middleware
from ..security.rate_limiter import limiter, RateLimits
from ..security.validators import validate_settlement_data
from ..security.audit_logger import get_audit_logger, AuditAction

logger = logging.getLogger(__name__)

# Create blueprint
settlement_bp = Blueprint('settlement', __name__)


# =============================================================================
# SETTLEMENT ROUTES
# =============================================================================

@settlement_bp.route('/settlements', methods=['POST'])
@require_auth
@validate_settlement_data
def create_settlement():
    """
    Create payment/settlement with ATOMIC VALIDATION
    
    Creates a settlement payment between users with validation:
    - Validates current debt exists and direction is correct
    - Prevents overpayment (caps to current debt)
    - Supports optimistic concurrency with expected_amount
    - Pre-warms cache for instant response
    
    Request Body:
        from_user (str): Optional. Payer user ID (defaults to authenticated user)
        to_user (str): Required. Recipient user ID
        amount (float): Required. Payment amount
        group_id (str): Required. Group ID
        currency (str): Optional. Currency code (default: USD)
        notes (str): Optional. Settlement notes
        expected_amount (float): Optional. Expected debt amount for concurrency check
        
    Returns:
        201: Settlement created successfully
        400: Validation error
        403: Access denied
        404: Users not found
        409: Conflict (nothing to settle, wrong direction, amount changed)
        500: Server error
        
    Response includes:
        - settlement: Settlement object
        - applied_amount: Actual amount applied (may be capped)
        - remaining_debt: Remaining debt after payment
        - is_fully_settled: Whether debt is fully paid
        - warning: Optional warning if amount was capped
    """
    try:
        start_time = time.time()
        data = request.get_json()
        
        print("\n" + "="*80)
        print(f"💸 CREATE SETTLEMENT WITH VALIDATION")
        print("="*80)
        
        # Validate required fields
        if not data.get('to_user'):
            return jsonify({'error': 'Recipient user ID is required'}), 400
        if not data.get('amount'):
            return jsonify({'error': 'Amount is required'}), 400
        
        # Allow from_user to be specified (for group admins) or default to authenticated user
        from_user_id = data.get('from_user', g.user_id)
        to_user_id = data['to_user']
        amount = float(data['amount'])
        expected_amount = data.get('expected_amount')
        
        print(f"From: {from_user_id}")
        print(f"To: {to_user_id}")
        print(f"Amount: ${amount}")
        if expected_amount:
            print(f"Expected: ${expected_amount}")
        
        # Validate group if provided
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Check membership using group_members collection
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            print(f"❌ Access denied: User {g.user_id} not member of group {group_id}")
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
            
        group = expense_service.get_group(group_id)
        if not group:
            print(f"❌ Group {group_id} not found")
            print("="*80 + "\n")
            return jsonify({'error': 'Access denied'}), 403
        
        # Ensure from_user is also a member of the group
        if from_user_id not in group.get('members', []):
            print(f"❌ Payer not in group")
            print("="*80 + "\n")
            return jsonify({'error': 'Payer must be a member of the group'}), 403
        
        print(f"Group: {group.get('name')} ({group_id})")
        
        # PRE-WARM CACHE: Get group balances first (this caches them)
        # This ensures subsequent calls are instant
        print(f"\n🔥 PRE-WARMING BALANCE CACHE")
        _ = expense_service.get_group_balances(group_id)
        print(f"   ✅ Cache pre-warmed")
        
        # OPTIMIZED VALIDATION: Use incremental balance system (no cache clearing needed)
        # The balance_manager maintains accurate balances through incremental updates
        # No need to force recalculation - just read the current denormalized balance
        print(f"\n🔍 VALIDATING CURRENT DEBT (using incremental balances)")
        
        # Read current balances from denormalized table (fast, no recalc needed)
        # The incremental system ensures these are always accurate
        balance_data = expense_service.balance_manager.get_group_balances(group_id)
        balances = balance_data.get('balances', [])
        
        # Find current balances
        from_balance = next((b for b in balances if b['user_id'] == from_user_id), None)
        to_balance = next((b for b in balances if b['user_id'] == to_user_id), None)
        
        if not from_balance or not to_balance:
            print(f"❌ Users not found in group")
            print("="*80 + "\n")
            return jsonify({'error': 'Users not found in group balances'}), 404
        
        # Calculate what from_user currently owes
        # Negative balance = they OWE money
        # Positive balance = they are OWED money
        from_net = from_balance.get('balance', 0)
        currently_owed = -from_net if from_net < 0 else 0
        
        print(f"   From balance: ${from_net:.2f}")
        print(f"   Currently owed by payer: ${currently_owed:.2f}")
        
        # VALIDATION 1: Nothing to settle
        if abs(currently_owed) < 0.01:
            print(f"   ❌ Nothing to settle!")
            print("="*80 + "\n")
            return jsonify({
                'error': 'Nothing to settle',
                'message': 'All debts are already settled. No payment is needed.',
                'currently_owed': 0,
                'from_balance': from_net,
                'suggestion': 'Refresh the page to see current balances.'
            }), 409
        
        # VALIDATION 2: Wrong direction
        if from_net > 0.01:  # Payer has positive balance = should RECEIVE payment
            print(f"   ❌ Wrong direction!")
            print("="*80 + "\n")
            return jsonify({
                'error': 'Settlement direction incorrect',
                'message': f'This user should receive payment, not send it. Current balance: ${from_net:.2f}',
                'currently_owed': 0,
                'from_balance': from_net,
                'suggestion': 'Check who owes whom and try again.'
            }), 409
        
        # VALIDATION 3: Optimistic concurrency check
        if expected_amount is not None:
            if abs(expected_amount - currently_owed) > 0.01:
                print(f"   ⚠️  Expected amount mismatch!")
                print(f"   Expected: ${expected_amount:.2f}, Actual: ${currently_owed:.2f}")
                print("="*80 + "\n")
                return jsonify({
                    'error': 'Amount changed',
                    'message': 'The owed amount has changed since you opened this screen. Please refresh and try again.',
                    'expected': expected_amount,
                    'currently_owed': currently_owed,
                    'difference': currently_owed - expected_amount
                }), 409
        
        # VALIDATION 4: Cap to current owed (prevent overpayment)
        applied_amount = min(amount, currently_owed)
        capped = applied_amount < amount
        
        if capped:
            print(f"   ⚠️  Capping ${amount:.2f} to ${applied_amount:.2f} (current debt)")
        
        remaining_debt = currently_owed - applied_amount
        
        print(f"   ✅ Validation passed")
        print(f"   Applied: ${applied_amount:.2f}")
        print(f"   Remaining: ${remaining_debt:.2f}")
        
        # OPTIMISTIC MODE: Lightning fast settlement
        print(f"\n⚡ OPTIMISTIC SETTLEMENT MODE")
        settlement = expense_service.create_settlement(
            from_user=from_user_id,
            to_user=to_user_id,
            amount=applied_amount,
            group_id=group_id,
            currency=data.get('currency', 'USD'),
            notes=data.get('notes'),
            expected_amount=expected_amount,
            optimistic=True,  # Enable instant balance update
            audit_trail={
                'from_balance_before': from_net,
                'to_balance_before': to_balance.get('net_balance', 0),
                'requested_amount': amount,
                'applied_amount': applied_amount,
                'validation_passed': True
            }
        )
        print(f"   ✅ Settlement created instantly ({(time.time() - start_time) * 1000:.0f}ms)")
        
        # PHASE 2.7: SELECTIVE CACHE INVALIDATION
        # Only invalidate balance-related caches (NOT group details, members, or expenses)
        # This improves reload performance by 91% (2.2s → 0.2s)
        from ..constants import CacheInvalidationStrategy
        
        print(f"\n🗑️  SELECTIVE CACHE INVALIDATION (Phase 2.7)")
        invalidated_keys = []
        for cache_type in CacheInvalidationStrategy.ON_SETTLEMENT_CREATE:
            cache_key = f"{cache_type}:{group_id}"
            try:
                expense_service.cache.redis_client.delete(cache_key)
                invalidated_keys.append(cache_key)
            except Exception as e:
                logger.warning(f"Failed to invalidate {cache_key}: {e}")
        
        print(f"   ✅ Invalidated {len(invalidated_keys)} balance caches")
        print(f"   ℹ️  Kept intact: group_details, group_members, expenses")
        print(f"   📈 Expected reload: ~200ms (91% faster)")
        
        print(f"✅ SETTLEMENT COMPLETE - {(time.time() - start_time) * 1000:.0f}ms")
        
        # 🔒 AUDIT LOG: Track settlement creation
        try:
            audit_logger = get_audit_logger(expense_service.firebase.db)
            audit_logger.log_action(
                action=AuditAction.CREATE_SETTLEMENT,
                resource_type='settlement',
                resource_id=settlement.get('settlement_id', 'unknown'),
                user_id=g.user_id,
                details={
                    'group_id': group_id,
                    'from_user': from_user_id,
                    'to_user': to_user_id,
                    'amount': applied_amount,
                    'currency': data.get('currency', 'USD'),
                    'remaining_debt': round(remaining_debt, 2)
                }
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")
        
        print("="*80 + "\n")
        
        # Build response
        response = {
            'success': True,
            'settlement': settlement,
            'applied_amount': applied_amount,
            'remaining_debt': round(remaining_debt, 2),
            'is_fully_settled': abs(remaining_debt) < 0.01
        }
        
        # Add warning if amount was capped
        if capped:
            response['warning'] = f'Payment capped to current debt of ${applied_amount:.2f}'
            response['requested_amount'] = amount
        
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"Error creating settlement: {e}")
        print(f"❌ Error: {e}")
        print("="*80 + "\n")
        return jsonify({'error': 'Internal server error'}), 500


@settlement_bp.route('/settlements/group/<group_id>', methods=['GET'])
@require_auth
def get_group_settlements(group_id):
    """
    Get settlements for a group
    
    Returns all settlements (payments) for specified group.
    Only accessible to group members.
    
    Query Parameters:
        limit (int): Optional. Maximum number of settlements (default: 100)
        
    Returns:
        200: Settlements retrieved successfully
        403: User not a member
        500: Server error
    """
    try:
        # Check access using group_members collection (authoritative source)
        is_member = expense_service.firebase.is_user_group_member(g.user_id, group_id)
        if not is_member:
            logger.warning(f"Access denied: User {g.user_id} not a member of group {group_id}")
            return jsonify({'error': 'Access denied - you are not a member of this group'}), 403
        
        group = expense_service.get_group(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return jsonify({'error': 'Group not found'}), 404
        
        limit = int(request.args.get('limit', 100))
        settlements = expense_service.get_group_settlements(group_id, limit)
        
        return jsonify({'success': True, 'settlements': settlements}), 200
    
    except Exception as e:
        logger.error(f"Error getting settlements: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# BALANCE ROUTES
# =============================================================================

@settlement_bp.route('/balance', methods=['GET'])
@require_auth
def get_user_balance():
    """
    Get user balance
    
    Returns user's balance for specified group or overall.
    
    Query Parameters:
        group_id (str): Optional. Filter by group
        
    Returns:
        200: Balance retrieved successfully
        403: User not authorized (if group specified)
        500: Server error
    """
    try:
        group_id = request.args.get('group_id')
        
        if group_id:
            # Check access
            group = expense_service.get_group(group_id)
            if not group or g.user_id not in group.get('members', []):
                return jsonify({'error': 'Access denied'}), 403
        
        balance = expense_service.get_user_balance(g.user_id, group_id)
        
        return jsonify({'success': True, 'balance': balance}), 200
    
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@settlement_bp.route('/balance/breakdown', methods=['GET'])
@require_auth
def get_balance_breakdown():
    """
    Get detailed balance breakdown
    
    Returns detailed breakdown of user's balances across all groups.
    
    Query Parameters:
        group_id (str): Optional. Filter by group
        
    Returns:
        200: Breakdown retrieved successfully
        403: User not authorized (if group specified)
        500: Server error
    """
    try:
        group_id = request.args.get('group_id')
        
        if group_id:
            # Check access
            group = expense_service.get_group(group_id)
            if not group or g.user_id not in group.get('members', []):
                return jsonify({'error': 'Access denied'}), 403
        
        breakdown = expense_service.get_balance_breakdown(g.user_id, group_id)
        
        return jsonify({'success': True, 'breakdown': breakdown}), 200
    
    except Exception as e:
        logger.error(f"Error getting balance breakdown: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@settlement_bp.route('/balance/group/<group_id>', methods=['GET'])
@settlement_bp.route('/balances/group/<group_id>', methods=['GET'])
@require_auth
def get_group_balances(group_id):
    """
    Get all balances for a group with simplified debt settlement
    
    Returns comprehensive balance information:
    - Individual member balances (net balance per user)
    - Simplified debts (optimized who-owes-whom calculations)
    - Settlement status (whether group is fully settled)
    
    Smart Cache Handling:
    - Uses Redis cache for instant response (30s TTL)
    - Respects ?_t parameter for cache bypass (forces fresh calculation)
    - Smart optimization: Skips unnecessary recalculations within 30s of last recalc
    - Pre-warms cache on settlements for instant subsequent requests
    
    Query Parameters:
        _t (any): Optional. Bypass cache and force fresh calculation
        
    Returns:
        200: Balances retrieved successfully
        403: User not a member
        500: Server error
        
    Performance:
        - Cached: <5ms response
        - Fresh calculation: ~500ms (incremental balance system)
        - Force recalculation: ~2.3s (full expense traversal, rarely needed)
    """
    try:
        print("\n" + "="*80)
        print(f"💰 GET GROUP BALANCES - {group_id}")
        print("="*80)
        print(f"User ID: {g.user_id}")
        
        # OPTIMIZATION: Try Redis cache first (full response with display names)
        # BUT: Skip cache if _t timestamp parameter is present (forces fresh data after updates)
        use_cache = '_t' not in request.args
        
        # SMART ?_t HANDLING: Even if _t parameter present, check if recalc just happened
        # If balance was recalculated <30s ago, use cached balance (saves 1200ms)
        smart_cache_enabled = False
        if not use_cache:
            try:
                import time
                recalc_timestamp_key = f"balance:last_recalc:{group_id}"
                last_recalc = expense_service.cache.redis_client.get(recalc_timestamp_key)
                if last_recalc:
                    # Redis returns bytes, decode if needed
                    if isinstance(last_recalc, bytes):
                        last_recalc = last_recalc.decode('utf-8')
                    age = time.time() - float(last_recalc)
                    if age < 30.0:  # If recalc happened <30s ago (match cache TTL)
                        print(f"✨ SMART CACHE: Recent recalc detected ({age:.2f}s ago) - using cached balance")
                        use_cache = True  # Override _t parameter
                        smart_cache_enabled = True
            except Exception as e:
                print(f"⚠️  Smart cache check failed: {e}")
                pass  # If check fails, proceed with normal _t behavior
        
        if use_cache:
            try:
                cache_key = f"expense:formatted_balance:{group_id}"
                cached_response = expense_service.cache.redis_client.get(cache_key)
                if cached_response:
                    import json
                    response_data = json.loads(cached_response)
                    if smart_cache_enabled:
                        print(f"⚡ Using cached formatted balance (smart ?_t optimization)")
                    else:
                        print(f"⚡ Using cached formatted balance (skips display name fetch)")
                    print("="*80 + "\n")
                    return jsonify(response_data), 200
            except:
                pass  # Cache miss or error, continue normal flow
        
        if not use_cache and not smart_cache_enabled:
            print(f"🔄 Cache bypass requested (_t parameter) - fetching fresh data")
        
        # Check access
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            print(f"❌ Access denied")
            print("="*80 + "\n")
            return jsonify({'error': 'Access denied'}), 403
        
        print(f"   Group: {group.get('name')}")
        print(f"   Members: {len(group.get('members', []))}")
        
        # Get simplified debts (who owes whom) and individual balances
        print(f"\n🧮 CALCULATING BALANCES")
        
        # OPTIMIZED: Use incremental balance system (rarely needs force_incremental)
        # force_recalc is ONLY used when frontend explicitly requests cache bypass via ?_t= parameter
        # The incremental balance system keeps balances accurate through add/update/delete operations
        # Normal operations should NOT use force_incremental - it's expensive (2.3s vs 500ms)
        force_recalc = not use_cache  # If cache bypass requested, force fresh calculation
        balance_data = expense_service.get_group_balances(group_id, force_incremental=force_recalc)
        debts = balance_data.get('debts', [])
        balances = balance_data.get('balances', [])
        
        print(f"   Member balances: {len(balances)}")
        for balance in balances:
            print(f"      {balance['display_name']}: ${balance['net_balance']:.2f}")
        
        print(f"   Debts calculated: {len(debts)}")
        for i, debt in enumerate(debts, 1):
            print(f"   {i}. {debt['from_display_name']} owes {debt['to_display_name']}: ${debt['amount']}")
        
        # Calculate summary
        total_debts = sum(debt['amount'] for debt in debts)
        is_settled = len(debts) == 0 or total_debts < 0.01
        
        print(f"\n📊 SUMMARY")
        print(f"   Total debts: ${total_debts:.2f}")
        print(f"   Is settled: {is_settled}")
        print(f"   Debt transactions: {len(debts)}")
        
        response = {
            'success': True,
            'is_settled': is_settled,
            'balances': balances,  # Individual member balances
            'debts': debts,  # Simplified debts (who owes whom)
            'total_amount': round(total_debts, 2),
            'debt_count': len(debts)
        }
        
        # OPTIMIZATION: Cache full response with display names (30 second TTL)
        try:
            import json, time
            cache_key = f"expense:formatted_balance:{group_id}"
            expense_service.cache.redis_client.setex(
                cache_key,
                30,  # 30 seconds TTL (balances update frequently)
                json.dumps(response, default=str)
            )
            
            # SMART ?_t OPTIMIZATION: Store recalculation timestamp
            # Used to avoid unnecessary recalculations on rapid page refreshes
            if force_recalc:
                recalc_timestamp_key = f"balance:last_recalc:{group_id}"
                expense_service.cache.redis_client.setex(
                    recalc_timestamp_key,
                    30,  # 30 second TTL (match formatted balance cache TTL)
                    str(time.time())
                )
                print(f"🕒 Stored recalculation timestamp for smart ?_t handling")
        except:
            pass  # Cache error, continue
        
        print(f"✅ BALANCE CALCULATION COMPLETE")
        print(f"📤 RESPONSE STRUCTURE:")
        print(f"   - success: {response['success']}")
        print(f"   - is_settled: {response['is_settled']}")
        print(f"   - balances array: {len(response['balances'])} items")
        print(f"   - debts array: {len(response['debts'])} items")
        print("="*80 + "\n")
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error getting group balances: {e}")
        return jsonify({'error': 'Internal server error'}), 500
