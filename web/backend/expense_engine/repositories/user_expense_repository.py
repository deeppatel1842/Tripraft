"""
User Expense Repository
Manages denormalized user expense index for fast lookups

Phase 6: Denormalized Data Architecture

The USER_EXPENSES collection stores an index of expenses per user:
- Quick lookup of all expenses user is involved in
- Paginated access without complex queries
- Pre-computed expense summaries

Document ID: user_id
Structure:
{
    "user_id": "uid",
    "expenses": [
        {
            "expense_id": "exp_123",
            "group_id": "grp_456",
            "group_name": "Trip to Paris",
            "description": "Dinner",
            "amount": 120.00,
            "currency": "USD",
            "user_share": 40.00,  # User's portion
            "is_payer": true,     # Did user pay?
            "expense_date": timestamp,
            "category": "food"
        },
        ...
    ],
    "total_paid": 500.00,      # Sum of expenses user paid
    "total_share": 350.00,     # Sum of user's shares
    "expense_count": 15,
    "updated_at": timestamp
}
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import time

from .base import BaseRepository
from ..config import firestore_collections

# Import enhanced operation logger
try:
    from ..utils.operation_logger import (
        log_firestore_read,
        log_firestore_write,
        log_firestore_delete
    )
    OPERATION_LOGGING_ENABLED = True
except ImportError:
    OPERATION_LOGGING_ENABLED = False
    def log_firestore_read(collection, doc_id=None, count=1, duration_ms=0): pass
    def log_firestore_write(collection, doc_id=None, count=1, duration_ms=0, operation="set"): pass
    def log_firestore_delete(collection, doc_id=None, count=1, duration_ms=0): pass

logger = logging.getLogger(__name__)


class UserExpenseRepository(BaseRepository[Dict]):
    """
    Repository for denormalized user expense index
    
    Key features:
    - Fast user expense lookups without querying main expenses collection
    - Pre-computed totals
    - Efficient pagination
    """
    
    # Maximum expenses to store in index (older ones are archived)
    MAX_EXPENSES_IN_INDEX = 100
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.USER_EXPENSES
    
    def get_user_expense_index(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's expense index
        
        Args:
            user_id: User ID
            
        Returns:
            User expense index or None if not found
        """
        return self.get_by_id(user_id)
    
    def get_user_expenses(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user's expenses from index (fast lookup)
        
        Args:
            user_id: User ID
            limit: Maximum expenses to return
            offset: Number to skip
            group_id: Optional group filter
            
        Returns:
            Dict with expenses and pagination info
        """
        index = self.get_user_expense_index(user_id)
        if not index:
            return {
                'expenses': [],
                'total': 0,
                'limit': limit,
                'offset': offset,
                'has_more': False
            }
        
        expenses = index.get('expenses', [])
        
        # Filter by group if specified
        if group_id:
            expenses = [e for e in expenses if e.get('group_id') == group_id]
        
        total = len(expenses)
        
        # Apply pagination
        paginated = expenses[offset:offset + limit]
        
        return {
            'expenses': paginated,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(paginated) < total
        }
    
    def get_user_expense_totals(self, user_id: str) -> Dict[str, float]:
        """
        Get user's expense totals
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with total_paid, total_share, expense_count
        """
        index = self.get_user_expense_index(user_id)
        if not index:
            return {
                'total_paid': 0.0,
                'total_share': 0.0,
                'expense_count': 0
            }
        
        return {
            'total_paid': index.get('total_paid', 0.0),
            'total_share': index.get('total_share', 0.0),
            'expense_count': index.get('expense_count', 0)
        }
    
    def initialize_user_index(self, user_id: str) -> Dict[str, Any]:
        """
        Initialize empty expense index for new user
        
        Args:
            user_id: User ID
            
        Returns:
            Created index document
        """
        index = {
            'user_id': user_id,
            'expenses': [],
            'total_paid': 0.0,
            'total_share': 0.0,
            'expense_count': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        self.create(user_id, index)
        return index
    
    def add_expense_to_index(
        self,
        user_id: str,
        expense_id: str,
        group_id: str,
        group_name: str,
        description: str,
        amount: float,
        currency: str,
        user_share: float,
        is_payer: bool,
        expense_date: datetime,
        category: str = 'general'
    ) -> None:
        """
        Add expense to user's index
        
        Args:
            user_id: User ID
            expense_id: Expense ID
            group_id: Group ID
            group_name: Group name for display
            description: Expense description
            amount: Total expense amount
            currency: Currency code
            user_share: User's portion of the expense
            is_payer: Whether user paid for this expense
            expense_date: Date of expense
            category: Expense category
        """
        start_time = time.time()
        
        # Get or create user index
        index = self.get_user_expense_index(user_id)
        if not index:
            index = self.initialize_user_index(user_id)
        
        # Create expense entry
        expense_entry = {
            'expense_id': expense_id,
            'group_id': group_id,
            'group_name': group_name,
            'description': description,
            'amount': amount,
            'currency': currency,
            'user_share': user_share,
            'is_payer': is_payer,
            'expense_date': expense_date,
            'category': category,
            'added_at': datetime.utcnow()
        }
        
        # Get current expenses and add new one at the beginning
        expenses = index.get('expenses', [])
        
        # Check for duplicate
        existing_ids = {e.get('expense_id') for e in expenses}
        if expense_id in existing_ids:
            logger.warning("Expense %s already in user %s index, skipping", expense_id, user_id)
            return
        
        expenses.insert(0, expense_entry)  # Add to beginning (most recent first)
        
        # Trim to max size
        if len(expenses) > self.MAX_EXPENSES_IN_INDEX:
            expenses = expenses[:self.MAX_EXPENSES_IN_INDEX]
        
        # Update totals
        total_paid = index.get('total_paid', 0.0)
        total_share = index.get('total_share', 0.0)
        
        if is_payer:
            total_paid += amount
        total_share += user_share
        
        # Update document
        update_data = {
            'expenses': expenses,
            'total_paid': round(total_paid, 2),
            'total_share': round(total_share, 2),
            'expense_count': index.get('expense_count', 0) + 1,
            'updated_at': datetime.utcnow()
        }
        
        self.update(user_id, update_data)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug("Added expense %s to user %s index (%.1fms)", expense_id, user_id, duration_ms)
    
    def remove_expense_from_index(
        self,
        user_id: str,
        expense_id: str
    ) -> None:
        """
        Remove expense from user's index (on delete)
        
        Args:
            user_id: User ID
            expense_id: Expense ID to remove
        """
        start_time = time.time()
        
        index = self.get_user_expense_index(user_id)
        if not index:
            return
        
        expenses = index.get('expenses', [])
        
        # Find and remove expense
        removed_expense = None
        new_expenses = []
        for exp in expenses:
            if exp.get('expense_id') == expense_id:
                removed_expense = exp
            else:
                new_expenses.append(exp)
        
        if not removed_expense:
            return  # Expense not in index
        
        # Update totals
        total_paid = index.get('total_paid', 0.0)
        total_share = index.get('total_share', 0.0)
        
        if removed_expense.get('is_payer'):
            total_paid -= removed_expense.get('amount', 0)
        total_share -= removed_expense.get('user_share', 0)
        
        # Update document
        update_data = {
            'expenses': new_expenses,
            'total_paid': max(0, round(total_paid, 2)),
            'total_share': max(0, round(total_share, 2)),
            'expense_count': max(0, index.get('expense_count', 1) - 1),
            'updated_at': datetime.utcnow()
        }
        
        self.update(user_id, update_data)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug("Removed expense %s from user %s index (%.1fms)", expense_id, user_id, duration_ms)
    
    def update_expense_in_index(
        self,
        user_id: str,
        expense_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update expense entry in user's index
        
        Args:
            user_id: User ID
            expense_id: Expense ID
            updates: Fields to update
        """
        start_time = time.time()
        
        index = self.get_user_expense_index(user_id)
        if not index:
            return
        
        expenses = index.get('expenses', [])
        
        # Find and update expense
        old_expense = None
        for i, exp in enumerate(expenses):
            if exp.get('expense_id') == expense_id:
                old_expense = exp.copy()
                expenses[i] = {**exp, **updates}
                break
        
        if not old_expense:
            return  # Expense not in index
        
        # Recalculate totals if amount/share changed
        total_paid = index.get('total_paid', 0.0)
        total_share = index.get('total_share', 0.0)
        
        if 'amount' in updates and old_expense.get('is_payer'):
            total_paid = total_paid - old_expense.get('amount', 0) + updates['amount']
        
        if 'user_share' in updates:
            total_share = total_share - old_expense.get('user_share', 0) + updates['user_share']
        
        # Update document
        update_data = {
            'expenses': expenses,
            'total_paid': round(total_paid, 2),
            'total_share': round(total_share, 2),
            'updated_at': datetime.utcnow()
        }
        
        self.update(user_id, update_data)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug("Updated expense %s in user %s index (%.1fms)", expense_id, user_id, duration_ms)
    
    def add_expense_for_participants(
        self,
        expense_id: str,
        group_id: str,
        group_name: str,
        description: str,
        amount: float,
        currency: str,
        payer_id: str,
        splits: Dict[str, float],
        expense_date: datetime,
        category: str = 'general'
    ) -> None:
        """
        Add expense to all participant indexes (BATCHED - Phase 17 optimization)
        
        Uses batch reads and writes to reduce Firestore operations:
        - 1 batch read for all user indexes (vs N individual reads)
        - 1 batch write for all updates (vs N individual writes)
        
        Args:
            expense_id: Expense ID
            group_id: Group ID
            group_name: Group name
            description: Description
            amount: Total amount
            currency: Currency
            payer_id: Who paid
            splits: Dict of user_id -> share amount
            expense_date: Date
            category: Category
        """
        start_time = time.time()
        user_ids = list(splits.keys())
        
        # Phase 17: Batch read all user indexes at once
        user_indexes = self._batch_get_user_indexes(user_ids)
        
        # Prepare all updates
        batch_updates = {}
        for user_id, share in splits.items():
            try:
                index = user_indexes.get(user_id)
                if not index:
                    # Initialize new index
                    index = {
                        'user_id': user_id,
                        'expenses': [],
                        'total_paid': 0.0,
                        'total_share': 0.0,
                        'expense_count': 0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                
                # Create expense entry
                is_payer = (user_id == payer_id)
                expense_entry = {
                    'expense_id': expense_id,
                    'group_id': group_id,
                    'group_name': group_name,
                    'description': description,
                    'amount': amount,
                    'currency': currency,
                    'user_share': share,
                    'is_payer': is_payer,
                    'expense_date': expense_date,
                    'category': category,
                    'added_at': datetime.utcnow()
                }
                
                # Get current expenses
                expenses = index.get('expenses', [])
                
                # Check for duplicate
                existing_ids = {e.get('expense_id') for e in expenses}
                if expense_id in existing_ids:
                    logger.warning("Expense %s already in user %s index, skipping", expense_id, user_id)
                    continue
                
                expenses.insert(0, expense_entry)
                
                # Trim to max size
                if len(expenses) > self.MAX_EXPENSES_IN_INDEX:
                    expenses = expenses[:self.MAX_EXPENSES_IN_INDEX]
                
                # Update totals
                total_paid = index.get('total_paid', 0.0)
                total_share = index.get('total_share', 0.0)
                
                if is_payer:
                    total_paid += amount
                total_share += share
                
                # Prepare update data
                batch_updates[user_id] = {
                    'user_id': user_id,
                    'expenses': expenses,
                    'total_paid': round(total_paid, 2),
                    'total_share': round(total_share, 2),
                    'expense_count': index.get('expense_count', 0) + 1,
                    'updated_at': datetime.utcnow()
                }
                
            except Exception as exc:
                logger.error("Failed to prepare expense update for user %s: %s", user_id, str(exc))
        
        # Phase 17: Batch write all updates at once
        if batch_updates:
            self._batch_set_user_indexes(batch_updates)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info("[BATCH] Added expense %s to %d user indexes in 1R+1W (%.1fms)", 
                   expense_id, len(batch_updates), duration_ms)
    
    def _batch_get_user_indexes(self, user_ids: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Batch get multiple user indexes in one Firestore call
        Phase 17: Reduces N reads to 1 batch read
        """
        start_time = time.time()
        result = {}
        
        if not user_ids:
            return result
        
        try:
            # Use get_all for batch reads
            doc_refs = [self.get_collection().document(uid) for uid in user_ids]
            docs = self.db.get_all(doc_refs)
            
            for doc in docs:
                if doc.exists:
                    result[doc.id] = doc.to_dict()
                else:
                    result[doc.id] = None
            
            duration_ms = (time.time() - start_time) * 1000
            if OPERATION_LOGGING_ENABLED:
                log_firestore_read(self.get_collection_name(), doc_id=f"batch({len(user_ids)})", 
                                   count=1, duration_ms=duration_ms)
            logger.debug("[BATCH][R] Read %d user indexes in %.1fms", len(user_ids), duration_ms)
            
        except Exception as exc:
            logger.error("Batch get user indexes failed: %s", str(exc))
            # Fallback to individual reads
            for uid in user_ids:
                result[uid] = self.get_by_id(uid)
        
        return result
    
    def _batch_set_user_indexes(self, updates: Dict[str, Dict]) -> None:
        """
        Batch set/update multiple user indexes in one Firestore call
        Phase 17: Reduces N writes to 1 batch write
        """
        start_time = time.time()
        
        if not updates:
            return
        
        try:
            batch = self.db.batch()
            for user_id, data in updates.items():
                doc_ref = self.get_collection().document(user_id)
                batch.set(doc_ref, data, merge=True)
            batch.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            if OPERATION_LOGGING_ENABLED:
                log_firestore_write(self.get_collection_name(), doc_id=f"batch({len(updates)})", 
                                    count=1, duration_ms=duration_ms, operation="batch_set")
            logger.debug("[BATCH][W] Wrote %d user indexes in %.1fms", len(updates), duration_ms)
            
        except Exception as exc:
            logger.error("Batch set user indexes failed: %s", str(exc))
            raise
    
    def remove_expense_for_participants(
        self,
        expense_id: str,
        participant_ids: List[str]
    ) -> None:
        """
        Remove expense from all participant indexes (BATCHED - Phase 17 optimization)
        
        Uses batch reads and writes to reduce Firestore operations.
        
        Args:
            expense_id: Expense ID
            participant_ids: List of user IDs
        """
        start_time = time.time()
        
        # Phase 17: Batch read all user indexes at once
        user_indexes = self._batch_get_user_indexes(participant_ids)
        
        # Prepare all updates
        batch_updates = {}
        for user_id in participant_ids:
            try:
                index = user_indexes.get(user_id)
                if not index:
                    continue
                
                expenses = index.get('expenses', [])
                
                # Find and remove expense
                removed_expense = None
                new_expenses = []
                for exp in expenses:
                    if exp.get('expense_id') == expense_id:
                        removed_expense = exp
                    else:
                        new_expenses.append(exp)
                
                if not removed_expense:
                    continue  # Expense not in index
                
                # Update totals
                total_paid = index.get('total_paid', 0.0)
                total_share = index.get('total_share', 0.0)
                
                if removed_expense.get('is_payer'):
                    total_paid -= removed_expense.get('amount', 0)
                total_share -= removed_expense.get('user_share', 0)
                
                # Prepare update data
                batch_updates[user_id] = {
                    'expenses': new_expenses,
                    'total_paid': max(0, round(total_paid, 2)),
                    'total_share': max(0, round(total_share, 2)),
                    'expense_count': max(0, index.get('expense_count', 1) - 1),
                    'updated_at': datetime.utcnow()
                }
                
            except Exception as exc:
                logger.error("Failed to prepare expense removal for user %s: %s", user_id, str(exc))
        
        # Phase 17: Batch write all updates at once
        if batch_updates:
            self._batch_set_user_indexes(batch_updates)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info("[BATCH] Removed expense %s from %d user indexes in 1R+1W (%.1fms)", 
                   expense_id, len(batch_updates), duration_ms)
    
    def get_recent_expenses_across_groups(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's most recent expenses across all groups
        
        Args:
            user_id: User ID
            limit: Maximum to return
            
        Returns:
            List of recent expenses
        """
        index = self.get_user_expense_index(user_id)
        if not index:
            return []
        
        expenses = index.get('expenses', [])
        return expenses[:limit]
