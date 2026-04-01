"""
Auth Infrastructure Package

- jwt.py         — JWT token creation/verification
- password.py    — bcrypt password hashing
- decorators.py  — Flask route protection decorators (@require_auth etc.)
"""
from .decorators import (get_current_user, get_current_user_id, optional_auth,
                         require_admin, require_auth, require_refresh_token)
from .jwt import (clear_auth_cookies, create_access_token,
                  create_refresh_token, decode_token, get_token_expiry,
                  get_token_identity, set_auth_cookies, verify_token)
from .password import hash_password, is_password_strong, verify_password

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
    'require_admin',
    'require_refresh_token',
    'optional_auth',
    'get_current_user',
    'get_current_user_id',
]
