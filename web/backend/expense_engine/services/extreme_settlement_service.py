"""
Extreme Settlement Service - Phase 21.3 Zero-Read Mutations
============================================================

This service implements zero-read settlement operations for the 10-operation architecture.
Every operation uses a single batch write and updates all affected dashboards.

Key principles:
1. NO Firestore reads during mutations (validate from Redis cache)
2. Single batch write per operation
3. Update ALL affected users' dashboard documents
4. Write-through cache (no re-reads needed)
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
MAX_RECENT_SETTLEMENTS = 10


class ExtremeSettlementService:
    """
    Phase 21.3: Zero-read settlement operations.
    
    All operations:
    1. Validate using Redis cache (0 Firestore reads)
    2. Execute single batch write
    3. Update all affected dashboards
    4. Update Redis cache (write-through)
    5. Return computed response (no re-read)
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
    # CREATE SETTLEMENT - 1 Batch Write
    # =========================================================================
    
    def create_settlement_extreme(
        self,
        group_id: str,
        payer_id: str,
        payee_id: str,
        amount: float,
        created_by: str,
        current_balances: Dict[str, float],
        group_members: List[Dict] = None,
        currency: str = "USD",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create a settlement with SINGLE batch write.
        
        A settlement is when payer_id pays payee_id an amount.
        This reduces payer_id's debt to payee_id (or increases payee_id's debt to payer_id).
        
        Operations:
        - 0 Firestore reads (balances from cache)
        - 1 Batch write:
            - expense_settlements/{new_id}
            - expense_group_balances/{group_id}
            - expense_user_dashboards/{payer}
            - expense_user_dashboards/{payee}
            - expense_user_dashboards/{other_members} (optional, for balance updates)
        
        Args:
            group_id: Group ID
            payer_id: User ID who is paying (sending money)
            payee_id: User ID receiving payment
            amount: Settlement amount
            created_by: User who created the settlement
            current_balances: Current balances from cache
            group_members: List of group members from cache
            currency: Currency code
            notes: Optional notes
            
        Returns:
            Created settlement with balance updates
        """
        start_time = datetime.utcnow()
        
        # Generate ID
        settlement_id = f"stl_{uuid.uuid4().hex[:12]}"
        
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        # Calculate balance changes
        # When payer pays payee:
        # - Payer's balance increases (less debt, or owed more)
        # - Payee's balance decreases (less owed to them)
        balance_deltas = {
            payer_id: self._round_currency(amount),    # Payer paid, so their balance goes up
            payee_id: self._round_currency(-amount)   # Payee received, so their balance goes down
        }
        
        # Apply deltas to get new balances
        new_balances = dict(current_balances)
        for user_id, delta in balance_deltas.items():
            current = new_balances.get(user_id, 0)
            new_balances[user_id] = self._round_currency(current + delta)
        
        # Prepare settlement data
        settlement_data = {
            'settlement_id': settlement_id,
            'group_id': group_id,
            'payer_id': payer_id,
            'payer_name': self._get_member_name(payer_id, group_members),
            'payee_id': payee_id,
            'payee_name': self._get_member_name(payee_id, group_members),
            'amount': self._round_currency(amount),
            'currency': currency,
            'notes': notes,
            'created_by': created_by,
            'created_at': now_iso,
            'is_deleted': False
        }
        
        # Prepare settlement summary for dashboard
        settlement_summary = {
            'settlement_id': settlement_id,
            'payer_id': payer_id,
            'payer_name': settlement_data['payer_name'],
            'payee_id': payee_id,
            'payee_name': settlement_data['payee_name'],
            'amount': self._round_currency(amount),
            'currency': currency,
            'created_at': now_iso
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Write settlement
        settlement_ref = self.db.collection(firestore_collections.SETTLEMENTS).document(settlement_id)
        batch.set(settlement_ref, settlement_data)
        
        # Update balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'updated_at': now_iso
        })
        
        # Update group
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'updated_at': now_iso
        })
        
        # Update each member's dashboard
        if group_members:
            for member in group_members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    member_balance = self._round_currency(new_balances.get(member_user_id, 0))
                    dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    
                    # Update balance and is_settled flag
                    batch.set(dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.your_balance': member_balance,
                        f'groups.{group_id}.is_settled': abs(member_balance) < 0.01,
                        f'groups.{group_id}.balances': new_balances
                    }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_create_settlement')
        
        logger.info("[EXTREME] Settlement created: %s (1 batch write)", settlement_id)
        
        # Invalidate caches
        self._update_caches_after_settlement(group_id, group_members)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'settlement': settlement_data,
            'balance_deltas': balance_deltas,
            'new_balances': new_balances,
            'meta': {
                'operation': 'create_settlement',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    def _get_member_name(self, user_id: str, members: List[Dict]) -> str:
        """Get member display name"""
        if not members:
            return user_id[:8]
        for member in members:
            if member.get('user_id') == user_id:
                return member.get('display_name', user_id[:8])
        return user_id[:8]
    
    def _update_caches_after_settlement(
        self,
        group_id: str,
        members: List[Dict]
    ) -> None:
        """Update Redis caches after settlement"""
        if not self._cache or not self._cache.is_available():
            return
        
        # Invalidate all affected member caches
        if members:
            for member in members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    cache_key = self._get_dashboard_cache_key(member_user_id)
                    self._cache.delete(cache_key)
        
        logger.debug("[EXTREME][CACHE] Invalidated caches after settlement")
    
    # =========================================================================
    # DELETE SETTLEMENT - 1 Batch Write
    # =========================================================================
    
    def delete_settlement_extreme(
        self,
        settlement_id: str,
        group_id: str,
        deleted_by: str,
        settlement_data: Dict,
        current_balances: Dict[str, float],
        group_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Soft-delete a settlement with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (settlement and balances from cache)
        - 1 Batch write:
            - expense_settlements/{id} (set is_deleted=True)
            - expense_group_balances/{group_id}
            - expense_user_dashboards/{each_member}
        
        Args:
            settlement_id: Settlement ID to delete
            group_id: Group ID
            deleted_by: User who deleted
            settlement_data: Settlement data from cache
            current_balances: Current balances from cache
            group_members: List of group members from cache
            
        Returns:
            Deletion confirmation with balance reversal
        """
        start_time = datetime.utcnow()
        
        now_iso = datetime.utcnow().isoformat()
        
        # Reverse the settlement's balance effect
        payer_id = settlement_data.get('payer_id')
        payee_id = settlement_data.get('payee_id')
        amount = settlement_data.get('amount', 0)
        
        # Reversal deltas (opposite of original)
        reversal_deltas = {
            payer_id: self._round_currency(-amount),   # Reverse payer's credit
            payee_id: self._round_currency(amount)    # Reverse payee's debit
        }
        
        # Apply reversal
        new_balances = dict(current_balances)
        for user_id, delta in reversal_deltas.items():
            current = new_balances.get(user_id, 0)
            new_balances[user_id] = self._round_currency(current + delta)
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Soft delete settlement
        settlement_ref = self.db.collection(firestore_collections.SETTLEMENTS).document(settlement_id)
        batch.update(settlement_ref, {
            'is_deleted': True,
            'deleted_at': now_iso,
            'deleted_by': deleted_by
        })
        
        # Update balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
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
        record_write(1, 'batch_delete_settlement')
        
        logger.info("[EXTREME] Settlement deleted: %s (1 batch write)", settlement_id)
        
        # Invalidate caches
        self._update_caches_after_settlement(group_id, group_members)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'deleted_settlement_id': settlement_id,
            'balance_deltas': reversal_deltas,
            'new_balances': new_balances,
            'meta': {
                'operation': 'delete_settlement',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }


# Singleton instance
_extreme_settlement_service = None

def get_extreme_settlement_service() -> ExtremeSettlementService:
    """Get singleton instance of ExtremeSettlementService"""
    global _extreme_settlement_service
    if _extreme_settlement_service is None:
        _extreme_settlement_service = ExtremeSettlementService()
    return _extreme_settlement_service
