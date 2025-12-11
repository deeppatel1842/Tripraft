"""
Thread-Safe Balance Manager
Wraps balance operations with proper locking and retry logic

Phase 10: Thread Safety & Concurrency
"""

import logging
from typing import Dict, Optional, TypeVar, Callable
from decimal import Decimal

from firebase_admin import firestore  # type: ignore[attr-defined]

# Type hint suppression: firestore.transactional is dynamically loaded at runtime
# pylint: disable=no-member

from ..models.expense import Expense
from ..repositories import BalanceRepository
from ..services.balance_service import BalanceService
from .thread_safety import (
    get_group_lock_manager,
    OptimisticLockManager,
    OptimisticLockError,
    RetryConfig,
    with_retry,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ThreadSafeBalanceManager:
    """
    Thread-safe wrapper for balance operations
    
    Provides:
    1. In-memory locking for same-process protection
    2. Optimistic locking for cross-process protection
    3. Automatic retry on version conflicts
    4. Transaction support for atomicity
    """
    
    # Default retry configuration
    DEFAULT_RETRY_CONFIG = RetryConfig(
        max_retries=3,
        base_delay_ms=50.0,
        max_delay_ms=2000.0,
        exponential_base=2.0
    )
    
    def __init__(
        self,
        balance_service: Optional[BalanceService] = None,
        balance_repo: Optional[BalanceRepository] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize the thread-safe balance manager
        
        Args:
            balance_service: BalanceService instance
            balance_repo: BalanceRepository instance
            retry_config: Configuration for retry behavior
        """
        self.balance_service = balance_service or BalanceService()
        self.balance_repo = balance_repo or BalanceRepository()
        self.retry_config = retry_config or self.DEFAULT_RETRY_CONFIG
        self.lock_manager = get_group_lock_manager()
        self.optimistic_lock = OptimisticLockManager()
        self._db = firestore.client()
    
    def _execute_with_lock_and_retry(
        self,
        group_id: str,
        operation: Callable[[], T],
        operation_name: str
    ) -> T:
        """
        Execute an operation with locking and retry logic
        
        Args:
            group_id: Group ID for locking
            operation: Callable to execute
            operation_name: Name for logging
            
        Returns:
            Result of the operation
        """
        @with_retry(config=self.retry_config, retry_exceptions=(OptimisticLockError,))
        def execute_with_retry() -> T:
            with self.lock_manager.acquire_group_lock(group_id):
                logger.debug(
                    "Executing %s for group %s with lock",
                    operation_name,
                    group_id
                )
                return operation()
        
        try:
            result = execute_with_retry()
            logger.info(
                "Successfully completed %s for group %s",
                operation_name,
                group_id
            )
            return result
        except OptimisticLockError as exc:
            logger.error(
                "Failed %s for group %s after retries: %s",
                operation_name,
                group_id,
                str(exc)
            )
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error in %s for group %s: %s",
                operation_name,
                group_id,
                str(exc)
            )
            raise
    
    def add_expense_safe(
        self,
        group_id: str,
        expense: Expense,
        expected_version: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Add expense with thread-safe balance update
        
        Args:
            group_id: Group ID
            expense: Expense to add
            expected_version: Expected balance version (for optimistic locking)
            
        Returns:
            Dictionary with new balances and version
        """
        def operation() -> Dict[str, any]:
            @firestore.transactional
            def update_in_transaction(transaction) -> Dict[str, any]:
                # Get current balance state
                balance_ref = self._db.collection('expense_group_balances').document(group_id)
                balance_doc = balance_ref.get(transaction=transaction)
                
                current_version = 0
                if balance_doc.exists:
                    current_data = balance_doc.to_dict()
                    current_version = current_data.get('version', 0)
                    
                    # Check optimistic lock if version provided
                    if expected_version is not None:
                        self.optimistic_lock.check_version(
                            group_id,
                            expected_version,
                            current_version
                        )
                
                # Calculate and apply deltas
                self.balance_service.add_expense_to_balances(
                    transaction,
                    group_id,
                    expense
                )
                
                # Return new version
                new_version = self.optimistic_lock.increment_version(current_version)
                return {
                    'success': True,
                    'version': new_version,
                    'group_id': group_id,
                    'expense_id': expense.expense_id
                }
            
            transaction = self._db.transaction()
            return update_in_transaction(transaction)
        
        return self._execute_with_lock_and_retry(
            group_id,
            operation,
            "add_expense"
        )
    
    def edit_expense_safe(
        self,
        group_id: str,
        old_expense: Expense,
        new_expense: Expense,
        expected_version: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Edit expense with thread-safe balance update
        
        Args:
            group_id: Group ID
            old_expense: Original expense
            new_expense: Updated expense
            expected_version: Expected balance version
            
        Returns:
            Dictionary with new balances and version
        """
        def operation() -> Dict[str, any]:
            @firestore.transactional
            def update_in_transaction(transaction) -> Dict[str, any]:
                # Get current balance state
                balance_ref = self._db.collection('expense_group_balances').document(group_id)
                balance_doc = balance_ref.get(transaction=transaction)
                
                current_version = 0
                if balance_doc.exists:
                    current_data = balance_doc.to_dict()
                    current_version = current_data.get('version', 0)
                    
                    if expected_version is not None:
                        self.optimistic_lock.check_version(
                            group_id,
                            expected_version,
                            current_version
                        )
                
                # Apply edit deltas
                self.balance_service.edit_expense_in_balances(
                    transaction,
                    group_id,
                    old_expense,
                    new_expense
                )
                
                new_version = self.optimistic_lock.increment_version(current_version)
                return {
                    'success': True,
                    'version': new_version,
                    'group_id': group_id,
                    'expense_id': new_expense.expense_id
                }
            
            transaction = self._db.transaction()
            return update_in_transaction(transaction)
        
        return self._execute_with_lock_and_retry(
            group_id,
            operation,
            "edit_expense"
        )
    
    def delete_expense_safe(
        self,
        group_id: str,
        expense: Expense,
        expected_version: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Delete expense with thread-safe balance update
        
        Args:
            group_id: Group ID
            expense: Expense to delete
            expected_version: Expected balance version
            
        Returns:
            Dictionary with new balances and version
        """
        def operation() -> Dict[str, any]:
            @firestore.transactional
            def update_in_transaction(transaction) -> Dict[str, any]:
                # Get current balance state
                balance_ref = self._db.collection('expense_group_balances').document(group_id)
                balance_doc = balance_ref.get(transaction=transaction)
                
                current_version = 0
                if balance_doc.exists:
                    current_data = balance_doc.to_dict()
                    current_version = current_data.get('version', 0)
                    
                    if expected_version is not None:
                        self.optimistic_lock.check_version(
                            group_id,
                            expected_version,
                            current_version
                        )
                
                # Reverse expense deltas
                self.balance_service.remove_expense_from_balances(
                    transaction,
                    group_id,
                    expense
                )
                
                new_version = self.optimistic_lock.increment_version(current_version)
                return {
                    'success': True,
                    'version': new_version,
                    'group_id': group_id,
                    'expense_id': expense.expense_id
                }
            
            transaction = self._db.transaction()
            return update_in_transaction(transaction)
        
        return self._execute_with_lock_and_retry(
            group_id,
            operation,
            "delete_expense"
        )
    
    def add_settlement_safe(
        self,
        group_id: str,
        from_user_id: str,
        to_user_id: str,
        amount: Decimal,
        expected_version: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Add settlement with thread-safe balance update
        
        Args:
            group_id: Group ID
            from_user_id: User paying
            to_user_id: User receiving
            amount: Settlement amount
            expected_version: Expected balance version
            
        Returns:
            Dictionary with new balances and version
        """
        def operation() -> Dict[str, any]:
            @firestore.transactional
            def update_in_transaction(transaction) -> Dict[str, any]:
                # Get current balance state
                balance_ref = self._db.collection('expense_group_balances').document(group_id)
                balance_doc = balance_ref.get(transaction=transaction)
                
                current_version = 0
                if balance_doc.exists:
                    current_data = balance_doc.to_dict()
                    current_version = current_data.get('version', 0)
                    
                    if expected_version is not None:
                        self.optimistic_lock.check_version(
                            group_id,
                            expected_version,
                            current_version
                        )
                
                # Apply settlement
                self.balance_service.add_settlement_to_balances(
                    transaction,
                    group_id,
                    from_user_id,
                    to_user_id,
                    amount
                )
                
                new_version = self.optimistic_lock.increment_version(current_version)
                return {
                    'success': True,
                    'version': new_version,
                    'group_id': group_id,
                    'from_user': from_user_id,
                    'to_user': to_user_id,
                    'amount': float(amount)
                }
            
            transaction = self._db.transaction()
            return update_in_transaction(transaction)
        
        return self._execute_with_lock_and_retry(
            group_id,
            operation,
            "add_settlement"
        )
    
    def get_balances_with_version(self, group_id: str) -> Dict[str, any]:
        """
        Get current balances with version number
        
        Args:
            group_id: Group ID
            
        Returns:
            Dictionary with balances and version
        """
        try:
            balance_ref = self._db.collection('expense_group_balances').document(group_id)
            balance_doc = balance_ref.get()
            
            if not balance_doc.exists:
                return {
                    'group_id': group_id,
                    'balances': {},
                    'version': 0
                }
            
            data = balance_doc.to_dict()
            return {
                'group_id': group_id,
                'balances': data.get('balances', {}),
                'version': data.get('version', 0)
            }
        except Exception as exc:
            logger.error(
                "Error getting balances with version for group %s: %s",
                group_id,
                str(exc)
            )
            raise
    
    def get_lock_stats(self, group_id: str) -> Optional[Dict[str, any]]:
        """
        Get locking statistics for a group
        
        Args:
            group_id: Group ID
            
        Returns:
            Lock statistics dictionary or None
        """
        stats = self.lock_manager.get_stats(group_id)
        if stats is None:
            return None
        
        return {
            'group_id': group_id,
            'acquisitions': stats.acquisitions,
            'releases': stats.releases,
            'contentions': stats.contentions,
            'timeouts': stats.timeouts,
            'average_wait_time_ms': stats.average_wait_time_ms
        }


# Singleton instance
_thread_safe_balance_manager: Optional[ThreadSafeBalanceManager] = None


def get_thread_safe_balance_manager() -> ThreadSafeBalanceManager:
    """
    Get the global thread-safe balance manager instance
    
    Returns:
        ThreadSafeBalanceManager singleton
    """
    # Use globals() to avoid pylint global statement warning
    if globals().get('_thread_safe_balance_manager') is None:
        globals()['_thread_safe_balance_manager'] = ThreadSafeBalanceManager()
    return globals()['_thread_safe_balance_manager']
