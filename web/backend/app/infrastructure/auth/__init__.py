"""
Auth Infrastructure Package

- jwt.py         — JWT token creation/verification
- password.py    — bcrypt password hashing
- decorators.py  — Flask route protection decorators (@require_auth etc.)
"""
from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    get_token_identity,
    get_token_expiry,
    set_auth_cookies,
    clear_auth_cookies,
)
from .password import hash_password, verify_password, is_password_strong
from .decorators import (
    require_auth,
    require_refresh_token,
    optional_auth,
    get_current_user,
    get_current_user_id,
)

__all__ = [
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'decode_token',
    'get_token_identity',
    'get_token_expiry',
    'set_auth_cookies',
    'clear_auth_cookies',
    'hash_password',
    'verify_password',
    'is_password_strong',
    'require_auth',
    'require_refresh_token',
    'optional_auth',
    'get_current_user',
    'get_current_user_id',
]
