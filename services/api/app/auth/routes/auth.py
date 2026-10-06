# Purpose: Authentication Routes API endpoints for user authentication.
"""
Authentication Routes
API endpoints for user authentication
"""

import logging

from app.core.apiutils.responses import (error_response, success_response,
                                     validation_error_response)
from app.core.apiutils.validators import parse_query_int, validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_auth
from app.auth.security.decorators import (get_current_user_id,
                                                require_auth,
                                                require_refresh_token)
from app.auth.security.jwt import clear_auth_cookies, set_auth_cookies
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import (ChangePasswordSchema, CheckEmailSchema,
                                LoginSchema, SignupSchema, UpdateProfileSchema,
                                validate_request)
from app.auth.services.auth_service import auth_service
from flask import Blueprint, g, jsonify, make_response, request

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


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
        return success_response(message='OK')
    
    data = request.get_json(silent=True)
    if not data:
        return error_response('Request body required')

    validated, errors = validate_request(SignupSchema, data)
    if errors:
        return validation_error_response(errors)

    success, result = auth_service.signup(
        email=validated['email'],
        password=validated['password'],
        display_name=validated.get('display_name') or validated['email'].split('@')[0],
        phone=validated.get('phone'),
        default_currency=validated.get('default_currency', Config.DEFAULT_CURRENCY)
    )
    
    if success:
        resp = make_response(jsonify({'success': True, 'message': 'Signup successful', 'data': result}), 201)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        return error_response(result.get('error', 'Signup failed'))


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
        return success_response({}, message='OK')
    
    data = request.get_json(silent=True)
    if not data:
        return error_response('Request body required')

    validated, errors = validate_request(LoginSchema, data)
    if errors:
        return error_response('Invalid credentials', 401)

    device_info = request.headers.get('User-Agent', 'Unknown')

    success, result = auth_service.login(
        email=validated['email'],
        password=validated['password'],
        device_info=device_info,
        client_ip=request.remote_addr,
    )
    
    if success:
        resp = make_response(jsonify({'success': True, 'message': 'Login successful', 'data': result}), 200)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        status = 429 if result.get('locked') else 401
        return error_response(result.get('error', 'Login failed'), status)


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
        resp = make_response(jsonify({'success': True, 'message': 'Logged out successfully', 'data': result}), 200)
        clear_auth_cookies(resp)
        return resp
    else:
        return error_response(result.get('error', 'Logout failed'))


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
        resp = make_response(jsonify({'success': True, 'message': 'Logged out from all devices', 'data': result}), 200)
        clear_auth_cookies(resp)
        return resp
    else:
        return error_response(result.get('error', 'Logout failed'))


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
    data = request.get_json(silent=True) or {}
    
    # Accept refresh token from body, cookie, or header (in priority order)
    refresh = data.get('refresh_token') or request.cookies.get('refresh_token')
    if not refresh:
        return error_response('Refresh token required')
    
    success, result = auth_service.refresh_tokens(refresh)
    
    if success:
        resp = make_response(jsonify({'success': True, 'message': 'Token refreshed', 'data': result}), 200)
        if result.get('access_token') and result.get('refresh_token'):
            set_auth_cookies(resp, result['access_token'], result['refresh_token'])
        return resp
    else:
        return error_response(result.get('error', 'Token refresh failed'), 401)


@auth_bp.route('/me', methods=['GET'])
@require_auth
@cache_response(key_prefix='auth:me', ttl=Config.CACHE_TTLS['user_detail'], vary_on_user=True)
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
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'User not found'), 404)


