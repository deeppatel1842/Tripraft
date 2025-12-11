"""
Settlement Repository
Handles settlement data access and payment tracking
"""

from typing import List, Optional, Dict
from datetime import datetime
from google.cloud.firestore import ArrayUnion
import logging

from .base import BaseRepository
from ..config import firestore_collections
from ..models.settlement import Settlement
from ..exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class SettlementRepository(BaseRepository[Settlement]):
    """
    Repository for settlement management
    Handles settlement CRUD and payment tracking
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.SETTLEMENTS
    
    def get_group_settlements(
        self,
        group_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get settlements for a group
        
        Args:
            group_id: Group ID
            status: Optional status filter (pending/completed/cancelled)
            limit: Maximum settlements to return
            
        Returns:
            List of settlement documents
        """
        try:
            filters = [('group_id', '==', group_id)]
            if status:
                filters.append(('status', '==', status))
            
            settlements = self.query(
                filters=filters,
                order_by=('created_at', 'DESCENDING'),
                limit=limit
            )
            
            return settlements
            
        except Exception as exc:
            logger.error("Error getting group settlements: %s", str(exc))
            raise
    
    def get_user_settlements(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        as_payer: bool = False,
        as_receiver: bool = False
    ) -> List[Dict]:
        """
        Get settlements involving a user
        
        Args:
            user_id: User ID
            group_id: Optional group filter
            as_payer: Filter where user is payer
            as_receiver: Filter where user is receiver
            
        Returns:
            List of settlement documents
        """
        try:
            filters = []
            
            if group_id:
                filters.append(('group_id', '==', group_id))
            
            if as_payer:
                filters.append(('payer_id', '==', user_id))
            elif as_receiver:
                filters.append(('receiver_id', '==', user_id))
            else:
                # Get both - need to do two queries
                payer_settlements = self.query(
                    filters=filters + [('payer_id', '==', user_id)],
                    order_by=('created_at', 'DESCENDING')
                )
                receiver_settlements = self.query(
                    filters=filters + [('receiver_id', '==', user_id)],
                    order_by=('created_at', 'DESCENDING')
                )
                
                # Combine and sort
                all_settlements = payer_settlements + receiver_settlements
                all_settlements.sort(
                    key=lambda x: x.get('created_at', datetime.min),
                    reverse=True
                )
                return all_settlements
            
            settlements = self.query(
                filters=filters,
                order_by=('created_at', 'DESCENDING')
            )
            
            return settlements
            
        except Exception as exc:
            logger.error("Error getting user settlements: %s", str(exc))
            raise
    
    def get_pending_settlements(
        self,
        group_id: str,
        payer_id: Optional[str] = None,
        receiver_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get pending settlements for a group
        
        Args:
            group_id: Group ID
            payer_id: Optional payer filter
            receiver_id: Optional receiver filter
            
        Returns:
            List of pending settlement documents
        """
        try:
            filters = [
                ('group_id', '==', group_id),
                ('status', '==', 'pending')
            ]
            
            if payer_id:
                filters.append(('payer_id', '==', payer_id))
            if receiver_id:
                filters.append(('receiver_id', '==', receiver_id))
            
            settlements = self.query(
                filters=filters,
                order_by=('created_at', 'ASCENDING')
            )
            
            return settlements
            
        except Exception as exc:
            logger.error("Error getting pending settlements: %s", str(exc))
            raise
    
    def mark_as_completed(
        self,
        settlement_id: str,
        completed_by: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Mark a settlement as completed
        
        Args:
            settlement_id: Settlement ID
            completed_by: User ID who completed it
            notes: Optional completion notes
        """
        try:
            settlement_data = self.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            update_data = {
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'completed_by': completed_by
            }
            
            if notes:
                update_data['notes'] = notes
            
            self.update(settlement_id, update_data)
            
            logger.info("Marked settlement %s as completed", settlement_id)
            
        except Exception as exc:
            logger.error("Error marking settlement as completed: %s", str(exc))
            raise
    
    def mark_as_cancelled(
        self,
        settlement_id: str,
        cancelled_by: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Cancel a settlement
        
        Args:
            settlement_id: Settlement ID
            cancelled_by: User ID who cancelled it
            reason: Optional cancellation reason
        """
        try:
            settlement_data = self.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            update_data = {
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow(),
                'cancelled_by': cancelled_by
            }
            
            if reason:
                update_data['cancellation_reason'] = reason
            
            self.update(settlement_id, update_data)
            
            logger.info("Cancelled settlement %s", settlement_id)
            
        except Exception as exc:
            logger.error("Error cancelling settlement: %s", str(exc))
            raise
    
    def add_payment_proof(
        self,
        settlement_id: str,
        proof_type: str,
        proof_url: str,
        uploaded_by: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Add payment proof to a settlement
        
        Args:
            settlement_id: Settlement ID
            proof_type: Type of proof (screenshot/receipt/transaction_id)
            proof_url: URL to proof file or transaction ID
            uploaded_by: User ID who uploaded proof
            notes: Optional notes
        """
        try:
            settlement_data = self.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            proof_data = {
                'proof_type': proof_type,
                'proof_url': proof_url,
                'uploaded_by': uploaded_by,
                'uploaded_at': datetime.utcnow()
            }
            
            if notes:
                proof_data['notes'] = notes
            
            self.update(settlement_id, {
                'payment_proof': ArrayUnion([proof_data])
            })
            
            logger.info("Added payment proof to settlement %s", settlement_id)
            
        except Exception as exc:
            logger.error("Error adding payment proof: %s", str(exc))
            raise
    
    def soft_delete_settlement(self, settlement_id: str) -> None:
        """
        Soft delete a settlement (mark as deleted)
        
        Args:
            settlement_id: Settlement ID
        """
        try:
            settlement_data = self.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            self.update(settlement_id, {
                'is_deleted': True,
                'deleted_at': datetime.utcnow()
            })
            
            logger.info("Soft deleted settlement: %s", settlement_id)
            
        except Exception as exc:
            logger.error("Error soft deleting settlement: %s", str(exc))
            raise
    
    def restore_settlement(self, settlement_id: str) -> None:
        """
        Restore a soft-deleted settlement
        
        Args:
            settlement_id: Settlement ID
        """
        try:
            settlement_data = self.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            self.update(settlement_id, {
                'is_deleted': False,
                'deleted_at': None
            })
            
            logger.info("Restored settlement: %s", settlement_id)
            
        except Exception as exc:
            logger.error("Error restoring settlement: %s", str(exc))
            raise
    
    def get_active_settlements(
        self,
        group_id: str,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get active (non-deleted) settlements for a group
        
        Args:
            group_id: Group ID
            status: Optional status filter
            
        Returns:
            List of active settlement documents
        """
        try:
            filters = [
                ('group_id', '==', group_id),
                ('is_deleted', '==', False)
            ]
            if status:
                filters.append(('status', '==', status))
            
            settlements = self.query(
                filters=filters,
                order_by=('created_at', 'DESCENDING')
            )
            
            return settlements
            
        except Exception as exc:
            logger.error("Error getting active settlements: %s", str(exc))
            raise
