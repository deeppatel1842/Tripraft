# Purpose: Invitation Service for Group Planner Handles group invitations using unified SQL database (tripraft.db).
"""
Invitation Service for Group Planner
Handles group invitations using unified SQL database (tripraft.db)


"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.trips.models import GroupActivity, TravelGroup
from app.trips.models import TripInvitation as Invitation
from app.trips.models import TripMember
from app.auth.models import User
from app.core.db.connection import get_db_session

logger = logging.getLogger(__name__)

# Default invitation expiry (7 days)
DEFAULT_EXPIRY_DAYS = 7


class InvitationService:
    """Service for invitation operations using SQL database"""
    
    @staticmethod
    def create_invitation(
        group_id: str,
        invited_email: str,
        inviter_id: str,
        inviter_email: str = None,
        expires_days: int = DEFAULT_EXPIRY_DAYS
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a group invitation
        
        Args:
            group_id: Group ID
            invited_email: Email of person to invite
            inviter_id: User ID sending the invitation
            inviter_email: Email of inviter (optional)
            expires_days: Days until expiration
            
        Returns:
            Tuple of (success, invitation_data/error)
        """
        try:
            with get_db_session() as session:
                # Check inviter is a member
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == inviter_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get group
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Normalize email
                invited_email = invited_email.strip().lower()
                
                # Check if already a member
                existing_member = session.query(TripMember, User).join(
                    User, TripMember.user_id == User.id
                ).filter(
                    TripMember.group_id == group_id,
                    User.email == invited_email,
                    TripMember.is_active == True
                ).first()
                
                if existing_member:
                    return False, {'error': 'User is already a member of this group'}
                
                # Check for existing pending invitation
                existing_invitation = session.query(Invitation).filter(
                    Invitation.group_id == group_id,
                    Invitation.invitee_email == invited_email,
                    Invitation.status == 'pending'
                ).first()
                
                if existing_invitation:
                    # Update existing invitation (resend)
                    existing_invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
                    existing_invitation.created_at = datetime.now(timezone.utc)
                    existing_invitation.invited_by = inviter_id
                    session.commit()
                    session.refresh(existing_invitation)
                    
                    inviter = session.get(User, inviter_id)
                    return True, {
                        'invitation': existing_invitation.to_dict(),
                        'invitation_id': str(existing_invitation.id),
                        'group_name': group.name,
                        'invited_email': invited_email,
                        'invited_by_name': inviter.display_name if inviter else 'Unknown',
                    }
                
                # Check if invited user exists
                invited_user = session.query(User).filter(
                    User.email == invited_email
                ).first()
                
                # Create invitation
                invitation = Invitation(
                    group_id=group_id,
                    invitee_email=invited_email,
                    invitee_user_id=invited_user.id if invited_user else None,
                    invited_by=inviter_id,
                    status='pending',
                    expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days)
                )
                session.add(invitation)
                session.flush()
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=inviter_id,
                    action='invitation_sent',
                    entity_type='invitation',
                    entity_id=invitation.id,
                    details={'invited_email': invited_email}
                )
                session.add(activity)
                
                session.commit()
                session.refresh(invitation)
                
                logger.info(f"Invitation created: {invitation.id} to {invited_email}")
                
                # Build response with group name and inviter name
                inviter = session.get(User, inviter_id)
                
                return True, {
                    'invitation': invitation.to_dict(),
                    'invitation_id': str(invitation.id),
                    'group_name': group.name,
                    'invited_email': invited_email,
                    'invited_by_name': inviter.display_name if inviter else 'Unknown'
                }
                
        except Exception as e:
            logger.error(f"Create invitation error: {str(e)}")
            return False, {'error': 'Failed to create invitation'}
    
    @staticmethod
    def get_invitation(invitation_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get invitation details (public - for viewing invitation link)
        
        Args:
            invitation_id: Invitation ID
            
        Returns:
            Tuple of (success, invitation_data/error)
        """
        try:
            with get_db_session() as session:
                invitation = session.get(Invitation, invitation_id)
                
                if not invitation:
                    return False, {'error': 'Invitation not found'}
                
                return True, {'invitation': invitation.to_dict()}
                
        except Exception as e:
            logger.error(f"Get invitation error: {str(e)}")
            return False, {'error': 'Failed to get invitation'}
    
    @staticmethod
    def accept_invitation(
        invitation_id: str,
        user_id: str,
        user_email: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Accept a group invitation
        
        Args:
            invitation_id: Invitation ID
            user_id: User accepting
            user_email: User's email
            
        Returns:
            Tuple of (success, result/error)
        """
        try:
            with get_db_session() as session:
                invitation = session.get(Invitation, invitation_id)
                
                if not invitation:
                    return False, {'error': 'Invitation not found'}
                
                if invitation.status != 'pending':
                    return False, {'error': f'Invitation is {invitation.status}'}
                
                # Check expiration
                expires_at = invitation.expires_at
                if expires_at is not None and expires_at.tzinfo is None:
                    # SQLite returns timezone-naive UTC from DateTime
                    # columns, even when an aware datetime was stored.
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at and expires_at < datetime.now(timezone.utc):
                    invitation.status = 'expired'
                    session.commit()
                    return False, {'error': 'Invitation has expired'}
                
                # Verify email matches (case-insensitive)
                if not invitation.invitee_email or invitation.invitee_email.lower() != user_email.lower():
                    return False, {'error': 'This invitation is for a different email address'}
                
                # Check if already a member
                existing_member = session.query(TripMember).filter(
                    TripMember.group_id == invitation.group_id,
                    TripMember.user_id == user_id,
                ).first()
                
                if existing_member:
                    if existing_member.is_active:
                        # Already a member, mark invitation as accepted.
                        invitation.status = 'accepted'
                        invitation.responded_at = datetime.now(timezone.utc)
                        session.commit()
                        return True, {
                            'group_id': str(invitation.group_id),
                            'invitation_id': str(invitation_id),
                            'message': 'Already a member'
                        }
                    existing_member.is_active = True
                    existing_member.role = 'member'
                    existing_member.joined_at = datetime.now(timezone.utc)
                    existing_member.removed_at = None
                    existing_member.removed_by = None
                else:
                    member = TripMember(
                        group_id=invitation.group_id,
                        user_id=user_id,
                        role='member',
                        is_active=True
                    )
                    session.add(member)
                
                # Update invitation
                invitation.status = 'accepted'
                invitation.responded_at = datetime.now(timezone.utc)
                invitation.invitee_user_id = user_id
                
                # Update group timestamp
                group = session.get(TravelGroup, invitation.group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=invitation.group_id,
                    user_id=user_id,
                    action='member_joined',
                    entity_type='member',
                    entity_id=user_id,
                    details={'via_invitation': invitation_id}
                )
                session.add(activity)
                
                session.commit()
                
                logger.info(f"Invitation accepted: {invitation_id} by user {user_id}")
                
                # Notify group members about new member
                try:
                    from app.notifications.services.notification_service import \
                        notification_service
                    notification_service.notify_group_members(
                        group_id=invitation.group_id,
                        exclude_user_id=user_id,
                        type='member_joined',
                        title='A new member joined the group',
                        data={'user_id': user_id}
                    )
                except Exception:
                    pass
                
                # Real-time broadcast
                try:
                    from app.trips.realtime.events import \
                        emit_to_group
                    emit_to_group(invitation.group_id, 'member:joined', {'user_id': user_id})
                except Exception:
                    pass
                
                return True, {
                    'group_id': str(invitation.group_id),
                    'invitation_id': str(invitation_id)
                }
                
        except Exception as e:
            logger.error(f"Accept invitation error: {str(e)}")
            return False, {'error': 'Failed to accept invitation'}
    
    @staticmethod
    def decline_invitation(
        invitation_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Decline a group invitation
        
        Args:
            invitation_id: Invitation ID
            user_id: User declining
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                invitation = session.get(Invitation, invitation_id)
                
                if not invitation:
                    return False, {'error': 'Invitation not found'}
                
                if invitation.status != 'pending':
                    return False, {'error': f'Invitation is already {invitation.status}'}
                
                invitation.status = 'declined'
                invitation.responded_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Invitation declined: {invitation_id}")
                
                return True, {'message': 'Invitation declined'}
                
        except Exception as e:
            logger.error(f"Decline invitation error: {str(e)}")
            return False, {'error': 'Failed to decline invitation'}
    
    @staticmethod
    def get_user_invitations(
        user_email: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all invitations for a user (both received and sent)
        
        Args:
            user_email: User's email
            user_id: User's ID
            
        Returns:
            Tuple of (success, invitations_list/error)
        """
        try:
            with get_db_session() as session:
                user_email = user_email.strip().lower()
                
                # Get received invitations (pending)
                received = session.query(Invitation).filter(
                    Invitation.invitee_email == user_email,
                    Invitation.status == 'pending'
                ).all()
                
                # Get sent invitations (as inviter)
                sent = session.query(Invitation).filter(
                    Invitation.invited_by == user_id
                ).all()
                
                # Combine and deduplicate
                all_invitations = {}
                
                for inv in received:
                    all_invitations[inv.id] = {
                        **inv.to_dict(),
                        'type': 'received'
                    }
                
                for inv in sent:
                    if inv.id in all_invitations:
                        all_invitations[inv.id]['type'] = 'both'
                    else:
                        all_invitations[inv.id] = {
                            **inv.to_dict(),
                            'type': 'sent'
                        }
                
                return True, {'invitations': list(all_invitations.values())}
                
        except Exception as e:
            logger.error(f"Get user invitations error: {str(e)}")
            return False, {'error': 'Failed to get invitations'}
    
    @staticmethod
    def resend_invitation(
        invitation_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Resend an invitation (update timestamps)
        
        Args:
            invitation_id: Invitation ID
            user_id: User resending (must be inviter or group member)
            
        Returns:
            Tuple of (success, invitation_data/error)
        """
        try:
            with get_db_session() as session:
                invitation = session.get(Invitation, invitation_id)
                
                if not invitation:
                    return False, {'error': 'Invitation not found'}
                
                # Verify user is the inviter or a group member
                member = session.query(TripMember).filter(
                    TripMember.group_id == invitation.group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not authorized to resend this invitation'}
                
                # Update invitation
                invitation.created_at = datetime.now(timezone.utc)
                invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS)
                invitation.status = 'pending'
                invitation.responded_at = None
                
                session.commit()
                session.refresh(invitation)
                
                logger.info(f"Invitation resent: {invitation_id}")
                
                # Get inviter name
                inviter = session.get(User, invitation.invited_by)
                
                return True, {
                    'invitation': invitation.to_dict(),
                    'invited_email': invitation.invitee_email,
                    'invited_by_name': inviter.display_name if inviter else 'Unknown',
                    'group_name': invitation.group.name if invitation.group else 'Unknown'
                }
                
        except Exception as e:
            logger.error(f"Resend invitation error: {str(e)}")
            return False, {'error': 'Failed to resend invitation'}
    
    @staticmethod
    def cancel_invitation(
        invitation_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cancel a pending invitation
        
        Args:
            invitation_id: Invitation ID
            user_id: User cancelling (must be inviter or group admin)
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                invitation = session.get(Invitation, invitation_id)
                
                if not invitation:
                    return False, {'error': 'Invitation not found'}
                
                if invitation.status != 'pending':
                    return False, {'error': 'Only pending invitations can be cancelled'}
                
                # Verify user is the inviter or group admin/creator
                if invitation.invited_by != user_id:
                    member = session.query(TripMember).filter(
                        TripMember.group_id == invitation.group_id,
                        TripMember.user_id == user_id,
                        TripMember.is_active == True,
                        TripMember.role.in_(['admin', 'creator'])
                    ).first()
                    
                    if not member:
                        return False, {'error': 'Not authorized to cancel this invitation'}
                
                # Delete invitation
                session.delete(invitation)
                session.commit()
                
                logger.info(f"Invitation cancelled: {invitation_id}")
                
                return True, {'message': 'Invitation cancelled'}
                
        except Exception as e:
            logger.error(f"Cancel invitation error: {str(e)}")
            return False, {'error': 'Failed to cancel invitation'}

    @staticmethod
    def get_group_pending_invitations(group_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all pending invitations for a specific group
        
        Args:
            group_id: Group ID
            
        Returns:
            Tuple of (success, invitations_list/error)
        """
        try:
            with get_db_session() as session:
                group = session.get(TravelGroup, group_id)
                if not group:
                    return False, {'error': 'Group not found'}
                
                # Get all pending invitations for this group
                invitations = session.query(Invitation).filter(
                    Invitation.group_id == group_id,
                    Invitation.status == 'pending'
                ).order_by(Invitation.created_at.desc()).all()
                
                invitations_list = [inv.to_dict() for inv in invitations]
                
                logger.info(f"Fetched {len(invitations_list)} pending invitations for group {group_id}")
                
                return True, {'invitations': invitations_list}
                
        except Exception as e:
            logger.error(f"Get group pending invitations error: {str(e)}")
            return False, {'error': 'Failed to get group invitations'}


# Singleton instance
invitation_service = InvitationService()
invitation_service = InvitationService()
invitation_service = InvitationService()
invitation_service = InvitationService()
