"""
Operation Logger - Detailed Terminal Logging for Firestore and Redis Operations
Phase 6: Enhanced Observability

Provides color-coded, detailed logging for all data operations:
- Firestore reads, writes, deletes
- Redis cache hits, misses, sets, invalidations
- Request-level statistics
"""

import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from flask import g, has_request_context
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ANSI Color Codes for Terminal Output
# =============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    
    # Regular colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bold colors
    BOLD = '\033[1m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_MAGENTA = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class OperationType(Enum):
    """Types of data operations"""
    # Firestore operations
    FIRESTORE_READ = "FS_READ"
    FIRESTORE_WRITE = "FS_WRITE"
    FIRESTORE_DELETE = "FS_DELETE"
    FIRESTORE_QUERY = "FS_QUERY"
    FIRESTORE_BATCH = "FS_BATCH"
    FIRESTORE_TRANSACTION = "FS_TRANSACTION"
    
    # Redis operations
    CACHE_HIT = "CACHE_HIT"
    CACHE_MISS = "CACHE_MISS"
    CACHE_SET = "CACHE_SET"
    CACHE_DELETE = "CACHE_DELETE"
    CACHE_INVALIDATE = "CACHE_INVALIDATE"


@dataclass
class OperationRecord:
    """Record of a single operation"""
    op_type: OperationType
    collection: Optional[str] = None
    key: Optional[str] = None
    doc_id: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


