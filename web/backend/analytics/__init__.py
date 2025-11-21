"""
Initialize Analytics Package
"""

from .analytics_engine import (
    AnalyticsEngine,
    EventType,
    UserTier,
    AnalyticsEvent,
    UserMetrics,
    BusinessMetrics,
    get_analytics_summary
)

from .plan_manager import (
    PlanManager,
    PlanTier,
    PlanLimits,
    FREE_PLAN,
    PAID_PLAN,
    check_and_track_expense_creation
)

from .settlement_archiver import (
    SettlementArchiver,
    SettlementSummary,
    generate_and_send_monthly_report
)

__all__ = [
    # Analytics Engine
    'AnalyticsEngine',
    'EventType',
    'UserTier',
    'AnalyticsEvent',
    'UserMetrics',
    'BusinessMetrics',
    'get_analytics_summary',
    
    # Plan Manager
    'PlanManager',
    'PlanTier',
    'PlanLimits',
    'FREE_PLAN',
    'PAID_PLAN',
    'check_and_track_expense_creation',
    
    # Settlement Archiver
    'SettlementArchiver',
    'SettlementSummary',
    'generate_and_send_monthly_report',
]

__version__ = '1.0.0'
__author__ = 'Production Team'
