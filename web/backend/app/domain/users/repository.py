"""
User Repository
================
Data access layer for User entities.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.auth.password import hash_password
from sqlalchemy.orm import Session

from .models import User, UserSession

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User data access operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._session.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        return self._session.query(User).filter(
            User.email == email.lower()
        ).first()

    def create(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> User:
        """
        Create a new user.
        
        Raises:
            ConflictError: If email already exists
        """
        email = email.lower().strip()
        
        if self.get_by_email(email):
            raise ConflictError(f'User with email {email} already exists')

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name or email.split('@')[0],
            phone=phone,
        )
        self._session.add(user)
        self._session.flush()
        logger.info('Created user: %s', email)
        return user

    def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ('id', 'email', 'password_hash'):
                setattr(user, key, value)
        user.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return user

    def update_password(self, user: User, new_password: str) -> None:
        """Update user password."""
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        logger.info('Password updated for user: %s', user.email)

    def update_last_login(self, user: User) -> None:
        """Update last login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        self._session.flush()

    def deactivate(self, user: User) -> None:
        """Deactivate a user account."""
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        logger.info('Deactivated user: %s', user.email)

    def delete(self, user: User) -> None:
        """Permanently delete a user (use with caution)."""
        email = user.email
        self._session.delete(user)
        self._session.flush()
        logger.warning('Deleted user: %s', email)


class UserSessionRepository:
    """Repository for UserSession data access operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        user_id: int,
        refresh_token: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserSession:
        """Create a new user session."""
        user_session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )
        self._session.add(user_session)
        self._session.flush()
        return user_session

    def get_by_token(self, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token."""
        return self._session.query(UserSession).filter(
            UserSession.refresh_token == refresh_token
        ).first()

    def get_active_sessions(self, user_id: int) -> list:
        """Get all active sessions for a user."""
        now = datetime.now(timezone.utc)
        return self._session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > now
        ).all()

    def update_last_used(self, session: UserSession) -> None:
        """Update last used timestamp."""
        session.last_used = datetime.now(timezone.utc)
        self._session.flush()

    def delete(self, session: UserSession) -> None:
        """Delete a session."""
        self._session.delete(session)
        self._session.flush()

    def delete_all_for_user(self, user_id: int) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        count = self._session.query(UserSession).filter(
            UserSession.user_id == user_id
        ).delete()
        self._session.flush()
        return count

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count deleted."""
        now = datetime.now(timezone.utc)
        count = self._session.query(UserSession).filter(
            UserSession.expires_at < now
        ).delete()
        self._session.flush()
        logger.info('Cleaned up %d expired sessions', count)
        return count
