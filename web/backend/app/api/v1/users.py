"""
Users API Endpoints
====================
REST API for user authentication and profile management.
Auth operations delegate to AuthService; profile operations use UserService.
"""
import logging

from app.api.utils.responses import (created_response, error_response,
                                     success_response)
from app.core.config import Config
from app.core.exceptions import AppError, ValidationError
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth
from app.infrastructure.auth.jwt import decode_token
from app.infrastructure.cache.redis import cache_response, invalidate_cache
from app.schemas.users import (PasswordChangeRequest, RefreshTokenRequest,
                               UserLoginRequest, UserRegisterRequest,
                               UserUpdateRequest)
from app.services.auth_service import auth_service
from app.services.user_service import user_service
from flask import Blueprint, g, request
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)


def _get_request_json() -> dict:
    """Get JSON from request body."""
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Request body must be JSON')
    return data


@users_bp.route('/register', methods=['POST'])
@limit_api(Config.RATE_LIMITS['auth'])
def register():
    """Register a new user."""
    try:
        data = _get_request_json()
        validated = UserRegisterRequest(**data)
        success, result = auth_service.signup(
            email=validated.email,
            password=validated.password,
            display_name=validated.display_name or validated.email.split('@')[0],
            phone=validated.phone,
        )
        if success:
            return created_response(data=result)
        return error_response(result.get('error', 'Registration failed'))
    except PydanticValidationError as e:
        return error_response(str(e.errors()[0]['msg']))
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/login', methods=['POST'])
@limit_api(Config.RATE_LIMITS['auth'])
def login():
    """Authenticate user and return tokens."""
    try:
        data = _get_request_json()
        validated = UserLoginRequest(**data)
        success, result = auth_service.login(
            email=validated.email,
            password=validated.password,
            device_info=request.headers.get('User-Agent'),
            client_ip=request.remote_addr,
        )
        if success:
            return success_response(data=result)
        status = 429 if result.get('locked') else 401
        return error_response(result.get('error', 'Login failed'), status)
    except PydanticValidationError as e:
        return error_response(str(e.errors()[0]['msg']))
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/refresh', methods=['POST'])
@limit_api(Config.RATE_LIMITS['auth'])
def refresh_token():
    """Refresh access token."""
    try:
        data = _get_request_json()
        validated = RefreshTokenRequest(**data)
        success, result = auth_service.refresh_tokens(validated.refresh_token)
        if success:
            return success_response(data=result)
        return error_response(result.get('error', 'Token refresh failed'), 401)
    except PydanticValidationError as e:
        return error_response(str(e.errors()[0]['msg']))
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/logout', methods=['POST'])
@limit_api(Config.RATE_LIMITS['auth'])
def logout():
    """Logout (invalidate refresh token)."""
    try:
        data = _get_request_json()
        refresh_token_str = data.get('refresh_token')
        if refresh_token_str:
            payload = decode_token(refresh_token_str)
            user_id = (payload.get('user_id') or 0) if payload else 0
            auth_service.logout(user_id, refresh_token_str)
        return success_response(message='Logged out successfully')
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/me', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='users:me', ttl=Config.CACHE_TTLS['user_detail'], vary_on_user=True)
def get_current_user():
    """Get current user profile."""
    try:
        user = user_service.get_user(g.current_user_id)
        return success_response(data={'user': user})
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/me', methods=['PATCH'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
def update_profile():
    """Update current user profile."""
    try:
        data = _get_request_json()
        validated = UserUpdateRequest(**data)
        update_data = validated.model_dump(exclude_none=True)
        user = user_service.update_profile(g.current_user_id, **update_data)
        invalidate_cache('users:me:*')
        invalidate_cache('auth:bootstrap:*')
        return success_response(data={'user': user})
    except PydanticValidationError as e:
        return error_response(str(e.errors()[0]['msg']))
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/me/password', methods=['PUT'])
@limit_api(Config.RATE_LIMITS['auth'])
@require_auth
def change_password():
    """Change user password."""
    try:
        data = _get_request_json()
        validated = PasswordChangeRequest(**data)
        user_service.change_password(
            user_id=g.current_user_id,
            current_password=validated.current_password,
            new_password=validated.new_password,
        )
        return success_response(message='Password changed successfully')
    except PydanticValidationError as e:
        return error_response(str(e.errors()[0]['msg']))
    except AppError as e:
        return error_response(e.message, e.status_code)


@users_bp.route('/me/sessions', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
def logout_all_sessions():
    """Logout from all devices."""
    try:
        auth_service.logout_all_devices(g.current_user_id)
        return success_response(message='Logged out from all sessions')
    except AppError as e:
        return error_response(e.message, e.status_code)
