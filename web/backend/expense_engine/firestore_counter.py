"""
Firestore Operation Counter
Tracks Firestore reads, writes, and deletes per request

Phase 5: Performance Optimization
"""
import threading
from typing import Dict, Any, Optional
from flask import g, has_request_context
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Thread-local storage for per-request counters
_local = threading.local()


class FirestoreOperationCounter:
    """
    Tracks Firestore operations per request
    
    Usage:
        counter = FirestoreOperationCounter()
        counter.read(1)  # Track 1 read
        counter.write(2)  # Track 2 writes
        
        stats = counter.get_stats()
        # {'reads': 1, 'writes': 2, 'deletes': 0, 'total': 3}
    """
    
    def __init__(self):
        self.reads = 0
        self.writes = 0
        self.deletes = 0
        self.collections: Dict[str, Dict[str, int]] = {}
    
    def read(self, count: int = 1, collection: Optional[str] = None):
        """Record Firestore read operation(s)"""
        self.reads += count
        if collection:
            if collection not in self.collections:
                self.collections[collection] = {'reads': 0, 'writes': 0, 'deletes': 0}
            self.collections[collection]['reads'] += count
    
    def write(self, count: int = 1, collection: Optional[str] = None):
        """Record Firestore write operation(s)"""
        self.writes += count
        if collection:
            if collection not in self.collections:
                self.collections[collection] = {'reads': 0, 'writes': 0, 'deletes': 0}
            self.collections[collection]['writes'] += count
    
    def delete(self, count: int = 1, collection: Optional[str] = None):
        """Record Firestore delete operation(s)"""
        self.deletes += count
        if collection:
            if collection not in self.collections:
                self.collections[collection] = {'reads': 0, 'writes': 0, 'deletes': 0}
            self.collections[collection]['deletes'] += count
    
    @property
    def total(self) -> int:
        """Total operations count"""
        return self.reads + self.writes + self.deletes
    
    def get_stats(self) -> Dict[str, Any]:
        """Get operation statistics"""
        return {
            'reads': self.reads,
            'writes': self.writes,
            'deletes': self.deletes,
            'total': self.total,
            'by_collection': self.collections if self.collections else None
        }
    
    def reset(self):
        """Reset counters"""
        self.reads = 0
        self.writes = 0
        self.deletes = 0
        self.collections.clear()


def init_operation_counter():
    """Initialize Firestore operation counter for current request"""
    if has_request_context():
        g.firestore_counter = FirestoreOperationCounter()


def get_operation_counter() -> Optional[FirestoreOperationCounter]:
    """Get the current request's Firestore counter"""
    if has_request_context() and hasattr(g, 'firestore_counter'):
        return g.firestore_counter
    return None


def record_read(count: int = 1, collection: Optional[str] = None):
    """Record Firestore read(s) for current request"""
    counter = get_operation_counter()
    if counter:
        counter.read(count, collection)


def record_write(count: int = 1, collection: Optional[str] = None):
    """Record Firestore write(s) for current request"""
    counter = get_operation_counter()
    if counter:
        counter.write(count, collection)


def record_delete(count: int = 1, collection: Optional[str] = None):
    """Record Firestore delete(s) for current request"""
    counter = get_operation_counter()
    if counter:
        counter.delete(count, collection)


def get_request_stats() -> Optional[Dict[str, Any]]:
    """Get Firestore stats for current request"""
    counter = get_operation_counter()
    if counter:
        return counter.get_stats()
    return None


def log_firestore_operations():
    """Log Firestore operations for current request (call in after_request)"""
    counter = get_operation_counter()
    if counter and counter.total > 0:
        stats = counter.get_stats()
        logger.info(
            "🔥 Firestore: %d reads, %d writes, %d deletes (total: %d)",
            stats['reads'], stats['writes'], stats['deletes'], stats['total']
        )
        
        # Also record in global performance monitor
        try:
            from expense_engine.monitoring import get_performance_monitor
            monitor = get_performance_monitor()
            
            if stats['reads'] > 0:
                monitor.record_firestore_read(stats['reads'])
            if stats['writes'] > 0:
                monitor.record_firestore_write(stats['writes'])
            if stats['deletes'] > 0:
                monitor.record_firestore_delete(stats['deletes'])
        except Exception:
            pass


def track_reads(count: int = 1, collection: Optional[str] = None):
    """Decorator to track Firestore reads"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            record_read(count, collection)
            return result
        return wrapper
    return decorator


def track_writes(count: int = 1, collection: Optional[str] = None):
    """Decorator to track Firestore writes"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            record_write(count, collection)
            return result
        return wrapper
    return decorator


def track_deletes(count: int = 1, collection: Optional[str] = None):
    """Decorator to track Firestore deletes"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            record_delete(count, collection)
            return result
        return wrapper
    return decorator
