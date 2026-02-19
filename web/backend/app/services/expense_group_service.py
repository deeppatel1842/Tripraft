"""
SQL-based Group Service
Handles group operations using local SQL database
"""

import logging
import random
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.expenses.models import Group, GroupBalance, GroupMember, User
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)


def generate_group_code(length: int = 8) -> str:
    """Generate a unique group invitation code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


class GroupServiceSQL:
    """Service for group operations using SQL database"""
    
    @staticmethod
    def create_group(
        user_id: int,
        name: str,
        description: Optional[str] = None,
        currency: str = 'INR',
        category: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new expense group
        
        Args:
            user_id: ID of the user creating the group
            name: Group name
            description: Optional group description
            currency: Default currency for the group
            category: Optional category (trip, home, couple, etc.)
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            # Validate name
            if not name or not name.strip():
                return False, {'error': 'Group name is required'}

            with get_db_session() as session:
                # Verify user exists
                user = session.query(User).get(user_id)
                if not user:
                    return False, {'error': 'User not found'}
                
                # Generate unique group code
                group_code = generate_group_code()
                while session.query(Group).filter(Group.group_code == group_code).first():
                    group_code = generate_group_code()
                
                # Create group
                group = Group(
                    name=name.strip(),
                    description=description.strip() if description else None,
                    currency=currency.upper(),
                    group_code=group_code,
                    category=category,
                    created_by=user_id
                )
                session.add(group)
                session.flush()  # Get group ID
                
                # Add creator as admin member
                member = GroupMember(
                    group_id=group.id,
                    user_id=user_id,
                    role='admin',
                    is_active=True
                )
                session.add(member)
                
                # Initialize balance for creator
                balance = GroupBalance(
                    group_id=group.id,
                    user_id=user_id,
                    balance=0.0
                )
                session.add(balance)
                
                session.commit()
                session.refresh(group)
                
                logger.info(f"Group created: {group.id} by user {user_id}")
                
                # Manually build members list since relationship might not be loaded
                members_data = []
                member_with_user = session.query(GroupMember, User).join(
                    User, GroupMember.user_id == User.id
                ).filter(
                    GroupMember.group_id == group.id,
                    GroupMember.is_active == True
                ).all()
                
                for gm, u in member_with_user:
                    members_data.append({
                        'id': gm.id,
                        'group_id': gm.group_id,
                        'user_id': gm.user_id,
                        'role': gm.role,
                        'is_active': gm.is_active,
                        'joined_at': gm.joined_at.isoformat() if gm.joined_at else None,
                        'user': {
                            'id': u.id,
                            'email': u.email,
                            'display_name': u.display_name,
                            'photo_url': u.photo_url
                        }
                    })
                
                # Build group dict with members
                group_dict = group.to_dict(include_members=False)
                group_dict['members'] = members_data
                group_dict['member_count'] = len(members_data)
                
                return True, {'group': group_dict}
                
        except Exception as e:
            logger.error(f"Create group error: {str(e)}")
            return False, {'error': 'Failed to create group'}
    
    @staticmethod
    def get_group(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get group details
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID (for access check)
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(Group).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                group_data = group.to_dict()
                
                # Add members list
                members = session.query(GroupMember, User).join(
                    User, GroupMember.user_id == User.id
                ).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.is_active == True
                ).all()
                
                group_data['members'] = [
                    {
                        'id': user.id,
                        'email': user.email,
                        'display_name': user.display_name,
                        'photo_url': user.photo_url,
                        'role': gm.role,
                        'joined_at': gm.joined_at.isoformat() if gm.joined_at else None
                    }
                    for gm, user in members
                ]
                
                # Add balances
                balances = session.query(GroupBalance).filter(
                    GroupBalance.group_id == group_id
                ).all()
                
                group_data['balances'] = {
                    str(b.user_id): b.balance for b in balances
                }
                
                return True, {'group': group_data}
                
        except Exception as e:
            logger.error(f"Get group error: {str(e)}")
            return False, {'error': 'Failed to get group'}
    
    @staticmethod
    def get_user_groups(user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all groups for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, groups_list/error)
        """
        try:
            with get_db_session() as session:
                memberships = session.query(GroupMember, Group).join(
                    Group, GroupMember.group_id == Group.id
                ).filter(
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True,
                    Group.is_active == True
                ).order_by(Group.updated_at.desc()).all()
                
                groups = []
                for membership, group in memberships:
                    group_data = group.to_dict()
                    
                    # Get all members for this group
                    members_query = session.query(GroupMember, User).join(
                        User, GroupMember.user_id == User.id
                    ).filter(
                        GroupMember.group_id == group.id,
                        GroupMember.is_active == True
                    ).all()
                    
                    group_data['members'] = [
                        {
                            'id': u.id,
                            'user_id': u.id,
                            'email': u.email,
                            'display_name': u.display_name,
                            'photo_url': u.photo_url,
                            'role': gm.role,
                            'joined_at': gm.joined_at.isoformat() if gm.joined_at else None
                        }
                        for gm, u in members_query
                    ]
                    
                    group_data['member_count'] = len(members_query)
                    group_data['my_role'] = membership.role
                    
                    # Get user's balance in this group
                    balance = session.query(GroupBalance).filter(
                        GroupBalance.group_id == group.id,
                        GroupBalance.user_id == user_id
                    ).first()
                    
                    group_data['my_balance'] = balance.balance if balance else 0.0
                    
                    groups.append(group_data)
                
                return True, {'groups': groups}
                
        except Exception as e:
            logger.error(f"Get user groups error: {str(e)}")
            return False, {'error': 'Failed to get groups'}
    
    @staticmethod
    def update_group(
        group_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        currency: Optional[str] = None,
        category: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update group details (admin only)
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            name: New name
            description: New description
            currency: New currency
            category: New category
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            with get_db_session() as session:
                # Check admin membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member or member.role != 'admin':
                    return False, {'error': 'Admin access required'}
                
                group = session.query(Group).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                if name:
                    group.name = name.strip()
                if description is not None:
                    group.description = description.strip() if description else None
                if currency:
                    group.currency = currency.upper()
                if category is not None:
                    group.category = category
                
                group.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(group)
                
                return True, {'group': group.to_dict()}
                
        except Exception as e:
            logger.error(f"Update group error: {str(e)}")
            return False, {'error': 'Failed to update group'}
    
    @staticmethod
    def delete_group(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete/archive a group (owner only)
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                group = session.query(Group).get(group_id)
                if not group:
                    return False, {'error': 'Group not found'}
                
                # Only the group owner can delete the group
                if group.created_by != user_id:
                    return False, {'error': 'Only the group owner can delete the group'}
                
                # Check for unsettled balances - can't delete group with outstanding debts
                balances = session.query(GroupBalance).filter(
                    GroupBalance.group_id == group_id
                ).all()
                
                for balance in balances:
                    if abs(balance.balance) > 0.01:
                        return False, {'error': 'Cannot delete group with unsettled balances. Please settle all debts first.'}
                
                # Soft delete
                group.is_active = False
                group.updated_at = datetime.now(timezone.utc)
                session.commit()
                
                logger.info(f"Group deleted: {group_id}")
                return True, {'message': 'Group deleted successfully'}
                
        except Exception as e:
            logger.error(f"Delete group error: {str(e)}")
            return False, {'error': 'Failed to delete group'}
    
    @staticmethod
    def add_member(
        group_id: int,
        user_id: int,
        member_email: str,
        role: str = 'member'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a member to the group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID (admin)
            member_email: Email of user to add
            role: Role for new member
            
        Returns:
            Tuple of (success, member_data/error)
        """
        try:
            with get_db_session() as session:
                # Check admin membership
                admin_member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not admin_member or admin_member.role != 'admin':
                    return False, {'error': 'Admin access required'}
                
                # Find user by email
                new_user = session.query(User).filter(
                    User.email == member_email.lower()
                ).first()
                
                if not new_user:
                    return False, {'error': 'User not found. They must sign up first.'}
                
                # Check if already a member
                existing = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == new_user.id
                ).first()
                
                if existing:
                    if existing.is_active:
                        return False, {'error': 'User is already a member'}
                    else:
                        # Reactivate membership
                        existing.is_active = True
                        existing.role = role
                        existing.joined_at = datetime.now(timezone.utc)
                        session.commit()
                        return True, {
                            'member': {
                                'id': new_user.id,
                                'email': new_user.email,
                                'display_name': new_user.display_name,
                                'role': role
                            }
                        }
                
                # Add new member
                member = GroupMember(
                    group_id=group_id,
                    user_id=new_user.id,
                    role=role,
                    is_active=True
                )
                session.add(member)
                
                # Initialize balance
                balance = GroupBalance(
                    group_id=group_id,
                    user_id=new_user.id,
                    balance=0.0
                )
                session.add(balance)
                
                session.commit()
                
                logger.info(f"Member {new_user.id} added to group {group_id}")
                return True, {
                    'member': {
                        'id': new_user.id,
                        'email': new_user.email,
                        'display_name': new_user.display_name,
                        'role': role
                    }
                }
                
        except Exception as e:
            logger.error(f"Add member error: {str(e)}")
            return False, {'error': 'Failed to add member'}
    
    @staticmethod
    def remove_member(
        group_id: int,
        user_id: int,
        member_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove a member from the group (owner only, or member leaving themselves)
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            member_id: ID of member to remove
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                # Get the group to check ownership
                group = session.query(Group).get(group_id)
                if not group:
                    return False, {'error': 'Group not found'}
                
                # Check if requesting user is a member
                requester = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not requester:
                    return False, {'error': 'Not a member of this group'}
                
                # Allow user to leave on their own, or owner can remove anyone
                is_owner = group.created_by == user_id
                is_self_removal = user_id == member_id
                
                if not is_owner and not is_self_removal:
                    return False, {'error': 'Only the group owner can remove other members'}
                
                # Owner cannot be removed
                if member_id == group.created_by:
                    return False, {'error': 'Cannot remove the group owner'}
                
                # Check member's balance
                balance = session.query(GroupBalance).filter(
                    GroupBalance.group_id == group_id,
                    GroupBalance.user_id == member_id
                ).first()
                
                if balance and abs(balance.balance) > 0.01:
                    return False, {'error': 'Cannot remove member with unsettled balance'}
                
                # Remove membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == member_id
                ).first()
                
                if not member:
                    return False, {'error': 'Member not found'}
                
                member.is_active = False
                session.commit()
                
                logger.info(f"Member {member_id} removed from group {group_id}")
                return True, {'message': 'Member removed successfully'}
                
        except Exception as e:
            logger.error(f"Remove member error: {str(e)}")
            return False, {'error': 'Failed to remove member'}
    
    @staticmethod
    def join_by_code(user_id: int, group_code: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Join a group using invitation code
        
        Args:
            user_id: User ID
            group_code: Group invitation code
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            group_code = str(group_code).strip().upper()

            with get_db_session() as session:
                # Find group by code
                group = session.query(Group).filter(
                    Group.group_code == group_code,
                    Group.is_active == True
                ).first()
                
                if not group:
                    return False, {'error': 'Invalid group code'}
                
                # Check if already a member
                existing = session.query(GroupMember).filter(
                    GroupMember.group_id == group.id,
                    GroupMember.user_id == user_id
                ).first()
                
                if existing:
                    if existing.is_active:
                        return False, {'error': 'Already a member of this group'}
                    else:
                        # Reactivate
                        existing.is_active = True
                        existing.joined_at = datetime.now(timezone.utc)
                        session.commit()
                        return True, {'group': group.to_dict()}
                
                # Add as member
                member = GroupMember(
                    group_id=group.id,
                    user_id=user_id,
                    role='member',
                    is_active=True
                )
                session.add(member)
                
                # Initialize balance
                balance = GroupBalance(
                    group_id=group.id,
                    user_id=user_id,
                    balance=0.0
                )
                session.add(balance)
                
                session.commit()
                
                logger.info(f"User {user_id} joined group {group.id}")
                return True, {'group': group.to_dict()}
                
        except Exception as e:
            logger.error(f"Join group error: {str(e)}")
            return False, {'error': 'Failed to join group'}
    
    @staticmethod
    def get_group_balances(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all member balances for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, balances_list/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get all balances with user info
                balances = session.query(GroupBalance, User).join(
                    User, GroupBalance.user_id == User.id
                ).filter(
                    GroupBalance.group_id == group_id
                ).all()
                
                balance_list = [
                    {
                        'user_id': user.id,
                        'display_name': user.display_name or user.email.split('@')[0],
                        'email': user.email,
                        'photo_url': user.photo_url,
                        'balance': float(gb.balance) if gb.balance else 0.0,
                        'net_balance': float(gb.balance) if gb.balance else 0.0
                    }
                    for gb, user in balances
                ]
                
                return True, {'balances': balance_list}
                
        except Exception as e:
            logger.error(f"Get balances error: {str(e)}")
            return False, {'error': 'Failed to get balances'}
    
    @staticmethod
    def get_group_members(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all members of a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, members_list/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                members = session.query(GroupMember, User).join(
                    User, GroupMember.user_id == User.id
                ).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.is_active == True
                ).all()
                
                member_list = [
                    {
                        'id': user.id,
                        'user_id': user.id,  # Frontend expects user_id
                        'email': user.email,
                        'display_name': user.display_name or user.email.split('@')[0],
                        'username': user.display_name or user.email.split('@')[0],
                        'photo_url': user.photo_url,
                        'role': gm.role,
                        'joined_at': gm.joined_at.isoformat() if gm.joined_at else None,
                        'is_active': gm.is_active
                    }
                    for gm, user in members
                ]
                
                return True, {'members': member_list}
                
        except Exception as e:
            logger.error(f"Get members error: {str(e)}")
            return False, {'error': 'Failed to get members'}


# Create singleton instance
group_service_sql = GroupServiceSQL()
