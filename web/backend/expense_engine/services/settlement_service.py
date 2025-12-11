"""
Settlement Service
Business logic for settlement management
"""

from typing import List, Dict, Optional
from decimal import Decimal
from firebase_admin import firestore
import logging

from ..repositories import SettlementRepository, GroupRepository, BalanceRepository
from ..services.balance_service import BalanceService
from ..models.settlement import Settlement
from ..config import business_rules
from ..exceptions import (
    ValidationError,
    ResourceNotFoundError
)

# Phase 13: Cache configuration
try:
    from ..utils.cache_manager import get_cache_manager
    from ..config import redis_config
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    def get_cache_manager():
        return None

# Phase 20: Import snapshot service for denormalized updates
try:
    from .snapshot_service import SnapshotService
    SNAPSHOT_ENABLED = True
except ImportError:
    SNAPSHOT_ENABLED = False
    SnapshotService = None

logger = logging.getLogger(__name__)


class SettlementService:
    """
    Service for settlement management operations
    Handles payment recording and balance updates
    """
    
    def __init__(
        self,
        settlement_repo: Optional[SettlementRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        balance_repo: Optional[BalanceRepository] = None
    ):
        """
        Initialize service
        
        Args:
            settlement_repo: Settlement repository instance (optional)
            group_repo: Group repository instance (optional)
            balance_repo: Balance repository instance (optional)
        """
        # pylint: disable=no-value-for-parameter
        self.settlement_repo = settlement_repo or SettlementRepository()
        self.group_repo = group_repo or GroupRepository()
        self.balance_repo = balance_repo or BalanceRepository()
        self.balance_service = BalanceService(balance_repo, None)
        
        # Phase 20: Lazy-load snapshot service to avoid Firebase in tests
        self._snapshot_service = None
    
    @property
    def snapshot_service(self) -> Optional[SnapshotService]:
        """Lazy-load snapshot service for denormalized updates"""
        if SNAPSHOT_ENABLED and self._snapshot_service is None:
            self._snapshot_service = SnapshotService()
        return self._snapshot_service
    
    def _invalidate_settlement_cache(self, group_id: str, receiver_id: str = None) -> None:
        """
        Invalidate settlement cache entries when settlements change
        Phase 13: New method for cache invalidation
        Phase 17.9: Only invalidate RECEIVER's mega-bootstrap (they need to see balance update)
        
        Args:
            group_id: Group ID
            receiver_id: User ID of settlement receiver (the one being paid)
        """
        if not CACHE_ENABLED:
            return
        try:
            cache = get_cache_manager()
            if cache and cache.is_available():
                # Invalidate group settlements cache
                cache.delete(redis_config.KEY_GROUP_SETTLEMENTS.format(gid=group_id))
                # Invalidate group balances cache (settlement updates balances)
                cache.delete(redis_config.KEY_GROUP_BALANCES.format(gid=group_id))
                # Also invalidate group summary since balances change
                cache.delete(redis_config.KEY_GROUP_SUMMARY.format(gid=group_id))
                
                # Phase 17.9: Only invalidate RECEIVER's mega-bootstrap
                # - Payer (from_user): Has optimistic update from frontend mutation
                # - Receiver (to_user): Needs cache invalidation to see updated balance
                # - Other members: Get updates via Firestore balance listener
                if receiver_id:
                    cache.delete(f"expense:mega_bootstrap:{receiver_id}")  # Dashboard
                    cache.delete(f"expense:mega_bootstrap:{receiver_id}:{group_id}")  # Group view
                    logger.info("Mega-bootstrap invalidated for receiver %s", receiver_id)
                
                logger.info("Settlement cache invalidated: group=%s, receiver=%s", group_id, receiver_id)
        except Exception as e:
            logger.warning("Failed to invalidate settlement cache: %s", e)
    
    def create_settlement(
        self,
        group_id: str,
        payer_id: str,
        receiver_id: str,
        amount: Decimal,
        created_by: str,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Create a new settlement
        
        Args:
            group_id: Group ID
            payer_id: User ID who is paying
            receiver_id: User ID who is receiving
            amount: Settlement amount
            created_by: User ID who created
            payment_method: Payment method (cash/bank_transfer/etc)
            notes: Optional notes
            
        Returns:
            Created settlement document
        """
        try:
            # Validate group exists
            group_data = self.group_repo.get_by_id(group_id)
            if not group_data:
                raise ResourceNotFoundError(f"Group {group_id} not found")
            
            # Validate users are group members using the member collection
            payer_member = self.group_repo.get_member(group_id, payer_id)
            if not payer_member:
                raise ValidationError(f"Payer {payer_id} is not a group member")
            
            receiver_member = self.group_repo.get_member(group_id, receiver_id)
            if not receiver_member:
                raise ValidationError(f"Receiver {receiver_id} is not a group member")
            
            # Validate amount
            if amount <= 0:
                raise ValidationError("Settlement amount must be positive")
            
            if amount > Decimal(str(business_rules.MAX_EXPENSE_AMOUNT)):
                raise ValidationError(
                    f"Settlement amount exceeds maximum: {business_rules.MAX_EXPENSE_AMOUNT}"
                )
            
            # Create settlement model
            # Use correct field names matching Settlement model
            settlement = Settlement(
                group_id=group_id,
                from_user_id=payer_id,
                to_user_id=receiver_id,
                amount=amount,
                method=payment_method or 'cash',
                notes=notes,
                recorded_by=created_by
            )
            
            # Create settlement and update balances in transaction
            # IMPORTANT: In Firestore transactions, ALL reads must come BEFORE any writes
            db = self.settlement_repo.db
            transaction = db.transaction()
            
            @firestore.transactional  # pylint: disable=no-member
            def create_with_balance_update(trans):
                # Generate document ID for settlement
                doc_ref = self.settlement_repo.get_collection().document()
                settlement_id = doc_ref.id
                settlement.settlement_id = settlement_id
                
                # STEP 1: READ balance document first (before any writes)
                balance_doc_ref = self.balance_service.balance_repo.get_collection().document(group_id)
                balance_doc = balance_doc_ref.get(transaction=trans)
                
                if balance_doc.exists:
                    current_data = balance_doc.to_dict()
                    current_balances = current_data.get('balances', {})
                else:
                    current_balances = {}
                
                # Calculate new balances
                from decimal import Decimal
                from ..config import business_rules
                from google.cloud.firestore_v1 import SERVER_TIMESTAMP, Increment
                
                new_balances = dict(current_balances)
                # from_user (payer) pays, so their balance increases (they owe less)
                current_payer = Decimal(str(new_balances.get(payer_id, 0)))
                new_balances[payer_id] = float(round(current_payer + amount, business_rules.BALANCE_PRECISION))
                # to_user (receiver) gets paid, so their balance decreases (they are owed less)
                current_receiver = Decimal(str(new_balances.get(receiver_id, 0)))
                new_balances[receiver_id] = float(round(current_receiver - amount, business_rules.BALANCE_PRECISION))
                
                # STEP 2: Write settlement document
                trans.set(doc_ref, settlement.to_dict())
                
                # STEP 3: Write balance update
                balance_update = {
                    'group_id': group_id,
                    'balances': new_balances,
                    'last_updated': SERVER_TIMESTAMP,
                    'version': Increment(1)
                }
                trans.set(balance_doc_ref, balance_update, merge=True)
                
                # Phase 19.5: Return both settlement_id AND new_balances to avoid re-read
                return settlement_id, new_balances
            
            settlement_id, computed_balances = create_with_balance_update(transaction)
            
            # Phase 13: Invalidate settlement cache
            # Phase 17.9: Pass receiver_id so their cache gets invalidated
            self._invalidate_settlement_cache(group_id, receiver_id)
            
            # Phase 20: Trigger snapshot update for settlement
            # Phase 19.5: Use computed_balances from transaction (no re-read!)
            if self.snapshot_service:
                try:
                    self.snapshot_service.on_settlement_created(
                        group_id=group_id,
                        new_balances=computed_balances
                    )
                except Exception as snap_exc:
                    logger.warning("Settlement snapshot update failed: %s", snap_exc)
            
            logger.info(
                "Created settlement %s from %s to %s in group %s",
                settlement_id, payer_id, receiver_id, group_id
            )
            
            # Phase 19.5: Build settlement response from model data (no re-read!)
            settlement_response = settlement.to_dict()
            settlement_response['settlement_id'] = settlement_id
            settlement_response['id'] = settlement_id
            return settlement_response
            
        except Exception as exc:
            logger.error("Error creating settlement: %s", str(exc))
            raise
    
    def get_settlement(self, settlement_id: str) -> Optional[Dict]:
        """
        Get settlement by ID
        
        Args:
            settlement_id: Settlement ID
            
        Returns:
            Settlement document or None
        """
        return self.settlement_repo.get_by_id(settlement_id)
    
    def get_group_settlements(
        self,
        group_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get settlements for a group, enriched with user display names
        Phase 13: Added Redis caching (TTL=60s)
        
        Args:
            group_id: Group ID
            status: Optional status filter
            limit: Maximum settlements to return
            
        Returns:
            List of settlement documents with from_display_name and to_display_name
        """
        # Only cache when no status filter and default limit (most common case)
        cache_key = None
        if CACHE_ENABLED and status is None and limit == 50:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache_key = redis_config.KEY_GROUP_SETTLEMENTS.format(gid=group_id)
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug("[CACHE][+] Group settlements cache hit: %s", group_id)
                    return cached
        
        # Fetch from Firestore
        settlements = self.settlement_repo.get_group_settlements(
            group_id,
            status=status,
            limit=limit
        )
        
        # Enrich settlements with user display names (Phase 15: use all members including removed)
        if settlements:
            # Get ALL members (active + removed) for proper display name resolution
            from .group_service import GroupService
            group_service = GroupService()
            # Use get_all_members_for_history to include removed members with cached names
            member_map = group_service.get_all_members_for_history(group_id)
            
            # Add display names to settlements
            for settlement in settlements:
                from_user = settlement.get('from_user_id')
                to_user = settlement.get('to_user_id')
                from_member = member_map.get(from_user, {})
                to_member = member_map.get(to_user, {})
                settlement['from_display_name'] = from_member.get('display_name', 'Unknown')
                settlement['to_display_name'] = to_member.get('display_name', 'Unknown')
                # Add indicator if user was removed (for UI styling if needed)
                settlement['from_user_removed'] = not from_member.get('is_active', True)
                settlement['to_user_removed'] = not to_member.get('is_active', True)
        
        # Cache result if no filters
        if cache_key:
            cache = get_cache_manager()
            if cache and cache.is_available():
                cache.set(cache_key, settlements, ttl=redis_config.TTL_GROUP_SETTLEMENTS)
                logger.debug("[CACHE][-] Group settlements cached: %s", group_id)
        
        return settlements
    
    def get_user_settlements(
        self,
        user_id: str,
        group_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get settlements involving a user
        
        Args:
            user_id: User ID
            group_id: Optional group filter
            
        Returns:
            List of settlement documents
        """
        return self.settlement_repo.get_user_settlements(
            user_id,
            group_id=group_id
        )
    
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
            uploaded_by: User ID who uploaded
            notes: Optional notes
        """
        try:
            # Validate settlement exists
            settlement_data = self.settlement_repo.get_by_id(settlement_id)
            if not settlement_data:
                raise ResourceNotFoundError(f"Settlement {settlement_id} not found")
            
            # Validate proof type
            valid_types = ['screenshot', 'receipt', 'transaction_id']
            if proof_type not in valid_types:
                raise ValidationError(
                    f"Invalid proof type. Must be one of: {', '.join(valid_types)}"
                )
            
            # Add proof
            self.settlement_repo.add_payment_proof(
                settlement_id,
                proof_type,
                proof_url,
                uploaded_by,
                notes
            )
            
            logger.info(
                "Added payment proof to settlement %s by %s",
                settlement_id, uploaded_by
            )
            
        except Exception as exc:
            logger.error("Error adding payment proof: %s", str(exc))
            raise
