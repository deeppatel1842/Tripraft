"""
Phase 17: History Helper Utilities

Provides efficient batch operations for expense history:
- Batch edit count queries
- History entry creation with return value
- Cache-aware history operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HistoryEnricher:
    """
    Enriches expense data with edit history information.
    
    Phase 17: Reduces N+1 queries by batch-fetching edit counts.
    """
    
    def __init__(self, history_repo):
        """
        Initialize with history repository.
        
        Args:
            history_repo: ExpenseHistoryRepository instance
        """
        self.history_repo = history_repo
    
    def get_edit_counts_batch(
        self,
        expense_ids: List[str],
        batch_size: int = 30
    ) -> Dict[str, int]:
        """
        Get edit counts for multiple expenses efficiently.
        
        Uses IN query with batching to avoid Firestore limits.
        Firestore IN queries support max 30 values.
        
        Args:
            expense_ids: List of expense IDs to check
            batch_size: Maximum IDs per query (default 30, Firestore limit)
            
        Returns:
            Dict mapping expense_id -> edit_count (0 if never edited)
        """
        if not expense_ids:
            return {}
        
        # Deduplicate while preserving order
        unique_ids = list(dict.fromkeys(expense_ids))
        result: Dict[str, int] = {eid: 0 for eid in unique_ids}
        
        try:
            # Process in batches due to Firestore IN limit
            for i in range(0, len(unique_ids), batch_size):
                batch_ids = unique_ids[i:i + batch_size]
                
                # Query history entries for this batch
                history_entries = self.history_repo.query(
                    filters=[
                        ('expense_id', 'in', batch_ids),
                        ('action', '==', 'updated')
                    ],
                    limit=500  # Reasonable upper bound
                )
                
                # Count edits per expense
                for entry in history_entries:
                    exp_id = entry.get('expense_id')
                    if exp_id in result:
                        result[exp_id] += 1
            
            return result
            
        except Exception as exc:
            logger.error("Failed to batch get edit counts: %s", str(exc))
            return result
    
    def get_last_edit_batch(
        self,
        expense_ids: List[str],
        batch_size: int = 30
    ) -> Dict[str, Optional[Dict]]:
        """
        Get last edit info for multiple expenses.
        
        Returns the most recent 'updated' history entry for each expense.
        
        Args:
            expense_ids: List of expense IDs
            batch_size: Maximum IDs per query
            
        Returns:
            Dict mapping expense_id -> last edit entry or None
        """
        if not expense_ids:
            return {}
        
        unique_ids = list(dict.fromkeys(expense_ids))
        result: Dict[str, Optional[Dict]] = {eid: None for eid in unique_ids}
        
        try:
            for i in range(0, len(unique_ids), batch_size):
                batch_ids = unique_ids[i:i + batch_size]
                
                # Query all update entries for this batch
                history_entries = self.history_repo.query(
                    filters=[
                        ('expense_id', 'in', batch_ids),
                        ('action', '==', 'updated')
                    ],
                    order_by=('changed_at', 'DESCENDING'),
                    limit=len(batch_ids) * 3  # Allow for multiple edits per expense
                )
                
                # Track latest per expense
                for entry in history_entries:
                    exp_id = entry.get('expense_id')
                    if exp_id in result and result[exp_id] is None:
                        # First (newest) entry for this expense
                        result[exp_id] = {
                            'changed_at': entry.get('changed_at'),
                            'changed_by': entry.get('changed_by'),
                            'changed_by_name': entry.get('changed_by_name'),
                            'changes': entry.get('changes', [])
                        }
            
            return result
            
        except Exception as exc:
            logger.error("Failed to batch get last edits: %s", str(exc))
            return result
    
    def enrich_expenses_with_history(
        self,
        expenses: List[Dict]
    ) -> List[Dict]:
        """
        Add edit_count and last_edited fields to expenses.
        
        Phase 17: Frontend can show "Edited" badge without extra API calls.
        
        Args:
            expenses: List of expense dicts
            
        Returns:
            Same expenses with history fields added
        """
        if not expenses:
            return expenses
        
        # Get expense IDs
        expense_ids = [
            e.get('expense_id') or e.get('id')
            for e in expenses
            if e.get('expense_id') or e.get('id')
        ]
        
        # Batch fetch edit counts
        edit_counts = self.get_edit_counts_batch(expense_ids)
        
        # Batch fetch last edits for edited expenses
        edited_ids = [eid for eid, count in edit_counts.items() if count > 0]
        last_edits = self.get_last_edit_batch(edited_ids) if edited_ids else {}
        
        # Enrich expenses
        for expense in expenses:
            exp_id = expense.get('expense_id') or expense.get('id')
            if not exp_id:
                continue
            
            expense['edit_count'] = edit_counts.get(exp_id, 0)
            
            if expense['edit_count'] > 0:
                last_edit = last_edits.get(exp_id)
                if last_edit:
                    expense['last_edited_at'] = last_edit.get('changed_at')
                    expense['last_edited_by'] = last_edit.get('changed_by')
                    expense['last_edited_by_name'] = last_edit.get('changed_by_name')
        
        return expenses


def create_history_entry_with_return(
    history_repo,
    expense_id: str,
    group_id: str,
    action: str,
    changed_by: str,
    after_snapshot: Dict,
    before_snapshot: Optional[Dict] = None,
    changed_by_name: Optional[str] = None,
    expense_description: Optional[str] = None,
    expense_amount: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create history entry and return it for frontend use.
    
    Phase 17: Returns the created entry so frontend can update
    optimistically without refetching.
    
    Args:
        history_repo: ExpenseHistoryRepository instance
        expense_id: ID of the expense
        group_id: ID of the group
        action: "created", "updated", "deleted", "restored"
        changed_by: User ID who made the change
        after_snapshot: Complete expense data after change
        before_snapshot: Complete expense data before change (optional)
        changed_by_name: Display name of user
        expense_description: Description for history display
        expense_amount: Amount for history display
        
    Returns:
        Dict with the created history entry
    """
    from ..models.expense_history import compute_changes
    
    changed_at = datetime.utcnow()
    
    # Compute changes for updates
    changes = []
    if action == "updated" and before_snapshot:
        changes = compute_changes(before_snapshot, after_snapshot)
    
    # Build history data
    history_data = {
        'expense_id': expense_id,
        'group_id': group_id,
        'action': action,
        'changed_by': changed_by,
        'changed_by_name': changed_by_name,
        'changed_at': changed_at.isoformat(),
        'changes': changes,
    }
    
    # Add expense info for delete entries (helpful for history display)
    if action == "deleted" and (expense_description or expense_amount):
        history_data['expense_description'] = expense_description
        history_data['expense_amount'] = expense_amount
    
    try:
        # Create the entry
        entry_id = history_repo.create_history_entry(
            expense_id=expense_id,
            group_id=group_id,
            action=action,
            changed_by=changed_by,
            after_snapshot=after_snapshot,
            before_snapshot=before_snapshot,
            changed_by_name=changed_by_name
        )
        
        # Return the entry with ID
        history_data['id'] = entry_id
        history_data['history_id'] = entry_id
        
        return history_data
        
    except Exception as exc:
        logger.error("Failed to create history entry: %s", str(exc))
        # Return entry without ID (frontend can still use optimistically)
        history_data['id'] = f"temp_{int(datetime.utcnow().timestamp() * 1000)}"
        history_data['_failed'] = True
        return history_data


