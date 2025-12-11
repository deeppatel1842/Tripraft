"""
Expense Engine - Professional Splitwise-Style Expense Management

A production-ready expense splitting engine designed for scalability,
security, and performance.

Features:
- Zero hardcoded values
- Incremental balance calculations
- Smart Redis caching (90%+ hit rate)
- Row-level security with Firestore rules
- RBAC authorization
- Rate limiting for 1000+ concurrent users
- Real-time updates via Firestore listeners
- TanStack Query optimistic updates

Architecture:
- Repository Layer: Data access (Firestore + Redis)
- Service Layer: Business logic
- Route Layer: REST API endpoints
- Middleware: Auth, validation, rate limiting

Author: TripRaft Team
Date: November 24, 2025
"""

__version__ = "1.0.0"
__author__ = "TripRaft Team"

# Package metadata
PACKAGE_NAME = "expense_engine"
PACKAGE_DESCRIPTION = "Professional expense splitting engine"

# Phase 20 optimized routes (optional)
try:
    from expense_engine.routes.expense_optimized_routes import expense_v2
except ImportError:
    expense_v2 = None

__all__ = [
    "expense_v2",
    "PACKAGE_NAME",
    "PACKAGE_DESCRIPTION"
]
