"""
Routes Package - Modular API Endpoints
Professional route organization for scalability (1000+ concurrent users)

This package splits the monolithic 2423-line routes.py into 6 focused modules:
- user_routes: User profile management (4 endpoints)
- group_routes: Group CRUD and members (9 endpoints)
- invitation_routes: Invitation system (6 endpoints)
- expense_routes: Expense management (7 endpoints)
- settlement_routes: Payments and balances (5 endpoints)
- admin_routes: Health, cache, metrics (9 endpoints)

Total: 40 production-ready endpoints with comprehensive documentation
"""

from flask import Blueprint

# Import all individual blueprints
from .user_routes import user_bp
from .group_routes import group_bp
from .invitation_routes import invitation_bp
from .expense_routes import expense_bp as expense_routes_bp
from .settlement_routes import settlement_bp
from .admin_routes import admin_bp


# Create combined blueprint for backward compatibility
# This merges all routes under a single 'expense' blueprint
expense_bp = Blueprint('expense', __name__, url_prefix='/api/expense')


def _combine_blueprints():
    """
    Combine all modular blueprints into single expense_bp for backward compatibility
    
    This allows existing code that imports 'expense_bp' to continue working
    without changes while maintaining modular code structure internally.
    """
    # Import view functions from each module and register with combined blueprint
    from .user_routes import create_user_profile, get_user_profile, update_user_profile, search_users
    from .group_routes import (
        create_group, get_user_groups, get_group, get_group_full, update_group, 
        delete_group, get_group_members, get_member_details, leave_group, remove_group_member
    )
    from .invitation_routes import (
        create_invitation, get_user_invitations, get_group_invitations, 
        get_invitation_details, accept_invitation, reject_invitation
    )
    from .expense_routes import (
        create_expense, get_expense, update_expense, delete_expense,
        get_personal_expenses, get_group_expenses, get_user_all_expenses
    )
    from .settlement_routes import (
        create_settlement, get_group_settlements, 
        get_user_balance, get_balance_breakdown, get_group_balances
    )
    from .admin_routes import (
        health_check, detailed_health_check, get_cache_stats, get_detailed_cache_stats,
        warm_cache, get_performance_metrics, get_rate_limits, get_categories, get_split_types
    )
    
    # Register user routes
    expense_bp.add_url_rule('/user/profile', 'create_user_profile', create_user_profile, methods=['POST'])
    expense_bp.add_url_rule('/user/profile', 'get_user_profile', get_user_profile, methods=['GET'])
    expense_bp.add_url_rule('/user/profile', 'update_user_profile', update_user_profile, methods=['PUT'])
    expense_bp.add_url_rule('/user/search', 'search_users', search_users, methods=['GET'])
    
    # Register group routes
    expense_bp.add_url_rule('/groups', 'create_group', create_group, methods=['POST'])
    expense_bp.add_url_rule('/groups', 'get_user_groups', get_user_groups, methods=['GET'])
    expense_bp.add_url_rule('/groups/<group_id>', 'get_group', get_group, methods=['GET'])
    expense_bp.add_url_rule('/groups/<group_id>/full', 'get_group_full', get_group_full, methods=['GET'])
    expense_bp.add_url_rule('/groups/<group_id>', 'update_group', update_group, methods=['PUT'])
    expense_bp.add_url_rule('/groups/<group_id>', 'delete_group', delete_group, methods=['DELETE'])
    expense_bp.add_url_rule('/groups/<group_id>/members', 'get_group_members', get_group_members, methods=['GET'])
    expense_bp.add_url_rule('/groups/<group_id>/members/<user_id>', 'get_member_details', get_member_details, methods=['GET'])
    expense_bp.add_url_rule('/groups/<group_id>/members/<user_id>', 'remove_group_member', remove_group_member, methods=['DELETE'])
    expense_bp.add_url_rule('/groups/<group_id>/leave', 'leave_group', leave_group, methods=['POST'])
    
    # Register invitation routes
    expense_bp.add_url_rule('/invitations', 'create_invitation', create_invitation, methods=['POST'])
    expense_bp.add_url_rule('/invitations', 'get_user_invitations', get_user_invitations, methods=['GET'])
    expense_bp.add_url_rule('/invitations/group/<group_id>', 'get_group_invitations', get_group_invitations, methods=['GET'])
    expense_bp.add_url_rule('/invitations/<invitation_id>/details', 'get_invitation_details', get_invitation_details, methods=['GET'])
    expense_bp.add_url_rule('/invitations/<invitation_id>/accept', 'accept_invitation', accept_invitation, methods=['POST'])
    expense_bp.add_url_rule('/invitations/<invitation_id>/reject', 'reject_invitation', reject_invitation, methods=['POST'])
    
    # Register expense routes
    expense_bp.add_url_rule('/expenses', 'create_expense', create_expense, methods=['POST'])
    expense_bp.add_url_rule('/expenses/<expense_id>', 'get_expense', get_expense, methods=['GET'])
    expense_bp.add_url_rule('/expenses/<expense_id>', 'update_expense', update_expense, methods=['PUT'])
    expense_bp.add_url_rule('/expenses/<expense_id>', 'delete_expense', delete_expense, methods=['DELETE'])
    expense_bp.add_url_rule('/expenses/personal', 'get_personal_expenses', get_personal_expenses, methods=['GET'])
    expense_bp.add_url_rule('/expenses/group/<group_id>', 'get_group_expenses', get_group_expenses, methods=['GET'])
    expense_bp.add_url_rule('/expenses/user', 'get_user_all_expenses', get_user_all_expenses, methods=['GET'])
    
    # Register settlement routes
    expense_bp.add_url_rule('/settlements', 'create_settlement', create_settlement, methods=['POST'])
    expense_bp.add_url_rule('/settlements/group/<group_id>', 'get_group_settlements', get_group_settlements, methods=['GET'])
    expense_bp.add_url_rule('/balance', 'get_user_balance', get_user_balance, methods=['GET'])
    expense_bp.add_url_rule('/balance/breakdown', 'get_balance_breakdown', get_balance_breakdown, methods=['GET'])
    expense_bp.add_url_rule('/balance/group/<group_id>', 'get_group_balances', get_group_balances, methods=['GET'])
    expense_bp.add_url_rule('/balances/group/<group_id>', 'get_group_balances_alias', get_group_balances, methods=['GET'])
    
    # Register admin routes
    expense_bp.add_url_rule('/health', 'health_check', health_check, methods=['GET'])
    expense_bp.add_url_rule('/health/detailed', 'detailed_health_check', detailed_health_check, methods=['GET'])
    expense_bp.add_url_rule('/cache/stats', 'get_cache_stats', get_cache_stats, methods=['GET'])
    expense_bp.add_url_rule('/cache/stats/detailed', 'get_detailed_cache_stats', get_detailed_cache_stats, methods=['GET'])
    expense_bp.add_url_rule('/cache/warm', 'warm_cache', warm_cache, methods=['POST'])
    expense_bp.add_url_rule('/metrics', 'get_performance_metrics', get_performance_metrics, methods=['GET'])
    expense_bp.add_url_rule('/rate-limits', 'get_rate_limits', get_rate_limits, methods=['GET'])
    expense_bp.add_url_rule('/categories', 'get_categories', get_categories, methods=['GET'])
    expense_bp.add_url_rule('/split-types', 'get_split_types', get_split_types, methods=['GET'])


# Execute blueprint combination
_combine_blueprints()


# Export for backward compatibility
__all__ = [
    'expense_bp',
    'user_bp',
    'group_bp', 
    'invitation_bp',
    'settlement_bp',
    'admin_bp'
]
