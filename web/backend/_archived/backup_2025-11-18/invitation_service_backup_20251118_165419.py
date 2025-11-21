"""
Group Invitation Service
Professional service layer for handling group invitations
Follows separation of concerns and clean code principles
"""

import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from firebase_admin import firestore, auth as firebase_auth

logger = logging.getLogger(__name__)


class InvitationService:
    """Service for managing group invitations"""

    # Configuration
    INVITATION_EXPIRY_DAYS = 7
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    INVITATION_STATUS_PENDING = 'pending'
    INVITATION_STATUS_ACCEPTED = 'accepted'
    INVITATION_STATUS_EXPIRED = 'expired'

    def __init__(self):
        """Initialize invitation service"""
        self.db = firestore.client()
        logger.info("InvitationService initialized")

    def validate_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        return bool(re.match(self.EMAIL_REGEX, email))

    def get_user_display_name(self, user_id: str, user_email: str) -> str:
        """
        Get user's display name from Firebase Auth
        Falls back to email prefix if display name not set
        
        Args:
            user_id: Firebase user ID
            user_email: User's email
            
        Returns:
            Display name or email prefix
        """
        try:
            user_record = firebase_auth.get_user(user_id)
            if user_record.display_name:
                return user_record.display_name
        except Exception as e:
            logger.warning(f"Could not fetch display name for {user_id}: {e}")
        
        return user_email.split('@')[0]

    def validate_invitation_request(
        self,
        group_id: str,
        invited_email: str,
        inviter_email: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate invitation request
        
        Args:
            group_id: Group ID
            invited_email: Email to invite
            inviter_email: Email of person sending invitation (for self-invite check)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not group_id or not invited_email:
            return False, "Missing group_id or email"
        
        # Validate email format
        if not self.validate_email(invited_email):
            return False, f"Invalid email format: {invited_email}"
        
        # Prevent self-invitation
        if inviter_email and invited_email.lower() == inviter_email.lower():
            return False, "You cannot invite yourself to a group"
        
        return True, None

    def get_group(self, inviter_id: str, group_id: str) -> Optional[Dict]:
        """
        Get group document from travel_groups collection (Phase 1 migration)
        
        Args:
            inviter_id: ID of user inviting (not used after migration, kept for API compatibility)
            group_id: Group ID
            
        Returns:
            Group data or None if not found
        """
        try:
            # Phase 1 Migration: Groups now in travel_groups collection, not users/{uid}/groups
            group_ref = self.db.collection('travel_groups').document(group_id)
            group_doc = group_ref.get()
            
            if group_doc.exists:
                return group_doc.to_dict()
            
            return None
        except Exception as e:
            logger.error(f"Error fetching group {group_id}: {e}")
            raise

    def create_invitation(
        self,
        group_id: str,
        invited_email: str,
        inviter_id: str,
        inviter_email: str,
    ) -> Dict:
        """
        Create a new group invitation
        
        Args:
            group_id: Group ID
            invited_email: Email to invite
            inviter_id: ID of user inviting
            inviter_email: Email of inviter
            
        Returns:
            Invitation document data
            
        Raises:
            ValueError: If validation fails
            Exception: If Firestore operation fails
        """
        # Validate request (including self-invitation check)
        is_valid, error_msg = self.validate_invitation_request(group_id, invited_email, inviter_email)
        if not is_valid:
            raise ValueError(error_msg)

        # Check for existing pending invitation for same email + group
        existing_invitations = (
            self.db.collection('group_invitations')
            .where('invited_email', '==', invited_email)
            .where('group_id', '==', group_id)
            .where('status', '==', self.INVITATION_STATUS_PENDING)
            .limit(1)
            .get()
        )
        
        if existing_invitations:
            existing_doc = list(existing_invitations)[0]
            existing_data = existing_doc.to_dict()
            logger.info(
                f"Pending invitation already exists for {invited_email} "
                f"to group {group_id}, returning existing invitation"
            )
            return existing_data

        # Get group to verify it exists
        group_data = self.get_group(inviter_id, group_id)
        if not group_data:
            raise ValueError(f"Group not found: {group_id}")

        # Prepare invitation data
        invitation_id = str(uuid.uuid4())
        inviter_name = self.get_user_display_name(inviter_id, inviter_email)
        expires_at = datetime.utcnow() + timedelta(days=self.INVITATION_EXPIRY_DAYS)

        invitation_data = {
            'invitation_id': invitation_id,
            'group_id': group_id,
            'group_name': group_data.get('name', 'Unknown Group'),
            'invited_by': inviter_id,
            'invited_by_email': inviter_email,
            'invited_by_name': inviter_name,
            'invited_email': invited_email,
            'status': self.INVITATION_STATUS_PENDING,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'responded_at': None
        }

        # Save to Firestore
        try:
            self.db.collection('group_invitations').document(
                invitation_id
            ).set(invitation_data)
            
            logger.info(
                f"Invitation created: {invitation_id} to {invited_email} "
                f"for group {group_id}"
            )
            return invitation_data
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            raise

    def get_invitation(self, invitation_id: str) -> Optional[Dict]:
        """
        Get invitation by ID
        
        Args:
            invitation_id: Invitation ID
            
        Returns:
            Invitation data or None
        """
        try:
            inv_doc = (
                self.db
                .collection('group_invitations')
                .document(invitation_id)
                .get()
            )
            
            if inv_doc.exists:
                return inv_doc.to_dict()
            
            return None
        except Exception as e:
            logger.error(f"Error fetching invitation {invitation_id}: {e}")
            raise

    def is_invitation_valid(self, invitation_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if invitation is valid for acceptance
        
        Args:
            invitation_data: Invitation document data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if already responded to
        status = invitation_data.get('status')
        if status != self.INVITATION_STATUS_PENDING:
            return False, f"Invitation already {status}"
        
        # Check if expired
        expires_at = datetime.fromisoformat(
            invitation_data.get('expires_at', '')
        )
        if datetime.utcnow() > expires_at:
            return False, "Invitation has expired"
        
        return True, None

    def accept_invitation(
        self,
        invitation_id: str,
        user_id: str,
        user_email: str,
    ) -> Dict:
        """
        Accept a group invitation and add user to group
        
        Args:
            invitation_id: Invitation ID to accept
            user_id: User ID accepting invitation
            user_email: User email
            
        Returns:
            Response data with group_id
            
        Raises:
            ValueError: If validation fails
            Exception: If Firestore operation fails
        """
        # Get invitation
        invitation_data = self.get_invitation(invitation_id)
        if not invitation_data:
            raise ValueError("Invitation not found")

        # Validate invitation
        is_valid, error_msg = self.is_invitation_valid(invitation_data)
        if not is_valid:
            raise ValueError(error_msg)

        # Check if email matches
        if invitation_data.get('invited_email') != user_email:
            raise ValueError(
                "This invitation is not for your email address"
            )

        inviter_id = invitation_data.get('invited_by')
        group_id = invitation_data.get('group_id')

        # Get group
        group_data = self.get_group(inviter_id, group_id)
        if not group_data:
            raise ValueError("Group not found")

        # Prepare member data
        user_display_name = self.get_user_display_name(user_id, user_email)
        member_detail = {
            'uid': user_id,
            'email': user_email,
            'display_name': user_display_name,
            'role': 'member',
            'is_creator': False,
            'joined_at': datetime.utcnow().isoformat()
        }
        
        # CRITICAL: Create/update user document in users collection
        # This ensures member details are available for all future operations
        from .firebase_operations import GroupPlannerFirebaseOperations
        firebase_ops = GroupPlannerFirebaseOperations()
        firebase_ops.create_or_update_user(
            uid=user_id,
            email=user_email,
            display_name=user_display_name
        )
        logger.info(f"✅ Created/updated user document for {user_id} ({user_email})")

        # Update group members
        if user_id not in group_data.get('members', []):
            group_data['members'].append(user_id)
            
        # Add to group_members collection (Phase 1 structure)
        from .models import GroupMember
        member = GroupMember(
            user_id=user_id,
            group_id=group_id,
            role='member',
            joined_at=datetime.utcnow(),
        )
        self.db.collection('group_members').add(member.to_dict())
        logger.info(f"✅ Added user {user_id} to group_members collection")

        # Check if member already exists in details
        member_exists = any(
            m.get('uid') == user_id 
            for m in group_data.get('member_details', [])
        )
        
        if not member_exists:
            if 'member_details' not in group_data:
                group_data['member_details'] = []
            group_data['member_details'].append(member_detail)

        try:
            # Phase 1 Migration: Update group in travel_groups collection
            group_ref = self.db.collection('travel_groups').document(group_id)
            group_ref.update({
                'members': group_data['members'],
                'member_details': group_data['member_details']
            })

            # Save group to user's collection for quick access
            self.db.collection('users').document(user_id).collection(
                'groups'
            ).document(group_id).set(group_data)

            # Update invitation status
            self.db.collection('group_invitations').document(
                invitation_id
            ).update({
                'status': self.INVITATION_STATUS_ACCEPTED,
                'responded_at': datetime.utcnow().isoformat(),
                'accepted_user_id': user_id
            })

            logger.info(
                f"Invitation {invitation_id} accepted by {user_id} "
                f"for group {group_id}"
            )
            
            # 🔥 CRITICAL: Immediately invalidate user's groups cache for instant update
            # This ensures the new group appears immediately when they navigate to group-trip page
            logger.info(f"🗑️ Invalidating groups cache for user {user_id} after invitation acceptance")

            return {
                'group_id': group_id,
                'invitation_id': invitation_id
            }
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            raise

    def get_user_invitations(self, user_email: str, user_id: str = None) -> list:
        """
        Get all pending invitations for a user
        Returns both:
        - Invitations RECEIVED by the user (invited_email == user_email) - type='received'
        - Invitations SENT by the user (invited_by == user_id) - type='sent'
        
        Args:
            user_email: User email
            user_id: User ID (optional, for getting sent invitations)
            
        Returns:
            List of invitation documents with 'invitation_type' field
        """
        try:
            print(f'\n🔍 [INVITATION_SERVICE] Querying invitations for: {user_email} (ID: {user_id})', flush=True)
            invitations = []
            seen_invitation_ids = set()  # Track IDs to prevent duplicates
            
            # 1. Get RECEIVED invitations (where this user is the invited person)
            print(f'   📥 Querying RECEIVED invitations (invited_email == {user_email})...', flush=True)
            received_query = (
                self.db
                .collection('group_invitations')
                .where('invited_email', '==', user_email)
            )
            received_docs = received_query.stream()

            received_count = 0
            for doc in received_docs:
                received_count += 1
                inv_data = doc.to_dict()
                print(f'      📄 Found RECEIVED: ID={doc.id}, status={inv_data.get("status")}', flush=True)

                # Mark as expired if needed
                if inv_data.get('status') == self.INVITATION_STATUS_PENDING:
                    expires_at = datetime.fromisoformat(
                        inv_data.get('expires_at', '')
                    )
                    if datetime.utcnow() > expires_at:
                        print(f'      ⚠️ Marking as expired: {doc.id}', flush=True)
                        doc.reference.update({
                            'status': self.INVITATION_STATUS_EXPIRED
                        })
                        inv_data['status'] = self.INVITATION_STATUS_EXPIRED

                # Only include pending invitations (and avoid duplicates)
                if inv_data.get('status') == self.INVITATION_STATUS_PENDING and doc.id not in seen_invitation_ids:
                    inv_data['invitation_type'] = 'received'  # Mark as received
                    seen_invitation_ids.add(doc.id)
                    print(f'      ✅ Including RECEIVED invitation: {doc.id}', flush=True)
                    invitations.append(inv_data)
                else:
                    print(f'      ⏭️ Skipping (status={inv_data.get("status")} or duplicate): {doc.id}', flush=True)
            
            # 2. Get SENT invitations (where this user is the inviter)
            if user_id:
                print(f'   📤 Querying SENT invitations (invited_by == {user_id})...', flush=True)
                sent_query = (
                    self.db
                    .collection('group_invitations')
                    .where('invited_by', '==', user_id)
                )
                sent_docs = sent_query.stream()

                sent_count = 0
                for doc in sent_docs:
                    sent_count += 1
                    inv_data = doc.to_dict()
                    print(f'      📄 Found SENT: ID={doc.id}, to={inv_data.get("invited_email")}, status={inv_data.get("status")}', flush=True)

                    # Mark as expired if needed
                    if inv_data.get('status') == self.INVITATION_STATUS_PENDING:
                        expires_at = datetime.fromisoformat(
                            inv_data.get('expires_at', '')
                        )
                        if datetime.utcnow() > expires_at:
                            print(f'      ⚠️ Marking as expired: {doc.id}', flush=True)
                            doc.reference.update({
                                'status': self.INVITATION_STATUS_EXPIRED
                            })
                            inv_data['status'] = self.INVITATION_STATUS_EXPIRED

                    # Only include pending invitations (and avoid duplicates)
                    if inv_data.get('status') == self.INVITATION_STATUS_PENDING and doc.id not in seen_invitation_ids:
                        inv_data['invitation_type'] = 'sent'  # Mark as sent
                        seen_invitation_ids.add(doc.id)
                        print(f'      ✅ Including SENT invitation: {doc.id}', flush=True)
                        invitations.append(inv_data)
                    else:
                        print(f'      ⏭️ Skipping (status={inv_data.get("status")}): {doc.id}', flush=True)

            print(f'🔍 [INVITATION_SERVICE] Query complete: {len(invitations)} total pending invitations', flush=True)
            logger.info(
                f"Retrieved {len(invitations)} invitations for {user_email}"
            )
            return invitations
        except Exception as e:
            print(f'❌ [INVITATION_SERVICE] Error: {e}', flush=True)
            logger.error(f"Error fetching user invitations: {e}")
            raise

    def resend_invitation(self, invitation_id: str) -> Dict:
        """
        Resend an existing pending invitation
        Updates the created_at timestamp and recalculates expiry
        
        Args:
            invitation_id: ID of invitation to resend
            
        Returns:
            Updated invitation data
            
        Raises:
            ValueError: If invitation not found or not pending
            Exception: If Firestore operation fails
        """
        try:
            # Get existing invitation
            inv_data = self.get_invitation(invitation_id)
            if not inv_data:
                raise ValueError(f"Invitation not found: {invitation_id}")

            # Check if invitation is still pending
            if inv_data.get('status') != self.INVITATION_STATUS_PENDING:
                raise ValueError(
                    f"Cannot resend invitation with status: {inv_data.get('status')}"
                )

            # Check if not expired
            expires_at_str = inv_data.get('expires_at', '')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() > expires_at:
                    raise ValueError("Invitation has expired")

            # Update with new timestamp and new expiry
            new_expires_at = datetime.utcnow() + timedelta(
                days=self.INVITATION_EXPIRY_DAYS
            )

            update_data = {
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': new_expires_at.isoformat(),
                'resent_at': datetime.utcnow().isoformat()
            }

            # Update in Firestore
            self.db.collection('group_invitations').document(
                invitation_id
            ).update(update_data)

            # Merge with original data for return
            inv_data.update(update_data)

            logger.info(
                f"Invitation resent: {invitation_id} to {inv_data.get('invited_email')}"
            )
            return inv_data
        except Exception as e:
            logger.error(f"Error resending invitation: {e}")
            raise

    def remove_member_from_group(
        self, group_id: str, member_id: str, owner_id: str
    ) -> bool:
        """
        Remove a member from a group (Phase 1 migration - uses travel_groups collection)
        
        Args:
            group_id: Group ID
            member_id: ID of member to remove
            owner_id: ID of group owner (for permission check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"Removing member {member_id} from group {group_id} by owner {owner_id}"
            )
            
            # Phase 1 Migration: Get group from travel_groups collection
            group_ref = self.db.collection('travel_groups').document(group_id)
            group_doc = group_ref.get()
            
            if not group_doc.exists:
                logger.error(f"Group {group_id} not found in travel_groups collection")
                return False
            
            group_data = group_doc.to_dict()
            
            # Verify owner permission
            if group_data.get('created_by') != owner_id:
                logger.error(f"User {owner_id} is not the owner of group {group_id}")
                return False
            
            members = group_data.get('members', [])
            member_details = group_data.get('member_details', [])
            
            # Remove from members array
            if member_id in members:
                members.remove(member_id)
                logger.info(f"Removed {member_id} from members array")
            else:
                logger.warning(f"Member {member_id} not found in members array")
            
            # Remove from member_details array (check both uid and user_id fields)
            member_details = [
                m for m in member_details 
                if m.get('uid') != member_id and m.get('user_id') != member_id
            ]
            logger.info(f"Updated member_details array, new length: {len(member_details)}")
            
            # Update group document in travel_groups collection
            group_ref.update({
                'members': members,
                'member_details': member_details
            })
            logger.info(f"Updated group document in travel_groups collection")
            
            logger.info(f"Successfully removed member {member_id} from group {group_id}")
            logger.info(f"Remaining members: {members}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing member from group: {e}")
            return False
