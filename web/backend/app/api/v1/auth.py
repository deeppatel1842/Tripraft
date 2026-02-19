"""
Authentication Routes
API endpoints for user authentication
"""

import logging

from app.core.rate_limiter import limit_auth
from app.infrastructure.auth.decorators import (get_current_user_id,
                                                require_auth,
                                                require_refresh_token)
from app.infrastructure.auth.jwt import clear_auth_cookies, set_auth_cookies
from app.schemas.common import (CheckEmailSchema, LoginSchema, SignupSchema,
                                validate_request)
from app.services.auth_service import auth_service
from flask import Blueprint, jsonify, make_response, request

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/expense')


@auth_bp.route('/signup', methods=['POST', 'OPTIONS'])
@limit_auth()
def signup():
    """
    Register a new user
    
    Request body:
    {
        "email": "user@example.com",
        "password": "SecurePass123!",
        "display_name": "John Doe",
        "phone": "+1234567890",  // optional
        "default_currency": "INR"  // optional, defaults to INR
    }
    
    Response:
    {
        "success": true,
        "user": {...},
        "access_token": "...",
        "refresh_token": "...",
        "token_type": "Bearer"
    }
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    validated, errors = validate_request(SignupSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    success, result = auth_service.signup(
        email=validated['email'],
        password=validated['password'],
        display_name=validated.get('display_name') or validated['email'].split('@')[0],
        phone=data.get('phone'),
        default_currency=data.get('default_currency', 'INR')
    )
    
    if success:
        resp = make_response(jsonify({'success': True, **result}), 201)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@limit_auth()
def login():
    """
    Authenticate user
    
    Request body:
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    
    Response:
    {
        "success": true,
        "user": {...},
        "access_token": "...",
        "refresh_token": "...",
        "token_type": "Bearer"
    }
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    validated, errors = validate_request(LoginSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    device_info = request.headers.get('User-Agent', 'Unknown')

    success, result = auth_service.login(
        email=validated['email'],
        password=validated['password'],
        device_info=device_info
    )
    
    if success:
        resp = make_response(jsonify({'success': True, **result}), 200)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        return jsonify({'success': False, **result}), 401


@auth_bp.route('/logout', methods=['POST'])
@require_refresh_token
def logout():
    """
    Logout current user (invalidate refresh token)
    
    Requires: Refresh token in Authorization header
    
    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    from flask import g
    
    user_id = g.current_user.get('id')
    current_refresh_token = g.refresh_token
    
    success, result = auth_service.logout(user_id, current_refresh_token)
    
    if success:
        resp = make_response(jsonify({'success': True, **result}), 200)
        clear_auth_cookies(resp)
        return resp
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/logout-all', methods=['POST'])
@require_auth
def logout_all():
    """
    Logout from all devices
    
    Requires: Access token in Authorization header
    
    Response:
    {
        "success": true,
        "message": "Logged out from all devices"
    }
    """
    user_id = get_current_user_id()
    
    success, result = auth_service.logout_all_devices(user_id)
    
    if success:
        resp = make_response(jsonify({'success': True, **result}), 200)
        clear_auth_cookies(resp)
        return resp
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh access token
    
    Request body:
    {
        "refresh_token": "..."
    }
    
    Response:
    {
        "success": true,
        "access_token": "...",
        "refresh_token": "...",
        "token_type": "Bearer"
    }
    """
    data = request.get_json() or {}
    
    # Accept refresh token from body, cookie, or header (in priority order)
    refresh = data.get('refresh_token') or request.cookies.get('refresh_token')
    if not refresh:
        return jsonify({
            'success': False,
            'error': 'Refresh token required'
        }), 400
    
    success, result = auth_service.refresh_tokens(refresh)
    
    if success:
        resp = make_response(jsonify({'success': True, **result}), 200)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        return jsonify({'success': False, **result}), 401


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me():
    """
    Get current user profile
    
    Requires: Access token in Authorization header
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    user_id = get_current_user_id()
    
    success, result = auth_service.get_current_user(user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 404


@auth_bp.route('/me', methods=['PUT'])
@require_auth
def update_me():
    """
    Update current user profile
    
    Requires: Access token in Authorization header
    
    Request body:
    {
        "display_name": "New Name",  // optional
        "phone": "+1234567890",  // optional
        "photo_url": "https://...",  // optional
        "default_currency": "USD"  // optional
    }
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    data = request.get_json() or {}
    user_id = get_current_user_id()
    
    success, result = auth_service.update_profile(
        user_id=user_id,
        display_name=data.get('display_name'),
        phone=data.get('phone'),
        photo_url=data.get('photo_url'),
        default_currency=data.get('default_currency')
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Change user password
    
    Requires: Access token in Authorization header
    
    Request body:
    {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!"
    }
    
    Response:
    {
        "success": true,
        "message": "Password changed successfully. Please login again."
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({
            'success': False,
            'error': 'Current password and new password are required'
        }), 400
    
    user_id = get_current_user_id()
    
    success, result = auth_service.change_password(
        user_id=user_id,
        current_password=current_password,
        new_password=new_password
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/check-email', methods=['POST'])
@limit_auth()
def check_email():
    """
    Check if email is already registered
    
    Request body:
    {
        "email": "user@example.com"
    }
    
    Response:
    {
        "success": true,
        "exists": true/false
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    validated, errors = validate_request(CheckEmailSchema, data)
    if errors:
        return jsonify({'success': False, 'error': 'Valid email is required'}), 400

    # Prevent email enumeration — always return same response shape + timing
    auth_service.check_email_exists(validated['email'])
    return jsonify({'success': True, 'message': 'Check complete'}), 200


@auth_bp.route('/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """
    Get user profile (alias for /me)
    For frontend compatibility
    """
    user_id = get_current_user_id()
    
    success, result = auth_service.get_current_user(user_id)
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 404


@auth_bp.route('/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """
    Update user profile (alias for PUT /me)
    For frontend compatibility
    """
    data = request.get_json() or {}
    user_id = get_current_user_id()
    
    success, result = auth_service.update_profile(
        user_id=user_id,
        display_name=data.get('display_name'),
        phone=data.get('phone'),
        photo_url=data.get('photo_url'),
        default_currency=data.get('default_currency')
    )
    
    if success:
        return jsonify({'success': True, **result}), 200
    else:
        return jsonify({'success': False, **result}), 400


@auth_bp.route('/mega-bootstrap', methods=['GET'])
@require_auth
def mega_bootstrap():
    """
    Get all user data in a single call (for quick app loading)
    
    Query params:
    - active_group_id: Currently selected group ID (optional)
    - recent_expenses_limit: Number of recent expenses to return (default 20)
    
    Response matches frontend expectations:
    {
        "success": true,
        "data": {
            "groups": [...],
            "invitations": [],
            "active_group": {
                "group": {...},
                "members": [...],
                "balances": [...],
                "expenses": [...],
                "settlements": [...],
                "invitations": [],
                "all_members_map": {...}
            }
        }
    }
    """
    from app.services.expense_group_service import group_service_sql
    from app.services.expense_invite_service import invitation_service_sql
    from app.services.expense_service import expense_service_sql
    from app.services.settlement_service import settlement_service_sql
    
    user_id = get_current_user_id()
    active_group_id = request.args.get('active_group_id')
    expenses_limit = int(request.args.get('recent_expenses_limit', 20))
    
    # Get user profile
    user_success, _user_result = auth_service.get_current_user(user_id)
    if not user_success:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get user groups
    groups_success, groups_result = group_service_sql.get_user_groups(user_id)
    groups = groups_result.get('groups', []) if groups_success else []
    
    # Get pending invitations
    invitations_success, invitations_result = invitation_service_sql.get_pending_invitations_for_user(user_id)
    invitations = invitations_result.get('invitations', []) if invitations_success else []
    
    # DEBUG: Log invitation fetch
    logger.info("Mega-bootstrap for user %s: Found %d pending invitations", user_id, len(invitations))
    if invitations:
        logger.info("   Invitations: %s", [inv.get('group_name') for inv in invitations])
    
    # Build response in frontend-expected format
    response_data = {
        'groups': groups,
        'invitations': invitations,
        'active_group': None
    }
    
    # Get active group details if provided
    if active_group_id:
        try:
            group_id = int(active_group_id)
            group_success, group_result = group_service_sql.get_group(group_id, user_id)
            if group_success:
                group_info = group_result.get('group', {})
                
                # Get group members
                members_success, members_result = group_service_sql.get_group_members(group_id, user_id)
                members = members_result.get('members', []) if members_success else []
                
                # Build all_members_map for quick lookups
                all_members_map = {}
                for member in members:
                    member_id = str(member.get('id'))
                    all_members_map[member_id] = {
                        'user_id': member.get('id'),
                        'display_name': member.get('display_name') or member.get('email', '').split('@')[0],
                        'email': member.get('email'),
                        'photo_url': member.get('photo_url'),
                        'role': member.get('role')
                    }
                
                # Get recent expenses for the group
                expenses_success, expenses_result = expense_service_sql.get_group_expenses(
                    group_id, user_id, limit=expenses_limit
                )
                expenses = expenses_result.get('expenses', []) if expenses_success else []
                
                # Get balances
                balances_success, balances_result = group_service_sql.get_group_balances(group_id, user_id)
                balances = balances_result.get('balances', []) if balances_success else []
                
                # Get settlements
                settlements_success, settlements_result = settlement_service_sql.get_group_settlements(
                    group_id, user_id
                )
                settlements = settlements_result.get('settlements', []) if settlements_success else []
                
                response_data['active_group'] = {
                    'group': group_info,
                    'members': members,
                    'balances': balances,
                    'expenses': expenses,
                    'settlements': settlements,
                    'invitations': [],  # Group pending invitations
                    'all_members_map': all_members_map
                }
        except (ValueError, TypeError) as e:
            logger.error("Error processing active group %s: %s", active_group_id, e)
    
    return jsonify({
        'success': True,
        'data': response_data,
        'meta': {
            'source': 'sql_database',
            'fetch_time_ms': 0
        }
    }), 200


# NOTE: Invitations endpoint is in invitations_sql_routes.py
# These placeholder routes have been removed to avoid conflict
# NOTE: Invitations endpoint is in invitations_sql_routes.py
# These placeholder routes have been removed to avoid conflict
