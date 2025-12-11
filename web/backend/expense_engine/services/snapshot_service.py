"""
Snapshot Service
Phase 20: Orchestrates bootstrap snapshot creation and updates

This service is responsible for:
1. Creating snapshots when users join groups
2. Updating snapshots when expenses/settlements change
3. Updating snapshots when invitations change
4. Rebuilding snapshots when needed

The goal is to pre-compute data that mega-bootstrap needs, reducing
reads from ~10-12 per group to 1 per group.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from ..repositories import (
    SnapshotRepository,
    GroupRepository,
    ExpenseRepository,
    BalanceRepository,
    InvitationRepository,
    UserRepository
)

logger = logging.getLogger(__name__)


class SnapshotService:
    """
    Service for managing bootstrap snapshots
    
    Snapshot Lifecycle:
    - Created: When user joins a group (accept invitation or create group)
    - Updated: On expense create/update/delete, settlement create, invitation change
    - Deleted: When user leaves group or group is deleted
    
    Performance Strategy:
    - Snapshots are updated asynchronously where possible
    - Partial updates are preferred over full rebuilds
    - Batch updates for group-wide changes
    """
    
    # Maximum recent expenses to store in snapshot
    MAX_RECENT_EXPENSES = 10
    
    def __init__(
        self,
        snapshot_repo: Optional[SnapshotRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        expense_repo: Optional[ExpenseRepository] = None,
        balance_repo: Optional[BalanceRepository] = None,
        invitation_repo: Optional[InvitationRepository] = None,
        user_repo: Optional[UserRepository] = None
    ):
        """Initialize with repositories (lazy-loaded to avoid Firebase in tests)"""
        self._snapshot_repo = snapshot_repo
        self._group_repo = group_repo
        self._expense_repo = expense_repo
        self._balance_repo = balance_repo
        self._invitation_repo = invitation_repo
        self._user_repo = user_repo
    
    @property
    def snapshot_repo(self) -> SnapshotRepository:
        """Lazy-load snapshot repository"""
        if self._snapshot_repo is None:
            self._snapshot_repo = SnapshotRepository()
        return self._snapshot_repo
    
    @property
    def group_repo(self) -> GroupRepository:
        """Lazy-load group repository"""
        if self._group_repo is None:
            self._group_repo = GroupRepository()
        return self._group_repo
    
    @property
    def expense_repo(self) -> ExpenseRepository:
        """Lazy-load expense repository"""
        if self._expense_repo is None:
            self._expense_repo = ExpenseRepository()
        return self._expense_repo
    
    @property
    def balance_repo(self) -> BalanceRepository:
        """Lazy-load balance repository"""
        if self._balance_repo is None:
            self._balance_repo = BalanceRepository()
        return self._balance_repo
    
    @property
    def invitation_repo(self) -> InvitationRepository:
        """Lazy-load invitation repository"""
        if self._invitation_repo is None:
            self._invitation_repo = InvitationRepository()
        return self._invitation_repo
    
    @property
    def user_repo(self) -> UserRepository:
        """Lazy-load user repository"""
        if self._user_repo is None:
            self._user_repo = UserRepository()
        return self._user_repo
    
    # =========================================================================
    # SNAPSHOT RETRIEVAL
    # =========================================================================
    
    def get_snapshot(self, user_id: str, group_id: str) -> Optional[Dict]:
        """
        Get a user's snapshot for a group
        
        If snapshot doesn't exist, creates it on-demand.
        
        Args:
            user_id: User ID
            group_id: Group ID
            
        Returns:
            Snapshot dict or None if user not in group
        """
        snapshot = self.snapshot_repo.get_snapshot(user_id, group_id)
        
        if not snapshot:
            # Try to build snapshot on-demand
            logger.info("Snapshot not found, building on-demand: %s/%s", user_id, group_id)
            snapshot = self.build_snapshot(user_id, group_id)
        
        return snapshot
    
    def get_user_snapshots(self, user_id: str) -> List[Dict]:
        """
        Get all snapshots for a user (dashboard view)
        
        Args:
            user_id: User ID
            
        Returns:
            List of snapshots for all user's groups
        """
        return self.snapshot_repo.get_user_snapshots(user_id)
    
    # =========================================================================
    # SNAPSHOT CREATION
    # =========================================================================
    
    def build_snapshot(self, user_id: str, group_id: str) -> Optional[Dict]:
        """
        Build a complete snapshot for a user/group from current data
        
        This is a "cold start" operation that reads all necessary data
        and creates the snapshot. Used for:
        - Initial snapshot creation
        - Snapshot rebuild after corruption
        - On-demand creation for missing snapshots
        
        Args:
            user_id: User ID
            group_id: Group ID
            
        Returns:
            Created snapshot or None if user not in group
        """
        try:
            # Get group data
            group_data = self.group_repo.get_by_id(group_id)
            if not group_data:
                logger.warning("Group not found for snapshot: %s", group_id)
                return None
            
            # Verify user is a member
            members_list = group_data.get('members', [])
            if user_id not in members_list:
                logger.warning("User %s not in group %s", user_id, group_id)
                return None
            
            # Build group info
            group_info = {
                'name': group_data.get('name', 'Unnamed Group'),
                'currency': group_data.get('currency', 'USD'),
                'createdAt': group_data.get('created_at'),
                'memberCount': len(members_list)
            }
            
            # Get member details
            members = self._get_member_details(members_list)
            
            # Get balances - balance_data is a GroupBalance Pydantic model
            balance_data = self.balance_repo.get_group_balances(group_id)
            if balance_data:
                # Convert GroupBalance model to dict for balances extraction
                balance_dict = balance_data.model_dump() if hasattr(balance_data, 'model_dump') else {}
                balances = balance_dict.get('balances', {})
            else:
                balances = {}
            
            # Get recent expenses
            recent_expenses = self._get_recent_expenses(group_id)
            
            # Get pending invitation count
            invitations = self.invitation_repo.get_group_invitations(group_id, status='pending')
            pending_count = len(invitations) if invitations else 0
            
            # Calculate totals - these fields may not exist on GroupBalance model
            total_expenses = 0
            expense_count = 0
            
            # Create snapshot
            return self.snapshot_repo.create_snapshot(
                user_id=user_id,
                group_id=group_id,
                group_info=group_info,
                members=members,
                balances=balances,
                recent_expenses=recent_expenses,
                pending_invitations_count=pending_count,
                total_expenses=total_expenses,
                expense_count=expense_count
            )
            
        except Exception as exc:
            logger.error("Failed to build snapshot %s/%s: %s", user_id, group_id, exc)
            return None
    
    def create_snapshots_for_group(self, group_id: str) -> int:
        """
        Create snapshots for all members of a group
        
        Used when:
        - A new group is created
        - Snapshots need to be rebuilt for a group
        
        Args:
            group_id: Group ID
            
        Returns:
            Number of snapshots created
        """
        try:
            group_data = self.group_repo.get_by_id(group_id)
            if not group_data:
                return 0
            
            members_list = group_data.get('members', [])
            created_count = 0
            
            for user_id in members_list:
                snapshot = self.build_snapshot(user_id, group_id)
                if snapshot:
                    created_count += 1
            
            logger.info("Created %d snapshots for group %s", created_count, group_id)
            return created_count
            
        except Exception as exc:
            logger.error("Failed to create group snapshots: %s", exc)
            return 0
    
    def create_snapshot_for_new_member(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict = None
    ) -> Optional[Dict]:
        """
        Create snapshot when a new member joins a group
        
        Also updates existing member snapshots with new member info.
        
        Args:
            user_id: New member's user ID
            group_id: Group ID
            group_data: Optional pre-fetched group data
            
        Returns:
            New member's snapshot
        """
        try:
            # Build snapshot for new member
            new_snapshot = self.build_snapshot(user_id, group_id)
            
            # Update existing members' snapshots with new member
            if group_data is None:
                group_data = self.group_repo.get_by_id(group_id)
            
            if group_data:
                members_list = group_data.get('members', [])
                members = self._get_member_details(members_list)
                self.snapshot_repo.update_members(
                    group_id=group_id,
                    members=members,
                    member_count=len(members_list)
                )
            
            return new_snapshot
            
        except Exception as exc:
            logger.error("Failed to create snapshot for new member: %s", exc)
            return None
    
    # =========================================================================
    # EXPENSE UPDATES
    # =========================================================================
    
    def on_expense_created(
        self,
        group_id: str,
        expense_data: Dict,
        new_balances: Dict[str, float] = None
    ) -> None:
        """
        Update snapshots when an expense is created
        
        Args:
            group_id: Group ID
            expense_data: The created expense
            new_balances: Updated balance dict (optional)
        """
        try:
            # Build expense summary for recent list
            expense_summary = self._build_expense_summary(expense_data)
            
            # Add to recent expenses
            self.snapshot_repo.add_recent_expense(
                group_id=group_id,
                expense_summary=expense_summary,
                max_recent=self.MAX_RECENT_EXPENSES
            )
            
            # Update balances if provided
            if new_balances:
                self.snapshot_repo.update_balances(group_id, new_balances)
            
            logger.debug("Updated snapshots for new expense in group %s", group_id)
            
        except Exception as exc:
            logger.error("Failed to update snapshots on expense create: %s", exc)
    
    def on_expense_updated(
        self,
        group_id: str,
        expense_id: str,
        expense_data: Dict,
        old_amount: float = 0,
        new_balances: Dict[str, float] = None
    ) -> None:
        """
        Update snapshots when an expense is updated
        
        Args:
            group_id: Group ID
            expense_id: Expense ID
            expense_data: Updated expense data
            old_amount: Previous amount (for total adjustment)
            new_balances: Updated balance dict (optional)
        """
        try:
            expense_summary = self._build_expense_summary(expense_data)
            
            self.snapshot_repo.update_expense_in_snapshots(
                group_id=group_id,
                expense_id=expense_id,
                updated_expense=expense_summary,
                old_amount=old_amount
            )
            
            if new_balances:
                self.snapshot_repo.update_balances(group_id, new_balances)
            
            logger.debug("Updated snapshots for expense %s update", expense_id)
            
        except Exception as exc:
            logger.error("Failed to update snapshots on expense update: %s", exc)
    
    def on_expense_deleted(
        self,
        group_id: str,
        expense_id: str,
        expense_amount: float = 0,
        new_balances: Dict[str, float] = None
    ) -> None:
        """
        Update snapshots when an expense is deleted
        
        Args:
            group_id: Group ID
            expense_id: Deleted expense ID
            expense_amount: Amount that was deleted
            new_balances: Updated balance dict (optional)
        """
        try:
            self.snapshot_repo.remove_expense_from_snapshots(
                group_id=group_id,
                expense_id=expense_id,
                expense_amount=expense_amount
            )
            
            if new_balances:
                self.snapshot_repo.update_balances(group_id, new_balances)
            
            logger.debug("Updated snapshots for expense %s deletion", expense_id)
            
        except Exception as exc:
            logger.error("Failed to update snapshots on expense delete: %s", exc)
    
    # =========================================================================
    # SETTLEMENT UPDATES
    # =========================================================================
    
    def on_settlement_created(
        self,
        group_id: str,
        new_balances: Dict[str, float]
    ) -> None:
        """
        Update snapshots when a settlement is created
        
        Settlements only affect balances, not recent expenses.
        
        Args:
            group_id: Group ID
            new_balances: Updated balance dict
        """
        try:
            self.snapshot_repo.update_balances(group_id, new_balances)
            logger.debug("Updated snapshots for settlement in group %s", group_id)
        except Exception as exc:
            logger.error("Failed to update snapshots on settlement: %s", exc)
    
    # =========================================================================
    # INVITATION UPDATES
    # =========================================================================
    
    def on_invitation_created(self, group_id: str) -> None:
        """Update snapshots when an invitation is created"""
        try:
            self.snapshot_repo.update_invitation_count(group_id, delta=1)
        except Exception as exc:
            logger.error("Failed to update invitation count: %s", exc)
    
    def on_invitation_accepted(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict = None
    ) -> None:
        """
        Handle invitation acceptance
        
        Creates snapshot for new member and updates existing snapshots.
        
        Args:
            user_id: New member's user ID
            group_id: Group ID
            group_data: Optional pre-fetched group data
        """
        try:
            # Create snapshot for new member
            self.create_snapshot_for_new_member(user_id, group_id, group_data)
            
            # Decrement invitation count
            self.snapshot_repo.update_invitation_count(group_id, delta=-1)
            
        except Exception as exc:
            logger.error("Failed to handle invitation acceptance: %s", exc)
    
    def on_invitation_declined(self, group_id: str) -> None:
        """Update snapshots when an invitation is declined"""
        try:
            self.snapshot_repo.update_invitation_count(group_id, delta=-1)
        except Exception as exc:
            logger.error("Failed to update invitation count: %s", exc)
    
    # =========================================================================
    # MEMBER UPDATES
    # =========================================================================
    
    def on_member_removed(self, user_id: str, group_id: str) -> None:
        """
        Handle member removal from group
        
        Deletes their snapshot and updates remaining members' snapshots.
        
        Args:
            user_id: Removed member's user ID
            group_id: Group ID
        """
        try:
            # Delete removed member's snapshot
            self.snapshot_repo.delete_snapshot(user_id, group_id)
            
            # Update remaining members' snapshots
            group_data = self.group_repo.get_by_id(group_id)
            if group_data:
                members_list = group_data.get('members', [])
                members = self._get_member_details(members_list)
                self.snapshot_repo.update_members(
                    group_id=group_id,
                    members=members,
                    member_count=len(members_list)
                )
            
        except Exception as exc:
            logger.error("Failed to handle member removal: %s", exc)
    
    def on_group_deleted(self, group_id: str) -> None:
        """Delete all snapshots when a group is deleted"""
        try:
            self.snapshot_repo.delete_group_snapshots(group_id)
        except Exception as exc:
            logger.error("Failed to delete group snapshots: %s", exc)
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _get_member_details(self, member_ids: List[str]) -> List[Dict]:
        """
        Get display details for a list of member IDs
        
        Args:
            member_ids: List of user IDs
            
        Returns:
            List of member detail dicts
        """
        members = []
        for user_id in member_ids:
            try:
                user = self.user_repo.get_by_id(user_id)
                if user:
                    members.append({
                        'userId': user_id,
                        'displayName': user.get('display_name') or user.get('email', 'Unknown'),
                        'photoURL': user.get('photo_url', '')
                    })
                else:
                    members.append({
                        'userId': user_id,
                        'displayName': 'Unknown User',
                        'photoURL': ''
                    })
            except Exception:
                members.append({
                    'userId': user_id,
                    'displayName': 'Unknown User',
                    'photoURL': ''
                })
        return members
    
    def _get_recent_expenses(self, group_id: str) -> List[Dict]:
        """
        Get recent expenses for a group
        
        Args:
            group_id: Group ID
            
        Returns:
            List of expense summaries
        """
        try:
            result = self.expense_repo.get_group_expenses(
                group_id,
                limit=self.MAX_RECENT_EXPENSES
            )
            # get_group_expenses returns {'expenses': [...], 'total': ..., ...}
            expenses = result.get('expenses', []) if isinstance(result, dict) else result
            return [self._build_expense_summary(exp) for exp in expenses]
        except Exception as exc:
            logger.error("Failed to get recent expenses: %s", exc)
            return []
    
    def _build_expense_summary(self, expense_data: Dict) -> Dict:
        """
        Build a summary dict for an expense (for recent expenses list)
        
        Args:
            expense_data: Full expense data
            
        Returns:
            Summary dict with key fields
        """
        # Handle case where expense_data might be a string ID instead of dict
        if isinstance(expense_data, str):
            logger.warning("Expected expense dict, got string: %s", expense_data[:50] if len(expense_data) > 50 else expense_data)
            return {'id': expense_data}
        
        if not isinstance(expense_data, dict):
            logger.warning("Expected expense dict, got %s", type(expense_data).__name__)
            return {}
            
        return {
            'id': expense_data.get('id') or expense_data.get('expense_id'),
            'description': expense_data.get('description', ''),
            'amount': expense_data.get('amount', 0),
            'currency': expense_data.get('currency', 'USD'),
            'category': expense_data.get('category', 'Other'),
            'date': expense_data.get('date'),
            'paidBy': expense_data.get('paid_by'),
            'createdAt': expense_data.get('created_at')
        }
