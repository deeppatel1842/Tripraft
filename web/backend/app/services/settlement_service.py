"""
SQL-based Settlement Service
Handles settling debts between users
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Config
from app.domain.expenses.models import (Group, GroupBalance, GroupMember,
                                        Settlement, User)
from app.infrastructure.db.connection import get_db_session
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class SettlementServiceSQL:
    """Service for settlement operations using SQL database"""
    
    @staticmethod
    def create_settlement(
        user_id: str,
        group_id: str,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        method: str = 'cash',
        notes: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a settlement (debt payment)
        
        Args:
            user_id: ID of user creating the settlement
            group_id: Group ID
            from_user_id: User who is paying (owes money)
            to_user_id: User who is receiving (is owed money)
            amount: Settlement amount
            method: Payment method ('cash', 'upi', 'bank_transfer', etc.)
            notes: Optional notes
            
        Returns:
            Tuple of (success, settlement_data/error)
        """
        try:
            with get_db_session() as session:
                # Verify group membership for all parties
                for uid in [user_id, from_user_id, to_user_id]:
                    member = session.query(GroupMember).filter(
                        GroupMember.group_id == group_id,
                        GroupMember.user_id == uid,
                        GroupMember.is_active == True
                    ).first()
                    
                    if not member:
                        return False, {'error': f'User {uid} is not a member of this group'}
                
                if amount <= 0:
                    return False, {'error': 'Amount must be positive'}
                
                if from_user_id == to_user_id:
                    return False, {'error': 'Cannot settle with yourself'}
                
                # Get group
                group = session.query(Group).get(group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                
                # Create settlement
                settlement = Settlement(
                    group_id=group_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    amount=amount,
                    currency=group.currency,
                    method=method,
                    notes=notes.strip() if notes else None,
                    recorded_by=user_id
                )
                session.add(settlement)
                
                # Update balances
                # from_user pays -> their balance increases (less debt)
                # to_user receives -> their balance decreases (less credit)
                
                from_balance = session.query(GroupBalance).filter(
                    GroupBalance.group_id == group_id,
                    GroupBalance.user_id == from_user_id
                ).first()
                
                to_balance = session.query(GroupBalance).filter(
                    GroupBalance.group_id == group_id,
                    GroupBalance.user_id == to_user_id
                ).first()
                
                if from_balance:
                    from_balance.balance += Decimal(str(amount))
                    from_balance.updated_at = datetime.now(timezone.utc)
                
                if to_balance:
                    to_balance.balance -= Decimal(str(amount))
                    to_balance.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(settlement)
                
                logger.info(f"Settlement created: {settlement.id} in group {group_id}")
                
                return True, {'settlement': SettlementServiceSQL._get_settlement_dict(session, settlement)}
                
        except Exception as e:
            logger.error(f"Create settlement error: {str(e)}")
            return False, {'error': 'Failed to create settlement'}
    
    @staticmethod
    def _get_settlement_dict(session, settlement: Settlement) -> Dict[str, Any]:
        """
        Get settlement as dictionary with user info.
        
        Expects settlement.from_user and settlement.to_user to be eager-loaded.
        Falls back to individual queries if not loaded.
        """
        data = settlement.to_dict()
        
        from_user = settlement.from_user or session.query(User).get(settlement.from_user_id)
        to_user = settlement.to_user or session.query(User).get(settlement.to_user_id)
        
        if from_user:
            data['from_user'] = {
                'id': from_user.id,
                'display_name': from_user.display_name,
                'email': from_user.email
            }
            data['from_display_name'] = from_user.display_name
        
        if to_user:
            data['to_user'] = {
                'id': to_user.id,
                'display_name': to_user.display_name,
                'email': to_user.email
            }
            data['to_display_name'] = to_user.display_name
        
        return data
    
    @staticmethod
    def get_settlement(settlement_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get settlement details
        
        Args:
            settlement_id: Settlement ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, settlement_data/error)
        """
        try:
            with get_db_session() as session:
                settlement = session.query(Settlement).options(
                    joinedload(Settlement.from_user),
                    joinedload(Settlement.to_user),
                ).get(settlement_id)
                
                if not settlement or settlement.is_deleted:
                    return False, {'error': 'Settlement not found'}
                
                # Verify membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == settlement.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                return True, {'settlement': SettlementServiceSQL._get_settlement_dict(session, settlement)}
                
        except Exception as e:
            logger.error(f"Get settlement error: {str(e)}")
            return False, {'error': 'Failed to get settlement'}
    
    @staticmethod
    def get_group_settlements(
        group_id: str,
        user_id: str,
        limit: int = Config.EXPENSE_DEFAULT_LIMIT,
        offset: int = 0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get settlements for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Tuple of (success, settlements_list/error)
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
                
                settlements = session.query(Settlement).options(
                    joinedload(Settlement.from_user),
                    joinedload(Settlement.to_user),
                ).filter(
                    Settlement.group_id == group_id,
                    Settlement.is_deleted == False
                ).order_by(Settlement.created_at.desc()).offset(offset).limit(limit).all()
                
                total = session.query(Settlement).filter(
                    Settlement.group_id == group_id,
                    Settlement.is_deleted == False
                ).count()
                
                settlement_list = [
                    SettlementServiceSQL._get_settlement_dict(session, s)
                    for s in settlements
                ]
                
                return True, {
                    'settlements': settlement_list,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
                
        except Exception as e:
            logger.error(f"Get group settlements error: {str(e)}")
            return False, {'error': 'Failed to get settlements'}
    
    @staticmethod
    def delete_settlement(settlement_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a settlement (soft delete and reverse balances)
        
        Args:
            settlement_id: Settlement ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                settlement = session.query(Settlement).get(settlement_id)
                
                if not settlement or settlement.is_deleted:
                    return False, {'error': 'Settlement not found'}
                
                # Verify membership
                member = session.query(GroupMember).filter(
                    GroupMember.group_id == settlement.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Reverse balance changes
                from_balance = session.query(GroupBalance).filter(
                    GroupBalance.group_id == settlement.group_id,
                    GroupBalance.user_id == settlement.from_user_id
                ).first()
                
                to_balance = session.query(GroupBalance).filter(
                    GroupBalance.group_id == settlement.group_id,
                    GroupBalance.user_id == settlement.to_user_id
                ).first()
                
                if from_balance:
                    from_balance.balance -= Decimal(str(settlement.amount))
                    from_balance.updated_at = datetime.now(timezone.utc)
                
                if to_balance:
                    to_balance.balance += Decimal(str(settlement.amount))
                    to_balance.updated_at = datetime.now(timezone.utc)
                
                # Soft delete
                settlement.is_deleted = True
                settlement.deleted_by = user_id
                settlement.deleted_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Settlement deleted: {settlement_id}")
                return True, {'message': 'Settlement deleted successfully'}
                
        except Exception as e:
            logger.error(f"Delete settlement error: {str(e)}")
            return False, {'error': 'Failed to delete settlement'}
    
    @staticmethod
    def get_group_balances(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all balances for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, balances_data/error)
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
                
                balances = session.query(GroupBalance, User).join(
                    User, GroupBalance.user_id == User.id
                ).filter(
                    GroupBalance.group_id == group_id
                ).all()
                
                balance_list = [
                    {
                        'user_id': balance.user_id,
                        'balance': float(balance.balance) if balance.balance else 0.0,
                        'net_balance': float(balance.balance) if balance.balance else 0.0,  # Frontend expects net_balance
                        'display_name': user.display_name,  # Frontend needs this at top level
                        'user': {
                            'id': user.id,
                            'display_name': user.display_name,
                            'email': user.email
                        }
                    }
                    for balance, user in balances
                ]
                
                return True, {'balances': balance_list}
                
        except Exception as e:
            logger.error(f"Get group balances error: {str(e)}")
            return False, {'error': 'Failed to get balances'}
    
    @staticmethod
    def get_simplified_debts(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get simplified debts (who owes whom)
        Uses balance simplification algorithm
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, debts_list/error)
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
                
                balances = session.query(GroupBalance, User).join(
                    User, GroupBalance.user_id == User.id
                ).filter(
                    GroupBalance.group_id == group_id
                ).all()
                
                # Separate into creditors (positive balance) and debtors (negative balance)
                creditors = []  # People who are owed money
                debtors = []    # People who owe money
                
                for balance, user in balances:
                    if balance.balance > Config.BALANCE_THRESHOLD:
                        creditors.append({
                            'user_id': user.id,
                            'display_name': user.display_name,
                            'email': user.email,
                            'amount': balance.balance
                        })
                    elif balance.balance < -Config.BALANCE_THRESHOLD:
                        debtors.append({
                            'user_id': user.id,
                            'display_name': user.display_name,
                            'email': user.email,
                            'amount': abs(balance.balance)
                        })
                
                # Calculate simplified debts
                # Simple greedy algorithm: match largest debtor with largest creditor
                debts = []
                
                creditors.sort(key=lambda x: x['amount'], reverse=True)
                debtors.sort(key=lambda x: x['amount'], reverse=True)
                
                i, j = 0, 0
                while i < len(creditors) and j < len(debtors):
                    creditor = creditors[i]
                    debtor = debtors[j]
                    
                    settle_amount = min(creditor['amount'], debtor['amount'])
                    
                    if settle_amount > Config.BALANCE_THRESHOLD:
                        debts.append({
                            'from_user': {
                                'id': debtor['user_id'],
                                'display_name': debtor['display_name'],
                                'email': debtor['email']
                            },
                            'to_user': {
                                'id': creditor['user_id'],
                                'display_name': creditor['display_name'],
                                'email': creditor['email']
                            },
                            'amount': round(settle_amount, 2)
                        })
                    
                    creditor['amount'] -= settle_amount
                    debtor['amount'] -= settle_amount
                    
                    if creditor['amount'] < Config.BALANCE_THRESHOLD:
                        i += 1
                    if debtor['amount'] < Config.BALANCE_THRESHOLD:
                        j += 1
                
                return True, {'debts': debts}
                
        except Exception as e:
            logger.error(f"Get simplified debts error: {str(e)}")
            return False, {'error': 'Failed to get simplified debts'}
    
    @staticmethod
    def get_user_total_balance(user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get user's total balance across all groups
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, balance_summary/error)
        """
        try:
            with get_db_session() as session:
                balances = session.query(GroupBalance, Group).join(
                    Group, GroupBalance.group_id == Group.id
                ).filter(
                    GroupBalance.user_id == user_id,
                    Group.is_active == True
                ).all()
                
                total_owed = 0.0  # Money owed to user
                total_owes = 0.0  # Money user owes
                
                group_balances = []
                for balance, group in balances:
                    if balance.balance > 0:
                        total_owed += balance.balance
                    else:
                        total_owes += abs(balance.balance)
                    
                    group_balances.append({
                        'group_id': group.id,
                        'group_name': group.name,
                        'balance': balance.balance,
                        'currency': group.currency
                    })
                
                return True, {
                    'total_owed': round(total_owed, 2),
                    'total_owes': round(total_owes, 2),
                    'net_balance': round(total_owed - total_owes, 2),
                    'group_balances': group_balances
                }
                
        except Exception as e:
            logger.error(f"Get user total balance error: {str(e)}")
            return False, {'error': 'Failed to get balance summary'}


# Create singleton instance
settlement_service_sql = SettlementServiceSQL()
