"""
Users API Endpoints
====================
REST API for user authentication and management.
"""
import logging
from functools import wraps
from typing import Callable, TypeVar

from app.core.exceptions import AppError, AuthenticationError, ValidationError
from app.infrastructure.auth.jwt import decode_token
from app.schemas.users import (PasswordChangeRequest, RefreshTokenRequest,
                               UserLoginRequest, UserRegisterRequest,
                               UserUpdateRequest)
from app.services import user_service
from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

F = TypeVar('F', bound=Callable)


def _get_request_json() -> dict:
    """Get JSON from request body."""
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Request body must be JSON')
    return data


def _success_response(data: dict, status_code: int = 200):
    """Create a success JSON response."""
    return jsonify({'success': True, **data}), status_code


def _error_response(message: str, status_code: int = 400):
    """Create an error JSON response."""
    return jsonify({'success': False, 'message': message}), status_code


def login_required(f: F) -> F:
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return _error_response('Authorization header required', 401)

        token = auth_header.split(' ', 1)[1]
        payload = decode_token(token)
        if not payload:
            return _error_response('Invalid or expired token', 401)

        if payload.get('type') != 'access':
            return _error_response('Invalid token type', 401)

        g.current_user_id = payload.get('user_id')
        g.current_user_email = payload.get('email')
        return f(*args, **kwargs)
    return decorated  # type: ignore


@users_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = _get_request_json()
        validated = UserRegisterRequest(**data)
        result = user_service.register(
            email=validated.email,
            password=validated.password,
            display_name=validated.display_name,
            phone=validated.phone,
        )
        return _success_response(result, 201)
    except PydanticValidationError as e:
        return _error_response(str(e.errors()[0]['msg']), 400)
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return tokens."""
    try:
        data = _get_request_json()
        validated = UserLoginRequest(**data)
        result = user_service.login(
            email=validated.email,
            password=validated.password,
            device_info=request.headers.get('User-Agent'),
            ip_address=request.remote_addr,
        )
        return _success_response(result)
    except PydanticValidationError as e:
        return _error_response(str(e.errors()[0]['msg']), 400)
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token."""
    try:
        data = _get_request_json()
        validated = RefreshTokenRequest(**data)
        result = user_service.refresh_tokens(validated.refresh_token)
        return _success_response(result)
    except PydanticValidationError as e:
        return _error_response(str(e.errors()[0]['msg']), 400)
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/logout', methods=['POST'])
def logout():
    """Logout (invalidate refresh token)."""
    try:
        data = _get_request_json()
        refresh_token = data.get('refresh_token')
        if refresh_token:
            user_service.logout(refresh_token)
        return _success_response({'message': 'Logged out successfully'})
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user profile."""
    try:
        user = user_service.get_user(g.current_user_id)
        return _success_response({'user': user})
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/me', methods=['PATCH'])
@login_required
def update_profile():
    """Update current user profile."""
    try:
        data = _get_request_json()
        validated = UserUpdateRequest(**data)
        update_data = validated.model_dump(exclude_none=True)
        user = user_service.update_profile(g.current_user_id, **update_data)
        return _success_response({'user': user})
    except PydanticValidationError as e:
        return _error_response(str(e.errors()[0]['msg']), 400)
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/me/password', methods=['PUT'])
@login_required
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
        return _success_response({'message': 'Password changed successfully'})
    except PydanticValidationError as e:
        return _error_response(str(e.errors()[0]['msg']), 400)
    except AppError as e:
        return _error_response(e.message, e.status_code)


@users_bp.route('/me/sessions', methods=['DELETE'])
@login_required
def logout_all_sessions():
    """Logout from all devices."""
    try:
        count = user_service.logout_all(g.current_user_id)
        return _success_response({'message': f'Logged out from {count} sessions'})
    except AppError as e:
        return _error_response(e.message, e.status_code)
