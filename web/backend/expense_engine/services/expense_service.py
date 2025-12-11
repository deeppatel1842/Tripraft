"""
Expense Service
Business logic for expense management

Phase 6: Added denormalized data maintenance
Phase 12: Added expense edit history tracking
Phase 13: Added Redis caching for expenses
"""

from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal
from firebase_admin import firestore
import logging

from ..repositories import (
    ExpenseRepository, GroupRepository, BalanceRepository,
    GroupSummaryRepository, UserExpenseRepository,
    ExpenseHistoryRepository, SnapshotRepository
)
from ..services.balance_service import BalanceService
from ..models.expense import Expense, ExpenseSplit
from ..exceptions import (
    ValidationError,
    ResourceNotFoundError
)
from ..config import redis_config

logger = logging.getLogger(__name__)

# Cache imports with graceful fallback
try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

# Fields allowed when creating Expense model from Firestore data
ALLOWED_EXPENSE_FIELDS = {
    'expense_id', 'group_id', 'description', 'amount', 'currency',
    'paid_by', 'paid_by_name', 'split_type', 'splits', 'created_by',
    'category', 'notes', 'receipt_url', 'expense_date', 'is_deleted',
    'deleted_at', 'created_at', 'updated_at', 'is_edited'
}


def _invalidate_expense_cache(expense_id: str, group_id: str, group_repo=None, current_user_id=None) -> None:
    """
    Invalidate cache entries when an expense changes.
    
    Clears:
    - Individual expense cache
    - Group expenses list cache (all pages)
    - Group summary cache (contains expense counts/totals)
    - Group balances cache (affected by expense changes)
    - Expense history cache (Phase 19.1)
    
    Phase 17.9: REMOVED mega-bootstrap invalidation for OTHER users
    - Other users get real-time updates via Firestore listeners
    - This eliminates the API call cascade that caused excessive /user/groups calls
    - Current user already has optimistic update from frontend
    
    Args:
        expense_id: The expense ID that changed
        group_id: The group ID containing the expense
        group_repo: Optional GroupRepository (no longer used for member lookups)
        current_user_id: The user who made the change (their cache is handled by frontend)
    """
    if not CACHE_ENABLED:
        return
    try:
        cache = get_cache_manager()
        if cache and cache.is_available():
            # Clear individual expense cache
            cache.delete(redis_config.KEY_EXPENSE.format(eid=expense_id))
            # Clear group expenses list (all pages - use pattern)
            cache.delete_pattern(f"expense:group_expenses:{group_id}:*")
            # Clear group summary (contains expense totals)
            cache.delete(redis_config.KEY_GROUP_SUMMARY.format(gid=group_id))
            # Clear group balances (affected by expense changes)
            cache.delete(redis_config.KEY_GROUP_BALANCES.format(gid=group_id))
            # Phase 19.1: Clear expense history cache (new history entry added)
            cache.delete(redis_config.KEY_EXPENSE_HISTORY.format(eid=expense_id))
            
            # Phase 17.9: DO NOT invalidate mega-bootstrap for ANY users
            # - Current user: Has optimistic update from frontend mutation
            # - Other users: Get real-time updates via Firestore listeners
            # This eliminates the API call cascade that caused 22+ /user/groups calls
            #
            # Previously (Phase 17.5): We invalidated OTHER users' caches,
            # but this caused them to refetch data even though Firestore listeners
            # would update their UI in real-time anyway.
            
            logger.debug("Cache invalidated for expense %s in group %s (no mega-bootstrap invalidation)", 
                        expense_id, group_id)
    except Exception as e:
        logger.warning("Failed to invalidate expense cache: %s", str(e))


def _write_through_expense_cache(expense_id: str, expense_data: Dict) -> None:
    """
    Phase 17.3: Write-through cache pattern.
    
    Instead of just invalidating, update the cache with the new expense data.
    This ensures the next read gets the updated value from cache instead of Firestore.
    
    Note: Group expenses list cache is still invalidated since updating list caches
    is complex (ordering, pagination).
    
    Args:
        expense_id: The expense ID
        expense_data: The complete expense data to cache
    """
    if not CACHE_ENABLED:
        return
    try:
        cache = get_cache_manager()
        if cache and cache.is_available():
            # Write new expense data to cache
            cache_key = redis_config.KEY_EXPENSE.format(eid=expense_id)
            cache.set(cache_key, expense_data, ttl=redis_config.TTL_EXPENSE)
            logger.debug("Write-through cache updated for expense %s", expense_id)
    except Exception as e:
        logger.warning("Failed to write-through expense cache: %s", str(e))


