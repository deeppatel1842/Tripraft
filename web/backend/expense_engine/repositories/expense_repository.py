"""
Expense Repository
Handles expense data access and queries
"""

from typing import List, Optional, Dict
from datetime import datetime
import logging

from .base import BaseRepository
from ..config import firestore_collections
from ..models.expense import Expense
from ..exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class ExpenseRepository(BaseRepository[Expense]):
    """
    Repository for expense management
    Handles expense CRUD and queries with pagination
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.EXPENSES
    
    def get_group_expenses(
        self,
        group_id: str,
        limit: int = 50,
        offset: int = 0,
        order_by: str = 'expense_date',
        order_direction: str = 'DESCENDING',
        include_deleted: bool = False
    ) -> Dict[str, any]:
        """
        Get expenses for a group with pagination
        
        Args:
            group_id: Group ID
            limit: Maximum expenses to return
            offset: Number of expenses to skip
            order_by: Field to order by
            order_direction: Sort direction
            include_deleted: Whether to include soft-deleted expenses
            
        Returns:
            Dict with expenses and pagination info
        """
        try:
            # Get all expenses for group first (Firestore doesn't support OR queries easily)
            all_expenses = self.query(
                filters=[('group_id', '==', group_id)],
                order_by=(order_by, order_direction),
                limit=500  # Get more to account for deleted ones
            )
            
            # Filter expenses based on include_deleted flag
            if include_deleted:
                # Include all expenses (both active and deleted)
                filtered_expenses = all_expenses
            else:
                # Filter out deleted expenses in Python
                # This handles both is_deleted=True AND missing is_deleted field
                filtered_expenses = [
                    exp for exp in all_expenses 
                    if not exp.get('is_deleted', False)
                ]
            
            total = len(filtered_expenses)
            
            # Apply pagination
            paginated = filtered_expenses[offset:offset + limit]
            
            return {
                'expenses': paginated,
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(paginated) < total
            }
            
        except Exception as exc:
            logger.error("Error getting group expenses: %s", str(exc))
            raise
    
    def get_user_expenses(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get expenses where user is payer or participant
        
        Args:
            user_id: User ID
            group_id: Optional group filter
            limit: Maximum expenses to return
            
        Returns:
            List of expense documents
        """
        try:
            filters = [('participants', 'array_contains', user_id)]
            if group_id:
                filters.append(('group_id', '==', group_id))
            
            expenses = self.query(
                filters=filters,
                order_by=('expense_date', 'DESCENDING'),
                limit=limit
            )
            
            return expenses
            
        except Exception as exc:
            logger.error("Error getting user expenses: %s", str(exc))
            raise
    
    def get_expenses_by_category(
        self,
        group_id: str,
        category: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get expenses by category with optional date range
        
        Args:
            group_id: Group ID
            category: Expense category
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of expense documents
        """
        try:
            filters = [
                ('group_id', '==', group_id),
                ('category', '==', category)
            ]
            
            if start_date:
                filters.append(('expense_date', '>=', start_date))
            if end_date:
                filters.append(('expense_date', '<=', end_date))
            
            expenses = self.query(
                filters=filters,
                order_by=('expense_date', 'DESCENDING')
            )
            
            return expenses
            
        except Exception as exc:
            logger.error("Error getting expenses by category: %s", str(exc))
            raise
    
    def get_expenses_by_date_range(
        self,
        group_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Get expenses within a date range
        
        Args:
            group_id: Group ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of expense documents
        """
        try:
            expenses = self.query(
                filters=[
                    ('group_id', '==', group_id),
                    ('expense_date', '>=', start_date),
                    ('expense_date', '<=', end_date)
                ],
                order_by=('expense_date', 'DESCENDING')
            )
            
            return expenses
            
        except Exception as exc:
            logger.error("Error getting expenses by date range: %s", str(exc))
            raise
    
    def get_expense_by_linked_id(
        self,
        group_id: str,
        linked_expense_id: str
    ) -> Optional[Dict]:
        """
        Find expense by linked expense ID
        Used for settlement tracking
        
        Args:
            group_id: Group ID
            linked_expense_id: Linked expense ID
            
        Returns:
            Expense document or None
        """
        try:
            results = self.query(
                filters=[
                    ('group_id', '==', group_id),
                    ('linked_expense_id', '==', linked_expense_id)
                ],
                limit=1
            )
            
            return results[0] if results else None
            
        except Exception as exc:
            logger.error("Error getting linked expense: %s", str(exc))
            raise
    
    def soft_delete_expense(self, expense_id: str) -> None:
        """
        Soft delete an expense (mark as deleted)
        Actual deletion requires balance reversal
        
        Args:
            expense_id: Expense ID
        """
        try:
            expense_data = self.get_by_id(expense_id)
            if not expense_data:
                raise ResourceNotFoundError(f"Expense {expense_id} not found")
            
            self.update(expense_id, {
                'is_deleted': True,
                'deleted_at': datetime.utcnow()
            })
            
            logger.info("Soft deleted expense: %s", expense_id)
            
        except Exception as exc:
            logger.error("Error soft deleting expense: %s", str(exc))
            raise
    
    def restore_expense(self, expense_id: str) -> None:
        """
        Restore a soft-deleted expense
        
        Args:
            expense_id: Expense ID
        """
        try:
            expense_data = self.get_by_id(expense_id)
            if not expense_data:
                raise ResourceNotFoundError(f"Expense {expense_id} not found")
            
            self.update(expense_id, {
                'is_deleted': False,
                'deleted_at': None
            })
            
            logger.info("Restored expense: %s", expense_id)
            
        except Exception as exc:
            logger.error("Error restoring expense: %s", str(exc))
            raise
