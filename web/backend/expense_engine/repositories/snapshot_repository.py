"""
Snapshot Repository
Phase 20: Bootstrap snapshot storage for pre-computed view documents

Reduces mega-bootstrap from ~10-12 reads to 1 read per group by storing
pre-aggregated data that would normally require multiple collection reads.

Collection: expense_bootstrap_snapshots
Document ID: {userId}_{groupId}
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import BaseRepository
from ..config import firestore_collections, redis_config
from ..utils.serialization import serialize_balances, serialize_expense_for_snapshot, serialize_document

# Import cache manager
try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


class SnapshotRepository(BaseRepository):
    """
    Repository for bootstrap snapshot documents
    
    Schema: expense_bootstrap_snapshots/{userId}_{groupId}
    {
        "userId": "abc123",
        "groupId": "xyz789",
        "groupInfo": {
            "name": "Trip to Paris",
            "currency": "EUR",
            "createdAt": "...",
            "memberCount": 4
        },
        "members": [
            {"userId": "abc123", "displayName": "John", "photoURL": "..."},
            {"userId": "def456", "displayName": "Jane", "photoURL": "..."}
        ],
        "balances": {
            "abc123": 50.00,
            "def456": -50.00
        },
        "yourBalance": 50.00,  // Convenience field for the snapshot owner
        "recentExpenses": [
            {"id": "exp1", "description": "Dinner", "amount": 100, "date": "..."}
        ],
        "pendingInvitationsCount": 2,
        "totalExpenses": 1500.00,
        "expenseCount": 15,
        "lastActivity": "2025-12-03T10:00:00Z",
        "lastUpdated": "2025-12-03T10:00:00Z",
        "version": 1
    }
    """
    
    def __init__(self):
        super().__init__()
        self._cache = get_cache_manager() if CACHE_ENABLED else None
    
    def get_collection_name(self) -> str:
        """Return collection name for bootstrap snapshots"""
        return firestore_collections.BOOTSTRAP_SNAPSHOTS
    
    @staticmethod
    def make_doc_id(user_id: str, group_id: str) -> str:
        """Generate document ID from user and group IDs"""
        return f"{user_id}_{group_id}"
    
    @staticmethod
    def parse_doc_id(doc_id: str) -> tuple:
        """Parse document ID into (user_id, group_id)"""
        parts = doc_id.split('_', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid snapshot doc_id: {doc_id}")
        return parts[0], parts[1]
    
    def _get_cache_key(self, user_id: str, group_id: str) -> str:
        """Generate Redis cache key"""
        return redis_config.KEY_BOOTSTRAP_SNAPSHOT.format(uid=user_id, gid=group_id)
    
    def get_snapshot(self, user_id: str, group_id: str) -> Optional[Dict]:
        """
        Get a user's snapshot for a specific group
        
        Uses Redis cache with fallback to Firestore
        
        Args:
            user_id: User ID
            group_id: Group ID
            
        Returns:
            Snapshot document or None
        """
        doc_id = self.make_doc_id(user_id, group_id)
        cache_key = self._get_cache_key(user_id, group_id)
        
        # Try cache first
        if CACHE_ENABLED and self._cache and self._cache.is_available():
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("[CACHE][+] Bootstrap snapshot hit: %s/%s", user_id, group_id)
                return cached
        
        # Fetch from Firestore
        snapshot = self.get_by_id(doc_id)
        
        # Cache result
        if snapshot and CACHE_ENABLED and self._cache and self._cache.is_available():
            self._cache.set(cache_key, snapshot, ttl=redis_config.TTL_BOOTSTRAP)
            logger.debug("[CACHE][S] Bootstrap snapshot cached: %s/%s", user_id, group_id)
        
        return snapshot
    
    def get_user_snapshots(self, user_id: str) -> List[Dict]:
        """
        Get all snapshots for a user (all their groups)
        
        Used for dashboard view showing all groups at once.
        
        Args:
            user_id: User ID
            
        Returns:
            List of snapshot documents
        """
        try:
            # Query by userId field
            docs = self.collection.where('userId', '==', user_id).stream()
            snapshots = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                snapshots.append(data)
            return snapshots
        except Exception as exc:
            logger.error("Failed to get user snapshots: %s", exc)
            return []
    
    def create_snapshot(
        self,
        user_id: str,
        group_id: str,
        group_info: Dict,
        members: List[Dict],
        balances: Dict[str, float],
        recent_expenses: List[Dict] = None,
        pending_invitations_count: int = 0,
        total_expenses: float = 0.0,
        expense_count: int = 0
    ) -> Dict:
        """
        Create a new bootstrap snapshot
        
        Args:
            user_id: User ID this snapshot is for
            group_id: Group ID
            group_info: Group metadata (name, currency, created_at, member_count)
            members: List of member dicts (userId, displayName, photoURL)
            balances: Dict of userId -> balance amount
            recent_expenses: List of recent expense summaries
            pending_invitations_count: Number of pending invitations
            total_expenses: Total amount spent in group
            expense_count: Number of expenses in group
            
        Returns:
            Created snapshot document
        """
        doc_id = self.make_doc_id(user_id, group_id)
        now = datetime.utcnow().isoformat()
        
        snapshot_data = {
            'userId': user_id,
            'groupId': group_id,
            'groupInfo': group_info,
            'members': members or [],
            'balances': balances or {},
            'yourBalance': balances.get(user_id, 0.0) if balances else 0.0,
            'recentExpenses': recent_expenses or [],
            'pendingInvitationsCount': pending_invitations_count,
            'totalExpenses': total_expenses,
            'expenseCount': expense_count,
            'lastActivity': now,
            'lastUpdated': now,
            'version': 1
        }
        
        self.create(doc_id, snapshot_data)
        
        # Invalidate cache
        self._invalidate_cache(user_id, group_id)
        
        logger.info("Created bootstrap snapshot: %s", doc_id)
        return snapshot_data
    
    def update_snapshot(
        self,
        user_id: str,
        group_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields in a snapshot
        
        Args:
            user_id: User ID
            group_id: Group ID
            updates: Dict of fields to update
            
        Returns:
            True if successful
        """
        doc_id = self.make_doc_id(user_id, group_id)
        
        # Always update lastUpdated
        updates['lastUpdated'] = datetime.utcnow().isoformat()
        
        # Increment version
        snapshot = self.get_by_id(doc_id)
        if snapshot:
            updates['version'] = snapshot.get('version', 0) + 1
        
        self.update(doc_id, updates)
        
        # Invalidate cache
        self._invalidate_cache(user_id, group_id)
        
        logger.debug("Updated bootstrap snapshot: %s", doc_id)
        return True
    
    def update_balances(
        self,
        group_id: str,
        balances: Dict[str, float],
        affected_user_ids: List[str] = None
    ) -> int:
        """
        Update balance fields in all snapshots for a group
        
        Args:
            group_id: Group ID
            balances: New balance dict (userId -> amount)
            affected_user_ids: If provided, only update these users
            
        Returns:
            Number of snapshots updated
        """
        try:
            # Serialize balances to convert Decimal to float
            serialized_balances = serialize_balances(balances)
            
            # Find all snapshots for this group
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                # Skip if not in affected list
                if affected_user_ids and user_id not in affected_user_ids:
                    continue
                
                # Update balance fields
                updates = {
                    'balances': serialized_balances,
                    'yourBalance': serialized_balances.get(user_id, 0.0),
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            logger.info("Updated balances in %d snapshots for group %s", updated_count, group_id)
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to update balances: %s", exc)
            return 0
    
    def add_recent_expense(
        self,
        group_id: str,
        expense_summary: Dict,
        max_recent: int = 10
    ) -> int:
        """
        Add an expense to the recentExpenses list in all group snapshots
        
        Args:
            group_id: Group ID
            expense_summary: Expense summary dict (id, description, amount, date, etc.)
            max_recent: Maximum number of recent expenses to keep
            
        Returns:
            Number of snapshots updated
        """
        try:
            # Serialize the expense for Firestore
            serialized_expense = serialize_expense_for_snapshot(expense_summary)
            
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                # Get current recent expenses
                recent = data.get('recentExpenses', [])
                
                # Add new expense at the beginning
                recent.insert(0, serialized_expense)
                
                # Trim to max
                recent = recent[:max_recent]
                
                # Get expense amount as float
                expense_amount = serialized_expense.get('amount', 0)
                
                # Update
                updates = {
                    'recentExpenses': recent,
                    'expenseCount': data.get('expenseCount', 0) + 1,
                    'totalExpenses': data.get('totalExpenses', 0) + expense_amount,
                    'lastActivity': datetime.utcnow().isoformat(),
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            logger.debug("Added expense to %d snapshots for group %s", updated_count, group_id)
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to add recent expense: %s", exc)
            return 0
    
    def update_expense_in_snapshots(
        self,
        group_id: str,
        expense_id: str,
        updated_expense: Dict,
        old_amount: float = 0
    ) -> int:
        """
        Update an expense in the recentExpenses list
        
        Args:
            group_id: Group ID
            expense_id: Expense ID to update
            updated_expense: Updated expense summary
            old_amount: Previous amount (for totalExpenses adjustment)
            
        Returns:
            Number of snapshots updated
        """
        try:
            # Serialize the expense for Firestore
            serialized_expense = serialize_expense_for_snapshot(updated_expense)
            
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            new_amount = serialized_expense.get('amount', 0)
            amount_diff = new_amount - (float(old_amount) if old_amount else 0)
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                # Find and update the expense in recent list
                recent = data.get('recentExpenses', [])
                found = False
                for i, exp in enumerate(recent):
                    if exp.get('id') == expense_id:
                        recent[i] = serialized_expense
                        found = True
                        break
                
                # Update snapshot
                updates = {
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                if found:
                    updates['recentExpenses'] = recent
                    updates['totalExpenses'] = data.get('totalExpenses', 0) + amount_diff
                    updates['lastActivity'] = datetime.utcnow().isoformat()
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to update expense in snapshots: %s", exc)
            return 0
    
    def remove_expense_from_snapshots(
        self,
        group_id: str,
        expense_id: str,
        expense_amount: float = 0
    ) -> int:
        """
        Remove an expense from the recentExpenses list (on delete)
        
        Args:
            group_id: Group ID
            expense_id: Expense ID to remove
            expense_amount: Amount being removed (for totalExpenses adjustment)
            
        Returns:
            Number of snapshots updated
        """
        try:
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                # Remove from recent list
                recent = data.get('recentExpenses', [])
                recent = [exp for exp in recent if exp.get('id') != expense_id]
                
                # Update
                updates = {
                    'recentExpenses': recent,
                    'expenseCount': max(0, data.get('expenseCount', 0) - 1),
                    'totalExpenses': max(0, data.get('totalExpenses', 0) - expense_amount),
                    'lastActivity': datetime.utcnow().isoformat(),
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to remove expense from snapshots: %s", exc)
            return 0
    
    def update_members(
        self,
        group_id: str,
        members: List[Dict],
        member_count: int = None
    ) -> int:
        """
        Update member list in all group snapshots
        
        Called when members join/leave the group.
        
        Args:
            group_id: Group ID
            members: Updated member list
            member_count: New member count (optional)
            
        Returns:
            Number of snapshots updated
        """
        try:
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                updates = {
                    'members': members,
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                if member_count is not None:
                    updates['groupInfo'] = {
                        **data.get('groupInfo', {}),
                        'memberCount': member_count
                    }
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to update members in snapshots: %s", exc)
            return 0
    
    def update_invitation_count(
        self,
        group_id: str,
        count: int = None,
        delta: int = None
    ) -> int:
        """
        Update pending invitation count in all group snapshots
        
        Args:
            group_id: Group ID
            count: Absolute count (overrides delta)
            delta: Change in count (+1 for new invite, -1 for accept/decline)
            
        Returns:
            Number of snapshots updated
        """
        try:
            docs = self.collection.where('groupId', '==', group_id).stream()
            updated_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                user_id = data.get('userId')
                
                if count is not None:
                    new_count = count
                elif delta is not None:
                    new_count = max(0, data.get('pendingInvitationsCount', 0) + delta)
                else:
                    continue
                
                updates = {
                    'pendingInvitationsCount': new_count,
                    'lastUpdated': datetime.utcnow().isoformat()
                }
                
                self.update(doc.id, updates)
                self._invalidate_cache(user_id, group_id)
                updated_count += 1
            
            return updated_count
            
        except Exception as exc:
            logger.error("Failed to update invitation count: %s", exc)
            return 0
    
    def delete_snapshot(self, user_id: str, group_id: str) -> bool:
        """
        Delete a user's snapshot for a group
        
        Called when user leaves a group.
        
        Args:
            user_id: User ID
            group_id: Group ID
            
        Returns:
            True if successful
        """
        doc_id = self.make_doc_id(user_id, group_id)
        self.delete(doc_id)
        self._invalidate_cache(user_id, group_id)
        logger.info("Deleted bootstrap snapshot: %s", doc_id)
        return True
    
    def delete_group_snapshots(self, group_id: str) -> int:
        """
        Delete all snapshots for a group
        
        Called when a group is deleted.
        
        Args:
            group_id: Group ID
            
        Returns:
            Number of snapshots deleted
        """
        try:
            docs = self.collection.where('groupId', '==', group_id).stream()
            deleted_count = 0
            
            for doc in docs:
                user_id = doc.to_dict().get('userId')
                doc.reference.delete()
                self._invalidate_cache(user_id, group_id)
                deleted_count += 1
            
            logger.info("Deleted %d snapshots for group %s", deleted_count, group_id)
            return deleted_count
            
        except Exception as exc:
            logger.error("Failed to delete group snapshots: %s", exc)
            return 0
    
    def _invalidate_cache(self, user_id: str, group_id: str) -> None:
        """Invalidate Redis cache for a snapshot"""
        if not CACHE_ENABLED or not self._cache or not self._cache.is_available():
            return
        
        cache_key = self._get_cache_key(user_id, group_id)
        self._cache.delete(cache_key)
        logger.debug("[CACHE][X] Bootstrap snapshot invalidated: %s/%s", user_id, group_id)
