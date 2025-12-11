"""
Group Service
Business logic for group management
"""

from typing import List, Dict, Optional
from datetime import datetime
import secrets
import string
import logging

from ..repositories import GroupRepository, BalanceRepository
from ..models.group import Group, GroupSettings
from ..config import business_rules, redis_config
from ..exceptions import (
    ValidationError,
    ResourceNotFoundError,
    MaxMembersReachedError,
    DuplicateEntryError
)

# Import Firestore counter for direct operations
try:
    from expense_engine.firestore_counter import record_read, record_write
    TRACKING_ENABLED = True
except ImportError:
    TRACKING_ENABLED = False
    def record_read(count=1, collection=None): pass
    def record_write(count=1, collection=None): pass

# Import cache decorator
try:
    from ..utils.cache_decorator import cached
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def cached(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


def _invalidate_membership_cache(group_id: str, user_id: str, group_repo=None):
    """
    Invalidate cache entries when membership changes.
    Phase 17.9: Only invalidate the ACTING user's cache (not other members).
    Other members receive updates via Firestore real-time listeners.
    """
    if not CACHE_ENABLED:
        return
    try:
        cache = get_cache_manager()
        if cache and cache.is_available():
            # Invalidate membership check cache
            cache.delete(f"expense:membership:{group_id}:{user_id}")
            # Invalidate user's groups list
            cache.delete(redis_config.KEY_USER_GROUPS.format(uid=user_id))
            # Invalidate group summary
            cache.delete(redis_config.KEY_GROUP_SUMMARY.format(gid=group_id))
            # Invalidate group data
            cache.delete(f"expense:group:{group_id}")
            
            # Phase 17.9: Invalidate mega-bootstrap cache ONLY for the acting user
            # Both with and without group_id (dashboard vs group view)
            cache.delete(f"expense:mega_bootstrap:{user_id}")  # Dashboard
            cache.delete(f"expense:mega_bootstrap:{user_id}:{group_id}")  # Group view
            
            # Phase 17.9: DO NOT invalidate mega-bootstrap for other group members
            # They receive real-time updates via Firestore listeners:
            # - listenToGroupInvitations for invitation status
            # - listenToGroupExpenses for expense updates  
            # - listenToUserBalances for balance updates
            # This eliminates the API call cascade that caused 22 /user/groups calls
            
            logger.info(f"Cache invalidated for membership change: {group_id}/{user_id} (acting user only)")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


class GroupService:
    """
    Service for group management operations
    Handles group lifecycle, members, and settings
    """
    
    def __init__(self, group_repo: Optional[GroupRepository] = None, balance_repo: Optional[BalanceRepository] = None):
        """
        Initialize service
        
        Args:
            group_repo: Group repository (optional, will create if None)
            balance_repo: Balance repository (optional, will create if None)
        """
        # pylint: disable=no-value-for-parameter
        self.group_repo = group_repo or GroupRepository()
        self.balance_repo = balance_repo or BalanceRepository()
    
    def create_group(
        self,
        name: str,
        created_by: str,
        creator_display_name: str,
        description: Optional[str] = None,
        currency: str = 'USD'
    ) -> Dict:
        """
        Create a new group
        
        Args:
            name: Group name
            created_by: Creator user ID
            creator_display_name: Creator's display name
            description: Optional description
            currency: Currency code
            
        Returns:
            Created group document
        """
        try:
            # Generate unique group code
            group_code = self._generate_group_code()
            
            # Ensure code is unique
            existing = self.group_repo.get_group_by_code(group_code)
            if existing:
                # Regenerate if collision
                group_code = self._generate_group_code()
            
            # Create group model
            group = Group(
                name=name,
                description=description or '',
                created_by=created_by,
                group_code=group_code,
                currency=currency,
                members=[created_by],
                member_details={
                    created_by: {
                        'user_id': created_by,
                        'display_name': creator_display_name,
                        'role': 'admin',
                        'joined_at': datetime.utcnow(),
                        'is_active': True
                    }
                },
                settings=GroupSettings().to_dict()
            )
            
            # Generate document ID
            doc_ref = self.group_repo.get_collection().document()
            group_id = doc_ref.id
            
            # Set group_id in model (CRITICAL: must be in Firestore document)
            group.group_id = group_id
            
            # Convert to dict and add denormalized summary fields
            group_dict = group.to_dict()
            group_dict.update({
                'member_count': 1,
                'expense_count': 0,
                'total_spent': 0.0,
                'last_activity': datetime.utcnow().isoformat(),
                'is_settled': True
            })
            
            # Create group document
            self.group_repo.create(group_id, group_dict)
            
            # Create member document for Firestore listener
            from firebase_admin import firestore as admin_firestore
            member_ref = admin_firestore.client().collection('expense_group_members').document(f"{group_id}_{created_by}")
            member_ref.set({
                'group_id': group_id,
                'user_id': created_by,
                'display_name': creator_display_name,
                'role': 'admin',
                'is_active': True,
                'joined_at': datetime.utcnow()
            })
            record_write(1, 'expense_group_members')  # Track direct Firestore write
            
            # Initialize balance document
            self.balance_repo.initialize_group_balances(group_id)
            
            logger.info(
                "Created group %s by %s with code %s",
                group_id, created_by, group_code
            )
            
            # Return created group (includes group_id via repository normalization)
            group_data = self.group_repo.get_by_id(group_id)
            return group_data
            
        except Exception as exc:
            logger.error("Error creating group: %s", str(exc))
            raise
    
    def get_group(self, group_id: str) -> Dict:
        """
        Get group by ID with Redis caching (TTL=60s)
        
        Args:
            group_id: Group ID
            
        Returns:
            Group document
        """
        # Try cache first
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = f"expense:group:{group_id}"
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
        
        # Get from Firestore
        group_data = self.group_repo.get_by_id(group_id)
        if not group_data:
            raise ResourceNotFoundError(f"Group {group_id} not found")
        
        # Cache result
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, group_data, ttl=60)
        
        return group_data
    
    def get_user_groups(self, user_id: str) -> List[Dict]:
        """
        Get all groups a user is member of with Redis caching (TTL=60s)
        
        Args:
            user_id: User ID
            
        Returns:
            List of group documents
        """
        # Try cache first
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_USER_GROUPS.format(uid=user_id)
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
        
        # Get from Firestore
        groups = self.group_repo.get_user_groups(user_id)
        
        # Cache result
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, groups, ttl=redis_config.TTL_USER_GROUPS)
        
        return groups
    
    def get_group_members(self, group_id: str) -> List[Dict]:
        """
        Get all members of a group from expense_group_members collection
        Enriches with user data from users collection
        
        Args:
            group_id: Group ID
            
        Returns:
            List of member documents with user details
        """
        from firebase_admin import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
        db = firestore.client()
        
        # Query expense_group_members collection using FieldFilter (recommended pattern)
        members_ref = db.collection('expense_group_members')
        query = members_ref.where(filter=FieldFilter('group_id', '==', group_id)).where(filter=FieldFilter('is_active', '==', True))
        
        members = []
        member_docs = list(query.stream())
        record_read(max(1, len(member_docs)), 'expense_group_members')  # Track query reads
        
        for doc in member_docs:
            member_data = doc.to_dict()
            member_data['id'] = doc.id
            user_id = member_data.get('user_id')
            
            # Try to get user data from users collection
            user_data = None
            try:
                user_doc = db.collection('users').document(user_id).get()
                record_read(1, 'users')  # Track user lookup read
                if user_doc.exists:
                    user_data = user_doc.to_dict()
            except Exception as e:
                logger.warning(f"Failed to fetch user data for {user_id}: {e}")
            
            # Use user data if available, otherwise fallback to member_data
            if user_data:
                display_name = user_data.get('display_name') or user_data.get('email', '').split('@')[0]
                email = user_data.get('email', '')
                photo_url = user_data.get('photo_url')
            else:
                display_name = member_data.get('display_name', user_id)
                email = member_data.get('email', '')
                photo_url = None
            
            # Structure for frontend compatibility
            member = {
                'user_id': user_id,
                'display_name': display_name,
                'role': member_data.get('role', 'member'),
                'joined_at': member_data.get('joined_at'),
                'is_active': member_data.get('is_active', True),
                'user': {
                    'display_name': display_name,
                    'email': email,
                    'username': display_name,
                    'photo_url': photo_url
                }
            }
            members.append(member)
        
        logger.info(f"Found {len(members)} active members for group {group_id}")
        return members
    
    def get_all_members_for_history(self, group_id: str) -> Dict[str, Dict]:
        """
        Get ALL members (active + removed) for expense history display (Phase 15)
        Phase 20: Added Redis caching to prevent extra reads
        
        Uses cached_display_name for removed members so their names
        still appear correctly in past transactions.
        
        Args:
            group_id: Group ID
            
        Returns:
            Dict mapping user_id -> member info including display_name
        """
        from firebase_admin import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        # Phase 20: Check cache first
        cache_key = None
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = f"expense:all_members_history:{group_id}"
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug("[CACHE][+] All members history cache hit: %s", group_id)
                    return cached
        
        db = firestore.client()
        
        # Query ALL members (not just active) from expense_group_members
        members_ref = db.collection('expense_group_members')
        query = members_ref.where(filter=FieldFilter('group_id', '==', group_id))
        
        member_map = {}
        member_docs = list(query.stream())
        record_read(max(1, len(member_docs)), 'expense_group_members')
        
        # Collect user IDs that need user document lookup
        active_user_ids = []
        
        for doc in member_docs:
            member_data = doc.to_dict()
            user_id = member_data.get('user_id')
            is_active = member_data.get('is_active', True)
            
            # For removed members, use cached name
            if not is_active:
                display_name = (
                    member_data.get('cached_display_name') or
                    member_data.get('display_name') or
                    f'Former Member ({user_id[:8]})'
                )
                member_map[user_id] = {
                    'user_id': user_id,
                    'display_name': display_name,
                    'is_active': False,
                    'removed_at': member_data.get('removed_at'),
                    'role': member_data.get('role', 'member')
                }
            else:
                # Store member data, will fetch user info below
                active_user_ids.append(user_id)
                member_map[user_id] = {
                    'user_id': user_id,
                    'display_name': member_data.get('display_name', user_id),
                    'is_active': True,
                    'role': member_data.get('role', 'member'),
                    '_member_data': member_data  # Temp storage
                }
        
        # Phase 20: Batch fetch user documents for active members (1 read instead of N)
        if active_user_ids:
            try:
                user_refs = [db.collection('users').document(uid) for uid in active_user_ids]
                user_docs = db.get_all(user_refs)
                record_read(1, 'users')  # Batch read counts as 1 operation
                
                user_data_map = {}
                for user_doc in user_docs:
                    if user_doc.exists:
                        user_data_map[user_doc.id] = user_doc.to_dict()
                
                # Update member info with user data
                for user_id in active_user_ids:
                    user_data = user_data_map.get(user_id)
                    member_data = member_map[user_id].pop('_member_data', {})
                    
                    if user_data:
                        display_name = user_data.get('display_name') or user_data.get('email', '').split('@')[0]
                    else:
                        display_name = member_data.get('display_name', user_id)
                    
                    member_map[user_id]['display_name'] = display_name
                    
            except Exception as e:
                logger.warning(f"Failed to batch fetch users for history: {e}")
                # Fallback: use member data display names
                for user_id in active_user_ids:
                    member_data = member_map[user_id].pop('_member_data', {})
                    member_map[user_id]['display_name'] = member_data.get('display_name', user_id)
        
        # Phase 20: Cache result (TTL=300s)
        if cache_key:
            cache = get_cache_manager()
            if cache and cache.is_available():
                # Clean up temp data before caching
                for m in member_map.values():
                    m.pop('_member_data', None)
                cache.set(cache_key, member_map, ttl=300)
                logger.debug("[CACHE][-] All members history cached: %s", group_id)
        
        logger.debug(f"Got {len(member_map)} total members (active+removed) for group {group_id}")
        return member_map
    
    def add_member(
        self,
        group_id: str,
        user_id: str,
        display_name: str,
        added_by: str
    ) -> None:
        """
        Add a member to group
        
        Args:
            group_id: Group ID
            user_id: User ID to add
            display_name: User's display name
            added_by: User ID who is adding
        """
        try:
            # Get group
            group_data = self.get_group(group_id)
            
            # Check max members limit
            member_count = len(group_data.get('members', []))
            if member_count >= business_rules.MAX_GROUP_MEMBERS:
                raise MaxMembersReachedError(
                    group_id,
                    business_rules.MAX_GROUP_MEMBERS
                )
            
            # Check if already a member
            if user_id in group_data.get('members', []):
                raise DuplicateEntryError(
                    f"User {user_id} is already a member",
                    'group_member',
                    user_id
                )
            
            # Add member
            self.group_repo.add_member(group_id, user_id, display_name)
            
            # Invalidate caches (pass group_repo to invalidate all members' mega-bootstrap)
            _invalidate_membership_cache(group_id, user_id, self.group_repo)
            
            logger.info(
                "Added member %s to group %s by %s",
                user_id, group_id, added_by
            )
            
        except Exception as exc:
            logger.error("Error adding member: %s", str(exc))
            raise
    
    def remove_member(
        self,
        group_id: str,
        user_id: str,
        removed_by: str,
        reason: str = None
    ) -> None:
        """
        Soft-delete a member from group (Phase 15)
        
        Preserves member info for transaction history.
        Member's name will still appear in past expenses.
        
        Args:
            group_id: Group ID
            user_id: User ID to remove
            removed_by: User ID who is removing
            reason: Optional reason (left, kicked, etc.)
        """
        try:
            # Get group
            group_data = self.get_group(group_id)
            
            # Check if member exists (if not, consider it already removed - idempotent operation)
            if user_id not in group_data.get('members', []):
                logger.warning(
                    "User %s is not a member of group %s (already removed or never added)",
                    user_id, group_id
                )
                # Return success - idempotent operation
                return
            
            # Don't allow removing last admin
            member_details = group_data.get('member_details', {})
            admins = [
                uid for uid, details in member_details.items()
                if details.get('role') == 'admin' and details.get('is_active', True)
            ]
            
            if len(admins) == 1 and user_id == admins[0]:
                raise ValidationError(
                    "Cannot remove the last admin from the group"
                )
            
            # Determine reason
            removal_reason = reason
            if not removal_reason:
                removal_reason = 'left' if user_id == removed_by else 'removed'
            
            # Soft-delete member (preserves for transaction history)
            self.group_repo.remove_member(group_id, user_id, removed_by, removal_reason)
            
            # Invalidate caches (pass group_repo to invalidate all members' mega-bootstrap)
            _invalidate_membership_cache(group_id, user_id, self.group_repo)
            
            logger.info(
                "Soft-deleted member %s from group %s by %s (reason: %s)",
                user_id, group_id, removed_by, removal_reason
            )
            
        except Exception as exc:
            logger.error("Error removing member: %s", str(exc))
            raise
    
    def update_member_role(
        self,
        group_id: str,
        user_id: str,
        new_role: str,
        updated_by: str
    ) -> None:
        """
        Update member's role
        
        Args:
            group_id: Group ID
            user_id: User ID
            new_role: New role (admin/member)
            updated_by: User ID who is updating
        """
        try:
            # Validate role
            if new_role not in ['admin', 'member']:
                raise ValidationError(f"Invalid role: {new_role}")
            
            # Get group
            group_data = self.get_group(group_id)
            member_details = group_data.get('member_details', {})
            
            # If demoting admin, ensure at least one admin remains
            if new_role == 'member':
                admins = [
                    uid for uid, details in member_details.items()
                    if details.get('role') == 'admin' and details.get('is_active', True)
                ]
                
                if len(admins) == 1 and user_id == admins[0]:
                    raise ValidationError(
                        "Cannot demote the last admin. Promote another member first."
                    )
            
            # Update role
            self.group_repo.update_member_role(group_id, user_id, new_role)
            
            # Invalidate caches - role changes affect group data
            _invalidate_membership_cache(group_id, user_id, self.group_repo)
            
            logger.info(
                "Updated role for %s in group %s to %s by %s",
                user_id, group_id, new_role, updated_by
            )
            
        except Exception as exc:
            logger.error("Error updating member role: %s", str(exc))
            raise
    
    def update_group_settings(
        self,
        group_id: str,
        settings: GroupSettings,
        updated_by: str
    ) -> None:
        """
        Update group settings
        
        Args:
            group_id: Group ID
            settings: New settings
            updated_by: User ID who is updating
        """
        try:
            # Verify group exists
            self.get_group(group_id)
            
            # Update settings
            self.group_repo.update_settings(group_id, settings)
            
            # Invalidate group cache - settings are part of group data
            if CACHE_ENABLED:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache.delete(f"expense:group:{group_id}")
                    cache.delete(redis_config.KEY_GROUP_SUMMARY.format(gid=group_id))
            
            logger.info(
                "Updated settings for group %s by %s",
                group_id, updated_by
            )
            
        except Exception as exc:
            logger.error("Error updating group settings: %s", str(exc))
            raise
    
    def get_group_by_code(self, group_code: str) -> Optional[Dict]:
        """
        Find group by invite code
        
        Args:
            group_code: Group invite code
            
        Returns:
            Group document or None
        """
        return self.group_repo.get_group_by_code(group_code)
    
    def _generate_group_code(self, length: int = 8) -> str:
        """
        Generate random group code
        
        Args:
            length: Code length
            
        Returns:
            Random alphanumeric code
        """
        characters = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(characters) for _ in range(length))
        return code
    
    def is_member(self, group_id: str, user_id: str) -> bool:
        """
        Check if user is a member of the group
        Uses Redis cache to reduce Firestore reads (TTL=60s)
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            True if user is a member, False otherwise
        """
        try:
            # Try cache first
            if CACHE_ENABLED:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache_key = f"expense:membership:{group_id}:{user_id}"
                    cached = cache.get(cache_key)
                    if cached is not None:
                        return cached
            
            # Check Firestore
            member = self.group_repo.get_member(group_id, user_id)
            result = member is not None
            
            # Cache result (TTL=60s)
            if CACHE_ENABLED:
                cache = get_cache_manager()
                if cache and cache.is_available():
                    cache.set(cache_key, result, ttl=60)
            
            return result
        except Exception as e:
            logger.error(f"Error checking membership: {e}")
            return False
    
    def has_permission(self, group_id: str, user_id: str, permission: str) -> bool:
        """
        Check if user has a specific permission in the group
        
        Args:
            group_id: Group ID
            user_id: User ID
            permission: Permission name (e.g., 'edit_group', 'delete_group')
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            # First check if user is the group creator (owner)
            group_data = self.group_repo.get_by_id(group_id)
            if group_data and group_data.get('created_by') == user_id:
                # Group owner/creator has ALL permissions
                return True
            
            member = self.group_repo.get_member(group_id, user_id)
            if not member:
                return False
            
            role = member.get('role', 'member')
            
            # Role 'owner' has all permissions (legacy support)
            if role == 'owner':
                return True
            
            # Admin permissions
            if role == 'admin':
                admin_permissions = [
                    'edit_group', 'invite_members', 'add_member', 'remove_member',
                    'edit_expense', 'delete_expense', 'manage_settlements',
                    'restore_expense', 'change_roles'
                ]
                return permission in admin_permissions
            
            # Member permissions
            member_permissions = ['create_expense']
            return permission in member_permissions
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False
    
    def get_user_statistics(self, user_id: str) -> Dict:
        """
        Get statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Statistics dictionary
        """
        try:
            groups = self.get_user_groups(user_id)
            
            return {
                'total_groups': len(groups),
                'total_expenses': 0,  # TODO: Implement
                'total_spent': 0.0,  # TODO: Implement
                'total_paid': 0.0,  # TODO: Implement
                'pending_invitations': 0,  # TODO: Implement
                'active_settlements': 0  # TODO: Implement
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    def get_user_recent_activity(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent activity for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of items
            
        Returns:
            List of activity items
        """
        # TODO: Implement
        return []
    
    def search_user_expenses(self, user_id: str, query: str, page: int = 1, limit: int = 20) -> List[Dict]:
        """
        Search user's expenses across all groups
        
        Args:
            user_id: User ID
            query: Search query
            page: Page number
            limit: Items per page
            
        Returns:
            List of matching expenses
        """
        # TODO: Implement
        return []
    
    def get_group_summary(self, group_id: str) -> Dict:
        """
        Get comprehensive group summary
        
        Args:
            group_id: Group ID
            
        Returns:
            Summary dictionary with group, members, balances, etc.
        """
        group = self.group_repo.get_by_id(group_id)
        members = self.group_repo.get_members(group_id)
        
        return {
            'group': group,
            'members': members,
            'balances': [],  # TODO: Get from balance service
            'recent_expenses': [],  # TODO: Get from expense service
            'stats': {}  # TODO: Calculate stats
        }
