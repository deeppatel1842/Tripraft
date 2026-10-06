# Purpose: Password Hashing Utilities Uses bcrypt for secure password hashing.
"""
Password Hashing Utilities
Uses bcrypt for secure password hashing.

Moved from expense_engine/auth/password.py — now in infrastructure.
"""

import logging

import bcrypt
from app.core.config import Config

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8'),
        )
    except Exception as e:
        logger.error("Password verification error: %s", str(e))
        return False


def is_password_strong(password: str) -> tuple[bool, str]:
    """
    Check if password meets strength requirements.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        Tuple of (is_strong, error_message)
    """
    if len(password) < Config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {Config.PASSWORD_MIN_LENGTH} characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    special_chars = Config.PASSWORD_SPECIAL_CHARS
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, ""
