"""
Write-Through Cache Manager - Phase 20.4
Provides write-through cache patterns for all expense engine operations.

Write-through caching:
1. Write to Firestore (source of truth)
2. Immediately update Redis cache with the new data
3. No re-read required - response uses computed data

This eliminates the pattern of:
1. Write to Firestore
2. Invalidate cache
3. Re-read from Firestore to return updated data

Results in 0 additional reads per write operation.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from ..utils.cache_manager import get_cache_manager
    from ..config import redis_config
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    redis_config = None
    def get_cache_manager():
        return None


class WriteThroughCacheManager:
    """
    Manages write-through cache updates for expense engine.
    
    Usage:
        cache_mgr = WriteThroughCacheManager()
        cache_mgr.update_expense(expense_id, expense_data, group_id)
        cache_mgr.update_balances(group_id, balances_data, affected_users)
    """
    
    def __init__(self):
        self._cache = get_cache_manager() if CACHE_ENABLED else None
    
    def is_available(self) -> bool:
        """Check if cache is available"""
        return self._cache is not None and self._cache.is_available()
    
    def update_expense(
        self,
        expense_id: str,
        expense_data: Dict,
        group_id: str
    ) -> bool:
        """
        Write-through update for expense data.
        
        Args:
            expense_id: Expense ID
            expense_data: Complete expense data
            group_id: Group ID for related cache invalidation
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            # Write expense to cache
            cache_key = redis_config.KEY_EXPENSE.format(eid=expense_id)
            self._cache.set(cache_key, expense_data, ttl=redis_config.TTL_EXPENSE)
            
            # Invalidate group expense list (pagination makes update complex)
            self._cache.delete_pattern(f"expense:group_expenses:{group_id}:*")
            
            logger.debug("[WRITE-THROUGH] Expense %s cached", expense_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update expense cache: %s", e)
            return False
    
    def update_balances(
        self,
        group_id: str,
        balances_data: Dict,
        affected_user_ids: List[str] = None
    ) -> bool:
        """
        Write-through update for group balances.
        
        Args:
            group_id: Group ID
            balances_data: Complete balances data (from balance calculation)
            affected_user_ids: Users whose personal caches should be updated
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            # Write balances to cache
            cache_key = redis_config.KEY_GROUP_BALANCES.format(gid=group_id)
            self._cache.set(cache_key, balances_data, ttl=redis_config.TTL_BALANCE)
            
            logger.debug("[WRITE-THROUGH] Balances for group %s cached", group_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update balances cache: %s", e)
            return False
    
    def update_group_summary(
        self,
        group_id: str,
        summary_data: Dict
    ) -> bool:
        """
        Write-through update for group summary.
        
        Args:
            group_id: Group ID
            summary_data: Complete summary data
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            cache_key = redis_config.KEY_GROUP_SUMMARY.format(gid=group_id)
            self._cache.set(cache_key, summary_data, ttl=redis_config.TTL_GROUP_SUMMARY)
            
            logger.debug("[WRITE-THROUGH] Summary for group %s cached", group_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update summary cache: %s", e)
            return False
    
    def update_user_dashboard(
        self,
        user_id: str,
        dashboard_data: Dict
    ) -> bool:
        """
        Write-through update for user dashboard.
        
        Args:
            user_id: User ID
            dashboard_data: Complete dashboard data
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            cache_key = redis_config.KEY_DASHBOARD.format(uid=user_id)
            self._cache.set(cache_key, dashboard_data, ttl=redis_config.TTL_DASHBOARD)
            
            logger.debug("[WRITE-THROUGH] Dashboard for user %s cached", user_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update dashboard cache: %s", e)
            return False
    
    def update_bootstrap_snapshot(
        self,
        user_id: str,
        group_id: str,
        snapshot_data: Dict
    ) -> bool:
        """
        Write-through update for bootstrap snapshot.
        
        Args:
            user_id: User ID
            group_id: Group ID
            snapshot_data: Complete snapshot data
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            cache_key = redis_config.KEY_BOOTSTRAP_SNAPSHOT.format(uid=user_id, gid=group_id)
            self._cache.set(cache_key, snapshot_data, ttl=redis_config.TTL_BOOTSTRAP)
            
            logger.debug("[WRITE-THROUGH] Snapshot for user %s/group %s cached", user_id, group_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update snapshot cache: %s", e)
            return False
    
    def update_settlement(
        self,
        settlement_id: str,
        settlement_data: Dict,
        group_id: str
    ) -> bool:
        """
        Write-through update for settlement data.
        
        Args:
            settlement_id: Settlement ID
            settlement_data: Complete settlement data
            group_id: Group ID for related cache updates
            
        Returns:
            True if cache was updated
        """
        if not self.is_available():
            return False
        
        try:
            # Invalidate settlements list cache (write-through would be complex)
            self._cache.delete(redis_config.KEY_GROUP_SETTLEMENTS.format(gid=group_id))
            
            logger.debug("[WRITE-THROUGH] Settlement list invalidated for group %s", group_id)
            return True
            
        except Exception as e:
            logger.warning("[WRITE-THROUGH] Failed to update settlement cache: %s", e)
            return False
    
    def batch_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        Perform multiple write-through updates in batch.
        
        Args:
            updates: List of update specs, each with:
                - type: 'expense', 'balances', 'summary', 'dashboard', 'snapshot'
                - data: The data to cache
                - ids: Relevant IDs (expense_id, group_id, user_id, etc.)
                
        Returns:
            Number of successful updates
        """
        if not self.is_available():
            return 0
        
        successful = 0
        
        for update in updates:
            update_type = update.get('type')
            data = update.get('data')
            ids = update.get('ids', {})
            
            try:
                if update_type == 'expense':
                    if self.update_expense(ids.get('expense_id'), data, ids.get('group_id')):
                        successful += 1
                elif update_type == 'balances':
                    if self.update_balances(ids.get('group_id'), data, ids.get('user_ids')):
                        successful += 1
                elif update_type == 'summary':
                    if self.update_group_summary(ids.get('group_id'), data):
                        successful += 1
                elif update_type == 'dashboard':
                    if self.update_user_dashboard(ids.get('user_id'), data):
                        successful += 1
                elif update_type == 'snapshot':
                    if self.update_bootstrap_snapshot(ids.get('user_id'), ids.get('group_id'), data):
                        successful += 1
            except Exception as e:
                logger.warning("[WRITE-THROUGH] Batch update failed for %s: %s", update_type, e)
        
        if successful > 0:
            logger.debug("[WRITE-THROUGH] Batch: %d/%d updates successful", successful, len(updates))
        
        return successful


# Singleton instance
_write_through_cache_manager: Optional[WriteThroughCacheManager] = None


def get_write_through_cache() -> WriteThroughCacheManager:
    """Get singleton write-through cache manager"""
    global _write_through_cache_manager
    if _write_through_cache_manager is None:
        _write_through_cache_manager = WriteThroughCacheManager()
    return _write_through_cache_manager


# Convenience functions for common operations

def write_through_expense(expense_id: str, expense_data: Dict, group_id: str) -> bool:
    """Write-through update for expense"""
    return get_write_through_cache().update_expense(expense_id, expense_data, group_id)


def write_through_balances(group_id: str, balances_data: Dict, affected_users: List[str] = None) -> bool:
    """Write-through update for balances"""
    return get_write_through_cache().update_balances(group_id, balances_data, affected_users)


def write_through_dashboard(user_id: str, dashboard_data: Dict) -> bool:
    """Write-through update for dashboard"""
    return get_write_through_cache().update_user_dashboard(user_id, dashboard_data)


def write_through_snapshot(user_id: str, group_id: str, snapshot_data: Dict) -> bool:
    """Write-through update for snapshot"""
    return get_write_through_cache().update_bootstrap_snapshot(user_id, group_id, snapshot_data)


__all__ = [
    'WriteThroughCacheManager',
    'get_write_through_cache',
    'write_through_expense',
    'write_through_balances',
    'write_through_dashboard',
    'write_through_snapshot'
]
