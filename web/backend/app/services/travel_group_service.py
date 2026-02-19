"""
Group Service for Group Planner
Handles all group operations using unified SQL database (pateldeep.db)


Uses shared users table with expense_engine
"""

import logging
import random
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.group_planner.models import (GroupActivity, ItineraryDocument,
                                             TravelGroup, TripMember)
from app.domain.users.models import User
from app.infrastructure.db.connection import get_db_session
from sqlalchemy import func

# Import expense-engine models for cross-module queries
try:
    from app.domain.expenses.models import GroupBalance
except ImportError:
    GroupBalance = None

logger = logging.getLogger(__name__)


def generate_group_code(length: int = 8) -> str:
    """Generate a unique group invitation code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


class GroupService:
    """Service for group operations using SQL database"""
    
    @staticmethod
    def create_group(
        user_id: int,
        name: str,
        description: Optional[str] = None,
        destination: Optional[str] = None,
        destination_lat: Optional[float] = None,
        destination_lng: Optional[float] = None,
        destination_type: Optional[str] = None,
        destination_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        estimated_budget: Optional[float] = None,
        budget_currency: str = 'USD'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new travel group
        
        Args:
            user_id: ID of the user creating the group
            name: Group name
            description: Optional group description
            destination: Optional destination
            start_date: Optional trip start date
            end_date: Optional trip end date
            estimated_budget: Optional estimated budget
            budget_currency: Budget currency (default USD)
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            with get_db_session() as session:
                # Verify user exists
                user = session.query(User).get(user_id)
                if not user:
                    return False, {'error': 'User not found'}
                
                # Generate unique group code
                group_code = generate_group_code()
                while session.query(TravelGroup).filter(TravelGroup.group_code == group_code).first():
                    group_code = generate_group_code()
                
                # Parse dates
                parsed_start_date = None
                parsed_end_date = None
                if start_date:
                    try:
                        parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
                    except:
                        pass
                if end_date:
                    try:
                        parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                    except:
                        pass
                
                # Create group
                group = TravelGroup(
                    name=name.strip(),
                    description=description.strip() if description else None,
                    destination=destination.strip() if destination else None,
                    destination_lat=destination_lat,
                    destination_lng=destination_lng,
                    destination_type=destination_type,
                    destination_id=str(destination_id) if destination_id else None,
                    group_code=group_code,
                    created_by=user_id,
                    start_date=parsed_start_date,
                    end_date=parsed_end_date,
                    estimated_budget=estimated_budget,
                    budget_currency=budget_currency.upper()
                )
                session.add(group)
                session.flush()  # Get group ID
                
                # Add creator as member with 'creator' role
                member = TripMember(
                    group_id=group.id,
                    user_id=user_id,
                    role='creator',
                    is_active=True
                )
                session.add(member)
                
                # Create empty itinerary document
                itinerary = ItineraryDocument(
                    group_id=group.id,
                    content='',
                    last_edited_by=user_id
                )
                session.add(itinerary)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group.id,
                    user_id=user_id,
                    action='group_created',
                    entity_type='group',
                    entity_id=group.id,
                    details={'name': name}
                )
                session.add(activity)
                
                session.commit()
                session.refresh(group)
                
                logger.info(f"Group created: {group.id} by user {user_id}")
                
                # Build response with members
                group_dict = group.to_dict(include_members=True)
                
                return True, {'group': group_dict}
                
        except Exception as e:
            logger.error(f"Create group error: {str(e)}")
            return False, {'error': 'Failed to create group'}
    
    @staticmethod
    def get_group(group_id: int, user_id: int, include_all: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Get group details
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID (for access check)
            include_all: Include members, places, polls
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                group_data = group.to_dict(
                    include_members=include_all,
                    include_places=include_all,
                    include_polls=include_all
                )
                
                # Add checklist items
                if include_all:
                    group_data['checklist'] = [
                        item.to_dict() for item in group.checklist_items 
                        if not item.is_deleted
                    ]
                    
                    # Add itinerary content
                    if group.itinerary:
                        group_data['itinerary_document'] = group.itinerary.content
                
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
                memberships = session.query(TripMember, TravelGroup).join(
                    TravelGroup, TripMember.group_id == TravelGroup.id
                ).filter(
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                    TravelGroup.is_active == True
                ).order_by(TravelGroup.updated_at.desc()).all()
                
                groups = []
                for membership, group in memberships:
                    group_data = group.to_dict(include_members=True)
                    group_data['my_role'] = membership.role
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
        destination: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        estimated_budget: Optional[float] = None,
        budget_currency: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update group details
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            name: New name
            description: New description
            destination: New destination
            start_date: New start date
            end_date: New end date
            estimated_budget: New budget
            budget_currency: New currency
            
        Returns:
            Tuple of (success, group_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Update fields
                if name is not None:
                    group.name = name.strip()
                if description is not None:
                    group.description = description.strip()
                if destination is not None:
                    group.destination = destination.strip()
                if start_date is not None:
                    try:
                        group.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
                    except:
                        pass
                if end_date is not None:
                    try:
                        group.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                    except:
                        pass
                if estimated_budget is not None:
                    group.estimated_budget = estimated_budget
                if budget_currency is not None:
                    group.budget_currency = budget_currency.upper()
                
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(group)
                
                logger.info(f"Group updated: {group_id}")
                
                return True, {'group': group.to_dict(include_members=True)}
                
        except Exception as e:
            logger.error(f"Update group error: {str(e)}")
            return False, {'error': 'Failed to update group'}
    
    @staticmethod
    def delete_group(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a group (soft delete, creator only)
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Only creator can delete
                if group.created_by != user_id:
                    return False, {'error': 'Only the group creator can delete the group'}
                
                # Soft delete
                group.is_active = False
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Group deleted: {group_id} by user {user_id}")
                
                return True, {'message': 'Group deleted successfully'}
                
        except Exception as e:
            logger.error(f"Delete group error: {str(e)}")
            return False, {'error': 'Failed to delete group'}
    
    @staticmethod
    def update_itinerary(
        group_id: int,
        user_id: int,
        content: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update group itinerary document
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            content: Itinerary content (markdown)
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get or create itinerary
                itinerary = session.query(ItineraryDocument).filter(
                    ItineraryDocument.group_id == group_id
                ).first()
                
                if not itinerary:
                    itinerary = ItineraryDocument(
                        group_id=group_id,
                        content=content,
                        last_edited_by=user_id
                    )
                    session.add(itinerary)
                else:
                    itinerary.content = content
                    itinerary.last_edited_by = user_id
                    itinerary.version += 1
                    itinerary.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Itinerary updated for group {group_id}")
                
                return True, {'updated': True, 'group_id': group_id}
                
        except Exception as e:
            logger.error(f"Update itinerary error: {str(e)}")
            return False, {'error': 'Failed to update itinerary'}
    
    @staticmethod
    def update_budget(
        group_id: int,
        user_id: int,
        estimated_budget: float,
        budget_currency: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update group estimated budget
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            estimated_budget: New budget value
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                group.estimated_budget = estimated_budget
                if budget_currency:
                    group.budget_currency = budget_currency
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Budget updated for group {group_id}")
                
                return True, {'estimated_budget': estimated_budget}
                
        except Exception as e:
            logger.error(f"Update budget error: {str(e)}")
            return False, {'error': 'Failed to update budget'}

    @staticmethod
    def is_member(group_id: int, user_id: int) -> bool:
        """Check if user is a member of the group"""
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                return member is not None
        except Exception:
            return False
    
    @staticmethod
    def link_expense_group(
        group_id: int,
        user_id: int,
        expense_group_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Link travel group to expense engine group"""
        try:
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group:
                    return False, {'error': 'Group not found'}
                
                group.expense_group_id = expense_group_id
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                return True, {'expense_group_id': expense_group_id}
                
        except Exception as e:
            logger.error(f"Link expense group error: {str(e)}")
            return False, {'error': 'Failed to link expense group'}
    
    @staticmethod
    def unlink_expense_group(
        group_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Unlink travel group from expense engine group"""
        try:
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group:
                    return False, {'error': 'Group not found'}
                
                group.expense_group_id = None
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                return True, {'message': 'Expense group unlinked'}
                
        except Exception as e:
            logger.error(f"Unlink expense group error: {str(e)}")
            return False, {'error': 'Failed to unlink expense group'}
    
    @staticmethod
    def get_group_activities(
        group_id: int,
        user_id: int,
        limit: int = 50
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get recent group activities for real-time updates"""
        try:
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                activities = session.query(GroupActivity).filter(
                    GroupActivity.group_id == group_id
                ).order_by(GroupActivity.created_at.desc()).limit(limit).all()
                
                return True, {
                    'activities': [a.to_dict() for a in activities]
                }
                
        except Exception as e:
            logger.error(f"Get activities error: {str(e)}")
            return False, {'error': 'Failed to get activities'}

    @staticmethod
    def update_itinerary_document(
        group_id: int,
        user_id: int,
        content
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update itinerary document content
        
        Args:
            group_id: Group ID
            user_id: User updating
            content: New document content (str or dict)
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            import json as _json

            # Serialize dict/list content to JSON string for SQLite storage
            if isinstance(content, (dict, list)):
                content = _json.dumps(content)
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Get or create itinerary document
                itinerary = session.query(ItineraryDocument).filter(
                    ItineraryDocument.group_id == group_id
                ).first()
                
                if not itinerary:
                    itinerary = ItineraryDocument(
                        group_id=group_id,
                        content=content,
                        last_edited_by=user_id,
                        version=1
                    )
                    session.add(itinerary)
                else:
                    itinerary.content = content
                    itinerary.last_edited_by = user_id
                    itinerary.version = (itinerary.version or 0) + 1
                    itinerary.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Itinerary document updated for group {group_id}")
                
                return True, {'content': content, 'version': itinerary.version}
                
        except Exception as e:
            logger.error(f"Update itinerary document error: {str(e)}")
            return False, {'error': 'Failed to update itinerary document'}

    @staticmethod
    def get_expense_summary(
        group_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get expense summary for a linked expense group
        
        Args:
            group_id: Travel group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, expense_summary/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                group = session.query(TravelGroup).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Check if linked to expense group
                if not group.expense_group_id:
                    return True, {
                        'linked': False,
                        'total_spent': 0,
                        'per_person': 0,
                        'estimated_budget': float(group.estimated_budget or 0),
                        'member_count': 0,
                        'expense_count': 0
                    }
                
                # Get expense data from expense_engine
                try:
                    from app.domain.expenses.models import Expense
                    from app.domain.expenses.models import \
                        GroupMember as ExpenseGroupMember
                    from app.infrastructure.db.connection import \
                        get_db_session as get_expense_session
                    
                    with get_expense_session() as expense_session:
                        # Get total spent from expense group
                        total_spent = expense_session.query(
                            func.sum(Expense.amount)
                        ).filter(
                            Expense.group_id == group.expense_group_id,
                            Expense.is_deleted == False
                        ).scalar() or 0
                        
                        # Get member count
                        member_count = expense_session.query(ExpenseGroupMember).filter(
                            ExpenseGroupMember.group_id == group.expense_group_id,
                            ExpenseGroupMember.is_active == True
                        ).count()
                        
                        # Get expense count
                        expense_count = expense_session.query(Expense).filter(
                            Expense.group_id == group.expense_group_id,
                            Expense.is_deleted == False
                        ).count()
                        
                        per_person = float(total_spent) / max(1, member_count)
                        
                        # Calculate each member's share of expenses
                        member_expenses = []
                        members = expense_session.query(
                            ExpenseGroupMember.user_id
                        ).filter(
                            ExpenseGroupMember.group_id == group.expense_group_id,
                            ExpenseGroupMember.is_active == True
                        ).all()
                        
                        for member in members:
                            # Get user email from shared users table
                            user = expense_session.query(User).get(member.user_id)
                            if not user:
                                continue
                            
                            # Get sum of amounts for this member
                            member_total = expense_session.query(
                                func.sum(Expense.amount)
                            ).filter(
                                Expense.group_id == group.expense_group_id,
                                Expense.paid_by == member.user_id,
                                Expense.is_deleted == False
                            ).scalar() or 0
                            
                            member_expenses.append({
                                'user_id': member.user_id,
                                'email': user.email,
                                'total_spent': float(member_total)
                            })
                        
                        # Get user's balance/share from expense group
                        user_balance = 0.0
                        try:
                            if GroupBalance is not None:
                                balance_result = session.query(
                                    func.sum(GroupBalance.balance)
                                ).filter(
                                    GroupBalance.group_id == group.expense_group_id,
                                    GroupBalance.user_id == user_id
                                ).scalar()
                                if balance_result:
                                    user_balance = float(balance_result)
                        except Exception:
                            pass  # If balance not found, default to 0
                        
                        return True, {
                            'linked': True,
                            'expense_group_id': group.expense_group_id,
                            'total_spent': float(total_spent),
                            'per_person': round(per_person, 2),
                            'estimated_budget': float(group.estimated_budget or 0),
                            'member_count': member_count,
                            'expense_count': expense_count,
                            'member_expenses': member_expenses,
                            'user_id': user_id,
                            'user_share': user_balance  # User's balance/share
                        }
                        
                except Exception as e:
                    logger.error(f"Error fetching expense summary: {str(e)}")
                    return True, {
                        'linked': True,
                        'expense_group_id': group.expense_group_id,
                        'total_spent': 0,
                        'per_person': 0,
                        'estimated_budget': float(group.estimated_budget or 0),
                        'member_count': 0,
                        'expense_count': 0,
                        'error': 'Could not fetch expense data'
                    }
                
        except Exception as e:
            logger.error(f"Get expense summary error: {str(e)}")
            return False, {'error': 'Failed to get expense summary'}
    
    @staticmethod
    def remove_member(group_id: int, member_id: int, requester_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove a member from the group (only owner can remove others)
        Also removes them from linked expense group
        """
        try:
            with get_db_session() as session:
                # Get the group
                group = session.query(TravelGroup).filter(TravelGroup.id == group_id).first()
                if not group:
                    return False, {'error': 'Group not found'}
                
                # Check permissions - only owner can remove others (except themselves)
                if group.created_by != requester_id:
                    return False, {'error': 'Only the group owner can remove members'}
                
                # Prevent owner from removing themselves
                if member_id == group.created_by:
                    return False, {'error': 'Group owner cannot remove themselves from the group'}
                
                # Get the member to remove
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == member_id
                ).first()
                
                if not member:
                    return False, {'error': 'Member not found in group'}
                
                # Get member details for response
                user = session.query(User).filter(User.id == member_id).first()
                member_name = user.display_name if user else "Unknown User"
                member_email = user.email if user else "unknown@email.com"
                
                # Remove from expense group if linked
                if group.expense_group_id:
                    try:
                        from expense_engine.services.group_service import \
                            group_service as group_service
                        success, result = group_service.remove_member(
                            group_id=group.expense_group_id,
                            member_email=member_email,
                            requester_id=requester_id
                        )
                        if not success:
                            logger.warning(f"Failed to remove member from expense group: {result}")
                    except Exception as e:
                        logger.error(f"Error removing member from expense group: {str(e)}")
                
                # Remove from travel group
                session.delete(member)
                session.commit()
                
                logger.info(f"Member {member_name} ({member_id}) removed from group {group_id} by owner {requester_id}")
                
                return True, {
                    'message': f'{member_name} has been removed from the group and expenses',
                    'removed_member': {
                        'id': member_id,
                        'name': member_name,
                        'email': member_email
                    },
                    'reinvite_message': f'To add {member_name} back to the group, send them a new invitation'
                }
                
        except Exception as e:
            logger.error(f"Remove member error: {str(e)}")
            return False, {'error': 'Failed to remove member'}
    
    @staticmethod
    def get_group_members_detailed(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get detailed member list with owner indicator and permissions
        """
        try:
            with get_db_session() as session:
                # Verify user is member of this group
                is_member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id
                ).first()
                
                if not is_member:
                    return False, {'error': 'Access denied - not a member of this group'}
                
                # Get group details
                group = session.query(TravelGroup).filter(TravelGroup.id == group_id).first()
                if not group:
                    return False, {'error': 'Group not found'}
                
                # Get all members with user details
                members_query = session.query(TripMember, User).join(
                    User, TripMember.user_id == User.id
                ).filter(TripMember.group_id == group_id)
                
                members = []
                for member, user in members_query.all():
                    is_owner = user.id == group.created_by
                    # can_remove: I'm the owner AND this member is not the owner AND it's not me
                    can_remove = (user_id == group.created_by) and not is_owner and (user.id != user_id)
                    
                    members.append({
                        'id': user.id,
                        'name': user.display_name or user.email.split('@')[0],
                        'email': user.email,
                        'is_owner': is_owner,
                        'can_remove': can_remove,
                        'joined_at': member.joined_at.isoformat() if member.joined_at else None,
                        'role': 'Owner' if is_owner else 'Member'
                    })
                
                # Sort with owner first
                members.sort(key=lambda m: (not m['is_owner'], m['name']))
                
                return True, {
                    'members': members,
                    'total_count': len(members),
                    'group_name': group.name,
                    'is_owner': user_id == group.created_by
                }
                
        except Exception as e:
            logger.error("Get detailed members error: %s", e)
            return False, {'error': 'Failed to get member details'}

    @staticmethod
    def leave_group(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Allow a non-owner member to leave a group.

        Args:
            group_id: ID of the group
            user_id: ID of the user leaving

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            with get_db_session() as session:
                group = session.query(TravelGroup).filter(
                    TravelGroup.id == group_id
                ).first()

                if not group:
                    return False, {'error': 'Group not found'}

                if group.created_by == user_id:
                    return False, {
                        'error': 'Group owner cannot leave. Transfer ownership or delete the group.'
                    }

                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                ).first()

                if not member:
                    return False, {'error': 'You are not a member of this group'}

                user = session.query(User).get(user_id)
                display_name = user.display_name if user else 'Unknown'

                session.delete(member)

                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='member_left',
                    details=f'{display_name} left the group',
                )
                session.add(activity)
                session.commit()

                logger.info("User %s left group %s", user_id, group_id)
                return True, {'message': 'You have left the group'}

        except Exception as e:
            logger.error("Leave group error: %s", e)
            return False, {'error': 'Failed to leave group'}


# Singleton instance
group_service = GroupService()
group_service = GroupService()
