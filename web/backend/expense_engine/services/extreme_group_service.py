"""
Extreme Group Service - Phase 21.3 Zero-Read Mutations
=======================================================

This service implements zero-read group operations for the 10-operation architecture.
Every operation uses a single batch write and updates all affected dashboards.

Key principles:
1. NO Firestore reads during mutations (validate from Redis cache)
2. Single batch write per operation
3. Update ALL affected users' dashboard documents
4. Write-through cache (no re-reads needed)
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from ..config import firestore_collections

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


class ExtremeGroupService:
    """
    Phase 21.3: Zero-read group operations.
    
    All operations:
    1. Validate using Redis cache (0 Firestore reads)
    2. Execute single batch write
    3. Update all affected dashboards
    4. Update Redis cache (write-through)
    5. Return computed response (no re-read)
    """
    
    def __init__(self):
        self._cache = get_cache_manager() if CACHE_ENABLED else None
        self._db = None
    
    @property
    def db(self):
        """Lazy-load Firestore client"""
        if self._db is None:
            self._db = firestore.client()
        return self._db
    
    def _get_dashboard_cache_key(self, user_id: str) -> str:
        """Generate Redis cache key for dashboard"""
        return f"expense:extreme_dashboard:{user_id}"
    
    def _get_membership_cache_key(self, group_id: str, user_id: str) -> str:
        """Generate Redis cache key for membership check"""
        return f"expense:membership:{group_id}:{user_id}"
    
    # =========================================================================
    # CREATE GROUP - 1 Batch Write
    # =========================================================================
    
    def create_group_extreme(
        self,
        user_id: str,
        name: str,
        currency: str = "USD",
        description: str = "",
        dashboard_cache: Dict = None,
        user_email: str = None,
        user_display_name: str = None
    ) -> Dict[str, Any]:
        """
        Create a new expense group with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (user validated by JWT)
        - 1 Batch write:
            - expense_groups/{new_id}
            - expense_group_members/{group_id}_{user_id}
            - expense_group_balances/{group_id}
            - expense_user_dashboards/{user_id}
        
        Args:
            user_id: Creator's user ID (from JWT)
            name: Group name
            currency: Currency code (default USD)
            description: Optional group description
            dashboard_cache: User's dashboard from cache (optional, for user info)
            user_email: Creator's email (optional, can extract from dashboard)
            user_display_name: Creator's display name (optional)
            
        Returns:
            Created group data with member and balance info
        """
        start_time = datetime.utcnow()
        
        # Extract user info from dashboard cache if not provided
        if dashboard_cache:
            if not user_email:
                user_email = dashboard_cache.get('user_email', '')
            if not user_display_name:
                user_display_name = dashboard_cache.get('user_display_name', '')
        
        # Fallback for email
        if not user_email:
            user_email = f"user_{user_id[:8]}@app.local"
        
        # Determine display name with fallbacks
        if not user_display_name:
            user_display_name = user_email.split('@')[0] if user_email else 'Unknown'
        
        # Generate IDs
        group_id = f"grp_{uuid.uuid4().hex[:12]}"
        member_id = f"{group_id}_{user_id}"
        
        # Prepare group data
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        group_data = {
            'group_id': group_id,
            'name': name,
            'description': description or '',
            'currency': currency,
            'created_by': user_id,
            'created_at': now_iso,
            'updated_at': now_iso,
            'total_spent': 0.0,
            'expense_count': 0,
            'is_deleted': False,
            'settings': {
                'simplify_debts': True,
                'default_split': 'equal'
            }
        }
        
        # Prepare member data
        member_data = {
            'member_id': member_id,
            'group_id': group_id,
            'user_id': user_id,
            'email': user_email,
            'display_name': user_display_name,
            'role': 'owner',
            'joined_at': now_iso,
            'is_active': True,
            'balance': 0.0
        }
        
        # Prepare balance data
        balance_data = {
            'group_id': group_id,
            'balances': {user_id: 0.0},
            'updated_at': now_iso
        }
        
        # Prepare dashboard update for creator
        dashboard_group_data = {
            'group_id': group_id,
            'name': name,
            'currency': currency,
            'created_by': user_id,
            'created_at': now_iso,
            'member_count': 1,
            'your_balance': 0.0,
            'total_spent': 0.0,
            'expense_count': 0,
            'is_settled': True,
            'members': [member_data],
            'balances': {user_id: 0.0},
            'recent_expenses': [],
            'recent_settlements': []
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Write group
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.set(group_ref, group_data)
        
        # Write member
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(member_id)
        batch.set(member_ref, member_data)
        
        # Write balance
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.set(balance_ref, balance_data)
        
        # Update user's dashboard
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
        batch.set(dashboard_ref, {
            'user_id': user_id,
            'updated_at': now_iso,
            f'groups.{group_id}': dashboard_group_data,
            'summary.group_count': firestore.Increment(1)
        }, merge=True)
        
        # Commit batch - SINGLE WRITE OPERATION
        batch.commit()
        record_write(1, 'batch_create_group')
        
        logger.info("[EXTREME] Group created: %s (1 batch write)", group_id)
        
        # Update Redis cache (write-through)
        self._update_cache_after_group_create(user_id, group_id, dashboard_group_data)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'group': group_data,
            'member': member_data,
            'balance': balance_data,
            'meta': {
                'operation': 'create_group',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    def _update_cache_after_group_create(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict
    ) -> None:
        """Update Redis cache after group creation"""
        if not self._cache or not self._cache.is_available():
            return
        
        cache_key = self._get_dashboard_cache_key(user_id)
        cached = self._cache.get(cache_key)
        
        if cached:
            # Update existing cache
            if 'groups' not in cached:
                cached['groups'] = {}
            cached['groups'][group_id] = group_data
            cached['summary'] = cached.get('summary', {})
            cached['summary']['group_count'] = len(cached['groups'])
            cached['updated_at'] = datetime.utcnow().isoformat()
            
            self._cache.set(cache_key, cached, ttl=3600)
            logger.debug("[EXTREME][CACHE] Updated cache after group create")
        else:
            # Cache miss - will be refreshed on next dashboard read
            logger.debug("[EXTREME][CACHE] No cache to update for group create")
    
    # =========================================================================
    # SEND INVITATION - 1 Batch Write
    # =========================================================================
    
    def send_invitation_extreme(
        self,
        group_id: str,
        invitee_email: str,
        invited_by: str,
        group_from_cache: Dict = None,
        role: str = "member"
    ) -> Dict[str, Any]:
        """
        Send an invitation to join a group with SINGLE batch write.
        
        This creates an invitation document that the invitee can accept.
        
        Operations:
        - 0 Firestore reads (group data from cache)
        - 1 Batch write:
            - expense_invitations/{new_id}
            - expense_user_dashboards/{invitee_user_id} (if user exists, add pending)
        
        Args:
            group_id: Group to invite to
            invitee_email: Email of person to invite
            invited_by: User ID who is inviting
            group_from_cache: Group data from dashboard cache
            role: Role to assign (default: member)
            
        Returns:
            Created invitation data
        """
        start_time = datetime.utcnow()
        
        # Normalize email
        invitee_email = invitee_email.strip().lower()
        
        # Generate invitation ID
        invitation_id = f"inv_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()
        
        # Get group name from cache
        group_name = group_from_cache.get('name', 'Unknown Group') if group_from_cache else 'Unknown Group'
        currency = group_from_cache.get('currency', 'USD') if group_from_cache else 'USD'
        
        # Calculate expiry (7 days)
        from datetime import timedelta
        expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        # Prepare invitation data
        invitation_data = {
            'invitation_id': invitation_id,
            'group_id': group_id,
            'group_name': group_name,
            'email': invitee_email,
            'invited_email': invitee_email,  # Duplicate for compatibility
            'invited_by': invited_by,
            'role': role,
            'status': 'pending',
            'created_at': now_iso,
            'expires_at': expires_at,
            'currency': currency
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Write invitation
        invitation_ref = self.db.collection(firestore_collections.INVITATIONS).document(invitation_id)
        batch.set(invitation_ref, invitation_data)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_send_invitation')
        
        logger.info("[EXTREME] Invitation sent: %s -> %s (1 batch write)", group_id, invitee_email)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'invitation': invitation_data,
            'meta': {
                'operation': 'send_invitation',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # ADD MEMBER - 1 Batch Write
    # =========================================================================
    
    def add_member_extreme(
        self,
        group_id: str,
        new_user_id: str,
        new_user_email: str,
        new_user_name: str,
        invited_by: str,
        role: str = "member",
        existing_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Add a member to a group with SINGLE batch write.
        
        This is called after invitation acceptance.
        The invitation service should provide existing_members from its cache.
        
        Operations:
        - 0 Firestore reads (data from invitation token + cache)
        - 1 Batch write:
            - expense_group_members/{group_id}_{user_id}
            - expense_group_balances/{group_id} (add new member)
            - expense_user_dashboards/{new_member} (add group)
            - expense_user_dashboards/{each_existing_member} (update member list)
        
        Args:
            group_id: Group to join
            new_user_id: New member's user ID
            new_user_email: New member's email
            new_user_name: New member's display name
            invited_by: User ID who sent invitation
            role: Member role (default: member)
            existing_members: List of existing members from cache
            
        Returns:
            Updated group data
        """
        start_time = datetime.utcnow()
        
        member_id = f"{group_id}_{new_user_id}"
        now_iso = datetime.utcnow().isoformat()
        
        # Prepare new member data
        new_member_data = {
            'member_id': member_id,
            'group_id': group_id,
            'user_id': new_user_id,
            'email': new_user_email,
            'display_name': new_user_name,
            'role': role,
            'joined_at': now_iso,
            'invited_by': invited_by,
            'is_active': True,
            'balance': 0.0
        }
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Write new member
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(member_id)
        batch.set(member_ref, new_member_data)
        
        # Update balance document (add new member with 0 balance)
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            f'balances.{new_user_id}': 0.0,
            'updated_at': now_iso
        })
        
        # Update new member's dashboard
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(new_user_id)
        batch.set(dashboard_ref, {
            'user_id': new_user_id,
            'updated_at': now_iso,
            'summary.group_count': firestore.Increment(1)
        }, merge=True)
        
        # Update each existing member's dashboard (add new member to their member list)
        if existing_members:
            for member in existing_members:
                member_user_id = member.get('user_id')
                if member_user_id and member_user_id != new_user_id:
                    member_dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.set(member_dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.member_count': firestore.Increment(1)
                    }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_add_member')
        
        logger.info("[EXTREME] Member added to group %s: %s (1 batch write)", group_id, new_user_id)
        
        # Invalidate affected caches
        self._invalidate_member_caches(group_id, existing_members or [], new_user_id)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'member': new_member_data,
            'meta': {
                'operation': 'add_member',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    def _invalidate_member_caches(
        self,
        group_id: str,
        existing_members: List[Dict],
        new_member_id: str
    ) -> None:
        """Invalidate dashboard caches for all affected members"""
        if not self._cache or not self._cache.is_available():
            return
        
        # Invalidate new member's cache
        cache_key = self._get_dashboard_cache_key(new_member_id)
        self._cache.delete(cache_key)
        
        # Invalidate existing members' caches
        for member in existing_members:
            member_user_id = member.get('user_id')
            if member_user_id:
                cache_key = self._get_dashboard_cache_key(member_user_id)
                self._cache.delete(cache_key)
        
        logger.debug("[EXTREME][CACHE] Invalidated caches for group %s members", group_id)
    
    # =========================================================================
    # REMOVE MEMBER - 1 Batch Write
    # =========================================================================
    
    def remove_member_extreme(
        self,
        group_id: str,
        user_id_to_remove: str,
        removed_by: str,
        existing_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Remove a member from a group with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads
        - 1 Batch write:
            - expense_group_members/{group_id}_{user_id} (set is_active=False)
            - expense_user_dashboards/{removed_user} (remove group)
            - expense_user_dashboards/{each_remaining_member} (update member count)
        
        Args:
            group_id: Group to leave
            user_id_to_remove: User ID being removed
            removed_by: User ID who initiated removal
            existing_members: List of existing members from cache
            
        Returns:
            Removal confirmation
        """
        start_time = datetime.utcnow()
        
        member_id = f"{group_id}_{user_id_to_remove}"
        now_iso = datetime.utcnow().isoformat()
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Soft delete member
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(member_id)
        batch.update(member_ref, {
            'is_active': False,
            'left_at': now_iso,
            'removed_by': removed_by
        })
        
        # Remove group from removed user's dashboard
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id_to_remove)
        batch.update(dashboard_ref, {
            f'groups.{group_id}': firestore.DELETE_FIELD,
            'updated_at': now_iso,
            'summary.group_count': firestore.Increment(-1)
        })
        
        # Update remaining members' dashboards
        if existing_members:
            for member in existing_members:
                member_user_id = member.get('user_id')
                if member_user_id and member_user_id != user_id_to_remove:
                    member_dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.update(member_dashboard_ref, {
                        'updated_at': now_iso,
                        f'groups.{group_id}.member_count': firestore.Increment(-1)
                    })
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_remove_member')
        
        logger.info("[EXTREME] Member removed from group %s: %s (1 batch write)", group_id, user_id_to_remove)
        
        # Invalidate caches
        self._invalidate_member_caches(group_id, existing_members or [], user_id_to_remove)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'removed_user_id': user_id_to_remove,
            'meta': {
                'operation': 'remove_member',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # UPDATE GROUP - 1 Batch Write
    # =========================================================================
    
    def update_group_extreme(
        self,
        group_id: str,
        updates: Dict[str, Any],
        group_data_from_cache: Dict = None,
        requester_id: str = None
    ) -> Dict[str, Any]:
        """
        Update group details with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (validate from cache)
        - 1 Batch write:
            - expense_groups/{group_id}
            - expense_user_dashboards/{each_member}
        """
        start_time = datetime.utcnow()
        now_iso = datetime.utcnow().isoformat()
        
        # Build update data
        update_data = {
            'updated_at': now_iso
        }
        if 'name' in updates:
            update_data['name'] = updates['name']
        if 'description' in updates:
            update_data['description'] = updates['description']
        if 'currency' in updates:
            update_data['currency'] = updates['currency']
        if 'settings' in updates:
            update_data['settings'] = updates['settings']
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Update group document
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, update_data)
        
        # Update all members' dashboards
        members = group_data_from_cache.get('members', []) if group_data_from_cache else []
        for member in members:
            member_user_id = member.get('user_id')
            if member_user_id:
                dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                dashboard_updates = {'updated_at': now_iso}
                if 'name' in updates:
                    dashboard_updates[f'groups.{group_id}.name'] = updates['name']
                if 'currency' in updates:
                    dashboard_updates[f'groups.{group_id}.currency'] = updates['currency']
                batch.update(dashboard_ref, dashboard_updates)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_update_group')
        
        logger.info("[EXTREME] Group updated: %s (1 batch write)", group_id)
        
        # Invalidate caches
        for member in members:
            member_user_id = member.get('user_id')
            if member_user_id and self._cache:
                cache_key = self._get_dashboard_cache_key(member_user_id)
                self._cache.delete(cache_key)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'group_id': group_id,
            **update_data,
            'meta': {
                'operation': 'update_group',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # ACCEPT INVITATION - 1 Batch Write
    # =========================================================================
    
    def accept_invitation_extreme(
        self,
        invitation_id: str,
        user_id: str,
        invitation_from_cache: Dict = None,
        user_dashboard: Dict = None
    ) -> Dict[str, Any]:
        """
        Accept an invitation with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (validate from cache)
        - 1 Batch write:
            - expense_invitations/{invitation_id} (update status)
            - expense_group_members/{group_id}_{user_id} (create)
            - expense_group_balances/{group_id} (add user)
            - expense_user_dashboards/{user_id} (add group)
        """
        start_time = datetime.utcnow()
        now_iso = datetime.utcnow().isoformat()
        
        if not invitation_from_cache:
            raise ValueError("Invitation data required from cache")
        
        group_id = invitation_from_cache.get('group_id')
        user_email = invitation_from_cache.get('email') or invitation_from_cache.get('invited_email')
        
        # Generate member ID
        member_id = f"{group_id}_{user_id}"
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # 1. Update invitation status
        invitation_ref = self.db.collection(firestore_collections.INVITATIONS).document(invitation_id)
        batch.update(invitation_ref, {
            'status': 'accepted',
            'accepted_at': now_iso,
            'accepted_by_user_id': user_id
        })
        
        # 2. Create group member
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(member_id)
        member_data = {
            'member_id': member_id,
            'group_id': group_id,
            'user_id': user_id,
            'email': user_email,
            'display_name': user_email.split('@')[0] if user_email else 'Unknown',
            'role': 'member',
            'joined_at': now_iso,
            'is_active': True,
            'balance': 0.0
        }
        batch.set(member_ref, member_data)
        
        # 3. Add user to group balances
        balance_ref = self.db.collection(firestore_collections.GROUP_BALANCES).document(group_id)
        batch.update(balance_ref, {
            f'balances.{user_id}': 0.0,
            'updated_at': now_iso
        })
        
        # 4. Add group to user's dashboard
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
        group_info = {
            'group_id': group_id,
            'name': invitation_from_cache.get('group_name', 'Unknown Group'),
            'currency': invitation_from_cache.get('currency', 'USD'),
            'your_balance': 0.0,
            'member_count': 1,
            'is_settled': True,
            'members': [member_data],
            'balances': {user_id: 0.0},
            'recent_expenses': [],
            'recent_settlements': []
        }
        batch.set(dashboard_ref, {
            f'groups.{group_id}': group_info,
            'updated_at': now_iso,
            'pending_invitations': firestore.ArrayRemove([invitation_from_cache])
        }, merge=True)
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_accept_invitation')
        
        logger.info("[EXTREME] Invitation accepted: %s -> group %s (1 batch write)", invitation_id, group_id)
        
        # Invalidate cache
        if self._cache:
            cache_key = self._get_dashboard_cache_key(user_id)
            self._cache.delete(cache_key)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'group_id': group_id,
            'member': member_data,
            'meta': {
                'operation': 'accept_invitation',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # DECLINE INVITATION - 1 Batch Write
    # =========================================================================
    
    def decline_invitation_extreme(
        self,
        invitation_id: str,
        user_id: str,
        invitation_from_cache: Dict = None
    ) -> Dict[str, Any]:
        """
        Decline an invitation with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads (validate from cache)
        - 1 Batch write:
            - expense_invitations/{invitation_id} (update status)
            - expense_user_dashboards/{user_id} (remove from pending)
        """
        start_time = datetime.utcnow()
        now_iso = datetime.utcnow().isoformat()
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # 1. Update invitation status
        invitation_ref = self.db.collection(firestore_collections.INVITATIONS).document(invitation_id)
        batch.update(invitation_ref, {
            'status': 'declined',
            'declined_at': now_iso
        })
        
        # 2. Remove from user's pending invitations
        dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(user_id)
        batch.update(dashboard_ref, {
            'pending_invitations': firestore.ArrayRemove([invitation_from_cache]) if invitation_from_cache else [],
            'updated_at': now_iso
        })
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_decline_invitation')
        
        logger.info("[EXTREME] Invitation declined: %s (1 batch write)", invitation_id)
        
        # Invalidate cache
        if self._cache:
            cache_key = self._get_dashboard_cache_key(user_id)
            self._cache.delete(cache_key)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'declined_invitation_id': invitation_id,
            'meta': {
                'operation': 'decline_invitation',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }
    
    # =========================================================================
    # DELETE GROUP - 1 Batch Write
    # =========================================================================
    
    def delete_group_extreme(
        self,
        group_id: str,
        deleted_by: str,
        existing_members: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Soft-delete a group with SINGLE batch write.
        
        Operations:
        - 0 Firestore reads
        - 1 Batch write:
            - expense_groups/{group_id} (set is_deleted=True)
            - expense_user_dashboards/{each_member} (remove group)
        
        Args:
            group_id: Group to delete
            deleted_by: User ID who initiated deletion
            existing_members: List of members from cache
            
        Returns:
            Deletion confirmation
        """
        start_time = datetime.utcnow()
        now_iso = datetime.utcnow().isoformat()
        
        # SINGLE BATCH WRITE
        batch = self.db.batch()
        
        # Soft delete group
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'is_deleted': True,
            'deleted_at': now_iso,
            'deleted_by': deleted_by
        })
        
        # Remove from all members' dashboards
        if existing_members:
            for member in existing_members:
                member_user_id = member.get('user_id')
                if member_user_id:
                    dashboard_ref = self.db.collection(firestore_collections.USER_DASHBOARDS).document(member_user_id)
                    batch.update(dashboard_ref, {
                        f'groups.{group_id}': firestore.DELETE_FIELD,
                        'updated_at': now_iso,
                        'summary.group_count': firestore.Increment(-1)
                    })
        
        # Commit batch
        batch.commit()
        record_write(1, 'batch_delete_group')
        
        logger.info("[EXTREME] Group deleted: %s (1 batch write)", group_id)
        
        # Invalidate all member caches
        if existing_members:
            for member in existing_members:
                member_user_id = member.get('user_id')
                if member_user_id and self._cache:
                    cache_key = self._get_dashboard_cache_key(member_user_id)
                    self._cache.delete(cache_key)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'success': True,
            'deleted_group_id': group_id,
            'meta': {
                'operation': 'delete_group',
                'read_count': 0,
                'write_count': 1,
                'duration_ms': duration_ms
            }
        }


# Singleton instance
_extreme_group_service = None

def get_extreme_group_service() -> ExtremeGroupService:
    """Get singleton instance of ExtremeGroupService"""
    global _extreme_group_service
    if _extreme_group_service is None:
        _extreme_group_service = ExtremeGroupService()
    return _extreme_group_service
