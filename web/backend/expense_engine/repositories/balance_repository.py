"""
Balance Repository
Handles balance storage and incremental updates

Phase 19.3: Enhanced with total expense tracking and cache integration
- Tracks totalExpenses and expenseCount for each group
- Uses Redis cache with TTL for fast reads
- Implements incremental delta updates (no full recalculation)
"""

from typing import Dict, Optional
from decimal import Decimal
from google.cloud.firestore import SERVER_TIMESTAMP, Increment
import logging

from .base import BaseRepository
from ..config import firestore_collections, business_rules

# Import cache manager
try:
    from ..utils.cache_manager import get_cache_manager
    from ..config import redis_config
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

from ..models.balance import GroupBalance

logger = logging.getLogger(__name__)


class BalanceRepository(BaseRepository[GroupBalance]):
    """
    Repository for group balances
    Handles incremental balance updates with transactions
    
    Phase 19.3: Enhanced with caching and total expense tracking
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.GROUP_BALANCES
    
    def get_group_balances(self, group_id: str, use_cache: bool = True) -> Optional[GroupBalance]:
        """
        Get all balances for a group with Redis caching
        
        Phase 19.3: Added Redis caching for faster reads
        
        Args:
            group_id: Group ID
            use_cache: Whether to check cache first (default True)
            
        Returns:
            GroupBalance model or None
        """
        try:
            # Phase 19.3: Try cache first
            cache_key = None
            if use_cache and CACHE_ENABLED:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache_key = redis_config.KEY_GROUP_BALANCES.format(gid=group_id)
                    cached = cache.get(cache_key)
                    if cached:
                        logger.debug("[CACHE][+] Group balances cache hit: %s", group_id)
                        # Handle both full model dump and balances-only cache
                        if isinstance(cached, dict):
                            if 'balances' in cached and 'group_id' in cached:
                                # Full model dump in cache
                                return GroupBalance(**cached)
                            else:
                                # Balances-only dict in cache - reconstruct model
                                return GroupBalance(group_id=group_id, balances=cached)
                        return cached
                    logger.debug("[CACHE][-] Group balances cache miss: %s", group_id)
            
            # Fetch from Firestore
            data = self.get_by_id(group_id)
            if not data:
                # Initialize empty balance for new group
                return GroupBalance(group_id=group_id, balances={})
            
            balance = GroupBalance(**data)
            
            # Phase 19.3: Cache the result - store only balances for cleaner reads
            if cache_key:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    # Cache only the balances dict to avoid confusion
                    cache.set(cache_key, balance.model_dump()['balances'], ttl=redis_config.TTL_BALANCE)
            
            return balance
            
        except Exception as exc:
            logger.error("Error getting balances for group %s: %s", group_id, str(exc))
            raise
    
    def initialize_group_balances(self, group_id: str) -> None:
        """
        Initialize balance document for a new group
        
        Args:
            group_id: Group ID
        """
        try:
            group_balance = GroupBalance(
                group_id=group_id,
                balances={}
            )
            self.create(group_id, group_balance.to_dict())
            logger.info("Initialized balances for group: %s", group_id)
        except Exception as exc:
            logger.error("Error initializing balances: %s", str(exc))
            raise
    
    def update_balances(
        self,
        transaction,
        group_id: str,
        balance_deltas: Dict[str, Decimal]
    ) -> None:
        """
        Update balances incrementally within a transaction
        This is the core of incremental balance calculation
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            balance_deltas: Map of user_id -> delta amount (positive or negative)
        """
        try:
            doc_ref = self.get_collection().document(group_id)
            
            # Read current state
            doc = doc_ref.get(transaction=transaction)
            
            if doc.exists:
                current_data = doc.to_dict()
                current_balances = current_data.get('balances', {})
            else:
                current_balances = {}
            
            # Apply deltas
            new_balances = dict(current_balances)
            for user_id, delta in balance_deltas.items():
                current = Decimal(str(new_balances.get(user_id, 0)))
                new_balance = current + delta
                # Round to precision
                new_balances[user_id] = float(round(new_balance, business_rules.BALANCE_PRECISION))
            
            # Prepare update data
            update_data = {
                'group_id': group_id,
                'balances': new_balances,
                'last_updated': SERVER_TIMESTAMP,
                'version': Increment(1)
            }
            
            # Write back (create if doesn't exist, update if does)
            transaction.set(doc_ref, update_data, merge=True)
            
            # Phase 19.3: Invalidate cache after update
            self._invalidate_balance_cache(group_id)
            
            logger.debug(
                "Updated balances for group %s: %s", 
                group_id, 
                {uid: float(delta) for uid, delta in balance_deltas.items()}
            )
            
        except Exception as exc:
            logger.error("Error updating balances in transaction: %s", str(exc))
            raise
    
    def update_expense_totals(
        self,
        transaction,
        group_id: str,
        expense_amount: Decimal,
        is_new_expense: bool = True
    ) -> None:
        """
        Phase 19.3: Update expense totals (totalExpenses, expenseCount) incrementally.
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            expense_amount: Amount to add/subtract
            is_new_expense: True if creating expense, False if deleting
        """
        try:
            doc_ref = self.get_collection().document(group_id)
            
            delta = float(expense_amount) if is_new_expense else -float(expense_amount)
            count_delta = 1 if is_new_expense else -1
            
            update_data = {
                'totalExpenses': Increment(delta),
                'expenseCount': Increment(count_delta),
                'last_updated': SERVER_TIMESTAMP
            }
            
            transaction.set(doc_ref, update_data, merge=True)
            
            # Invalidate cache
            self._invalidate_balance_cache(group_id)
            
            logger.debug(
                "Updated expense totals for group %s: delta=%s, count_delta=%d",
                group_id, delta, count_delta
            )
            
        except Exception as exc:
            logger.error("Error updating expense totals: %s", str(exc))
            raise
    
    def _invalidate_balance_cache(self, group_id: str) -> None:
        """Phase 19.3: Invalidate balance cache for a group."""
        if not CACHE_ENABLED:
            return
        try:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.delete(redis_config.KEY_GROUP_BALANCES.format(gid=group_id))
                logger.debug("Balance cache invalidated for group %s", group_id)
        except Exception as e:
            logger.warning("Failed to invalidate balance cache: %s", e)
    
    def get_user_balance(self, group_id: str, user_id: str) -> Decimal:
        """
        Get balance for a specific user in a group
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            User's balance
        """
        try:
            group_balance = self.get_group_balances(group_id)
            if not group_balance:
                return Decimal("0.00")
            
            return group_balance.get_balance(user_id)
            
        except Exception as exc:
            logger.error("Error getting user balance: %s", str(exc))
            raise
    
    def is_group_settled(self, group_id: str) -> bool:
        """
        Check if all balances in a group are settled
        
        Args:
            group_id: Group ID
            
        Returns:
            True if all balances are within settlement tolerance
        """
        try:
            group_balance = self.get_group_balances(group_id)
            if not group_balance:
                return True
            
            balances_data = group_balance.model_dump()['balances']
            tolerance = Decimal(str(business_rules.SETTLEMENT_TOLERANCE))
            
            for balance_amount in balances_data.values():
                if abs(Decimal(str(balance_amount))) > tolerance:
                    return False
            
            return True
            
        except Exception as exc:
            logger.error("Error checking settlement status: %s", str(exc))
            raise
