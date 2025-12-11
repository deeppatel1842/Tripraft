"""
Extreme Dashboard Service - Phase 21 True 10-Operation Architecture
====================================================================

This service implements the ultimate optimization goal:
- 1 READ on login (single dashboard document)
- 1 WRITE per mutation (batched)
- 0 reads for all other operations (Redis cache)

The extreme dashboard document contains EVERYTHING a user needs:
- All groups with full details (members, balances, expenses, settlements)
- All pending invitations with JWT tokens
- Global statistics

This eliminates 95%+ of Firestore reads by embedding all data in one document.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..config import firestore_collections, redis_config

try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

try:
    from ..firestore_counter import record_read, record_write
except ImportError:
    def record_read(count=1, collection=None): pass
    def record_write(count=1, collection=None): pass

logger = logging.getLogger(__name__)


# Maximum items to store in arrays (to stay under 1MB limit)
MAX_RECENT_EXPENSES = 20
MAX_RECENT_SETTLEMENTS = 10
MAX_RECENT_HISTORY = 20


class ExtremeDashboardService:
    """
    Phase 21: Extreme optimization service for 10-operation sessions.
    
    Key principles:
    1. Single document read on login (expense_user_dashboards/{uid})
    2. All mutations use batch writes (1 write operation)
    3. All reads served from Redis (0 Firestore operations)
    4. Write-through cache (update Redis after Firestore write)
    5. Computed responses (no re-reads after mutations)
    """
    
    # Cache TTL: 1 hour (invalidated on mutations)
    CACHE_TTL = 3600
    
    def __init__(self):
        self._cache = get_cache_manager() if CACHE_ENABLED else None
        self._db = None
    
    @property
    def db(self):
        """Lazy-load Firestore client"""
        if self._db is None:
            self._db = firestore.client()
        return self._db
    
    def _get_cache_key(self, user_id: str) -> str:
        """Generate Redis cache key for dashboard"""
        return f"expense:extreme_dashboard:{user_id}"
    
    def get_dashboard_from_cache(self, user_id: str) -> Optional[Dict]:
        """
        Get dashboard from Redis cache only (0 Firestore reads).
        
        Used by mutation endpoints to validate data without reading Firestore.
        
        Args:
            user_id: User ID
            
        Returns:
            Dashboard data if cached, None otherwise
        """
        if not self._cache or not self._cache.is_available():
            return None
        
        cache_key = self._get_cache_key(user_id)
        cached = self._cache.get(cache_key)
        
        if cached:
            logger.debug("[EXTREME][CACHE] Dashboard retrieved from cache for user %s", user_id)
            return cached
        
        return None
    
    # =========================================================================
    # PHASE 21.1: Dashboard Document Schema & Operations
    # =========================================================================
    
    def get_extreme_dashboard(
        self,
        user_id: str,
        user_email: str = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get user's complete dashboard in a SINGLE Firestore read.
        
        This is THE core optimization - one document contains everything:
        - All groups with members, balances, expenses, settlements
        - All pending invitations
        - Global statistics
        
        Args:
            user_id: User ID
            user_email: User email (for invitation lookup)
            force_refresh: Skip cache and read from Firestore
            
        Returns:
            Complete dashboard with structure:
            {
                "success": true,
                "data": {
                    "user": {...},
                    "groups": {...},
                    "pending_invitations": [...],
                    "summary": {...}
                },
                "meta": {
                    "source": "cache" | "firestore",
                    "cached_at": "...",
                    "read_count": 1
                }
            }
        """
        start_time = datetime.utcnow()
        cache_key = self._get_cache_key(user_id)
        
        # Check Redis cache first (0 Firestore reads)
        if not force_refresh and self._cache and self._cache.is_available():
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.info("[EXTREME][CACHE][+] Dashboard cache hit for user %s", user_id)
                return {
                    'success': True,
                    'data': cached,
                    'meta': {
                        'source': 'cache',
                        'cached_at': cached.get('_cached_at'),
                        'read_count': 0
                    }
                }
        
        # Cache miss - single Firestore read
        logger.info("[EXTREME][CACHE][-] Dashboard cache miss for user %s, reading from Firestore", user_id)
        
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
        dashboard_doc = dashboard_ref.get()
        record_read(1, firestore_collections.USER_DASHBOARDS)
        
        if dashboard_doc.exists:
            dashboard_data = dashboard_doc.to_dict()
            group_count = len(dashboard_data.get('groups', {})) if dashboard_data else 0
            logger.info("[EXTREME] Loaded existing dashboard with %d groups for user %s", group_count, user_id)
            
            # If force_refresh OR dashboard is empty, rebuild it
            if force_refresh or group_count == 0:
                logger.info("[EXTREME] Rebuilding dashboard (force_refresh=%s, empty=%s) for user %s", 
                          force_refresh, group_count == 0, user_id)
                dashboard_data = self._build_dashboard_from_existing_data(user_id, user_email)
                if dashboard_data:
                    group_count = len(dashboard_data.get('groups', {}))
                    logger.info("[EXTREME] Rebuilt dashboard with %d groups for user %s", group_count, user_id)
                    dashboard_ref.set(dashboard_data)
                    record_write(1, firestore_collections.USER_DASHBOARDS)
        else:
            # First time user - build dashboard from existing data
            logger.info("[EXTREME] Building initial dashboard for user %s", user_id)
            dashboard_data = self._build_dashboard_from_existing_data(user_id, user_email)
            
            # Save the built dashboard
            if dashboard_data:
                group_count = len(dashboard_data.get('groups', {}))
                logger.info("[EXTREME] Saving new dashboard with %d groups for user %s", group_count, user_id)
                dashboard_ref.set(dashboard_data)
                record_write(1, firestore_collections.USER_DASHBOARDS)
        
        # Cache the result
        if dashboard_data and self._cache and self._cache.is_available():
            dashboard_data['_cached_at'] = datetime.utcnow().isoformat()
            self._cache.set(cache_key, dashboard_data, ttl=self.CACHE_TTL)
            logger.info("[EXTREME][CACHE][S] Dashboard cached for user %s (TTL=%ds)", user_id, self.CACHE_TTL)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("[EXTREME] Dashboard loaded for user %s in %.2fms", user_id, duration_ms)
        
        return {
            'success': True,
            'data': dashboard_data or self._empty_dashboard(user_id),
            'meta': {
                'source': 'firestore',
                'fetch_time_ms': duration_ms,
                'read_count': 1
            }
        }
    
    def _empty_dashboard(self, user_id: str) -> Dict:
        """Create empty dashboard structure"""
        return {
            'user_id': user_id,
            'updated_at': datetime.utcnow().isoformat(),
            'groups': {},
            'pending_invitations': [],
            'summary': {
                'total_owed_to_you': 0.0,
                'total_you_owe': 0.0,
                'net_balance': 0.0,
                'group_count': 0,
                'active_group_count': 0
            }
        }
    
    def _build_dashboard_from_existing_data(
        self,
        user_id: str,
        user_email: str = None
    ) -> Dict:
        """
        Build dashboard document from existing collections.
        
        This is called on first login for existing users.
        Reads from multiple collections but only happens ONCE per user.
        
        Args:
            user_id: User ID
            user_email: User email for invitation lookup
            
        Returns:
            Complete dashboard document
        """
        dashboard = self._empty_dashboard(user_id)
        
        try:
            # Fetch user's groups
            members_ref = self.db.collection(firestore_collections.GROUP_MEMBERS)
            member_query = members_ref.where(filter=FieldFilter('user_id', '==', user_id))
            member_docs = list(member_query.where(filter=FieldFilter('is_active', '==', True)).stream())
            record_read(max(1, len(member_docs)), firestore_collections.GROUP_MEMBERS)
            
            logger.info("[EXTREME] Found %d active memberships for user %s", len(member_docs), user_id)
            
            group_ids = [doc.to_dict().get('group_id') for doc in member_docs]
            
            if group_ids:
                # Batch fetch groups
                group_refs = [self.db.collection('expense_groups').document(gid) for gid in group_ids]
                group_docs = self.db.get_all(group_refs)
                record_read(1, 'expense_groups')  # Batch read = 1 op
                
                # Batch fetch balances
                balance_refs = [self.db.collection('expense_group_balances').document(gid) for gid in group_ids]
                balance_docs = self.db.get_all(balance_refs)
                record_read(1, 'expense_group_balances')
                
                # Build group map
                balance_map = {}
                for doc in balance_docs:
                    if doc.exists:
                        balance_map[doc.id] = doc.to_dict()
                
                total_owed = 0.0
                total_owes = 0.0
                
                for doc in group_docs:
                    if doc.exists:
                        group_data = doc.to_dict()
                        group_id = doc.id
                        balances = balance_map.get(group_id, {}).get('balances', {})
                        user_balance = float(balances.get(user_id, 0))
                        
                        if user_balance > 0:
                            total_owed += user_balance
                        else:
                            total_owes += abs(user_balance)
                        
                        # Get members for this group
                        group_members = []
                        for m_doc in member_docs:
                            m_data = m_doc.to_dict()
                            if m_data.get('group_id') == group_id:
                                group_members.append({
                                    'user_id': m_data.get('user_id'),
                                    'display_name': m_data.get('display_name', 'Unknown'),
                                    'role': m_data.get('role', 'member')
                                })
                        
                        # Fetch recent expenses for this group
                        recent_expenses = self._fetch_recent_expenses(group_id, limit=MAX_RECENT_EXPENSES)
                        
                        # Fetch recent settlements
                        recent_settlements = self._fetch_recent_settlements(group_id, limit=MAX_RECENT_SETTLEMENTS)
                        
                        dashboard['groups'][group_id] = {
                            'group_id': group_id,
                            'name': group_data.get('name', 'Unknown Group'),
                            'currency': group_data.get('currency', 'USD'),
                            'created_by': group_data.get('created_by'),
                            'created_at': group_data.get('created_at'),
                            'member_count': len(group_members),
                            'your_balance': user_balance,
                            'total_spent': group_data.get('total_spent', 0),
                            'expense_count': group_data.get('expense_count', 0),
                            'is_settled': abs(user_balance) < 0.01,
                            'members': group_members,
                            'balances': balances,
                            'recent_expenses': recent_expenses,
                            'recent_settlements': recent_settlements
                        }
                
                dashboard['summary']['total_owed_to_you'] = total_owed
                dashboard['summary']['total_you_owe'] = total_owes
                dashboard['summary']['net_balance'] = total_owed - total_owes
                dashboard['summary']['group_count'] = len(group_ids)
                dashboard['summary']['active_group_count'] = len([g for g in dashboard['groups'].values() if not g['is_settled']])
                
                logger.info("[EXTREME] Built dashboard with %d groups for user %s", len(dashboard['groups']), user_id)
            
            # Fetch pending invitations
            if user_email:
                invitations = self._fetch_pending_invitations(user_email)
                dashboard['pending_invitations'] = invitations
            
        except Exception as e:
            logger.error("[EXTREME] Error building dashboard for user %s: %s", user_id, e)
        
        return dashboard
    
    def _fetch_recent_expenses(self, group_id: str, limit: int = 20) -> List[Dict]:
        """Fetch recent expenses for a group"""
        try:
            expenses_ref = self.db.collection('expense_expenses')
            query = (expenses_ref
                    .where(filter=FieldFilter('group_id', '==', group_id))
                    .where(filter=FieldFilter('is_deleted', '==', False))
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = list(query.stream())
            record_read(max(1, len(docs)), 'expense_expenses')
            
            return [self._expense_to_summary(doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.warning("Error fetching recent expenses for group %s: %s", group_id, e)
            return []
    
    def _fetch_recent_settlements(self, group_id: str, limit: int = 10) -> List[Dict]:
        """Fetch recent settlements for a group"""
        try:
            settlements_ref = self.db.collection('expense_settlements')
            query = (settlements_ref
                    .where(filter=FieldFilter('group_id', '==', group_id))
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = list(query.stream())
            record_read(max(1, len(docs)), 'expense_settlements')
            
            return [self._settlement_to_summary(doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.warning("Error fetching recent settlements for group %s: %s", group_id, e)
            return []
    
    def _fetch_pending_invitations(self, user_email: str) -> List[Dict]:
        """Fetch pending invitations for a user"""
        try:
            invitations_ref = self.db.collection('expense_invitations')
            query = (invitations_ref
                    .where(filter=FieldFilter('invitee_email', '==', user_email.lower()))
                    .where(filter=FieldFilter('status', '==', 'pending')))
            
            docs = list(query.stream())
            record_read(max(1, len(docs)), 'expense_invitations')
            
            return [self._invitation_to_summary(doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.warning("Error fetching invitations for %s: %s", user_email, e)
            return []
    
    def _expense_to_summary(self, expense: Dict) -> Dict:
        """Convert expense to summary for dashboard embedding"""
        return {
            'expense_id': expense.get('expense_id'),
            'description': expense.get('description'),
            'amount': float(expense.get('amount', 0)),
            'currency': expense.get('currency', 'USD'),
            'paid_by': expense.get('paid_by'),
            'paid_by_name': expense.get('paid_by_name'),
            'split_type': expense.get('split_type'),
            'category': expense.get('category'),
            'expense_date': expense.get('expense_date'),
            'created_at': expense.get('created_at'),
            'is_edited': expense.get('is_edited', False)
        }
    
    def _settlement_to_summary(self, settlement: Dict) -> Dict:
        """Convert settlement to summary for dashboard embedding"""
        return {
            'settlement_id': settlement.get('settlement_id'),
            'from_user_id': settlement.get('from_user_id'),
            'to_user_id': settlement.get('to_user_id'),
            'amount': float(settlement.get('amount', 0)),
            'currency': settlement.get('currency', 'USD'),
            'status': settlement.get('status'),
            'created_at': settlement.get('created_at')
        }
    
    def _invitation_to_summary(self, invitation: Dict) -> Dict:
        """Convert invitation to summary for dashboard embedding"""
        return {
            'invitation_id': invitation.get('invitation_id'),
            'group_id': invitation.get('group_id'),
            'group_name': invitation.get('group_name'),
            'invited_by': invitation.get('invited_by'),
            'inviter_name': invitation.get('inviter_name'),
            'inviter_email': invitation.get('inviter_email'),
            'token': invitation.get('token'),  # JWT token for zero-read accept
            'created_at': invitation.get('created_at'),
            'expires_at': invitation.get('expires_at')
        }
    
    def rebuild_user_dashboard(
        self,
        user_id: str,
        user_email: str = None
    ) -> Dict:
        """
        Rebuild user dashboard from source collections.
        
        Public API for:
        - Initializing dashboards for existing users
        - Repairing corrupted dashboard data
        - Force-syncing with source collections
        
        Args:
            user_id: User ID
            user_email: User email for invitation lookup
            
        Returns:
            Rebuilt dashboard data
        """
        logger.info("[EXTREME] Rebuilding dashboard for user %s", user_id)
        
        # Build fresh dashboard from source
        dashboard = self._build_dashboard_from_existing_data(user_id, user_email)
        dashboard['updated_at'] = datetime.utcnow().isoformat()
        dashboard['_rebuilt_at'] = datetime.utcnow().isoformat()
        
        # Save to Firestore
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
        dashboard_ref.set(dashboard)
        record_write(1, firestore_collections.USER_DASHBOARDS)
        
        # Refresh cache
        if self._cache and self._cache.is_available():
            cache_key = self._get_cache_key(user_id)
            dashboard['_cached_at'] = datetime.utcnow().isoformat()
            self._cache.set(cache_key, dashboard, ttl=self.CACHE_TTL)
            logger.info("[EXTREME][CACHE][S] Rebuilt dashboard cached for user %s", user_id)
        
        return dashboard
    
    # =========================================================================
    # PHASE 21.2: Dashboard Update Operations (Write-Through)
    # =========================================================================
    
    def invalidate_dashboard_cache(self, user_id: str) -> bool:
        """
        Invalidate dashboard cache for a user.
        Called after mutations to ensure fresh data on next read.
        
        Args:
            user_id: User ID
            
        Returns:
            True if cache was invalidated
        """
        if self._cache and self._cache.is_available():
            cache_key = self._get_cache_key(user_id)
            self._cache.delete(cache_key)
            logger.debug("[EXTREME][CACHE][X] Dashboard cache invalidated for user %s", user_id)
            return True
        return False
    
    def update_dashboard_write_through(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update dashboard using write-through pattern.
        
        1. Update Firestore
        2. Update Redis cache immediately (no re-read)
        
        Args:
            user_id: User ID
            updates: Field updates to apply
            
        Returns:
            True if successful
        """
        try:
            # Update Firestore
            dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
            updates['updated_at'] = datetime.utcnow().isoformat()
            dashboard_ref.update(updates)
            record_write(1, firestore_collections.USER_DASHBOARDS)
            
            # Update cache (write-through)
            if self._cache and self._cache.is_available():
                cache_key = self._get_cache_key(user_id)
                cached = self._cache.get(cache_key)
                if cached:
                    # Apply updates to cached data
                    for key, value in updates.items():
                        if '.' in key:
                            # Handle nested keys like "groups.group_id.balances"
                            self._set_nested_value(cached, key, value)
                        else:
                            cached[key] = value
                    cached['_cached_at'] = datetime.utcnow().isoformat()
                    self._cache.set(cache_key, cached, ttl=self.CACHE_TTL)
                    logger.debug("[EXTREME][CACHE][W] Write-through update for user %s", user_id)
            
            return True
        except Exception as e:
            logger.error("[EXTREME] Write-through update failed for user %s: %s", user_id, e)
            # Invalidate cache on failure
            self.invalidate_dashboard_cache(user_id)
            return False
    
    def _set_nested_value(self, data: Dict, key: str, value: Any) -> None:
        """Set a nested value in a dictionary using dot notation"""
        keys = key.split('.')
        current = data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    # =========================================================================
    # PHASE 21: Batch Update All Affected Users
    # =========================================================================
    
    def batch_update_dashboards(
        self,
        user_updates: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Batch update multiple user dashboards in a single write operation.
        
        This is key to the 1-write-per-mutation pattern.
        
        Args:
            user_updates: Map of user_id -> updates
            
        Returns:
            Number of dashboards updated
        """
        if not user_updates:
            return 0
        
        try:
            batch = self.db.batch()
            now = datetime.utcnow().isoformat()
            
            for user_id, updates in user_updates.items():
                dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
                updates['updated_at'] = now
                batch.update(dashboard_ref, updates)
            
            batch.commit()
            record_write(1, firestore_collections.USER_DASHBOARDS)  # Batch = 1 write
            
            # Invalidate all affected caches
            for user_id in user_updates.keys():
                self.invalidate_dashboard_cache(user_id)
            
            logger.info("[EXTREME] Batch updated %d dashboards", len(user_updates))
            return len(user_updates)
            
        except Exception as e:
            logger.error("[EXTREME] Batch dashboard update failed: %s", e)
            return 0
    
    # =========================================================================
    # Document Size Monitoring
    # =========================================================================
    
    def get_dashboard_size(self, user_id: str) -> int:
        """
        Get approximate size of dashboard document in bytes.
        Firestore limit is 1MB (1,048,576 bytes).
        
        Args:
            user_id: User ID
            
        Returns:
            Approximate size in bytes
        """
        try:
            dashboard = self.get_extreme_dashboard(user_id)
            if dashboard and dashboard.get('data'):
                return len(json.dumps(dashboard['data']).encode('utf-8'))
            return 0
        except Exception as e:
            logger.warning("Error calculating dashboard size for %s: %s", user_id, e)
            return 0
    
    def check_document_size_limit(self, user_id: str, warn_threshold: float = 0.8) -> Dict:
        """
        Check if dashboard is approaching size limit.
        
        Args:
            user_id: User ID
            warn_threshold: Percentage of limit to warn at (default 80%)
            
        Returns:
            {
                "size_bytes": 123456,
                "limit_bytes": 1048576,
                "percentage": 11.7,
                "warning": False
            }
        """
        size = self.get_dashboard_size(user_id)
        limit = 1048576  # 1MB
        percentage = (size / limit) * 100
        
        result = {
            'size_bytes': size,
            'limit_bytes': limit,
            'percentage': round(percentage, 2),
            'warning': percentage >= (warn_threshold * 100)
        }
        
        if result['warning']:
            logger.warning(
                "[EXTREME] Dashboard size warning for user %s: %.1f%% of limit (%d bytes)",
                user_id, percentage, size
            )
        
        return result


# Singleton instance
_extreme_dashboard_service = None


def get_extreme_dashboard_service() -> ExtremeDashboardService:
    """Get singleton instance of ExtremeDashboardService"""
    global _extreme_dashboard_service
    if _extreme_dashboard_service is None:
        _extreme_dashboard_service = ExtremeDashboardService()
    return _extreme_dashboard_service
