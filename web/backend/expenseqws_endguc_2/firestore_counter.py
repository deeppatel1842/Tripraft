"""
Firestore Operation Counter
Tracks read, write, delete, and snapshot operations for monitoring costs
Integrated with analytics dashboard for real-time monitoring
"""
import logging
from functools import wraps
from flask import g, request
import time

logger = logging.getLogger(__name__)

# Import analytics tracker
try:
    from .analytics import analytics_tracker
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False
    logger.warning("Analytics module not available for Firestore tracking")


class FirestoreOperationCounter:
    """Thread-safe counter for Firestore operations"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all counters"""
        self.reads = 0
        self.writes = 0
        self.deletes = 0
        self.snapshots = 0
    
    def increment_read(self, count=1):
        """Increment read counter"""
        self.reads += count
    
    def increment_write(self, count=1):
        """Increment write counter"""
        self.writes += count
    
    def increment_delete(self, count=1):
        """Increment delete counter"""
        self.deletes += count
    
    def increment_snapshot(self, count=1):
        """Increment snapshot counter"""
        self.snapshots += count
    
    def get_totals(self):
        """Get operation totals"""
        return {
            'reads': self.reads,
            'writes': self.writes,
            'deletes': self.deletes,
            'snapshots': self.snapshots,
            'total': self.reads + self.writes + self.deletes + self.snapshots
        }
    
    def get_summary(self):
        """Get formatted summary string"""
        totals = self.get_totals()
        return (f"Firestore Ops: {totals['total']} total "
                f"(R:{totals['reads']} W:{totals['writes']} "
                f"D:{totals['deletes']} S:{totals['snapshots']})")


def init_operation_counter():
    """Initialize operation counter for the request"""
    if not hasattr(g, 'firestore_counter'):
        g.firestore_counter = FirestoreOperationCounter()


def log_firestore_operations():
    """Log Firestore operations at the end of the request"""
    if hasattr(g, 'firestore_counter'):
        totals = g.firestore_counter.get_totals()
        if totals['total'] > 0:
            endpoint = request.endpoint or 'unknown'
            method = request.method
            path = request.path
            summary = g.firestore_counter.get_summary()
            
            # Color code based on total operations
            if totals['total'] > 10:
                level = logging.WARNING
                marker = "⚠️  HIGH"
            elif totals['total'] > 5:
                level = logging.INFO
                marker = "ℹ️  MEDIUM"
            else:
                level = logging.DEBUG
                marker = "✅ LOW"
            
            # Print detailed breakdown
            print(f"\n{'='*80}")
            print(f"📊 FIRESTORE API CALLS - {method} {path}")
            print(f"{'='*80}")
            print(f"   Reads:      {totals['reads']}")
            print(f"   Writes:     {totals['writes']}")
            print(f"   Deletes:    {totals['deletes']}")
            print(f"   Snapshots:  {totals['snapshots']}")
            print(f"   {'─'*76}")
            print(f"   TOTAL:      {totals['total']} operations - {marker}")
            print(f"{'='*80}\n")
            
            logger.log(level, f"{marker} [{method} {endpoint}] {summary}")


def count_firestore_operation(operation_type='read', count=1):
    """
    Manually count a Firestore operation
    Tracks both in request context and analytics dashboard
    
    Args:
        operation_type: 'read', 'write', 'delete', or 'snapshot'
        count: Number of operations (default 1)
    """
    # Track in request context (for per-request logging)
    if hasattr(g, 'firestore_counter'):
        if operation_type == 'read':
            g.firestore_counter.increment_read(count)
        elif operation_type == 'write':
            g.firestore_counter.increment_write(count)
        elif operation_type == 'delete':
            g.firestore_counter.increment_delete(count)
        elif operation_type == 'snapshot':
            g.firestore_counter.increment_snapshot(count)
    
    # Track in analytics dashboard (for real-time monitoring)
    if ANALYTICS_ENABLED:
        analytics_tracker.track_firestore_op(operation_type, count)


def track_firestore_ops(func):
    """
    Decorator to track Firestore operations for a function
    Use this on database operation methods
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Count based on function name patterns
        func_name = func.__name__.lower()
        
        # Execute the function
        result = wrapper(*args, **kwargs)
        
        # Auto-count based on function name if counter exists
        if hasattr(g, 'firestore_counter'):
            if 'get_' in func_name or 'list_' in func_name or 'find_' in func_name:
                # Read operations
                if isinstance(result, list):
                    count_firestore_operation('read', len(result) if result else 1)
                else:
                    count_firestore_operation('read', 1 if result else 0)
            
            elif 'create_' in func_name or 'add_' in func_name or 'update_' in func_name or 'save_' in func_name:
                # Write operations
                count_firestore_operation('write', 1)
            
            elif 'delete_' in func_name or 'remove_' in func_name:
                # Delete operations
                count_firestore_operation('delete', 1)
        
        return result
    
    return wrapper
