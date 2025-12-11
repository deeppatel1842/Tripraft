"""
Group Repository
Handles group data access and member management
"""

from typing import List, Optional, Dict
from datetime import datetime
from google.cloud.firestore import ArrayUnion, ArrayRemove
import logging

from .base import BaseRepository
from ..config import firestore_collections
from ..models.group import Group, GroupSettings
from ..exceptions import ResourceNotFoundError, ValidationError as CustomValidationError

# Import Firestore counter for direct operations
try:
    from expense_engine.firestore_counter import record_read, record_write
    TRACKING_ENABLED = True
except ImportError:
    TRACKING_ENABLED = False
    def record_read(count=1, collection=None): pass
    def record_write(count=1, collection=None): pass

logger = logging.getLogger(__name__)


class GroupRepository(BaseRepository[Group]):
    """
    Repository for group management
    Handles group CRUD and member operations
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.GROUPS
    
    def _normalize_group_data(self, data: Dict) -> Dict:
        """Ensure group_id field is present in group data"""
        if data and 'id' in data and 'group_id' not in data:
            data['group_id'] = data['id']
        return data
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get group by ID with normalized group_id field"""
        data = super().get_by_id(doc_id)
        return self._normalize_group_data(data) if data else None
    
    def get_member(self, group_id: str, user_id: str) -> Optional[Dict]:
        """Get member document from expense_group_members collection"""
        try:
            from firebase_admin import firestore as admin_firestore
            doc = admin_firestore.client().collection('expense_group_members').document(f"{group_id}_{user_id}").get()
            record_read(1, 'expense_group_members')  # Track direct Firestore read
            if doc.exists:
                data = doc.to_dict()
                # Only return if active member
                if data and data.get('is_active', False):
                    return data
            return None
        except Exception as exc:
            logger.error("Error getting member %s from group %s: %s", user_id, group_id, str(exc))
            return None
    
    def get_user_groups(self, user_id: str) -> List[Dict]:
        """
        Get all groups a user is a member of (excluding deleted/inactive groups)
        
        Args:
            user_id: User ID
            
        Returns:
            List of group documents
        """
        try:
            # Query groups where user is in members array
            results = self.query(
                filters=[
                    ('members', 'array_contains', user_id)
                ],
                order_by=('created_at', 'DESCENDING')
            )
            
            # Filter out inactive/deleted groups and normalize
            active_groups = [
                self._normalize_group_data(group) 
                for group in results 
                if group.get('is_active', True) is not False
            ]
            return active_groups
            
        except Exception as exc:
            logger.error("Error getting groups for user %s: %s", user_id, str(exc))
            raise
    
    def get_group_by_code(self, group_code: str) -> Optional[Dict]:
        """
        Find group by invite code
        
        Args:
            group_code: Group invite code
            
        Returns:
            Group document or None
        """
        try:
            results = self.query(
                filters=[
                    ('group_code', '==', group_code)
                ],
                limit=1
            )
            
            return self._normalize_group_data(results[0]) if results else None
            
        except Exception as exc:
            logger.error("Error finding group by code: %s", str(exc))
            raise
    
    def add_member(
        self,
        group_id: str,
        user_id: str,
        display_name: str,
        role: str = 'member',
        return_group_data: bool = False
    ):
        """
        Add a member to a group
        
        Phase 19.5: Added return_group_data option to avoid re-read after add_member
        
        Args:
            group_id: Group ID
            user_id: User ID
            display_name: User's display name
            role: Member role (admin/member)
            return_group_data: If True, return the updated group data
            
        Returns:
            None by default, or updated group_data dict if return_group_data=True
        """
        try:
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Check if already a member
            members = group_data.get('members', [])
            if user_id in members:
                logger.warning("User %s already in group %s", user_id, group_id)
                return group_data if return_group_data else None
            
            # Update group document (members array + member_details)
            self.update(group_id, {
                'members': ArrayUnion([user_id]),
                f'member_details.{user_id}': {
                    'user_id': user_id,
                    'display_name': display_name,
                    'role': role,
                    'joined_at': datetime.utcnow(),
                    'is_active': True
                }
            })
            
            # CRITICAL: Also create expense_group_members document for Firestore listeners
            from firebase_admin import firestore as admin_firestore
            member_ref = admin_firestore.client().collection('expense_group_members').document(f"{group_id}_{user_id}")
            member_ref.set({
                'group_id': group_id,
                'user_id': user_id,
                'display_name': display_name,
                'role': role,
                'is_active': True,
                'joined_at': datetime.utcnow()
            })
            record_write(1, 'expense_group_members')  # Track direct Firestore write
            
            logger.info("Added member %s to group %s (both collections updated)", user_id, group_id)
            
            # Phase 19.5: Return updated group data to avoid re-read
            if return_group_data:
                # Update in-memory group_data to reflect the change
                group_data['members'] = members + [user_id]
                if 'member_details' not in group_data:
                    group_data['member_details'] = {}
                group_data['member_details'][user_id] = {
                    'user_id': user_id,
                    'display_name': display_name,
                    'role': role,
                    'is_active': True
                }
                return group_data
            
            return None
            
        except Exception as exc:
            logger.error("Error adding member to group: %s", str(exc))
            raise
    
    def remove_member(self, group_id: str, user_id: str, removed_by: str = None, reason: str = None) -> None:
        """
        Soft-delete a member from a group (Phase 15)
        
        Preserves member info for transaction history.
        Member's name will still appear in past expenses.
        
        Args:
            group_id: Group ID
            user_id: User ID to remove
            removed_by: User ID who initiated the removal
            reason: Optional reason (left, kicked, etc.)
        """
        try:
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Check if member exists
            members = group_data.get('members', [])
            if user_id not in members:
                logger.warning("User %s not in group %s", user_id, group_id)
                return
            
            # Get current member details to preserve name
            member_details = group_data.get('member_details', {}).get(user_id, {})
            current_name = member_details.get('display_name') or member_details.get('user_name', '')
            current_email = member_details.get('email', '')
            
            removal_timestamp = datetime.utcnow()
            
            # Update group document - soft delete
            self.update(group_id, {
                'members': ArrayRemove([user_id]),
                f'member_details.{user_id}.is_active': False,
                f'member_details.{user_id}.removed_at': removal_timestamp,
                f'member_details.{user_id}.removed_by': removed_by,
                f'member_details.{user_id}.removal_reason': reason or 'removed',
                f'member_details.{user_id}.cached_display_name': current_name,
                f'member_details.{user_id}.cached_email': current_email,
            })
            
            # CRITICAL: Also update expense_group_members document with soft-delete
            # Use set with merge=True in case document doesn't exist
            from firebase_admin import firestore as admin_firestore
            member_ref = admin_firestore.client().collection('expense_group_members').document(f"{group_id}_{user_id}")
            member_ref.set({
                'group_id': group_id,
                'user_id': user_id,
                'is_active': False,
                'removed_at': removal_timestamp,
                'removed_by': removed_by,
                'removal_reason': reason or 'removed',
                'cached_display_name': current_name,
                'cached_email': current_email,
            }, merge=True)  # Use merge to handle case where document doesn't exist
            record_write(1, 'expense_group_members')  # Track direct Firestore write
            
            logger.info("Soft-deleted member %s from group %s (preserved for history)", user_id, group_id)
            
        except Exception as exc:
            logger.error("Error removing member from group: %s", str(exc))
            raise
    
    def update_member_role(self, group_id: str, user_id: str, new_role: str) -> None:
        """
        Update a member's role
        
        Args:
            group_id: Group ID
            user_id: User ID
            new_role: New role (admin/member)
        """
        try:
            if new_role not in ['admin', 'member']:
                raise CustomValidationError(f"Invalid role: {new_role}")
            
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Check if member exists
            members = group_data.get('members', [])
            if user_id not in members:
                raise CustomValidationError(f"User {user_id} not in group")
            
            # Update role
            self.update(group_id, {
                f'member_details.{user_id}.role': new_role
            })
            
            logger.info("Updated role for %s in group %s to %s", user_id, group_id, new_role)
            
        except Exception as exc:
            logger.error("Error updating member role: %s", str(exc))
            raise
    
    def get_group_members(self, group_id: str) -> List[Dict]:
        """
        Get all active members of a group
        
        Args:
            group_id: Group ID
            
        Returns:
            List of member details
        """
        try:
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            member_details = group_data.get('member_details', {})
            active_members = [
                details for details in member_details.values()
                if details.get('is_active', True)
            ]
            
            return active_members
            
        except Exception as exc:
            logger.error("Error getting group members: %s", str(exc))
            raise
    
    def update_settings(self, group_id: str, settings: GroupSettings) -> None:
        """
        Update group settings
        
        Args:
            group_id: Group ID
            settings: New settings
        """
        try:
            self.update(group_id, {
                'settings': settings.to_dict()
            })
            
            logger.info("Updated settings for group %s", group_id)
            
        except Exception as exc:
            logger.error("Error updating group settings: %s", str(exc))
            raise
    
    def soft_delete_group(self, group_id: str) -> None:
        """
        Soft delete a group (mark as inactive/deleted)
        
        Args:
            group_id: Group ID
        """
        try:
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            self.update(group_id, {
                'is_active': False,
                'deleted_at': datetime.utcnow()
            })
            
            logger.info("Soft deleted group: %s", group_id)
            
        except Exception as exc:
            logger.error("Error soft deleting group: %s", str(exc))
            raise
    
    def restore_group(self, group_id: str) -> None:
        """
        Restore a soft-deleted group
        
        Args:
            group_id: Group ID
        """
        try:
            group_data = self.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            self.update(group_id, {
                'is_active': True,
                'deleted_at': None
            })
            
            logger.info("Restored group: %s", group_id)
            
        except Exception as exc:
            logger.error("Error restoring group: %s", str(exc))
            raise
    
    def get_active_groups_for_user(self, user_id: str) -> List[Dict]:
        """
        Get only active (non-deleted) groups for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of active group documents
        """
        try:
            results = self.query(
                filters=[
                    ('members', 'array_contains', user_id),
                    ('is_active', '==', True)
                ],
                order_by=('created_at', 'DESCENDING')
            )
            
            return [self._normalize_group_data(group) for group in results]
            
        except Exception as exc:
            logger.error("Error getting active groups for user %s: %s", user_id, str(exc))
            raise
