"""
Invitation Repository
Handles invitation data access and status management
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from google.cloud.firestore import Increment
import logging

from .base import BaseRepository
from ..config import firestore_collections, business_rules
from ..models.invitation import Invitation
from ..exceptions import ResourceNotFoundError, ValidationError as CustomValidationError

logger = logging.getLogger(__name__)


class InvitationRepository(BaseRepository[Invitation]):
    """
    Repository for invitation management
    Handles invitation CRUD and status tracking
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.INVITATIONS
    
    def get_group_invitations(
        self,
        group_id: str,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get invitations for a group
        
        Args:
            group_id: Group ID
            status: Optional status filter (pending/accepted/declined/expired)
            
        Returns:
            List of invitation documents
        """
        try:
            filters = [('group_id', '==', group_id)]
            if status:
                filters.append(('status', '==', status))
            
            # Note: Removed order_by to avoid composite index requirement
            # Sort in Python instead
            invitations = self.query(filters=filters)
            
            # Sort by created_at descending in Python
            invitations.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Add invited_email alias for frontend compatibility
            for inv in invitations:
                if 'email' in inv and 'invited_email' not in inv:
                    inv['invited_email'] = inv['email']
            
            return invitations
            
        except Exception as exc:
            logger.error("Error getting group invitations: %s", str(exc))
            raise
    
    def get_user_invitations(
        self,
        email: str,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get invitations for a user by email
        
        Args:
            email: User email
            status: Optional status filter
            
        Returns:
            List of invitation documents
        """
        try:
            # Phase 17.5: Normalize email to lowercase
            email = email.strip().lower() if email else ''
            
            # Query by 'email' field (not 'invitee_email')
            filters = [('email', '==', email)]
            if status:
                filters.append(('status', '==', status))
            
            # Note: Removed order_by to avoid composite index requirement
            invitations = self.query(filters=filters)
            
            # Phase 17.5: Filter out expired invitations when status is 'pending'
            if status == 'pending':
                now = datetime.utcnow()
                valid_invitations = []
                for inv in invitations:
                    expires_at = inv.get('expires_at')
                    # Handle both datetime objects and ISO format strings
                    if expires_at is None:
                        valid_invitations.append(inv)  # No expiry means valid
                    elif isinstance(expires_at, datetime):
                        if expires_at > now:
                            valid_invitations.append(inv)
                    elif isinstance(expires_at, str):
                        try:
                            # Parse ISO format string
                            exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            # Make naive for comparison if needed
                            if exp_dt.tzinfo is not None:
                                exp_dt = exp_dt.replace(tzinfo=None)
                            if exp_dt > now:
                                valid_invitations.append(inv)
                        except (ValueError, TypeError):
                            valid_invitations.append(inv)  # Invalid date, keep it
                    else:
                        valid_invitations.append(inv)  # Unknown type, keep it
                invitations = valid_invitations
            
            # Sort by created_at descending in Python
            invitations.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Add invited_email alias for frontend compatibility
            for inv in invitations:
                if 'email' in inv and 'invited_email' not in inv:
                    inv['invited_email'] = inv['email']
            
            return invitations
            
        except Exception as exc:
            logger.error("Error getting user invitations: %s", str(exc))
            raise
    
    def get_pending_invitations(
        self,
        email: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get pending invitations with optional filters
        
        Args:
            email: Optional email filter
            group_id: Optional group filter
            
        Returns:
            List of pending invitation documents
        """
        try:
            filters = [
                ('status', '==', 'pending'),
                ('expires_at', '>', datetime.utcnow())
            ]
            
            if email:
                filters.append(('email', '==', email))  # Field is 'email' not 'invitee_email'
            if group_id:
                filters.append(('group_id', '==', group_id))
            
            # Note: Removed order_by to avoid composite index requirement
            invitations = self.query(filters=filters)
            
            # Sort by created_at descending in Python
            invitations.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Add invited_email alias for frontend compatibility
            for inv in invitations:
                if 'email' in inv and 'invited_email' not in inv:
                    inv['invited_email'] = inv['email']
            
            return invitations
            
        except Exception as exc:
            logger.error("Error getting pending invitations: %s", str(exc))
            raise
    
    def accept_invitation(
        self,
        invitation_id: str,
        accepted_by_user_id: str,
        invitation_data: Dict = None  # Phase 19: Optional pre-fetched data
    ) -> Dict:
        """
        Accept an invitation
        
        Phase 19 Optimization: Accept pre-fetched invitation_data to avoid duplicate reads
        
        Args:
            invitation_id: Invitation ID
            accepted_by_user_id: User ID who accepted
            invitation_data: Optional pre-fetched invitation data (avoids 1 read)
            
        Returns:
            Updated invitation document
        """
        try:
            # Phase 19: Use pre-fetched data if provided, otherwise fetch
            if invitation_data is None:
                invitation_data = self.get_by_id(invitation_id)
            if not invitation_data:
                raise ResourceNotFoundError(f"Invitation {invitation_id} not found")
            
            # Validate invitation
            if invitation_data['status'] != 'pending':
                raise CustomValidationError(
                    f"Cannot accept invitation with status: {invitation_data['status']}"
                )
            
            # Handle expires_at - could be string, datetime, or Firestore timestamp
            expires_at = invitation_data['expires_at']
            if isinstance(expires_at, str):
                # Parse ISO format string and make it naive UTC
                try:
                    parsed_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    # Convert to naive UTC if timezone-aware
                    expires_at = parsed_dt.replace(tzinfo=None) if parsed_dt.tzinfo else parsed_dt
                except (ValueError, AttributeError) as exc:
                    # If parsing fails, treat as expired
                    logger.warning("Could not parse expires_at: %s", expires_at)
                    self.update(invitation_id, {'status': 'expired'})
                    raise CustomValidationError("Invalid invitation expiry date") from exc
            elif hasattr(expires_at, 'timestamp'):
                # Handle Firestore timestamp (has timestamp() method)
                expires_at = datetime.utcfromtimestamp(expires_at.timestamp())
            elif isinstance(expires_at, datetime):
                # Already datetime - ensure it's naive UTC
                expires_at = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
            
            # Check expiry (both are now naive UTC)
            if expires_at < datetime.utcnow():
                self.update(invitation_id, {'status': 'expired'})
                raise CustomValidationError("Invitation has expired")
            
            # Update invitation
            self.update(invitation_id, {
                'status': 'accepted',
                'accepted_at': datetime.utcnow(),
                'accepted_by': accepted_by_user_id
            })
            
            logger.info("Accepted invitation %s", invitation_id)
            
            # Phase 19: Return updated data without extra read
            # Construct updated response from what we know
            updated_data = dict(invitation_data)
            updated_data['status'] = 'accepted'
            updated_data['accepted_by'] = accepted_by_user_id
            return updated_data
            
        except Exception as exc:
            logger.error("Error accepting invitation: %s", str(exc))
            raise
    
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
            invitation_data = self.get_by_id(invitation_id)
            if not invitation_data:
                raise ResourceNotFoundError(f"Invitation {invitation_id} not found")
            
            if invitation_data['status'] != 'pending':
                raise CustomValidationError(
                    f"Cannot decline invitation with status: {invitation_data['status']}"
                )
            
            self.update(invitation_id, {
                'status': 'declined',
                'declined_at': datetime.utcnow(),
                'declined_by': declined_by_user_id
            })
            
            logger.info("Declined invitation %s", invitation_id)
            
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
            invitation_data = self.get_by_id(invitation_id)
            if not invitation_data:
                raise ResourceNotFoundError(f"Invitation {invitation_id} not found")
            
            self.update(invitation_id, {
                'status': 'revoked',
                'revoked_at': datetime.utcnow(),
                'revoked_by': revoked_by_user_id
            })
            
            logger.info("Revoked invitation %s", invitation_id)
            
        except Exception as exc:
            logger.error("Error revoking invitation: %s", str(exc))
            raise
    
    def expire_old_invitations(self) -> int:
        """
        Mark expired invitations as expired
        Should be run periodically
        
        Returns:
            Number of invitations expired
        """
        try:
            expired_invitations = self.query(
                filters=[
                    ('status', '==', 'pending'),
                    ('expires_at', '<', datetime.utcnow())
                ]
            )
            
            count = 0
            for invitation in expired_invitations:
                self.update(invitation['id'], {'status': 'expired'})
                count += 1
            
            if count > 0:
                logger.info("Expired %d invitations", count)
            
            return count
            
        except Exception as exc:
            logger.error("Error expiring invitations: %s", str(exc))
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
            invitation_data = self.get_by_id(invitation_id)
            if not invitation_data:
                raise ResourceNotFoundError(f"Invitation {invitation_id} not found")
            
            # Reset expiry
            new_expiry = datetime.utcnow() + timedelta(
                days=business_rules.INVITATION_EXPIRY_DAYS
            )
            
            self.update(invitation_id, {
                'status': 'pending',
                'expires_at': new_expiry,
                'resent_at': datetime.utcnow(),
                'resent_by': resent_by_user_id,
                'resend_count': Increment(1)
            })
            
            logger.info("Resent invitation %s", invitation_id)
            
            return self.get_by_id(invitation_id)
            
        except Exception as exc:
            logger.error("Error resending invitation: %s", str(exc))
            raise
