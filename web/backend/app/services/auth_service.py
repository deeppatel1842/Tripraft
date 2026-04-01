"""
Authentication Service
Handles user registration, login, logout, and token management.

Profile operations (get_current_user, update_profile, change_password)
are delegated to UserService — single source of truth for user data.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.config import Config
from app.domain.expenses.models import User, UserSession
from app.infrastructure.auth.jwt import (create_access_token,
                                         create_email_verification_token,
                                         create_refresh_token, decode_token,
                                         verify_token)
from app.infrastructure.auth.password import (hash_password,
                                              is_password_strong,
                                              verify_password)
from app.infrastructure.cache.redis import (check_lockout, clear_lockout,
                                            record_failed_login)
from app.infrastructure.db.connection import get_db_session
from app.infrastructure.email.smtp import email_service

logger = logging.getLogger(__name__)

# Refresh token expiration — derived from Config (seconds → days)
_REFRESH_TOKEN_EXPIRES_SECONDS = Config.JWT_REFRESH_TOKEN_EXPIRES
REFRESH_TOKEN_EXPIRES_DAYS = _REFRESH_TOKEN_EXPIRES_SECONDS // 86400


class AuthService:
    """Service for handling authentication operations"""
    
    @staticmethod
    def signup(
        email: str,
        password: str,
        display_name: str,
        phone: Optional[str] = None,
        default_currency: str = 'INR'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Register a new user
        
        Args:
            email: User's email address
            password: Plain text password
            display_name: User's display name
            phone: Optional phone number
            default_currency: Default currency code
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                # Check if email already exists
                existing_user = session.query(User).filter(
                    User.email == email.lower()
                ).first()
                
                if existing_user:
                    return False, {'error': 'Email already registered'}
                
                # Validate password strength
                is_strong, message = is_password_strong(password)
                if not is_strong:
                    return False, {'error': message}
                
                # Create new user
                user = User(
                    email=email.lower().strip(),
                    password_hash=hash_password(password),
                    display_name=display_name.strip(),
                    phone=phone.strip() if phone else None,
                    default_currency=default_currency.upper()
                )
                
                session.add(user)
                session.commit()
                session.refresh(user)
                
                # Generate tokens
                access_token = create_access_token(
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name
                )
                refresh_token = create_refresh_token(user_id=user.id)
                
                # Store refresh token in session
                user_session = UserSession(
                    user_id=user.id,
                    refresh_token=refresh_token,
                    device_info='Web',
                    expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
                )
                session.add(user_session)
                session.commit()
                
                # Send verification email (best-effort, don't block signup)
                try:
                    vtoken = create_email_verification_token(user.id, user.email)
                    email_service.send_verification(user.email, vtoken)
                except Exception as ve:
                    logger.warning("Failed to send verification email: %s", ve)
                
                logger.info(f"New user registered: {user.email}")
                
                return True, {
                    'user': user.to_dict(),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer'
                }
                
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            return False, {'error': 'Registration failed. Please try again.'}
    
    @staticmethod
    def login(
        email: str,
        password: str,
        device_info: str = 'Web',
        client_ip: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user and return tokens
        
        Args:
            email: User's email
            password: Plain text password
            device_info: Device/client information
            client_ip: Client IP address for lockout tracking
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            # Check lockout before hitting the database
            remaining = check_lockout(email, ip=client_ip)
            if remaining is not None:
                minutes = max(1, remaining // 60)
                return False, {
                    'error': f'Account locked. Try again in {minutes} minute(s).',
                    'locked': True,
                    'retry_after': remaining,
                }

            with get_db_session() as session:
                # Find user by email
                user = session.query(User).filter(
                    User.email == email.lower()
                ).first()
                
                if not user:
                    record_failed_login(email, ip=client_ip)
                    return False, {'error': 'Invalid email or password'}
                
                # Check if user is active
                if not user.is_active:
                    return False, {'error': 'Account is deactivated'}
                
                # Verify password
                if not verify_password(password, user.password_hash):
                    count = record_failed_login(email, ip=client_ip)
                    logger.warning("Failed login for %s (attempt %d)", email, count)
                    return False, {'error': 'Invalid email or password'}
                
                # Successful authentication — clear any lockout counter
                clear_lockout(email)
                
                # Generate tokens
                access_token = create_access_token(
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name
                )
                refresh_token = create_refresh_token(user_id=user.id)
                
                # ── Session limit enforcement (FIFO eviction) ──────────
                now = datetime.now(timezone.utc)
                max_sessions = Config.MAX_SESSIONS_PER_USER

                active_sessions = (
                    session.query(UserSession)
                    .filter(
                        UserSession.user_id == user.id,
                        UserSession.expires_at > now,
                    )
                    .order_by(UserSession.last_used.asc().nullsfirst(), UserSession.created_at.asc())
                    .all()
                )

                # Evict oldest sessions to make room (keep max_sessions - 1)
                overflow = len(active_sessions) - (max_sessions - 1)
                if overflow > 0:
                    for stale in active_sessions[:overflow]:
                        logger.info(
                            "Evicting oldest session %d for user %d (device=%s)",
                            stale.id, user.id, stale.device_info,
                        )
                        session.delete(stale)

                # Store refresh token session
                user_session = UserSession(
                    user_id=user.id,
                    refresh_token=refresh_token,
                    device_info=device_info,
                    ip_address=client_ip,
                    last_used=now,
                    expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS),
                )
                session.add(user_session)
                
                # Update last login
                user.last_login = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"User logged in: {user.email}")
                
                return True, {
                    'user': user.to_dict(),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer'
                }
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, {'error': 'Login failed. Please try again.'}
    
    @staticmethod
    def logout(user_id: str, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Logout user by invalidating refresh token
        
        Args:
            user_id: Current user ID
            refresh_token: Refresh token to invalidate
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                # Find and delete the session
                user_session = session.query(UserSession).filter(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token
                ).first()
                
                if user_session:
                    session.delete(user_session)
                    session.commit()
                
                logger.info(f"User logged out: {user_id}")
                return True, {'message': 'Logged out successfully'}
                
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False, {'error': 'Logout failed'}
    
    @staticmethod
    def logout_all_devices(user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Logout user from all devices by invalidating all refresh tokens
        
        Args:
            user_id: Current user ID
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                session.query(UserSession).filter(
                    UserSession.user_id == user_id
                ).delete()
                session.commit()
                
                logger.info(f"User logged out from all devices: {user_id}")
                return True, {'message': 'Logged out from all devices'}
                
        except Exception as e:
            logger.error(f"Logout all error: {str(e)}")
            return False, {'error': 'Logout failed'}
    
    @staticmethod
    def refresh_tokens(refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            # Verify refresh token
            if not verify_token(refresh_token, token_type='refresh'):
                return False, {'error': 'Invalid or expired refresh token'}
            
            payload = decode_token(refresh_token)
            if not payload:
                return False, {'error': 'Invalid token'}
            
            # Get user_id from payload
            user_id = payload.get('sub')
            
            with get_db_session() as session:
                # Verify session exists
                user_session = session.query(UserSession).filter(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token
                ).first()
                
                if not user_session:
                    return False, {'error': 'Session not found or expired'}
                
                # Check if session is still valid
                # Handle offset-naive datetimes from SQLite by adding UTC timezone
                expires_at = user_session.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                if expires_at < datetime.now(timezone.utc):
                    session.delete(user_session)
                    session.commit()
                    return False, {'error': 'Session expired'}
                
                # Get user
                user = session.query(User).get(user_id)
                if not user or not user.is_active:
                    return False, {'error': 'User not found or inactive'}
                
                # Generate new tokens
                new_access_token = create_access_token(
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name
                )
                new_refresh_token = create_refresh_token(user_id=user.id)
                
                # Update session with new refresh token
                user_session.refresh_token = new_refresh_token
                user_session.last_used = datetime.now(timezone.utc)
                
                session.commit()
                
                return True, {
                    'access_token': new_access_token,
                    'refresh_token': new_refresh_token,
                    'token_type': 'Bearer'
                }
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False, {'error': 'Token refresh failed'}

    @staticmethod
    def verify_email(token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a user's email using the verification token.

        Args:
            token: JWT verification token (type=email_verify)

        Returns:
            Tuple of (success, data/error)
        """
        payload = decode_token(token)
        if not payload or payload.get('type') != 'email_verify':
            return False, {'error': 'Invalid or expired verification link'}

        user_id = payload.get('sub')
        if not user_id:
            return False, {'error': 'Invalid token payload'}

        try:
            with get_db_session() as session:
                user = session.query(User).get(user_id)
                if not user:
                    return False, {'error': 'User not found'}

                if user.email_verified:
                    return True, {'message': 'Email already verified'}

                user.email_verified = True
                user.email_verified_at = datetime.now(timezone.utc)
                session.commit()

                logger.info("Email verified for user %s", user.email)
                return True, {'message': 'Email verified successfully'}
        except Exception as e:
            logger.error("Email verification error: %s", e)
            return False, {'error': 'Verification failed'}

    @staticmethod
    def resend_verification(user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Resend the verification email for the given user.

        Args:
            user_id: Authenticated user's ID

        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                user = session.query(User).get(user_id)
                if not user:
                    return False, {'error': 'User not found'}

                if user.email_verified:
                    return True, {'message': 'Email already verified'}

                vtoken = create_email_verification_token(user.id, user.email)
                sent = email_service.send_verification(user.email, vtoken)
                if not sent:
                    return False, {'error': 'Failed to send verification email'}

                return True, {'message': 'Verification email sent'}
        except Exception as e:
            logger.error("Resend verification error: %s", e)
            return False, {'error': 'Failed to resend verification email'}
    
    # ------------------------------------------------------------------
    # Profile operations — delegated to UserService (single source of truth)
    # ------------------------------------------------------------------

    @staticmethod
    def get_current_user(user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get current authenticated user's profile."""
        try:
            from app.services.user_service import user_service
            user_data = user_service.get_user(user_id)
            return True, {'user': user_data}
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return False, {'error': str(e) if 'not found' in str(e).lower() else 'Failed to get user'}

    @staticmethod
    def update_profile(
        user_id: str,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
        photo_url: Optional[str] = None,
        default_currency: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Update user profile."""
        try:
            from app.services.user_service import user_service
            kwargs = {}
            if display_name is not None:
                kwargs['display_name'] = display_name.strip()
            if phone is not None:
                kwargs['phone'] = phone.strip() if phone else None
            if photo_url is not None:
                kwargs['photo_url'] = photo_url
            if default_currency is not None:
                kwargs['default_currency'] = default_currency.upper()
            user_data = user_service.update_profile(user_id, **kwargs)
            return True, {'user': user_data}
        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return False, {'error': 'Failed to update profile'}

    @staticmethod
    def change_password(
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Change user password."""
        try:
            from app.services.user_service import user_service
            user_service.change_password(user_id, current_password, new_password)
            return True, {'message': 'Password changed successfully. Please login again.'}
        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return False, {'error': str(e) if 'incorrect' in str(e).lower() or 'weak' in str(e).lower() else 'Failed to change password'}

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            with get_db_session() as session:
                return session.query(User).filter(
                    User.email == email.lower()
                ).first()
        except Exception as e:
            logger.error(f"Get user by email error: {str(e)}")
            return None

    @staticmethod
    def check_email_exists(email: str) -> bool:
        """Check if email is already registered."""
        try:
            with get_db_session() as session:
                return session.query(User).filter(
                    User.email == email.lower()
                ).first() is not None
        except Exception as e:
            logger.error(f"Check email error: {str(e)}")
            return False


# Create singleton instance
auth_service = AuthService()
