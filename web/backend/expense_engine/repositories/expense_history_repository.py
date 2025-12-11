"""
Expense History Repository
Handles expense history/audit trail data access
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from .base import BaseRepository
from ..config import firestore_collections
from ..models.expense_history import ExpenseHistory, compute_changes

logger = logging.getLogger(__name__)


class ExpenseHistoryRepository(BaseRepository[ExpenseHistory]):
    """
    Repository for expense edit history
    
    Collection: expense_history
    
    Provides:
    - Create history entries on expense changes
    - Query history by expense_id
    - Query history by group_id (for group-wide audit)
    - Query history by user (for user activity log)
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.EXPENSE_HISTORY
    
    def create_history_entry(
        self,
        expense_id: str,
        group_id: str,
        action: str,
        changed_by: str,
        after_snapshot: Dict,
        before_snapshot: Optional[Dict] = None,
        changed_by_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create a new history entry
        
        Args:
            expense_id: ID of the expense
            group_id: ID of the group
            action: "created", "updated", "deleted", "restored"
            changed_by: User ID who made the change
            after_snapshot: Complete expense data after change
            before_snapshot: Complete expense data before change (optional)
            changed_by_name: Display name of user
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            ID of the created history entry
        """
        try:
            # Compute changes if this is an update
            changes = []
            if action == "updated" and before_snapshot:
                changes = compute_changes(before_snapshot, after_snapshot)
            
            # Create history entry
            history_entry = ExpenseHistory(
                expense_id=expense_id,
                group_id=group_id,
                action=action,
                changed_by=changed_by,
                changed_by_name=changed_by_name,
                changed_at=datetime.utcnow(),
                changes=changes,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Convert to dict for Firestore
            history_data = history_entry.to_dict()
            
            # Remove None id before creating
            history_data.pop('id', None)
            
            # Create document
            doc_ref = self.get_collection().document()
            doc_ref.set(history_data)
            
            logger.info(
                "Created history entry for expense %s: %s by %s",
                expense_id, action, changed_by
            )
            
            return doc_ref.id
            
        except Exception as exc:
            logger.error("Error creating history entry: %s", str(exc))
            raise
    
    def get_expense_history(
        self,
        expense_id: str,
        limit: int = 50,
        include_snapshots: bool = False
    ) -> List[Dict]:
        """
        Get history for a specific expense
        
        Args:
            expense_id: ID of the expense
            limit: Maximum entries to return
            include_snapshots: Whether to include full before/after snapshots
            
        Returns:
            List of history entries, newest first
        """
        try:
            entries = self.query(
                filters=[('expense_id', '==', expense_id)],
                order_by=('changed_at', 'DESCENDING'),
                limit=limit
            )
            
            # Optionally strip snapshots to reduce payload
            if not include_snapshots:
                for entry in entries:
                    entry.pop('before_snapshot', None)
                    entry.pop('after_snapshot', None)
            
            return entries
            
        except Exception as exc:
            logger.error("Error getting expense history: %s", str(exc))
            raise
    
    def get_group_history(
        self,
        group_id: str,
        limit: int = 100,
        offset: int = 0,
        include_snapshots: bool = False
    ) -> Dict:
        """
        Get all history entries for a group (audit log)
        
        Args:
            group_id: ID of the group
            limit: Maximum entries to return
            offset: Number of entries to skip
            include_snapshots: Whether to include full snapshots
            
        Returns:
            Dict with entries and pagination info
        """
        try:
            # Get all entries for group
            all_entries = self.query(
                filters=[('group_id', '==', group_id)],
                order_by=('changed_at', 'DESCENDING'),
                limit=500
            )
            
            total = len(all_entries)
            
            # Apply pagination
            paginated = all_entries[offset:offset + limit]
            
            # Optionally strip snapshots
            if not include_snapshots:
                for entry in paginated:
                    entry.pop('before_snapshot', None)
                    entry.pop('after_snapshot', None)
            
            return {
                'entries': paginated,
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(paginated) < total
            }
            
        except Exception as exc:
            logger.error("Error getting group history: %s", str(exc))
            raise
    
    def get_user_activity(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get history of changes made by a specific user
        
        Args:
            user_id: ID of the user
            group_id: Optional filter by group
            limit: Maximum entries to return
            
        Returns:
            List of history entries
        """
        try:
            filters = [('changed_by', '==', user_id)]
            if group_id:
                filters.append(('group_id', '==', group_id))
            
            entries = self.query(
                filters=filters,
                order_by=('changed_at', 'DESCENDING'),
                limit=limit
            )
            
            # Strip snapshots for user activity
            for entry in entries:
                entry.pop('before_snapshot', None)
                entry.pop('after_snapshot', None)
            
            return entries
            
        except Exception as exc:
            logger.error("Error getting user activity: %s", str(exc))
            raise
    
    def get_recent_edits(
        self,
        expense_ids: List[str],
        limit_per_expense: int = 1
    ) -> Dict[str, List[Dict]]:
        """
        Get most recent edit for multiple expenses (for showing "Edited" badge)
        
        Args:
            expense_ids: List of expense IDs
            limit_per_expense: Number of history entries per expense
            
        Returns:
            Dict mapping expense_id to list of recent history entries
        """
        try:
            result = {}
            
            for expense_id in expense_ids:
                entries = self.query(
                    filters=[
                        ('expense_id', '==', expense_id),
                        ('action', '==', 'updated')
                    ],
                    order_by=('changed_at', 'DESCENDING'),
                    limit=limit_per_expense
                )
                
                if entries:
                    # Strip snapshots
                    for entry in entries:
                        entry.pop('before_snapshot', None)
                        entry.pop('after_snapshot', None)
                    result[expense_id] = entries
            
            return result
            
        except Exception as exc:
            logger.error("Error getting recent edits: %s", str(exc))
            raise
    
    def get_edit_count(self, expense_id: str) -> int:
        """
        Get number of times an expense was edited
        
        Args:
            expense_id: ID of the expense
            
        Returns:
            Number of edit (update) entries
        """
        try:
            entries = self.query(
                filters=[
                    ('expense_id', '==', expense_id),
                    ('action', '==', 'updated')
                ],
                limit=100
            )
            return len(entries)
            
        except Exception as exc:
            logger.error("Error getting edit count: %s", str(exc))
            return 0
    
    def delete_expense_history(self, expense_id: str) -> int:
        """
        Delete all history entries for an expense (for permanent deletion)
        
        Args:
            expense_id: ID of the expense
            
        Returns:
            Number of entries deleted
        """
        try:
            entries = self.query(
                filters=[('expense_id', '==', expense_id)],
                limit=500
            )
            
            batch = self.db.batch()
            count = 0
            
            for entry in entries:
                if 'id' in entry:
                    doc_ref = self.get_collection().document(entry['id'])
                    batch.delete(doc_ref)
                    count += 1
            
            if count > 0:
                batch.commit()
                logger.info("Deleted %d history entries for expense %s", count, expense_id)
            
            return count
            
        except Exception as exc:
            logger.error("Error deleting expense history: %s", str(exc))
            raise
