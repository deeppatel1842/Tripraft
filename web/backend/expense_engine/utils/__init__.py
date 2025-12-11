"""
Utility functions for expense_engine

Phase 5: Performance Optimization modules
Phase 6: Enhanced Observability
"""

from .cache_manager import (
    CacheManager,
    CacheConfig,
    CacheStats,
    get_cache_manager,
    invalidate_cache_for_expense_change,
    generate_cache_key
)

from .cache_decorator import (
    cached,
    cached_property,
    cache_aside,
    CachedRepository,
    invalidate_on_write,
    warm_cache,
    batch_warm_cache
)

from .query_optimizer import (
    QueryResult,
    QueryBuilder,
    QueryCache,
    BatchQueryExecutor,
    OptimizedRepository,
    optimize_filters,
    estimate_query_cost,
    get_query_cache,
    invalidate_query_cache_for_collection
)

from .cache_warmer import (
    CacheWarmer,
    CacheWarmerTask,
    get_cache_warmer,
    initialize_cache_warming,
    warm_cache_for_user,
    warm_cache_for_group,
    init_flask_cache_warming,
    warm_on_access
)

from .operation_logger import (
    Colors,
    OperationType,
    OperationRecord,
    RequestOperationTracker,
    init_request_tracker,
    get_request_tracker,
    finalize_request_tracker,
    log_firestore_read,
    log_firestore_write,
    log_firestore_delete,
    log_firestore_query,
    log_cache_hit,
    log_cache_miss,
    log_cache_set,
    log_cache_delete,
    track_firestore_operation,
    track_cache_operation
)

from .denormalized_cache import (
    DenormalizedCacheConfig,
    DenormalizedCacheLayer,
    get_denormalized_cache,
    invalidate_on_expense_change
)

from .thread_safety import (
    LockType,
    LockStats,
    GroupLockManager,
    get_group_lock_manager,
    with_group_lock,
    OptimisticLockError,
    OptimisticLockManager,
    RetryConfig,
    with_retry
)

from .thread_safe_balance import (
    ThreadSafeBalanceManager,
    get_thread_safe_balance_manager
)

from .batch_operations import (
    parallel_read,
    batch_get_all,
    batch_get_all_as_dicts,
    BatchWriter,
    create_expense_with_batch,
    update_expense_with_batch,
    delete_expense_with_batch,
    create_settlement_with_batch
)

from .request_cache import (
    RequestDocumentCache,
    get_request_cache,
    cache_document_read,
    cache_query_result,
    invalidate_cached_document,
    update_cached_document,
    log_request_cache_stats
)

from .history_helpers import (
    HistoryEnricher,
    create_history_entry_with_return,
    format_balances_for_response
)

from .serialization import (
    to_firestore_value,
    serialize_balances,
    serialize_expense_for_snapshot,
    serialize_document
)

# Phase 20.1: Invitation tokens (JWT-like signed tokens)
from .invitation_token import (
    create_invitation_token,
    decode_invitation_token,
    is_token_valid,
    InvitationTokenError,
    TokenExpiredError,
    TokenInvalidError
)

# Phase 20.4: Write-through cache manager
from .write_through_cache import (
    WriteThroughCacheManager,
    get_write_through_cache,
    write_through_expense,
    write_through_balances,
    write_through_dashboard,
    write_through_snapshot
)

__all__ = [
    # Cache Manager
    'CacheManager',
    'CacheConfig',
    'CacheStats',
    'get_cache_manager',
    'invalidate_cache_for_expense_change',
    'generate_cache_key',
    
    # Cache Decorator
    'cached',
    'cached_property',
    'cache_aside',
    'CachedRepository',
    'invalidate_on_write',
    'warm_cache',
    'batch_warm_cache',
    
    # Query Optimizer
    'QueryResult',
    'QueryBuilder',
    'QueryCache',
    'BatchQueryExecutor',
    'OptimizedRepository',
    'optimize_filters',
    'estimate_query_cost',
    'get_query_cache',
    'invalidate_query_cache_for_collection',
    
    # Cache Warmer
    'CacheWarmer',
    'CacheWarmerTask',
    'get_cache_warmer',
    'initialize_cache_warming',
    'warm_cache_for_user',
    'warm_cache_for_group',
    'init_flask_cache_warming',
    'warm_on_access',
    
    # Operation Logger (Phase 6)
    'Colors',
    'OperationType',
    'OperationRecord',
    'RequestOperationTracker',
    'init_request_tracker',
    'get_request_tracker',
    'finalize_request_tracker',
    'log_firestore_read',
    'log_firestore_write',
    'log_firestore_delete',
    'log_firestore_query',
    'log_cache_hit',
    'log_cache_miss',
    'log_cache_set',
    'log_cache_delete',
    'track_firestore_operation',
    'track_cache_operation',
    
    # Denormalized Cache (Phase 6)
    'DenormalizedCacheConfig',
    'DenormalizedCacheLayer',
    'get_denormalized_cache',
    'invalidate_on_expense_change',
    
    # Thread Safety (Phase 10)
    'LockType',
    'LockStats',
    'GroupLockManager',
    'get_group_lock_manager',
    'with_group_lock',
    'OptimisticLockError',
    'OptimisticLockManager',
    'RetryConfig',
    'with_retry',
    
    # Thread-Safe Balance Manager (Phase 10)
    'ThreadSafeBalanceManager',
    'get_thread_safe_balance_manager',
    
    # Batch Operations (Phase 14)
    'parallel_read',
    'batch_get_all',
    'batch_get_all_as_dicts',
    'BatchWriter',
    'create_expense_with_batch',
    'update_expense_with_batch',
    'delete_expense_with_batch',
    'create_settlement_with_batch',
    
    # Request Cache (Phase 17)
    'RequestDocumentCache',
    'get_request_cache',
    'cache_document_read',
    'cache_query_result',
    'invalidate_cached_document',
    'update_cached_document',
    'log_request_cache_stats',
    
    # History Helpers (Phase 17)
    'HistoryEnricher',
    'create_history_entry_with_return',
    'format_balances_for_response',
    
    # Serialization (Phase 20)
    'to_firestore_value',
    'serialize_balances',
    'serialize_expense_for_snapshot',
    'serialize_document',
    
    # Invitation Tokens (Phase 20.1)
    'create_invitation_token',
    'decode_invitation_token',
    'is_token_valid',
    'InvitationTokenError',
    'TokenExpiredError',
    'TokenInvalidError',
    
    # Write-Through Cache (Phase 20.4)
    'WriteThroughCacheManager',
    'get_write_through_cache',
    'write_through_expense',
    'write_through_balances',
    'write_through_dashboard',
    'write_through_snapshot'
]