def expense_from_firestore(expense_data: dict) -> 'Expense':
    """
    Convert Firestore expense data to Expense model.
    Handles converting splits from dicts to ExpenseSplit objects.
    
    Args:
        expense_data: Raw expense data from Firestore
        
    Returns:
        Expense model instance
    """
    # Filter to allowed fields only
    clean_data = {k: v for k, v in expense_data.items() if k in ALLOWED_EXPENSE_FIELDS}
    
    # Convert splits from dicts to ExpenseSplit objects if needed
    if 'splits' in clean_data and clean_data['splits']:
        clean_data['splits'] = [
            ExpenseSplit(
                user_id=s.get('user_id'),
                amount=Decimal(str(s.get('amount', 0))),
                user_name=s.get('user_name'),
                percentage=s.get('percentage'),
                shares=s.get('shares')
            ) if isinstance(s, dict) else s
            for s in clean_data['splits']
        ]
    
    return Expense(**clean_data)


class ExpenseService:
    """
    Service for expense management operations
    Handles expense CRUD with balance updates
    
    Phase 6: Maintains denormalized data in GROUP_SUMMARIES and USER_EXPENSES
    Phase 12: Tracks all changes in expense_history collection
    """
    
    def __init__(
        self,
        expense_repo: Optional[ExpenseRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        balance_repo: Optional[BalanceRepository] = None,
        group_summary_repo: Optional[GroupSummaryRepository] = None,
        user_expense_repo: Optional[UserExpenseRepository] = None,
        history_repo: Optional[ExpenseHistoryRepository] = None,
        snapshot_repo: Optional['SnapshotRepository'] = None
    ):
        """
        Initialize service
        
        Args:
            expense_repo: Expense repository instance (optional)
            group_repo: Group repository instance (optional)
            balance_repo: Balance repository instance (optional)
            group_summary_repo: Group summary repository (Phase 6)
            user_expense_repo: User expense repository (Phase 6)
            history_repo: Expense history repository (Phase 12)
            snapshot_repo: Snapshot repository (Phase 20)
        """
        # pylint: disable=no-value-for-parameter
        self.expense_repo = expense_repo or ExpenseRepository()
        self.group_repo = group_repo or GroupRepository()
        self.balance_repo = balance_repo or BalanceRepository()
        self.balance_service = BalanceService(balance_repo, expense_repo)
        
        # Phase 6: Denormalized repositories
        self.group_summary_repo = group_summary_repo or GroupSummaryRepository()
        self.user_expense_repo = user_expense_repo or UserExpenseRepository()
        
        # Phase 12: History repository
        self.history_repo = history_repo or ExpenseHistoryRepository()
        
        # Phase 20: Snapshot repository (lazy init to avoid Firebase in tests)
        self._snapshot_repo = snapshot_repo
    
    @property
    def snapshot_repo(self) -> 'SnapshotRepository':
        """Lazy-load snapshot repository to avoid Firebase initialization in tests"""
        if self._snapshot_repo is None:
            self._snapshot_repo = SnapshotRepository()
        return self._snapshot_repo
    
    def create_expense(
        self,
        group_id: str,
        description: str,
        amount: Decimal,
        paid_by: str,
        split_type: str,
        splits: List[Dict],
        created_by: str,
        currency: str = 'USD',
        category: Optional[str] = None,
        notes: Optional[str] = None,
        expense_date: Optional[datetime] = None
    ) -> Dict:
        """
        Create a new expense with balance updates
        
        Args:
            group_id: Group ID
            description: Expense description
            amount: Total amount
            paid_by: User ID who paid
            split_type: Split type (equal/percentage/exact)
            splits: List of split details
            created_by: User ID who created
            currency: Currency code
            category: Optional category
            notes: Optional notes
            expense_date: Optional expense date
            
        Returns:
            Created expense document
        """
        try:
            # Validate group exists
            group_data = self.group_repo.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Validate all users are group members
            members = group_data.get('members', [])
            if paid_by not in members:
                raise ValidationError(f"Payer {paid_by} is not a group member")
            
            for split in splits:
                if split['user_id'] not in members:
                    raise ValidationError(
                        f"User {split['user_id']} is not a group member"
                    )
            
            # Create expense splits
            expense_splits = [
                ExpenseSplit(
                    user_id=split['user_id'],
                    amount=Decimal(str(split['amount']))
                )
                for split in splits
            ]
            
            # Create expense model
            expense = Expense(
                group_id=group_id,
                description=description,
                amount=amount,
                currency=currency,
                paid_by=paid_by,
                split_type=split_type,
                splits=expense_splits,
                created_by=created_by,
                category=category,
                notes=notes,
                expense_date=expense_date or datetime.utcnow()
            )
            
            # Create expense and update balances in transaction
            db = self.expense_repo.db
            transaction = db.transaction()
            
            @firestore.transactional  # pylint: disable=no-member
            def create_with_balance_update(trans):
                # Generate document ID
                doc_ref = self.expense_repo.get_collection().document()
                expense_id = doc_ref.id
                
                # Create expense
                self.expense_repo.create(expense_id, expense.to_dict())
                expense.expense_id = expense_id
                
                # Update balances
                self.balance_service.add_expense_to_balances(
                    trans,
                    group_id,
                    expense
                )
                
                return expense_id
            
            expense_id = create_with_balance_update(transaction)
            
            logger.info(
                "Created expense %s in group %s by %s",
                expense_id, group_id, created_by
            )
            
            # Phase 17: Trust what we wrote - build response from model instead of re-reading
            # This saves 1 Firestore read per expense creation
            created_expense_data = expense.to_dict()
            created_expense_data['id'] = expense_id
            created_expense_data['expense_id'] = expense_id
            
            # Phase 12: Create history entry for expense creation
            try:
                self.history_repo.create_history_entry(
                    expense_id=expense_id,
                    group_id=group_id,
                    action="created",
                    changed_by=created_by,
                    after_snapshot=created_expense_data,
                    before_snapshot=None
                )
            except Exception as history_exc:
                logger.warning("Failed to create history entry for expense %s: %s", 
                              expense_id, str(history_exc))
            
            # Phase 6: Update denormalized data (async-safe, non-transactional)
            try:
                self._update_denormalized_on_create(
                    expense_id=expense_id,
                    group_id=group_id,
                    group_name=group_data.get('name', 'Unknown Group'),
                    description=description,
                    amount=float(amount),
                    currency=currency,
                    paid_by=paid_by,
                    splits=splits,
                    expense_date=expense_date or datetime.utcnow(),
                    category=category or 'general'
                )
            except Exception as denorm_exc:
                # Log but don't fail - denormalized data can be rebuilt
                logger.warning("Failed to update denormalized data for expense %s: %s", 
                              expense_id, str(denorm_exc))
            
            # Phase 13 + 17.5: Write-through cache then invalidate list caches
            # Pass current_user_id to skip invalidating their cache (they have optimistic update)
            _write_through_expense_cache(expense_id, created_expense_data)
            _invalidate_expense_cache(expense_id, group_id, self.group_repo, current_user_id=created_by)
            
            # Phase 20: Update bootstrap snapshots asynchronously
            try:
                # Get updated balances for snapshot - balance_data is GroupBalance model
                balance_data = self.balance_repo.get_group_balances(group_id)
                new_balances = balance_data.balances if balance_data else {}
                
                # Build expense summary
                expense_summary = {
                    'id': expense_id,
                    'description': description,
                    'amount': float(amount),
                    'currency': currency,
                    'category': category or 'Other',
                    'date': (expense_date or datetime.utcnow()).isoformat() if isinstance(expense_date or datetime.utcnow(), datetime) else str(expense_date),
                    'paidBy': paid_by,
                    'createdAt': datetime.utcnow().isoformat()
                }
                
                # Add to snapshot recent expenses
                self.snapshot_repo.add_recent_expense(group_id, expense_summary)
                
                # Update balances in snapshots
                if new_balances:
                    self.snapshot_repo.update_balances(group_id, new_balances)
                    
                logger.debug("Updated snapshots for expense %s creation", expense_id)
            except Exception as snapshot_exc:
                # Non-critical - don't fail expense creation
                logger.warning("Failed to update snapshots for expense %s: %s", expense_id, snapshot_exc)
            
            # Phase 17: Return the data we wrote instead of re-reading from Firestore
            # This saves 1 Firestore read per expense creation
            return created_expense_data
            
        except Exception as exc:
            logger.error("Error creating expense: %s", str(exc))
            raise
    
    def get_expense(self, expense_id: str) -> Optional[Dict]:
        """
        Get expense by ID with Redis caching (TTL=60s)
        
        Args:
            expense_id: Expense ID
            
        Returns:
            Expense document or None
        """
        # Try cache first
        if CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_EXPENSE.format(eid=expense_id)
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
        
        # Get from Firestore
        expense_data = self.expense_repo.get_by_id(expense_id)
        
        # Cache result if found
        if expense_data and CACHE_ENABLED:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, expense_data, ttl=redis_config.TTL_GROUP_EXPENSES)
        
        return expense_data
    
    def get_group_expenses(
        self,
        group_id: str,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> Dict:
        """
        Get expenses for a group with pagination and Redis caching
        
        Args:
            group_id: Group ID
            limit: Maximum expenses to return
            offset: Number of expenses to skip
            include_deleted: Whether to include soft-deleted expenses
            
        Returns:
            Dict with expenses and pagination info
        """
        # Only cache default queries (no deleted, standard pagination)
        use_cache = (
            CACHE_ENABLED and
            not include_deleted and
            limit == 50
        )
        
        if use_cache:
            cache = get_cache_manager()
            if cache and cache.is_available():
                page = offset // limit
                cache_key = redis_config.KEY_GROUP_EXPENSES.format(gid=group_id, page=page)
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
        
        # Get from Firestore
        result = self.expense_repo.get_group_expenses(
            group_id,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )
        
        # Cache standard queries
        if use_cache and result:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, result, ttl=redis_config.TTL_GROUP_EXPENSES)
        
        return result
    
    def update_expense(
        self,
        expense_id: str,
        updated_by: str,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
        paid_by: Optional[str] = None,
        splits: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        expense_date: Optional[str] = None
    ) -> Dict:
        """
        Update an existing expense
        
        Args:
            expense_id: Expense ID
            updated_by: User ID who is updating
            description: New description
            amount: New amount
            paid_by: New payer user ID
            splits: New splits
            category: New category
            notes: New notes
            expense_date: New expense date (YYYY-MM-DD format)
            
        Returns:
            Updated expense document
        """
        try:
            # Get old expense
            old_expense_data = self.expense_repo.get_by_id(expense_id)
            if not old_expense_data:
                raise ResourceNotFoundError(f"Expense {expense_id} not found")
            
            # Create old expense model using helper
            old_expense = expense_from_firestore(old_expense_data)
            
            # NOTE: Permission check removed - route handles role-based permissions
            # Group owners can edit any expense, members can edit their own
            
            # Build update data
            update_data = {
                'updated_at': datetime.utcnow()
            }
            
            if description is not None:
                update_data['description'] = description
            if amount is not None:
                update_data['amount'] = float(amount)
            if paid_by is not None:
                update_data['paid_by'] = paid_by
            if category is not None:
                update_data['category'] = category
            if notes is not None:
                update_data['notes'] = notes
            if expense_date is not None:
                update_data['expense_date'] = expense_date
            if splits is not None:
                expense_splits = [
                    ExpenseSplit(
                        user_id=split['user_id'],
                        amount=Decimal(str(split['amount']))
                    ).to_dict()
                    for split in splits
                ]
                update_data['splits'] = expense_splits
            
            # Phase 12: Mark expense as edited
            update_data['is_edited'] = True
            
            # Create new expense model for balance calculation
            # Merge old data with updates, then filter to allowed fields
            merged_data = {**old_expense_data, **update_data}
            new_expense_data = {k: v for k, v in merged_data.items() if k in ALLOWED_EXPENSE_FIELDS}
            new_expense = expense_from_firestore(new_expense_data)
            
            # Update expense and balances in transaction
            db = self.expense_repo.db
            transaction = db.transaction()
            
            @firestore.transactional  # pylint: disable=no-member
            def update_with_balance_change(trans):
                # Update expense
                self.expense_repo.update(expense_id, update_data)
                
                # Update balances
                self.balance_service.edit_expense_in_balances(
                    trans,
                    old_expense.group_id,
                    old_expense,
                    new_expense
                )
            
            update_with_balance_change(transaction)
            
            # Phase 17: Build the updated expense from known data instead of re-reading
            # This saves 2 Firestore reads per expense update
            updated_expense_data = {**merged_data, 'id': expense_id}
            
            # Phase 12: Create history entry for expense update
            try:
                self.history_repo.create_history_entry(
                    expense_id=expense_id,
                    group_id=old_expense.group_id,
                    action="updated",
                    changed_by=updated_by,
                    before_snapshot=old_expense_data,
                    after_snapshot=updated_expense_data
                )
            except Exception as history_exc:
                logger.warning("Failed to create history entry for expense update %s: %s", 
                              expense_id, str(history_exc))
            
            # Phase 6: Update denormalized data
            try:
                old_splits_data = [s.to_dict() if hasattr(s, 'to_dict') else s 
                                   for s in old_expense.splits]
                new_splits_data = new_expense_data.get('splits', old_splits_data)
                if new_splits_data and hasattr(new_splits_data[0], 'to_dict'):
                    new_splits_data = [s.to_dict() for s in new_splits_data]
                
                self._update_denormalized_on_update(
                    expense_id=expense_id,
                    group_id=old_expense.group_id,
                    old_splits=old_splits_data,
                    new_splits=new_splits_data,
                    updates=update_data
                )
            except Exception as denorm_exc:
                logger.warning("Failed to update denormalized data on update %s: %s", 
                              expense_id, str(denorm_exc))
            
            # Phase 13 + 17.5: Write-through cache then invalidate list caches
            # Pass current_user_id to skip invalidating their cache (they have optimistic update)
            _write_through_expense_cache(expense_id, updated_expense_data)
            _invalidate_expense_cache(expense_id, old_expense.group_id, self.group_repo, current_user_id=updated_by)
            
            # Phase 20: Update bootstrap snapshots
            try:
                old_amount = float(old_expense.amount) if old_expense.amount else 0
                new_amount = float(amount) if amount else old_amount
                
                # Get updated balances - balance_data is GroupBalance model
                balance_data = self.balance_repo.get_group_balances(old_expense.group_id)
                new_balances = balance_data.balances if balance_data else {}
                
                # Build updated expense summary
                expense_summary = {
                    'id': expense_id,
                    'description': description or old_expense.description,
                    'amount': new_amount,
                    'currency': updated_expense_data.get('currency', 'USD'),
                    'category': category or old_expense.category or 'Other',
                    'date': expense_date or old_expense_data.get('expense_date'),
                    'paidBy': paid_by or old_expense.paid_by,
                    'createdAt': old_expense_data.get('created_at')
                }
                
                self.snapshot_repo.update_expense_in_snapshots(
                    group_id=old_expense.group_id,
                    expense_id=expense_id,
                    updated_expense=expense_summary,
                    old_amount=old_amount
                )
                
                if new_balances:
                    self.snapshot_repo.update_balances(old_expense.group_id, new_balances)
                    
                logger.debug("Updated snapshots for expense %s update", expense_id)
            except Exception as snapshot_exc:
                logger.warning("Failed to update snapshots for expense update %s: %s", expense_id, snapshot_exc)
            
            logger.info(
                "Updated expense %s by %s",
                expense_id, updated_by
            )
            
            # Phase 17: Return the merged data instead of re-reading from Firestore
            return updated_expense_data
            
        except Exception as exc:
            logger.error("Error updating expense: %s", str(exc))
            raise
    
    def delete_expense(self, expense_id: str, deleted_by: str) -> None:
        """
        Delete an expense (soft delete with balance reversal)
        
        Args:
            expense_id: Expense ID
            deleted_by: User ID who is deleting
        """
        try:
            # Get expense
            expense_data = self.expense_repo.get_by_id(expense_id)
            if not expense_data:
                raise ResourceNotFoundError(f"Expense {expense_id} not found")
            
            # Create expense model using helper
            expense = expense_from_firestore(expense_data)
            
            # NOTE: Permission check removed - route handles role-based permissions
            # Group owners can delete any expense, members can delete their own
            
            # Delete expense and reverse balances in transaction
            db = self.expense_repo.db
            transaction = db.transaction()
            
            @firestore.transactional  # pylint: disable=no-member
            def delete_with_balance_reversal(trans):
                # Soft delete expense
                self.expense_repo.soft_delete_expense(expense_id)
                
                # Reverse balances
                self.balance_service.remove_expense_from_balances(
                    trans,
                    expense.group_id,
                    expense
                )
            
            delete_with_balance_reversal(transaction)
            
            # Phase 17: Build deleted snapshot from known data instead of re-reading
            # This saves 1 Firestore read per expense deletion
            deleted_expense_data = {
                **expense_data,
                'id': expense_id,
                'is_deleted': True,
                'deleted_at': datetime.utcnow().isoformat()
            }
            
            # Phase 12: Create history entry for expense deletion
            try:
                self.history_repo.create_history_entry(
                    expense_id=expense_id,
                    group_id=expense.group_id,
                    action="deleted",
                    changed_by=deleted_by,
                    before_snapshot=expense_data,
                    after_snapshot=deleted_expense_data
                )
            except Exception as history_exc:
                logger.warning("Failed to create history entry for expense deletion %s: %s", 
                              expense_id, str(history_exc))
            
            # Phase 6: Update denormalized data
            try:
                self._update_denormalized_on_delete(
                    expense_id=expense_id,
                    group_id=expense.group_id,
                    participant_ids=[s.user_id for s in expense.splits]
                )
            except Exception as denorm_exc:
                logger.warning("Failed to update denormalized data on delete %s: %s", 
                              expense_id, str(denorm_exc))
            
            # Phase 13 + 17.5: Invalidate related caches (pass group_repo for mega-bootstrap invalidation)
            # Pass current_user_id to skip invalidating their cache (they have optimistic update)
            _invalidate_expense_cache(expense_id, expense.group_id, self.group_repo, current_user_id=deleted_by)
            
            # Phase 20: Update bootstrap snapshots
            try:
                expense_amount = float(expense.amount) if expense.amount else 0
                
                # Get updated balances - balance_data is GroupBalance model
                balance_data = self.balance_repo.get_group_balances(expense.group_id)
                new_balances = balance_data.balances if balance_data else {}
                
                # Remove from snapshots
                self.snapshot_repo.remove_expense_from_snapshots(
                    group_id=expense.group_id,
                    expense_id=expense_id,
                    expense_amount=expense_amount
                )
                
                if new_balances:
                    self.snapshot_repo.update_balances(expense.group_id, new_balances)
                    
                logger.debug("Updated snapshots for expense %s deletion", expense_id)
            except Exception as snapshot_exc:
                logger.warning("Failed to update snapshots for expense deletion %s: %s", expense_id, snapshot_exc)
            
            logger.info(
                "Deleted expense %s by %s",
                expense_id, deleted_by
            )
            
        except Exception as exc:
            logger.error("Error deleting expense: %s", str(exc))
            raise
    
    # =========================================================================
    # Phase 6: Denormalized Data Maintenance
    # =========================================================================
    
    def _update_denormalized_on_create(
        self,
        expense_id: str,
        group_id: str,
        group_name: str,
        description: str,
        amount: float,
        currency: str,
        paid_by: str,
        splits: List[Dict],
        expense_date: datetime,
        category: str
    ) -> None:
        """
        Update denormalized collections after expense creation (Phase 17: Batched)
        
        Updates:
        - USER_EXPENSES: Add expense to all participant indexes (batched)
        - GROUP_SUMMARIES: Update balance for each participant (batched)
        """
        logger.debug("Updating denormalized data for new expense %s", expense_id)
        
        # Build splits dict for user expense repo
        splits_dict = {s['user_id']: float(s['amount']) for s in splits}
        
        # 1. Add to USER_EXPENSES index for all participants (BATCHED)
        self.user_expense_repo.add_expense_for_participants(
            expense_id=expense_id,
            group_id=group_id,
            group_name=group_name,
            description=description,
            amount=amount,
            currency=currency,
            payer_id=paid_by,
            splits=splits_dict,
            expense_date=expense_date,
            category=category
        )
        
        # 2. Update GROUP_SUMMARIES for all participants (BATCHED - Phase 17)
        # Calculate balance deltas: payer gets +amount, each participant gets -share
        balance_deltas = {}
        for split in splits:
            user_id = split['user_id']
            share = float(split['amount'])
            
            if user_id == paid_by:
                # Payer paid the full amount, owes their share
                # Net effect: +(amount - share)
                balance_deltas[user_id] = amount - share
            else:
                # Non-payer owes their share to the payer
                # Net effect: -share (they owe money)
                balance_deltas[user_id] = -share
        
        try:
            self.group_summary_repo.batch_update_group_balances(
                group_id=group_id,
                balance_deltas=balance_deltas,
                increment_expense_count=True
            )
        except Exception as exc:
            logger.warning("Failed to batch update group summaries: %s", str(exc))
    
    def _update_denormalized_on_delete(
        self,
        expense_id: str,
        group_id: str,
        participant_ids: List[str]
    ) -> None:
        """
        Update denormalized collections after expense deletion
        
        Updates:
        - USER_EXPENSES: Remove expense from all participant indexes
        - GROUP_SUMMARIES: Recalculate balances (handled by balance_service)
        """
        logger.debug("Updating denormalized data for deleted expense %s", expense_id)
        
        # Remove from USER_EXPENSES index
        self.user_expense_repo.remove_expense_for_participants(
            expense_id=expense_id,
            participant_ids=participant_ids
        )
        
        # Note: GROUP_SUMMARIES balance updates are handled by balance_service
        # through the main transaction. We could trigger a full recalc here
        # but it's expensive. Better to rely on balance_service for consistency.
    
    def _update_denormalized_on_update(
        self,
        expense_id: str,
        group_id: str,
        old_splits: List[Dict],
        new_splits: List[Dict],
        updates: Dict
    ) -> None:
        """
        Update denormalized collections after expense update
        
        Updates:
        - USER_EXPENSES: Update expense entry for all participants
        """
        logger.debug("Updating denormalized data for updated expense %s", expense_id)
        
        old_participant_ids = {s.get('user_id') for s in old_splits}
        new_participant_ids = {s.get('user_id') for s in new_splits}
        
        # Handle participant changes
        removed = old_participant_ids - new_participant_ids
        added = new_participant_ids - old_participant_ids
        
        # Remove from removed participants
        if removed:
            self.user_expense_repo.remove_expense_for_participants(
                expense_id=expense_id,
                participant_ids=list(removed)
            )
        
        # Update existing participants
        for user_id in (old_participant_ids & new_participant_ids):
            try:
                # Find new share for this user
                user_share = next(
                    (float(s.get('amount', 0)) for s in new_splits if s.get('user_id') == user_id),
                    0
                )
                update_data = {
                    'user_share': user_share,
                    **{k: v for k, v in updates.items() 
                       if k in ('description', 'amount', 'expense_date', 'category')}
                }
                self.user_expense_repo.update_expense_in_index(
                    user_id=user_id,
                    expense_id=expense_id,
                    updates=update_data
                )
            except Exception as exc:
                logger.warning("Failed to update expense in user %s index: %s", 
                              user_id, str(exc))

    # =========================================================================
    # Phase 12: Expense History Methods
    # =========================================================================
    
    def get_expense_history(
        self,
        expense_id: str,
        limit: int = 50,
        include_snapshots: bool = False
    ) -> List[Dict]:
        """
        Get edit history for an expense
        
        Args:
            expense_id: Expense ID
            limit: Maximum entries to return
            include_snapshots: Whether to include full before/after data
            
        Returns:
            List of history entries, newest first
        """
        return self.history_repo.get_expense_history(
            expense_id=expense_id,
            limit=limit,
            include_snapshots=include_snapshots
        )
    
    def get_group_audit_log(
        self,
        group_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Get all expense changes for a group (audit log)
        
        Args:
            group_id: Group ID
            limit: Maximum entries
            offset: Pagination offset
            
        Returns:
            Dict with entries and pagination info
        """
        return self.history_repo.get_group_history(
            group_id=group_id,
            limit=limit,
            offset=offset
        )
    
    def is_expense_edited(self, expense_id: str) -> bool:
        """
        Check if an expense has been edited
        
        Args:
            expense_id: Expense ID
            
        Returns:
            True if expense has update history entries
        """
        return self.history_repo.get_edit_count(expense_id) > 0
    
    def get_expense_edit_count(self, expense_id: str) -> int:
        """
        Get number of times an expense has been edited
        
        Args:
            expense_id: Expense ID
            
        Returns:
            Number of edit (update) entries
        """
        return self.history_repo.get_edit_count(expense_id)
    
    def get_expenses_with_edit_flags(
        self,
        expense_ids: List[str]
    ) -> Dict[str, bool]:
        """
        Get edit status for multiple expenses
        
        Args:
            expense_ids: List of expense IDs
            
        Returns:
            Dict mapping expense_id to bool (True if edited)
        """
        recent_edits = self.history_repo.get_recent_edits(expense_ids)
        return {
            expense_id: expense_id in recent_edits
            for expense_id in expense_ids
        }

    # =========================================================================
    # Phase 17: Enhanced Mutation Methods with Balance Deltas
    # These return balance deltas and history entries for instant frontend updates
    # =========================================================================

    def create_expense_with_deltas(
        self,
        group_id: str,
        description: str,
        amount: Decimal,
        paid_by: str,
        split_type: str,
        splits: List[Dict],
        created_by: str,
        currency: str = 'USD',
        category: Optional[str] = None,
        notes: Optional[str] = None,
        expense_date: Optional[datetime] = None
    ) -> Dict:
        """
        Create expense and return balance deltas for instant frontend update.
        
        Phase 17: Eliminates need for frontend to refetch balances after mutation.
        Returns expense data + balance_deltas + history_entry in single response.
        
        Args:
            group_id: Group ID
            description: Expense description
            amount: Total amount
            paid_by: User ID who paid
            split_type: Split type (equal/percentage/exact)
            splits: List of split details
            created_by: User ID who created
            currency: Currency code
            category: Optional category
            notes: Optional notes
            expense_date: Optional expense date
            
        Returns:
            Dict with: expense, balance_deltas, history_entry
        """
        # Create expense using existing method
        expense_data = self.create_expense(
            group_id=group_id,
            description=description,
            amount=amount,
            paid_by=paid_by,
            split_type=split_type,
            splits=splits,
            created_by=created_by,
            currency=currency,
            category=category,
            notes=notes,
            expense_date=expense_date
        )
        
        # Calculate balance deltas from the created expense
        expense_splits = [
            ExpenseSplit(
                user_id=split['user_id'],
                amount=Decimal(str(split['amount']))
            )
            for split in splits
        ]
        
        temp_expense = Expense(
            group_id=group_id,
            description=description,
            amount=amount,
            currency=currency,
            paid_by=paid_by,
            split_type=split_type,
            splits=expense_splits,
            created_by=created_by
        )
        
        balance_deltas = self.balance_service.calculate_expense_deltas(temp_expense)
        
        # Convert Decimal to float for JSON serialization
        balance_deltas_serializable = {
            uid: float(delta) for uid, delta in balance_deltas.items()
        }
        
        # Get the history entry we just created
        expense_id = expense_data.get('id') or expense_data.get('expense_id')
        history_entry = None
        try:
            history = self.history_repo.get_expense_history(
                expense_id=expense_id,
                limit=1,
                include_snapshots=False
            )
            if history:
                history_entry = history[0]
        except Exception as hist_exc:  # pylint: disable=broad-except
            logger.warning("Failed to fetch history entry: %s", str(hist_exc))
        
        return {
            'expense': expense_data,
            'balance_deltas': balance_deltas_serializable,
            'history_entry': history_entry
        }

    def update_expense_with_deltas(
        self,
        expense_id: str,
        updated_by: str,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
        paid_by: Optional[str] = None,
        splits: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        expense_date: Optional[str] = None
    ) -> Dict:
        """
        Update expense and return balance deltas for instant frontend update.
        
        Phase 17: Returns both the old->new balance delta and the history entry.
        Frontend can apply deltas directly without refetching balances.
        
        Args:
            expense_id: Expense ID
            updated_by: User ID who is updating
            description: New description
            amount: New amount
            paid_by: New payer user ID
            splits: New splits
            category: New category
            notes: New notes
            expense_date: New expense date (YYYY-MM-DD format)
            
        Returns:
            Dict with: expense, balance_deltas, history_entry
        """
        # Get old expense before update for delta calculation
        old_expense_data = self.expense_repo.get_by_id(expense_id)
        if not old_expense_data:
            raise ResourceNotFoundError(f"Expense {expense_id} not found")
        
        old_expense = expense_from_firestore(old_expense_data)
        
        # Update expense using existing method
        updated_expense_data = self.update_expense(
            expense_id=expense_id,
            updated_by=updated_by,
            description=description,
            amount=amount,
            paid_by=paid_by,
            splits=splits,
            category=category,
            notes=notes,
            expense_date=expense_date
        )
        
        # Build new expense model for delta calculation
        new_expense = expense_from_firestore(updated_expense_data)
        
        # Calculate combined delta (reverse old + apply new)
        old_deltas = self.balance_service.calculate_expense_deltas(old_expense)
        new_deltas = self.balance_service.calculate_expense_deltas(new_expense)
        
        combined_deltas = {}
        all_users = set(old_deltas.keys()) | set(new_deltas.keys())
        for uid in all_users:
            old_delta = old_deltas.get(uid, Decimal("0.00"))
            new_delta = new_deltas.get(uid, Decimal("0.00"))
            combined_deltas[uid] = float(new_delta - old_delta)
        
        # Get the history entry we just created
        history_entry = None
        try:
            history = self.history_repo.get_expense_history(
                expense_id=expense_id,
                limit=1,
                include_snapshots=False
            )
            if history:
                history_entry = history[0]
        except Exception as hist_exc:  # pylint: disable=broad-except
            logger.warning("Failed to fetch history entry: %s", str(hist_exc))
        
        return {
            'expense': updated_expense_data,
            'balance_deltas': combined_deltas,
            'history_entry': history_entry
        }

    def delete_expense_with_deltas(
        self,
        expense_id: str,
        deleted_by: str
    ) -> Dict:
        """
        Delete expense and return balance deltas for instant frontend update.
        
        Phase 17: Returns reverse deltas so frontend can update balances
        without refetching. Also returns the deletion history entry.
        
        Args:
            expense_id: Expense ID
            deleted_by: User ID who is deleting
            
        Returns:
            Dict with: expense_id, group_id, balance_deltas, history_entry
        """
        # Get expense before deletion for delta calculation
        expense_data = self.expense_repo.get_by_id(expense_id)
        if not expense_data:
            raise ResourceNotFoundError(f"Expense {expense_id} not found")
        
        expense = expense_from_firestore(expense_data)
        group_id = expense.group_id
        
        # Calculate reverse deltas (what to subtract from balances)
        deltas = self.balance_service.calculate_expense_deltas(expense)
        reverse_deltas = {
            uid: float(-delta) for uid, delta in deltas.items()
        }
        
        # Delete expense using existing method
        self.delete_expense(expense_id=expense_id, deleted_by=deleted_by)
        
        # Get the history entry we just created
        history_entry = None
        try:
            history = self.history_repo.get_expense_history(
                expense_id=expense_id,
                limit=1,
                include_snapshots=False
            )
            if history:
                history_entry = history[0]
        except Exception as hist_exc:  # pylint: disable=broad-except
            logger.warning("Failed to fetch history entry: %s", str(hist_exc))
        
        return {
            'expense_id': expense_id,
            'group_id': group_id,
            'balance_deltas': reverse_deltas,
            'history_entry': history_entry,
            'deleted_expense': {
                **expense_data,
                'id': expense_id,
                'is_deleted': True
            }
        }
