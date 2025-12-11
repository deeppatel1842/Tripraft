"""
Group Planner Module - Phase 1 + Phase 20 Optimization
Authentication verification and group operations
"""

from .routes import group_planner_bp

# Phase 20 optimized routes (optional)
try:
    from .routes.optimized_routes import group_planner_v2
except ImportError:
    group_planner_v2 = None

__version__ = "2.0.0"
__all__ = [
    "group_planner_bp",
    "group_planner_v2",
]