class RequestOperationTracker:
    """
    Tracks all operations for a single request
    Thread-safe for concurrent operations
    """
    
    def __init__(self, request_id: str = None):
        self.request_id = request_id or "unknown"
        self.start_time = datetime.utcnow()
        self._lock = threading.Lock()
        
        # Firestore counters
        self.firestore_reads = 0
        self.firestore_writes = 0
        self.firestore_deletes = 0
        self.firestore_queries = 0
        
        # Redis counters
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_sets = 0
        self.cache_deletes = 0
        
        # Detailed operation log
        self.operations: List[OperationRecord] = []
        
        # Per-collection breakdown
        self.collections: Dict[str, Dict[str, int]] = {}
    
    def record_firestore_read(
        self, 
        collection: str, 
        doc_id: str = None, 
        count: int = 1,
        duration_ms: float = 0
    ):
        """Record a Firestore read operation"""
        with self._lock:
            self.firestore_reads += count
            self._update_collection_stats(collection, 'reads', count)
            
            record = OperationRecord(
                op_type=OperationType.FIRESTORE_READ,
                collection=collection,
                doc_id=doc_id,
                duration_ms=duration_ms,
                details={'count': count}
            )
            self.operations.append(record)
            
            # Log immediately to terminal
            self._log_operation(record)
    
    def record_firestore_write(
        self, 
        collection: str, 
        doc_id: str = None, 
        count: int = 1,
        duration_ms: float = 0,
        operation: str = "set"
    ):
        """Record a Firestore write operation"""
        with self._lock:
            self.firestore_writes += count
            self._update_collection_stats(collection, 'writes', count)
            
            record = OperationRecord(
                op_type=OperationType.FIRESTORE_WRITE,
                collection=collection,
                doc_id=doc_id,
                duration_ms=duration_ms,
                details={'count': count, 'operation': operation}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_firestore_delete(
        self, 
        collection: str, 
        doc_id: str = None, 
        count: int = 1,
        duration_ms: float = 0
    ):
        """Record a Firestore delete operation"""
        with self._lock:
            self.firestore_deletes += count
            self._update_collection_stats(collection, 'deletes', count)
            
            record = OperationRecord(
                op_type=OperationType.FIRESTORE_DELETE,
                collection=collection,
                doc_id=doc_id,
                duration_ms=duration_ms,
                details={'count': count}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_firestore_query(
        self, 
        collection: str, 
        result_count: int = 0,
        duration_ms: float = 0,
        filters: List[str] = None
    ):
        """Record a Firestore query operation"""
        with self._lock:
            self.firestore_queries += 1
            self.firestore_reads += result_count  # Each doc in result is a read
            self._update_collection_stats(collection, 'reads', result_count)
            
            record = OperationRecord(
                op_type=OperationType.FIRESTORE_QUERY,
                collection=collection,
                duration_ms=duration_ms,
                details={'result_count': result_count, 'filters': filters}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_cache_hit(
        self, 
        key: str, 
        duration_ms: float = 0,
        data_size: int = 0
    ):
        """Record a cache hit"""
        with self._lock:
            self.cache_hits += 1
            
            record = OperationRecord(
                op_type=OperationType.CACHE_HIT,
                key=key,
                duration_ms=duration_ms,
                details={'data_size': data_size}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_cache_miss(self, key: str, duration_ms: float = 0):
        """Record a cache miss"""
        with self._lock:
            self.cache_misses += 1
            
            record = OperationRecord(
                op_type=OperationType.CACHE_MISS,
                key=key,
                duration_ms=duration_ms
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_cache_set(
        self, 
        key: str, 
        ttl: int = 0, 
        duration_ms: float = 0,
        data_size: int = 0
    ):
        """Record a cache set operation"""
        with self._lock:
            self.cache_sets += 1
            
            record = OperationRecord(
                op_type=OperationType.CACHE_SET,
                key=key,
                duration_ms=duration_ms,
                details={'ttl': ttl, 'data_size': data_size}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def record_cache_delete(
        self, 
        key: str, 
        duration_ms: float = 0,
        pattern: bool = False
    ):
        """Record a cache delete/invalidation"""
        with self._lock:
            self.cache_deletes += 1
            
            record = OperationRecord(
                op_type=OperationType.CACHE_DELETE if not pattern else OperationType.CACHE_INVALIDATE,
                key=key,
                duration_ms=duration_ms,
                details={'pattern': pattern}
            )
            self.operations.append(record)
            self._log_operation(record)
    
    def _update_collection_stats(self, collection: str, op_type: str, count: int):
        """Update per-collection statistics"""
        if collection not in self.collections:
            self.collections[collection] = {'reads': 0, 'writes': 0, 'deletes': 0}
        self.collections[collection][op_type] += count
    
    def _log_operation(self, record: OperationRecord):
        """Log operation to terminal with color coding"""
        op = record.op_type
        
        # Color and emoji based on operation type
        if op == OperationType.FIRESTORE_READ:
            color = Colors.CYAN
            icon = "R"
            prefix = "FIRESTORE"
        elif op == OperationType.FIRESTORE_WRITE:
            color = Colors.YELLOW
            icon = "W"
            prefix = "FIRESTORE"
        elif op == OperationType.FIRESTORE_DELETE:
            color = Colors.RED
            icon = "D"
            prefix = "FIRESTORE"
        elif op == OperationType.FIRESTORE_QUERY:
            color = Colors.MAGENTA
            icon = "Q"
            prefix = "FIRESTORE"
        elif op == OperationType.CACHE_HIT:
            color = Colors.GREEN
            icon = "+"
            prefix = "CACHE"
        elif op == OperationType.CACHE_MISS:
            color = Colors.RED
            icon = "-"
            prefix = "CACHE"
        elif op == OperationType.CACHE_SET:
            color = Colors.BLUE
            icon = "S"
            prefix = "CACHE"
        elif op in (OperationType.CACHE_DELETE, OperationType.CACHE_INVALIDATE):
            color = Colors.YELLOW
            icon = "X"
            prefix = "CACHE"
        else:
            color = Colors.WHITE
            icon = "?"
            prefix = "OP"
        
        # Build log message
        duration_str = f"{record.duration_ms:.1f}ms" if record.duration_ms > 0 else ""
        
        if record.collection:
            target = f"{record.collection}"
            if record.doc_id:
                target += f"/{record.doc_id[:8]}..."
        elif record.key:
            # Truncate long keys
            key_display = record.key if len(record.key) < 50 else f"{record.key[:47]}..."
            target = key_display
        else:
            target = ""
        
        # Format details
        detail_str = ""
        if record.details:
            if 'count' in record.details and record.details['count'] > 1:
                detail_str = f" [{record.details['count']} docs]"
            elif 'result_count' in record.details:
                detail_str = f" [{record.details['result_count']} results]"
            elif 'ttl' in record.details:
                detail_str = f" [TTL={record.details['ttl']}s]"
        
        # Print colored log
        log_msg = f"{color}[{prefix}][{icon}]{Colors.RESET} {target}{detail_str} {Colors.CYAN}{duration_str}{Colors.RESET}"
        print(log_msg)
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    @property
    def total_firestore_ops(self) -> int:
        """Total Firestore operations"""
        return self.firestore_reads + self.firestore_writes + self.firestore_deletes
    
    @property
    def total_cache_ops(self) -> int:
        """Total cache operations"""
        return self.cache_hits + self.cache_misses + self.cache_sets + self.cache_deletes
    
    def get_summary(self) -> Dict[str, Any]:
        """Get operation summary for the request"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        return {
            'request_id': self.request_id,
            'duration_ms': elapsed,
            'firestore': {
                'reads': self.firestore_reads,
                'writes': self.firestore_writes,
                'deletes': self.firestore_deletes,
                'queries': self.firestore_queries,
                'total': self.total_firestore_ops,
                'by_collection': self.collections
            },
            'cache': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'sets': self.cache_sets,
                'deletes': self.cache_deletes,
                'hit_rate': self.cache_hit_rate,
                'total': self.total_cache_ops
            },
            'operation_count': len(self.operations)
        }
    
    def print_summary(self):
        """Print colored summary to terminal"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        # Determine overall status color
        if self.cache_hit_rate >= 0.9:
            status_color = Colors.GREEN
        elif self.cache_hit_rate >= 0.7:
            status_color = Colors.YELLOW
        else:
            status_color = Colors.RED
        
        # Determine latency color
        if elapsed < 100:
            latency_color = Colors.GREEN
        elif elapsed < 500:
            latency_color = Colors.YELLOW
        else:
            latency_color = Colors.RED
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD_CYAN}REQUEST SUMMARY{Colors.RESET}")
        print(f"{'='*60}")
        
        # Latency
        print(f"  {latency_color}Latency: {elapsed:.1f}ms{Colors.RESET}")
        
        # Firestore stats
        print(f"\n  {Colors.BOLD}FIRESTORE:{Colors.RESET}")
        print(f"    {Colors.CYAN}Reads:   {self.firestore_reads}{Colors.RESET}")
        print(f"    {Colors.YELLOW}Writes:  {self.firestore_writes}{Colors.RESET}")
        print(f"    {Colors.RED}Deletes: {self.firestore_deletes}{Colors.RESET}")
        print(f"    {Colors.MAGENTA}Queries: {self.firestore_queries}{Colors.RESET}")
        
        # Per-collection breakdown if any
        if self.collections:
            print(f"\n    {Colors.BOLD}By Collection:{Colors.RESET}")
            for coll, stats in self.collections.items():
                print(f"      {coll}: R={stats['reads']} W={stats['writes']} D={stats['deletes']}")
        
        # Cache stats
        print(f"\n  {Colors.BOLD}CACHE:{Colors.RESET}")
        print(f"    {Colors.GREEN}Hits:    {self.cache_hits}{Colors.RESET}")
        print(f"    {Colors.RED}Misses:  {self.cache_misses}{Colors.RESET}")
        print(f"    {Colors.BLUE}Sets:    {self.cache_sets}{Colors.RESET}")
        print(f"    {Colors.YELLOW}Deletes: {self.cache_deletes}{Colors.RESET}")
        print(f"    {status_color}Hit Rate: {self.cache_hit_rate*100:.1f}%{Colors.RESET}")
        
        print(f"{'='*60}\n")


# =============================================================================
# Request Context Integration
# =============================================================================

def init_request_tracker(request_id: str = None) -> RequestOperationTracker:
    """Initialize operation tracker for current request"""
    if has_request_context():
        tracker = RequestOperationTracker(request_id)
        g.operation_tracker = tracker
        return tracker
    return RequestOperationTracker(request_id)


def get_request_tracker() -> Optional[RequestOperationTracker]:
    """Get the current request's operation tracker"""
    if has_request_context() and hasattr(g, 'operation_tracker'):
        return g.operation_tracker
    return None


def finalize_request_tracker():
    """Finalize and log request operations"""
    tracker = get_request_tracker()
    if tracker:
        tracker.print_summary()
        return tracker.get_summary()
    return None


# =============================================================================
# Convenience Functions (for use in repositories/services)
# =============================================================================

def log_firestore_read(collection: str, doc_id: str = None, count: int = 1, duration_ms: float = 0):
    """Log a Firestore read operation"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_firestore_read(collection, doc_id, count, duration_ms)
    else:
        # Fallback to simple logging
        print(f"{Colors.CYAN}[FIRESTORE][R]{Colors.RESET} {collection}/{doc_id or ''}")


def log_firestore_write(collection: str, doc_id: str = None, count: int = 1, duration_ms: float = 0, operation: str = "set"):
    """Log a Firestore write operation"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_firestore_write(collection, doc_id, count, duration_ms, operation)
    else:
        print(f"{Colors.YELLOW}[FIRESTORE][W]{Colors.RESET} {collection}/{doc_id or ''}")


def log_firestore_delete(collection: str, doc_id: str = None, count: int = 1, duration_ms: float = 0):
    """Log a Firestore delete operation"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_firestore_delete(collection, doc_id, count, duration_ms)
    else:
        print(f"{Colors.RED}[FIRESTORE][D]{Colors.RESET} {collection}/{doc_id or ''}")


def log_firestore_query(collection: str, result_count: int = 0, duration_ms: float = 0, filters: List[str] = None):
    """Log a Firestore query operation"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_firestore_query(collection, result_count, duration_ms, filters)
    else:
        print(f"{Colors.MAGENTA}[FIRESTORE][Q]{Colors.RESET} {collection} [{result_count} results]")


def log_cache_hit(key: str, duration_ms: float = 0, data_size: int = 0):
    """Log a cache hit"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_cache_hit(key, duration_ms, data_size)
    else:
        print(f"{Colors.GREEN}[CACHE][+]{Colors.RESET} {key}")


def log_cache_miss(key: str, duration_ms: float = 0):
    """Log a cache miss"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_cache_miss(key, duration_ms)
    else:
        print(f"{Colors.RED}[CACHE][-]{Colors.RESET} {key}")


def log_cache_set(key: str, ttl: int = 0, duration_ms: float = 0, data_size: int = 0):
    """Log a cache set"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_cache_set(key, ttl, duration_ms, data_size)
    else:
        print(f"{Colors.BLUE}[CACHE][S]{Colors.RESET} {key} [TTL={ttl}s]")


def log_cache_delete(key: str, duration_ms: float = 0, pattern: bool = False):
    """Log a cache delete/invalidation"""
    tracker = get_request_tracker()
    if tracker:
        tracker.record_cache_delete(key, duration_ms, pattern)
    else:
        print(f"{Colors.YELLOW}[CACHE][X]{Colors.RESET} {key}")


# =============================================================================
# Decorators for automatic logging
# =============================================================================

def track_firestore_operation(op_type: str = 'read', collection: str = None):
    """
    Decorator to automatically track Firestore operations
    
    Usage:
        @track_firestore_operation('write', 'expense_expenses')
        def create_expense(data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = datetime.utcnow()
            result = func(*args, **kwargs)
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            
            coll = collection or (args[0].get_collection_name() if hasattr(args[0], 'get_collection_name') else 'unknown')
            
            if op_type == 'read':
                log_firestore_read(coll, duration_ms=duration)
            elif op_type == 'write':
                log_firestore_write(coll, duration_ms=duration)
            elif op_type == 'delete':
                log_firestore_delete(coll, duration_ms=duration)
            
            return result
        return wrapper
    return decorator


def track_cache_operation(func):
    """
    Decorator to automatically track cache operations
    Expects function to return (value, was_hit) tuple
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = datetime.utcnow()
        result = func(*args, **kwargs)
        duration = (datetime.utcnow() - start).total_seconds() * 1000
        
        # Extract key from args (assumes first arg after self is key)
        key = args[1] if len(args) > 1 else kwargs.get('key', 'unknown')
        
        if isinstance(result, tuple) and len(result) == 2:
            value, was_hit = result
            if was_hit:
                log_cache_hit(key, duration)
            else:
                log_cache_miss(key, duration)
            return value
        
        return result
    return wrapper
