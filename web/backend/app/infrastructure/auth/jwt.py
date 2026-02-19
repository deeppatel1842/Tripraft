"""
JWT Token Handler
Creates and validates JWT tokens for authentication.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from app.core.config import Config

logger = logging.getLogger(__name__)

# Configuration from central config
JWT_SECRET_KEY = Config.JWT_SECRET_KEY
JWT_ALGORITHM = Config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRES = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
REFRESH_TOKEN_EXPIRES = timedelta(seconds=Config.JWT_REFRESH_TOKEN_EXPIRES)

# Cookie configuration (for secure cookie handling)
COOKIE_SECURE = Config.FLASK_ENV == 'production'
COOKIE_SAMESITE = 'Lax'
COOKIE_PATH = '/'


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: int,
    email: str,
    display_name: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a JWT access token."""
    now = _utc_now()
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'email': email,
        'name': display_name,
        'type': 'access',
        'iat': now,
        'exp': now + ACCESS_TOKEN_EXPIRES,
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, session_id: Optional[int] = None) -> str:
    """Create a JWT refresh token."""
    now = _utc_now()
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'type': 'refresh',
        'session_id': session_id,
        'iat': now,
        'exp': now + REFRESH_TOKEN_EXPIRES,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = 'access') -> bool:
    """Verify if a token is valid and of expected type."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != token_type:
            logger.warning("Token type mismatch: expected %s, got %s", token_type, payload.get('type'))
            return False
        return True
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return False
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", str(e))
        return False


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token and return payload, or None if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", str(e))
        return None


def get_token_identity(token: str) -> Optional[int]:
    """Get user ID from token."""
    payload = decode_token(token)
    if payload:
        return payload.get('sub')
    return None


def get_token_expiry() -> Dict[str, int]:
    """Get token expiry times in seconds."""
    return {
        'access_token_expires': int(ACCESS_TOKEN_EXPIRES.total_seconds()),
        'refresh_token_expires': int(REFRESH_TOKEN_EXPIRES.total_seconds()),
    }


# ---------------------------------------------------------------------------
# httpOnly cookie helpers
# ---------------------------------------------------------------------------

def set_auth_cookies(response, access_token: str, refresh_token: str):
    """Set httpOnly cookies for both access and refresh tokens."""
    common = dict(
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )

    response.set_cookie(
        'access_token',
        access_token,
        max_age=int(ACCESS_TOKEN_EXPIRES.total_seconds()),
        **common,
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        max_age=int(REFRESH_TOKEN_EXPIRES.total_seconds()),
        **common,
    )
    return response


def clear_auth_cookies(response):
    """Remove auth cookies on logout."""
    common = dict(
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )

    response.delete_cookie('access_token', **common)
    response.delete_cookie('refresh_token', **common)
    return response
