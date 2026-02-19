"""
Checklist Service for Group Planner
Handles all checklist operations using local SQL database
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.group_planner.models import (ChecklistItem, GroupActivity,
                                             TravelGroup, TripMember)
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)


class ChecklistService:
    """Service for checklist operations using SQL database"""
    
    @staticmethod
    def add_item(
        group_id: int,
        text: str,
        created_by_id: int,
        category: str = None,
        priority: str = 'medium',
        due_date: str = None,
        assigned_to_id: int = None
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
                
                # Create checklist item (only use fields that exist in model)
                checklist_item = ChecklistItem(
                    group_id=group_id,
                    item=text.strip(),
                    completed=False,
                    author_id=created_by_id
                )
                session.add(checklist_item)
                session.flush()
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
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
    def get_checklist(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all checklist items for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, items_list/error)
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
                
                items = session.query(ChecklistItem).filter(
                    ChecklistItem.group_id == group_id,
                    ChecklistItem.is_deleted == False
                ).order_by(ChecklistItem.created_at.asc()).all()
                
                return True, {'checklist': [i.to_dict() for i in items]}
                
        except Exception as e:
            logger.error(f"Get checklist error: {str(e)}")
            return False, {'error': 'Failed to get checklist'}
    
    @staticmethod
    def toggle_item(
        group_id: int,
        item_id: int,
        user_id: int
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
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(item)
                
                logger.info(f"Checklist item toggled: {item_id} to {item.completed}")
                
                return True, {
                    'id': str(item_id),
                    'completed': item.completed
                }
                
        except Exception as e:
            logger.error(f"Toggle checklist item error: {str(e)}")
            return False, {'error': 'Failed to toggle checklist item'}
    
    @staticmethod
    def update_item(
        item_id: int,
        user_id: int,
        text: str = None,
        category: str = None,
        priority: str = None,
        due_date: str = None,
        assigned_to_id: int = None,
        completed: bool = None
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
                if text is not None:
                    item.item = text.strip()
                
                if completed is not None:
                    item.completed = completed
                    if completed:
                        item.completed_by = user_id
                        item.completed_at = datetime.now(timezone.utc)
                    else:
                        item.completed_by = None
                        item.completed_at = None
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
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
        group_id: int,
        item_id: int,
        user_id: int
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
                group = session.query(TravelGroup).get(group_id)
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
