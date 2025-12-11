"""
Expense Engine Routes
API endpoints for expense management

Phase 6: Complete REST API
- Group management (CRUD, members)
- Expense management (CRUD, pagination)
- Settlement tracking
- Invitation workflow
- User statistics and balances
- Performance monitoring (Phase 5)

Phase 7: Bootstrap & Dashboard Optimization
- Single endpoint for initial dashboard data
- Parallel data fetching
- Cache analytics

Phase 21: Extreme Optimization (10 operations target)
- Zero-read mutations
- Single-document dashboard pattern
- Write-through cache
"""

from .group_routes import group_bp
from .expense_routes import expense_bp
from .expense_flat_routes import expense_flat_bp
from .settlement_routes import settlement_bp
from .settlement_standalone_routes import settlement_standalone_bp
from .invitation_routes import invitation_bp
from .user_routes import user_bp
from .performance_routes import performance_bp
from .bootstrap_routes import bootstrap_bp
from .extreme_routes import extreme_bp

__all__ = [
    'group_bp',
    'expense_bp',
    'expense_flat_bp',
    'settlement_bp',
    'settlement_standalone_bp',
    'invitation_bp',
    'user_bp',
    'performance_bp',
    'bootstrap_bp',
    'expense_v2',
    'extreme_bp',
]

# Phase 20 optimized routes
try:
    from .expense_optimized_routes import expense_v2
except ImportError:
    expense_v2 = None
