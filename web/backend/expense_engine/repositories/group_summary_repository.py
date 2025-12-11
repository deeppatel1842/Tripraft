"""
Group Summary Repository
Manages denormalized per-user group summaries for fast lookups

Phase 6: Denormalized Data Architecture

The GROUP_SUMMARIES collection stores pre-computed per-user statistics:
- User's groups with basic info
- Total owed/owing across all groups
- Activity counts
- Last activity timestamps

Document ID: user_id
Structure:
{
    "user_id": "uid",
    "groups": {
        "group_id_1": {
            "name": "Trip to Paris",
            "currency": "USD",
            "balance": 150.00,  # Positive = owed to user, Negative = user owes
            "expense_count": 5,
            "last_activity": timestamp,
            "role": "admin"
        },
        ...
    },
    "total_owed": 250.00,      # Sum of positive balances
    "total_owing": 100.00,     # Sum of negative balances (abs value)
    "net_balance": 150.00,     # total_owed - total_owing
    "group_count": 3,
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


class GroupSummaryRepository(BaseRepository[Dict]):
    """
    Repository for denormalized per-user group summaries
    
    Key features:
    - Single document per user with all group summaries
    - Pre-computed balance totals
    - Atomic updates for consistency
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.GROUP_SUMMARIES
    
    def get_user_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's complete group summary
        
        Args:
            user_id: User ID
            
        Returns:
            User summary with all groups or None if not found
        """
        return self.get_by_id(user_id)
    
    def get_user_groups_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of user's groups from summary (fast lookup)
        
        Args:
            user_id: User ID
            
        Returns:
            List of group summaries
        """
        summary = self.get_user_summary(user_id)
        if not summary or 'groups' not in summary:
            return []
        
        groups = []
        for group_id, group_data in summary.get('groups', {}).items():
            group_info = {
                'group_id': group_id,
                **group_data
            }
            groups.append(group_info)
        
        # Sort by last_activity descending
        groups.sort(key=lambda g: g.get('last_activity', datetime.min), reverse=True)
        return groups
    
    def get_user_balance_totals(self, user_id: str) -> Dict[str, float]:
        """
        Get user's total balance across all groups
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with total_owed, total_owing, net_balance
        """
        summary = self.get_user_summary(user_id)
        if not summary:
            return {
                'total_owed': 0.0,
                'total_owing': 0.0,
                'net_balance': 0.0,
                'group_count': 0
            }
        
        return {
            'total_owed': summary.get('total_owed', 0.0),
            'total_owing': summary.get('total_owing', 0.0),
            'net_balance': summary.get('net_balance', 0.0),
            'group_count': summary.get('group_count', 0)
        }
    
    def initialize_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Initialize empty summary for new user
        
        Args:
            user_id: User ID
            
        Returns:
            Created summary document
        """
        summary = {
            'user_id': user_id,
            'groups': {},
            'total_owed': 0.0,
            'total_owing': 0.0,
            'net_balance': 0.0,
            'group_count': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        self.create(user_id, summary)
        return summary
    
    def add_group_to_user(
        self,
        user_id: str,
        group_id: str,
        group_name: str,
        currency: str = 'USD',
        role: str = 'member',
        initial_balance: float = 0.0
    ) -> None:
        """
        Add a group to user's summary (when joining a group)
        
        Args:
            user_id: User ID
            group_id: Group ID
            group_name: Group name for display
            currency: Group currency
            role: User's role in group
            initial_balance: Starting balance (usually 0)
        """
        start_time = time.time()
        
        # Get or create user summary
        summary = self.get_user_summary(user_id)
        if not summary:
            summary = self.initialize_user_summary(user_id)
        
        # Add group entry
        group_entry = {
            'name': group_name,
            'currency': currency,
            'balance': initial_balance,
            'expense_count': 0,
            'last_activity': datetime.utcnow(),
            'role': role,
            'joined_at': datetime.utcnow()
        }
        
        # Update summary
        groups = summary.get('groups', {})
        groups[group_id] = group_entry
        
        # Recalculate totals
        totals = self._calculate_totals(groups)
        
        # Update document
        update_data = {
            f'groups.{group_id}': group_entry,
            'group_count': len(groups),
            'updated_at': datetime.utcnow(),
            **totals
        }
        
        self.update(user_id, update_data)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info("Added group %s to user %s summary (%.1fms)", group_id, user_id, duration_ms)
    
    def remove_group_from_user(self, user_id: str, group_id: str) -> None:
        """
        Remove a group from user's summary (when leaving a group)
        
        Args:
            user_id: User ID
            group_id: Group ID
        """
        from google.cloud.firestore_v1 import DELETE_FIELD
        
        start_time = time.time()
        
        summary = self.get_user_summary(user_id)
        if not summary:
            return
        
        groups = summary.get('groups', {})
        if group_id not in groups:
            return
        
        # Remove group and recalculate
        del groups[group_id]
        totals = self._calculate_totals(groups)
        
        # Update document (delete field)
        update_data = {
            f'groups.{group_id}': DELETE_FIELD,
            'group_count': len(groups),
            'updated_at': datetime.utcnow(),
            **totals
        }
        
        self.update(user_id, update_data)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info("Removed group %s from user %s summary (%.1fms)", group_id, user_id, duration_ms)
    
    def update_group_balance(
        self,
        user_id: str,
        group_id: str,
        balance_delta: float,
        increment_expense_count: bool = False
    ) -> None:
        """
        Update user's balance in a specific group (incremental update)
        
        Args:
            user_id: User ID
            group_id: Group ID
            balance_delta: Amount to add to balance (can be negative)
            increment_expense_count: Whether to increment expense count
        """
        from google.cloud.firestore_v1 import Increment
        
        start_time = time.time()
        
        # Use incremental updates for atomicity
        update_data = {
            f'groups.{group_id}.balance': Increment(balance_delta),
            f'groups.{group_id}.last_activity': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        if increment_expense_count:
            update_data[f'groups.{group_id}.expense_count'] = Increment(1)
        
        try:
            # Use upsert instead of update to handle case where document doesn't exist yet
            self.upsert(user_id, update_data)
            
            # Recalculate totals asynchronously (or defer)
            self._recalculate_user_totals(user_id)
            
            duration_ms = (time.time() - start_time) * 1000
            logger.debug("Updated balance for user %s in group %s: delta=%.2f (%.1fms)", 
                        user_id, group_id, balance_delta, duration_ms)
        except Exception as exc:
            logger.error("Failed to update balance for user %s in group %s: %s", 
                        user_id, group_id, str(exc))
            raise
    
    def set_group_balance(
        self,
        user_id: str,
        group_id: str,
        new_balance: float
    ) -> None:
        """
        Set user's absolute balance in a group (for recalculation)
        
        Args:
            user_id: User ID
            group_id: Group ID
            new_balance: New absolute balance
        """
        start_time = time.time()
        
        update_data = {
            f'groups.{group_id}.balance': new_balance,
            f'groups.{group_id}.last_activity': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Use upsert to handle case where document doesn't exist yet
        self.upsert(user_id, update_data)
        
        # Recalculate totals
        self._recalculate_user_totals(user_id)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug("Set balance for user %s in group %s: %.2f (%.1fms)", 
                    user_id, group_id, new_balance, duration_ms)
    
    def update_group_info(
        self,
        user_id: str,
        group_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update group info in user's summary (name change, etc.)
        
        Args:
            user_id: User ID
            group_id: Group ID
            updates: Fields to update (name, currency, etc.)
        """
        update_data = {
            f'groups.{group_id}.{key}': value
            for key, value in updates.items()
        }
        update_data['updated_at'] = datetime.utcnow()
        
        # Use upsert to handle case where document doesn't exist yet
        self.upsert(user_id, update_data)
    
    def _calculate_totals(self, groups: Dict[str, Dict]) -> Dict[str, float]:
        """
        Calculate balance totals from groups dict
        
        Args:
            groups: Dict of group_id -> group_data
            
        Returns:
            Dict with total_owed, total_owing, net_balance
        """
        total_owed = 0.0
        total_owing = 0.0
        
        for group_data in groups.values():
            balance = group_data.get('balance', 0.0)
            if balance > 0:
                total_owed += balance
            elif balance < 0:
                total_owing += abs(balance)
        
        return {
            'total_owed': round(total_owed, 2),
            'total_owing': round(total_owing, 2),
            'net_balance': round(total_owed - total_owing, 2)
        }
    
    def _recalculate_user_totals(self, user_id: str) -> None:
        """
        Recalculate user's balance totals from all groups
        
        Args:
            user_id: User ID
        """
        summary = self.get_user_summary(user_id)
        if not summary:
            return
        
        groups = summary.get('groups', {})
        totals = self._calculate_totals(groups)
        
        # Use upsert for safety, even though document should exist after initial upsert
        self.upsert(user_id, {
            **totals,
            'updated_at': datetime.utcnow()
        })
    
    def _batch_get_user_summaries(self, user_ids: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Batch get multiple user summaries in one Firestore call
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
            logger.debug("[BATCH][R] Read %d user summaries in %.1fms", len(user_ids), duration_ms)
            
        except Exception as exc:
            logger.error("Batch get user summaries failed: %s", str(exc))
            # Fallback to individual reads
            for uid in user_ids:
                result[uid] = self.get_by_id(uid)
        
        return result
    
    def batch_update_group_balances(
        self,
        group_id: str,
        balance_deltas: Dict[str, float],
        increment_expense_count: bool = False
    ) -> None:
        """
        Update group balances for multiple users in a single batch (Phase 17 optimization)
        
        Uses Firestore Increment for atomic updates and batches all writes together.
        
        Args:
            group_id: Group ID
            balance_deltas: Dict of user_id -> balance_delta (amount to add/subtract)
            increment_expense_count: Whether to increment expense count
        """
        from google.cloud.firestore_v1 import Increment
        
        start_time = time.time()
        
        if not balance_deltas:
            return
        
        try:
            batch = self.db.batch()
            
            for user_id, balance_delta in balance_deltas.items():
                doc_ref = self.get_collection().document(user_id)
                
                update_data = {
                    f'groups.{group_id}.balance': Increment(balance_delta),
                    f'groups.{group_id}.last_activity': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                if increment_expense_count:
                    update_data[f'groups.{group_id}.expense_count'] = Increment(1)
                
                # Use set with merge to handle case where user doc doesn't exist
                batch.set(doc_ref, update_data, merge=True)
            
            batch.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            if OPERATION_LOGGING_ENABLED:
                log_firestore_write(self.get_collection_name(), doc_id=f"batch({len(balance_deltas)})", 
                                    count=1, duration_ms=duration_ms, operation="batch_update")
            logger.info("[BATCH][W] Updated %d user group summaries in %.1fms", 
                       len(balance_deltas), duration_ms)
            
            # Queue totals recalculation (can be deferred)
            for user_id in balance_deltas.keys():
                try:
                    self._recalculate_user_totals(user_id)
                except Exception as exc:
                    logger.warning("Failed to recalculate totals for user %s: %s", user_id, str(exc))
                    
        except Exception as exc:
            logger.error("Batch update group balances failed: %s", str(exc))
            raise
    
    def bulk_update_balances_for_group(
        self,
        group_id: str,
        user_balances: Dict[str, float]
    ) -> None:
        """
        Update balances for multiple users in a group (after expense)
        
        Args:
            group_id: Group ID
            user_balances: Dict of user_id -> new_balance
        """
        start_time = time.time()
        
        for user_id, new_balance in user_balances.items():
            try:
                self.set_group_balance(user_id, group_id, new_balance)
            except Exception as exc:
                logger.error("Failed to update balance for user %s: %s", user_id, str(exc))
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info("Bulk updated %d user balances for group %s (%.1fms)", 
                   len(user_balances), group_id, duration_ms)
    
    def sync_from_group_balances(
        self,
        user_id: str,
        group_id: str,
        balance_data: Dict[str, Any]
    ) -> None:
        """
        Sync user's summary from group_balances collection
        
        Args:
            user_id: User ID
            group_id: Group ID
            balance_data: Balance data from group_balances collection
        """
        # Extract user's balance from group balance matrix
        # Balance format: balance_data['balances'][user_id][other_user_id]
        
        net_balance = 0.0
        balances = balance_data.get('balances', {})
        
        if user_id in balances:
            # Sum what this user is owed by others
            for other_user, amount in balances[user_id].items():
                net_balance += amount
        
        # Subtract what user owes others
        for other_user, their_balances in balances.items():
            if other_user != user_id and user_id in their_balances:
                net_balance -= their_balances[user_id]
        
        self.set_group_balance(user_id, group_id, net_balance)
