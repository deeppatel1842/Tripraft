"""
Balance Service
Incremental balance calculation engine

Phase 13: Added Redis caching for balance lookups
"""

from typing import Dict, Optional
from decimal import Decimal
from firebase_admin import firestore
import logging

from ..repositories import BalanceRepository, ExpenseRepository
from ..models.expense import Expense
from ..config import business_rules, redis_config

logger = logging.getLogger(__name__)

# Cache imports with graceful fallback
try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None


def _invalidate_balance_cache(group_id: str) -> None:
    """
    Invalidate balance cache when balances change.
    
    Args:
        group_id: The group ID whose balances changed
    """
    if not CACHE_ENABLED:
        return
    try:
        cache = get_cache_manager()
        if cache and cache.is_available():
            cache.delete(redis_config.KEY_GROUP_BALANCES.format(gid=group_id))
            # Also invalidate group summary as it contains balance info
            cache.delete(redis_config.KEY_GROUP_SUMMARY.format(gid=group_id))
            logger.debug("Balance cache invalidated for group %s", group_id)
    except Exception as e:
        logger.warning("Failed to invalidate balance cache: %s", str(e))


class BalanceService:
    """
    Incremental balance calculation service
    Never scans all expenses - always updates incrementally
    """
    
    def __init__(
        self,
        balance_repo: Optional[BalanceRepository] = None,
        expense_repo: Optional[ExpenseRepository] = None
    ):
        """
        Initialize service
        
        Args:
            balance_repo: Balance repository instance (optional)
            expense_repo: Expense repository instance (optional)
        """
        # pylint: disable=no-value-for-parameter
        self.balance_repo = balance_repo or BalanceRepository()
        self.expense_repo = expense_repo or ExpenseRepository()
    
    def calculate_expense_deltas(self, expense: Expense) -> Dict[str, Decimal]:
        """
        Calculate balance deltas for an expense
        
        Logic:
        - Payer gets credited: +amount
        - Each participant gets debited: -split_amount
        - Net effect: payer gets (amount - their_split)
        
        Args:
            expense: Expense model
            
        Returns:
            Map of user_id -> delta
        """
        deltas: Dict[str, Decimal] = {}
        
        # Credit the payer with full amount
        deltas[expense.paid_by] = expense.amount
        
        # Debit each participant
        for split in expense.splits:
            if split.user_id in deltas:
                # If payer is also a participant, net their amount
                deltas[split.user_id] -= split.amount
            else:
                deltas[split.user_id] = -split.amount
        
        # Round to precision
        for user_id in deltas:
            deltas[user_id] = Decimal(
                str(round(float(deltas[user_id]), business_rules.BALANCE_PRECISION))
            )
        
        return deltas
    
    def add_expense_to_balances(
        self,
        transaction,
        group_id: str,
        expense: Expense
    ) -> None:
        """
        Add expense and update balances incrementally
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            expense: Expense model
        """
        try:
            deltas = self.calculate_expense_deltas(expense)
            
            self.balance_repo.update_balances(
                transaction,
                group_id,
                deltas
            )
            
            # Phase 13: Invalidate balance cache
            _invalidate_balance_cache(group_id)
            
            logger.info(
                "Updated balances for expense %s in group %s",
                expense.expense_id, group_id
            )
            
        except Exception as exc:
            logger.error("Error adding expense to balances: %s", str(exc))
            raise
    
    def edit_expense_in_balances(
        self,
        transaction,
        group_id: str,
        old_expense: Expense,
        new_expense: Expense
    ) -> None:
        """
        Edit expense - reverse old deltas, apply new deltas
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            old_expense: Old expense model
            new_expense: New expense model
        """
        try:
            # Calculate reverse deltas for old expense
            old_deltas = self.calculate_expense_deltas(old_expense)
            reverse_deltas = {
                uid: -delta for uid, delta in old_deltas.items()
            }
            
            # Calculate new deltas
            new_deltas = self.calculate_expense_deltas(new_expense)
            
            # Combine deltas
            combined_deltas: Dict[str, Decimal] = {}
            all_users = set(reverse_deltas.keys()) | set(new_deltas.keys())
            
            for uid in all_users:
                combined = (
                    reverse_deltas.get(uid, Decimal("0.00")) +
                    new_deltas.get(uid, Decimal("0.00"))
                )
                combined_deltas[uid] = Decimal(
                    str(round(float(combined), business_rules.BALANCE_PRECISION))
                )
            
            # Apply in transaction
            self.balance_repo.update_balances(
                transaction,
                group_id,
                combined_deltas
            )
            
            # Phase 13: Invalidate balance cache
            _invalidate_balance_cache(group_id)
            
            logger.info(
                "Updated balances for expense edit %s in group %s",
                new_expense.expense_id, group_id
            )
            
        except Exception as exc:
            logger.error("Error editing expense in balances: %s", str(exc))
            raise
    
    def remove_expense_from_balances(
        self,
        transaction,
        group_id: str,
        expense: Expense
    ) -> None:
        """
        Delete expense - reverse its deltas
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            expense: Expense model
        """
        try:
            deltas = self.calculate_expense_deltas(expense)
            reverse_deltas = {
                uid: -delta for uid, delta in deltas.items()
            }
            
            self.balance_repo.update_balances(
                transaction,
                group_id,
                reverse_deltas
            )
            
            # Phase 13: Invalidate balance cache
            _invalidate_balance_cache(group_id)
            
            logger.info(
                "Removed expense %s from balances in group %s",
                expense.expense_id, group_id
            )
            
        except Exception as exc:
            logger.error("Error removing expense from balances: %s", str(exc))
            raise
    
    def add_settlement_to_balances(
        self,
        transaction,
        group_id: str,
        from_user_id: str,
        to_user_id: str,
        amount: Decimal
    ) -> None:
        """
        Record settlement - update balances
        
        Logic: from_user pays to_user
        - from_user balance increases (they owe less)
        - to_user balance decreases (they are owed less)
        
        Args:
            transaction: Firestore transaction
            group_id: Group ID
            from_user_id: User ID who is paying
            to_user_id: User ID who is receiving
            amount: Settlement amount
        """
        try:
            deltas = {
                from_user_id: amount,    # from_user's debt decreases
                to_user_id: -amount      # to_user is owed less
            }
            
            self.balance_repo.update_balances(
                transaction,
                group_id,
                deltas
            )
            
            # Phase 13: Invalidate balance cache
            _invalidate_balance_cache(group_id)
            
            logger.info(
                "Recorded settlement from %s to %s: %s in group %s",
                from_user_id, to_user_id, amount, group_id
            )
            
        except Exception as exc:
            logger.error("Error adding settlement to balances: %s", str(exc))
            raise
    
    def get_group_balances(self, group_id: str) -> Dict[str, Decimal]:
        """
        Get all balances for a group with Redis caching
        
        Args:
            group_id: Group ID
            
        Returns:
            Map of user_id -> balance
        """
        try:
            # Try cache first
            if CACHE_ENABLED:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache_key = redis_config.KEY_GROUP_BALANCES.format(gid=group_id)
                    cached = cache.get(cache_key)
                    if cached is not None:
                        # Cache may contain full GroupBalance model_dump or just balances dict
                        # Extract balances dict if it's a full model dump
                        if isinstance(cached, dict) and 'balances' in cached:
                            cached_balances = cached['balances']
                        else:
                            cached_balances = cached
                        
                        # Convert cached floats back to Decimal with error handling
                        result = {}
                        for uid, balance in cached_balances.items():
                            try:
                                # Skip if balance is not a numeric type
                                if isinstance(balance, (int, float, str, Decimal)):
                                    result[uid] = Decimal(str(balance))
                            except Exception as conv_err:
                                logger.warning("Invalid cached balance for %s: %s (error: %s)", uid, balance, conv_err)
                        return result
            
            group_balance = self.balance_repo.get_group_balances(group_id)
            if not group_balance:
                return {}
            
            balances_data = group_balance.model_dump()['balances']
            result = {}
            for uid, balance in balances_data.items():
                try:
                    result[uid] = Decimal(str(balance))
                except Exception as conv_err:
                    logger.warning("Invalid balance for user %s in group %s: %s (error: %s)", uid, group_id, balance, conv_err)
                    result[uid] = Decimal("0.00")
            
            # Cache only the balances dict (not full model) for cleaner cache reads
            if CACHE_ENABLED and result:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache_key = redis_config.KEY_GROUP_BALANCES.format(gid=group_id)
                    cacheable = {uid: float(balance) for uid, balance in result.items()}
                    cache.set(cache_key, cacheable, ttl=redis_config.TTL_BALANCE)
            
            return result
            
        except Exception as exc:
            logger.error("Error getting group balances for %s: %s", group_id, str(exc))
            raise
    
    def is_group_settled(self, group_id: str) -> bool:
        """
        Check if all balances in a group are settled
        
        Args:
            group_id: Group ID
            
        Returns:
            True if all balances are within settlement tolerance
        """
        return self.balance_repo.is_group_settled(group_id)
    
    def get_user_balance(self, group_id: str, user_id: str) -> Dict:
        """
        Get balance details for a specific user in a group
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            Balance information dictionary
        """
        balances = self.balance_repo.get_group_balances(group_id)
        user_balance = balances.get(user_id, Decimal('0'))
        
        return {
            'balance': float(user_balance),
            'currency': 'USD',  # TODO: Get from group
            'owed_to': [],  # TODO: Calculate who owes this user
            'owes': []  # TODO: Calculate who this user owes
        }
    
    def get_all_user_balances(self, user_id: str) -> Dict:
        """
        Get user's balances across all groups
        
        Args:
            user_id: User ID
            
        Returns:
            Aggregated balance information
        """
        # TODO: Implement
        return {
            'balances': [],
            'total_owed_to_you': 0.0,
            'total_you_owe': 0.0,
            'net_balance': 0.0
        }
