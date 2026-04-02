"""
Unified Authentication Decorators
Single source of truth for route-protection across the entire backend.

Every decorator sets a consistent set of Flask `g` attributes:
    g.current_user   dict  {'id': str, 'email': str, 'name': str}
    g.user_id         str   convenience alias (UUIDv7)
    g.user_email      str   convenience alias
    g.token_payload   dict  raw JWT payload
"""

import logging
import uuid as _uuid
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


def _ensure_user_exists(user_id: str, email: str, name: Optional[str] = None) -> bool:
    """Verify that a User row exists in the shared database. Returns False (401) if not found."""
    try:
        from app.domain.users.models import User
        from app.infrastructure.db.connection import get_db_session

        uid = _uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        session = get_db_session()
        try:
            user = session.query(User).get(uid)
            if user:
                return True
            logger.warning("User %s not found in DB -- rejecting request", user_id)
            return False
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
    Require a valid JWT token.

    On success the decorated route will have access to:
        g.current_user   {'id', 'email', 'name'}
        g.user_id        str
        g.user_email     str
        g.token_payload  dict
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

        payload = _decode_jwt(token)
        if payload and payload.get('type') == 'access':
            uid = payload.get('sub')
            user_info = {
                'id': uid,
                'email': payload.get('email'),
                'name': payload.get('name', payload.get('display_name', '')),
            }
            g.token_payload = payload

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
        g.user_id = _uuid.UUID(user_info['id']) if isinstance(user_info['id'], str) else user_info['id']
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
        g.user_id = _uuid.UUID(uid) if isinstance(uid, str) else uid
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
                uid = payload.get('sub')
                g.current_user = {
                    'id': uid,
                    'email': payload.get('email'),
                    'name': payload.get('name', ''),
                }
                g.user_id = _uuid.UUID(uid) if isinstance(uid, str) else uid
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


def get_current_user_id():
    """Return the current authenticated user's UUID, or None."""
    return getattr(g, 'user_id', None)


# ---------------------------------------------------------------------------
# Admin role enforcement
# ---------------------------------------------------------------------------

def require_admin(f):
    """
    Decorator that must be stacked AFTER require_auth.
    Checks that the authenticated user's email is in ADMIN_EMAILS.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.core.config import Config
        email = getattr(g, 'user_email', '')
        if not email or email not in Config.ADMIN_EMAILS:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Group-level RBAC
# ---------------------------------------------------------------------------

# Role hierarchy (higher index = more privilege)
_ROLE_RANK = {'viewer': 0, 'member': 1, 'admin': 2, 'creator': 3}


def require_group_role(min_role='member'):
    """
    Decorator that must be stacked AFTER require_auth.
    Checks that the authenticated user has at least *min_role* in the group
    identified by the ``group_id`` URL parameter.

    Sets ``g.member_role`` for downstream use.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app.domain.group_planner.models import TripMember
            from app.infrastructure.db.connection import get_db_session

            group_id = kwargs.get('group_id')
            if group_id is None:
                return jsonify({'success': False, 'error': 'group_id required'}), 400

            user_id = getattr(g, 'user_id', None)
            if user_id is None:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401

            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()

                if not member:
                    return jsonify({'success': False, 'error': 'Not a member of this group'}), 403

                actual_rank = _ROLE_RANK.get(member.role, 0)
                required_rank = _ROLE_RANK.get(min_role, 1)

                if actual_rank < required_rank:
                    return jsonify({
                        'success': False,
                        'error': f'{min_role} role or higher required'
                    }), 403

                g.member_role = member.role

            return f(*args, **kwargs)
        return decorated
    return decorator
