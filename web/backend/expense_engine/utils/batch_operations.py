"""
Batch Operations Utility
Phase 14: Reduce Firestore operations through parallel reads and atomic batch writes

This module provides utilities for:
1. Parallel document reads (reduce sequential read latency)
2. Atomic batch writes (reduce individual write operations)
3. Transaction helpers for consistent multi-document updates
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from firebase_admin import firestore
from google.cloud.firestore_v1 import DocumentReference, DocumentSnapshot
from google.cloud.firestore_v1.transforms import Increment
import logging
import time

logger = logging.getLogger(__name__)

# Maximum batch size for Firestore (500 operations per batch)
MAX_BATCH_SIZE = 500

# Thread pool for parallel reads
_executor: Optional[ThreadPoolExecutor] = None


def get_executor() -> ThreadPoolExecutor:
    """Get or create thread pool executor for parallel operations."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=10)
    return _executor


def parallel_read(refs: List[DocumentReference]) -> List[Optional[Dict[str, Any]]]:
    """
    Read multiple documents in parallel using thread pool.
    
    Args:
        refs: List of Firestore DocumentReference objects
        
    Returns:
        List of document data dicts (or None for non-existent docs)
        Order matches input refs order
    
    Example:
        group_ref = db.collection('expense_groups').document(group_id)
        balance_ref = db.collection('expense_group_balances').document(group_id)
        
        group_data, balance_data = parallel_read([group_ref, balance_ref])
    """
    if not refs:
        return []
    
    start_time = time.time()
    executor = get_executor()
    
    # Map to track original order
    future_to_index = {}
    results = [None] * len(refs)
    
    def fetch_doc(ref: DocumentReference) -> Tuple[int, Optional[Dict]]:
        """Fetch single document and return with index."""
        try:
            doc = ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.warning("Failed to fetch document %s: %s", ref.path, str(e))
            return None
    
    # Submit all read tasks
    futures = []
    for i, ref in enumerate(refs):
        future = executor.submit(fetch_doc, ref)
        future_to_index[future] = i
        futures.append(future)
    
    # Collect results maintaining order
    for future in as_completed(futures):
        index = future_to_index[future]
        try:
            results[index] = future.result()
        except Exception as e:
            logger.error("Error in parallel read: %s", str(e))
            results[index] = None
    
    elapsed = (time.time() - start_time) * 1000
    logger.debug(
        "Parallel read of %d documents completed in %.2fms",
        len(refs), elapsed
    )
    
    return results


def batch_get_all(refs: List[DocumentReference]) -> List[DocumentSnapshot]:
    """
    Use Firestore's native get_all for batched reads.
    
    This is the most efficient way to read multiple documents as it uses
    a single network request.
    
    Args:
        refs: List of DocumentReference objects
        
    Returns:
        List of DocumentSnapshot objects
    """
    if not refs:
        return []
    
    start_time = time.time()
    db = firestore.client()
    
    # Firestore's get_all is optimized for batch reads
    snapshots = list(db.get_all(refs))
    
    elapsed = (time.time() - start_time) * 1000
    logger.debug(
        "Batch get_all of %d documents completed in %.2fms",
        len(refs), elapsed
    )
    
    return snapshots


def batch_get_all_as_dicts(refs: List[DocumentReference]) -> List[Optional[Dict[str, Any]]]:
    """
    Batch read multiple documents and return as dicts.
    
    Args:
        refs: List of DocumentReference objects
        
    Returns:
        List of document data dicts (None for non-existent docs)
    """
    snapshots = batch_get_all(refs)
    return [
        snap.to_dict() if snap.exists else None
        for snap in snapshots
    ]


class BatchWriter:
    """
    Context manager for atomic batch writes.
    
    Automatically commits the batch when exiting the context.
    Supports up to 500 operations per batch.
    
    Example:
        with BatchWriter() as batch:
            batch.set(expense_ref, expense_data)
            batch.update(balance_ref, {'amount': Increment(10)})
            batch.update(summary_ref, summary_updates)
        # Commits automatically on exit
    """
    
    def __init__(self, db=None):
        """
        Initialize batch writer.
        
        Args:
            db: Firestore client (uses default if None)
        """
        self._db = db or firestore.client()
        self._batch = self._db.batch()
        self._operation_count = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._operation_count > 0:
            self.commit()
        return False
    
    def set(
        self,
        ref: DocumentReference,
        data: Dict[str, Any],
        merge: bool = False
    ) -> 'BatchWriter':
        """
        Add a set operation to the batch.
        
        Args:
            ref: Document reference
            data: Document data
            merge: If True, merge with existing data
            
        Returns:
            Self for chaining
        """
        self._check_batch_size()
        self._batch.set(ref, data, merge=merge)
        self._operation_count += 1
        return self
    
    def update(
        self,
        ref: DocumentReference,
        data: Dict[str, Any]
    ) -> 'BatchWriter':
        """
        Add an update operation to the batch.
        
        Args:
            ref: Document reference
            data: Fields to update
            
        Returns:
            Self for chaining
        """
        self._check_batch_size()
        self._batch.update(ref, data)
        self._operation_count += 1
        return self
    
    def delete(self, ref: DocumentReference) -> 'BatchWriter':
        """
        Add a delete operation to the batch.
        
        Args:
            ref: Document reference
            
        Returns:
            Self for chaining
        """
        self._check_batch_size()
        self._batch.delete(ref)
        self._operation_count += 1
        return self
    
    def commit(self) -> None:
        """Commit all batched operations atomically."""
        if self._operation_count == 0:
            return
        
        start_time = time.time()
        self._batch.commit()
        elapsed = (time.time() - start_time) * 1000
        
        logger.debug(
            "Batch write of %d operations completed in %.2fms",
            self._operation_count, elapsed
        )
        
        # Reset for potential reuse
        self._batch = self._db.batch()
        self._operation_count = 0
    
    def _check_batch_size(self) -> None:
        """Check if batch size limit is reached and auto-commit if needed."""
        if self._operation_count >= MAX_BATCH_SIZE:
            logger.warning(
                "Batch size limit (%d) reached, auto-committing",
                MAX_BATCH_SIZE
            )
            self.commit()


