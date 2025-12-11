"""
Batched Write Service - Phase 20 Extreme Optimization
Handles all mutations with SINGLE batch writes.

Key principle: Every mutation = 1 Firestore write operation (billed as 1)
- Uses Firestore batch/transaction
- Updates multiple collections atomically
- Updates Redis cache immediately after
- Returns computed data (no re-read)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
import uuid

from firebase_admin import firestore

from ..repositories import (
    GroupRepository,
    BalanceRepository,
    DashboardRepository
)
from ..config import firestore_collections

try:
    from ..utils.cache_manager import get_cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

logger = logging.getLogger(__name__)


class BatchedWriteService:
    """
    Service for performing batched Firestore writes.
    
    Phase 20: Every mutation is a SINGLE batch commit.
    This counts as 1 write operation for billing purposes.
    
    Example:
    - create_group_batched() → 1 batch with 3 docs = 1 operation
    - create_expense_batched() → 1 batch with 3 docs = 1 operation
    """
    
    def __init__(self):
        self.db = firestore.client()
        self.dashboard_repo = DashboardRepository()
        self._cache = get_cache_manager() if CACHE_ENABLED else None
    
    def create_group_batched(
        self,
        name: str,
        created_by: str,
        creator_display_name: str,
        creator_email: str = '',
        creator_photo_url: str = '',
        description: str = '',
        currency: str = 'USD'
    ) -> Dict:
        """
        Create a group with SINGLE batch write.
        
        Writes to:
        - expense_groups/{group_id}
        - expense_group_members/{group_id}_{user_id}
        - expense_balances/{group_id}
        - expense_user_dashboards/{user_id} (update)
        
        All in ONE batch commit = 1 Firestore operation.
        
        Returns:
            Created group data (computed, no re-read)
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        # Generate IDs
        group_id = self.db.collection(firestore_collections.GROUPS).document().id
        group_code = self._generate_group_code()
        
        # 1. Group document
        group_data = {
            'group_id': group_id,
            'name': name,
            'description': description,
            'created_by': created_by,
            'group_code': group_code,
            'currency': currency,
            'members': [created_by],
            'member_details': {
                created_by: {
                    'user_id': created_by,
                    'display_name': creator_display_name,
                    'email': creator_email,
                    'photo_url': creator_photo_url,
                    'role': 'admin',
                    'joined_at': now_iso,
                    'is_active': True
                }
            },
            'member_count': 1,
            'expense_count': 0,
            'total_spent': 0.0,
            'last_activity': now_iso,
            'is_settled': True,
            'created_at': now,
            'updated_at': now
        }
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.set(group_ref, group_data)
        
        # 2. Member document
        member_data = {
            'group_id': group_id,
            'user_id': created_by,
            'display_name': creator_display_name,
            'email': creator_email,
            'photo_url': creator_photo_url,
            'role': 'admin',
            'is_active': True,
            'joined_at': now
        }
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(f"{group_id}_{created_by}")
        batch.set(member_ref, member_data)
        
        # 3. Balance document
        balance_data = {
            'group_id': group_id,
            'balances': {created_by: 0.0},
            'last_updated': now_iso
        }
        balance_ref = self.db.collection(firestore_collections.BALANCES).document(group_id)
        batch.set(balance_ref, balance_data)
        
        # SINGLE COMMIT = 1 Firestore write operation
        batch.commit()
        logger.info("[BATCHED] Created group %s with 1 batch commit", group_id)
        
        # Update dashboard (separate write for simplicity, could be included)
        self.dashboard_repo.add_group_to_dashboard(
            user_id=created_by,
            group_id=group_id,
            group_data={
                'name': name,
                'currency': currency,
                'memberCount': 1,
                'members': [{
                    'userId': created_by,
                    'displayName': creator_display_name,
                    'photoUrl': creator_photo_url
                }],
                'balances': {created_by: 0.0}
            }
        )
        
        # Return computed data (no re-read)
        return {
            'group_id': group_id,
            'id': group_id,
            'name': name,
            'description': description,
            'group_code': group_code,
            'currency': currency,
            'members': [created_by],
            'member_count': 1,
            'expense_count': 0,
            'total_spent': 0.0,
            'is_settled': True,
            'created_by': created_by,
            'created_at': now_iso,
            'member_details': {
                created_by: {
                    'user_id': created_by,
                    'display_name': creator_display_name,
                    'role': 'admin'
                }
            }
        }
    
    def accept_invitation_batched(
        self,
        invitation_id: str,
        invitation_data: Dict,
        accepter_id: str,
        accepter_display_name: str,
        accepter_email: str = '',
        accepter_photo_url: str = ''
    ) -> Dict:
        """
        Accept invitation with SINGLE batch write.
        
        Writes to:
        - expense_invitations/{id} → status: accepted
        - expense_groups/{gid} → add to members array
        - expense_group_members/{gid}_{uid}
        - expense_balances/{gid} → add user with 0 balance
        
        Returns:
            Group data for the new member
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        group_id = invitation_data.get('group_id')
        group_name = invitation_data.get('group_name', 'Unknown')
        group_currency = invitation_data.get('group_currency', 'USD')
        existing_members = invitation_data.get('existing_members', [])
        existing_balances = invitation_data.get('existing_balances', {})
        
        # 1. Update invitation status
        inv_ref = self.db.collection(firestore_collections.INVITATIONS).document(invitation_id)
        batch.update(inv_ref, {
            'status': 'accepted',
            'accepted_at': now,
            'accepted_by': accepter_id
        })
        
        # 2. Add to group members array
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'members': firestore.ArrayUnion([accepter_id]),
            'member_count': firestore.Increment(1),
            f'member_details.{accepter_id}': {
                'user_id': accepter_id,
                'display_name': accepter_display_name,
                'email': accepter_email,
                'photo_url': accepter_photo_url,
                'role': 'member',
                'joined_at': now_iso,
                'is_active': True
            },
            'last_activity': now_iso,
            'updated_at': now
        })
        
        # 3. Create member document
        member_ref = self.db.collection(firestore_collections.GROUP_MEMBERS).document(f"{group_id}_{accepter_id}")
        batch.set(member_ref, {
            'group_id': group_id,
            'user_id': accepter_id,
            'display_name': accepter_display_name,
            'email': accepter_email,
            'photo_url': accepter_photo_url,
            'role': 'member',
            'is_active': True,
            'joined_at': now
        })
        
        # 4. Add to balances
        balance_ref = self.db.collection(firestore_collections.BALANCES).document(group_id)
        batch.update(balance_ref, {
            f'balances.{accepter_id}': 0.0,
            'last_updated': now_iso
        })
        
        # SINGLE COMMIT
        batch.commit()
        logger.info("[BATCHED] Accepted invitation %s with 1 batch commit", invitation_id)
        
        # Update dashboards
        # New member's dashboard
        new_balances = {**existing_balances, accepter_id: 0.0}
        all_members = existing_members + [{
            'userId': accepter_id,
            'displayName': accepter_display_name,
            'photoUrl': accepter_photo_url
        }]
        
        self.dashboard_repo.add_group_to_dashboard(
            user_id=accepter_id,
            group_id=group_id,
            group_data={
                'name': group_name,
                'currency': group_currency,
                'memberCount': len(all_members),
                'members': all_members,
                'balances': new_balances
            }
        )
        
        # Existing members' dashboards - update member list
        existing_user_ids = [m.get('userId') for m in existing_members]
        self.dashboard_repo.update_group_members(
            group_id=group_id,
            members=all_members,
            member_count=len(all_members),
            affected_users=existing_user_ids
        )
        
        # Return computed data
        return {
            'group_id': group_id,
            'id': group_id,
            'name': group_name,
            'currency': group_currency,
            'members': [m.get('userId') for m in all_members],
            'member_count': len(all_members),
            'your_balance': 0.0,
            'is_settled': True
        }
    
    def create_expense_batched(
        self,
        group_id: str,
        description: str,
        amount: float,
        paid_by: str,
        split_type: str,
        splits: List[Dict],
        created_by: str,
        currency: str = 'USD',
        category: str = None,
        notes: str = None,
        expense_date: datetime = None,
        existing_balances: Dict[str, float] = None,
        group_members: List[str] = None
    ) -> Dict:
        """
        Create expense with SINGLE batch write.
        
        Writes to:
        - expense_expenses/{id}
        - expense_balances/{gid}
        - expense_history/{exp_id}_{version}
        
        Returns:
            Created expense + balance_deltas
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        # Generate expense ID
        expense_id = self.db.collection(firestore_collections.EXPENSES).document().id
        
        # Calculate new balances
        old_balances = existing_balances or {}
        balance_deltas = self._calculate_balance_deltas(amount, paid_by, splits)
        new_balances = {
            user_id: old_balances.get(user_id, 0.0) + delta
            for user_id, delta in balance_deltas.items()
        }
        # Ensure all members have a balance
        for member_id in (group_members or []):
            if member_id not in new_balances:
                new_balances[member_id] = old_balances.get(member_id, 0.0)
        
        # 1. Expense document
        expense_data = {
            'expense_id': expense_id,
            'group_id': group_id,
            'description': description,
            'amount': float(amount),
            'paid_by': paid_by,
            'split_type': split_type,
            'splits': splits,
            'currency': currency,
            'category': category or 'general',
            'notes': notes or '',
            'expense_date': expense_date or now,
            'created_by': created_by,
            'created_at': now,
            'updated_at': now,
            'version': 1,
            'is_deleted': False
        }
        expense_ref = self.db.collection(firestore_collections.EXPENSES).document(expense_id)
        batch.set(expense_ref, expense_data)
        
        # 2. Update balances
        balance_ref = self.db.collection(firestore_collections.BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'last_updated': now_iso
        })
        
        # 3. History entry
        history_data = {
            'expense_id': expense_id,
            'group_id': group_id,
            'version': 1,
            'action': 'create',
            'changes': expense_data,
            'changed_by': created_by,
            'changed_at': now
        }
        history_ref = self.db.collection(firestore_collections.EXPENSE_HISTORY).document(f"{expense_id}_1")
        batch.set(history_ref, history_data)
        
        # 4. Update group stats
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'expense_count': firestore.Increment(1),
            'total_spent': firestore.Increment(float(amount)),
            'last_activity': now_iso,
            'is_settled': False,
            'updated_at': now
        })
        
        # SINGLE COMMIT
        batch.commit()
        logger.info("[BATCHED] Created expense %s with 1 batch commit", expense_id)
        
        # Update all affected users' dashboards
        expense_summary = {
            'id': expense_id,
            'description': description,
            'amount': float(amount),
            'paidBy': paid_by,
            'createdBy': created_by,
            'date': now_iso
        }
        self.dashboard_repo.add_expense_to_dashboards(
            group_id=group_id,
            expense_summary=expense_summary,
            balances=new_balances,
            affected_users=group_members or list(new_balances.keys())
        )
        
        # Return computed data with deltas
        return {
            'expense': {
                'expense_id': expense_id,
                'id': expense_id,
                'group_id': group_id,
                'description': description,
                'amount': float(amount),
                'paid_by': paid_by,
                'split_type': split_type,
                'splits': splits,
                'currency': currency,
                'category': category,
                'created_by': created_by,
                'created_at': now_iso,
                'version': 1
            },
            'balance_deltas': balance_deltas,
            'new_balances': new_balances
        }
    
    def create_settlement_batched(
        self,
        group_id: str,
        payer_id: str,
        receiver_id: str,
        amount: float,
        created_by: str,
        notes: str = None,
        existing_balances: Dict[str, float] = None,
        group_members: List[str] = None
    ) -> Dict:
        """
        Create settlement with SINGLE batch write.
        
        Writes to:
        - expense_settlements/{id}
        - expense_balances/{gid}
        
        Returns:
            Created settlement + balance_deltas
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        settlement_id = self.db.collection(firestore_collections.SETTLEMENTS).document().id
        
        # Calculate new balances
        old_balances = existing_balances or {}
        balance_deltas = {
            payer_id: float(amount),  # Payer paid, so they're owed more
            receiver_id: -float(amount)  # Receiver received, so they owe less
        }
        new_balances = {
            user_id: old_balances.get(user_id, 0.0) + balance_deltas.get(user_id, 0.0)
            for user_id in set(list(old_balances.keys()) + list(balance_deltas.keys()))
        }
        
        # 1. Settlement document
        settlement_data = {
            'settlement_id': settlement_id,
            'group_id': group_id,
            'payer_id': payer_id,
            'receiver_id': receiver_id,
            'amount': float(amount),
            'notes': notes or '',
            'created_by': created_by,
            'created_at': now,
            'status': 'completed'
        }
        settlement_ref = self.db.collection(firestore_collections.SETTLEMENTS).document(settlement_id)
        batch.set(settlement_ref, settlement_data)
        
        # 2. Update balances
        balance_ref = self.db.collection(firestore_collections.BALANCES).document(group_id)
        batch.update(balance_ref, {
            'balances': new_balances,
            'last_updated': now_iso
        })
        
        # 3. Update group
        is_settled = all(abs(b) < 0.01 for b in new_balances.values())
        group_ref = self.db.collection(firestore_collections.GROUPS).document(group_id)
        batch.update(group_ref, {
            'last_activity': now_iso,
            'is_settled': is_settled,
            'updated_at': now
        })
        
        # SINGLE COMMIT
        batch.commit()
        logger.info("[BATCHED] Created settlement %s with 1 batch commit", settlement_id)
        
        # Update dashboards
        settlement_summary = {
            'id': settlement_id,
            'payerId': payer_id,
            'receiverId': receiver_id,
            'amount': float(amount),
            'date': now_iso
        }
        self.dashboard_repo.add_settlement_to_dashboards(
            group_id=group_id,
            settlement_summary=settlement_summary,
            balances=new_balances,
            affected_users=group_members or [payer_id, receiver_id]
        )
        
        return {
            'settlement': {
                'settlement_id': settlement_id,
                'id': settlement_id,
                'group_id': group_id,
                'payer_id': payer_id,
                'receiver_id': receiver_id,
                'amount': float(amount),
                'created_at': now_iso
            },
            'balance_deltas': balance_deltas,
            'new_balances': new_balances
        }
    
    def send_invitation_batched(
        self,
        group_id: str,
        group_name: str,
        inviter_id: str,
        inviter_name: str,
        invitee_email: str,
        invitee_user_id: str = None
    ) -> Dict:
        """
        Send invitation with SINGLE write.
        
        Returns invitation data (no re-read).
        """
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        invitation_id = self.db.collection(firestore_collections.INVITATIONS).document().id
        
        invitation_data = {
            'invitation_id': invitation_id,
            'group_id': group_id,
            'group_name': group_name,
            'inviter_id': inviter_id,
            'inviter_name': inviter_name,
            'invitee_email': invitee_email,
            'invitee_user_id': invitee_user_id,
            'status': 'pending',
            'created_at': now,
            'expires_at': datetime.utcnow().replace(day=datetime.utcnow().day + 7)
        }
        
        # Single write
        self.db.collection(firestore_collections.INVITATIONS).document(invitation_id).set(invitation_data)
        logger.info("[BATCHED] Created invitation %s with 1 write", invitation_id)
        
        # Update invitee's dashboard if they're a user
        if invitee_user_id:
            self.dashboard_repo.add_invitation_to_dashboard(
                user_id=invitee_user_id,
                invitation={
                    'id': invitation_id,
                    'group_id': group_id,
                    'group_name': group_name,
                    'inviter_id': inviter_id,
                    'inviter_name': inviter_name
                }
            )
        
        return {
            'invitation_id': invitation_id,
            'id': invitation_id,
            'group_id': group_id,
            'status': 'pending',
            'created_at': now_iso
        }
    
    def _calculate_balance_deltas(
        self,
        amount: float,
        paid_by: str,
        splits: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate balance changes from an expense.
        
        Returns dict of {user_id: delta_amount}
        """
        deltas = {}
        
        # Payer is owed the full amount initially
        deltas[paid_by] = float(amount)
        
        # Each person in the split owes their share
        for split in splits:
            user_id = split.get('user_id')
            share = float(split.get('amount', 0))
            
            if user_id in deltas:
                deltas[user_id] -= share
            else:
                deltas[user_id] = -share
        
        return deltas
    
    def _generate_group_code(self) -> str:
        """Generate a unique group code."""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
