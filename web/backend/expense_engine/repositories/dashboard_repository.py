"""
Dashboard Repository - Phase 20 Extreme Optimization
Single-document pattern for achieving 10 total Firestore operations per session.

Collection: expense_user_dashboards/{user_id}
Contains ALL data a user needs in a single document:
- All groups with embedded balances, members, recent expenses
- Pending invitations
- Global stats (total owed/owes)

This replaces multiple reads from:
- expense_groups (N groups)
- expense_balances (N groups)
- expense_group_members (N groups)
- expense_invitations
- expense_bootstrap_snapshots
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from .base import BaseRepository
from ..config import firestore_collections

try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


class DashboardRepository(BaseRepository):
    """
    Repository for user dashboard documents.
    
    Schema: expense_user_dashboards/{user_id}
    {
        "userId": "abc123",
        "lastUpdated": "2025-12-04T10:00:00Z",
        
        "groups": {
            "group1": {
                "groupId": "group1",
                "name": "Trip to Paris",
                "currency": "EUR",
                "memberCount": 3,
                "yourBalance": 50.00,
                "totalSpent": 1500.00,
                "expenseCount": 15,
                "isSettled": false,
                "lastActivity": "2025-12-04T09:00:00Z",
                "members": [
                    {"userId": "abc", "displayName": "John", "photoUrl": "..."},
                    {"userId": "def", "displayName": "Jane", "photoUrl": "..."}
                ],
                "balances": {"abc": 50.0, "def": -30.0, "ghi": -20.0},
                "recentExpenses": [
                    {"id": "exp1", "description": "Dinner", "amount": 100, ...}
                ],
                "recentSettlements": [
                    {"id": "set1", "payerId": "def", "receiverId": "abc", ...}
                ]
            }
        },
        
        "pendingInvitations": [
            {
                "id": "inv1",
                "groupId": "group2",
                "groupName": "Beach Trip",
                "inviterId": "xyz",
                "inviterName": "Alice",
                "inviterEmail": "alice@example.com",
                "createdAt": "2025-12-03T10:00:00Z"
            }
        ],
        
        "stats": {
            "totalOwed": 150.00,
            "totalOwes": 50.00,
            "netBalance": 100.00,
            "groupCount": 3,
            "activeGroupCount": 2
        }
    }
    """
    
    # Cache TTL: 1 hour (invalidated on mutations)
    CACHE_TTL = 3600
    
    def __init__(self):
        super().__init__()
        self._cache = get_cache_manager() if CACHE_ENABLED else None
    
    def get_collection_name(self) -> str:
        """Return collection name for user dashboards"""
        return 'expense_user_dashboards'
    
    def _get_cache_key(self, user_id: str) -> str:
        """Generate Redis cache key"""
        return f"expense:dashboard:{user_id}"
    
    def get_dashboard(self, user_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get user's complete dashboard in a SINGLE read.
        
        This is the core of Phase 20 optimization:
        - First check Redis cache
        - If miss, single Firestore read
        - Cache result for 1 hour
        
        Args:
            user_id: User ID
            use_cache: Whether to use Redis cache
            
        Returns:
            Complete dashboard document or None
        """
        cache_key = self._get_cache_key(user_id)
        
        # Try cache first
        if use_cache and self._cache and self._cache.is_available():
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("[CACHE][+] Dashboard hit for user %s", user_id)
                return cached
        
        # Single Firestore read
        dashboard = self.get_by_id(user_id)
        
        if dashboard:
            # Cache for 1 hour
            if self._cache and self._cache.is_available():
                self._cache.set(cache_key, dashboard, ttl=self.CACHE_TTL)
                logger.debug("[CACHE][S] Dashboard cached for user %s", user_id)
        
        return dashboard
    
    def create_dashboard(self, user_id: str, initial_data: Dict = None) -> Dict:
        """
        Create a new dashboard document for a user.
        
        Called on first login or user registration.
        
        Args:
            user_id: User ID
            initial_data: Optional initial data
            
        Returns:
            Created dashboard document
        """
        now = datetime.utcnow().isoformat()
        
        dashboard = {
            'userId': user_id,
            'lastUpdated': now,
            'groups': {},
            'pendingInvitations': [],
            'stats': {
                'totalOwed': 0.0,
                'totalOwes': 0.0,
                'netBalance': 0.0,
                'groupCount': 0,
                'activeGroupCount': 0
            }
        }
        
        if initial_data:
            dashboard.update(initial_data)
        
        self.create(user_id, dashboard)
        self._invalidate_cache(user_id)
        
        logger.info("Created dashboard for user %s", user_id)
        return dashboard
    
    def add_group_to_dashboard(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict
    ) -> bool:
        """
        Add a group to user's dashboard.
        
        Called when:
        - User creates a group
        - User accepts an invitation
        
        Args:
            user_id: User ID
            group_id: Group ID
            group_data: Group data to embed
            
        Returns:
            True if successful
        """
        try:
            # Ensure dashboard exists
            dashboard = self.get_by_id(user_id)
            if not dashboard:
                dashboard = self.create_dashboard(user_id)
            
            # Add group
            groups = dashboard.get('groups', {})
            groups[group_id] = {
                'groupId': group_id,
                'name': group_data.get('name', 'Unnamed Group'),
                'currency': group_data.get('currency', 'USD'),
                'memberCount': group_data.get('memberCount', 1),
                'yourBalance': 0.0,
                'totalSpent': 0.0,
                'expenseCount': 0,
                'isSettled': True,
                'lastActivity': datetime.utcnow().isoformat(),
                'members': group_data.get('members', []),
                'balances': group_data.get('balances', {}),
                'recentExpenses': [],
                'recentSettlements': []
            }
            
            # Update stats
            stats = dashboard.get('stats', {})
            stats['groupCount'] = len(groups)
            stats['activeGroupCount'] = len([g for g in groups.values() if not g.get('isSettled', True)])
            
            # Update document
            self.update(user_id, {
                'groups': groups,
                'stats': stats,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            logger.info("Added group %s to dashboard for user %s", group_id, user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to add group to dashboard: %s", exc)
            return False
    
    def update_group_balances(
        self,
        group_id: str,
        balances: Dict[str, float],
        affected_users: List[str]
    ) -> int:
        """
        Update balance data in all affected users' dashboards.
        
        Called after expense create/update/delete or settlement.
        
        Args:
            group_id: Group ID
            balances: New balance dict {user_id: balance}
            affected_users: List of user IDs to update
            
        Returns:
            Number of dashboards updated
        """
        updated_count = 0
        now = datetime.utcnow().isoformat()
        
        for user_id in affected_users:
            try:
                dashboard = self.get_by_id(user_id)
                if not dashboard:
                    continue
                
                groups = dashboard.get('groups', {})
                if group_id not in groups:
                    continue
                
                # Update group data
                groups[group_id]['balances'] = balances
                groups[group_id]['yourBalance'] = balances.get(user_id, 0.0)
                groups[group_id]['isSettled'] = abs(balances.get(user_id, 0.0)) < 0.01
                groups[group_id]['lastActivity'] = now
                
                # Recalculate global stats
                total_owed = 0.0
                total_owes = 0.0
                for g in groups.values():
                    bal = g.get('yourBalance', 0)
                    if bal > 0:
                        total_owed += bal
                    else:
                        total_owes += abs(bal)
                
                stats = dashboard.get('stats', {})
                stats['totalOwed'] = total_owed
                stats['totalOwes'] = total_owes
                stats['netBalance'] = total_owed - total_owes
                stats['activeGroupCount'] = len([g for g in groups.values() if not g.get('isSettled', True)])
                
                # Update
                self.update(user_id, {
                    'groups': groups,
                    'stats': stats,
                    'lastUpdated': now
                })
                
                self._invalidate_cache(user_id)
                updated_count += 1
                
            except Exception as exc:
                logger.error("Failed to update dashboard for user %s: %s", user_id, exc)
        
        logger.info("Updated %d dashboards for group %s", updated_count, group_id)
        return updated_count
    
    def add_expense_to_dashboards(
        self,
        group_id: str,
        expense_summary: Dict,
        balances: Dict[str, float],
        affected_users: List[str],
        max_recent: int = 10
    ) -> int:
        """
        Add an expense to affected users' dashboards.
        
        Args:
            group_id: Group ID
            expense_summary: Expense summary dict
            balances: Updated balances
            affected_users: Users to update
            max_recent: Max recent expenses to keep
            
        Returns:
            Number of dashboards updated
        """
        updated_count = 0
        now = datetime.utcnow().isoformat()
        
        for user_id in affected_users:
            try:
                dashboard = self.get_by_id(user_id)
                if not dashboard:
                    continue
                
                groups = dashboard.get('groups', {})
                if group_id not in groups:
                    continue
                
                group = groups[group_id]
                
                # Add expense to recent list
                recent = group.get('recentExpenses', [])
                recent.insert(0, expense_summary)
                recent = recent[:max_recent]
                
                # Update group data
                group['recentExpenses'] = recent
                group['expenseCount'] = group.get('expenseCount', 0) + 1
                group['totalSpent'] = group.get('totalSpent', 0) + expense_summary.get('amount', 0)
                group['balances'] = balances
                group['yourBalance'] = balances.get(user_id, 0.0)
                group['isSettled'] = abs(balances.get(user_id, 0.0)) < 0.01
                group['lastActivity'] = now
                
                groups[group_id] = group
                
                # Update stats
                stats = self._recalculate_stats(groups)
                
                self.update(user_id, {
                    'groups': groups,
                    'stats': stats,
                    'lastUpdated': now
                })
                
                self._invalidate_cache(user_id)
                updated_count += 1
                
            except Exception as exc:
                logger.error("Failed to add expense to dashboard: %s", exc)
        
        return updated_count
    
    def add_settlement_to_dashboards(
        self,
        group_id: str,
        settlement_summary: Dict,
        balances: Dict[str, float],
        affected_users: List[str],
        max_recent: int = 10
    ) -> int:
        """
        Add a settlement to affected users' dashboards.
        """
        updated_count = 0
        now = datetime.utcnow().isoformat()
        
        for user_id in affected_users:
            try:
                dashboard = self.get_by_id(user_id)
                if not dashboard:
                    continue
                
                groups = dashboard.get('groups', {})
                if group_id not in groups:
                    continue
                
                group = groups[group_id]
                
                # Add settlement
                recent = group.get('recentSettlements', [])
                recent.insert(0, settlement_summary)
                recent = recent[:max_recent]
                
                group['recentSettlements'] = recent
                group['balances'] = balances
                group['yourBalance'] = balances.get(user_id, 0.0)
                group['isSettled'] = abs(balances.get(user_id, 0.0)) < 0.01
                group['lastActivity'] = now
                
                groups[group_id] = group
                stats = self._recalculate_stats(groups)
                
                self.update(user_id, {
                    'groups': groups,
                    'stats': stats,
                    'lastUpdated': now
                })
                
                self._invalidate_cache(user_id)
                updated_count += 1
                
            except Exception as exc:
                logger.error("Failed to add settlement to dashboard: %s", exc)
        
        return updated_count
    
    def add_invitation_to_dashboard(
        self,
        user_id: str,
        invitation: Dict
    ) -> bool:
        """
        Add a pending invitation to user's dashboard.
        """
        try:
            dashboard = self.get_by_id(user_id)
            if not dashboard:
                dashboard = self.create_dashboard(user_id)
            
            invitations = dashboard.get('pendingInvitations', [])
            invitations.append({
                'id': invitation.get('id'),
                'groupId': invitation.get('group_id'),
                'groupName': invitation.get('group_name', 'Unknown'),
                'inviterId': invitation.get('inviter_id'),
                'inviterName': invitation.get('inviter_name', 'Someone'),
                'inviterEmail': invitation.get('inviter_email', ''),
                'createdAt': datetime.utcnow().isoformat()
            })
            
            self.update(user_id, {
                'pendingInvitations': invitations,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to add invitation: %s", exc)
            return False
    
    def remove_invitation_from_dashboard(
        self,
        user_id: str,
        invitation_id: str
    ) -> bool:
        """
        Remove a pending invitation (accepted or declined).
        """
        try:
            dashboard = self.get_by_id(user_id)
            if not dashboard:
                return False
            
            invitations = dashboard.get('pendingInvitations', [])
            invitations = [inv for inv in invitations if inv.get('id') != invitation_id]
            
            self.update(user_id, {
                'pendingInvitations': invitations,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to remove invitation: %s", exc)
            return False
    
    def update_group_members(
        self,
        group_id: str,
        members: List[Dict],
        member_count: int,
        affected_users: List[str]
    ) -> int:
        """
        Update member list in affected dashboards.
        """
        updated_count = 0
        now = datetime.utcnow().isoformat()
        
        for user_id in affected_users:
            try:
                dashboard = self.get_by_id(user_id)
                if not dashboard:
                    continue
                
                groups = dashboard.get('groups', {})
                if group_id not in groups:
                    continue
                
                groups[group_id]['members'] = members
                groups[group_id]['memberCount'] = member_count
                groups[group_id]['lastActivity'] = now
                
                self.update(user_id, {
                    'groups': groups,
                    'lastUpdated': now
                })
                
                self._invalidate_cache(user_id)
                updated_count += 1
                
            except Exception as exc:
                logger.error("Failed to update members: %s", exc)
        
        return updated_count
    
    def _recalculate_stats(self, groups: Dict) -> Dict:
        """Recalculate global stats from groups."""
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
    
    def _invalidate_cache(self, user_id: str):
        """Invalidate Redis cache for user."""
        if self._cache and self._cache.is_available():
            cache_key = self._get_cache_key(user_id)
            self._cache.delete(cache_key)
            logger.debug("[CACHE][-] Invalidated dashboard for user %s", user_id)