def create_expense_with_batch(
    db,
    expense_ref: DocumentReference,
    expense_data: Dict[str, Any],
    balance_ref: DocumentReference,
    balance_deltas: Dict[str, float],
    group_ref: Optional[DocumentReference] = None,
    group_updates: Optional[Dict[str, Any]] = None,
    history_ref: Optional[DocumentReference] = None,
    history_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Create expense with all related updates in a single atomic batch.
    
    This reduces the typical 7 write operations to 1 atomic batch commit.
    
    Args:
        db: Firestore client
        expense_ref: Reference to new expense document
        expense_data: Expense document data
        balance_ref: Reference to group balances document
        balance_deltas: Map of user_id -> balance change
        group_ref: Optional reference to group document
        group_updates: Optional group updates (last_activity, expense_count, etc.)
        history_ref: Optional reference to history document
        history_data: Optional history entry data
    """
    with BatchWriter(db) as batch:
        # Write expense
        batch.set(expense_ref, expense_data)
        
        # Update balances using Increment for atomic updates
        balance_updates = {
            f"balances.{user_id}": Increment(delta)
            for user_id, delta in balance_deltas.items()
        }
        batch.update(balance_ref, balance_updates)
        
        # Update group if provided
        if group_ref and group_updates:
            batch.update(group_ref, group_updates)
        
        # Write history if provided
        if history_ref and history_data:
            batch.set(history_ref, history_data)


def update_expense_with_batch(
    db,
    expense_ref: DocumentReference,
    expense_updates: Dict[str, Any],
    balance_ref: DocumentReference,
    balance_deltas: Dict[str, float],
    history_ref: Optional[DocumentReference] = None,
    history_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Update expense with balance adjustments in a single atomic batch.
    
    Args:
        db: Firestore client
        expense_ref: Reference to expense document
        expense_updates: Fields to update on expense
        balance_ref: Reference to group balances document
        balance_deltas: Map of user_id -> balance change (net of old - new)
        history_ref: Optional reference to history document
        history_data: Optional history entry data
    """
    with BatchWriter(db) as batch:
        # Update expense
        batch.update(expense_ref, expense_updates)
        
        # Update balances
        if balance_deltas:
            balance_updates = {
                f"balances.{user_id}": Increment(delta)
                for user_id, delta in balance_deltas.items()
            }
            batch.update(balance_ref, balance_updates)
        
        # Write history if provided
        if history_ref and history_data:
            batch.set(history_ref, history_data)


def delete_expense_with_batch(
    db,
    expense_ref: DocumentReference,
    expense_updates: Dict[str, Any],
    balance_ref: DocumentReference,
    balance_deltas: Dict[str, float],
    history_ref: Optional[DocumentReference] = None,
    history_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Soft-delete expense with balance reversal in a single atomic batch.
    
    Args:
        db: Firestore client
        expense_ref: Reference to expense document
        expense_updates: Soft-delete fields (is_deleted, deleted_at)
        balance_ref: Reference to group balances document
        balance_deltas: Map of user_id -> balance reversal (negative of original)
        history_ref: Optional reference to history document
        history_data: Optional history entry data
    """
    with BatchWriter(db) as batch:
        # Soft-delete expense
        batch.update(expense_ref, expense_updates)
        
        # Reverse balances
        if balance_deltas:
            balance_updates = {
                f"balances.{user_id}": Increment(delta)
                for user_id, delta in balance_deltas.items()
            }
            batch.update(balance_ref, balance_updates)
        
        # Write history if provided
        if history_ref and history_data:
            batch.set(history_ref, history_data)


def create_settlement_with_batch(
    db,
    settlement_ref: DocumentReference,
    settlement_data: Dict[str, Any],
    balance_ref: DocumentReference,
    balance_deltas: Dict[str, float],
    group_ref: Optional[DocumentReference] = None,
    group_updates: Optional[Dict[str, Any]] = None
) -> None:
    """
    Create settlement with balance updates in a single atomic batch.
    
    Args:
        db: Firestore client
        settlement_ref: Reference to new settlement document
        settlement_data: Settlement document data
        balance_ref: Reference to group balances document
        balance_deltas: Map of user_id -> balance change
        group_ref: Optional reference to group document
        group_updates: Optional group updates (is_settled flag, etc.)
    """
    with BatchWriter(db) as batch:
        # Write settlement
        batch.set(settlement_ref, settlement_data)
        
        # Update balances
        balance_updates = {
            f"balances.{user_id}": Increment(delta)
            for user_id, delta in balance_deltas.items()
        }
        batch.update(balance_ref, balance_updates)
        
        # Update group if provided
        if group_ref and group_updates:
            batch.update(group_ref, group_updates)
