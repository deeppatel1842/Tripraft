"""
Repositories - Data Access Layer

Phase 5: Added cached repository support
Phase 6: Added denormalized repositories (GROUP_SUMMARIES, USER_EXPENSES)
Phase 12: Added expense history repository
"""

from .base import BaseRepository
from .cached_repository import (
    CachedRepositoryMixin,
    CacheAwareRepository,
    cached_method,
    invalidate_after,
    group_cache_key,
    user_cache_key,
    paginated_cache_key
)
from .balance_repository import BalanceRepository
from .group_repository import GroupRepository
from .expense_repository import ExpenseRepository
from .settlement_repository import SettlementRepository
from .invitation_repository import InvitationRepository
from .user_repository import UserRepository

# Phase 6: Denormalized repositories
from .group_summary_repository import GroupSummaryRepository
from .user_expense_repository import UserExpenseRepository

# Phase 12: Expense history repository
from .expense_history_repository import ExpenseHistoryRepository

# Phase 19.2: Email lookup repository
from .email_lookup_repository import EmailLookupRepository, normalize_email

# Phase 20: Bootstrap snapshot repository
from .snapshot_repository import SnapshotRepository

# Phase 20: User dashboard repository (extreme optimization)
from .dashboard_repository import DashboardRepository

__all__ = [
    'BaseRepository',
    'CachedRepositoryMixin',
    'CacheAwareRepository',
    'cached_method',
    'invalidate_after',
    'group_cache_key',
    'user_cache_key',
    'paginated_cache_key',
    'BalanceRepository',
    'GroupRepository',
    'ExpenseRepository',
    'SettlementRepository',
    'InvitationRepository',
    'UserRepository',
    # Phase 6: Denormalized
    'GroupSummaryRepository',
    'UserExpenseRepository',
    # Phase 12: History
    'ExpenseHistoryRepository',
    # Phase 19.2: Email lookup
    'EmailLookupRepository',
    'normalize_email',
    # Phase 20: Bootstrap snapshots
    'SnapshotRepository',
    # Phase 20: User dashboard (extreme optimization)
    'DashboardRepository',
]
