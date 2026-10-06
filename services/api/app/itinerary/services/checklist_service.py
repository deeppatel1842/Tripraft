# Purpose: Checklist Service for Group Planner Handles all checklist operations using local SQL database.
"""
Checklist Service for Group Planner
Handles all checklist operations using local SQL database
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.trips.models import (ChecklistItem, GroupActivity,
                                             TravelGroup, TripMember)
from app.core.config import Config
from app.core.sanitize import sanitize_text
from app.core.db.connection import get_db_session
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)
_UNSET = object()


def _parse_due_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date/datetime into a UTC datetime for persistence."""
    if value is None or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except (TypeError, ValueError) as exc:
        raise ValueError('due_date must be an ISO-8601 date or datetime') from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_assignee(session, group_id: str, assigned_to_id: Optional[str]) -> bool:
    """An assignee must be an active member of the same travel group."""
    if assigned_to_id is None:
        return True
    return session.query(TripMember).filter(
        TripMember.group_id == group_id,
        TripMember.user_id == assigned_to_id,
        TripMember.is_active == True,
    ).first() is not None


class ChecklistService:
    """Service for checklist operations using SQL database"""
    
    @staticmethod
    def add_item(
        group_id: str,
        text: str,
        created_by_id: str,
        category: str = None,
        priority: str = 'medium',
        due_date: str = None,
        assigned_to_id: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a checklist item
        
        Args:
            group_id: Group ID
            text: Item text
            created_by_id: User adding the item
            category: Optional category
            priority: Priority level (low, medium, high)
            due_date: Optional due date string
            assigned_to_id: Optional user ID to assign to
            
        Returns:
            Tuple of (success, item_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == created_by_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Validate item text
                if not text or not text.strip():
                    return False, {'error': 'Item text is required'}
                
                text = sanitize_text(text)
                if len(text) > Config.MAX_CHECKLIST_ITEM_LENGTH:
                    return False, {'error': f'Item text exceeds {Config.MAX_CHECKLIST_ITEM_LENGTH} characters'}
                
                if priority not in Config.PRIORITY_LEVELS:
                    return False, {'error': 'Invalid priority'}
                try:
                    parsed_due_date = _parse_due_date(due_date)
                except ValueError as exc:
                    return False, {'error': str(exc)}
                if not _validate_assignee(session, group_id, assigned_to_id):
                    return False, {'error': 'Assignee must be an active group member'}

                checklist_item = ChecklistItem(
                    group_id=group_id,
                    item=text.strip(),
                    completed=False,
                    author_id=created_by_id,
                    category=category.strip() if category else None,
                    priority=priority,
                    due_date=parsed_due_date,
                    assigned_to_id=assigned_to_id,
                )
                session.add(checklist_item)
                session.flush()
                
                # Update group timestamp
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=created_by_id,
                    action='checklist_item_added',
                    entity_type='checklist',
                    entity_id=checklist_item.id,
                    details={'item': text[:50]}  # Truncate for storage
                )
                session.add(activity)
                
                session.commit()
                session.refresh(checklist_item)
                
                logger.info(f"Checklist item added: {checklist_item.id} in group {group_id}")
                
                return True, {'item': checklist_item.to_dict()}
                
        except Exception as e:
            logger.error(f"Add checklist item error: {str(e)}")
            return False, {'error': 'Failed to add checklist item'}
    
    @staticmethod
    def get_checklist(group_id: str, user_id: str, page: int = 1, per_page: int = 50,
                      completed: Optional[bool] = None, q: Optional[str] = None,
                      sort_by: str = 'created_at', sort_order: str = 'asc') -> Tuple[bool, Dict[str, Any]]:
        """
        Get checklist items for a group (paginated, filterable, sortable)
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
                
                base_query = session.query(ChecklistItem).filter(
                    ChecklistItem.group_id == group_id,
                    ChecklistItem.is_deleted == False
                )
                
                # Apply filters
                if completed is not None:
                    base_query = base_query.filter(ChecklistItem.completed == completed)
                if q:
                    base_query = base_query.filter(ChecklistItem.item.ilike(f"%{q}%"))
                
                total = base_query.count()
                
                # Apply sorting
                sort_col = {
                    'created_at': ChecklistItem.created_at,
                    'completed': ChecklistItem.completed,
                }.get(sort_by, ChecklistItem.created_at)
                
                order_fn = sort_col.asc() if sort_order == 'asc' else sort_col.desc()
                
                items = base_query.options(
                    joinedload(ChecklistItem.author),
                    joinedload(ChecklistItem.completer),
                    joinedload(ChecklistItem.assignee),
                ).order_by(
                    order_fn
                ).offset((page - 1) * per_page).limit(per_page).all()
                
                return True, {
                    'checklist': [i.to_dict() for i in items],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': max(1, -(-total // per_page))
                    }
                }
                
        except Exception as e:
            logger.error(f"Get checklist error: {str(e)}")
            return False, {'error': 'Failed to get checklist'}
    
    @staticmethod
    def toggle_item(
        group_id: str,
        item_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Toggle checklist item completion
        
        Args:
            group_id: Group ID
            item_id: Checklist item ID
            user_id: User toggling
            
        Returns:
            Tuple of (success, item_data/error)
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
                
                # Get item
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id,
                    ChecklistItem.group_id == group_id,
                    ChecklistItem.is_deleted == False
                ).first()
                
                if not item:
                    return False, {'error': 'Checklist item not found'}
                
                # Toggle completion
                item.completed = not item.completed
                if item.completed:
                    item.completed_by = user_id
                    item.completed_at = datetime.now(timezone.utc)
                else:
                    item.completed_by = None
                    item.completed_at = None
                
                # Update group timestamp
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(item)
                
                logger.info(f"Checklist item toggled: {item_id} to {item.completed}")
                
                # Real-time broadcast
                try:
                    from app.trips.realtime.events import emit_to_group
                    emit_to_group(group_id, 'checklist:toggled', {
                        'item_id': item_id, 'completed': item.completed, 'user_id': user_id
                    })
                except Exception:
                    pass
                
                return True, {
                    'id': str(item_id),
                    'completed': item.completed
                }
                
        except Exception as e:
            logger.error(f"Toggle checklist item error: {str(e)}")
            return False, {'error': 'Failed to toggle checklist item'}
    
    @staticmethod
    def update_item(
        item_id: str,
        user_id: str,
        text: Any = _UNSET,
        category: Any = _UNSET,
        priority: Any = _UNSET,
        due_date: Any = _UNSET,
        assigned_to_id: Any = _UNSET,
        completed: Any = _UNSET,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update checklist item
        
        Args:
            item_id: Checklist item ID
            user_id: User updating
            text: New item text (optional)
            category: Category (optional)
            priority: Priority level (optional)
            due_date: Due date (optional)
            assigned_to_id: User to assign (optional)
            completed: Completion status (optional)
            
        Returns:
            Tuple of (success, item_data/error)
        """
        try:
            with get_db_session() as session:
                # Get item first to find group_id
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id,
                    ChecklistItem.is_deleted == False
                ).first()
                
                if not item:
                    return False, {'error': 'Checklist item not found'}
                
                group_id = item.group_id
                
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Update fields if provided
                if text is not _UNSET:
                    cleaned_text = sanitize_text(text)
                    if not cleaned_text:
                        return False, {'error': 'Item text is required'}
                    if len(cleaned_text) > Config.MAX_CHECKLIST_ITEM_LENGTH:
                        return False, {'error': f'Item text exceeds {Config.MAX_CHECKLIST_ITEM_LENGTH} characters'}
                    item.item = cleaned_text

                if category is not _UNSET:
                    item.category = category.strip() if category else None
                if priority is not _UNSET:
                    if priority not in Config.PRIORITY_LEVELS:
                        return False, {'error': 'Invalid priority'}
                    item.priority = priority
                if due_date is not _UNSET:
                    try:
                        item.due_date = _parse_due_date(due_date)
                    except ValueError as exc:
                        return False, {'error': str(exc)}
                if assigned_to_id is not _UNSET:
                    if not _validate_assignee(session, group_id, assigned_to_id):
                        return False, {'error': 'Assignee must be an active group member'}
                    item.assigned_to_id = assigned_to_id

                if completed is not _UNSET:
                    item.completed = completed
                    if completed:
                        item.completed_by = user_id
                        item.completed_at = datetime.now(timezone.utc)
                    else:
                        item.completed_by = None
                        item.completed_at = None
                
                # Update group timestamp
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(item)
                
                logger.info(f"Checklist item updated: {item_id}")
                
                return True, {'item': item.to_dict()}
                
        except Exception as e:
            logger.error(f"Update checklist item error: {str(e)}")
            return False, {'error': 'Failed to update checklist item'}
    
    @staticmethod
    def delete_item(
        group_id: str,
        item_id: str,
        user_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a checklist item (soft delete)
        
        Args:
            group_id: Group ID
            item_id: Checklist item ID
            user_id: User deleting
            
        Returns:
            Tuple of (success, message/error)
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
                
                # Get item
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id,
                    ChecklistItem.group_id == group_id,
                    ChecklistItem.is_deleted == False
                ).first()
                
                if not item:
                    return False, {'error': 'Checklist item not found'}
                
                # Soft delete
                item.is_deleted = True
                
                # Update group timestamp
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Checklist item deleted: {item_id}")
                
                return True, {'message': 'Checklist item deleted'}
                
        except Exception as e:
            logger.error(f"Delete checklist item error: {str(e)}")
            return False, {'error': 'Failed to delete checklist item'}


# Singleton instance
checklist_service = ChecklistService()
