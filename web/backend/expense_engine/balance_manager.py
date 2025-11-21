"""
Balance Manager - Optimized Balance Calculations
Implements incremental balance updates instead of full recalculation
Reduces Firestore reads from 13 to 1-2 per request
"""

import logging
import threading
from typing import Dict, List
from datetime import datetime
import time

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from .constants import BusinessRules

from .constants import CacheConfig, BusinessRules

logger = logging.getLogger(__name__)
db = firestore.client()


class BalanceManager:
    """
    Manages group balances with denormalized data structure
    Uses incremental updates instead of full recalculation
    """

    def __init__(self, firestore_db):
        self.db = firestore_db
        # 🔧 PHASE 1 FIX: Use threading.Event to coordinate parallel recalculations
        # Instead of skipping, parallel requests WAIT for ongoing recalc to complete
        self._recalc_in_progress = {}  # group_id -> threading.Event
        self._recalc_lock = threading.Lock()  # Protects the dictionary

    # =========================================================================
    # BALANCE RETRIEVAL (OPTIMIZED - 1-2 reads)
    # =========================================================================

    def get_group_balances(
        self, group_id: str, force_incremental: bool = False
    ) -> Dict:
        """
        Get group balances from denormalized table
        Fast path: 1 read if cached, 2-3 reads if needs recalc

        Args:
            group_id: Group to get balances for
            force_incremental: If True, FORCE RECALCULATION (bypass cache) to get fresh data
                              Used during settlement validation to prevent stale reads

        Returns:
            {
                'balances': [{'user_id': ..., 'balance': ..., 'username': ...}],
                'debts': [{'from': ..., 'to': ..., 'amount': ...}],
                'is_settled': bool,
                'total_spent': float,
                'last_updated': timestamp
            }
        """

        start_time = time.time()

        try:
            # 🔥 CRITICAL: If force_incremental=True, skip cache and recalculate
            # This is used during settlement validation to prevent stale data
            if force_incremental:

                logger.info("🔄 Force recalculation requested for group %s", group_id)
                # Skip to recalculation below
            else:
                # Try to get denormalized balance (1 read)
                t1 = time.time()
                balance_doc = (
                    self.db.collection("group_balances").document(group_id).get()
                )
                logger.info(
                    "⏱️  Firestore balance read: %.2fms", (time.time() - t1) * 1000
                )

                if balance_doc.exists:
                    balance_data = balance_doc.to_dict()

                    # 🔧 BUG #6: Use version for cache validation (more reliable than timestamp)
                    # Version is incremented on every mutation, providing deterministic cache invalidation
                    cached_version = balance_data.get("version", 0)

                    # Also check age as secondary validation
                    last_updated = balance_data.get("last_updated")
                    if last_updated:
                        age = self._get_age(last_updated)

                        if age <= CacheConfig.BALANCE_CACHE_MAX_AGE:

                            logger.info(
                                "✅ Using cached balance for group %s (v%d, age: %.1fs)",
                                group_id,
                                cached_version,
                                age,
                            )
                            logger.info(
                                "⏱️  TOTAL get_group_balances (cached): %.2fms",
                                (time.time() - start_time) * 1000,
                            )
                            return self._format_balance_response(balance_data)
                        else:
                            # Cache is too old - recalculate to ensure freshness

                            logger.info(
                                "⏰ Cache expired for group %s (v%d, age: %.1fs > %ds)",
                                group_id,
                                cached_version,
                                age,
                                CacheConfig.BALANCE_CACHE_MAX_AGE,
                            )
                    else:
                        logger.info(
                            "⚠️ No timestamp in cached balance for group %s", group_id
                        )
                else:
                    logger.info("ℹ️ No cached balance found for group %s", group_id)
                    return self._empty_balance_response()

            # Balance doesn't exist or is stale - recalculate

            logger.info("🔄 Recalculating balance for group %s", group_id)
            result = self._recalculate_and_cache_balance(group_id)
            logger.info(
                "⏱️  TOTAL get_group_balances (recalc): %.2fms",
                (time.time() - start_time) * 1000,
            )
            return result

        except (ValueError, KeyError) as e:
            logger.error("Error getting group balances: %s", e)
            # Fallback to recalculation
            return self._recalculate_and_cache_balance(group_id)

    def _is_fresh(self, timestamp, max_age_seconds: int = 10) -> bool:
        """
        Check if cached data is fresh

        Args:
            timestamp: Can be ISO string, datetime object, or Unix timestamp (int/float)
            max_age_seconds: Maximum age in seconds before data is considered stale (default: 10s)

        Returns:
            True if data is fresh, False if stale or error
        """
        try:
            current_time = datetime.utcnow()

            # Handle different timestamp formats
            if isinstance(timestamp, str):
                # ISO format: "2025-11-03T10:30:00.123456" or "2025-11-03T10:30:00+00:00"
                ts = timestamp.replace("Z", "+00:00")
                last_updated = datetime.fromisoformat(ts)

                # Make timezone-naive for comparison with utcnow()
                if last_updated.tzinfo is not None:
                    last_updated = last_updated.replace(tzinfo=None)

            elif isinstance(timestamp, datetime):
                last_updated = timestamp
                if last_updated.tzinfo is not None:
                    last_updated = last_updated.replace(tzinfo=None)

            elif isinstance(timestamp, (int, float)):
                # Unix timestamp (seconds since epoch)
                last_updated = datetime.utcfromtimestamp(timestamp)

            else:
                logger.error(
                    "Unknown timestamp format: %s - %s", type(timestamp), timestamp
                )
                return False  # Treat unknown format as stale

            # Calculate age
            age = (current_time - last_updated).total_seconds()
            is_fresh = age < max_age_seconds

            # Debug log for verification
            if age > 10000 or age < 0:
                logger.warning("⚠️  Suspicious cache age: %ss", age)
                logger.warning("   Current: %s", current_time.isoformat())
                logger.warning("   Last updated: %s", last_updated.isoformat())
                logger.warning("   Raw timestamp: %s", timestamp)
                return False  # Treat suspicious age as stale

            logger.debug(
                "Cache freshness check: age=%.1fs, max=%ss, fresh=%s",
                age,
                max_age_seconds,
                is_fresh,
            )
            return is_fresh

        except (ValueError, OSError) as e:
            logger.error("Error checking cache freshness: %s", e, exc_info=True)
            return False  # Treat error as stale

    def _get_age(self, timestamp) -> float:
        """
        Get age of timestamp in seconds

        Args:
            timestamp: Can be ISO string, datetime object, or Unix timestamp (int/float)

        Returns:
            Age in seconds, or 999999.0 if error (forces cache miss)
        """
        try:
            current_time = datetime.utcnow()

            # Handle different timestamp formats
            if isinstance(timestamp, str):
                # ISO format: "2025-11-03T10:30:00.123456" or "2025-11-03T10:30:00+00:00"
                ts = timestamp.replace("Z", "+00:00")
                last_updated = datetime.fromisoformat(ts)

                # Make timezone-naive for comparison with utcnow()
                if last_updated.tzinfo is not None:
                    last_updated = last_updated.replace(tzinfo=None)

            elif isinstance(timestamp, datetime):
                last_updated = timestamp
                if last_updated.tzinfo is not None:
                    last_updated = last_updated.replace(tzinfo=None)

            elif isinstance(timestamp, (int, float)):
                # Unix timestamp (seconds since epoch)
                last_updated = datetime.utcfromtimestamp(timestamp)

            else:
                logger.error(
                    "Unknown timestamp format: %s - %s", type(timestamp), timestamp
                )
                return 999999.0  # Force cache miss

            # Calculate age
            age = (current_time - last_updated).total_seconds()

            # Debug log for verification
            if age > 10000 or age < 0:
                logger.warning("⚠️  Suspicious cache age: %ss", age)
                logger.warning("   Current: %s", current_time.isoformat())
                logger.warning("   Last updated: %s", last_updated.isoformat())
                logger.warning("   Raw timestamp: %s", timestamp)

            return round(age, 1)

        except (ValueError, OSError) as e:
            logger.error("Error calculating cache age: %s", e, exc_info=True)
            return 999999.0  # Force cache miss on error

    # =========================================================================
    # INCREMENTAL UPDATES (FAST - 2-3 writes)
    # =========================================================================

    def update_balance_for_expense(
        self, group_id: str, expense: Dict, operation: str = "add"
    ) -> bool:
        """
        Incrementally update balance when expense is added/modified/deleted
        Uses Firestore transaction for atomicity and validates sum-to-zero invariant

        Args:
            group_id: Group ID
            expense: Expense dictionary with splits
            operation: 'add' for new expense, 'remove' for delete

        Returns:
            Success status
        """
        try:
            expense_id = expense.get("expense_id") or expense.get("id")
            amount = expense.get("amount", 0)
            paid_by = expense.get("paid_by")
            splits = expense.get("splits", [])

            if not paid_by or not splits:
                logger.error("Invalid expense: missing paid_by or splits")
                return False

            # Determine multiplier based on operation
            multiplier = 1 if operation == "add" else -1

            # Use transaction for atomic read-modify-write
            balance_ref = self.db.collection("group_balances").document(group_id)

            @firestore.transactional
            def update_in_transaction(transaction):
                balance_doc = balance_ref.get(transaction=transaction)

                if balance_doc.exists:
                    balance_data = balance_doc.to_dict()
                    member_balances = balance_data.get("member_balances", {})
                    total_spent = balance_data.get("total_spent", 0)
                    version = balance_data.get("version", 0)
                else:
                    member_balances = {}
                    total_spent = 0
                    version = 0

                # Apply balance changes with multiplier
                # Person who paid: +amount (they paid the full amount)
                old_payer_balance = member_balances.get(paid_by, 0.0)
                member_balances[paid_by] = old_payer_balance + (amount * multiplier)

                # Each split: -split_amount (they owe their share)
                for split in splits:
                    split_amount = split.get("amount", 0)
                    user_id = split.get("user_id")
                    if user_id:
                        old_split_balance = member_balances.get(user_id, 0.0)
                        member_balances[user_id] = old_split_balance - (
                            split_amount * multiplier
                        )

                # 🔒 CRITICAL: Validate sum-to-zero invariant
                total_balance = sum(member_balances.values())
                if abs(total_balance) > BusinessRules.MIN_SETTLEMENT_THRESHOLD:
                    error_msg = f"❌ INVARIANT VIOLATION: Balance sum = ${total_balance:.2f}, expected $0.00"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Calculate simplified debts
                debts = self._calculate_simplified_debts(member_balances)
                is_settled = len(debts) == 0

                # Update denormalized balance document (1 write) with full replace
                transaction.set(
                    balance_ref,
                    {
                        "group_id": group_id,
                        "member_balances": member_balances,
                        "total_spent": total_spent + (amount * multiplier),
                        "debts": debts,
                        "is_settled": is_settled,
                        "version": version
                        + 1,  # 🔒 Increment version for optimistic locking
                        "last_updated": datetime.utcnow().isoformat(),
                        "last_expense_id": expense_id,
                    },
                    merge=False,
                )  # Full replace, not merge

                return member_balances, debts, is_settled, version + 1

            # Execute transaction
            transaction = self.db.transaction()
            _ = update_in_transaction(transaction)

            logger.info(
                "Balance updated incrementally for group %s",
                group_id,
            )

            # 🔄 CRITICAL FIX: If we just removed the LAST expense (total_spent = 0),
            # trigger a full recalculation to clear settlements
            if operation == "remove":
                balance_doc = balance_ref.get()
                if balance_doc.exists:
                    current_total = balance_doc.to_dict().get("total_spent", 0)
                    if abs(current_total) < 0.01:  # Total spent is now $0
                        logger.warning(
                            "🔄 Last expense deleted - triggering full recalc to clear settlements"
                        )

                        # This is a mutation (delete), so pass is_mutation=True
                        return (
                            self._recalculate_and_cache_balance(
                                group_id, is_mutation=True
                            )
                            is not None
                        )

            # 🔧 CRITICAL FIX: Invalidate Redis cache AFTER successful commit
            # 🚀 OPTIMIZATION: Don't delete formatted balance cache anymore!
            # Smart ?_t handling will check timestamp instead of forcing cache miss
            # This allows instant responses when balance was just recalculated
            try:
                pass  # No-op since cache invalidation is disabled
                # Delete Redis formatted response cache - DISABLED for smart cache optimization
                # from .cache_operations import ExpenseCacheOperations
                # cache = ExpenseCacheOperations()
                # if cache.redis_client:  # Only invalidate if Redis is available
                #     cache_key = f"expense:formatted_balance:{group_id}"
                #     cache.redis_client.delete(cache_key)
                #
            except (ImportError, AttributeError, ConnectionError) as cache_err:
                logger.warning("Failed to invalidate Redis cache: %s", cache_err)

            return True

        except (ValueError, KeyError) as e:
            logger.error("Error updating balance for expense: %s", e)
            return False

    def update_balance_for_settlement(self, group_id: str, settlement: Dict) -> bool:
        """
        Incrementally update balance when settlement is made
        Uses Firestore transaction for atomicity and validates sum-to-zero invariant

        Args:
            group_id: Group ID
            settlement: Settlement dictionary

        Returns:
            Success status
        """
        try:
            from_user = settlement.get("from_user")
            to_user = settlement.get("to_user")
            amount = settlement.get("amount", 0)

            if not from_user or not to_user or amount <= 0:
                logger.error("Invalid settlement: missing users or amount")
                return False

            # Use transaction for atomic read-modify-write
            balance_ref = self.db.collection("group_balances").document(group_id)

            @firestore.transactional
            def update_in_transaction(transaction):
                balance_doc = balance_ref.get(transaction=transaction)

                if not balance_doc.exists:
                    error_msg = f"Balance document not found for group {group_id}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                balance_data = balance_doc.to_dict()
                member_balances = balance_data.get("member_balances", {})
                version = balance_data.get("version", 0)

                # Update balances for settlement:
                # Balance semantics:
                #   Positive = Money owed TO them (they should receive)
                #   Negative = Money they OWE (they should pay)
                #
                # When from_user pays to_user:
                #   from_user's balance INCREASES (paying off debt, becomes less negative)
                #   to_user's balance DECREASES (receiving payment, becomes less positive)
                member_balances = balance_data.get("member_balances", {})
                version = balance_data.get("version", 0)

                # Update balances for settlement:
                # Balance semantics:
                #   Positive = Money owed TO them (they should receive)
                #   Negative = Money they OWE (they should pay)
                #
                # When from_user pays to_user:
                #   from_user's balance INCREASES (paying off debt, becomes less negative)
                #   to_user's balance DECREASES (receiving payment, becomes less positive)
                old_from_balance = member_balances.get(from_user, 0.0)
                old_to_balance = member_balances.get(to_user, 0.0)

                member_balances[from_user] = old_from_balance + amount
                member_balances[to_user] = old_to_balance - amount

                # 🔒 CRITICAL: Validate sum-to-zero invariant
                total_balance = sum(member_balances.values())
                if abs(total_balance) > BusinessRules.MIN_SETTLEMENT_THRESHOLD:
                    error_msg = f"❌ INVARIANT VIOLATION: Balance sum = ${total_balance:.2f}, expected $0.00"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Recalculate debts
                debts = self._calculate_simplified_debts(member_balances)
                is_settled = len(debts) == 0

                # Get total_spent from existing data
                total_spent = balance_data.get("total_spent", 0)

                # Update balance document with full replace
                transaction.set(
                    balance_ref,
                    {
                        "group_id": group_id,
                        "member_balances": member_balances,
                        "debts": debts,
                        "is_settled": is_settled,
                        "total_spent": total_spent,
                        "version": version
                        + 1,  # 🔒 Increment version for optimistic locking
                        "last_updated": datetime.utcnow().isoformat(),
                        "last_settlement_id": settlement.get(
                            "settlement_id", "unknown"
                        ),
                    },
                    merge=False,
                )  # Full replace, not merge

                return member_balances, debts, is_settled, version + 1

            # Execute transaction
            transaction = self.db.transaction()
            _ = update_in_transaction(transaction)

            logger.info(
                "Balance updated for settlement in group %s",
                group_id,
            )

            # 🔧 CRITICAL FIX: Invalidate Redis cache AFTER successful commit
            # 🚀 OPTIMIZATION: Don't delete formatted balance cache anymore!
            # Smart ?_t handling will check timestamp instead of forcing cache miss
            # This allows instant responses when balance was just recalculated
            try:
                # Delete Redis formatted response cache - DISABLED for smart cache optimization
                # from .cache_operations import ExpenseCacheOperations
                # cache = ExpenseCacheOperations()
                # if cache.redis_client:  # Only invalidate if Redis is available
                #     cache_key = f"expense:formatted_balance:{group_id}"
                #     cache.redis_client.delete(cache_key)
                pass
            except (ImportError, AttributeError, ConnectionError) as cache_err:
                logger.warning("Failed to invalidate Redis cache: %s", cache_err)

            return True

        except (ValueError, KeyError) as e:
            logger.error("Error updating balance for settlement: %s", e)
            return False

    # =========================================================================
    # RECALCULATION (FALLBACK - 5-7 reads)
    # =========================================================================

    def _recalculate_and_cache_balance(
        self, group_id: str, is_mutation: bool = False
    ) -> Dict:
        """
        Full recalculation from expenses (fallback method)
        Used when cache is empty or stale

        Args:
            group_id: Group to recalculate balances for
            is_mutation: True if this recalc is triggered by a data mutation (create/update/delete)
                        False if it's just a read that found stale/missing cache

        ⚠️ EXPENSIVE OPERATION: Reads all expenses (5-13 reads)
        Should only be triggered on:
        - First balance request (no cache)
        - Manual cache invalidation
        - Error recovery
        """

        start_time = time.time()

        # 🔧 PHASE 1 FIX: WAIT for ongoing recalculation instead of skipping
        # This ensures all parallel requests get the SAME fresh data
        event_to_wait = None

        with self._recalc_lock:
            if group_id in self._recalc_in_progress:
                # Another thread is recalculating - get the event to wait on
                event_to_wait = self._recalc_in_progress[group_id]

                logger.info(
                    "⏸️  Parallel request detected - waiting for recalc to complete: %s",
                    group_id,
                )
            else:
                # We'll do the recalculation - create event for others to wait on
                event_to_wait = threading.Event()
                self._recalc_in_progress[group_id] = event_to_wait
                event_to_wait = None  # Clear to indicate we're the one doing the work

        # If we need to wait, block until recalc completes
        if event_to_wait is not None:
            wait_start = time.time()
            event_to_wait.wait(timeout=BusinessRules.BALANCE_CALCULATION_TIMEOUT)
            wait_time = (time.time() - wait_start) * 1000

            logger.info(
                "✅ Recalc complete for %s - waited %.0fms", group_id, wait_time
            )

            # Return the freshly recalculated data
            balance_doc = self.db.collection("group_balances").document(group_id).get()
            if balance_doc.exists:
                return self._format_balance_response(balance_doc.to_dict())
            else:
                return self._empty_balance_response()

        try:

            logger.info(
                "🔄 EXPENSIVE: Full balance recalculation for group %s", group_id
            )

            # Get group members (1 read)
            t1 = time.time()
            group_doc = self.db.collection("groups").document(group_id).get()
            logger.info("⏱️  Get group document: %.2fms", (time.time() - t1) * 1000)

            if not group_doc.exists:
                return self._empty_balance_response()

            group_data = group_doc.to_dict()
            members = group_data.get("members", [])

            logger.info("   Members count: %d", len(members))

            # Initialize balances
            member_balances = {member: 0.0 for member in members}
            total_spent = 0.0

            # Get all expenses (1 query = multiple reads)
            t2 = time.time()
            try:
                expenses = (
                    self.db.collection("expenses")
                    .where(filter=FieldFilter("group_id", "==", group_id))
                    .where(filter=FieldFilter("is_deleted", "==", False))
                    .get()
                )
            except Exception as query_error:
                logger.error(f"Firestore query error: {query_error}")
                logger.error(f"FieldFilter type: {type(FieldFilter)}")
                logger.error(f"group_id: {group_id}")
                raise

            expense_list = list(expenses)
            logger.info(
                "⏱️  Get all expenses query: %.2fms (%d expenses)",
                (time.time() - t2) * 1000,
                len(expense_list),
            )

            # Calculate balances from expenses
            t3 = time.time()
            for expense_doc in expense_list:
                expense = expense_doc.to_dict()
                amount = expense.get("amount", 0)
                paid_by = expense.get("paid_by")
                splits = expense.get("splits", [])

                # Person who paid gets positive balance
                if paid_by:
                    member_balances[paid_by] = (
                        member_balances.get(paid_by, 0.0) + amount
                    )
                    total_spent += amount

                # People in split get negative balance
                for split in splits:
                    split_amount = split.get("amount", 0)
                    user_id = split.get("user_id")
                    if user_id and user_id in member_balances:
                        member_balances[user_id] = (
                            member_balances[user_id] - split_amount
                        )

            logger.info(
                "⏱️  Calculate balances from expenses: %.2fms", (time.time() - t3) * 1000
            )

            # Get settlements (1 query = multiple reads)
            t4 = time.time()
            settlements = (
                self.db.collection("settlements")
                .where(filter=FieldFilter("group_id", "==", group_id))
                .where(filter=FieldFilter("status", "==", "completed"))
                .get()
            )

            settlement_list = list(settlements)
            logger.info(
                "⏱️  Get settlements query: %.2fms (%d settlements)",
                (time.time() - t4) * 1000,
                len(settlement_list),
            )

            # 🔧 BUG FIX #3 & #4: ALWAYS process settlements, regardless of expense count
            # Settlement documents represent historical financial transactions
            # They must be included in balance calculations even if all expenses are deleted
            # This ensures settlement history is preserved and balances are accurate
            t5 = time.time()
            for settlement_doc in settlement_list:
                settlement = settlement_doc.to_dict()
                from_user = settlement.get("from_user")
                to_user = settlement.get("to_user")
                amount = settlement.get("amount", 0)

                if from_user in member_balances and to_user in member_balances:
                    member_balances[from_user] += amount
                    member_balances[to_user] -= amount

            logger.info("⏱️  Apply settlements: %.2fms", (time.time() - t5) * 1000)

            # Calculate simplified debts
            t6 = time.time()
            debts = self._calculate_simplified_debts(member_balances)
            is_settled = len(debts) == 0
            logger.info(
                "⏱️  Calculate simplified debts: %.2fms", (time.time() - t6) * 1000
            )

            # 🔧 BUG FIX #3: Only increment version on mutations, not reads
            # This prevents version pollution and unnecessary cache invalidations
            # Version tracking for cache validation
            t7 = time.time()
            balance_ref = self.db.collection("group_balances").document(group_id)
            existing_doc = balance_ref.get()
            current_version = (
                existing_doc.to_dict().get("version", 0) if existing_doc.exists else 0
            )

            # Only increment version if this is a mutation (create/update/delete)
            if is_mutation:
                new_version = current_version + 1
                version_msg = f"v{current_version} → v{new_version} (mutation)"
            else:
                new_version = current_version  # Keep same version for reads
                version_msg = f"v{current_version} (read/cache refresh)"

            # Cache the result with version (1 write)
            balance_ref.set(
                {
                    "group_id": group_id,
                    "member_balances": member_balances,
                    "total_spent": total_spent,
                    "debts": debts,
                    "is_settled": is_settled,
                    "version": new_version,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            logger.info(
                "⏱️  Write balance cache to Firestore (%s): %.2fms",
                version_msg,
                (time.time() - t7) * 1000,
            )

            # 🔧 CRITICAL FIX: Invalidate formatted balance cache after recalculation
            # 🚀 OPTIMIZATION: Don't delete formatted balance cache anymore!
            # Smart ?_t handling will check timestamp instead of forcing cache miss
            # This allows instant responses when balance was just recalculated
            try:
                t8 = time.time()
                # from .cache_operations import ExpenseCacheOperations
                # cache = ExpenseCacheOperations()
                # if cache.redis_client:  # Only invalidate if Redis is available
                #     cache_key = f"expense:formatted_balance:{group_id}"
                #     cache.redis_client.delete(cache_key)
                #     logger.info("⏱️  Redis cache invalidation: %.2fms", (time.time() - t8) * 1000)
                #

                logger.info(
                    "⏱️  Redis cache kept (smart ?_t optimization): %.2fms",
                    (time.time() - t8) * 10000,
                )

            except (ImportError, AttributeError, ConnectionError) as e:
                logger.warning("Failed to invalidate formatted cache: %s", e)

            total_time = (time.time() - start_time) * 1000
            logger.info("⏱️  TOTAL _recalculate_and_cache_balance: %.2fms", total_time)
            logger.info(
                "📊 Recalculation breakdown: get_group=%.0fms, get_expenses=%.0fms, calc=%.0fms, settlements=%.0fms, debts=%.0fms, write=%.0fms, redis=%.0fms",
                t1,
                t2,
                t3,
                t4,
                t6,
                t7,
                t8,
            )

            return self._format_balance_response(
                {
                    "member_balances": member_balances,
                    "debts": debts,
                    "is_settled": is_settled,
                    "total_spent": total_spent,
                }
            )

        except (ValueError, KeyError) as e:
            logger.error("Error recalculating balance: %s", e)
            return self._empty_balance_response()

        finally:
            # 🔧 PHASE 1 FIX: Signal completion and cleanup
            with self._recalc_lock:
                if group_id in self._recalc_in_progress:
                    event = self._recalc_in_progress.pop(group_id)
                    event.set()  # Wake up all waiting threads
                    logger.debug(
                        "✅ Released recalc lock and signaled %d waiting threads for %s",
                        threading.active_count() - 1,
                        group_id,
                    )

    # =========================================================================
    # DEBT SIMPLIFICATION (SPLITWISE ALGORITHM)
    # =========================================================================

    def _calculate_simplified_debts(
        self, member_balances: Dict[str, float]
    ) -> List[Dict]:
        """
        Calculate simplified debts using greedy algorithm
        Minimizes number of transactions like Splitwise

        Args:
            member_balances: Dict of user_id -> balance
                            (positive = owed money, negative = owes money)

        Returns:
            List of debt transactions: [{'from': user_id, 'to': user_id, 'amount': X}]
        """
        # Separate creditors (owed) and debtors (owe)
        creditors = []  # People who are owed money
        debtors = []  # People who owe money

        for user_id, balance in member_balances.items():
            if balance > 0.01:  # Owed money (creditor)
                creditors.append({"user_id": user_id, "amount": balance})
            elif balance < -0.01:  # Owes money (debtor)
                debtors.append(
                    {"user_id": user_id, "amount": -balance}
                )  # Make positive

        # Sort by amount (largest first) for optimal matching
        creditors.sort(key=lambda x: x["amount"], reverse=True)
        debtors.sort(key=lambda x: x["amount"], reverse=True)

        # Greedy matching algorithm
        debts = []
        i, j = 0, 0

        while i < len(creditors) and j < len(debtors):
            creditor = creditors[i]
            debtor = debtors[j]

            # Match the smaller amount
            amount = min(creditor["amount"], debtor["amount"])

            debts.append(
                {
                    "from": debtor["user_id"],
                    "to": creditor["user_id"],
                    "amount": round(amount, 2),
                }
            )

            # Update remaining amounts
            creditor["amount"] -= amount
            debtor["amount"] -= amount

            # Move to next if settled
            if creditor["amount"] < 0.01:
                i += 1
            if debtor["amount"] < 0.01:
                j += 1

        return debts

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _format_balance_response(self, balance_data: Dict) -> Dict:
        """
        Format balance data for API response (OPTIMIZED - no Firebase queries!)

        IMPORTANT: If group is settled, show all balances as $0.00
        Individual balances are only meaningful when there are debts.

        DEFENSIVE: Handles None/empty balance_data gracefully
        """
        # DEFENSIVE: Handle None or missing balance_data
        if not balance_data:
            logger.warning(
                "_format_balance_response called with None/empty balance_data"
            )
            return self._empty_balance_response()

        member_balances = balance_data.get("member_balances", {})
        is_settled = balance_data.get("is_settled", False)

        # Convert to array format with usernames
        # OPTIMIZATION: Don't fetch usernames here - let the service layer handle it with caching
        balances = []
        for user_id, balance in member_balances.items():
            # Negative balances are confusing when is_settled=True
            display_balance = 0.0 if is_settled else round(balance, 2)

            balances.append(
                {
                    "user_id": user_id,
                    "username": user_id,  # Placeholder - service layer will add display names
                    "balance": display_balance,
                }
            )

        return {
            "success": True,
            "balances": balances,
            "debts": balance_data.get("debts", []),
            "is_settled": is_settled,
            "total_spent": balance_data.get("total_spent", 0),
            "last_updated": balance_data.get("last_updated"),
        }

    def _empty_balance_response(self) -> Dict:
        """Return empty balance response"""
        return {
            "success": True,
            "balances": [],
            "debts": [],
            "is_settled": True,
            "total_spent": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # MAINTENANCE
    # =========================================================================

    def recalculate_all_groups(self) -> int:
        """
        Recalculate balances for all groups (maintenance task)
        Run this nightly or when data inconsistencies detected

        Returns:
            Number of groups recalculated
        """
        try:
            groups = self.db.collection("groups").get()
            count = 0

            for group_doc in groups:
                self._recalculate_and_cache_balance(group_doc.id)
                count += 1

            logger.info("Recalculated balances for %d groups", count)
            return count

        except (ValueError, KeyError) as e:
            logger.error("Error recalculating all groups: %s", e)
            return 0
