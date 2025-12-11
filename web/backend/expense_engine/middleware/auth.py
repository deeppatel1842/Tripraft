"""
Authentication Middleware
JWT validation using Firebase Admin SDK
"""

from functools import wraps
from flask import request, g
from firebase_admin import auth as firebase_auth
import logging
import time
import threading

from ..exceptions import UnauthorizedError, ForbiddenError, InvalidTokenError

logger = logging.getLogger(__name__)

# Pre-warm debounce tracking (user_id -> last_prewarm_timestamp)
_prewarm_timestamps = {}
_prewarm_lock = threading.Lock()
PREWARM_DEBOUNCE_SECONDS = 30  # Only prewarm once per 30 seconds per user


def _should_prewarm(user_id: str) -> bool:
    """
    Check if we should pre-warm dashboard for this user.
    Implements debouncing to prevent multiple rapid pre-warm calls.
    """
    with _prewarm_lock:
        now = time.time()
        last_prewarm = _prewarm_timestamps.get(user_id, 0)
        
        if now - last_prewarm > PREWARM_DEBOUNCE_SECONDS:
            _prewarm_timestamps[user_id] = now
            return True
        return False


def require_auth(f):
    """
    Require valid Firebase JWT token
    Extracts user info and stores in g.current_user
    
    Usage:
        @require_auth
        def my_route():
            user = get_current_user()
            return jsonify({'uid': user['uid']})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("Missing Authorization header")
            raise UnauthorizedError("Missing authentication token")
        
        if not auth_header.startswith('Bearer '):
            logger.warning("Invalid Authorization header format")
            raise UnauthorizedError("Invalid authorization header format")
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify token with Firebase (allow 10s clock skew)
            decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=10)
            
            # Store user info in request context
            g.current_user = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture')
            }
            
            # Create/update user document in Firestore (async, don't block request)
            try:
                from firebase_admin import firestore
                db = firestore.client()
                
                # Extract name parts
                full_name = decoded_token.get('name', decoded_token.get('email', '').split('@')[0])
                name_parts = full_name.split(' ', 1) if full_name else ['', '']
                first_name = name_parts[0] if name_parts else None
                last_name = name_parts[1] if len(name_parts) > 1 else None
                
                # Check if user exists
                user_ref = db.collection('users').document(decoded_token['uid'])
                user_doc = user_ref.get()
                
                from datetime import datetime
                now = datetime.utcnow()
                
                if user_doc.exists:
                    # Update existing user
                    user_ref.update({
                        'last_login': now.isoformat(),
                        'email': decoded_token.get('email', ''),
                        'display_name': full_name
                    })
                else:
                    # Create new user
                    user_ref.set({
                        'uid': decoded_token['uid'],
                        'email': decoded_token.get('email', ''),
                        'display_name': full_name,
                        'first_name': first_name,
                        'last_name': last_name,
                        'photo_url': decoded_token.get('picture'),
                        'email_verified': decoded_token.get('email_verified', False),
                        'created_at': now.isoformat(),
                        'last_login': now.isoformat()
                    })
            except Exception as user_exc:
                # Don't fail the request if user doc creation fails
                logger.warning(f"Failed to create/update user document: {user_exc}")
            
            # Phase 20.3: Pre-warm dashboard cache on login (background thread)
            # With debouncing to prevent multiple rapid pre-warm calls
            try:
                if _should_prewarm(decoded_token['uid']):
                    from ..services.bootstrap_service import get_bootstrap_service
                    bootstrap_service = get_bootstrap_service()
                    bootstrap_service.prewarm_dashboard(
                        user_id=decoded_token['uid'],
                        user_email=decoded_token.get('email', ''),
                        background=True  # Don't block auth response
                    )
                else:
                    logger.debug("Dashboard pre-warm debounced for user: %s", decoded_token['uid'])
            except Exception as prewarm_exc:
                # Pre-warming failure should not affect authentication
                logger.debug("Dashboard pre-warm skipped: %s", prewarm_exc)
            
            logger.debug("Authenticated user: %s", g.current_user['uid'])
            
        except firebase_auth.ExpiredIdTokenError as exc:
            logger.warning("Expired Firebase token")
            raise InvalidTokenError("Authentication token expired") from exc
        except firebase_auth.RevokedIdTokenError as exc:
            logger.warning("Revoked Firebase token")
            raise InvalidTokenError("Authentication token has been revoked") from exc
        except firebase_auth.InvalidIdTokenError as exc:
            logger.warning("Invalid Firebase token")
            raise InvalidTokenError("Invalid authentication token") from exc
        except Exception as exc:
            logger.error("Token verification error: %s", str(exc))
            raise UnauthorizedError("Authentication failed") from exc
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """
    Get current authenticated user from request context
    
    Returns:
        dict: User info with keys: uid, email, email_verified, name, picture
    
    Raises:
        UnauthorizedError: If no authenticated user in context
    """
    if not hasattr(g, 'current_user'):
        raise UnauthorizedError("No authenticated user")
    return g.current_user


def get_current_user_id():
    """
    Get current user's UID
    
    Returns:
        str: User ID
    
    Raises:
        UnauthorizedError: If no authenticated user
    """
    user = get_current_user()
    return user['uid']


def require_group_member(group_id_param='group_id'):
    """
    Require user to be a member of the specified group
    
    Args:
        group_id_param: Name of the parameter containing group_id
                       Can be in kwargs or request.view_args
    
    Usage:
        @require_auth
        @require_group_member('group_id')
        def my_route(group_id):
            # User is authenticated and a member of the group
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # GroupService will be implemented in Phase 4
            # For now, allow all authenticated users (will be restricted in Phase 4)
            current_user = get_current_user()
            group_id = kwargs.get(group_id_param) or request.view_args.get(group_id_param)
            
            if not group_id:
                raise ForbiddenError("Group ID required")
            
            # TODO Phase 4: Check membership using GroupService
            # group_service = GroupService()
            # if not group_service.is_member(group_id, current_user['uid']):
            #     raise ForbiddenError("You are not a member of this group")
            logger.debug("Group membership check placeholder (Phase 4): user=%s, group=%s", 
                        current_user['uid'], group_id)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def optional_auth(f):
    """
    Optional authentication - doesn't fail if no token provided
    If token is provided, it must be valid
    
    Usage:
        @optional_auth
        def my_route():
            if hasattr(g, 'current_user'):
                # User is authenticated
                pass
            else:
                # Anonymous user
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            # No auth header - allow through as anonymous
            return f(*args, **kwargs)
        
        if not auth_header.startswith('Bearer '):
            # Invalid format - allow through as anonymous
            return f(*args, **kwargs)
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            g.current_user = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture')
            }
        except (firebase_auth.InvalidIdTokenError, 
                firebase_auth.ExpiredIdTokenError,
                firebase_auth.RevokedIdTokenError) as exc:
            # Invalid token - allow through as anonymous
            logger.debug("Optional auth failed: %s", str(exc))
        
        return f(*args, **kwargs)
    
    return decorated_function
