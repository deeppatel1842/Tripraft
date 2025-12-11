"""
Group Planner Firebase Operations
Firebase/Firestore database operations for group planner system
Following expense engine architecture patterns
"""

import logging
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore, exceptions
from google.cloud.firestore import ArrayRemove, ArrayUnion

from .models import (
    TravelGroup,
    GroupMember,
    GroupInvitation,
    GroupRole,
    InvitationStatus,
    create_group_id,
    create_invitation_id,
    validate_email
)
from .config import get_collection_name

logger = logging.getLogger(__name__)


class GroupPlannerFirebaseOperations:
    """Firebase database operations for group planner system"""

    def __init__(self):
        """Initialize Firebase connection"""
        try:
            self.db = firestore.client()
            logger.info("GroupPlannerFirebaseOperations initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Firebase: %s", e)
            raise

    # =========================================================================
    # GROUP OPERATIONS
    # =========================================================================

    def create_group(
        self,
        name: str,
        description: str,
        created_by: str,
        destination: Optional[str] = None,
        trip_dates: Optional[Dict] = None,
        budget_range: Optional[Dict] = None,
        group_id: Optional[str] = None,
    ) -> str:
        """
        Create a new travel group
        Args:
            name: Group name
            description: Group description
            created_by: Creator's user ID
            destination: Optional destination
            trip_dates: Optional trip dates {start_date, end_date}
            budget_range: Optional budget {min, max, currency}
            group_id: Optional pre-generated group ID (for optimistic updates)
        Returns:
            Group ID
        """
        try:
            if not group_id:
                group_id = create_group_id()

            # Get creator's email and display name from Firebase Auth
            try:
                from firebase_admin import auth as firebase_auth
                user_record = firebase_auth.get_user(created_by)
                creator_email = user_record.email
                creator_display_name = user_record.display_name or creator_email.split('@')[0]
            except Exception as e:
                logger.warning(f"Could not fetch creator info: {e}")
                creator_email = "unknown@example.com"
                creator_display_name = "Unknown User"

            group = TravelGroup(
                group_id=group_id,
                name=name,
                description=description,
                created_by=created_by,
                created_at=datetime.utcnow(),
                members=[created_by],  # Creator is first member
                destination=destination,
                trip_dates=trip_dates,
                budget_range=budget_range,
            )
            
            # Convert to dict and add member_details with creator info
            group_dict = group.to_dict()
            group_dict['member_details'] = [{
                'user_id': created_by,
                'email': creator_email,
                'display_name': creator_display_name,
                'role': 'creator',
                'is_creator': True,
                'joined_at': datetime.utcnow().isoformat()
            }]

            # Create group document
            collection_name = get_collection_name('TRAVEL_GROUPS')
            self.db.collection(collection_name).document(group_id).set(group_dict)

            # Add creator as member with CREATOR role
            member = GroupMember(
                user_id=created_by,
                group_id=group_id,
                role=GroupRole.CREATOR.value,
                joined_at=datetime.utcnow(),
            )

            collection_name = get_collection_name('GROUP_MEMBERS')
            self.db.collection(collection_name).add(member.to_dict())

            logger.info("Travel group created: %s by %s", group_id, created_by)
            return group_id

        except exceptions.FirebaseError as e:
            logger.error("Error creating group: %s", e)
            raise

    def _enrich_member_details(self, member_details: List[Dict]) -> List[Dict]:
        """
        Enrich member_details with email and display_name from Firebase Auth
        For existing groups that don't have email field populated
        """
        logger.info(f"🔍 [ENRICH] Processing {len(member_details)} members")
        enriched = []
        
        for idx, member in enumerate(member_details):
            logger.info(f"🔍 [ENRICH] Member {idx}: {member}")
            
            # If email already exists, keep as is
            if member.get('email'):
                logger.info(f"✅ [ENRICH] Member {idx} already has email: {member.get('email')}")
                enriched.append(member)
                continue
            
            # Fetch email from Firebase Auth
            user_id = member.get('user_id') or member.get('uid')
            if user_id:
                try:
                    from firebase_admin import auth as firebase_auth
                    user_record = firebase_auth.get_user(user_id)
                    member['email'] = user_record.email
                    # Update display_name if null
                    if not member.get('display_name'):
                        member['display_name'] = user_record.display_name or user_record.email.split('@')[0]
                    logger.info(f"✅ [ENRICH] Enriched member {user_id} with email: {user_record.email}, name: {member['display_name']}")
                except Exception as e:
                    logger.warning(f"❌ [ENRICH] Could not fetch email for user {user_id}: {e}")
                    member['email'] = 'unknown@example.com'
            else:
                logger.warning(f"⚠️ [ENRICH] Member {idx} has no user_id or uid!")
            
            enriched.append(member)
        
        logger.info(f"✅ [ENRICH] Finished enriching {len(enriched)} members")
        return enriched

    def get_group(self, group_id: str) -> Optional[Dict]:
        """Get group by ID with enriched member_details"""
        try:
            doc = self.db.collection("travel_groups").document(group_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["group_id"] = doc.id
                
                logger.info(f"📦 [GET_GROUP] Retrieved group {group_id}, has member_details: {'member_details' in data}")
                
                # If member_details doesn't exist, create it from members array
                if 'member_details' not in data or not data['member_details']:
                    logger.warning(f"⚠️ [GET_GROUP] Group {group_id} has no member_details, generating from members array")
                    members_array = data.get('members', [])
                    created_by = data.get('created_by')
                    
                    if members_array:
                        member_details = []
                        from firebase_admin import auth as firebase_auth
                        
                        for user_id in members_array:
                            try:
                                user_record = firebase_auth.get_user(user_id)
                                member_detail = {
                                    'user_id': user_id,
                                    'email': user_record.email,
                                    'display_name': user_record.display_name or user_record.email.split('@')[0],
                                    'role': 'creator' if user_id == created_by else 'member',
                                    'is_creator': user_id == created_by,
                                    'avatar_url': user_record.photo_url if hasattr(user_record, 'photo_url') else None,
                                    'joined_at': data.get('created_at', datetime.utcnow().isoformat())
                                }
                                member_details.append(member_detail)
                                logger.info(f"✅ [GET_GROUP] Generated member_detail for {user_id}: {user_record.email}")
                            except Exception as e:
                                logger.error(f"❌ [GET_GROUP] Could not fetch user {user_id}: {e}")
                        
                        # Update data with generated member_details
                        data['member_details'] = member_details
                        
                        # Persist to Firestore so we don't have to regenerate next time
                        try:
                            doc.reference.update({'member_details': member_details})
                            logger.info(f"💾 [GET_GROUP] Saved member_details to Firestore for group {group_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ [GET_GROUP] Could not save member_details: {e}")
                
                # Enrich member_details with emails if missing
                if 'member_details' in data and data['member_details']:
                    logger.info(f"🔄 [GET_GROUP] Enriching {len(data['member_details'])} members")
                    data['member_details'] = self._enrich_member_details(data['member_details'])
                
                return data
            return None
        except exceptions.FirebaseError as e:
            logger.error("Error getting group %s: %s", group_id, e)
            return None

    def update_group(self, group_id: str, updates: Dict) -> bool:
        """Update group information"""
        try:
            # Remove None values and add timestamp
            clean_updates = {k: v for k, v in updates.items() if v is not None}
            clean_updates["updated_at"] = datetime.utcnow().isoformat()

            self.db.collection("travel_groups").document(group_id).update(clean_updates)
            logger.info("Group updated: %s", group_id)
            return True
        except Exception as e:
            logger.error("Error updating group %s: %s", group_id, e)
            return False

    def delete_group(self, group_id: str, user_id: str) -> bool:
        """
        Delete group (only creator can delete)
        Also deletes all related data: members, places, polls, invitations
        Idempotent: returns True if group doesn't exist (already deleted)
        """
        try:
            # First check if group exists
            group = self.get_group(group_id)
            if not group:
                # Group already deleted - treat as success (idempotent)
                logger.info(
                    "Group %s not found, already deleted - returning success",
                    group_id,
                )
                return True
            
            # Check if user is creator
            created_by = group.get("created_by")
            if created_by != user_id:
                logger.warning(
                    "User %s attempted to delete group %s without permission (creator: %s)",
                    user_id,
                    group_id,
                    created_by,
                )
                return False

            batch = self.db.batch()

            # Delete group document
            group_ref = self.db.collection("travel_groups").document(group_id)
            batch.delete(group_ref)

            # Delete all members
            members_query = self.db.collection("group_members").where(
                "group_id", "==", group_id
            )
            for member_doc in members_query.stream():
                batch.delete(member_doc.reference)

            # Delete all places
            places_query = self.db.collection("travel_places").where(
                "group_id", "==", group_id
            )
            for place_doc in places_query.stream():
                batch.delete(place_doc.reference)

            # Delete all polls
            polls_query = self.db.collection("travel_polls").where(
                "group_id", "==", group_id
            )
            for poll_doc in polls_query.stream():
                batch.delete(poll_doc.reference)

            # Delete all invitations
            invitations_query = self.db.collection("group_invitations").where(
                "group_id", "==", group_id
            )
            for invitation_doc in invitations_query.stream():
                batch.delete(invitation_doc.reference)

            # Delete trip documents
            docs_query = self.db.collection("trip_documents").where(
                "group_id", "==", group_id
            )
            for doc_doc in docs_query.stream():
                batch.delete(doc_doc.reference)

            batch.commit()
            logger.info("Group deleted: %s by %s", group_id, user_id)
            return True

        except Exception as e:
            logger.error("Error deleting group %s: %s", group_id, e)
            return False

    def get_user_groups(self, user_id: str) -> List[Dict]:
        """Get all groups for a user"""
        try:
            # Get user's memberships
            memberships_query = self.db.collection("group_members").where(
                "user_id", "==", user_id
            )
            group_ids = [
                doc.to_dict()["group_id"] for doc in memberships_query.stream()
            ]

            if not group_ids:
                return []

            # Get group details
            groups = []
            for group_id in group_ids:
                group = self.get_group(group_id)
                if group:
                    groups.append(group)

            # Sort by created_at (most recent first)
            groups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return groups

        except Exception as e:
            logger.error("Error getting user groups for %s: %s", user_id, e)
            return []

    # =========================================================================
    # MEMBER OPERATIONS
    # =========================================================================

    def add_member_to_group(
        self, group_id: str, user_id: str, role: str = GroupRole.MEMBER.value
    ) -> bool:
        """Add member to group"""
        try:
            # Check if already a member
            existing_query = (
                self.db.collection("group_members")
                .where("group_id", "==", group_id)
                .where("user_id", "==", user_id)
                .limit(1)
            )

            if len(list(existing_query.stream())) > 0:
                logger.info(
                    "User %s is already a member of group %s", user_id, group_id
                )
                return True

            member = GroupMember(
                user_id=user_id,
                group_id=group_id,
                role=role,
                joined_at=datetime.utcnow(),
            )

            # Add member document
            # Update group members list
            group_ref = self.db.collection("travel_groups").document(group_id)
            group_ref.update({"members": ArrayUnion([user_id])})

            logger.info("Member added to group: %s -> %s", user_id, group_id)
            return True
            return True

        except Exception as e:
            logger.error("Error adding member %s to group %s: %s", user_id, group_id, e)
            return False

    def remove_member_from_group(
        self, group_id: str, user_id: str, removed_by: str
    ) -> bool:
        """Remove member from group"""
        try:
            # Check permissions (creator/admin can remove, members can remove themselves)
            if user_id != removed_by and not self.is_group_admin(group_id, removed_by):
                logger.warning(
                    "User %s attempted to remove %s without permission",
                    removed_by,
                    user_id,
                )
                return False

            # Cannot remove creator
            if self.is_group_creator(group_id, user_id):
                logger.warning(
                    "Cannot remove group creator %s from group %s", user_id, group_id
                )
                return False

            # Remove member document
            members_query = (
                self.db.collection("group_members")
                .where("group_id", "==", group_id)
                .where("user_id", "==", user_id)
            )

            for member_doc in members_query.stream():
                member_doc.reference.delete()

            # Update group members list
            group_ref = self.db.collection("travel_groups").document(group_id)
            group_ref.update({"members": ArrayRemove([user_id])})

            logger.info("Member removed from group: %s <- %s", user_id, group_id)
            return True

        except Exception as e:
            logger.error(
                "Error removing member %s from group %s: %s", user_id, group_id, e
            )
            return False

    def get_group_members(self, group_id: str) -> List[Dict]:
        """Get all members of a group"""
        try:
            members_query = self.db.collection("group_members").where(
                "group_id", "==", group_id
            )
            members = []

            for doc in members_query.stream():
                member_data = doc.to_dict()
                member_data["member_id"] = doc.id

                # Get user details from users collection
                user = self.get_user(member_data["user_id"])
                if user:
                    member_data["display_name"] = user.get(
                        "display_name", user.get("email", "")
                    )
                    member_data["email"] = user.get("email", "")
                    member_data["avatar_url"] = user.get("avatar_url")
                else:
                    # Fallback: Get user details from Firebase Auth
                    logger.debug("🔍 [MEMBERS] User %s not in users collection, fetching from Firebase Auth", member_data["user_id"])
                    try:
                        from firebase_admin import auth as firebase_auth
                        user_record = firebase_auth.get_user(member_data["user_id"])
                        member_data["display_name"] = user_record.display_name or user_record.email.split('@')[0] if user_record.email else "Unknown User"
                        member_data["email"] = user_record.email
                        member_data["avatar_url"] = user_record.photo_url
                        logger.debug("✅ [MEMBERS] Enriched from Auth: %s (%s)", member_data["display_name"], member_data["email"])
                    except Exception as auth_error:
                        logger.warning("⚠️ [MEMBERS] Could not fetch user %s from Auth: %s", member_data["user_id"], auth_error)
                        member_data["display_name"] = "Unknown User"
                        member_data["email"] = ""
                        member_data["avatar_url"] = None

                members.append(member_data)

            # Sort by role (creator first, then admin, then members) and join date
            role_order = {
                GroupRole.CREATOR.value: 0,
                GroupRole.ADMIN.value: 1,
                GroupRole.MEMBER.value: 2,
            }
            members.sort(
                key=lambda x: (role_order.get(x["role"], 3), x.get("joined_at", ""))
            )

            return members

        except Exception as e:
            logger.error("Error getting members for group %s: %s", group_id, e)
            return []

    def is_group_member(self, group_id: str, user_id: str) -> bool:
        """Check if user is a member of the group"""
        try:
            # First check group_members collection (Phase 1 migration)
            members_query = (
                self.db.collection("group_members")
                .where("group_id", "==", group_id)
                .where("user_id", "==", user_id)
                .limit(1)
            )

            is_member = len(list(members_query.stream())) > 0
            
            # Fallback: Check group document's members array
            if not is_member:
                logger.debug("🔍 User %s not in group_members collection, checking group document", user_id)
                group_doc = self.db.collection("travel_groups").document(group_id).get()
                if group_doc.exists:
                    members = group_doc.to_dict().get('members', [])
                    is_member = user_id in members
                    logger.debug("🔍 Members array check: %s in %s = %s", user_id, members, is_member)
            
            return is_member
        except Exception as e:
            logger.error(
                "Error checking membership for %s in group %s: %s", user_id, group_id, e
            )
            return False

    def is_group_admin(self, group_id: str, user_id: str) -> bool:
        """Check if user is admin or creator of the group"""
        try:
            members_query = (
                self.db.collection("group_members")
                .where("group_id", "==", group_id)
                .where("user_id", "==", user_id)
                .limit(1)
            )

            for doc in members_query.stream():
                role = doc.to_dict().get("role")
                return role in [GroupRole.CREATOR.value, GroupRole.ADMIN.value]

            return False
        except Exception as e:
            logger.error(
                "Error checking admin status for %s in group %s: %s",
                user_id,
                group_id,
                e,
            )
            return False

    def is_group_creator(self, group_id: str, user_id: str) -> bool:
        """Check if user is creator of the group"""
        try:
            group = self.get_group(group_id)
            if not group:
                logger.warning(f"❌ [IS_CREATOR] Group {group_id} not found")
                return False
            
            created_by = group.get("created_by")
            is_creator = created_by == user_id
            
            logger.info(f"🔍 [IS_CREATOR] Group {group_id}: created_by={created_by}, user_id={user_id}, is_creator={is_creator}")
            return is_creator
        except Exception as e:
            logger.error(
                "Error checking creator status for %s in group %s: %s",
                user_id,
                group_id,
                e,
            )
            return False

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            doc = self.db.collection("users").document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["uid"] = doc.id
                return data
            return None
        except Exception as e:
            logger.error("Error getting user %s: %s", user_id, e)
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            users_query = (
                self.db.collection("users").where("email", "==", email).limit(1)
            )
            for doc in users_query.stream():
                data = doc.to_dict()
                data["uid"] = doc.id
                return data
            return None
        except Exception as e:
            logger.error("Error getting user by email %s: %s", email, e)
            return None

    def create_or_update_user(
        self, uid: str, email: str, display_name: str, username: Optional[str] = None
    ) -> bool:
        """Create or update user profile"""
        try:
            user_data = {
                "email": email,
                "display_name": display_name,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if username:
                user_data["username"] = username

            # Check if user exists
            existing_user = self.get_user(uid)
            if existing_user:
                # Update existing user
                self.db.collection("users").document(uid).update(user_data)
                logger.info("User updated: %s", uid)
            else:
                # Create new user
                user_data["created_at"] = datetime.utcnow().isoformat()
                self.db.collection("users").document(uid).set(user_data)
                logger.info("User created: %s", uid)

            return True
        except Exception as e:
            logger.error("Error creating/updating user %s: %s", uid, e)
            return False

    # =========================================================================
    # INVITATION OPERATIONS (Following expense engine pattern)
    # =========================================================================

    def create_invitation(
        self,
        group_id: str,
        invited_by: str,
        invited_email: str,
        expires_in_days: int = 7,
    ) -> Dict:
        """
        Create group invitation
        Args:
            group_id: Target group ID
            invited_by: Inviter's user ID
            invited_email: Email to invite
            expires_in_days: Invitation expiration days
        Returns:
            Invitation dictionary
        """
        try:
            if not validate_email(invited_email):
                raise ValueError("Invalid email address: %s" % invited_email)

            invitation_id = create_invitation_id()
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            # Check if user already exists
            invited_user = None
            existing_user = self.get_user_by_email(invited_email)
            if existing_user:
                invited_user = existing_user["uid"]

            invitation = GroupInvitation(
                invitation_id=invitation_id,
                group_id=group_id,
                invited_by=invited_by,
                invited_email=invited_email,
                invited_user=invited_user,
                status=InvitationStatus.PENDING.value,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
            )

            self.db.collection("group_invitations").document(invitation_id).set(
                invitation.to_dict()
            )
            logger.info("Group invitation created: %s", invitation_id)

            return invitation.to_dict()

        except Exception as e:
            logger.error("Error creating invitation: %s", e)
            raise

    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict]:
        """Get invitation by ID"""
        try:
            doc = self.db.collection("group_invitations").document(invitation_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["invitation_id"] = doc.id
                return data
            return None
        except Exception as e:
            logger.error("Error getting invitation %s: %s", invitation_id, e)
            return None

    def respond_to_invitation(
        self, invitation_id: str, user_id: str, accept: bool
    ) -> bool:
        """Respond to group invitation"""
        try:
            invitation = self.get_invitation_by_id(invitation_id)
            if not invitation:
                logger.error("Invitation not found: %s", invitation_id)
                return False

            if invitation["status"] != InvitationStatus.PENDING.value:
                logger.error("Invitation %s is not pending", invitation_id)
                return False

            # Check if expired
            expires_at = datetime.fromisoformat(invitation["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.error("Invitation %s has expired", invitation_id)
                return False

            # Update invitation status
            new_status = (
                InvitationStatus.ACCEPTED.value
                if accept
                else InvitationStatus.REJECTED.value
            )
            update_data = {
                "status": new_status,
                "responded_at": datetime.utcnow().isoformat(),
            }

            self.db.collection("group_invitations").document(invitation_id).update(
                update_data
            )

            # If accepted, add user to group
            if accept:
                success = self.add_member_to_group(invitation["group_id"], user_id)
                if not success:
                    logger.error(
                        "Failed to add user %s to group after accepting invitation",
                        user_id,
                    )
                    return False

            logger.info(
                "Invitation %s %s by %s",
                invitation_id,
                "accepted" if accept else "rejected",
                user_id,
            )
            return True

        except Exception as e:
            logger.error("Error responding to invitation %s: %s", invitation_id, e)
            return False

    def get_user_invitations(self, user_id: str) -> List[Dict]:
        """Get pending invitations for a user"""
        try:
            # Get by user ID if user exists
            invitations_query = (
                self.db.collection("group_invitations")
                .where("invited_user", "==", user_id)
                .where("status", "==", InvitationStatus.PENDING.value)
            )

            invitations = []
            for doc in invitations_query.stream():
                invitation_data = doc.to_dict()
                invitation_data["invitation_id"] = doc.id

                # Check if expired
                expires_at = datetime.fromisoformat(invitation_data["expires_at"])
                if datetime.utcnow() <= expires_at:
                    # Get group details
                    group = self.get_group(invitation_data["group_id"])
                    if group:
                        invitation_data["group_name"] = group["name"]
                        invitation_data["group_destination"] = group.get("destination")

                    # Get inviter details
                    inviter = self.get_user(invitation_data["invited_by"])
                    if inviter:
                        invitation_data["inviter_name"] = inviter.get(
                            "display_name", inviter.get("email", "")
                        )

                    invitations.append(invitation_data)

            return invitations

        except Exception as e:
            logger.error("Error getting invitations for user %s: %s", user_id, e)
            return []

    def get_group_invitations(self, group_id: str) -> List[Dict]:
        """Get all invitations for a group"""
        try:
            invitations_query = self.db.collection("group_invitations").where(
                "group_id", "==", group_id
            )

            invitations = []
            for doc in invitations_query.stream():
                invitation_data = doc.to_dict()
                invitation_data["invitation_id"] = doc.id

                # Get inviter details
                inviter = self.get_user(invitation_data["invited_by"])
                if inviter:
                    invitation_data["inviter_name"] = inviter.get(
                        "display_name", inviter.get("email", "")
                    )

                invitations.append(invitation_data)

            # Sort by created_at (most recent first)
            invitations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return invitations

        except Exception as e:
            logger.error("Error getting invitations for group %s: %s", group_id, e)
            return []
