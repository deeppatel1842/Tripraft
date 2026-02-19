"""
Unified Authentication Decorators
Single source of truth for route-protection across the entire backend.

Supports:
  * SQL JWT tokens  (primary)
  * Firebase ID tokens  (fallback for legacy clients)

Every decorator sets a consistent set of Flask `g` attributes:
    g.current_user   dict  {'id': int, 'email': str, 'name': str}
    g.user_id         int   convenience alias
    g.user_email      str   convenience alias
    g.token_payload   dict  raw JWT payload (None for Firebase tokens)

Moved from shared_db/auth.py — now lives in infrastructure/auth/.
"""

import logging
from functools import wraps
from typing import Any, Dict, Optional

from flask import g, jsonify, request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def get_token_from_header() -> Optional[str]:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1]


def get_access_token() -> Optional[str]:
    """
    Resolve the access token using two sources (in priority order):
      1. Authorization: Bearer header  (explicit API calls)
      2. httpOnly cookie ``access_token``  (browser sessions)
    """
    header_token = get_token_from_header()
    if header_token:
        return header_token
    return request.cookies.get('access_token')


def get_refresh_token_value() -> Optional[str]:
    """
    Resolve the refresh token:
      1. httpOnly cookie ``refresh_token``
      2. Authorization: Bearer header (legacy)
    """
    cookie_token = request.cookies.get('refresh_token')
    if cookie_token:
        return cookie_token
    return get_token_from_header()


def _decode_jwt(token: str) -> Optional[Dict]:
    """Decode a SQL JWT token."""
    try:
        from app.infrastructure.auth.jwt import decode_token
        return decode_token(token)
    except ImportError:
        logger.warning("app.infrastructure.auth.jwt not available")
        return None


def _verify_firebase_token(token: str) -> Optional[Dict]:
    """Verify a Firebase ID token and return normalised user info."""
    try:
        from firebase_admin import auth as firebase_auth
        decoded = firebase_auth.verify_id_token(token)
        return {
            'id': decoded.get('uid'),
            'email': decoded.get('email'),
            'name': decoded.get('name', decoded.get('email', 'User')),
        }
    except Exception as e:
        logger.debug("Not a Firebase token: %s", e)
        return None


def _ensure_user_exists(user_id: int, email: str, name: Optional[str] = None) -> bool:
    """Make sure a User row exists in the shared database."""
    try:
        from app.domain.users.models import User
        from app.infrastructure.db.connection import get_db_session

        session = get_db_session()
        try:
            user = session.query(User).get(user_id)
            if user:
                return True

            logger.warning("User %s not in DB, creating...", user_id)
            session.add(User(
                id=user_id,
                email=email,
                display_name=name or email.split('@')[0],
                password_hash='',
                is_active=True,
                email_verified=True,
            ))
            session.commit()
            return True
        finally:
            session.close()
    except Exception as e:
        logger.error("Error in _ensure_user_exists: %s", e)
        return False


# ---------------------------------------------------------------------------
# Core decorators
# ---------------------------------------------------------------------------

def require_auth(f):
    """
    Require a valid JWT (or Firebase) token.

    On success the decorated route will have access to:
        g.current_user   {'id', 'email', 'name'}
        g.user_id        int
        g.user_email     str
        g.token_payload  dict | None
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 200

        token = get_access_token()
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authorization token required',
            }), 401

        user_info = None

        # 1. SQL JWT (primary path)
        payload = _decode_jwt(token)
        if payload and payload.get('type') == 'access':
            uid = payload.get('user_id', int(payload.get('sub', 0)))
            user_info = {
                'id': uid,
                'email': payload.get('email'),
                'name': payload.get('name', payload.get('display_name', '')),
            }
            g.token_payload = payload
        else:
            # 2. Firebase fallback
            fb_user = _verify_firebase_token(token)
            if fb_user:
                user_info = fb_user
                g.token_payload = None

        if not user_info:
            logger.warning("Token verification failed: %s...", token[:20])
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
            }), 401

        # Ensure the user row exists
        if not _ensure_user_exists(
            user_info['id'],
            user_info.get('email', ''),
            user_info.get('name'),
        ):
            return jsonify({
                'success': False,
                'error': 'Failed to initialise user',
            }), 500

        # Set standardised g attributes
        g.current_user = user_info
        g.user_id = user_info['id']
        g.user_email = user_info.get('email', '')

        return f(*args, **kwargs)
    return decorated


def require_refresh_token(f):
    """Decorator for routes that need a *refresh* token (e.g. /auth/refresh)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_refresh_token_value()
        if not token:
            return jsonify({
                'success': False,
                'error': 'Refresh token required',
            }), 401

        try:
            from app.infrastructure.auth.jwt import decode_token, verify_token
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Auth module unavailable',
            }), 500

        if not verify_token(token, token_type='refresh'):
            return jsonify({
                'success': False,
                'error': 'Invalid or expired refresh token',
            }), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid token payload',
            }), 401

        uid = payload.get('sub')
        g.current_user = {'id': uid}
        g.user_id = uid
        g.user_email = payload.get('email', '')
        g.token_payload = payload
        g.refresh_token = token

        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Allow both authenticated and unauthenticated requests."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_access_token()
        if token:
            payload = _decode_jwt(token)
            if payload and payload.get('type') == 'access':
                uid = payload.get('user_id', int(payload.get('sub', 0)))
                g.current_user = {
                    'id': uid,
                    'email': payload.get('email'),
                    'name': payload.get('name', ''),
                }
                g.user_id = uid
                g.user_email = payload.get('email', '')
                g.token_payload = payload
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Accessor helpers
# ---------------------------------------------------------------------------

def get_current_user() -> Optional[Dict[str, Any]]:
    """Return the current authenticated user dict, or None."""
    return getattr(g, 'current_user', None)


def get_current_user_id() -> Optional[int]:
    """Return the current authenticated user's numeric ID, or None."""
    user = get_current_user()
    return user.get('id') if user else None
