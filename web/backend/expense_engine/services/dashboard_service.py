"""
Dashboard Service - Phase 20 Extreme Optimization
Business logic for user dashboard operations.

Provides single-document pattern for achieving minimal Firestore operations:
- 1 READ on login (mega-bootstrap)
- 1 WRITE per mutation (batched)
- 0 reads for cached data

This service coordinates between DashboardRepository and other services
to maintain the denormalized dashboard document.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..repositories import DashboardRepository, GroupRepository, BalanceRepository
from ..config import redis_config

try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service for managing user dashboards.
    
    Phase 20 Architecture:
    - Single document contains ALL user data
    - Every mutation updates the document via batched writes
    - Redis cache serves all reads after initial load
    - Cache invalidation on mutations keeps data fresh
    """
    
    def __init__(
        self,
        dashboard_repo: Optional[DashboardRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        balance_repo: Optional[BalanceRepository] = None
    ):
        """
        Initialize service with repositories.
        
        Args:
            dashboard_repo: Dashboard repository instance
            group_repo: Group repository (for fallback data)
            balance_repo: Balance repository (for fallback data)
        """
        self.dashboard_repo = dashboard_repo or DashboardRepository()
        self.group_repo = group_repo or GroupRepository()
        self.balance_repo = balance_repo or BalanceRepository()
        self._cache = get_cache_manager() if CACHE_ENABLED else None
    
    def get_user_dashboard(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        Get user's complete dashboard data.
        
        Phase 20: This is the ONLY read needed for dashboard view.
        - First checks Redis cache (0 Firestore ops)
        - If miss, single Firestore read
        - Caches result for 1 hour
        
        Args:
            user_id: User ID
            force_refresh: Skip cache and read from Firestore
            
        Returns:
            Complete dashboard data including:
            - groups: All groups with embedded data
            - pendingInvitations: Pending invitations
            - stats: Global statistics
        """
        return self.dashboard_repo.get_dashboard(
            user_id=user_id,
            use_cache=not force_refresh
        )
    
    def ensure_dashboard_exists(self, user_id: str) -> Dict:
        """
        Ensure a dashboard document exists for the user.
        Creates one if it doesn't exist.
        
        Called during:
        - User registration
        - First login
        - Migration from old schema
        
        Args:
            user_id: User ID
            
        Returns:
            Dashboard document (existing or newly created)
        """
        dashboard = self.dashboard_repo.get_by_id(user_id)
        
        if not dashboard:
            logger.info("Creating new dashboard for user %s", user_id)
            dashboard = self.dashboard_repo.create_dashboard(user_id)
        
        return dashboard
    
    def on_group_created(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict
    ) -> bool:
        """
        Handle group creation - add to user's dashboard.
        
        Called after batched group creation completes.
        Updates dashboard with new group data.
        
        Args:
            user_id: Creator's user ID
            group_id: New group ID
            group_data: Group data to embed
            
        Returns:
            True if successful
        """
        return self.dashboard_repo.add_group_to_dashboard(
            user_id=user_id,
            group_id=group_id,
            group_data=group_data
        )
    
    def on_invitation_accepted(
        self,
        new_member_id: str,
        group_id: str,
        group_data: Dict,
        existing_member_ids: List[str]
    ) -> None:
        """
        Handle invitation acceptance.
        
        Updates:
        - New member's dashboard: Add the group
        - Existing members' dashboards: Update member list
        
        Args:
            new_member_id: User ID of the new member
            group_id: Group ID
            group_data: Group data for new member
            existing_member_ids: IDs of existing members to update
        """
        # Add group to new member's dashboard
        self.dashboard_repo.add_group_to_dashboard(
            user_id=new_member_id,
            group_id=group_id,
            group_data=group_data
        )
        
        # Update existing members' dashboards
        if existing_member_ids:
            self.dashboard_repo.update_group_members(
                group_id=group_id,
                members=group_data.get('members', []),
                member_count=group_data.get('memberCount', len(existing_member_ids) + 1),
                affected_users=existing_member_ids
            )
    
    def on_expense_created(
        self,
        group_id: str,
        expense_summary: Dict,
        new_balances: Dict[str, float],
        affected_user_ids: List[str]
    ) -> int:
        """
        Handle expense creation - update all affected dashboards.
        
        Args:
            group_id: Group ID
            expense_summary: Summary of the expense
            new_balances: Updated balances for the group
            affected_user_ids: Users whose dashboards need updating
            
        Returns:
            Number of dashboards updated
        """
        return self.dashboard_repo.add_expense_to_dashboards(
            group_id=group_id,
            expense_summary=expense_summary,
            balances=new_balances,
            affected_users=affected_user_ids
        )
    
    def on_expense_updated(
        self,
        group_id: str,
        new_balances: Dict[str, float],
        affected_user_ids: List[str]
    ) -> int:
        """
        Handle expense update - update balances in dashboards.
        
        Args:
            group_id: Group ID
            new_balances: Updated balances
            affected_user_ids: Users to update
            
        Returns:
            Number of dashboards updated
        """
        return self.dashboard_repo.update_group_balances(
            group_id=group_id,
            balances=new_balances,
            affected_users=affected_user_ids
        )
    
    def on_settlement_created(
        self,
        group_id: str,
        settlement_summary: Dict,
        new_balances: Dict[str, float],
        affected_user_ids: List[str]
    ) -> int:
        """
        Handle settlement creation - update dashboards.
        
        Args:
            group_id: Group ID
            settlement_summary: Summary of the settlement
            new_balances: Updated balances
            affected_user_ids: Users to update
            
        Returns:
            Number of dashboards updated
        """
        return self.dashboard_repo.add_settlement_to_dashboards(
            group_id=group_id,
            settlement_summary=settlement_summary,
            balances=new_balances,
            affected_users=affected_user_ids
        )
    
    def on_invitation_sent(
        self,
        invitee_user_id: str,
        invitation: Dict
    ) -> bool:
        """
        Handle invitation sent - add to invitee's dashboard.
        
        Args:
            invitee_user_id: User ID of the invitee
            invitation: Invitation data
            
        Returns:
            True if successful
        """
        return self.dashboard_repo.add_invitation_to_dashboard(
            user_id=invitee_user_id,
            invitation=invitation
        )
    
    def on_invitation_removed(
        self,
        user_id: str,
        invitation_id: str
    ) -> bool:
        """
        Handle invitation removal (accepted/declined).
        
        Args:
            user_id: User ID
            invitation_id: Invitation ID to remove
            
        Returns:
            True if successful
        """
        return self.dashboard_repo.remove_invitation_from_dashboard(
            user_id=user_id,
            invitation_id=invitation_id
        )
    
    def invalidate_user_cache(self, user_id: str) -> None:
        """
        Invalidate cache for a specific user.
        
        Called when dashboard data changes outside normal mutation flow.
        
        Args:
            user_id: User ID
        """
        self.dashboard_repo._invalidate_cache(user_id)
    
    def invalidate_group_members_cache(
        self,
        group_id: str,
        member_ids: List[str]
    ) -> None:
        """
        Invalidate cache for all members of a group.
        
        Called when group data changes.
        
        Args:
            group_id: Group ID
            member_ids: List of member IDs
        """
        for user_id in member_ids:
            self.dashboard_repo._invalidate_cache(user_id)
    
    def build_dashboard_from_scratch(
        self,
        user_id: str
    ) -> Dict:
        """
        Build dashboard document from existing data.
        
        Used for:
        - Migration from old schema
        - Recovering corrupted dashboard
        - First-time setup for existing users
        
        This reads from multiple collections and aggregates into
        a single dashboard document.
        
        Args:
            user_id: User ID
            
        Returns:
            Built dashboard document
        """
        try:
            # Get user's groups
            groups_data = {}
            member_docs = self.group_repo.get_user_memberships(user_id)
            
            for membership in member_docs:
                group_id = membership.get('group_id')
                if not group_id:
                    continue
                
                # Get group details
                group = self.group_repo.get_by_id(group_id)
                if not group:
                    continue
                
                # Get balances
                balance_doc = self.balance_repo.get_by_id(group_id)
                balances = balance_doc.get('balances', {}) if balance_doc else {}
                
                # Build group entry
                groups_data[group_id] = {
                    'groupId': group_id,
                    'name': group.get('name', 'Unnamed Group'),
                    'currency': group.get('currency', 'USD'),
                    'memberCount': group.get('member_count', 1),
                    'yourBalance': balances.get(user_id, 0.0),
                    'totalSpent': group.get('total_spent', 0.0),
                    'expenseCount': group.get('expense_count', 0),
                    'isSettled': abs(balances.get(user_id, 0.0)) < 0.01,
                    'lastActivity': group.get('last_activity', datetime.utcnow().isoformat()),
                    'members': self._build_member_list(group),
                    'balances': balances,
                    'recentExpenses': [],
                    'recentSettlements': []
                }
            
            # Calculate stats
            stats = self._calculate_stats(groups_data)
            
            # Build dashboard
            dashboard = {
                'userId': user_id,
                'lastUpdated': datetime.utcnow().isoformat(),
                'groups': groups_data,
                'pendingInvitations': [],  # Will be populated by invitation service
                'stats': stats
            }
            
            # Save to Firestore
            self.dashboard_repo.create(user_id, dashboard)
            self.dashboard_repo._invalidate_cache(user_id)
            
            logger.info("Built dashboard from scratch for user %s", user_id)
            return dashboard
            
        except Exception as exc:
            logger.error("Failed to build dashboard: %s", exc)
            return self.dashboard_repo.create_dashboard(user_id)
    
    def _build_member_list(self, group: Dict) -> List[Dict]:
        """Build member list from group document."""
        member_details = group.get('member_details', {})
        return [
            {
                'userId': uid,
                'displayName': details.get('display_name', 'Unknown'),
                'photoUrl': details.get('photo_url', '')
            }
            for uid, details in member_details.items()
        ]
    
    def _calculate_stats(self, groups: Dict) -> Dict:
        """Calculate global stats from groups."""
        total_owed = 0.0
        total_owes = 0.0
        
        for g in groups.values():
            bal = g.get('yourBalance', 0)
            if bal > 0:
                total_owed += bal
            else:
                total_owes += abs(bal)
        
        return {
            'totalOwed': total_owed,
            'totalOwes': total_owes,
            'netBalance': total_owed - total_owes,
            'groupCount': len(groups),
            'activeGroupCount': len([g for g in groups.values() if not g.get('isSettled', True)])
        }