@auth_bp.route('/me', methods=['PUT'])
@require_auth
@validate_schema(UpdateProfileSchema)
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
    data = g.validated_data
    user_id = get_current_user_id()
    
    success, result = auth_service.update_profile(
        user_id=user_id,
        display_name=data.get('display_name'),
        phone=data.get('phone'),
        photo_url=data.get('photo_url'),
        default_currency=data.get('default_currency')
    )
    
    if success:
        invalidate_cache('auth:me:*')
        invalidate_cache('auth:profile:*')
        invalidate_cache('auth:bootstrap:*')
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to update profile'))


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
@validate_schema(ChangePasswordSchema)
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
    data = g.validated_data
    user_id = get_current_user_id()
    
    success, result = auth_service.change_password(
        user_id=user_id,
        current_password=data['current_password'],
        new_password=data['new_password']
    )
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to change password'))


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
    data = request.get_json(silent=True)
    if not data:
        return error_response('Email is required')

    validated, errors = validate_request(CheckEmailSchema, data)
    if errors:
        return error_response('Valid email is required')

    # Prevent email enumeration -- always return same response shape + timing
    auth_service.check_email_exists(validated['email'])
    return success_response(message='Check complete')


@auth_bp.route('/user/profile', methods=['GET'])
@require_auth
@cache_response(key_prefix='auth:profile', ttl=Config.CACHE_TTLS['user_detail'], vary_on_user=True)
def get_user_profile():
    """
    Get user profile (alias for /me)
    For frontend compatibility
    """
    user_id = get_current_user_id()
    
    success, result = auth_service.get_current_user(user_id)
    
    if success:
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'User not found'), 404)


@auth_bp.route('/user/profile', methods=['PUT'])
@require_auth
@validate_schema(UpdateProfileSchema)
def update_user_profile():
    """
    Update user profile (alias for PUT /me)
    For frontend compatibility
    """
    data = g.validated_data
    user_id = get_current_user_id()
    
    success, result = auth_service.update_profile(
        user_id=user_id,
        display_name=data.get('display_name'),
        phone=data.get('phone'),
        photo_url=data.get('photo_url'),
        default_currency=data.get('default_currency')
    )
    
    if success:
        invalidate_cache('auth:me:*')
        invalidate_cache('auth:profile:*')
        invalidate_cache('auth:bootstrap:*')
        return success_response(data=result)
    else:
        return error_response(result.get('error', 'Failed to update profile'))


@auth_bp.route('/mega-bootstrap', methods=['GET'])
@require_auth
@cache_response(key_prefix='auth:bootstrap', ttl=Config.CACHE_TTLS['dashboard'], vary_on_user=True)
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
    from app.expenses.services.expense_group_service import group_service_sql
    from app.expenses.services.expense_invite_service import invitation_service_sql
    from app.expenses.services.expense_service import expense_service_sql
    from app.expenses.services.settlement_service import settlement_service_sql
    
    user_id = get_current_user_id()
    active_group_id = request.args.get('active_group_id')
    expenses_limit = parse_query_int(
        'recent_expenses_limit', Config.SEARCH_DEFAULT_LIMIT,
        minimum=1,
        maximum=100,
    )
    
    # Get user profile
    user_success, _user_result = auth_service.get_current_user(user_id)
    if not user_success:
        return error_response('User not found', 404)
    
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
            group_id = active_group_id
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
    
    return success_response(
        data=response_data,
        meta={'source': 'sql_database'}
    )


# NOTE: Invitations endpoint is in invitations_sql_routes.py
# These placeholder routes have been removed to avoid conflict
# NOTE: Invitations endpoint is in invitations_sql_routes.py


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

@auth_bp.route('/verify-email', methods=['GET'])
def verify_email():
    """
    Verify user email via token (sent in verification email link).

    Query params:
        token: JWT verification token
    """
    token = request.args.get('token')
    if not token:
        return error_response('Verification token required', 400)

    success, result = auth_service.verify_email(token)
    if success:
        return success_response(data=result, message=result.get('message'))
    return error_response(result.get('error', 'Verification failed'), 400)


@auth_bp.route('/resend-verification', methods=['POST'])
@require_auth
@limit_auth()
def resend_verification():
    """Resend verification email for the current authenticated user."""
    user_id = get_current_user_id()
    success, result = auth_service.resend_verification(user_id)
    if success:
        return success_response(data=result, message=result.get('message'))
    return error_response(result.get('error', 'Failed to resend verification'), 400)
# These placeholder routes have been removed to avoid conflict
