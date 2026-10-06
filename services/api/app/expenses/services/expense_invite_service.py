# Purpose: SQL-based Invitation Service Handles group invitations using local SQL database.
"""
SQL-based Invitation Service
Handles group invitations using local SQL database
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple

from app.core.config import Config
from app.expenses.models import (Group, GroupBalance, GroupMember,
                                        Invitation, User)
from app.core.db.connection import get_db, get_db_session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class InvitationServiceSQL:
    """Service for managing group invitations"""
    
    # Invitation expiry in days
    INVITATION_EXPIRY_DAYS = Config.INVITATION_EXPIRY_DAYS
    
    @staticmethod
    def _send_invitation_email(invitee_email: str, inviter_name: str, group_name: str, invitation_id: str) -> str:
        """
        Dispatch invitation email via Celery for async delivery.
        Falls back to synchronous send if Celery is unavailable.
        
        Returns:
            Email status: 'queued', 'sent', 'disabled', or 'failed'
        """
        try:
            from .email_service import email_service
            
            if not email_service.enabled:
                logger.info(f"Email service disabled - skipping invitation email to {invitee_email}")
                return 'disabled'
            
            # Dispatch via Celery (non-blocking)
            try:
                from app.core.workers.tasks.email_tasks import send_invitation_email
                send_invitation_email.delay(
                    invitee_email, inviter_name, group_name, invitation_id
                )
                logger.info(f"Invitation email queued for {invitee_email}")
                return 'queued'
            except Exception as celery_err:
                logger.warning(f"Celery dispatch failed, sending synchronously: {celery_err}")
            
            # Fallback: synchronous send
            success = email_service.send_group_invitation(
                to_email=invitee_email,
                inviter_name=inviter_name,
                group_name=group_name,
                invitation_id=str(invitation_id)
            )
            
            if success:
                logger.info(f"Invitation email sent to {invitee_email}")
                return 'sent'
            else:
                logger.warning(f"Failed to send invitation email to {invitee_email}")
                return 'failed'
                
        except Exception as e:
            logger.error(f"Error sending invitation email: {str(e)}")
            return 'failed'
    
    @staticmethod
    def send_invitation(group_id: str, invitee_email: str, invited_by_user_id: str) -> Tuple[bool, Dict]:
        """
        Send invitation to join a group
        
        Args:
            group_id: ID of the group
            invitee_email: Email of the person being invited
            invited_by_user_id: User ID of the person sending the invitation
        
        Returns:
            (success, result_dict)
        """
        try:
          invitee_email = invitee_email.strip().lower()
          with get_db() as session:
            # Verify group exists and user has permission
            group = session.query(Group).filter(Group.id == group_id).first()
            if not group:
                return False, {'error': 'Group not found'}
            
            # Check if invited_by_user_id is a member of the group
            is_member = session.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == invited_by_user_id,
                GroupMember.is_active == True
            ).first()
            
            if not is_member:
                return False, {'error': 'You are not a member of this group'}
            
            # Check if email is already a member
            existing_user = session.query(User).filter(User.email == invitee_email).first()
            if existing_user:
                existing_member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == existing_user.id,
                    GroupMember.is_active == True
                ).first()
                
                if existing_member:
                    return False, {'error': 'User is already a member of this group'}
            
            # Check for existing pending invitation
            existing_invitation = session.query(Invitation).filter(
                Invitation.group_id == group_id,
                Invitation.invitee_email == invitee_email,
                Invitation.status == 'pending'
            ).first()
            
            if existing_invitation:
                # Check if invitation has expired
                if existing_invitation.expires_at and existing_invitation.expires_at < datetime.utcnow():
                    # Invitation has expired, update it as a resend
                    existing_invitation.expires_at = datetime.utcnow() + timedelta(
                        days=InvitationServiceSQL.INVITATION_EXPIRY_DAYS
                    )
                    existing_invitation.created_at = datetime.utcnow()
                    session.commit()
                    
                    inviter = session.query(User).filter(User.id == invited_by_user_id).first()
                    inviter_name = inviter.display_name or inviter.email.split('@')[0] if inviter else 'Someone'
                    
                    email_status = InvitationServiceSQL._send_invitation_email(
                        invitee_email=invitee_email,
                        inviter_name=inviter_name,
                        group_name=group.name,
                        invitation_id=existing_invitation.id
                    )
                    
                    formatted_invitation = {
                        'invitation_id': existing_invitation.id,
                        'id': existing_invitation.id,
                        'group_id': group.id,
                        'group_name': group.name,
                        'group_currency': group.currency,
                        'invitee_email': invitee_email,
                        'invited_by': invited_by_user_id,
                        'invited_by_name': inviter_name,
                        'status': existing_invitation.status,
                        'created_at': existing_invitation.created_at.isoformat() if existing_invitation.created_at else None,
                        'expires_at': existing_invitation.expires_at.isoformat() if existing_invitation.expires_at else None
                    }
                    
                    return True, {
                        'invitation': formatted_invitation, 
                        'message': 'Invitation resent (previous had expired)',
                        'email_status': email_status
                    }
                else:
                    # Pending invitation still valid - don't send again
                    return False, {'error': 'Invitation already sent and is pending. Please wait for the user to respond.'}
            
            # Check for declined invitation - allow resending
            declined_invitation = session.query(Invitation).filter(
                Invitation.group_id == group_id,
                Invitation.invitee_email == invitee_email,
                Invitation.status == 'declined'
            ).first()
            
            if declined_invitation:
                # Reset declined invitation to pending and extend expiry
                declined_invitation.status = 'pending'
                declined_invitation.expires_at = datetime.utcnow() + timedelta(
                    days=InvitationServiceSQL.INVITATION_EXPIRY_DAYS
                )
                declined_invitation.created_at = datetime.utcnow()
                session.commit()
                
                # Get inviter info for email
                inviter = session.query(User).filter(User.id == invited_by_user_id).first()
                inviter_name = inviter.display_name or inviter.email.split('@')[0] if inviter else 'Someone'
                
                # Send invitation email
                email_status = InvitationServiceSQL._send_invitation_email(
                    invitee_email=invitee_email,
                    inviter_name=inviter_name,
                    group_name=group.name,
                    invitation_id=declined_invitation.id
                )
                
                # Return formatted invitation data
                formatted_invitation = {
                    'invitation_id': declined_invitation.id,
                    'id': declined_invitation.id,
                    'group_id': group.id,
                    'group_name': group.name,
                    'group_currency': group.currency,
                    'invitee_email': invitee_email,
                    'invited_by': invited_by_user_id,
                    'invited_by_name': inviter_name,
                    'status': declined_invitation.status,
                    'created_at': declined_invitation.created_at.isoformat() if declined_invitation.created_at else None,
                    'expires_at': declined_invitation.expires_at.isoformat() if declined_invitation.expires_at else None
                }
                
                return True, {
                    'invitation': formatted_invitation, 
                    'message': 'Invitation resent (user had previously declined)',
                    'email_status': email_status
                }

            # The database keeps one historical invitation per group/email.
            # Re-open accepted or explicitly expired rows when that person is
            # no longer an active member, rather than attempting an insert that
            # violates uq_invitation and makes a later invitation impossible.
            historical_invitation = session.query(Invitation).filter(
                Invitation.group_id == group_id,
                Invitation.invitee_email == invitee_email,
                Invitation.status.in_(['accepted', 'expired'])
            ).order_by(Invitation.created_at.desc()).first()

            if historical_invitation:
                historical_invitation.status = 'pending'
                historical_invitation.invited_by = invited_by_user_id
                historical_invitation.invitee_user_id = existing_user.id if existing_user else None
                historical_invitation.expires_at = datetime.utcnow() + timedelta(
                    days=InvitationServiceSQL.INVITATION_EXPIRY_DAYS
                )
                historical_invitation.created_at = datetime.utcnow()
                historical_invitation.responded_at = None
                session.commit()

                inviter = session.query(User).filter(User.id == invited_by_user_id).first()
                inviter_name = inviter.display_name or inviter.email.split('@')[0] if inviter else 'Someone'
                email_status = InvitationServiceSQL._send_invitation_email(
                    invitee_email=invitee_email,
                    inviter_name=inviter_name,
                    group_name=group.name,
                    invitation_id=historical_invitation.id,
                )
                formatted_invitation = {
                    'invitation_id': historical_invitation.id,
                    'id': historical_invitation.id,
                    'group_id': group.id,
                    'group_name': group.name,
                    'group_currency': group.currency,
                    'invitee_email': invitee_email,
                    'invited_by': invited_by_user_id,
                    'invited_by_name': inviter_name,
                    'status': historical_invitation.status,
                    'created_at': historical_invitation.created_at.isoformat() if historical_invitation.created_at else None,
                    'expires_at': historical_invitation.expires_at.isoformat() if historical_invitation.expires_at else None,
                }
                return True, {
                    'invitation': formatted_invitation,
                    'message': 'Invitation resent from historical invitation',
                    'email_status': email_status,
                }
            
            # Create new invitation
            invitation = Invitation(
                group_id=group_id,
                invitee_email=invitee_email,
                invited_by=invited_by_user_id,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(
                    days=InvitationServiceSQL.INVITATION_EXPIRY_DAYS
                )
            )
            
            session.add(invitation)
            session.commit()
            
            logger.info(f"Invitation created: ID={invitation.id}, group={group_id}, email={invitee_email}, status={invitation.status}")
            
            # Verify it was saved by querying it back
            saved_inv = session.query(Invitation).filter(Invitation.id == invitation.id).first()
            if saved_inv:
                logger.debug(f"Invitation verified in DB: ID={saved_inv.id}, email={saved_inv.invitee_email}")
            else:
                logger.error(f"Invitation NOT found in DB after creation!")
            session.refresh(invitation)
            
            # Get inviter info for email
            inviter = session.query(User).filter(User.id == invited_by_user_id).first()
            inviter_name = inviter.display_name or inviter.email.split('@')[0] if inviter else 'Someone'
            
            # Send invitation email
            email_status = InvitationServiceSQL._send_invitation_email(
                invitee_email=invitee_email,
                inviter_name=inviter_name,
                group_name=group.name,
                invitation_id=invitation.id
            )
            
            # Build invitation link
            frontend_url = Config.FRONTEND_URL
            invitation_link = f"{frontend_url}/expenses?invitation={invitation.id}"
            
            # Return formatted invitation data (same as what invitee would see in pending list)
            formatted_invitation = {
                'invitation_id': invitation.id,
                'id': invitation.id,  # For backward compatibility
                'group_id': group.id,
                'group_name': group.name,
                'group_currency': group.currency,
                'invitee_email': invitee_email,
                'invited_by': invited_by_user_id,
                'invited_by_name': inviter_name,
                'status': invitation.status,
                'created_at': invitation.created_at.isoformat() if invitation.created_at else None,
                'expires_at': invitation.expires_at.isoformat() if invitation.expires_at else None
            }
            
            return True, {
                'invitation': formatted_invitation,
                'email_status': email_status,
                'invitation_link': invitation_link,
                'message': 'Invitation sent successfully'
            }
            
        except IntegrityError:
            return False, {'error': 'Invitation already exists'}
        except Exception as e:
            return False, {'error': f'Failed to send invitation: {str(e)}'}
    
    @staticmethod
    def get_invitations(user_id: str, group_id: str = None) -> Tuple[bool, Dict]:
        """
        Get invitations for a user or group
        
        Args:
            user_id: User ID
            group_id: Optional - filter by specific group
        
        Returns:
            (success, result_dict)
        """
        session = get_db_session()
        
        try:
            query = session.query(Invitation).filter(
                Invitation.invitee_email == session.query(User.email).filter(User.id == user_id).scalar()
            )
            
            if group_id:
                query = query.filter(Invitation.group_id == group_id)
            
            invitations = query.all()
            
            return True, {
                'invitations': [inv.to_dict() for inv in invitations],
                'count': len(invitations)
            }
        except Exception as e:
            return False, {'error': f'Failed to get invitations: {str(e)}'}
        finally:
            session.close()
    
    @staticmethod
    def get_pending_invitations_for_user(user_id: str) -> Tuple[bool, Dict]:
        """
        Get pending invitations for the current user (for homepage popup)
        
        Args:
            user_id: User ID
        
        Returns:
            (success, result_dict) with invitations containing group info
        """
        from app.core.db.connection import get_db_session
        
        session = get_db_session()
        
        logger.info(f"GET_PENDING_INVITATIONS_FOR_USER called with user_id={user_id}")
        
        try:
            # Get user email
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User not found: user_id={user_id}")
                return False, {'error': 'User not found'}
            
            logger.debug(f"User found: email={user.email}")
            
            # Get pending invitations for this email
            invitations = session.query(Invitation).filter(
                Invitation.invitee_email == user.email,
                Invitation.status == 'pending'
            ).all()
            
            logger.info(f"Found {len(invitations)} pending invitations for email={user.email}")
            
            # Format invitations with group info for frontend
            formatted_invitations = []
            for inv in invitations:
                group = session.query(Group).filter(Group.id == inv.group_id).first()
                inviter = session.query(User).filter(User.id == inv.invited_by).first()
                
                logger.info(f"   - Invitation {inv.id}: group={group.name if group else 'None'}, inviter={inviter.display_name if inviter else 'None'}")
                
                formatted_invitations.append({
                    'invitation_id': inv.id,
                    'group_id': inv.group_id,
                    'group_name': group.name if group else 'Unknown Group',
                    'group_currency': group.currency if group else Config.DEFAULT_CURRENCY,
                    'invited_by': inv.invited_by,
                    'invited_by_name': inviter.display_name if inviter else 'Unknown',
                    'status': inv.status,
                    'created_at': inv.created_at.isoformat() if inv.created_at else None,
                    'expires_at': inv.expires_at.isoformat() if inv.expires_at else None
                })
            
            return True, {
                'invitations': formatted_invitations,
                'count': len(formatted_invitations)
            }
        except Exception as e:
            logger.error(f"Error getting pending invitations: {str(e)}")
            return False, {'error': f'Failed to get invitations: {str(e)}'}
        finally:
            session.close()
    
    @staticmethod
    def accept_invitation(invitation_id: str, user_id: str) -> Tuple[bool, Dict]:
        """
        Accept group invitation
        
        Args:
            invitation_id: ID of the invitation
            user_id: User ID accepting the invitation
        
        Returns:
            (success, result_dict) with full group details
        """
        session = get_db_session()
        
        try:
            invitation = session.query(Invitation).filter(Invitation.id == invitation_id).first()
            
            if not invitation:
                return False, {'error': 'Invitation not found'}
            
            if invitation.status != 'pending':
                return False, {'error': f'Invitation is {invitation.status}'}
            
            if invitation.expires_at and invitation.expires_at < datetime.utcnow():
                invitation.status = 'expired'
                session.commit()
                return False, {'error': 'Invitation has expired'}
            
            # Get the user
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, {'error': 'User not found'}
            
            if user.email.lower() != (invitation.invitee_email or '').lower():
                return False, {'error': 'Invitation is not for this user'}
            
            # Check if already a member
            existing_member = session.query(GroupMember).filter(
                GroupMember.group_id == invitation.group_id,
                GroupMember.user_id == user_id,
            ).first()
            
            if existing_member:
                if existing_member.is_active:
                    return False, {'error': 'User is already a member of this group'}
                # Unique memberships are permanent. Rejoin by reactivating
                # the old row rather than attempting an insert that rolls
                # the whole acceptance transaction back.
                existing_member.is_active = True
                existing_member.role = 'member'
                existing_member.joined_at = datetime.utcnow()
                existing_member.removed_at = None
                existing_member.removed_by = None
            else:
                member = GroupMember(
                    group_id=invitation.group_id,
                    user_id=user_id,
                    role='member'
                )
                session.add(member)
                session.add(GroupBalance(
                    group_id=invitation.group_id,
                    user_id=user_id,
                    balance=0.0
                ))
            
            # Update invitation
            invitation.status = 'accepted'
            invitation.invitee_user_id = user_id
            invitation.responded_at = datetime.utcnow()
            
            session.commit()
            
            # Get full group info for response
            group = session.query(Group).filter(Group.id == invitation.group_id).first()
            if not group:
                return False, {'error': 'Group not found'}
            
            # Get all group members with user details
            members_query = session.query(GroupMember, User).join(
                User, GroupMember.user_id == User.id
            ).filter(
                GroupMember.group_id == invitation.group_id,
                GroupMember.is_active == True
            ).all()
            
            members = []
            for gm, u in members_query:
                members.append({
                    'user_id': u.id,
                    'email': u.email,
                    'display_name': u.display_name,
                    'role': gm.role,
                    'joined_at': gm.joined_at.isoformat() if gm.joined_at else None
                })
            
            # Get all balances
            balances_query = session.query(GroupBalance, User).join(
                User, GroupBalance.user_id == User.id
            ).filter(
                GroupBalance.group_id == invitation.group_id
            ).all()
            
            balances = []
            for gb, u in balances_query:
                balances.append({
                    'user_id': u.id,
                    'user_name': u.display_name or u.email.split('@')[0],
                    'balance': gb.balance
                })
            
            # Build full group response
            group_data = {
                'id': group.id,
                'name': group.name,
                'currency': group.currency,
                'created_by': group.created_by,
                'created_at': group.created_at.isoformat() if group.created_at else None,
                'members': members,
                'balances': balances,
                'expenses': [],  # Will be empty for newly joined group
                'simplified_debts': []  # No debts initially
            }
            
            return True, {
                'message': 'Invitation accepted successfully',
                'invitation': invitation.to_dict(),
                'group': group_data,
                'refresh_required': True
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Error accepting invitation: {str(e)}")
            return False, {'error': f'Failed to accept invitation: {str(e)}'}
        finally:
            session.close()
    
    @staticmethod
    def decline_invitation(invitation_id: str, user_id: str) -> Tuple[bool, Dict]:
        """
        Decline group invitation
        
        Args:
            invitation_id: ID of the invitation
            user_id: User ID declining the invitation
        
        Returns:
            (success, result_dict)
        """
        session = get_db_session()
        
        try:
            invitation = session.query(Invitation).filter(Invitation.id == invitation_id).first()
            
            if not invitation:
                return False, {'error': 'Invitation not found'}
            
            if invitation.status != 'pending':
                return False, {'error': f'Invitation is already {invitation.status}'}
            
            # Verify the user is the invitee
            user = session.query(User).filter(User.id == user_id).first()
            if not user or user.email != invitation.invitee_email:
                return False, {'error': 'You cannot decline this invitation'}
            
            # Update invitation status
            invitation.status = 'declined'
            invitation.responded_at = datetime.utcnow()
            
            session.commit()
            
            # Get group info for logging
            group = session.query(Group).filter(Group.id == invitation.group_id).first()
            group_name = group.name if group else 'Unknown'
            
            logger.info(f"Invitation {invitation_id} declined by user {user_id} for group '{group_name}'")
            
            return True, {
                'message': 'Invitation declined successfully',
                'invitation': invitation.to_dict(),
                'group_id': invitation.group_id,
                'group_name': group_name
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Error declining invitation: {str(e)}")
            return False, {'error': f'Failed to decline invitation: {str(e)}'}
        finally:
            session.close()
    
    @staticmethod
    def get_group_invitations(group_id: str, user_id: str) -> Tuple[bool, Dict]:
        """
        Get all invitations for a group (admin only)
        
        Args:
            group_id: ID of the group
            user_id: User ID (must be group member)
        
        Returns:
            (success, result_dict)
        """
        session = get_db_session()
        
        try:
            # Verify user is a member of the group
            is_member = session.query(GroupMember).filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.is_active == True
            ).first()
            
            if not is_member:
                return False, {'error': 'You are not a member of this group'}
            
            invitations = session.query(Invitation).filter(
                Invitation.group_id == group_id
            ).all()
            
            return True, {
                'invitations': [inv.to_dict() for inv in invitations],
                'count': len(invitations)
            }
        except Exception as e:
            return False, {'error': f'Failed to get group invitations: {str(e)}'}
        finally:
            session.close()


# Create singleton instance
invitation_service_sql = InvitationServiceSQL()
