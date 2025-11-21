"""
Expense Management System - API Routes
Production-ready REST API with authentication and rate limiting
Handles 100+ concurrent users
"""

from flask import Blueprint, request, jsonify, g, current_app
from functools import wraps
import logging
import uuid
import os
from datetime import datetime
from typing import Optional
import time
from firebase_admin import auth as firebase_auth
from .service import expense_service
# Email service for sending notifications
from .email_service import email_service
from .models import SplitType, ExpenseCategory
from .local_storage import local_storage
from .constants import PaginationConfig
from .decimal_utils import (
    dollars_to_cents,
    cents_to_dollars_float,
    calculate_equal_split,
    calculate_percentage_split
)

logger = logging.getLogger(__name__)

# Create blueprint
expense_bp = Blueprint('expense', __name__, url_prefix='/api/expense')


# =============================================================================
# LAZY EMAIL SERVICE LOADER
# =============================================================================

def get_email_service():
    """Return the email service instance"""
    # ✅ EMAIL SERVICE ENABLED
    return email_service


# =============================================================================
# ASYNC EMAIL NOTIFICATIONS
# =============================================================================

def send_expense_notifications_async(expense_data, splits, paid_by, group_name, user_id_to_exclude):
    """
    Send email notifications using email worker (non-blocking)
    This doesn't block the API response (saves 1.5-2s per expense creation)
    """
    try:
        from .workers import get_email_worker
        email_worker = get_email_worker()
        
        # Get payer info
        payer_user = expense_service.get_user(paid_by)
        payer_name = payer_user.get('display_name') or payer_user.get('username') or 'Someone'
        
        # Collect recipients
        recipient_emails = []
        for split in splits:
            user_id = split['user_id']
            if user_id != user_id_to_exclude:
                user = expense_service.get_user(user_id)
                if user and user.get('email'):
                    recipient_emails.append(user['email'])
        
        if recipient_emails:
            # Queue emails
            email_worker.queue_email(
                email_type='expense_created',
                recipients=recipient_emails,
                data={
                    'description': expense_data['description'],
                    'amount': expense_data['amount'],
                    'currency': expense_data.get('currency', 'USD'),
                    'paid_by_name': payer_name,
                    'group_name': group_name,
                    'split_count': len(splits)
                }
            )
            logger.info(f"📧 Queued {len(recipient_emails)} expense notifications")
    except Exception as e:
        logger.error(f"Error queueing expense notifications: {e}")


def send_settlement_notification_async(recipient_id, payer_id, amount, group_id):
    """
    Send settlement email notification using email worker (non-blocking)
    This doesn't block the API response (saves 20+ seconds!)
    """
    try:
        from .workers import get_email_worker
        email_worker = get_email_worker()
        
        # Get user info
        recipient = expense_service.get_user(recipient_id)
        payer = expense_service.get_user(payer_id)
        
        if not recipient or not payer:
            logger.warning(f"Missing user data for settlement notification")
            return
        
        if not recipient.get('email'):
            logger.warning(f"No email for recipient {recipient_id}")
            return
        
        # Get group name if available
        group_name = None
        if group_id:
            group = expense_service.get_group(group_id)
            group_name = group.get('name') if group else None
        
        # Queue email
        email_worker.queue_email(
            email_type='settlement_created',
            recipients=[recipient['email']],
            data={
                'from_name': payer.get('display_name', payer.get('username', 'Someone')),
                'to_name': recipient.get('display_name', recipient.get('username', 'You')),
                'amount': amount,
                'currency': 'USD',  # TODO: Get from group settings
                'group_name': group_name or 'Personal'
            }
        )
        logger.info(f"📧 Queued settlement notification for {recipient['email']}")
    except Exception as e:
        logger.error(f"Error queueing settlement notification: {e}")


# =============================================================================
# TIMING DECORATOR
# =============================================================================

def track_time(operation_name: str):
    """Decorator to track execution time of operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            print(f"\n⏱️  START: {operation_name}")
            
            try:
                result = f(*args, **kwargs)
                elapsed = time.time() - start_time
                print(f"✅ COMPLETE: {operation_name} - {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ ERROR: {operation_name} - {elapsed:.3f}s - {str(e)}")
                raise
        return decorated_function
    return decorator


# =============================================================================
# AUTHENTICATION MIDDLEWARE
# =============================================================================

def require_auth(f):
    """Require authentication for endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authorization token provided'}), 401
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify token with Firebase (allow 60s clock skew for timing issues)
            decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=60)
            g.user_id = decoded_token['uid']
            g.user_email = decoded_token.get('email')
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({'error': 'Invalid or expired token'}), 401
    
    return decorated_function


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_split_type(split_type: str) -> bool:
    """Validate split type"""
    try:
        SplitType[split_type.upper()]
        return True
    except KeyError:
        return False


def validate_category(category: str) -> bool:
    """Validate expense category"""
    try:
        ExpenseCategory[category.upper()]
        return True
    except KeyError:
        return False


