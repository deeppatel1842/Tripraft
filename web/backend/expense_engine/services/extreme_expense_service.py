"""
Extreme Expense Service - Phase 21.3 Zero-Read Mutations
=========================================================

This service implements zero-read expense operations for the 10-operation architecture.
Every operation uses a single batch write and updates all affected dashboards.

Key principles:
1. NO Firestore reads during mutations (validate from Redis cache)
2. Single batch write per operation
3. Update ALL affected users' dashboard documents
4. Write-through cache (no re-reads needed)
5. Balance calculations done in-memory
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from firebase_admin import firestore

from ..config import firestore_collections

try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

try:
    from ..firestore_counter import record_read, record_write
except ImportError:
    def record_read(count=1, collection=None): pass
    def record_write(count=1, collection=None): pass

logger = logging.getLogger(__name__)


# Maximum items in dashboard arrays
MAX_RECENT_EXPENSES = 20
MAX_RECENT_HISTORY = 20


class ExtremeExpenseService:
    """
    Phase 21.3: Zero-read expense operations.
    
    All operations:
    1. Validate using Redis cache (0 Firestore reads)
    2. Calculate balances in-memory
    3. Execute single batch write
    4. Update all affected dashboards
    5. Update Redis cache (write-through)
    6. Return computed response (no re-read)
    """
    
    def __init__(self):
        self._cache = get_cache_manager() if CACHE_ENABLED else None
        self._db = None
    
    @property
    def db(self):
        """Lazy-load Firestore client"""
        if self._db is None:
            self._db = firestore.client()
        return self._db
    
    def _get_dashboard_cache_key(self, user_id: str) -> str:
        """Generate Redis cache key for dashboard"""
        return f"expense:extreme_dashboard:{user_id}"
    
    def _round_currency(self, amount: float) -> float:
        """Round to 2 decimal places for currency"""
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    # =========================================================================
    # CREATE EXPENSE - 1 Batch Write
    # =========================================================================
    
    def create_expense_extreme(
        self,
        group_id: str,
        paid_by: str,
        amount: float,
        description: str,
        split_between: List[str],
        split_type: str = "equal",
        split_details: Dict[str, float] = None,
        category: str = "general",
        created_by: str = None,
        current_balances: Dict[str, float] = None,
        group_members: List[Dict] = None,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Create a new expense with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (balances and members from Redis cache)
        - 1 Batch write:
            - expense_expenses/{new_id}
            - expense_group_balances/{group_id}
            - expense_history/{history_id}
            - expense_groups/{group_id} (update totals)
            - expense_user_dashboards/{each_member} (update balances + recent expenses)
        
        Args:
            group_id: Group ID
            paid_by: User ID who paid
            amount: Expense amount
            description: Expense description
            split_between: List of user IDs to split between
            split_type: "equal", "exact", or "percent"
            split_details: Per-user amounts for exact/percent splits
            category: Expense category
            created_by: User who created (defaults to paid_by)
            current_balances: Current balances from cache
            group_members: List of group members from cache
            currency: Currency code
            
        Returns:
            Created expense with balance deltas
        """
        start_time = datetime.utcnow()
        
        # Generate IDs
        expense_id = f"exp_{uuid.uuid4().hex[:12]}"
        history_id = f"hist_{expense_id}_v1"
        
        created_by = created_by or paid_by
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        # Calculate splits
        splits = self._calculate_splits(
            amount=amount,
            paid_by=paid_by,
            split_between=split_between,
            split_type=split_type,
            split_details=split_details
        )
        
        # Calculate balance deltas
        balance_deltas = self._calculate_balance_deltas(paid_by, splits)
        
        # Apply deltas to get new balances
        current_balances = current_balances or {}
        new_balances = self._apply_balance_deltas(current_balances, balance_deltas)
        
        # Prepare expense data
        expense_data = {
            'expense_id': expense_id,
            'group_id': group_id,
            'description': description,
            'amount': self._round_currency(amount),
            'currency': currency,
            'paid_by': paid_by,
            'split_between': split_between,
            'split_type': split_type,
            'splits': splits,
            'category': category,
            'created_by': created_by,
            'created_at': now_iso,
            'updated_at': now_iso,
            'is_deleted': False,
            'version': 1
        }
        
        # Prepare expense summary for dashboard
        expense_summary = {
            'expense_id': expense_id,
            'description': description,
            'amount': self._round_currency(amount),
            'currency': currency,
            'paid_by': paid_by,
            'paid_by_name': self._get_member_name(paid_by, group_members),
            'split_between': split_between,
            'category': category,
            'created_at': now_iso
        }
        
        # Prepare history entry
        history_data = {
            'history_id': history_id,
            'expense_id': expense_id,
            'group_id': group_id,
            'version': 1,
            'action': 'created',
            'changed_by': created_by,
            'changed_at': now_iso,
            'changes': {},
            'snapshot': expense_data
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Write expense
        expense_ref = self.db.collection(firestore_collections.EXPENSES).document(expense_id)
        batch.set(expense_ref, expense_data)
        
        # Update balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'updated_at': now_iso
        })
        
        # Write history
        history_ref = self.db.collection(firestore_collections.EXPENSE_HISTORY).document(history_id)
        batch.set(history_ref, history_data)
        
        # Update group totals
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'total_spent': firestore.Increment(amount),
            'expense_count': firestore.Increment(1),
            'updated_at': now_iso
        })
        
        # Update each member's dashboard
        if group_members:
            for member in group_members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    member_balance = self._round_currency(new_balances.get(member_user_id, 0))
                    dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.set(dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.your_balance': member_balance,
                        f'groups.{group_id}.total_spent': firestore.Increment(amount),
                        f'groups.{group_id}.expense_count': firestore.Increment(1),
                        f'groups.{group_id}.is_settled': abs(member_balance) < 0.01,
                        f'groups.{group_id}.balances': new_balances
                    }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_create_expense')
        
        logger.info("[EXTREME] Expense created: %s (1 batch write)", expense_id)
        
        # Update Redis caches
        self._update_caches_after_expense(group_id, group_members, new_balances, expense_summary)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'expense': expense_data,
            'balance_deltas': balance_deltas,
            'new_balances': new_balances,
            'meta': {
                'operation': 'create_expense',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    def _calculate_splits(
        self,
        amount: float,
        paid_by: str,
        split_between: List[str],
        split_type: str,
        split_details: Dict[str, float] = None
    ) -> Dict[str, float]:
        """Calculate how much each person owes"""
        splits = {}
        
        if split_type == "equal":
            share = self._round_currency(amount / len(split_between))
            for user_id in split_between:
                splits[user_id] = share
            
            # Handle rounding remainder
            total_split = sum(splits.values())
            if total_split != amount:
                remainder = self._round_currency(amount - total_split)
                splits[split_between[0]] = self._round_currency(splits[split_between[0]] + remainder)
        
        elif split_type == "exact" and split_details:
            for user_id in split_between:
                splits[user_id] = self._round_currency(split_details.get(user_id, 0))
        
        elif split_type == "percent" and split_details:
            for user_id in split_between:
                percent = split_details.get(user_id, 0)
                splits[user_id] = self._round_currency(amount * percent / 100)
        
        else:
            # Default to equal split
            share = self._round_currency(amount / len(split_between))
            for user_id in split_between:
                splits[user_id] = share
        
        return splits
    
    def _calculate_balance_deltas(
        self,
        paid_by: str,
        splits: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate how balances change from this expense"""
        deltas = {}
        
        for user_id, share in splits.items():
            if user_id == paid_by:
                # Payer gets credited for what others owe them
                deltas[user_id] = self._round_currency(sum(s for uid, s in splits.items() if uid != paid_by))
            else:
                # Others owe their share
                deltas[user_id] = self._round_currency(-share)
        
        return deltas
    
    def _apply_balance_deltas(
        self,
        current_balances: Dict[str, float],
        deltas: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply deltas to current balances"""
        new_balances = dict(current_balances)
        
        for user_id, delta in deltas.items():
            current = new_balances.get(user_id, 0)
            new_balances[user_id] = self._round_currency(current + delta)
        
        return new_balances
    
    def _get_member_name(self, user_id: str, members: List[Dict]) -> str:
        """Get member display name"""
        if not members:
            return user_id[:8]
        for member in members:
            if member.get('user_id') == user_id:
                return member.get('display_name', user_id[:8])
        return user_id[:8]
    
    def _update_caches_after_expense(
        self,
        group_id: str,
        members: List[Dict],
        new_balances: Dict[str, float],
        expense_summary: Dict
    ) -> None:
        """Update Redis caches after expense creation"""
        if not self._cache or not self._cache.is_available():
            return
        
        # Invalidate all affected member caches (they'll refresh on next read)
        if members:
            for member in members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    cache_key = self._get_dashboard_cache_key(member_user_id)
                    self._cache.delete(cache_key)
        
        logger.debug("[EXTREME][CACHE] Invalidated caches after expense create")
    
    # =========================================================================
    # UPDATE EXPENSE - 1 Batch Write
    # =========================================================================
    
    def update_expense_extreme(
        self,
        expense_id: str,
        group_id: str,
        updates: Dict[str, Any],
        updated_by: str,
        old_expense: Dict,
        current_balances: Dict[str, float],
        group_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Update an expense with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (old expense and balances from cache)
        - 1 Batch write:
            - expense_expenses/{id}
            - expense_group_balances/{group_id}
            - expense_history/{history_id}
            - expense_groups/{group_id} (update totals if amount changed)
            - expense_user_dashboards/{each_member}
        
        Args:
            expense_id: Expense ID to update
            group_id: Group ID
            updates: Fields to update
            updated_by: User who made the update
            old_expense: Previous expense data from cache
            current_balances: Current balances from cache
            group_members: List of group members from cache
            
        Returns:
            Updated expense with balance deltas
        """
        start_time = datetime.utcnow()
        
        now_iso = datetime.utcnow().isoformat()
        old_version = old_expense.get('version', 1)
        new_version = old_version + 1
        history_id = f"hist_{expense_id}_v{new_version}"
        
        # Build updated expense
        updated_expense = dict(old_expense)
        updated_expense.update(updates)
        updated_expense['updated_at'] = now_iso
        updated_expense['version'] = new_version
        
        # Recalculate splits if amount or split changed
        if 'amount' in updates or 'split_between' in updates or 'split_type' in updates:
            new_splits = self._calculate_splits(
                amount=updated_expense.get('amount'),
                paid_by=updated_expense.get('paid_by'),
                split_between=updated_expense.get('split_between', []),
                split_type=updated_expense.get('split_type', 'equal'),
                split_details=updated_expense.get('split_details')
            )
            updated_expense['splits'] = new_splits
        
        # Calculate balance changes
        old_splits = old_expense.get('splits', {})
        old_paid_by = old_expense.get('paid_by')
        new_splits = updated_expense.get('splits', {})
        new_paid_by = updated_expense.get('paid_by')
        
        # Reverse old balances and apply new
        old_deltas = self._calculate_balance_deltas(old_paid_by, old_splits)
        new_deltas = self._calculate_balance_deltas(new_paid_by, new_splits)
        
        # Net deltas (reverse old, apply new)
        net_deltas = {}
        all_users = set(old_deltas.keys()) | set(new_deltas.keys())
        for user_id in all_users:
            old_delta = old_deltas.get(user_id, 0)
            new_delta = new_deltas.get(user_id, 0)
            net_deltas[user_id] = self._round_currency(new_delta - old_delta)
        
        # Apply to get new balances
        new_balances = self._apply_balance_deltas(current_balances, net_deltas)
        
        # Prepare history entry
        changes = {}
        for key in updates:
            if old_expense.get(key) != updates.get(key):
                changes[key] = {
                    'old': old_expense.get(key),
                    'new': updates.get(key)
                }
        
        history_data = {
            'history_id': history_id,
            'expense_id': expense_id,
            'group_id': group_id,
            'version': new_version,
            'action': 'updated',
            'changed_by': updated_by,
            'changed_at': now_iso,
            'changes': changes,
            'snapshot': updated_expense
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Update expense
        expense_ref = self.db.collection(firestore_collections.EXPENSES).document(expense_id)
        batch.update(expense_ref, updated_expense)
        
        # Update balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'updated_at': now_iso
        })
        
        # Write history
        history_ref = self.db.collection(firestore_collections.EXPENSE_HISTORY).document(history_id)
        batch.set(history_ref, history_data)
        
        # Update group totals if amount changed
        if 'amount' in updates:
            old_amount = old_expense.get('amount', 0)
            new_amount = updates.get('amount', old_amount)
            amount_diff = new_amount - old_amount
            if amount_diff != 0:
                group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
                batch.update(group_ref, {
                    'total_spent': firestore.Increment(amount_diff),
                    'updated_at': now_iso
                })
        
        # Update each member's dashboard
        if group_members:
            for member in group_members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    member_balance = self._round_currency(new_balances.get(member_user_id, 0))
                    dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.set(dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.your_balance': member_balance,
                        f'groups.{group_id}.is_settled': abs(member_balance) < 0.01,
                        f'groups.{group_id}.balances': new_balances
                    }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_update_expense')
        
        logger.info("[EXTREME] Expense updated: %s (1 batch write)", expense_id)
        
        # Invalidate caches
        self._update_caches_after_expense(group_id, group_members, new_balances, {})
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'expense': updated_expense,
            'balance_deltas': net_deltas,
            'new_balances': new_balances,
            'meta': {
                'operation': 'update_expense',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # DELETE EXPENSE - 1 Batch Write
    # =========================================================================
    
    def delete_expense_extreme(
        self,
        expense_id: str,
        group_id: str,
        deleted_by: str,
        expense_data: Dict,
        current_balances: Dict[str, float],
        group_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Soft-delete an expense with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (expense and balances from cache)
        - 1 Batch write:
            - expense_expenses/{id} (set is_deleted=True)
            - expense_group_balances/{group_id}
            - expense_history/{history_id}
            - expense_groups/{group_id} (update totals)
            - expense_user_dashboards/{each_member}
        
        Args:
            expense_id: Expense ID to delete
            group_id: Group ID
            deleted_by: User who deleted
            expense_data: Expense data from cache
            current_balances: Current balances from cache
            group_members: List of group members from cache
            
        Returns:
            Deletion confirmation with balance updates
        """
        start_time = datetime.utcnow()
        
        now_iso = datetime.utcnow().isoformat()
        version = expense_data.get('version', 1) + 1
        history_id = f"hist_{expense_id}_v{version}"
        
        # Reverse the expense's balance effect
        old_splits = expense_data.get('splits', {})
        old_paid_by = expense_data.get('paid_by')
        old_amount = expense_data.get('amount', 0)
        
        # Calculate reversal deltas
        old_deltas = self._calculate_balance_deltas(old_paid_by, old_splits)
        reversal_deltas = {k: -v for k, v in old_deltas.items()}
        
        # Apply reversal
        new_balances = self._apply_balance_deltas(current_balances, reversal_deltas)
        
        # Prepare history entry
        history_data = {
            'history_id': history_id,
            'expense_id': expense_id,
            'group_id': group_id,
            'version': version,
            'action': 'deleted',
            'changed_by': deleted_by,
            'changed_at': now_iso,
            'changes': {'is_deleted': {'old': False, 'new': True}},
            'snapshot': {**expense_data, 'is_deleted': True}
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Soft delete expense
        expense_ref = self.db.collection(firestore_collections.EXPENSES).document(expense_id)
        batch.update(expense_ref, {
            'is_deleted': True,
            'deleted_at': now_iso,
            'deleted_by': deleted_by,
            'version': version
        })
        
        # Update balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'updated_at': now_iso
        })
        
        # Write history
        history_ref = self.db.collection(firestore_collections.EXPENSE_HISTORY).document(history_id)
        batch.set(history_ref, history_data)
        
        # Update group totals
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'total_spent': firestore.Increment(-old_amount),
            'expense_count': firestore.Increment(-1),
            'updated_at': now_iso
        })
        
        # Update each member's dashboard
        if group_members:
            for member in group_members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    member_balance = self._round_currency(new_balances.get(member_user_id, 0))
                    dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.set(dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.your_balance': member_balance,
                        f'groups.{group_id}.total_spent': firestore.Increment(-old_amount),
                        f'groups.{group_id}.expense_count': firestore.Increment(-1),
                        f'groups.{group_id}.is_settled': abs(member_balance) < 0.01,
                        f'groups.{group_id}.balances': new_balances
                    }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_delete_expense')
        
        logger.info("[EXTREME] Expense deleted: %s (1 batch write)", expense_id)
        
        # Invalidate caches
        self._update_caches_after_expense(group_id, group_members, new_balances, {})
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'deleted_expense_id': expense_id,
            'balance_deltas': reversal_deltas,
            'new_balances': new_balances,
            'meta': {
                'operation': 'delete_expense',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }


# Singleton instance
_extreme_expense_service = None

def get_extreme_expense_service() -> ExtremeExpenseService:
    """Get singleton instance of ExtremeExpenseService"""
    global _extreme_expense_service
    if _extreme_expense_service is None:
        _extreme_expense_service = ExtremeExpenseService()
    return _extreme_expense_service
