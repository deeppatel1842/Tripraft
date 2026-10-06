# Purpose: JWT Token Handler Creates and validates JWT tokens for authentication.
"""
JWT Token Handler
Creates and validates JWT tokens for authentication.
Supports key rotation via kid (Key ID) in JWT headers.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from app.core.config import Config

logger = logging.getLogger(__name__)

# Configuration from central config
JWT_ALGORITHM = Config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRES = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
REFRESH_TOKEN_EXPIRES = timedelta(seconds=Config.JWT_REFRESH_TOKEN_EXPIRES)

# Key rotation — strip empty keys
_SIGNING_KEYS: Dict[str, str] = {
    k: v for k, v in Config.JWT_SIGNING_KEYS.items() if v
}
_CURRENT_KID: str = Config.JWT_CURRENT_KEY_VERSION

# Cookie configuration (for secure cookie handling)
COOKIE_SECURE = Config.COOKIE_SECURE
COOKIE_SAMESITE = Config.COOKIE_SAMESITE
COOKIE_PATH = Config.COOKIE_PATH


def _get_signing_key() -> str:
    """Return the current active signing key."""
    key = _SIGNING_KEYS.get(_CURRENT_KID)
    if not key:
        raise RuntimeError(f"JWT signing key '{_CURRENT_KID}' is not configured")
    return key


def _get_verification_key(token: str) -> str:
    """Extract kid from token header and return the matching key."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError:
        raise jwt.InvalidTokenError("Malformed token header")

    kid = header.get('kid', 'v1')
    key = _SIGNING_KEYS.get(kid)
    if not key:
        raise jwt.InvalidTokenError(f"Unknown key version: {kid}")
    return key


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: str,
    email: str,
    display_name: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a JWT access token signed with the current key version."""
    now = _utc_now()
    payload = {
        'sub': str(user_id),
        'user_id': str(user_id),
        'email': email,
        'name': display_name,
        'type': 'access',
        'iat': now,
        'exp': now + ACCESS_TOKEN_EXPIRES,
    }
    if additional_claims:
        _RESERVED = frozenset(('sub', 'user_id', 'email', 'type', 'iat', 'exp'))
        sanitized = {k: v for k, v in additional_claims.items() if k not in _RESERVED}
        payload.update(sanitized)
    return jwt.encode(
        payload,
        _get_signing_key(),
        algorithm=JWT_ALGORITHM,
        headers={'kid': _CURRENT_KID},
    )


def create_refresh_token(user_id: str, session_id: Optional[str] = None) -> str:
    """Create a JWT refresh token signed with the current key version."""
    now = _utc_now()
    payload = {
        'sub': str(user_id),
        'user_id': str(user_id),
        'type': 'refresh',
        'session_id': session_id,
        # Without a unique claim the payload is fully determined by
        # (user_id, session_id, iat, exp), and iat has one-second
        # resolution -- so two refresh tokens minted for the same user in
        # the same second were byte-identical. Rotation then handed back
        # the token it was supposed to retire, and two devices signing in
        # together collided on one user_sessions row.
        'jti': secrets.token_urlsafe(16),
        'iat': now,
        'exp': now + REFRESH_TOKEN_EXPIRES,
    }
    return jwt.encode(
        payload,
        _get_signing_key(),
        algorithm=JWT_ALGORITHM,
        headers={'kid': _CURRENT_KID},
    )


_EMAIL_VERIFY_EXPIRES = timedelta(hours=24)


def create_email_verification_token(user_id: str, email: str) -> str:
    """Create a short-lived JWT for email verification (24h)."""
    now = _utc_now()
    payload = {
        'sub': str(user_id),
        'email': email,
        'type': 'email_verify',
        'iat': now,
        'exp': now + _EMAIL_VERIFY_EXPIRES,
    }
    return jwt.encode(
        payload,
        _get_signing_key(),
        algorithm=JWT_ALGORITHM,
        headers={'kid': _CURRENT_KID},
    )


def verify_token(token: str, token_type: str = 'access') -> bool:
    """Verify if a token is valid and of expected type."""
    try:
        key = _get_verification_key(token)
        payload = jwt.decode(token, key, algorithms=[JWT_ALGORITHM])
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
    """Decode a JWT token using the appropriate key version, or None if invalid."""
    try:
        key = _get_verification_key(token)
        return jwt.decode(token, key, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", str(e))
        return None


def get_token_identity(token: str) -> Optional[str]:
    """Get user ID from token."""
    payload = decode_token(token)
    if payload:
        return payload.get('sub')
    return None


def hash_refresh_token(token: str) -> str:
    """Digest a refresh token for storage.

    Refresh tokens were persisted verbatim, so any read of user_sessions --
    a backup, a dump, SQL injection elsewhere -- yielded live credentials
    (audit P0-14). Only the digest is stored now, and lookups compare
    digests.

    A plain SHA-256 is the right primitive here, unlike for passwords: the
    token is already long and uniformly random, so there is nothing to brute
    force and no reason to pay a slow KDF on every refresh.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    """Set httpOnly cookies for both access and refresh tokens, plus a CSRF token."""
    from app.core.security import generate_csrf_token, set_csrf_cookie

    common = dict(
        httponly=Config.COOKIE_HTTPONLY,
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

    # CSRF double-submit cookie (readable by JavaScript)
    set_csrf_cookie(response, generate_csrf_token())

    return response


def clear_auth_cookies(response):
    """Remove auth and CSRF cookies on logout."""
    common = dict(
        httponly=Config.COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )

    response.delete_cookie('access_token', **common)
    response.delete_cookie('refresh_token', **common)
    response.delete_cookie('csrf_token', path=COOKIE_PATH)
    return response
