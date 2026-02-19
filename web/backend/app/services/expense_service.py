"""
SQL-based Expense Service
Handles expense operations using local SQL database
Like Splitwise - tracks who paid and who owes
"""

import json
import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.infrastructure.db.connection import get_db_session
from app.domain.expenses.models import (Expense, ExpenseHistory, ExpenseSplit, Group,
                               GroupBalance, GroupMember, User)

logger = logging.getLogger(__name__)


class ExpenseServiceSQL:
    """Service for expense operations using SQL database"""
    
    @staticmethod
    def create_expense(
        user_id: int,
        group_id: Optional[int],
        description: str,
        amount: float,
        paid_by: int,
        split_type: str = 'equal',
        splits: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        expense_date: Optional[str] = None,
        notes: Optional[str] = None,
        receipt_url: Optional[str] = None,
        currency: str = 'USD'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new expense (personal or group)
        
        Args:
            user_id: ID of user creating expense
            group_id: Group ID (None for personal expenses)
            description: Expense description
            amount: Total amount
            paid_by: User ID who paid
            split_type: 'equal', 'exact', 'percentage', 'shares'
            splits: Split configuration per user
            category: Optional category
            expense_date: Optional date string
            notes: Optional notes
            receipt_url: Optional receipt image URL
            currency: Currency code (default USD)
            
        Returns:
            Tuple of (success, expense_data/error)
        """
        try:
            with get_db_session() as session:
                # For personal expenses (no group)
                if group_id is None:
                    return ExpenseServiceSQL._create_personal_expense(
                        session, user_id, description, amount, paid_by,
                        category, expense_date, notes, receipt_url, currency
                    )
                
                # For group expenses
                # Verify group membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    logger.warning(f"User {user_id} is not a member of group {group_id}")
                    return False, {'error': 'Not a member of this group'}
                
                # Verify payer is a member
                payer_member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == paid_by,
                    GroupMember.is_active == True
                ).first()
                
                if not payer_member:
                    # List all members for debugging
                    all_members = session.query(GroupMember).filter(
                        GroupMember.group_id == group_id,
                        GroupMember.is_active == True
                    ).all()
                    member_ids = [m.user_id for m in all_members]
                    logger.warning(f"Payer {paid_by} (type: {type(paid_by)}) is not a member of group {group_id}. Active members: {member_ids}")
                    return False, {'error': f'Payer is not a member of this group. Active members: {member_ids}'}
                
                # Get group currency
                group = session.query(Group).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Parse expense date
                exp_date = None
                if expense_date:
                    try:
                        exp_date = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
                    except:
                        exp_date = datetime.now(timezone.utc)
                else:
                    exp_date = datetime.now(timezone.utc)
                
                # Create expense
                expense = Expense(
                    group_id=group_id,
                    description=description.strip(),
                    amount=amount,
                    currency=group.currency,
                    paid_by=paid_by,
                    created_by=user_id,
                    split_type=split_type,
                    category=category,
                    expense_date=exp_date,
                    notes=notes.strip() if notes else None,
                    receipt_url=receipt_url
                )
                session.add(expense)
                session.flush()  # Get expense ID
                
                # Calculate and create splits
                expense_splits = ExpenseServiceSQL._calculate_splits(
                    session, group_id, expense.id, amount, paid_by, split_type, splits
                )
                
                if not expense_splits:
                    return False, {'error': 'Failed to calculate splits'}
                
                for split in expense_splits:
                    session.add(split)
                
                # Determine actual split status (EQUAL or CUSTOM)
                # EQUAL = all group members included, CUSTOM = subset of members
                all_group_members = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.is_active == True
                ).count()
                
                split_count = len(expense_splits)
                # If split includes all members, it's equal, otherwise exact
                expense.split_type = 'equal' if split_count == all_group_members else 'exact'
                
                # Update group balances
                ExpenseServiceSQL._update_balances(session, group_id, expense_splits, paid_by, amount)
                
                # Record history
                history = ExpenseHistory(
                    expense_id=expense.id,
                    group_id=group_id,
                    action='created',
                    changed_by=user_id,
                    changes_json='{}'
                )
                session.add(history)
                
                # Update group timestamp
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(expense)
                
                logger.info(f"Expense created: {expense.id} in group {group_id}")
                
                # Get updated balances for instant UI update
                from app.services.settlement_service import \
                    settlement_service_sql
                balances_success, balances_result = settlement_service_sql.get_group_balances(group_id, user_id)
                
                # Return full expense data with balances
                result = {'expense': ExpenseServiceSQL._get_expense_dict(session, expense)}
                if balances_success:
                    result['balances'] = balances_result.get('balances', [])
                
                return True, result
                
        except Exception as e:
            logger.error(f"Create expense error: {str(e)}")
            return False, {'error': 'Failed to create expense'}
    
    @staticmethod
    def _create_personal_expense(
        session,
        user_id: int,
        description: str,
        amount: float,
        paid_by: int,
        category: Optional[str] = None,
        expense_date: Optional[str] = None,
        notes: Optional[str] = None,
        receipt_url: Optional[str] = None,
        currency: str = 'USD'
    ) -> Tuple[bool, Dict[str, Any]]:
        """Create a personal expense (not associated with any group)"""
        try:
            # Parse expense date
            exp_date = None
            if expense_date:
                try:
                    exp_date = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
                except:
                    exp_date = datetime.now(timezone.utc)
            else:
                exp_date = datetime.now(timezone.utc)
            
            # Create expense without group
            expense = Expense(
                group_id=None,  # Personal expense
                description=description.strip(),
                amount=amount,
                currency=currency,
                paid_by=paid_by,
                created_by=user_id,
                split_type='none',  # No split for personal
                category=category,
                expense_date=exp_date,
                notes=notes.strip() if notes else None,
                receipt_url=receipt_url
            )
            session.add(expense)
            session.flush()
            
            # Create single split for personal expense
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=paid_by,
                amount=amount
            )
            session.add(split)
            
            # Record history - for personal expenses, group_id is None
            history = ExpenseHistory(
                expense_id=expense.id,
                group_id=None,  # Personal expenses have no group
                action='created',
                changed_by=user_id,
                changes_json='{}'
            )
            session.add(history)
            
            session.commit()
            session.refresh(expense)
            
            logger.info(f"Personal expense created: {expense.id}")
            
            return True, {'expense': ExpenseServiceSQL._get_expense_dict(session, expense)}
            
        except Exception as e:
            logger.error(f"Create personal expense error: {str(e)}")
            return False, {'error': 'Failed to create personal expense'}
    
    @staticmethod
    def _calculate_splits(
        session,
        group_id: int,
        expense_id: int,
        amount: float,
        paid_by: int,
        split_type: str,
        splits: Optional[List[Dict]]
    ) -> List[ExpenseSplit]:
        """Calculate expense splits based on split type"""
        
        result_splits = []
        
        # Get active members
        members = session.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).all()
        
        member_ids = [m.user_id for m in members]
        
        # Normalize split_type to lowercase for comparison
        split_type_lower = split_type.lower()
        
        # Debug logging
        logger.info(f"Calculate splits: group_id={group_id}, split_type={split_type} ({split_type_lower}), members={member_ids}, splits={splits}")
        
        if split_type_lower == 'equal':
            # Split equally among all members
            if splits:
                # Custom list of users for equal split
                split_users = [s['user_id'] for s in splits if s.get('user_id') in member_ids]
                logger.info(f"Equal split with custom users: provided={[s.get('user_id') for s in splits]}, filtered={split_users}")
            else:
                split_users = member_ids
            
            if not split_users:
                return []
            
            per_person = round(amount / len(split_users), 2)
            
            # Handle rounding remainder
            remainder = round(amount - (per_person * len(split_users)), 2)
            
            for i, uid in enumerate(split_users):
                split_amount = per_person
                if i == 0:  # First person gets the remainder
                    split_amount = round(split_amount + remainder, 2)
                
                result_splits.append(ExpenseSplit(
                    expense_id=expense_id,
                    user_id=uid,
                    amount=split_amount,
                    percentage=round(100 / len(split_users), 2)
                ))
        
        elif split_type_lower == 'exact':
            # Exact amounts specified
            if not splits:
                return []
            
            total_split = sum(s.get('amount', 0) for s in splits)
            if abs(total_split - amount) > 0.01:
                logger.warning(f"Split total {total_split} doesn't match amount {amount}")
            
            for s in splits:
                if s.get('user_id') not in member_ids:
                    continue
                result_splits.append(ExpenseSplit(
                    expense_id=expense_id,
                    user_id=s['user_id'],
                    amount=s['amount'],
                    percentage=round((s['amount'] / amount) * 100, 2) if amount > 0 else 0
                ))
        
        elif split_type_lower == 'percentage':
            # Percentage-based split
            if not splits:
                return []
            
            total_pct = sum(s.get('percentage', 0) for s in splits)
            if abs(total_pct - 100) > 0.01:
                logger.warning(f"Percentage total {total_pct} doesn't equal 100")
            
            for s in splits:
                if s.get('user_id') not in member_ids:
                    continue
                pct = s.get('percentage', 0)
                split_amount = round((pct / 100) * amount, 2)
                result_splits.append(ExpenseSplit(
                    expense_id=expense_id,
                    user_id=s['user_id'],
                    amount=split_amount,
                    percentage=pct
                ))
        
        elif split_type_lower == 'shares':
            # Share-based split (like 2 shares for me, 1 share for you)
            if not splits:
                return []
            
            total_shares = sum(s.get('shares', 0) for s in splits)
            if total_shares <= 0:
                return []
            
            for s in splits:
                if s.get('user_id') not in member_ids:
                    continue
                shares = s.get('shares', 0)
                split_amount = round((shares / total_shares) * amount, 2)
                result_splits.append(ExpenseSplit(
                    expense_id=expense_id,
                    user_id=s['user_id'],
                    amount=split_amount,
                    percentage=round((shares / total_shares) * 100, 2),
                    shares=shares
                ))
        
        return result_splits
    
    @staticmethod
    def _update_balances(
        session,
        group_id: int,
        splits: List[ExpenseSplit],
        paid_by: int,
        total_amount: float
    ):
        """Update group balances after expense creation"""
        
        # Payer gains the total amount they paid
        # Then we subtract what they owe from their split
        
        for split in splits:
            balance = session.query(GroupBalance).filter(
                GroupBalance.group_id == group_id,
                GroupBalance.user_id == split.user_id
            ).first()
            
            if not balance:
                balance = GroupBalance(
                    group_id=group_id,
                    user_id=split.user_id,
                    balance=Decimal('0.0')
                )
                session.add(balance)
            
            if split.user_id == paid_by:
                # Payer: add what they paid, subtract their share
                balance.balance += (Decimal(str(total_amount)) - Decimal(str(split.amount)))
            else:
                # Others: subtract their share (they owe this)
                balance.balance -= Decimal(str(split.amount))
            
            balance.updated_at = datetime.now(timezone.utc)
    
    @staticmethod
    def _get_expense_dict(session, expense: Expense) -> Dict[str, Any]:
        """Get expense as dictionary with splits"""
        data = expense.to_dict()
        
        # Add payer info
        payer = session.query(User).get(expense.paid_by)
        if payer:
            data['paid_by_user'] = {
                'id': payer.id,
                'display_name': payer.display_name,
                'email': payer.email
            }
        
        # Add splits with user info
        splits = session.query(ExpenseSplit, User).join(
            User, ExpenseSplit.user_id == User.id
        ).filter(ExpenseSplit.expense_id == expense.id).all()
        
        data['splits'] = [
            {
                'user_id': split.user_id,
                'amount': split.amount,
                'percentage': split.percentage,
                'shares': split.shares,
                'user': {
                    'id': user.id,
                    'display_name': user.display_name,
                    'email': user.email
                }
            }
            for split, user in splits
        ]
        
        return data
    
    @staticmethod
    def get_expense(expense_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get expense details
        
        Args:
            expense_id: Expense ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, expense_data/error)
        """
        try:
            with get_db_session() as session:
                expense = session.query(Expense).get(expense_id)
                
                if not expense or expense.is_deleted:
                    return False, {'error': 'Expense not found'}
                
                # Allow access to personal expenses
                if expense.group_id is None:
                    # Personal expense - only creator can access
                    if expense.created_by != user_id:
                        return False, {'error': 'You can only view your own personal expenses'}
                else:
                    # Group expense - verify membership
                    member = session.query(GroupMember).filter(
                        GroupMember.group_id == expense.group_id,
                        GroupMember.user_id == user_id,
                        GroupMember.is_active == True
                    ).first()
                    
                    if not member:
                        return False, {'error': 'Not a member of this group'}
                
                return True, {'expense': ExpenseServiceSQL._get_expense_dict(session, expense)}
                
        except Exception as e:
            logger.error(f"Get expense error: {str(e)}")
            return False, {'error': 'Failed to get expense'}
    
    @staticmethod
    def get_group_expenses(
        group_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get expenses for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            limit: Max results
            offset: Pagination offset
            include_deleted: If True, include deleted expenses in results
            
        Returns:
            Tuple of (success, expenses_list/error)
        """
        try:
            with get_db_session() as session:
                # Verify membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Build query
                query = session.query(Expense).filter(
                    Expense.group_id == group_id
                )
                
                if not include_deleted:
                    query = query.filter(Expense.is_deleted == False)
                
                # Get expenses
                expenses = query.order_by(Expense.expense_date.desc()).offset(offset).limit(limit).all()
                
                # Get total count with same filter
                count_query = session.query(Expense).filter(
                    Expense.group_id == group_id
                )
                if not include_deleted:
                    count_query = count_query.filter(Expense.is_deleted == False)
                total = count_query.count()
                
                expense_list = [
                    ExpenseServiceSQL._get_expense_dict(session, e)
                    for e in expenses
                ]
                
                return True, {
                    'expenses': expense_list,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
                
        except Exception as e:
            logger.error(f"Get group expenses error: {str(e)}")
            return False, {'error': 'Failed to get expenses'}
    
    @staticmethod
    def update_expense(
        expense_id: int,
        user_id: int,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        paid_by: Optional[int] = None,
        split_type: Optional[str] = None,
        splits: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        expense_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update an expense (personal or group)
        
        Args:
            expense_id: Expense ID
            user_id: Requesting user ID
            ... other fields to update
            
        Returns:
            Tuple of (success, expense_data/error)
        """
        try:
            with get_db_session() as session:
                expense = session.query(Expense).get(expense_id)
                
                if not expense or expense.is_deleted:
                    return False, {'error': 'Expense not found'}
                
                # Check permissions based on expense type
                if expense.group_id is None:
                    # Personal expense - only creator can update
                    if expense.created_by != user_id:
                        return False, {'error': 'You can only edit your own personal expenses'}
                    
                    logger.debug(f"Updating personal expense {expense_id}")
                    
                    # Track changes for history
                    changes = []
                    
                    # Update personal expense fields and track changes
                    if description is not None:
                        new_desc = description.strip()
                        if new_desc != expense.description:
                            changes.append({
                                'field': 'description',
                                'old': expense.description,
                                'new': new_desc
                            })
                        expense.description = new_desc
                    if amount is not None and float(amount) != float(expense.amount):
                        changes.append({
                            'field': 'amount',
                            'old': float(expense.amount),
                            'new': float(amount)
                        })
                        expense.amount = amount
                    if category is not None:
                        if category != expense.category:
                            changes.append({
                                'field': 'category',
                                'old': expense.category,
                                'new': category
                            })
                        expense.category = category
                    if expense_date:
                        try:
                            new_date = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
                            old_date_str = expense.expense_date.strftime('%Y-%m-%d') if expense.expense_date else None
                            new_date_str = new_date.strftime('%Y-%m-%d')
                            if old_date_str != new_date_str:
                                changes.append({
                                    'field': 'expense_date',
                                    'old': old_date_str,
                                    'new': new_date_str
                                })
                            expense.expense_date = new_date
                        except Exception as e:
                            logger.warning(f"Error parsing date {expense_date}: {e}")
                    if notes is not None:
                        new_notes = notes.strip() if notes else None
                        if new_notes != expense.notes:
                            changes.append({
                                'field': 'notes',
                                'old': expense.notes,
                                'new': new_notes
                            })
                        expense.notes = new_notes
                    
                    expense.is_edited = True
                    expense.updated_at = datetime.now(timezone.utc)
                    
                    logger.debug(f"Personal expense {expense_id}: {len(changes)} changes tracked")
                    
                    # Record history for personal expense with actual changes
                    history = ExpenseHistory(
                        expense_id=expense_id,
                        group_id=None,
                        action='updated',
                        changed_by=user_id,
                        changes_json=json.dumps(changes) if changes else '{}'
                    )
                    session.add(history)
                    
                    session.commit()
                    session.refresh(expense)
                    
                    return True, {'expense': ExpenseServiceSQL._get_expense_dict(session, expense)}
                
                # Group expense - verify membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == expense.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Check if user can edit (creator or group owner)
                group = session.query(Group).get(expense.group_id)
                is_group_owner = group and group.created_by == user_id
                is_expense_creator = expense.created_by == user_id
                
                if not is_group_owner and not is_expense_creator:
                    return False, {'error': 'You can only edit expenses you created'}
                
                # Store old values for balance reversal and change tracking
                old_amount = expense.amount
                old_paid_by = expense.paid_by
                old_description = expense.description
                old_category = expense.category
                old_date = expense.expense_date.strftime('%Y-%m-%d') if expense.expense_date else None
                old_notes = expense.notes
                
                old_splits = session.query(ExpenseSplit).filter(
                    ExpenseSplit.expense_id == expense_id
                ).all()
                
                # Track changes for history
                changes = []
                
                # Reverse old balances
                ExpenseServiceSQL._reverse_balances(
                    session, expense.group_id, old_splits, old_paid_by, old_amount
                )
                
                # Update expense fields and track changes
                if description:
                    new_desc = description.strip()
                    if new_desc != old_description:
                        changes.append({'field': 'description', 'old': old_description, 'new': new_desc})
                    expense.description = new_desc
                if amount is not None and float(amount) != float(old_amount):
                    changes.append({'field': 'amount', 'old': float(old_amount), 'new': float(amount)})
                    expense.amount = amount
                elif amount is not None:
                    expense.amount = amount
                if paid_by is not None and paid_by != old_paid_by:
                    changes.append({'field': 'paid_by', 'old': old_paid_by, 'new': paid_by})
                    expense.paid_by = paid_by
                elif paid_by is not None:
                    expense.paid_by = paid_by
                if split_type:
                    expense.split_type = split_type
                if category is not None and category != old_category:
                    changes.append({'field': 'category', 'old': old_category, 'new': category})
                    expense.category = category
                elif category is not None:
                    expense.category = category
                if expense_date:
                    try:
                        new_date = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
                        new_date_str = new_date.strftime('%Y-%m-%d')
                        if old_date != new_date_str:
                            changes.append({'field': 'expense_date', 'old': old_date, 'new': new_date_str})
                        expense.expense_date = new_date
                    except:
                        pass
                if notes is not None:
                    new_notes = notes.strip() if notes else None
                    if new_notes != old_notes:
                        changes.append({'field': 'notes', 'old': old_notes, 'new': new_notes})
                    expense.notes = new_notes
                
                expense.updated_at = datetime.now(timezone.utc)
                
                # Track split changes (Phase 18: Enhanced split history tracking)
                if splits is not None:
                    # Get the old split user IDs
                    old_split_user_ids = sorted([split.user_id for split in old_splits])
                    # Get the new split user IDs
                    new_split_user_ids = sorted([split['user_id'] for split in splits]) if splits else []
                    
                    # Only track if splits actually changed
                    if old_split_user_ids != new_split_user_ids:
                        # Get user display names for better history display
                        from app.domain.expenses.models import User
                        users_map = session.query(User).filter(
                            User.id.in_(old_split_user_ids + new_split_user_ids)
                        ).all()
                        user_dict = {u.id: u.display_name or f'User {u.id}' for u in users_map}
                        
                        # Calculate added and removed members
                        added_members = [uid for uid in new_split_user_ids if uid not in old_split_user_ids]
                        removed_members = [uid for uid in old_split_user_ids if uid not in new_split_user_ids]
                        
                        # Build detailed split change with member names
                        split_change = {
                            'field': 'splits',
                            'old': old_split_user_ids,
                            'new': new_split_user_ids,
                            'added_members': [
                                {'user_id': uid, 'name': user_dict.get(uid, f'User {uid}'), 'color': 'green'}
                                for uid in added_members
                            ],
                            'removed_members': [
                                {'user_id': uid, 'name': user_dict.get(uid, f'User {uid}'), 'color': 'red'}
                                for uid in removed_members
                            ]
                        }
                        changes.append(split_change)
                
                # Delete old splits
                session.query(ExpenseSplit).filter(
                    ExpenseSplit.expense_id == expense_id
                ).delete()
                
                # Calculate new splits
                new_splits = ExpenseServiceSQL._calculate_splits(
                    session,
                    expense.group_id,
                    expense_id,
                    expense.amount,
                    expense.paid_by,
                    expense.split_type,
                    splits
                )
                
                for split in new_splits:
                    session.add(split)
                
                # Determine actual split status (EQUAL or CUSTOM)
                # EQUAL = all group members included, CUSTOM = subset of members
                all_group_members = session.query(GroupMember).filter(
                    GroupMember.group_id == expense.group_id,
                    GroupMember.is_active == True
                ).count()
                
                split_count = len(new_splits)
                old_split_status = expense.split_type  # Store old status
                new_split_status = 'EQUAL' if split_count == all_group_members else 'CUSTOM'
                # Update split_type to reflect actual status
                expense.split_type = new_split_status
                
                # Track if split status changed
                if old_split_status != new_split_status:
                    changes.append({
                        'field': 'split_status',
                        'old': old_split_status,
                        'new': new_split_status
                    })
                
                # Update balances with new values
                ExpenseServiceSQL._update_balances(
                    session, expense.group_id, new_splits, expense.paid_by, expense.amount
                )
                
                # Record history with actual changes
                history = ExpenseHistory(
                    expense_id=expense_id,
                    group_id=expense.group_id,
                    action='updated',
                    changed_by=user_id,
                    changes_json=json.dumps(changes) if changes else '{}'
                )
                session.add(history)
                
                expense.is_edited = True
                session.commit()
                session.refresh(expense)
                
                # Get updated balances for instant UI update
                from app.services.settlement_service import \
                    settlement_service_sql
                balances_success, balances_result = settlement_service_sql.get_group_balances(expense.group_id, user_id)
                
                logger.info(f"Update expense {expense.id}: balances_success={balances_success}, balances_count={len(balances_result.get('balances', [])) if balances_success else 0}")
                
                result = {'expense': ExpenseServiceSQL._get_expense_dict(session, expense)}
                if balances_success:
                    result['balances'] = balances_result.get('balances', [])
                    logger.info(f"Returning balances: {result['balances']}")
                
                return True, result
                
        except Exception as e:
            logger.error(f"Update expense error: {str(e)}")
            return False, {'error': 'Failed to update expense'}
    
    @staticmethod
    def _reverse_balances(
        session,
        group_id: int,
        splits: List[ExpenseSplit],
        paid_by: int,
        total_amount: float
    ):
        """Reverse balance changes from an expense"""
        
        for split in splits:
            balance = session.query(GroupBalance).filter(
                GroupBalance.group_id == group_id,
                GroupBalance.user_id == split.user_id
            ).first()
            
            if balance:
                if split.user_id == paid_by:
                    balance.balance -= (Decimal(str(total_amount)) - Decimal(str(split.amount)))
                else:
                    balance.balance += Decimal(str(split.amount))
                balance.updated_at = datetime.now(timezone.utc)
    
    @staticmethod
    def delete_expense(expense_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete an expense (soft delete) - personal or group
        
        Args:
            expense_id: Expense ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                expense = session.query(Expense).get(expense_id)
                
                if not expense or expense.is_deleted:
                    return False, {'error': 'Expense not found'}
                
                # Check permissions based on expense type
                if expense.group_id is None:
                    # Personal expense - only creator can delete
                    if expense.created_by != user_id:
                        return False, {'error': 'You can only delete your own personal expenses'}
                else:
                    # Group expense - verify membership
                    member = session.query(GroupMember).filter(
                        GroupMember.group_id == expense.group_id,
                        GroupMember.user_id == user_id,
                        GroupMember.is_active == True
                    ).first()
                    
                    if not member:
                        return False, {'error': 'Not a member of this group'}
                    
                    # Check if user can delete (creator or group owner)
                    group = session.query(Group).get(expense.group_id)
                    is_group_owner = group and group.created_by == user_id
                    is_expense_creator = expense.created_by == user_id
                    
                    if not is_group_owner and not is_expense_creator:
                        return False, {'error': 'You can only delete expenses you created'}
                    
                    # Reverse balances for group expenses
                    old_splits = session.query(ExpenseSplit).filter(
                        ExpenseSplit.expense_id == expense_id
                    ).all()
                    
                    ExpenseServiceSQL._reverse_balances(
                        session, expense.group_id, old_splits, expense.paid_by, expense.amount
                    )
                
                # Store group_id before delete for balance retrieval
                group_id_for_balances = expense.group_id
                
                # Soft delete
                expense.is_deleted = True
                expense.deleted_by = user_id
                expense.deleted_at = datetime.now(timezone.utc)
                expense.updated_at = datetime.now(timezone.utc)
                
                # Record history
                history = ExpenseHistory(
                    expense_id=expense_id,
                    group_id=expense.group_id,
                    action='deleted',
                    changed_by=user_id,
                    changes_json='{}'
                )
                session.add(history)
                
                session.commit()
                
                logger.info(f"Expense deleted: {expense_id}")
                
                # Get updated balances for instant UI update if group expense
                result = {'message': 'Expense deleted successfully'}
                if group_id_for_balances:
                    from app.services.settlement_service import \
                        settlement_service_sql
                    balances_success, balances_result = settlement_service_sql.get_group_balances(group_id_for_balances, user_id)
                    if balances_success:
                        result['balances'] = balances_result.get('balances', [])
                
                return True, result
                
        except Exception as e:
            logger.error(f"Delete expense error: {str(e)}")
            return False, {'error': 'Failed to delete expense'}
    
    @staticmethod
    def get_user_expenses(
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        personal_only: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all expenses involving a user (both personal and group)
        
        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset
            personal_only: If True, only return personal expenses (no group)
            
        Returns:
            Tuple of (success, expenses_list/error)
        """
        try:
            with get_db_session() as session:
                from sqlalchemy import or_
                
                if personal_only:
                    # Only personal expenses (include deleted to show faded)
                    query = session.query(Expense).filter(
                        Expense.group_id.is_(None),
                        Expense.created_by == user_id
                    )
                else:
                    # Get user's groups
                    memberships = session.query(GroupMember).filter(
                        GroupMember.user_id == user_id,
                        GroupMember.is_active == True
                    ).all()
                    
                    group_ids = [m.group_id for m in memberships]
                    
                    # Get both group expenses and personal expenses
                    if group_ids:
                        query = session.query(Expense).filter(
                            or_(
                                Expense.group_id.in_(group_ids),
                                (Expense.group_id.is_(None) & (Expense.created_by == user_id))
                            )
                        )
                    else:
                        # Only personal expenses (no groups, include deleted)
                        query = session.query(Expense).filter(
                            Expense.group_id.is_(None),
                            Expense.created_by == user_id
                        )
                
                total = query.count()
                
                expenses = query.order_by(
                    Expense.expense_date.desc()
                ).offset(offset).limit(limit).all()
                
                expense_list = [
                    ExpenseServiceSQL._get_expense_dict(session, e)
                    for e in expenses
                ]
                
                return True, {
                    'expenses': expense_list,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
                
        except Exception as e:
            logger.error(f"Get user expenses error: {str(e)}")
            return False, {'error': 'Failed to get expenses'}
    
    @staticmethod
    def get_expense_history(
        expense_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get expense edit history
        
        Args:
            expense_id: Expense ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, history_list/error)
        """
        try:
            with get_db_session() as session:
                # Get expense first
                expense = session.query(Expense).get(expense_id)
                
                if not expense:
                    return False, {'error': 'Expense not found'}
                
                # Check permissions
                if expense.group_id is None:
                    # Personal expense
                    if expense.created_by != user_id:
                        return False, {'error': 'Not authorized to view this expense history'}
                else:
                    # Group expense - verify membership
                    member = session.query(GroupMember).filter(
                        GroupMember.group_id == expense.group_id,
                        GroupMember.user_id == user_id,
                        GroupMember.is_active == True
                    ).first()
                    
                    if not member:
                        return False, {'error': 'Not a member of this group'}
                
                # Get history entries
                history_entries = session.query(ExpenseHistory).filter(
                    ExpenseHistory.expense_id == expense_id
                ).order_by(ExpenseHistory.created_at.desc()).all()
                
                history_list = [entry.to_dict() for entry in history_entries]
                
                return True, {
                    'history': history_list,
                    'expense_id': expense_id,
                    'count': len(history_list)
                }
                
        except Exception as e:
            logger.error(f"Get expense history error: {str(e)}")
            return False, {'error': 'Failed to get expense history'}


# Create singleton instance
expense_service_sql = ExpenseServiceSQL()

# Create singleton instance
expense_service_sql = ExpenseServiceSQL()
