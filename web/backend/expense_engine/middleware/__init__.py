"""Middleware (auth, validation, rate limiting, audit, logging)"""

from .auth import (
    require_auth,
    optional_auth,
    require_group_member,
    get_current_user,
    get_current_user_id
)

from .rbac import (
    require_permission,
    require_role,
    require_owner,
    require_admin,
    require_group_member as rbac_require_group_member,
    require_expense_owner_or_admin,
    can_edit_expense,
    can_delete_expense
)

from .rate_limiter import (
    RateLimiter,
    init_limiter,
    get_rate_limiter,
    rate_limit,
    rate_limit_read,
    rate_limit_write
)

from .audit import (
    AuditLogger,
    get_audit_logger,
    audit_action,
    set_audit_before_data,
    set_audit_after_data
)

from .request_logger import (
    init_request_logging,
    log_operation_summary
)

__all__ = [
    # Auth
    'require_auth',
    'optional_auth',
    'require_group_member',
    'get_current_user',
    'get_current_user_id',
    
    # RBAC
    'require_permission',
    'require_role',
    'require_owner',
    'require_admin',
    'require_expense_owner_or_admin',
    'can_edit_expense',
    'can_delete_expense',
    
    # Rate Limiting
    'RateLimiter',
    'init_limiter',
    'get_rate_limiter',
    'rate_limit',
    'rate_limit_read',
    'rate_limit_write',
    
    # Audit
    'AuditLogger',
    'get_audit_logger',
    'audit_action',
    'set_audit_before_data',
    'set_audit_after_data',
    
    # Request Logging (Phase 6)
    'init_request_logging',
    'log_operation_summary',
]