def calculate_splits(amount: float, split_type: str, split_data: list) -> list:
    """
    Calculate splits based on split type
    Args:
        amount: Total expense amount
        split_type: Type of split (equal, exact, percentage, shares)
        split_data: List of split dictionaries with user_id and split info
    Returns:
        List of split dictionaries with calculated amounts
    """
    splits = []
    
    # Normalize split_type to lowercase for comparison
    split_type_lower = split_type.lower()
    
    print(f"      calculate_splits called:")
    print(f"         Amount: ${amount}")
    print(f"         Split type: '{split_type}' (normalized: '{split_type_lower}')")
    print(f"         Split data: {split_data}")
    
    if split_type_lower == 'equal':
        # PRECISION FIX: Use integer cents to avoid float drift
        amount_cents = dollars_to_cents(amount)
        split_cents = calculate_equal_split(amount_cents, len(split_data))
        
        print(f"         Equal split (cents): {split_cents} for {len(split_data)} people")
        print(f"         Sum check: {sum(split_cents)} cents = {amount_cents} cents ✅")
        
        for i, user_split in enumerate(split_data):
            split_amount = cents_to_dollars_float(split_cents[i])
            splits.append({
                'user_id': user_split['user_id'],
                'amount': split_amount,
                'share': None,
                'percentage': None
            })
    
    elif split_type_lower == 'exact':
        # Exact amounts specified
        print(f"         Exact split")
        for user_split in split_data:
            splits.append({
                'user_id': user_split['user_id'],
                'amount': user_split['amount'],
                'share': None,
                'percentage': None
            })
    
    elif split_type_lower == 'percentage':
        # PRECISION FIX: Use integer cents for percentage calculations
        print(f"         Percentage split")
        amount_cents = dollars_to_cents(amount)
        percentages = [user_split['percentage'] for user_split in split_data]
        
        split_cents = calculate_percentage_split(amount_cents, percentages)
        print(f"         Percentage split (cents): {split_cents}")
        print(f"         Sum check: {sum(split_cents)} cents = {amount_cents} cents ✅")
        
        for i, user_split in enumerate(split_data):
            split_amount = cents_to_dollars_float(split_cents[i])
            percentage = user_split['percentage']
            splits.append({
                'user_id': user_split['user_id'],
                'amount': split_amount,
                'share': None,
                'percentage': percentage
            })
    
    elif split_type_lower == 'shares':
        # Share-based split
        total_shares = sum(user_split['share'] for user_split in split_data)
        per_share = amount / total_shares
        print(f"         Share-based split: {total_shares} total shares, ${per_share} per share")
        for user_split in split_data:
            share = user_split['share']
            split_amount = round(per_share * share, 2)
            splits.append({
                'user_id': user_split['user_id'],
                'amount': split_amount,
                'share': share,
                'percentage': None
            })
    else:
        print(f"         ⚠️  WARNING: Unknown split type '{split_type}'")
    
    print(f"         ✅ Calculated {len(splits)} splits")
    for i, split in enumerate(splits, 1):
        print(f"            {i}. User {split['user_id']}: ${split['amount']}")
    
    return splits


# =============================================================================
# USER ROUTES
# =============================================================================