def format_balances_for_response(
    balances_dict: Dict[str, Any],
    members: List[Dict],
    all_members_map: Optional[Dict[str, Dict]] = None
) -> List[Dict]:
    """
    Format balances dict into array format for frontend.
    
    Args:
        balances_dict: Dict mapping user_id -> balance
        members: List of active member dicts
        all_members_map: Optional dict mapping user_id -> member info
        
    Returns:
        List of balance objects with user info
    """
    if all_members_map is None:
        all_members_map = {}
    
    result = []
    members_added = set()
    
    # Add active members
    for member in members:
        uid = member.get('user_id') if isinstance(member, dict) else str(member)
        if not uid:
            continue
        
        member_info = all_members_map.get(uid, {})
        display_name = (
            member_info.get('display_name') or
            member.get('display_name', 'Unknown') if isinstance(member, dict) else 'Unknown'
        )
        balance_value = float(balances_dict.get(uid, 0))
        
        result.append({
            'user_id': uid,
            'display_name': display_name,
            'balance': balance_value,
            'net_balance': balance_value,
            'is_active': member_info.get('is_active', True)
        })
        members_added.add(uid)
    
    # Add removed members with non-zero balances
    for uid, balance_value in balances_dict.items():
        if uid in members_added:
            continue
        
        balance_float = float(balance_value)
        if abs(balance_float) < 0.01:
            continue
        
        member_info = all_members_map.get(uid, {})
        display_name = member_info.get('display_name', f'Former Member ({uid[:8]}...)')
        
        result.append({
            'user_id': uid,
            'display_name': display_name,
            'balance': balance_float,
            'net_balance': balance_float,
            'is_active': False
        })
    
    return result
