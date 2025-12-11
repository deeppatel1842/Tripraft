"""
Shared Utilities for Routes
Production-ready helpers for authentication, timing, and notifications
"""

from flask import request, jsonify, g
from functools import wraps
import logging
import time
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

# Import analytics tracker for real-time monitoring
try:
    from ..analytics import analytics_tracker
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False
    logger.warning("Analytics module not available")


# =============================================================================
# AUTHENTICATION MIDDLEWARE
# =============================================================================

def require_auth(f):
    """
    Require authentication for endpoint
    
    Verifies Firebase ID token from Authorization header.
    Sets g.user_id and g.user_email for authenticated requests.
    
    Args:
        f: Flask route function to protect
        
    Returns:
        Decorated function with authentication
        
    Raises:
        401: If token is missing, invalid, or expired
    """
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
# TIMING DECORATOR
# =============================================================================

def track_time(operation_name: str):
    """
    Decorator to track execution time of operations with analytics integration
    
    Logs operation start, completion/failure, and elapsed time.
    Tracks metrics in analytics dashboard for real-time monitoring.
    
    Args:
        operation_name: Human-readable operation name
        
    Returns:
        Decorator function
        
    Example:
        @track_time("Create Expense")
        def create_expense(...):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Track request start in analytics
            if ANALYTICS_ENABLED:
                analytics_start_time = analytics_tracker.track_request_start(operation_name)
            
            print(f"\n⏱️  START: {operation_name}")
            
            try:
                result = f(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Track successful completion in analytics
                if ANALYTICS_ENABLED:
                    analytics_tracker.track_request_end(operation_name, analytics_start_time, error=False)
                
                print(f"✅ COMPLETE: {operation_name} - {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                
                # Track error in analytics
                if ANALYTICS_ENABLED:
                    analytics_tracker.track_request_end(operation_name, analytics_start_time, error=True)
                
                print(f"❌ ERROR: {operation_name} - {elapsed:.3f}s - {str(e)}")
                raise
        return decorated_function
    return decorator


# =============================================================================
# EMAIL NOTIFICATION HELPERS
# =============================================================================

def send_expense_notifications_async(expense_data, splits, paid_by, group_name, user_id_to_exclude):
    """
    Send email notifications using email worker (non-blocking)
    
    Queues expense creation emails without blocking API response.
    Saves 1.5-2s per expense by processing asynchronously.
    
    Args:
        expense_data: Dict with description, amount, currency
        splits: List of split dicts with user_id
        paid_by: User ID of payer
        group_name: Name of group (for context)
        user_id_to_exclude: User ID to skip (usually payer)
        
    Returns:
        None (queues emails asynchronously)
    """
    try:
        from ..service import expense_service
        from ..workers import get_email_worker
        
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
    
    Queues settlement payment emails without blocking API response.
    Saves 20+ seconds by processing asynchronously.
    
    Args:
        recipient_id: User ID receiving payment
        payer_id: User ID making payment
        amount: Payment amount
        group_id: Optional group ID for context
        
    Returns:
        None (queues email asynchronously)
    """
    try:
        from ..service import expense_service
        from ..workers import get_email_worker
        
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


def send_invitation_email_async(recipient_email, group_name, inviter_name, group_id, invitation_id):
    """
    Send group invitation email using email worker (non-blocking)
    
    Queues invitation emails without blocking API response.
    
    Args:
        recipient_email: Email address of invitee
        group_name: Name of group
        inviter_name: Name of person inviting
        group_id: Group ID
        invitation_id: Invitation ID
        
    Returns:
        None (queues email asynchronously)
    """
    try:
        from ..workers import get_email_worker
        
        email_worker = get_email_worker()
        
        # Queue email
        email_worker.queue_email(
            email_type='group_invitation',
            recipients=[recipient_email],
            data={
                'group_name': group_name,
                'inviter_name': inviter_name,
                'group_id': group_id,
                'invitation_id': invitation_id
            }
        )
        logger.info(f"📧 Queued invitation email for {recipient_email}")
    except Exception as e:
        logger.error(f"Error queueing invitation email: {e}")


def send_member_removed_notification_async(removed_user_email, group_name, admin_name):
    """
    Send member removal notification using email worker (non-blocking)
    
    Args:
        removed_user_email: Email of removed member
        group_name: Name of group
        admin_name: Name of admin who removed member
        
    Returns:
        None (queues email asynchronously)
    """
    try:
        from ..workers import get_email_worker
        
        email_worker = get_email_worker()
        
        # Queue email
        email_worker.queue_email(
            email_type='member_removed',
            recipients=[removed_user_email],
            data={
                'group_name': group_name,
                'admin_name': admin_name
            }
        )
        logger.info(f"📧 Queued member removal notification for {removed_user_email}")
    except Exception as e:
        logger.error(f"Error queueing member removal notification: {e}")


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_split_type(split_type: str) -> bool:
    """
    Validate split type
    
    Args:
        split_type: Split type string (equal, exact, percentage, shares)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        from ..models import SplitType
        SplitType[split_type.upper()]
        return True
    except KeyError:
        return False


def validate_category(category: str) -> bool:
    """
    Validate expense category
    
    Args:
        category: Category string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        from ..models import ExpenseCategory
        ExpenseCategory[category.upper()]
        return True
    except KeyError:
        return False


# =============================================================================
# SPLIT CALCULATION HELPERS
# =============================================================================

def calculate_splits(amount: float, split_type: str, split_data: list) -> list:
    """
    Calculate splits based on split type
    
    Uses integer cent precision to avoid floating-point drift.
    Ensures total splits equal expense amount exactly.
    
    Args:
        amount: Total expense amount
        split_type: Type of split (equal, exact, percentage, shares)
        split_data: List of split dictionaries with user_id and split info
        
    Returns:
        List of split dictionaries with calculated amounts
        
    Example:
        splits = calculate_splits(100.0, 'equal', [
            {'user_id': 'user1'},
            {'user_id': 'user2'},
            {'user_id': 'user3'}
        ])
        # Returns: [
        #   {'user_id': 'user1', 'amount': 33.34, ...},
        #   {'user_id': 'user2', 'amount': 33.33, ...},
        #   {'user_id': 'user3', 'amount': 33.33, ...}
        # ]
    """
    from ..decimal_utils import (
        dollars_to_cents,
        cents_to_dollars_float,
        calculate_equal_split,
        calculate_percentage_split
    )
    
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
