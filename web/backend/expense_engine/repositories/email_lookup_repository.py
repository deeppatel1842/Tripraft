"""
Email Lookup Repository
Phase 19.2: Fast email -> userId lookup

This collection provides O(1) lookup for user by email address,
eliminating the need for expensive WHERE queries on the users collection.

Collection: user_emails
Document ID: normalized email (lowercase, trimmed)
Document structure:
{
    "user_id": "abc123",
    "display_name": "John Doe",
    "photo_url": "https://...",
    "created_at": "2025-12-03T10:00:00Z",
    "updated_at": "2025-12-03T10:00:00Z"
}
"""

from typing import Optional, Dict
from datetime import datetime
import logging

from .base import BaseRepository
from ..config import firestore_collections

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """
    Normalize email for use as document ID.
    
    - Lowercase
    - Strip whitespace
    - Replace special characters that are invalid in Firestore doc IDs
    
    Args:
        email: Raw email address
        
    Returns:
        Normalized email suitable for document ID
    """
    if not email:
        return ""
    # Lowercase and strip
    normalized = email.strip().lower()
    # Firestore doc IDs cannot contain '/' - replace with '__'
    normalized = normalized.replace('/', '__')
    return normalized


class EmailLookupRepository(BaseRepository[Dict]):
    """
    Repository for email -> userId lookup documents.
    
    Phase 19.2: Provides O(1) lookup by email instead of collection query.
    
    This dramatically reduces Firestore reads in invitation flow:
    - Before: Query users collection WHERE email == x (1+ reads)
    - After: Direct document read by email (1 read, cached)
    """
    
    def get_collection_name(self) -> str:
        """Return collection name"""
        return firestore_collections.USER_EMAILS
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user info by email address (O(1) lookup).
        
        Args:
            email: User email address
            
        Returns:
            Dict with user_id, display_name, photo_url or None if not found
        """
        normalized = normalize_email(email)
        if not normalized:
            return None
        
        try:
            result = self.get_by_id(normalized)
            if result:
                logger.debug("Email lookup HIT: %s -> %s", email, result.get('user_id'))
            else:
                logger.debug("Email lookup MISS: %s", email)
            return result
        except Exception as e:
            logger.warning("Email lookup error for %s: %s", email, e)
            return None
    
    def set_user_email(
        self,
        email: str,
        user_id: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None
    ) -> bool:
        """
        Create or update email -> userId mapping.
        
        Should be called:
        - When a new user registers
        - When user updates their profile (display_name, photo)
        
        Args:
            email: User email address
            user_id: Firebase user ID
            display_name: User's display name
            photo_url: User's profile photo URL
            
        Returns:
            True if successful, False otherwise
        """
        normalized = normalize_email(email)
        if not normalized or not user_id:
            logger.warning("Cannot set email lookup: invalid email or user_id")
            return False
        
        try:
            now = datetime.utcnow().isoformat()
            
            # Check if exists to determine created_at
            existing = self.get_by_id(normalized)
            
            data = {
                'user_id': user_id,
                'display_name': display_name or '',
                'photo_url': photo_url or '',
                'updated_at': now
            }
            
            if existing:
                # Update - preserve created_at
                data['created_at'] = existing.get('created_at', now)
                self.update(normalized, data)
                logger.info("Updated email lookup: %s -> %s", email, user_id)
            else:
                # Create new
                data['created_at'] = now
                self.create(normalized, data)
                logger.info("Created email lookup: %s -> %s", email, user_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to set email lookup for %s: %s", email, e)
            return False
    
    def delete_user_email(self, email: str) -> bool:
        """
        Remove email -> userId mapping.
        
        Should be called when:
        - User changes their email address (delete old, create new)
        - User account is deleted
        
        Args:
            email: Email address to remove
            
        Returns:
            True if successful, False otherwise
        """
        normalized = normalize_email(email)
        if not normalized:
            return False
        
        try:
            self.delete(normalized)
            logger.info("Deleted email lookup: %s", email)
            return True
        except Exception as e:
            logger.warning("Failed to delete email lookup for %s: %s", email, e)
            return False
    
    def bulk_create_from_users(self, users: list) -> int:
        """
        Bulk create email lookup documents from existing users.
        
        Used for initial migration to populate the collection.
        
        Args:
            users: List of user dicts with email, uid/id, display_name, photo_url
            
        Returns:
            Number of documents created
        """
        count = 0
        for user in users:
            email = user.get('email')
            user_id = user.get('uid') or user.get('id')
            display_name = user.get('display_name', '')
            photo_url = user.get('photo_url', '')
            
            if email and user_id:
                if self.set_user_email(email, user_id, display_name, photo_url):
                    count += 1
        
        logger.info("Bulk created %d email lookup documents", count)
        return count
