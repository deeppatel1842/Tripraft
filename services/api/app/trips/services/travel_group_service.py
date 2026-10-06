# Purpose: Group Service for Group Planner Handles all group operations using unified SQL database (pateldeep.db).
"""
Group Service for Group Planner
Handles all group operations using unified SQL database (pateldeep.db)


Uses shared users table with expense_engine
"""

import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Config
from app.trips.models import (GroupActivity, ItineraryDocument,
                                             TravelGroup, TripMember)
from app.auth.models import User
from app.core.db.connection import get_db_session
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Import expense-engine models for cross-module queries
try:
    from app.expenses.models import GroupBalance
except ImportError:
    GroupBalance = None

logger = logging.getLogger(__name__)


def generate_group_code(length: int = Config.GROUP_CODE_LENGTH) -> str:
    """Generate a unique group invitation code"""
    chars = Config.GROUP_CODE_CHARSET
    return ''.join(secrets.choice(chars) for _ in range(length))


class GroupService:
    """Service for group operations using SQL database"""
    
    @staticmethod
    def create_group(
        user_id: str,
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
        budget_currency: str = Config.DEFAULT_CURRENCY
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
                user = session.get(User, user_id)
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
                    except (ValueError, TypeError):
                        pass
                if end_date:
                    try:
                        parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                    except (ValueError, TypeError):
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
    def get_group(group_id: str, user_id: str, include_all: bool = True) -> Tuple[bool, Dict[str, Any]]:
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
                
                group = session.get(TravelGroup, group_id)
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
    def get_user_groups(user_id: str, page: int = 1, per_page: int = 20) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all groups for a user (paginated)
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Items per page
            
        Returns:
            Tuple of (success, groups_list with pagination/error)
        """
        try:
            with get_db_session() as session:
                base_query = session.query(TripMember, TravelGroup).join(
                    TravelGroup, TripMember.group_id == TravelGroup.id
                ).filter(
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                    TravelGroup.is_active == True
                )
                total = base_query.count()
                memberships = base_query.options(
                    joinedload(TravelGroup.members).joinedload(TripMember.user)
                ).order_by(
                    TravelGroup.updated_at.desc()
                ).offset((page - 1) * per_page).limit(per_page).all()
                
                groups = []
                for membership, group in memberships:
                    group_data = group.to_dict(include_members=True)
                    group_data['my_role'] = membership.role
                    groups.append(group_data)
                
                return True, {
                    'groups': groups,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': max(1, -(-total // per_page))
                    }
                }
                
        except Exception as e:
            logger.error(f"Get user groups error: {str(e)}")
            return False, {'error': 'Failed to get groups'}
    
    @staticmethod
    def update_group(
        group_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        destination: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        estimated_budget: Optional[float] = None,
        budget_currency: Optional[str] = None,
        expected_updated_at: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update group details with optimistic locking.
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            expected_updated_at: If provided, ISO timestamp to check against (409 on mismatch)
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
                
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Optimistic locking: reject if updated_at mismatch
                if expected_updated_at is not None and group.updated_at:
                    try:
                        expected_dt = datetime.fromisoformat(expected_updated_at.replace('Z', '+00:00'))
                        if group.updated_at.replace(tzinfo=None) != expected_dt.replace(tzinfo=None):
                            return False, {
                                'error': 'Conflict: group was modified by another user',
                                'status': 409,
                                'current_updated_at': group.updated_at.isoformat()
                            }
                    except (ValueError, AttributeError):
                        pass
                
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
                    except Exception:
                        pass
                if end_date is not None:
                    try:
                        group.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                    except Exception:
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
    def delete_group(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
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
                group = session.get(TravelGroup, group_id)
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
        group_id: str,
        user_id: str,
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
                group = session.get(TravelGroup, group_id)
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
        group_id: str,
        user_id: str,
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
                
                group = session.get(TravelGroup, group_id)
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
    def is_member(group_id: str, user_id: str) -> bool:
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
        group_id: str,
        user_id: str,
        expense_group_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Link travel group to expense engine group"""
        try:
            with get_db_session() as session:
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}

                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}
                if (
                    member.role not in {'creator', 'admin'}
                    and str(group.created_by) != str(user_id)
                ):
                    return False, {
                        'error': 'Only the travel group creator or admin may link an expense group',
                        'status_code': 403,
                    }
                
                group.expense_group_id = expense_group_id
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                return True, {'expense_group_id': expense_group_id}
                
        except Exception as e:
            logger.error(f"Link expense group error: {str(e)}")
            return False, {'error': 'Failed to link expense group'}
    
    @staticmethod
    def unlink_expense_group(
        group_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Unlink travel group from expense engine group"""
        try:
            with get_db_session() as session:
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}

                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}
                if (
                    member.role not in {'creator', 'admin'}
                    and str(group.created_by) != str(user_id)
                ):
                    return False, {
                        'error': 'Only the travel group creator or admin may unlink an expense group',
                        'status_code': 403,
                    }
                
                group.expense_group_id = None
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                return True, {'message': 'Expense group unlinked'}
                
        except Exception as e:
            logger.error(f"Unlink expense group error: {str(e)}")
            return False, {'error': 'Failed to unlink expense group'}
    
    @staticmethod
    def get_group_activities(
        group_id: str,
        user_id: str,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get recent group activities (paginated)"""
        try:
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                base_query = session.query(GroupActivity).filter(
                    GroupActivity.group_id == group_id
                )
                total = base_query.count()
                activities = base_query.options(
                    joinedload(GroupActivity.user)
                ).order_by(
                    GroupActivity.created_at.desc()
                ).offset((page - 1) * per_page).limit(per_page).all()
                
                return True, {
                    'activities': [a.to_dict() for a in activities],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': max(1, -(-total // per_page))
                    }
                }
                
        except Exception as e:
            logger.error(f"Get activities error: {str(e)}")
            return False, {'error': 'Failed to get activities'}

    @staticmethod
    def update_itinerary_document(
        group_id: str,
        user_id: str,
        content,
        expected_version: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update itinerary document content with optimistic locking.
        
        Args:
            group_id: Group ID
            user_id: User updating
            content: New document content (str or dict)
            expected_version: If provided, check version matches before updating (409 on mismatch)
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            import json as _json

            # Sanitize and enforce size limit
            from app.core.config import Config as _Cfg
            from app.core.sanitize import sanitize_rich_text
            if isinstance(content, str):
                content = sanitize_rich_text(content)
            raw = _json.dumps(content) if isinstance(content, (dict, list)) else content
            if len(raw.encode('utf-8')) > _Cfg.MAX_ITINERARY_SIZE:
                return False, {'error': f'Itinerary content exceeds {_Cfg.MAX_ITINERARY_SIZE // 1024}KB limit'}

            # Serialize dict/list content to JSON string for SQLite storage
            if isinstance(content, (dict, list)):
                content = _json.dumps(content)
            with get_db_session() as session:
                # Check membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}
                
                group = session.get(TravelGroup, group_id)
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
                    # Optimistic locking: reject if version mismatch
                    if expected_version is not None and itinerary.version != expected_version:
                        return False, {
                            'error': 'Conflict: itinerary was modified by another user',
                            'status': 409,
                            'current_version': itinerary.version
                        }
                    itinerary.content = content
                    itinerary.last_edited_by = user_id
                    itinerary.version = (itinerary.version or 0) + 1
                    itinerary.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Itinerary document updated for group {group_id}")
                
                # Real-time broadcast
                try:
                    from app.trips.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'itinerary:updated', {
                        'version': itinerary.version, 'user_id': user_id
                    })
                except Exception:
                    pass
                
                return True, {'content': content, 'version': itinerary.version}
                
        except Exception as e:
            logger.error(f"Update itinerary document error: {str(e)}")
            return False, {'error': 'Failed to update itinerary document'}

    @staticmethod
    def get_expense_summary(
        group_id: str,
        user_id: str
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
                
                group = session.get(TravelGroup, group_id)
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
                    from app.expenses.models import Expense
                    from app.expenses.models import \
                        GroupMember as ExpenseGroupMember
                    from app.core.db.connection import \
                        get_db_session as get_expense_session
                    
                    with get_expense_session() as expense_session:
                        # A travel-group link alone is not authorization to
                        # expose another expense group's balances.  Validate
                        # the requester belongs to the linked target too.
                        expense_membership = expense_session.query(
                            ExpenseGroupMember
                        ).filter(
                            ExpenseGroupMember.group_id == group.expense_group_id,
                            ExpenseGroupMember.user_id == user_id,
                            ExpenseGroupMember.is_active == True,
                        ).first()
                        if not expense_membership:
                            return False, {
                                'error': 'Not a member of the linked expense group',
                                'status_code': 403,
                            }

                        # Aggregate totals in a single query
                        summary = expense_session.query(
                            func.sum(Expense.amount).label('total_spent'),
                            func.count(Expense.id).label('expense_count'),
                        ).filter(
                            Expense.group_id == group.expense_group_id,
                            Expense.is_deleted == False
                        ).one()
                        
                        total_spent = float(summary.total_spent or 0)
                        expense_count = summary.expense_count or 0
                        
                        # Get member count
                        member_count = expense_session.query(ExpenseGroupMember).filter(
                            ExpenseGroupMember.group_id == group.expense_group_id,
                            ExpenseGroupMember.is_active == True
                        ).count()
                        
                        per_person = total_spent / max(1, member_count)
                        
                        # Per-member spend via SQL GROUP BY instead of N+1 loop
                        member_totals = expense_session.query(
                            Expense.paid_by,
                            func.sum(Expense.amount).label('total'),
                        ).filter(
                            Expense.group_id == group.expense_group_id,
                            Expense.is_deleted == False,
                        ).group_by(Expense.paid_by).all()

                        payer_ids = [row.paid_by for row in member_totals]
                        users_map = {}
                        if payer_ids:
                            users_list = expense_session.query(
                                User.id, User.email
                            ).filter(User.id.in_(payer_ids)).all()
                            users_map = {u.id: u.email for u in users_list}

                        member_expenses = [
                            {
                                'user_id': row.paid_by,
                                'email': users_map.get(row.paid_by, ''),
                                'total_spent': float(row.total),
                            }
                            for row in member_totals
                        ]
                        
                        # Get user's balance/share from expense group
                        user_balance = 0.0
                        try:
                            if GroupBalance is not None:
                                balance_result = expense_session.query(
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
    def remove_member(group_id: str, member_id: str, requester_id: str) -> Tuple[bool, Dict[str, Any]]:
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
    def update_member_role(group_id: str, member_id: str, new_role: str, requester_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Update a member's role within the group (admin only, cannot change creator)"""
        VALID_ROLES = ('admin', 'member', 'viewer')
        if new_role not in VALID_ROLES:
            return False, {'error': f'Invalid role. Must be one of: {", ".join(VALID_ROLES)}'}

        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == member_id,
                    TripMember.is_active == True
                ).first()

                if not member:
                    return False, {'error': 'Member not found in group'}

                if member.role == 'creator':
                    return False, {'error': 'Cannot change the creator role'}

                member.role = new_role
                session.commit()

                logger.info(f"Member {member_id} role updated to {new_role} in group {group_id} by {requester_id}")
                return True, {'member': member.to_dict()}

        except Exception as e:
            logger.error(f"Update member role error: {str(e)}")
            return False, {'error': 'Failed to update member role'}

    @staticmethod
    def get_group_members_detailed(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
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
                        'user_id': user.id,
                        'name': user.display_name or user.email.split('@')[0],
                        'display_name': user.display_name or user.email.split('@')[0],
                        'email': user.email,
                        'photo_url': getattr(user, 'photo_url', None),
                        'is_owner': is_owner,
                        'is_creator': member.role == 'creator',
                        'can_remove': can_remove,
                        'joined_at': member.joined_at.isoformat() if member.joined_at else None,
                        'role': member.role
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
    def leave_group(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
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

                user = session.get(User, user_id)
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

    # ------------------------------------------------------------------
    # C7.3 — Trip Cloning
    # ------------------------------------------------------------------

    @staticmethod
    def clone_group(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Clone a group as a new template.
        Copies places, checklist items, and poll structure (not votes).
        Resets dates, clears members (only creator).
        """
        from app.trips.models import ChecklistItem, Place, Poll
        try:
            with get_db_session() as session:
                original = session.get(TravelGroup, group_id)
                if not original or not original.is_active:
                    return False, {'error': 'Group not found'}

                # Verify membership
                if not GroupService.is_member(group_id, user_id):
                    return False, {'error': 'Not a member of this group'}

                # Generate unique code
                code = generate_group_code()
                while session.query(TravelGroup).filter_by(group_code=code).first():
                    code = generate_group_code()

                clone = TravelGroup(
                    name=f'{original.name} (Copy)',
                    description=original.description,
                    destination=original.destination,
                    destination_lat=original.destination_lat,
                    destination_lng=original.destination_lng,
                    destination_type=original.destination_type,
                    destination_id=original.destination_id,
                    group_code=code,
                    created_by=user_id,
                    estimated_budget=original.estimated_budget,
                    budget_currency=original.budget_currency,
                )
                session.add(clone)
                session.flush()

                # Add creator as member
                session.add(TripMember(
                    group_id=clone.id,
                    user_id=user_id,
                    role='creator',
                ))

                # Copy places (no votes)
                places = session.query(Place).filter(
                    Place.group_id == group_id, Place.is_deleted == False
                ).all()
                for p in places:
                    session.add(Place(
                        group_id=clone.id, name=p.name, description=p.description,
                        address=p.address, latitude=p.latitude, longitude=p.longitude,
                        category=p.category, suggested_duration=p.suggested_duration,
                        photo_url=p.photo_url, website=p.website, rating=p.rating,
                        added_by=user_id,
                    ))

                # Copy checklist items (unchecked)
                items = session.query(ChecklistItem).filter(
                    ChecklistItem.group_id == group_id, ChecklistItem.is_deleted == False
                ).all()
                for item in items:
                    session.add(ChecklistItem(
                        group_id=clone.id, item=item.item, completed=False, author_id=user_id,
                    ))

                # Copy poll structure (no votes)
                polls = session.query(Poll).filter(
                    Poll.group_id == group_id, Poll.is_deleted == False
                ).all()
                for poll in polls:
                    session.add(Poll(
                        group_id=clone.id, name=poll.name, options=poll.options,
                        is_multiple_choice=poll.is_multiple_choice, created_by=user_id,
                    ))

                # Activity log
                session.add(GroupActivity(
                    group_id=clone.id, user_id=user_id,
                    action='group_created', details={'cloned_from': group_id},
                ))

                session.commit()
                session.refresh(clone)
                logger.info('Group %s cloned to %s by user %s', group_id, clone.id, user_id)
                return True, {'group': clone.to_dict()}

        except Exception as e:
            logger.error('Clone group error: %s', e)
            return False, {'error': 'Failed to clone group'}

    # ------------------------------------------------------------------
    # C7.4 — Join by Code
    # ------------------------------------------------------------------

    @staticmethod
    def join_by_code(code: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Join a group using its group_code."""
        try:
            with get_db_session() as session:
                group = session.query(TravelGroup).filter(
                    TravelGroup.group_code == code,
                    TravelGroup.is_active == True,
                ).first()
                if not group:
                    return False, {'error': 'Invalid group code'}

                # Check if already a member
                existing = session.query(TripMember).filter(
                    TripMember.group_id == group.id,
                    TripMember.user_id == user_id,
                ).first()
                if existing:
                    if existing.is_active:
                        return False, {'error': 'Already a member of this group'}
                    existing.is_active = True
                else:
                    session.add(TripMember(
                        group_id=group.id, user_id=user_id, role='member',
                    ))

                session.add(GroupActivity(
                    group_id=group.id, user_id=user_id,
                    action='member_joined', details={'via': 'group_code'},
                ))
                session.commit()

                # Notify + real-time
                try:
                    from app.notifications.services.notification_service import \
                        notification_service
                    notification_service.notify_group_members(
                        group_id=group.id, exclude_user_id=user_id,
                        type='member_joined', title='A new member joined via invite code',
                        data={'user_id': user_id},
                    )
                except Exception:
                    pass
                try:
                    from app.trips.realtime.events import \
                        emit_to_group
                    emit_to_group(group.id, 'member:joined', {'user_id': user_id})
                except Exception:
                    pass

                logger.info('User %s joined group %s via code', user_id, group.id)
                return True, {'group_id': group.id, 'group_name': group.name}

        except Exception as e:
            logger.error('Join by code error: %s', e)
            return False, {'error': 'Failed to join group'}


# Singleton instance
group_service = GroupService()
