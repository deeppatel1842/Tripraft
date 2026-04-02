"""
User Service
=============
Business logic for user profile management.
Auth operations (login/signup/tokens) live in AuthService.
"""
import logging
from typing import Optional

from app.core.exceptions import (AuthenticationError, NotFoundError,
                                 ValidationError)
from app.domain.users import User, UserRepository
from app.infrastructure.auth.password import (is_password_strong,
                                              verify_password)
from app.infrastructure.db import get_db

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user profile operations."""

    def get_user(self, user_id: str) -> dict:
        """Get user by ID."""
        with get_db() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError('User not found')
            return user.to_dict()

    def update_profile(self, user_id: str, **kwargs) -> dict:
        """Update user profile."""
        with get_db() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError('User not found')

            user = user_repo.update(user, **kwargs)
            return user.to_dict()

    def change_password(
        self, user_id: str, current_password: str, new_password: str
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
