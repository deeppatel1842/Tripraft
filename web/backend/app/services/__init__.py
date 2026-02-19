"""
Service layer -- orchestrates domain logic and infrastructure.
"""

from .user_service import UserService, user_service

__all__ = [
    "UserService",
    "user_service",
]
