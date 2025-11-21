"""
Expense Routes - Expense management endpoints for the expense engine
Handles expense CRUD operations with optimistic updates and smart caching
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
import logging
import uuid
from datetime import datetime
import time
import hashlib
import json

# Import from parent expense_engine module
from ..service import expense_service
from ..local_storage import local_storage
from ..constants import PaginationConfig
from ..decimal_utils import (
    dollars_to_cents,
    cents_to_dollars_float,
    calculate_equal_split,
    calculate_percentage_split
)

# Import from route_helpers submodule
from .route_helpers import (
    track_time,
    require_auth,
    validate_category,
    validate_split_type,
    calculate_splits,
    send_expense_notifications_async
)

# Import security middleware
from ..security.rate_limiter import limiter, RateLimits
from ..security.validators import validate_expense_data, validate_group_id
from ..security.audit_logger import get_audit_logger, AuditAction

logger = logging.getLogger(__name__)

# Create blueprint
expense_bp = Blueprint('expense', __name__)


@expense_bp.route('/expenses', methods=['POST'])
@require_auth
@validate_expense_data
@track_time("CREATE EXPENSE")
def create_expense():
    """Create new expense (with idempotency support)"""
    try:
        data = request.get_json()
        
        # IDEMPOTENCY: Get or generate idempotency key
        idempotency_key = request.headers.get('Idempotency-Key')
        
        # Auto-generate idempotency key if not provided (for duplicate click prevention)
        if not idempotency_key:
            import hashlib
            import json
            # Create deterministic key from user + amount + description + timestamp (2 second window)
            import time
            timestamp_window = int(time.time() / 2)  # 2-second window for duplicate clicks
            idempotency_data = {
                'user': g.user_id,
                'amount': data.get('amount'),
                'description': data.get('description'),
                'category': data.get('category'),
                'window': timestamp_window
            }
            idempotency_hash = hashlib.sha256(json.dumps(idempotency_data, sort_keys=True).encode()).hexdigest()
            idempotency_key = f"auto:{idempotency_hash[:16]}"
            logger.info(f"🔐 Auto-generated idempotency key: {idempotency_key}")
        
        if idempotency_key:
            cache_key = f"idempotency:{idempotency_key}"
            lock_key = f"lock:{idempotency_key}"
            
            try:
                # Check if we've seen this request before (24h TTL)
                cached_response = expense_service.cache.redis_client.get(cache_key)
                if cached_response:
                    import json
                    cached_data = json.loads(cached_response)
                    logger.info(f"🔄 Idempotency hit for key: {idempotency_key}")
                    print(f"🔄 IDEMPOTENCY HIT: Returning cached response for {idempotency_key}")
                    print(f"   ✅ DUPLICATE PREVENTED - Returning same expense")
                    # Return 201 (same as original) so frontend always shows success
                    return jsonify(cached_data), 201
                
                # Try to acquire lock (prevents concurrent processing of identical requests)
                lock_acquired = expense_service.cache.redis_client.set(
                    lock_key, 
                    "1", 
                    ex=10,  # Lock expires in 10 seconds
                    nx=True  # Only set if not exists
                )
                
                if not lock_acquired:
                    # Another request is already processing this
                    print(f"⏳ LOCK EXISTS: Another identical request is being processed")
                    # Wait for first request to complete and cache response
                    import time
                    max_retries = 20  # Try for up to 10 seconds (20 * 0.5s)
                    for retry in range(max_retries):
                        time.sleep(0.5)
                        cached_response = expense_service.cache.redis_client.get(cache_key)
                        if cached_response:
                            import json
                            cached_data = json.loads(cached_response)
                            logger.info(f"🔄 Idempotency hit after lock wait (retry {retry+1}): {idempotency_key}")
                            print(f"🔄 IDEMPOTENCY HIT (after {(retry+1)*0.5}s wait): Returning cached response")
                            print(f"   ✅ DUPLICATE PREVENTED - Returning same expense as first request")
                            # Return 201 (same as first request) so frontend shows success
                            return jsonify(cached_data), 201
                    
                    # If we get here, first request failed or took too long
                    # Let this request proceed (don't block user)
                    logger.warning(f"Lock timeout for {idempotency_key}, proceeding anyway")
                    print(f"⚠️  Lock timeout - allowing request to proceed")
                        
            except Exception as cache_err:
                logger.warning(f"Idempotency cache check failed: {cache_err}")
        
        print("\n" + "="*80)
        print("📝 CREATE EXPENSE - START")
        print("="*80)
        print(f"User ID: {g.user_id}")
        print(f"Request Data: {data}")
        if idempotency_key:
            print(f"Idempotency-Key: {idempotency_key}")
        
        # Validate required fields
        if not data.get('description'):
            return jsonify({'error': 'Description is required'}), 400
        if not data.get('amount'):
            return jsonify({'error': 'Amount is required'}), 400
        if not data.get('category'):
            return jsonify({'error': 'Category is required'}), 400
        if not data.get('splits'):
            return jsonify({'error': 'Splits are required'}), 400
        
        print(f"✅ Validation passed")
        print(f"   Description: {data['description']}")
        print(f"   Amount: {data['amount']}")
        print(f"   Category: {data['category']}")
        print(f"   Splits received: {data['splits']}")
        print(f"   Paid by (from request): {data.get('paid_by')}")
        
        # Normalize category to lowercase
        category = data['category'].lower()
        
        # Validate category (case-insensitive)
        if not validate_category(category):
            return jsonify({'error': f'Invalid category: {category}'}), 400
        
        # Validate split type
        split_type = data.get('split_type', 'equal')
        if not validate_split_type(split_type):
            return jsonify({'error': 'Invalid split type'}), 400
        
        print(f"   Split Type: {split_type}")
        
        # Get group if provided
        group_id = data.get('group_id')
        print(f"   Group ID: {group_id}")
        print(f"   Group ID: {group_id}")
        
        # FAST PATH FOR PERSONAL EXPENSES - Use only local storage
        if not group_id:
            print("\n📦 PERSONAL EXPENSE - Local Storage Only")
            # Create personal expense directly in local storage
            expense_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Parse date if provided, otherwise use current date
            expense_date = data.get('date')
            if expense_date:
                # Handle ISO format dates
                if 'T' in expense_date:
                    expense_date = expense_date.split('T')[0]
            else:
                expense_date = current_time.strftime('%Y-%m-%d')
            
            print(f"   Expense ID: {expense_id}")
            print(f"   Date: {expense_date}")
            
            # Get paid_by from request data or default to current user
            paid_by = data.get('paid_by') or g.user_id
            print(f"   Paid by: {paid_by}")
            
            expense = {
                'id': expense_id,
                'expense_id': expense_id,
                'description': data['description'],
                'amount': float(data['amount']),
                'paid_by': paid_by,  # Use paid_by from request or default to current user
                'group_id': None,
                'category': category,
                'split_type': split_type.lower(),
                'currency': data.get('currency', 'USD'),
                'date': expense_date,
                'notes': data.get('notes'),
                'image_url': data.get('image_url'),
                'splits': data['splits'],
                'created_at': current_time.isoformat(),
                'updated_at': current_time.isoformat(),
                'is_deleted': False
            }
            
            print(f"   Expense Object Created:")
            print(f"   - Splits in expense: {expense['splits']}")
            
            # Save to local storage only
            local_storage.save_expense(expense)
            print(f"✅ Saved to local storage")
            print("="*80 + "\n")
            
            return jsonify({'success': True, 'expense': expense}), 201
        
        # GROUP EXPENSES - Use Firebase
        print("\n👥 GROUP EXPENSE - Firebase + Local Storage")
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        print(f"   Group Name: {group.get('name')}")
        print(f"   Group Members: {len(group.get('members', []))}")
        
        # VALIDATION: Require at least 2 members to create group expense
        member_count = len(group.get('members', []))
        if member_count < 2:
            logger.warning(f"❌ Cannot create expense: Group {group_id} has only {member_count} member(s)")
            return jsonify({
                'success': False,
                'error': 'At least 2 members required to create group expense',
                'code': 'INSUFFICIENT_MEMBERS',
                'member_count': member_count
            }), 400
        
        # Calculate splits
        print(f"\n🧮 CALCULATING SPLITS")
        print(f"   Input splits: {data['splits']}")
        splits = calculate_splits(
            data['amount'],
            split_type,
            data['splits']
        )
        print(f"   Calculated splits: {splits}")
        print(f"   Number of splits: {len(splits)}")
        
        # Create expense ID
        expense_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        # Parse date
        if 'date' in data and data['date']:
            try:
                parsed_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                expense_date = parsed_date.strftime('%Y-%m-%d')
            except:
                expense_date = data['date'].split('T')[0] if 'T' in data['date'] else data['date']
        else:
            expense_date = current_time.strftime('%Y-%m-%d')
        
        print(f"   Expense ID: {expense_id}")
        print(f"   Date: {expense_date}")
        
        # Get paid_by from request data or default to current user
        paid_by = data.get('paid_by') or g.user_id
        print(f"   Paid by: {paid_by}")
        
        # Create expense object
        expense = {
            'id': expense_id,
            'expense_id': expense_id,
            'description': data['description'],
            'amount': float(data['amount']),
            'paid_by': paid_by,  # Use paid_by from request or default to current user
            'group_id': group_id,
            'category': category,
            'split_type': split_type.lower(),
            'currency': data.get('currency', group.get('currency', 'USD')),
            'date': expense_date,
            'notes': data.get('notes'),
            'image_url': data.get('image_url'),
            'splits': splits,
            'created_at': current_time.isoformat(),
            'updated_at': current_time.isoformat(),
            'is_deleted': False
        }
        
        print(f"\n💾 SAVING EXPENSE")
        print(f"   Final expense object:")
        print(f"   - Amount: ${expense['amount']}")
        print(f"   - Splits: {expense['splits']}")
        print(f"   - Split count: {len(expense['splits'])}")
        
        # 🚀 OPTIMISTIC CREATE: Return immediately, sync in background
        try:
            print(f"   ⚡ OPTIMISTIC MODE: Creating expense instantly...")
            firebase_expense = expense_service.create_expense(
                description=data['description'],
                amount=data['amount'],
                paid_by=paid_by,  # Use paid_by from request (line 1072), not g.user_id
                category=category,
                splits=splits,
                group_id=group_id,
                split_type=split_type,
                currency=data.get('currency', group.get('currency', 'USD')),
                date=data.get('date'),
                notes=data.get('notes'),
                image_url=data.get('image_url'),
                expense_id=expense_id,
                optimistic=True  # 🚀 INSTANT RESPONSE!
            )
            print(f"   ✅ Response ready (Firebase syncing in background)")
            
            # Save to local storage for immediate UI access
            local_storage.save_expense(expense)
            print(f"   ✅ Saved to local storage")
            
            # 🔥 CRITICAL: Invalidate formatted balance cache BEFORE response
            # 🚀 OPTIMIZATION: Don't delete! Smart ?_t will handle freshness
            try:
                # cache_key = f"expense:formatted_balance:{group_id}"
                # if expense_service.cache.redis_client:
                #     expense_service.cache.redis_client.delete(cache_key)
                #     print(f"   🗑️  Invalidated formatted balance cache (instant)")
                print(f"   ✅ Keeping formatted balance cache (smart ?_t will handle freshness)")
            except Exception as e:
                logger.warning(f"Failed to invalidate balance cache: {e}")
            
            # Send email notifications asynchronously (doesn't block response)
            if group_id:
                print(f"\n📧 STARTING ASYNC EMAIL NOTIFICATIONS")
                send_expense_notifications_async(
                    expense_data=data,
                    splits=splits,
                    paid_by=paid_by,
                    group_name=group.get('name', 'Your Group'),
                    user_id_to_exclude=g.user_id
                )
                print(f"   ✅ Email notifications started in background (non-blocking)")
            
            # 🔒 AUDIT LOG: Track expense creation
            try:
                audit_logger = get_audit_logger(expense_service.firebase.db)
                audit_logger.log_action(
                    action=AuditAction.CREATE_EXPENSE,
                    resource_type='expense',
                    resource_id=expense_id,
                    user_id=g.user_id,
                    details={
                        'group_id': group_id,
                        'amount': float(data['amount']),
                        'currency': data.get('currency', 'USD'),
                        'category': category,
                        'split_count': len(splits)
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Audit logging failed: {audit_error}")
        except Exception as firebase_error:
            logger.error(f"Firebase sync error: {firebase_error}")
            print(f"   ❌ Firebase sync error: {firebase_error}")
            return jsonify({'error': 'Failed to create expense'}), 500
        
        print("="*80 + "\n")
        
        # Build response with optimistic balance data
        response_data = {'success': True, 'expense': expense}
        
        # 🚀 OPTIMISTIC: Calculate and return updated balances for instant UI update
        if group_id:
            try:
                print(f"🧮 Calculating updated balances for optimistic response...")
                # Get balance data using incremental system (already up-to-date)
                balance_result = expense_service.balance_manager.get_group_balances(
                    group_id=group_id
                    # No force_incremental needed - incremental updates keep it current
                )
                
                if balance_result:
                    # Add balance data to response for instant UI update
                    response_data['balances'] = {
                        'member_balances': balance_result.get('balances', []),
                        'debts': balance_result.get('debts', []),
                        'is_settled': balance_result.get('is_settled', False)
                    }
                    print(f"✅ Added balance data to response ({len(balance_result.get('balances', []))} members)")
                else:
                    print(f"⚠️  Balance calculation returned None")
            except Exception as balance_err:
                logger.warning(f"Failed to calculate balances for optimistic response: {balance_err}")
                print(f"⚠️  Balance calculation failed: {balance_err}")
                # Continue without balances - frontend will fetch separately
        
        # IDEMPOTENCY: Cache the response for 24 hours
        if idempotency_key:
            cache_key = f"idempotency:{idempotency_key}"
            lock_key = f"lock:{idempotency_key}"
            try:
                import json
                expense_service.cache.redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(response_data)
                )
                logger.info(f"✅ Cached idempotent response for key: {idempotency_key}")
                print(f"✅ IDEMPOTENCY: Cached response for {idempotency_key} (24h TTL)")
                
                # Release the lock
                if expense_service.cache.redis_client:
                    expense_service.cache.redis_client.delete(lock_key)
                print(f"✅ IDEMPOTENCY: Released lock for {idempotency_key}")
            except Exception as cache_err:
                logger.warning(f"Failed to cache idempotent response: {cache_err}")
                # Try to release lock even if caching failed
                try:
                    if expense_service.cache.redis_client:
                        expense_service.cache.redis_client.delete(lock_key)
                except:
                    pass
        
        return jsonify(response_data), 201
    
    except Exception as e:
        logger.error(f"Error creating expense: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/<expense_id>', methods=['GET'])
@require_auth
def get_expense(expense_id):
    """Get expense details"""
    try:
        expense = expense_service.get_expense(expense_id)
        
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        # Check access
        if expense.get('group_id'):
            group = expense_service.get_group(expense['group_id'])
            if not group or g.user_id not in group.get('members', []):
                return jsonify({'error': 'Access denied'}), 403
        elif expense['paid_by'] != g.user_id:
            # Personal expense - only payer can view
            is_in_split = any(s['user_id'] == g.user_id for s in expense.get('splits', []))
            if not is_in_split:
                return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'success': True, 'expense': expense}), 200
    
    except Exception as e:
        logger.error(f"Error getting expense: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/<expense_id>', methods=['PUT'])
@require_auth
@track_time("UPDATE EXPENSE")
def update_expense(expense_id):
    """Update expense - Only people involved in the expense can edit it"""
    try:
        print("\n" + "="*80)
        print(f"✏️  UPDATE EXPENSE - {expense_id}")
        print("="*80)
        print(f"User ID: {g.user_id}")
        
        # Import Phase 3 change detector
        from expense_engine.utils.change_detector import (
            is_financial_change, get_changed_fields, format_change_summary
        )
        
        # 🔍 CRITICAL FIX: Check local storage first (for personal expenses)
        expense = local_storage.get_expense(expense_id)
        print(f"   Local storage lookup: {'Found' if expense else 'Not found'}")
        
        # If not in local storage, try Firebase (for group expenses)
        if not expense:
            expense = expense_service.get_expense(expense_id)
            print(f"   Firebase lookup: {'Found' if expense else 'Not found'}")
        
        if not expense:
            print(f"❌ Expense not found")
            print("="*80 + "\n")
            return jsonify({'error': 'Expense not found'}), 404
        
        print(f"   Expense: {expense['description']}")
        print(f"   Amount: ${expense['amount']}")
        print(f"   Paid by: {expense['paid_by']}")
        print(f"   Group ID: {expense.get('group_id', 'None (Personal)')}")
        
        # Check if user is involved in this expense
        is_payer = expense['paid_by'] == g.user_id
        is_in_split = any(
            split.get('user_id') == g.user_id 
            for split in expense.get('splits', [])
        )
        
        print(f"   Is payer: {is_payer}")
        print(f"   Is in split: {is_in_split}")
        
        # Only people involved in the expense can update
        if not (is_payer or is_in_split):
            print(f"❌ Access denied")
            print("="*80 + "\n")
            return jsonify({
                'error': 'Access denied',
                'message': 'Only people involved in this expense can edit it.'
            }), 403
        
        data = request.get_json()
        print(f"   Update data: {data}")
        
        # � CRITICAL: Transform frontend format to backend format
        # Frontend: paidBy, splitWith (camelCase)
        # Backend: paid_by, splits (snake_case)
        if 'paidBy' in data:
            data['paid_by'] = data.pop('paidBy')
        if 'splitWith' in data:
            # PRECISION FIX: Transform splitWith array to splits with integer cent arithmetic
            split_users = data.pop('splitWith')
            amount = data.get('amount', expense.get('amount'))
            
            # Use precise cent calculation
            amount_cents = dollars_to_cents(amount)
            split_cents = calculate_equal_split(amount_cents, len(split_users))
            
            data['splits'] = [
                {'user_id': split_users[i], 'amount': cents_to_dollars_float(split_cents[i])}
                for i in range(len(split_users))
            ]
        
        print(f"   Transformed data: {data}")
        
        # PHASE 3: Smart cache invalidation - detect if only metadata changed
        from ..utils.change_detector import is_metadata_only_change
        metadata_only = is_metadata_only_change(expense, data)
        if metadata_only:
            print(f"   🎯 SMART CACHE: Metadata-only change detected (description/category/date)")
            print(f"   💨 Skipping balance cache invalidation (96% faster!)")
        else:
            print(f"   💰 Financial change detected - balance recalculation needed")
        
        # Group expense - OPTIMISTIC UPDATE (instant response)
        if expense.get('group_id'):
            print(f"\n⚡ OPTIMISTIC UPDATE: Updating instantly...")
            success = expense_service.update_expense(expense_id, data, optimistic=True)
            if success:
                # Update local storage immediately for instant UI
                print(f"   🔄 Updating local storage...")
                local_storage.update_expense(expense_id, data)
                updated_expense = local_storage.get_expense(expense_id)
                
                # PHASE 3: Smart cache invalidation - only invalidate if financial data changed
                if not metadata_only:
                    # 🔧 CRITICAL: Invalidate balance cache IMMEDIATELY after update
                    try:
                        cache_key = f"expense:formatted_balance:{expense['group_id']}"
                        if expense_service.cache.redis_client:
                            expense_service.cache.redis_client.delete(cache_key)
                            print(f"   🗑️  Invalidated formatted balance cache (financial change)")
                        else:
                            print(f"   ⚠️  Redis not available - cache not invalidated")
                    except Exception as cache_error:
                        logger.warning(f"Cache invalidation error (non-critical): {cache_error}")
                else:
                    print(f"   ✅ Balance cache preserved (metadata-only change, no recalculation needed)")
                
                print(f"   ✅ Instant update complete (Firebase syncing in background)")
            else:
                print(f"   ❌ Update failed")
        else:
            # Personal expense - update in local storage
            print(f"\n💾 Updating in local storage...")
            success = local_storage.update_expense(expense_id, data)
            if success:
                updated_expense = local_storage.get_expense(expense_id)
                print(f"   ✅ Local storage update successful")
            else:
                print(f"   ❌ Local storage update failed")
        
        if success:
            print(f"✅ UPDATE COMPLETE")
            print("="*80 + "\n")
            return jsonify({'success': True, 'expense': updated_expense}), 200
        else:
            print(f"❌ UPDATE FAILED")
            print("="*80 + "\n")
            return jsonify({'error': 'Failed to update expense'}), 500
    
    except Exception as e:
        logger.error(f"Error updating expense: {e}")
        print(f"❌ EXCEPTION: {e}")
        print("="*80 + "\n")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/<expense_id>', methods=['DELETE'])
@require_auth
@track_time("DELETE EXPENSE")
def delete_expense(expense_id):
    """Delete expense"""
    try:
        print("\n" + "="*80)
        print(f"🗑️  DELETE EXPENSE - {expense_id}")
        print("="*80)
        print(f"User ID: {g.user_id}")
        
        # Try to get from local storage first
        expense = local_storage.get_expense(expense_id)
        print(f"   Local storage lookup: {'Found' if expense else 'Not found'}")
        
        # If not in local storage, try Firebase
        if not expense:
            expense = expense_service.get_expense(expense_id)
            print(f"   Firebase lookup: {'Found' if expense else 'Not found'}")
        
        if not expense:
            print(f"❌ Expense not found")
            print("="*80 + "\n")
            return jsonify({'error': 'Expense not found'}), 404
        
        print(f"   Expense: {expense['description']}")
        print(f"   Amount: ${expense['amount']}")
        print(f"   Paid by: {expense['paid_by']}")
        print(f"   Group ID: {expense.get('group_id', 'None')}")
        
        # Check if user is involved in this expense
        is_payer = expense['paid_by'] == g.user_id
        is_in_split = any(
            split.get('user_id') == g.user_id 
            for split in expense.get('splits', [])
        )
        
        # Allow deletion if: user is involved OR user is group admin
        can_delete = is_payer or is_in_split
        if expense.get('group_id'):
            is_admin = expense_service.is_group_admin(
                expense['group_id'], g.user_id
            )
            can_delete = can_delete or is_admin
            print(f"   Is group admin: {is_admin}")
        
        print(f"   Is payer: {is_payer}")
        print(f"   Is in split: {is_in_split}")
        print(f"   Can delete: {can_delete}")
        
        if not can_delete:
            print(f"❌ Access denied")
            print("="*80 + "\n")
            return jsonify({
                'error': 'Access denied',
                'message': 'Only people involved in this expense can delete it.'
            }), 403
        
        # Delete from both local storage and Firebase in parallel for speed
        print(f"\n💾 DELETING FROM STORAGE (OPTIMIZED)")
        
        group_id = expense.get('group_id')
        
        # Step 1: Delete from local storage (instant)
        local_deleted = local_storage.delete_expense(expense_id)
        print(f"   Local storage: {'✅ Deleted' if local_deleted else '❌ Failed'}")
        
        # Step 2: Queue Firebase deletion (non-blocking)
        if group_id and local_deleted:
            try:
                # Use threading to make Firebase delete non-blocking
                import threading
                
                def delete_from_firebase():
                    try:
                        expense_service.delete_expense(expense_id)
                        print(f"   📤 Firebase: ✅ Deleted (background)")
                    except Exception as fb_error:
                        logger.error(f"Firebase delete error: {fb_error}")
                
                # Start Firebase deletion in background
                firebase_thread = threading.Thread(target=delete_from_firebase, daemon=True)
                firebase_thread.start()
                print(f"   📤 Firebase deletion queued (non-blocking)")
                
            except Exception as firebase_error:
                logger.error(f"Error queueing Firebase delete: {firebase_error}")
                print(f"   ⚠️  Firebase queue error (non-critical): {firebase_error}")
        
        # Send email notifications to all involved users (except who deleted it) - FULLY ASYNC
        if group_id and local_deleted:
            print(f"\n📧 SCHEDULING DELETE NOTIFICATIONS (instant queue)")
            
            try:
                # OPTIMIZATION: Queue emails in background thread (instant)
                import threading
                
                def queue_emails_background():
                    try:
                        from ..workers import get_email_worker
                        email_worker = get_email_worker()
                        
                        # Get deleter info
                        deleter_user = expense_service.get_user(g.user_id)
                        deleter_name = deleter_user.get('display_name') or deleter_user.get('username') or 'Someone'
                        
                        # Get group info (from cache)
                        group = expense_service.get_group(group_id)
                        group_name = group.get('name', 'Your Group') if group else 'Your Group'
                        
                        # Queue emails for each user (except deleter)
                        recipient_emails = []
                        for split in expense.get('splits', []):
                            user_id = split.get('user_id')
                            if user_id != g.user_id:
                                user = expense_service.get_user(user_id)
                                if user and user.get('email'):
                                    recipient_emails.append(user['email'])
                        
                        if recipient_emails:
                            email_worker.queue_email(
                                email_type='expense_deleted',
                                recipients=recipient_emails,
                                data={
                                    'description': expense['description'],
                                    'amount': expense['amount'],
                                    'currency': expense.get('currency', 'USD'),
                                    'deleted_by_name': deleter_name,
                                    'group_name': group_name
                                }
                            )
                            logger.info(f"✅ Queued {len(recipient_emails)} delete notifications")
                    except Exception as email_error:
                        logger.error(f"Error in background email queue: {email_error}")
                
                # Start email queueing in background (instant return)
                email_thread = threading.Thread(target=queue_emails_background, daemon=True)
                email_thread.start()
                print(f"   ✅ Email queueing started (non-blocking)")
                    
            except Exception as email_error:
                logger.error(f"Error starting email thread: {email_error}")
                print(f"   ⚠️  Email thread error (non-critical): {email_error}")
        
        # 🔒 AUDIT LOG: Track expense deletion
        if local_deleted:
            try:
                audit_logger = get_audit_logger(expense_service.firebase.db)
                audit_logger.log_action(
                    action=AuditAction.DELETE_EXPENSE,
                    resource_type='expense',
                    resource_id=expense_id,
                    user_id=g.user_id,
                    details={
                        'group_id': expense.get('group_id'),
                        'amount': expense.get('amount'),
                        'description': expense.get('description'),
                        'currency': expense.get('currency', 'USD')
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Audit logging failed: {audit_error}")
        
        if local_deleted:
            print(f"✅ EXPENSE DELETED SUCCESSFULLY")
            print("="*80 + "\n")
            return jsonify({
                'success': True, 
                'message': 'Expense deleted',
                'group_id': expense.get('group_id')
            }), 200
        else:
            print(f"❌ FAILED TO DELETE EXPENSE")
            print("="*80 + "\n")
            return jsonify({'error': 'Failed to delete expense'}), 500
    
    except Exception as e:
        logger.error(f"Error deleting expense: {e}")
        print(f"❌ ERROR: {e}")
        print("="*80 + "\n")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/personal', methods=['GET'])
@require_auth
def get_personal_expenses():
    """Get personal expenses"""
    try:
        limit = int(request.args.get('limit', 100))
        expenses = expense_service.get_user_personal_expenses(g.user_id, limit)
        return jsonify({'success': True, 'expenses': expenses}), 200
    
    except Exception as e:
        logger.error(f"Error getting personal expenses: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/group/<group_id>', methods=['GET'])
@require_auth
@track_time("GET GROUP EXPENSES")
def get_group_expenses(group_id):
    """Get expenses for a group with pagination support
    
    Query Parameters:
        limit: Maximum number of expenses to return (default: 50, max: 100)
        offset: Number of expenses to skip (default: 0)
    
    Returns:
        JSON with:
            - expenses: List of expense objects
            - pagination: {limit, offset, has_more, returned_count}
    """
    try:
        print(f"\n" + "="*80)
        print(f"📋 GET GROUP EXPENSES (PAGINATED) - {group_id}")
        print("="*80)
        print(f"User ID: {g.user_id}")
        
        # Check access
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            print(f"❌ Access denied")
            print("="*80 + "\n")
            return jsonify({'error': 'Access denied'}), 403
        
        print(f"   Group: {group.get('name')}")
        
        # Get pagination parameters using configured defaults
        try:
            limit = min(
                int(request.args.get('limit', PaginationConfig.DEFAULT_PAGE_SIZE)), 
                PaginationConfig.MAX_PAGE_SIZE
            )
            offset = max(int(request.args.get('offset', 0)), 0)
        except (ValueError, TypeError):
            limit = PaginationConfig.DEFAULT_PAGE_SIZE
            offset = 0
        
        print(f"   Pagination: limit={limit}, offset={offset}")
        
        # Fetch expenses with pagination from service layer
        print(f"\n📦 Fetching expenses with pagination...")
        result = expense_service.get_group_expenses(group_id, limit=limit, offset=offset)
        
        expenses = result.get('expenses', [])
        pagination_info = {
            'limit': result.get('limit', limit),
            'offset': result.get('offset', offset),
            'has_more': result.get('has_more', False),
            'returned_count': result.get('returned_count', len(expenses))
        }
        
        print(f"   Retrieved: {pagination_info['returned_count']} expenses")
        print(f"   Has more: {pagination_info['has_more']}")
        
        # Ensure date format is correct and add type field
        for expense in expenses:
            if expense.get('date') and 'T' in str(expense['date']):
                expense['date'] = expense['date'].split('T')[0]
            # Add type field so frontend can filter
            if 'type' not in expense:
                expense['type'] = 'expense'
        
        print(f"✅ Returning {len(expenses)} expenses with pagination")
        print(f"   Pagination: {pagination_info}")
        print("="*80 + "\n")
        
        return jsonify({
            'success': True,
            'expenses': expenses,
            'pagination': pagination_info
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting group expenses: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/expenses/user', methods=['GET'])
@require_auth
def get_user_all_expenses():
    """Get all expenses for current user"""
    try:
        group_id = request.args.get('group_id')
        limit = int(request.args.get('limit', 100))
        personal_only = request.args.get('personal_only', 'false').lower() == 'true'
        
        logger.info(f"📋 GET USER EXPENSES - User: {g.user_id}, Group: {group_id}, Personal Only: {personal_only}")
        
        # FAST PATH FOR PERSONAL EXPENSES - Use only local storage
        if not group_id or group_id == 'null':
            # Get personal expenses from local storage only
            if personal_only:
                # Filter for ONLY personal expenses (group_id = None)
                expenses = local_storage.get_all_expenses(user_id=g.user_id, group_id=None)
                # Double-check filtering
                expenses = [e for e in expenses if e.get('group_id') is None]
                logger.info(f"   ✅ Filtered to {len(expenses)} personal-only expenses")
            else:
                # Get ALL user expenses (personal + group)
                expenses = local_storage.get_all_expenses(user_id=g.user_id, group_id=None)
            
            # Ensure date format is correct
            for expense in expenses:
                if expense.get('date') and 'T' in str(expense['date']):
                    expense['date'] = expense['date'].split('T')[0]
            
            return jsonify({'success': True, 'expenses': expenses[:limit]}), 200
        
        # GROUP EXPENSES - Get from all members via local storage
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get from local storage - it will aggregate from all members
        expenses = local_storage.get_all_expenses(group_id=group_id)
        
        # Ensure date format is correct
        for expense in expenses:
            if expense.get('date') and 'T' in str(expense['date']):
                expense['date'] = expense['date'].split('T')[0]
        
        # If no local expenses, try Firebase (fallback)
        if not expenses:
            try:
                expenses = expense_service.get_user_expenses(g.user_id, group_id, limit)
            except Exception as firebase_error:
                logger.error(f"Firebase fetch error: {firebase_error}")
                expenses = []
        
        return jsonify({'success': True, 'expenses': expenses[:limit]}), 200
    
    except Exception as e:
        logger.error(f"Error getting user expenses: {e}")
        return jsonify({'error': 'Internal server error'}), 500
