"""Group Planner Routes Package - Phase 20 Optimized"""

try:
    from Group_planner.routes.optimized_routes import group_planner_v2
except ImportError:
    group_planner_v2 = None

__all__ = ['group_planner_v2']
