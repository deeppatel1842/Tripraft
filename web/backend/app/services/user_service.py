"""
User Service
=============
Business logic for user authentication and management.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from app.core.exceptions import (AuthenticationError, ConflictError,
                                 NotFoundError, ValidationError)
from app.domain.users import (User, UserRepository, UserSession,
                              UserSessionRepository)
from app.infrastructure.auth.jwt import (ACCESS_TOKEN_EXPIRES,
                                         REFRESH_TOKEN_EXPIRES,
                                         create_access_token,
                                         create_refresh_token, decode_token)
from app.infrastructure.auth.password import (is_password_strong,
                                              verify_password)
from app.infrastructure.db import get_db

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user operations."""

    def register(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> dict:
        """
        Register a new user.
        
        Returns:
            User data with tokens
            
        Raises:
            ValidationError: If password is weak
            ConflictError: If email already exists
        """
        # Validate password strength
        is_strong, error_msg = is_password_strong(password)
        if not is_strong:
            raise ValidationError(error_msg)

        with get_db() as session:
            user_repo = UserRepository(session)
            session_repo = UserSessionRepository(session)

            # Create user
            user = user_repo.create(
                email=email,
                password=password,
                display_name=display_name,
                phone=phone,
            )

            # Create tokens
            access_token = create_access_token(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
            )
            refresh_token = create_refresh_token(user_id=user.id)

            # Save session
            expires_at = datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRES
            session_repo.create(
                user_id=user.id,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

            logger.info('Registered user: %s', email)
            return {
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token,
            }

    def login(
        self,
        email: str,
        password: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Authenticate user and return tokens.
        
        Returns:
            User data with tokens
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        with get_db() as session:
            user_repo = UserRepository(session)
            session_repo = UserSessionRepository(session)

            user = user_repo.get_by_email(email)
            if not user or not verify_password(password, user.password_hash):
                raise AuthenticationError('Invalid email or password')

            if not user.is_active:
                raise AuthenticationError('Account is deactivated')

            # Update last login
            user_repo.update_last_login(user)

            # Create tokens
            access_token = create_access_token(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
            )
            refresh_token = create_refresh_token(user_id=user.id)

            # Save session
            expires_at = datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRES
            session_repo.create(
                user_id=user.id,
                refresh_token=refresh_token,
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address,
            )

            logger.info('User logged in: %s', email)
            return {
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token,
            }

    def refresh_tokens(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.
        
        Returns:
            New access and refresh tokens
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        payload = decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            raise AuthenticationError('Invalid refresh token')

        user_id = payload.get('user_id')

        with get_db() as session:
            user_repo = UserRepository(session)
            session_repo = UserSessionRepository(session)

            # Verify session exists
            user_session = session_repo.get_by_token(refresh_token)
            if not user_session:
                raise AuthenticationError('Session not found')

            # Check expiry (compare naive datetimes — SQLite stores without tz)
            if user_session.expires_at < datetime.utcnow():
                session_repo.delete(user_session)
                raise AuthenticationError('Session expired')

            user = user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise AuthenticationError('User not found or inactive')

            # Rotate refresh token
            session_repo.delete(user_session)

            new_access_token = create_access_token(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
            )
            new_refresh_token = create_refresh_token(user_id=user.id)

            expires_at = datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRES
            session_repo.create(
                user_id=user.id,
                refresh_token=new_refresh_token,
                expires_at=expires_at,
            )

            return {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
            }

    def logout(self, refresh_token: str) -> bool:
        """Invalidate a refresh token (logout)."""
        with get_db() as session:
            session_repo = UserSessionRepository(session)
            user_session = session_repo.get_by_token(refresh_token)
            if user_session:
                session_repo.delete(user_session)
                return True
            return False

    def logout_all(self, user_id: int) -> int:
        """Invalidate all sessions for a user. Returns count."""
        with get_db() as session:
            session_repo = UserSessionRepository(session)
            count = session_repo.delete_all_for_user(user_id)
            logger.info('Logged out %d sessions for user %d', count, user_id)
            return count

    def get_user(self, user_id: int) -> dict:
        """Get user by ID."""
        with get_db() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError('User not found')
            return user.to_dict()

    def update_profile(self, user_id: int, **kwargs) -> dict:
        """Update user profile."""
        with get_db() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError('User not found')

            user = user_repo.update(user, **kwargs)
            return user.to_dict()

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """
        Change user password.
        
        Raises:
            AuthenticationError: If current password is wrong
            ValidationError: If new password is weak
        """
        is_strong, error_msg = is_password_strong(new_password)
        if not is_strong:
            raise ValidationError(error_msg)

        with get_db() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError('User not found')

            if not verify_password(current_password, user.password_hash):
                raise AuthenticationError('Current password is incorrect')

            user_repo.update_password(user, new_password)
            return True


# Singleton instance
user_service = UserService()