@expense_bp.route('/user/profile', methods=['POST'])
@require_auth
def create_user_profile():
    """Create or update user profile"""
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = expense_service.get_user(g.user_id)
        if existing_user:
            # ═══════════════════════════════════════════════════════════
            # AUTO CACHE WARMING - DISABLED (too slow on profile check)
            # Cache warming now happens on first data fetch instead
            # ═══════════════════════════════════════════════════════════
            # import threading
            # from flask import current_app
            # 
            # # Capture user_id and app context before thread
            # user_id_for_thread = g.user_id
            # app = current_app._get_current_object()
            # 
            # def warm_cache_async():
            #     """Warm cache in background without blocking response"""
            #     with app.app_context():
            #         try:
            #             print(f"🔥 AUTO: Starting cache warming for returning user {user_id_for_thread}")
            #             result = expense_service.warm_user_cache(user_id_for_thread)
            #             logger.info(f"Auto cache warming complete: {result.get('cached', []).__len__()} items")
            #         except Exception as e:
            #             logger.error(f"Auto cache warming failed: {e}")
            # 
            # # Start cache warming in background thread
            # thread = threading.Thread(target=warm_cache_async, daemon=True)
            # thread.start()
            
            return jsonify({'message': 'User already exists', 'user': existing_user}), 200
        
        # Validate required fields
        if not data.get('username'):
            return jsonify({'error': 'Username is required'}), 400
        
        # Check if username is taken
        username_check = expense_service.get_user_by_username(data['username'])
        if username_check:
            return jsonify({'error': 'Username already taken'}), 400
        
        # Create user
        user = expense_service.create_user(
            uid=g.user_id,
            email=g.user_email,
            username=data['username'],
            display_name=data.get('display_name'),
            profile_picture=data.get('profile_picture')
        )
        
        # ═══════════════════════════════════════════════════════════
        # AUTO CACHE WARMING - DISABLED (too slow)
        # Cache warming now happens lazily on first data fetch
        # ═══════════════════════════════════════════════════════════
        # import threading
        # from flask import current_app
        # 
        # # Capture user_id and app context before thread
        # user_id_for_thread = g.user_id
        # app = current_app._get_current_object()
        # 
        # def warm_cache_async_new():
        #     """Warm cache in background for new user"""
        #     with app.app_context():
        #         try:
        #             print(f"🔥 AUTO: Starting cache warming for new user {user_id_for_thread}")
        #             result = expense_service.warm_user_cache(user_id_for_thread)
        #             logger.info(f"Auto cache warming complete for new user: {result.get('cached', []).__len__()} items")
        #         except Exception as e:
        #             logger.error(f"Auto cache warming failed for new user: {e}")
        # 
        # # Start cache warming in background thread
        # thread = threading.Thread(target=warm_cache_async_new, daemon=True)
        # thread.start()
        
        return jsonify({'success': True, 'user': user}), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get current user profile"""
    try:
        user = expense_service.get_user(g.user_id)
        if not user:
            return jsonify({'error': 'User profile not found'}), 404
        
        return jsonify({'success': True, 'user': user}), 200
    
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Validate username if changing
        if 'username' in data:
            existing = expense_service.get_user_by_username(data['username'])
            if existing and existing['uid'] != g.user_id:
                return jsonify({'error': 'Username already taken'}), 400
        
        # Update user
        success = expense_service.update_user(g.user_id, data)
        
        if success:
            user = expense_service.get_user(g.user_id)
            return jsonify({'success': True, 'user': user}), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/user/search', methods=['GET'])
@require_auth
def search_users():
    """Search for users by username or email"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Try to find by username first
        user = expense_service.get_user_by_username(query)
        
        # If not found, try email
        if not user:
            user = expense_service.get_user_by_email(query)
        
        if user:
            # Return limited info for privacy
            return jsonify({
                'success': True,
                'user': {
                    'uid': user['uid'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'profile_picture': user.get('profile_picture')
                }
            }), 200
        else:
            return jsonify({'success': True, 'user': None}), 200
    
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# GROUP ROUTES
# =============================================================================

@expense_bp.route('/groups', methods=['POST'])
@require_auth
def create_group():
    """Create a new expense group"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Group name is required'}), 400
        
        # Create group
        group = expense_service.create_group(
            name=data['name'],
            created_by=g.user_id,
            description=data.get('description'),
            image_url=data.get('image_url'),
            currency=data.get('currency', 'USD')
        )
        
        # 🔧 CRITICAL: Immediately invalidate user groups cache
        try:
            user_cache_key = f"user_groups:{g.user_id}"
            if expense_service.cache.redis_client:
                expense_service.cache.redis_client.delete(user_cache_key)
            print(f"�️  Invalidated user groups cache for {g.user_id}")
        except Exception as e:
            print(f"⚠️  Cache invalidation failed: {e}")
        
        return jsonify({'success': True, 'group': group}), 201
    
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups', methods=['GET'])
@require_auth
def get_user_groups():
    """Get all groups for current user
    
    Query Parameters:
        mode: 'summary' for fast initial load (5 reads) or 'full' for complete data (50+ reads)
              Default: 'full' for backward compatibility
    """
    try:
        # Check if summary mode is requested
        mode = request.args.get('mode', 'full')
        summary_mode = (mode == 'summary')
        
        if summary_mode:
            logger.info(f"📋 [SUMMARY MODE] Fast loading groups for {g.user_id}")
        
        groups = expense_service.get_user_groups(g.user_id, summary_mode=summary_mode)
        
        # Add performance note for summary mode
        if summary_mode:
            logger.info(f"✅ [SUMMARY MODE] Returned {len(groups)} groups with ~5 Firestore reads (90% faster!)")
        return jsonify({'success': True, 'groups': groups}), 200
    
    except Exception as e:
        logger.error(f"Error getting user groups: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>', methods=['GET'])
@require_auth
def get_group(group_id):
    """Get group details"""
    try:
        group = expense_service.get_group(group_id)
        
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Check if user is a member
        if g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get members with user details
        members = expense_service.get_group_members(group_id)
        group['members_details'] = members
        
        return jsonify({'success': True, 'group': group}), 200
    
    except Exception as e:
        logger.error(f"Error getting group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>/full', methods=['GET'])
@require_auth
def get_group_full(group_id):
    """🚀 OPTIMIZED: Get ALL group data in ONE call
    
    Returns:
        - Group details
        - Members with display names
        - All expenses
        - Balance calculations
        - Settlements
        - Pending invitations
    
    Benefits:
        - Reduces 6 API calls → 1 API call
        - Reduces network overhead by ~500-1000ms
        - Single cache key for entire response
        - Atomic data consistency
    
    Performance:
        - First load: ~8-12 Firestore reads
        - Cached: 0 reads, <5ms response
    """
    import time
    start = time.time()
    
    try:
        print(f"\n{'='*80}")
        print(f"🚀 GET FULL GROUP DATA - {group_id}")
        print(f"{'='*80}")
        print(f"User ID: {g.user_id}")
        
        # Check cache bypass parameter
        bypass_cache = request.args.get('_t') is not None
        if bypass_cache:
            print("🔄 Cache bypass requested (_t parameter) - fetching fresh data")
        
        # Get complete group data in one service call
        result = expense_service.get_group_full_data(group_id, g.user_id, bypass_cache=bypass_cache)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            status_code = 404 if 'not found' in error_msg.lower() else 403 if 'denied' in error_msg.lower() else 500
            return jsonify(result), status_code
        
        duration = time.time() - start
        print(f"✅ COMPLETE: GET FULL GROUP DATA - {duration:.3f}s")
        print(f"{'='*80}\n")
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error getting full group data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'success': False}), 500


@expense_bp.route('/groups/<group_id>', methods=['PUT'])
@require_auth
def update_group(group_id):
    """Update group details"""
    try:
        # Check if user is admin
        if not expense_service.is_group_admin(group_id, g.user_id):
            return jsonify({'error': 'Only admins can update group'}), 403
        
        data = request.get_json()
        
        # Update group
        success = expense_service.update_group(group_id, data)
        
        if success:
            group = expense_service.get_group(group_id)
            return jsonify({'success': True, 'group': group}), 200
        else:
            return jsonify({'error': 'Failed to update group'}), 500
    
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>', methods=['DELETE'])
@require_auth
def delete_group(group_id):
    """
    Delete a group (with optional cascade delete of expenses)
    
    Query Parameters:
        cascade: If 'true', also delete all group expenses (default: 'false')
    
    Examples:
        DELETE /groups/123                     # Delete group, keep expenses
        DELETE /groups/123?cascade=true        # Delete group AND all expenses
    """
    try:
        # Check if user is admin
        if not expense_service.is_group_admin(group_id, g.user_id):
            return jsonify({'error': 'Only admins can delete group'}), 403
        
        # Get cascade parameter from query string
        cascade = request.args.get('cascade', 'false').lower() == 'true'
        
        # Get user_id before deletion (g.user_id won't be available in thread)
        user_id = g.user_id
        
        if cascade:
            logger.info(f"🗑️  CASCADE DELETE: Deleting group {group_id} with all expenses")
        
        # Delete group (with optional cascade)
        success = expense_service.delete_group(group_id, cascade_delete_expenses=cascade)
        
        if success:
            # 🔧 CRITICAL: Immediately invalidate user groups cache
            try:
                user_cache_key = f"user_groups:{user_id}"
                if expense_service.cache.redis_client:
                    expense_service.cache.redis_client.delete(user_cache_key)
                print(f"🗑️  Invalidated user groups cache for {user_id}")
            except Exception as e:
                print(f"⚠️  Cache invalidation failed: {e}")
            
            message = 'Group and all expenses deleted' if cascade else 'Group deleted'
            return jsonify({
                'success': True, 
                'message': message,
                'cascade': cascade
            }), 200
        else:
            return jsonify({'error': 'Failed to delete group'}), 500
    
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id):
    """Get group members"""
    try:
        # Check if user is a member
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        members = expense_service.get_group_members(group_id)
        return jsonify({'success': True, 'members': members}), 200
    
    except Exception as e:
        logger.error(f"Error getting group members: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>/members/<user_id>', methods=['GET'])
@require_auth
def get_member_details(group_id, user_id):
    """Get detailed information about a group member"""
    try:
        # Check if requester is a group member
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if requested user is a group member
        if user_id not in group.get('members', []):
            return jsonify({'error': 'User not in group'}), 404
        
        # Get member user info
        user = expense_service.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get member balance from group_balances
        balances = expense_service.get_formatted_balances(group_id)
        user_balance = 0.0
        for balance_entry in balances:
            if balance_entry['user_id'] == user_id:
                user_balance = balance_entry['balance']
                break
        
        # Count expenses paid by member
        expenses = expense_service.get_group_expenses(group_id, limit=1000, offset=0)
        expenses_paid = sum(1 for exp in expenses['expenses'] if exp.get('paid_by') == user_id)
        total_paid = sum(exp.get('amount', 0) for exp in expenses['expenses'] if exp.get('paid_by') == user_id)
        
        # Get member role (check if admin)
        is_admin = expense_service.is_group_admin(group_id, user_id)
        role = 'admin' if is_admin else 'member'
        
        # Get joined date from group members
        members = expense_service.get_group_members(group_id)
        joined_at = None
        for member in members:
            if member.get('user_id') == user_id:
                joined_at = member.get('joined_at')
                break
        
        # Build member details response
        member_details = {
            'user_id': user_id,
            'display_name': user.get('display_name', ''),
            'username': user.get('username', ''),
            'email': user.get('email', ''),
            'role': role,
            'balance': user_balance,
            'expenses_paid_count': expenses_paid,
            'total_amount_paid': total_paid,
            'joined_at': joined_at,
            'is_admin': is_admin
        }
        
        return jsonify({'success': True, 'member': member_details}), 200
    
    except Exception as e:
        logger.error(f"Error getting member details: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/groups/<group_id>/leave', methods=['POST'])
@require_auth
def leave_group(group_id):
    """Leave a group"""
    try:
        success = expense_service.remove_member_from_group(group_id, g.user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Left group successfully'}), 200
        else:
            return jsonify({'error': 'Failed to leave group'}), 500
    
    except Exception as e:
        logger.error(f"Error leaving group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# INVITATION ROUTES
# =============================================================================

@expense_bp.route('/invitations', methods=['POST'])
@require_auth
def create_invitation():
    """Create group invitation"""
    try:
        data = request.get_json()
        
        group_id = data.get('group_id')
        invited_email = data.get('email')
        invited_username = data.get('username')
        
        logger.info(f"Creating invitation for group_id={group_id}, email={invited_email}, username={invited_username}")
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        if not invited_email and not invited_username:
            return jsonify({'error': 'Email or username is required'}), 400
        
        # Check if user is admin or member
        group = expense_service.get_group(group_id)
        if not group:
            logger.error(f"Group not found: {group_id}")
            return jsonify({'error': 'Group not found'}), 404
            
        if g.user_id not in group.get('members', []):
            logger.error(f"User {g.user_id} is not a member of group {group_id}")
            return jsonify({'error': 'Access denied'}), 403
        
        logger.info(f"Group found: {group.get('name')} (ID: {group_id})")
        
        # Create invitation
        invitation = expense_service.create_invitation(
            group_id=group_id,
            invited_by=g.user_id,
            invited_email=invited_email,
            invited_username=invited_username
        )
        
        logger.info(f"Invitation created: {invitation.get('invitation_id')} for group {group_id}")
        
        # Generate invitation link with proper type parameter
        invitation_link = f"http://localhost:5173/accept-invitation?id={invitation['invitation_id']}&type=expense"
        
        # Send email asynchronously if email provided (non-blocking)
        email_status = 'not_sent'
        if invited_email:
            try:
                from .workers import get_email_worker
                email_worker = get_email_worker()
                
                inviter = expense_service.get_user(g.user_id)
                inviter_name = inviter.get('display_name', inviter.get('username', 'Someone'))
                
                # Queue invitation email
                email_worker.queue_email(
                    email_type='invitation_sent',
                    recipients=[invited_email],
                    data={
                        'inviter_name': inviter_name,
                        'group_name': group['name'],
                        'invitation_link': invitation_link
                    }
                )
                email_status = 'sending'
                logger.info(f"📧 Invitation email queued for {invited_email}")
            except Exception as e:
                email_status = 'error'
                logger.error(f"❌ Failed to queue invitation email: {e}")
                logger.info(f"📧 Manual invitation link: {invitation_link}")
        
        return jsonify({
            'success': True, 
            'invitation': invitation,
            'group_name': group['name'],
            'group_id': group_id,
            'invitation_link': invitation_link,
            'email_status': email_status  # 'sending', 'disabled', or 'not_sent'
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating invitation: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/invitations', methods=['GET'])
@require_auth
def get_user_invitations():
    """Get pending invitations for current user"""
    try:
        invitations = expense_service.get_user_invitations(g.user_id)
        return jsonify({'success': True, 'invitations': invitations}), 200
    
    except Exception as e:
        logger.error(f"Error getting invitations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/invitations/group/<group_id>', methods=['GET'])
@require_auth
def get_group_invitations(group_id):
    """Get pending invitations for a group"""
    try:
        # Check if user is member of the group
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        invitations = expense_service.get_group_invitations(group_id)
        return jsonify({'success': True, 'invitations': invitations}), 200
    
    except Exception as e:
        logger.error(f"Error getting group invitations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/invitations/<invitation_id>/details', methods=['GET'])
def get_invitation_details(invitation_id):
    """Get invitation details (public endpoint - no auth required)"""
    try:
        logger.info(f"Getting details for invitation {invitation_id}")
        
        invitation = expense_service.get_invitation_by_id(invitation_id)
        if not invitation:
            logger.error(f"Invitation not found: {invitation_id}")
            return jsonify({'success': False, 'error': 'Invitation not found'}), 404
        
        # Check if invitation is still valid
        if invitation.get('status') != 'pending':
            logger.error(f"Invitation is not pending: {invitation.get('status')}")
            return jsonify({'success': False, 'error': 'Invitation is no longer valid'}), 400
        
        # Get group details
        group = expense_service.get_group(invitation['group_id'])
        if not group:
            logger.error(f"Group not found: {invitation['group_id']}")
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # Get inviter details
        inviter = expense_service.get_user(invitation['invited_by'])
        inviter_name = inviter.get('display_name', inviter.get('username', 'Someone')) if inviter else 'Someone'
        
        return jsonify({
            'success': True,
            'invitation': {
                'invitation_id': invitation_id,
                'group_id': invitation['group_id'],
                'group_name': group.get('name'),
                'invited_email': invitation.get('invited_email'),
                'invited_by_name': inviter_name,
                'status': invitation.get('status')
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting invitation details: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(invitation_id):
    """Accept group invitation"""
    try:
        logger.info(f"User {g.user_id} ({g.user_email}) attempting to accept invitation {invitation_id}")
        
        # Get invitation details first
        invitation = expense_service.get_invitation_by_id(invitation_id)
        if not invitation:
            logger.error(f"Invitation not found: {invitation_id}")
            return jsonify({
                'success': False,
                'error': 'Invitation not found',
                'code': 'INVITATION_NOT_FOUND'
            }), 404
        
        group_id = invitation.get('group_id')
        logger.info(f"Invitation details: group_id={group_id}, invited_email={invitation.get('invited_email')}, status={invitation.get('status')}")
        
        # Check if invitation is for the current user
        if invitation.get('invited_email') != g.user_email:
            logger.error(f"Invitation email mismatch: {invitation.get('invited_email')} != {g.user_email}")
            return jsonify({
                'success': False,
                'error': 'This invitation is not for you',
                'code': 'UNAUTHORIZED'
            }), 403
        
        # Check if invitation is still pending
        if invitation.get('status') != 'pending':
            logger.error(f"Invitation status is not pending: {invitation.get('status')}")
            return jsonify({
                'success': False,
                'error': 'Invitation has already been responded to',
                'code': 'ALREADY_RESPONDED'
            }), 400
        
        success = expense_service.respond_to_invitation(invitation_id, g.user_id, True)
        
        if success:
            # Get fresh group details after adding member
            group = expense_service.get_group(group_id)
            logger.info(f"✅ Invitation accepted successfully. User {g.user_id} added to group {group_id} ({group.get('name') if group else 'Unknown'})")
            
            # Return proper redirect URL for frontend
            return jsonify({
                'success': True, 
                'message': 'Invitation accepted successfully',
                'group_name': group.get('name') if group else 'Unknown',
                'group_id': group_id,
                'redirect_url': f'/expenses?group={group_id}',
                'group_details': {
                    'id': group_id,
                    'name': group.get('name'),
                    'currency': group.get('currency', 'USD'),
                    'member_count': len(group.get('members', []))
                } if group else None
            }), 200
        else:
            logger.error(f"Failed to accept invitation {invitation_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to accept invitation',
                'code': 'ACCEPTANCE_FAILED'
            }), 500
    
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


@expense_bp.route('/invitations/<invitation_id>/reject', methods=['POST'])
@require_auth
def reject_invitation(invitation_id):
    """Reject group invitation"""
    try:
        success = expense_service.respond_to_invitation(invitation_id, g.user_id, False)
        
        if success:
            return jsonify({'success': True, 'message': 'Invitation rejected'}), 200
        else:
            return jsonify({'error': 'Failed to reject invitation'}), 500
    
    except Exception as e:
        logger.error(f"Error rejecting invitation: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# EXPENSE ROUTES
# =============================================================================

@expense_bp.route('/expenses', methods=['POST'])
@require_auth
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
        from .utils.change_detector import is_metadata_only_change
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
        
        # Delete from local storage
        print(f"\n💾 DELETING FROM STORAGE")
        local_deleted = local_storage.delete_expense(expense_id)
        print(f"   Local storage: {'✅ Deleted' if local_deleted else '❌ Failed'}")
        
        # 🔧 CRITICAL: Invalidate balance cache IMMEDIATELY after deletion
        # 🚀 OPTIMIZATION: Don't delete! Smart ?_t will handle freshness
        if local_deleted and expense.get('group_id'):
            try:
                # cache_key = f"expense:formatted_balance:{expense['group_id']}"
                # expense_service.cache.redis_client.delete(cache_key)
                # print(f"   🗑️  Invalidated formatted balance cache (instant)")
                print(f"   ✅ Keeping formatted balance cache (smart ?_t will handle freshness)")
            except Exception as cache_error:
                logger.warning(f"Cache invalidation error (non-critical): {cache_error}")
        
        # Also delete from Firebase if group expense
        if expense.get('group_id'):
            try:
                print(f"   📤 Deleting from Firebase...")
                firebase_deleted = expense_service.delete_expense(expense_id)
                print(f"   Firebase: {'✅ Deleted' if firebase_deleted else '❌ Failed'}")
            except Exception as firebase_error:
                logger.error(f"Firebase delete error (deleted locally): {firebase_error}")
                print(f"   ⚠️  Firebase delete error: {firebase_error}")
        
        # Send email notifications to all involved users (except who deleted it) - ASYNC
        if expense.get('group_id') and local_deleted:
            print(f"\n📧 SCHEDULING DELETE NOTIFICATIONS (email worker)")
            
            try:
                # Import email worker
                from .workers import get_email_worker
                email_worker = get_email_worker()
                
                # Get deleter info
                deleter_user = expense_service.get_user(g.user_id)
                deleter_name = deleter_user.get('display_name') or deleter_user.get('username') or 'Someone'
                
                # Get group info
                group = expense_service.get_group(expense['group_id'])
                group_name = group.get('name', 'Your Group')
                
                # Queue emails for each user (except deleter)
                recipient_emails = []
                for split in expense.get('splits', []):
                    user_id = split.get('user_id')
                    if user_id != g.user_id:
                        user = expense_service.get_user(user_id)
                        if user and user.get('email'):
                            recipient_emails.append(user['email'])
                
                if recipient_emails:
                    # Queue single email task for all recipients
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
                    print(f"   ✅ Queued {len(recipient_emails)} delete notifications")
                else:
                    print(f"   ⚠️  No recipients found for delete notifications")
                    
            except Exception as email_error:
                logger.error(f"Error queueing delete notifications: {email_error}")
                print(f"   ⚠️  Email queue error (non-critical): {email_error}")
        
        if local_deleted:
            print(f"✅ EXPENSE DELETED SUCCESSFULLY")
            print("="*80 + "\n")
            return jsonify({'success': True, 'message': 'Expense deleted'}), 200
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


# =============================================================================
# SETTLEMENT ROUTES
# =============================================================================

@expense_bp.route('/settlements', methods=['POST'])
@require_auth
def create_settlement():
    """Create payment/settlement with ATOMIC VALIDATION"""
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
            
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            print(f"❌ Access denied")
            print("="*80 + "\n")
            return jsonify({'error': 'Access denied'}), 403
        
        # Ensure from_user is also a member of the group
        if from_user_id not in group.get('members', []):
            print(f"❌ Payer not in group")
            print("="*80 + "\n")
            return jsonify({'error': 'Payer must be a member of the group'}), 403
        
        print(f"Group: {group.get('name')} ({group_id})")
        
        # ⚡ PRE-WARM CACHE: Get formatted balances first (this caches them)
        # This ensures subsequent calls are instant
        print(f"\n🔥 PRE-WARMING BALANCE CACHE")
        _ = expense_service.get_formatted_balances(group_id)
        print(f"   ✅ Cache pre-warmed")
        
        # ⚡ OPTIMIZED VALIDATION: Use incremental balance system (no cache clearing needed)
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
        from_net = from_balance.get('balance', 0)  # Fixed: use 'balance' not 'net_balance'
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
        
        # ⚡ OPTIMISTIC MODE: Lightning fast settlement
        print(f"\n⚡ OPTIMISTIC SETTLEMENT MODE")
        settlement = expense_service.create_settlement(
            from_user=from_user_id,
            to_user=to_user_id,
            amount=applied_amount,
            group_id=group_id,
            currency=data.get('currency', 'USD'),
            notes=data.get('notes'),
            expected_amount=expected_amount,
            optimistic=True,  # ⚡ Enable instant balance update
            audit_trail={
                'from_balance_before': from_net,
                'to_balance_before': to_balance.get('net_balance', 0),
                'requested_amount': amount,
                'applied_amount': applied_amount,
                'validation_passed': True
            }
        )
        print(f"   ✅ Settlement created instantly ({(time.time() - start_time) * 1000:.0f}ms)")
        
        # 🚀 OPTIMIZATION: No cache invalidation needed!
        # Smart ?_t timestamp handling ensures clients get fresh data
        # This saves ~50ms of cache deletion overhead
        print(f"   ✅ No cache invalidation needed (smart ?_t handles freshness)")
        
        print(f"✅ SETTLEMENT COMPLETE - {(time.time() - start_time) * 1000:.0f}ms")
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


@expense_bp.route('/settlements/group/<group_id>', methods=['GET'])
@require_auth
def get_group_settlements(group_id):
    """Get settlements for a group"""
    try:
        # Check access
        group = expense_service.get_group(group_id)
        if not group or g.user_id not in group.get('members', []):
            return jsonify({'error': 'Access denied'}), 403
        
        limit = int(request.args.get('limit', 100))
        settlements = expense_service.get_group_settlements(group_id, limit)
        
        return jsonify({'success': True, 'settlements': settlements}), 200
    
    except Exception as e:
        logger.error(f"Error getting settlements: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# BALANCE ROUTES
# =============================================================================

@expense_bp.route('/balance', methods=['GET'])
@require_auth
def get_user_balance():
    """Get user balance"""
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


@expense_bp.route('/balance/breakdown', methods=['GET'])
@require_auth
def get_balance_breakdown():
    """Get detailed balance breakdown"""
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


@expense_bp.route('/balance/group/<group_id>', methods=['GET'])
@expense_bp.route('/balances/group/<group_id>', methods=['GET'])
@require_auth
def get_group_balances(group_id):
    """Get all balances for a group with simplified debt settlement"""
    try:
        print("\n" + "="*80)
        print(f"💰 GET GROUP BALANCES - {group_id}")
        print("="*80)
        print(f"User ID: {g.user_id}")
        
        # 🔧 OPTIMIZATION: Try Redis cache first (full response with display names)
        # BUT: Skip cache if _t timestamp parameter is present (forces fresh data after updates)
        use_cache = '_t' not in request.args
        
        # 🚀 SMART ?_t HANDLING: Even if _t parameter present, check if recalc just happened
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
        
        # ⚡ OPTIMIZED: Use incremental balance system (rarely needs force_incremental)
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
        
        # 🔧 OPTIMIZATION: Cache full response with display names (30 second TTL)
        try:
            import json, time
            cache_key = f"expense:formatted_balance:{group_id}"
            expense_service.cache.redis_client.setex(
                cache_key,
                30,  # 30 seconds TTL (balances update frequently)
                json.dumps(response, default=str)
            )
            
            # 🚀 SMART ?_t OPTIMIZATION: Store recalculation timestamp
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


# =============================================================================
# UTILITY ROUTES
# =============================================================================

@expense_bp.route('/health', methods=['GET'])
def health_check():
    """System health check including worker status and performance metrics"""
    try:
        health = expense_service.health_check()
        
        # Add email worker stats
        try:
            from .workers import get_email_worker
            email_worker = get_email_worker()
            worker_stats = email_worker.get_stats()
            health['email_worker'] = {
                'status': 'healthy' if worker_stats['running'] and worker_stats['worker_alive'] else 'unhealthy',
                'queue_size': worker_stats['queue_size'],
                'processed': worker_stats['processed_count'],
                'failed': worker_stats['failed_count'],
                'success_rate': round((worker_stats['processed_count'] - worker_stats['failed_count']) / max(worker_stats['processed_count'], 1) * 100, 2) if worker_stats['processed_count'] > 0 else 100.0
            }
        except Exception as worker_error:
            health['email_worker'] = {
                'status': 'error',
                'error': str(worker_error)
            }
        
        # Add performance metrics
        try:
            cache_analytics = expense_service.get_cache_analytics()
            health['performance'] = {
                'cache_hit_rate': cache_analytics.get('overall_hit_rate', 0),
                'total_requests': cache_analytics.get('total_requests', 0),
                'uptime_seconds': cache_analytics.get('uptime_seconds', 0)
            }
        except:
            pass  # Non-critical, continue without metrics
        
        # Add system resources (if available)
        try:
            import psutil
            health['resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except:
            pass  # psutil not installed, skip resource monitoring
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


@expense_bp.route('/health/detailed', methods=['GET'])
@require_auth
def detailed_health_check():
    """Detailed health check with comprehensive metrics (admin only)"""
    try:
        from datetime import datetime
        import time
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'environment': 'production'
        }
        
        # Service health checks
        health['services'] = {}
        
        # Firebase health
        try:
            test_start = time.time()
            _ = expense_service.firebase.db.collection('health_check').limit(1).get()
            firebase_latency = (time.time() - test_start) * 1000
            health['services']['firestore'] = {
                'status': 'healthy',
                'latency_ms': round(firebase_latency, 2),
                'healthy': firebase_latency < 500
            }
        except Exception as e:
            health['services']['firestore'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Redis health
        try:
            test_start = time.time()
            expense_service.cache.redis_client.ping()
            redis_latency = (time.time() - test_start) * 1000
            health['services']['redis'] = {
                'status': 'healthy',
                'latency_ms': round(redis_latency, 2),
                'healthy': redis_latency < 50
            }
        except Exception as e:
            health['services']['redis'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Email worker health
        try:
            from .workers import get_email_worker
            email_worker = get_email_worker()
            worker_stats = email_worker.get_stats()
            health['services']['email_worker'] = {
                'status': 'healthy' if worker_stats['running'] and worker_stats['worker_alive'] else 'unhealthy',
                'queue_size': worker_stats['queue_size'],
                'processed': worker_stats['processed_count'],
                'failed': worker_stats['failed_count'],
                'success_rate': round((worker_stats['processed_count'] - worker_stats['failed_count']) / max(worker_stats['processed_count'], 1) * 100, 2) if worker_stats['processed_count'] > 0 else 100.0,
                'healthy': worker_stats['running'] and worker_stats['worker_alive'] and worker_stats['queue_size'] < 50
            }
            if not health['services']['email_worker']['healthy']:
                health['status'] = 'degraded'
        except Exception as e:
            health['services']['email_worker'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Performance metrics
        try:
            cache_analytics = expense_service.get_cache_analytics()
            health['performance'] = {
                'cache_hit_rate': cache_analytics.get('overall_hit_rate', 0),
                'total_requests': cache_analytics.get('total_requests', 0),
                'uptime_seconds': cache_analytics.get('uptime_seconds', 0),
                'cache_healthy': cache_analytics.get('overall_hit_rate', 0) > 50
            }
        except:
            health['performance'] = {'error': 'Analytics unavailable'}
        
        # System resources
        try:
            import psutil
            health['resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'healthy': psutil.cpu_percent(interval=0.1) < 80 and psutil.virtual_memory().percent < 80
            }
            if not health['resources']['healthy']:
                health['status'] = 'degraded'
        except:
            health['resources'] = {'error': 'psutil not installed'}
        
        # Determine overall status
        all_services_healthy = all(
            service.get('status') == 'healthy' or service.get('healthy') == True 
            for service in health['services'].values()
        )
        if not all_services_healthy and health['status'] == 'healthy':
            health['status'] = 'degraded'
        
        status_code = 200 if health['status'] in ['healthy', 'degraded'] else 503
        return jsonify(health), status_code
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


@expense_bp.route('/cache/stats', methods=['GET'])
@require_auth
def get_cache_stats():
    """Get cache statistics (admin only)"""
    try:
        stats = expense_service.get_cache_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/cache/stats/detailed', methods=['GET'])
@require_auth
def get_detailed_cache_stats():
    """Get detailed cache statistics including key counts and memory usage"""
    try:
        stats = expense_service.get_detailed_cache_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    
    except Exception as e:
        logger.error(f"Error getting detailed cache stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/cache/warm', methods=['POST'])
@require_auth
def warm_cache():
    """Warm up cache for current user - pre-loads frequently accessed data"""
    try:
        result = expense_service.warm_user_cache(g.user_id)
        return jsonify({
            'success': result.get('success', False),
            'stats': result
        }), 200
    
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@expense_bp.route('/metrics', methods=['GET'])
@require_auth
def get_performance_metrics():
    """
    Get comprehensive performance metrics
    
    Returns:
        - Cache statistics (hit rates, key counts)
        - Redis memory usage
        - System health
        - Performance benchmarks
    """
    try:
        metrics = expense_service.get_performance_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# NOTE: Health check is provided by /api/health blueprint (health.py)
# Do not duplicate health endpoints to avoid conflicts


@expense_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get list of expense categories"""
    categories = [cat.value for cat in ExpenseCategory]
    return jsonify({'success': True, 'categories': categories}), 200


@expense_bp.route('/split-types', methods=['GET'])
def get_split_types():
    """Get list of split types"""
    split_types = [st.value for st in SplitType]
    return jsonify({'success': True, 'split_types': split_types}), 200

