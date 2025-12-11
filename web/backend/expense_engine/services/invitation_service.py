"""
Invitation Service
Business logic for invitation management

Phase 19.2: Added EmailLookupRepository for fast email -> userId lookups
Phase 20: Added SnapshotRepository for bootstrap snapshot updates
Phase 20.1: JWT-like invitation tokens to eliminate lookup reads
Phase 20.2: Combined validation queries for reduced Firestore ops
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from ..repositories import InvitationRepository, GroupRepository, EmailLookupRepository, SnapshotRepository
from ..repositories.user_repository import UserRepository
from ..models.invitation import Invitation
from ..config import business_rules
from ..exceptions import (
    ValidationError,
    ResourceNotFoundError,
    MaxMembersReachedError,
    DuplicateEntryError
)

# Phase 20.1: Import invitation token utilities
try:
    from ..utils.invitation_token import (
        create_invitation_token,
        decode_invitation_token,
        TokenExpiredError,
        TokenInvalidError
    )
    TOKENS_ENABLED = True
except ImportError:
    TOKENS_ENABLED = False

# Cache configuration
try:
    from ..utils.cache_manager import get_cache_manager
    from ..config import redis_config
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


class InvitationService:
    """
    Service for invitation management operations
    Handles invitation lifecycle
    
    Phase 19.2: Uses EmailLookupRepository for O(1) email lookups
    """
    
    def __init__(
        self,
        invitation_repo: Optional[InvitationRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        email_lookup_repo: Optional[EmailLookupRepository] = None,
        snapshot_repo: Optional[SnapshotRepository] = None
    ):
        """
        Initialize service
        
        Args:
            invitation_repo: Invitation repository instance (optional)
            group_repo: Group repository instance (optional)
            email_lookup_repo: Email lookup repository instance (optional, Phase 19.2)
            snapshot_repo: Snapshot repository instance (optional, Phase 20)
        """
        # pylint: disable=no-value-for-parameter
        self.invitation_repo = invitation_repo or InvitationRepository()
        self.group_repo = group_repo or GroupRepository()
        # Lazy-load to avoid Firebase initialization in tests
        self._email_lookup_repo = email_lookup_repo
        self._snapshot_repo = snapshot_repo
    
    @property
    def email_lookup_repo(self) -> EmailLookupRepository:
        """Lazy-load email lookup repository"""
        if self._email_lookup_repo is None:
            self._email_lookup_repo = EmailLookupRepository()
        return self._email_lookup_repo
    
    @property
    def snapshot_repo(self) -> SnapshotRepository:
        """Lazy-load snapshot repository"""
        if self._snapshot_repo is None:
            self._snapshot_repo = SnapshotRepository()
        return self._snapshot_repo
    
    def _get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Phase 19.2: Get user by email using fast lookup.
        
        Tries email lookup collection first (O(1)), falls back to query.
        
        Args:
            email: User email address
            
        Returns:
            User dict with id/uid, display_name, photo_url or None
        """
        # Try fast lookup first
        lookup_result = self.email_lookup_repo.get_user_by_email(email)
        if lookup_result:
            # Return in same format as UserRepository.get_user_by_email
            return {
                'id': lookup_result.get('user_id'),
                'uid': lookup_result.get('user_id'),
                'display_name': lookup_result.get('display_name'),
                'photo_url': lookup_result.get('photo_url'),
                'email': email
            }
        
        # Fallback to query (for users not yet in lookup collection)
        user_repo = UserRepository()
        user = user_repo.get_user_by_email(email)
        
        # If found via query, populate the lookup collection for next time
        if user:
            user_id = user.get('uid') or user.get('id')
            if user_id:
                self.email_lookup_repo.set_user_email(
                    email=email,
                    user_id=user_id,
                    display_name=user.get('display_name'),
                    photo_url=user.get('photo_url')
                )
                logger.info("Populated email lookup for %s (fallback)", email)
        
        return user
    
    def _invalidate_membership_cache(self, group_id: str, user_id: str, group_data: Dict = None) -> None:
        """
        Invalidate cache entries when membership changes
        
        Phase 19: Accept optional pre-fetched group_data to avoid re-reading
        
        Args:
            group_id: Group ID
            user_id: User ID whose membership changed
            group_data: Optional pre-fetched group data (avoids 1 read)
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
                
                # Phase 17 Bug Fix: Invalidate mega-bootstrap cache for the new member
                # Both with and without group_id (dashboard vs group view)
                cache.delete(f"expense:mega_bootstrap:{user_id}")  # Dashboard view
                cache.delete(f"expense:mega_bootstrap:{user_id}:{group_id}")  # Group view
                
                # Phase 17 Bug Fix: Invalidate mega-bootstrap cache for ALL existing group members
                # Phase 19: Use pre-fetched group_data if available to avoid re-read
                if group_data is None:
                    group_data = self.group_repo.get_by_id(group_id)
                if group_data:
                    # members is a list of user_id strings
                    members = group_data.get('members', [])
                    for member_id in members:
                        if member_id and isinstance(member_id, str) and member_id != user_id:
                            cache.delete(f"expense:mega_bootstrap:{member_id}")  # Dashboard
                            cache.delete(f"expense:mega_bootstrap:{member_id}:{group_id}")  # Group view
                            logger.debug("Invalidated mega-bootstrap cache for member %s", member_id)
                
                logger.info("Cache invalidated for membership change: %s/%s", group_id, user_id)
        except Exception as e:
            logger.warning("Failed to invalidate cache: %s", e)
    
    def _invalidate_invitation_cache(self, group_id: str, invitee_email: str) -> None:
        """
        Invalidate invitation cache entries when invitations change
        Phase 13: New method for cache invalidation
        Phase 17.9: Only invalidate INVITEE's cache (not group members)
        
        Args:
            group_id: Group ID
            invitee_email: Email of invitee
        """
        if not CACHE_ENABLED:
            return
        try:
            cache = get_cache_manager()
            if cache and cache.is_available():
                # Invalidate user invitations cache
                cache.delete(redis_config.KEY_USER_INVITES.format(email=invitee_email))
                # Invalidate group invitations cache
                cache.delete(redis_config.KEY_GROUP_INVITES.format(gid=group_id))
                
                # Phase 17.9: DO NOT invalidate mega-bootstrap for existing group members
                # They receive real-time updates via Firestore listenToGroupInvitations
                # This eliminates unnecessary API call cascade
                
                # Phase 19.2: Use fast email lookup instead of query
                # The invitee is not a group member yet, so they don't have a Firestore listener
                # They need their cache invalidated to see the new invitation
                invitee = self._get_user_by_email(invitee_email)
                if invitee:
                    invitee_id = invitee.get('id') or invitee.get('uid')
                    if invitee_id:
                        cache.delete(f"expense:mega_bootstrap:{invitee_id}")  # Dashboard
                        logger.info("Mega-bootstrap cache invalidated for invitee %s (%s)", invitee_id, invitee_email)
                
                logger.info("Invitation cache invalidated: group=%s, email=%s (invitee only)", group_id, invitee_email)
        except Exception as e:
            logger.warning("Failed to invalidate invitation cache: %s", e)
    
    def create_invitation(
        self,
        group_id: str,
        invitee_email: str,
        invited_by: str,
        role: str = 'member'
    ) -> Dict:
        """
        Create a new invitation
        
        Args:
            group_id: Group ID
            invitee_email: Email of person to invite
            invited_by: User ID who is inviting
            role: Role to assign (admin/member)
            
        Returns:
            Created invitation document
        """
        try:
            # Phase 17.5: Normalize email to lowercase for consistent lookups
            invitee_email = invitee_email.strip().lower()
            
            # Validate group exists
            group_data = self.group_repo.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Check max members limit
            member_count = len(group_data.get('members', []))
            if member_count >= business_rules.MAX_GROUP_MEMBERS:
                raise MaxMembersReachedError(
                    group_id,
                    business_rules.MAX_GROUP_MEMBERS
                )
            
            # Validate role
            if role not in ['admin', 'member']:
                raise ValidationError(f"Invalid role: {role}")
            
            # Check if invitation already exists
            existing = self.invitation_repo.get_pending_invitations(
                email=invitee_email,
                group_id=group_id
            )
            
            if existing:
                raise ValidationError(
                    f"Invitation already exists for {invitee_email} in this group"
                )
            
            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(
                days=business_rules.INVITATION_EXPIRY_DAYS
            )
            
            # Get inviter details for enrichment
            user_repo = UserRepository()
            inviter = user_repo.get_by_id(invited_by)
            inviter_name = inviter.get('display_name') or inviter.get('email', 'Someone') if inviter else 'Someone'
            
            # Generate document ID first
            doc_ref = self.invitation_repo.get_collection().document()
            invitation_id = doc_ref.id
            
            # Create invitation model with enrichment
            invitation = Invitation(
                invitation_id=invitation_id,  # Set ID in model
                group_id=group_id,
                group_name=group_data.get('name'),  # Enrich with group name
                email=invitee_email,
                invited_by=invited_by,
                invited_by_name=inviter_name,  # Enrich with inviter name
                expires_at=expires_at
            )
            
            # Create invitation in Firestore
            self.invitation_repo.create(invitation_id, invitation.to_dict())
            
            # Phase 13: Invalidate invitation caches
            self._invalidate_invitation_cache(group_id, invitee_email)
            
            # Phase 20: Update invitation count in snapshots
            try:
                self.snapshot_repo.update_invitation_count(group_id, delta=1)
            except Exception as snapshot_exc:
                logger.warning("Failed to update snapshots for invitation: %s", snapshot_exc)
            
            logger.info(
                "Created invitation %s for %s to group %s (%s)",
                invitation_id, invitee_email, group_id, group_data.get('name')
            )
            
            # Phase 20.1: Generate invitation token (contains all data needed to accept)
            invitation_token = None
            if TOKENS_ENABLED:
                try:
                    invitation_token = create_invitation_token(
                        invitation_id=invitation_id,
                        group_id=group_id,
                        group_name=group_data.get('name', ''),
                        inviter_id=invited_by,
                        inviter_name=inviter_name,
                        invitee_email=invitee_email,
                        role=role,
                        expiry_days=business_rules.INVITATION_EXPIRY_DAYS
                    )
                    logger.debug("[TOKEN] Generated token for invitation %s", invitation_id)
                except Exception as token_exc:
                    logger.warning("Failed to generate invitation token: %s", token_exc)
            
            # Send email notification asynchronously (with token if available)
            self._send_invitation_email(
                invitation_id=invitation_id,
                invitee_email=invitee_email,
                inviter_name=inviter_name,
                group_name=group_data.get('name'),
                invitation_token=invitation_token
            )
            
            # Build response (no re-read needed - use data we already have)
            # Phase 20.2: Eliminate final get_by_id read
            response = {
                'invitation_id': invitation_id,
                'id': invitation_id,
                'group_id': group_id,
                'group_name': group_data.get('name'),
                'email': invitee_email,
                'invited_email': invitee_email,
                'invited_by': invited_by,
                'invited_by_name': inviter_name,
                'status': 'pending',
                'role': role,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Include token in response if generated
            if invitation_token:
                response['token'] = invitation_token
            
            return response
            
        except Exception as exc:
            logger.error("Error creating invitation: %s", str(exc))
            raise
    
    def _send_invitation_email(
        self,
        invitation_id: str,
        invitee_email: str,
        inviter_name: str,
        group_name: str,
        invitation_token: str = None
    ) -> None:
        """
        Send invitation email asynchronously
        
        Phase 20.1: Include token in invitation link for zero-read acceptance
        """
        try:
            # Import email config and worker
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from email_config import email_config
            
            # Check if invitation emails are enabled
            if not email_config.is_enabled('invitation'):
                logger.info("Invitation emails disabled - skipping email for %s", invitee_email)
                return
            
            # Import email worker
            from ..workers import get_email_worker
            email_worker = get_email_worker()
            
            # Generate invitation link
            # Phase 20.1: Use token-based link if token is available
            import os
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
            if invitation_token:
                # Token contains all data - accept endpoint can skip invitation lookup
                invitation_link = f"{frontend_url}/accept-invitation?token={invitation_token}&type=expense"
            else:
                # Fallback to ID-based link
                invitation_link = f"{frontend_url}/accept-invitation?id={invitation_id}&type=expense"
            
            # Queue email (use 'invitation_sent' type as expected by email_worker)
            email_worker.queue_email(
                email_type='invitation_sent',
                recipients=[invitee_email],
                data={
                    'inviter_name': inviter_name,
                    'group_name': group_name,
                    'invitation_link': invitation_link
                }
            )
            logger.info("Invitation email queued for %s", invitee_email)
            
        except (OSError, RuntimeError) as e:
            # Email failures should not break invitation creation
            logger.error("Failed to send invitation email: %s", e)
    
    def get_invitation(self, invitation_id: str) -> Optional[Dict]:
        """
        Get invitation by ID
        
        Args:
            invitation_id: Invitation ID
            
        Returns:
            Invitation document or None
        """
        return self.invitation_repo.get_by_id(invitation_id)
    
    def get_user_invitations(
        self,
        email: str,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get invitations for a user with Redis caching (TTL=60s)
        Phase 13: Added caching for performance optimization
        
        Args:
            email: User email
            status: Optional status filter
            
        Returns:
            List of invitation documents
        """
        # Only cache when no status filter (most common case)
        cache_key = None
        if CACHE_ENABLED and status is None:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_USER_INVITES.format(email=email)
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug("[CACHE][+] User invitations cache hit: %s", email)
                    return cached
        
        # Fetch from Firestore
        invitations = self.invitation_repo.get_user_invitations(email, status=status)
        # Transform 'id' to 'invitation_id' for frontend compatibility
        for invitation in invitations:
            if 'id' in invitation and 'invitation_id' not in invitation:
                invitation['invitation_id'] = invitation['id']
        
        # Cache result if no status filter
        if cache_key:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, invitations, ttl=redis_config.TTL_USER_INVITES)
                logger.debug("[CACHE][-] User invitations cached: %s", email)
        
        return invitations
    
    def get_group_invitations(
        self,
        group_id: str,
        status: Optional[str] = None,
        include_all: bool = False
    ) -> List[Dict]:
        """
        Get invitations for a group with Redis caching (TTL=60s)
        Phase 13: Added caching for performance optimization
        Phase 17: Added include_all parameter for mega-bootstrap
        
        Args:
            group_id: Group ID
            status: Optional status filter
            include_all: If True, return all statuses (overrides status filter)
            
        Returns:
            List of invitation documents
        """
        # If include_all is True, ignore status filter and get all invitations
        effective_status = None if include_all else status
        
        # Only cache when no status filter (most common case)
        cache_key = None
        if CACHE_ENABLED and effective_status is None:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_GROUP_INVITES.format(gid=group_id)
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug("[CACHE][+] Group invitations cache hit: %s", group_id)
                    return cached
        
        # Fetch from Firestore
        invitations = self.invitation_repo.get_group_invitations(group_id, status=effective_status)
        # Transform 'id' to 'invitation_id' for frontend compatibility
        for invitation in invitations:
            if 'id' in invitation and 'invitation_id' not in invitation:
                invitation['invitation_id'] = invitation['id']
        
        # Cache result if no status filter
        if cache_key:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, invitations, ttl=redis_config.TTL_GROUP_INVITES)
                logger.debug("[CACHE][-] Group invitations cached: %s", group_id)
        
        return invitations
    
    def accept_invitation(
        self,
        invitation_id: str,
        accepted_by_user_id: str,
        invitation_token: str = None
    ) -> Dict:
        """
        Accept an invitation and add user to the group
        
        Phase 19.5: Ultra-optimized to achieve ≤10 Firestore ops
        Phase 20.1: Token-based acceptance eliminates invitation read
        
        With token: 0R (invitation) + 1R (user) + 1R (group via add_member) + 3W = 5 ops
        Without token: 1R (invitation) + 1R (user) + 1R (group via add_member) + 3W = 6 ops
        
        Args:
            invitation_id: Invitation ID (can be extracted from token)
            accepted_by_user_id: User ID who accepted
            invitation_token: Optional JWT token (Phase 20.1)
            
        Returns:
            Group data dict with group details
        """
        try:
            invitation_data = None
            group_id = None
            invitee_email = ''
            group_name = ''
            
            # Phase 20.1: Try token-based acceptance first (0 reads for invitation data)
            if invitation_token and TOKENS_ENABLED:
                try:
                    token_data = decode_invitation_token(invitation_token)
                    invitation_id = token_data['invitation_id']
                    group_id = token_data['group_id']
                    group_name = token_data['group_name']
                    invitee_email = token_data['invitee_email']
                    
                    # Build pseudo invitation_data from token (no Firestore read!)
                    invitation_data = {
                        'id': invitation_id,
                        'group_id': group_id,
                        'group_name': group_name,
                        'email': invitee_email,
                        'invited_by': token_data['inviter_id'],
                        'invited_by_name': token_data['inviter_name'],
                        'role': token_data['role'],
                        'status': 'pending'  # Assumed - will be updated
                    }
                    logger.info("[TOKEN] Accepting invitation via token (0 reads)")
                    
                except TokenExpiredError:
                    logger.warning("[TOKEN] Token expired, falling back to Firestore read")
                    invitation_token = None  # Fall through to normal path
                except TokenInvalidError as e:
                    logger.warning("[TOKEN] Invalid token: %s, falling back to Firestore read", e)
                    invitation_token = None  # Fall through to normal path
            
            # Fallback: Read invitation from Firestore (1R)
            if invitation_data is None:
                invitation_data = self.invitation_repo.get_by_id(invitation_id)
                if not invitation_data:
                    raise ResourceNotFoundError(f"Invitation {invitation_id} not found")
                
                group_id = invitation_data.get('group_id')
                invitee_email = invitation_data.get('email', '')
                group_name = invitation_data.get('group_name', '')
            
            if not group_id:
                raise ValidationError("Invitation has no associated group")
            
            # 1W: Update invitation status (no read - pass pre-fetched data)
            self.invitation_repo.accept_invitation(
                invitation_id,
                accepted_by_user_id,
                invitation_data=invitation_data
            )
            
            # 1R: Get user details for display name
            user_repo = UserRepository()
            user_data = user_repo.get_by_id(accepted_by_user_id)
            display_name = 'Unknown User'
            if user_data:
                display_name = user_data.get('display_name') or user_data.get('email', 'Unknown User')
            
            # 1R + 1W: Add user to group (reads group, writes member)
            # Phase 19.5: add_member now returns group_data to avoid re-read
            group_data = self.group_repo.add_member(
                group_id=group_id,
                user_id=accepted_by_user_id,
                display_name=display_name,
                return_group_data=True  # Phase 19.5: Return group data to avoid re-read
            )
            
            # Cache invalidation (no Firestore ops - Redis only)
            # Phase 19.5: Pass group_data to avoid ANY re-reads
            self._invalidate_membership_cache(group_id, accepted_by_user_id, group_data=group_data)
            self._invalidate_invitation_cache(group_id, invitee_email)
            
            # 1R + 1W: Create minimal snapshot for new member
            # Phase 19.5: Use lightweight snapshot creation (no full rebuild)
            try:
                self._create_minimal_snapshot_for_new_member(
                    user_id=accepted_by_user_id,
                    group_id=group_id,
                    group_data=group_data,
                    display_name=display_name
                )
            except Exception as snapshot_exc:
                logger.warning("Failed to create snapshot: %s", snapshot_exc)
            
            logger.info(
                "Accepted invitation %s - added user %s to group %s%s",
                invitation_id, accepted_by_user_id, group_id,
                " (via token)" if invitation_token else ""
            )
            
            # Return group data (already fetched)
            if group_data:
                group_data['group_id'] = group_id
            else:
                group_data = {'group_id': group_id, 'name': group_name}
            return group_data
            
        except Exception as exc:
            logger.error("Error accepting invitation: %s", str(exc))
            raise
    
    def _create_minimal_snapshot_for_new_member(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict,
        display_name: str
    ) -> None:
        """
        Phase 19.5: Create minimal snapshot without full data rebuild.
        
        Instead of reading expenses/balances/invitations for snapshot,
        create a skeleton snapshot. It will be populated on first
        mega-bootstrap call (which will happen immediately anyway).
        
        This reduces snapshot creation from 5+ reads to 1 write.
        A new member's balance always starts at 0, so no need to read balances.
        
        Args:
            user_id: New member's user ID
            group_id: Group ID
            group_data: Pre-fetched group data
            display_name: User's display name
        """
        try:
            members_list = group_data.get('members', []) if group_data else [user_id]
            
            # Build minimal group info from pre-fetched data
            group_info = {
                'name': group_data.get('name', 'Unknown Group') if group_data else 'Unknown Group',
                'currency': group_data.get('currency', 'USD') if group_data else 'USD',
                'memberCount': len(members_list)
            }
            
            # Phase 19.5: New member's balance is ALWAYS 0 - no need to read!
            # Other members' balances don't change when someone joins
            balances = {user_id: 0.0}
            
            # Build minimal members list (only current user for now)
            members = [{
                'userId': user_id,
                'displayName': display_name,
                'photoURL': ''
            }]
            
            # 1W: Create minimal snapshot (no reads needed!)
            self.snapshot_repo.create_snapshot(
                user_id=user_id,
                group_id=group_id,
                group_info=group_info,
                members=members,
                balances=balances,
                recent_expenses=[],  # Will be populated on first mega-bootstrap
                pending_invitations_count=0,
                total_expenses=0,
                expense_count=0
            )
            
            logger.debug("Created minimal snapshot for new member %s in group %s", user_id, group_id)
            
        except Exception as exc:
            logger.warning("Failed to create minimal snapshot: %s", exc)
    
    def decline_invitation(
        self,
        invitation_id: str,
        declined_by_user_id: str
    ) -> None:
        """
        Decline an invitation
        
        Args:
            invitation_id: Invitation ID
            declined_by_user_id: User ID who declined
        """
        try:
            # Get invitation details for cache invalidation
            invitation_data = self.invitation_repo.get_by_id(invitation_id)
            
            self.invitation_repo.decline_invitation(
                invitation_id,
                declined_by_user_id
            )
            
            # Phase 13: Invalidate invitation caches
            if invitation_data:
                group_id = invitation_data.get('group_id', '')
                invitee_email = invitation_data.get('email', '')
                self._invalidate_invitation_cache(group_id, invitee_email)
                
                # Phase 20: Update invitation count in snapshots
                try:
                    self.snapshot_repo.update_invitation_count(group_id, delta=-1)
                except Exception as snapshot_exc:
                    logger.warning("Failed to update snapshots for declined invitation: %s", snapshot_exc)
            
            logger.info(
                "Declined invitation %s by %s",
                invitation_id, declined_by_user_id
            )
            
        except Exception as exc:
            logger.error("Error declining invitation: %s", str(exc))
            raise
    
    def revoke_invitation(
        self,
        invitation_id: str,
        revoked_by_user_id: str
    ) -> None:
        """
        Revoke an invitation (admin action)
        
        Args:
            invitation_id: Invitation ID
            revoked_by_user_id: User ID who revoked
        """
        try:
            self.invitation_repo.revoke_invitation(
                invitation_id,
                revoked_by_user_id
            )
            
            logger.info(
                "Revoked invitation %s by %s",
                invitation_id, revoked_by_user_id
            )
            
        except Exception as exc:
            logger.error("Error revoking invitation: %s", str(exc))
            raise
    
    def resend_invitation(
        self,
        invitation_id: str,
        resent_by_user_id: str
    ) -> Dict:
        """
        Resend an invitation with new expiry
        
        Args:
            invitation_id: Invitation ID
            resent_by_user_id: User ID who resent
            
        Returns:
            Updated invitation document
        """
        try:
            invitation_data = self.invitation_repo.resend_invitation(
                invitation_id,
                resent_by_user_id
            )
            
            logger.info(
                "Resent invitation %s by %s",
                invitation_id, resent_by_user_id
            )
            
            return invitation_data
            
        except Exception as exc:
            logger.error("Error resending invitation: %s", str(exc))
            raise
    
    def expire_old_invitations(self) -> int:
        """
        Mark expired invitations as expired
        Should be run periodically (cron job)
        
        Returns:
            Number of invitations expired
        """
        try:
            count = self.invitation_repo.expire_old_invitations()
            
            if count > 0:
                logger.info("Expired %d invitations", count)
            
            return count
            
        except Exception as exc:
            logger.error("Error expiring invitations: %s", str(exc))
            raise
