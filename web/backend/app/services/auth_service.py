"""
Authentication Service
Handles user registration, login, logout, and token management
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.domain.expenses.models import User, UserSession
from app.infrastructure.auth.jwt import (create_access_token,
                                         create_refresh_token, decode_token,
                                         verify_token)
from app.infrastructure.auth.password import (hash_password,
                                              is_password_strong,
                                              verify_password)
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)

# Refresh token expiration (should match jwt_handler.py)
REFRESH_TOKEN_EXPIRES_DAYS = 30


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
        device_info: str = 'Web'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user and return tokens
        
        Args:
            email: User's email
            password: Plain text password
            device_info: Device/client information
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                # Find user by email
                user = session.query(User).filter(
                    User.email == email.lower()
                ).first()
                
                if not user:
                    return False, {'error': 'Invalid email or password'}
                
                # Check if user is active
                if not user.is_active:
                    return False, {'error': 'Account is deactivated'}
                
                # Verify password
                if not verify_password(password, user.password_hash):
                    return False, {'error': 'Invalid email or password'}
                
                # Generate tokens
                access_token = create_access_token(
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name
                )
                refresh_token = create_refresh_token(user_id=user.id)
                
                # Store refresh token session
                user_session = UserSession(
                    user_id=user.id,
                    refresh_token=refresh_token,
                    device_info=device_info,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
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
    def logout(user_id: int, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
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
    def logout_all_devices(user_id: int) -> Tuple[bool, Dict[str, Any]]:
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
            
            # Get user_id from payload (handle both old integer and new string format)
            user_id = payload.get('user_id') or int(payload.get('sub'))
            
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
                user_session.updated_at = datetime.now(timezone.utc)
                
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
    def get_current_user(user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get current authenticated user's profile
        
        Args:
            user_id: User ID from token
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                user = session.query(User).get(user_id)
                
                if not user:
                    return False, {'error': 'User not found'}
                
                if not user.is_active:
                    return False, {'error': 'Account is deactivated'}
                
                return True, {'user': user.to_dict()}
                
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return False, {'error': 'Failed to get user'}
    
    @staticmethod
    def update_profile(
        user_id: int,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
        photo_url: Optional[str] = None,
        default_currency: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update user profile
        
        Args:
            user_id: User ID
            display_name: New display name
            phone: New phone number
            photo_url: New photo URL
            default_currency: New default currency
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                user = session.query(User).get(user_id)
                
                if not user:
                    return False, {'error': 'User not found'}
                
                if display_name:
                    user.display_name = display_name.strip()
                if phone is not None:
                    user.phone = phone.strip() if phone else None
                if photo_url is not None:
                    user.photo_url = photo_url
                if default_currency:
                    user.default_currency = default_currency.upper()
                
                user.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(user)
                
                return True, {'user': user.to_dict()}
                
        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return False, {'error': 'Failed to update profile'}
    
    @staticmethod
    def change_password(
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Change user password
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            with get_db_session() as session:
                user = session.query(User).get(user_id)
                
                if not user:
                    return False, {'error': 'User not found'}
                
                # Verify current password
                if not verify_password(current_password, user.password_hash):
                    return False, {'error': 'Current password is incorrect'}
                
                # Validate new password strength
                is_strong, message = is_password_strong(new_password)
                if not is_strong:
                    return False, {'error': message}
                
                # Update password
                user.password_hash = hash_password(new_password)
                user.updated_at = datetime.now(timezone.utc)
                
                # Invalidate all other sessions (security)
                session.query(UserSession).filter(
                    UserSession.user_id == user_id
                ).delete()
                
                session.commit()
                
                logger.info(f"Password changed for user: {user.email}")
                return True, {'message': 'Password changed successfully. Please login again.'}
                
        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return False, {'error': 'Failed to change password'}
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get user by email address
        
        Args:
            email: User's email
            
        Returns:
            User object or None
        """
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
        """
        Check if email is already registered
        
        Args:
            email: Email to check
            
        Returns:
            True if email exists
        """
        try:
            with get_db_session() as session:
                exists = session.query(User).filter(
                    User.email == email.lower()
                ).first() is not None
                return exists
        except Exception as e:
            logger.error(f"Check email error: {str(e)}")
            return False


# Create singleton instance
auth_service = AuthService()
