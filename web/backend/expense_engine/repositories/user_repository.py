"""
User Repository
Data access layer for users collection
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[Dict[str, Any]]):
    """Repository for user documents in Firestore"""
    
    def get_collection_name(self) -> str:
        """Return collection name for users"""
        return 'users'
    
    def create_or_update_user(
        self,
        uid: str,
        email: str,
        display_name: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        email_verified: bool = False
    ) -> Dict:
        """
        Create or update user document
        
        Args:
            uid: Firebase user ID
            email: User email
            display_name: Display name
            first_name: First name (optional)
            last_name: Last name (optional)
            photo_url: Profile photo URL (optional)
            email_verified: Email verification status
            
        Returns:
            User document dict
        """
        # Check if user exists
        existing = self.get_by_id(uid)
        
        now = datetime.utcnow()
        
        if existing:
            # Update existing user
            update_data = {
                'email': email,
                'display_name': display_name,
                'last_login': now.isoformat(),
                'email_verified': email_verified
            }
            
            # Update optional fields only if provided
            if first_name:
                update_data['first_name'] = first_name
            if last_name:
                update_data['last_name'] = last_name
            if photo_url:
                update_data['photo_url'] = photo_url
            
            self.update(uid, update_data)
            logger.info("Updated user: %s (%s)", uid, email)
            
            # Phase 19.2: Update email lookup collection
            self._update_email_lookup(uid, email, display_name, photo_url)
            
            # Return updated document
            return self.get_by_id(uid)
        
        # Create new user
        user_dict = {
            'uid': uid,
            'email': email,
            'display_name': display_name,
            'first_name': first_name,
            'last_name': last_name,
            'photo_url': photo_url,
            'email_verified': email_verified,
            'created_at': now.isoformat(),
            'last_login': now.isoformat()
        }
        
        self.create(uid, user_dict)
        logger.info("Created user: %s (%s)", uid, email)
        
        # Phase 19.2: Create email lookup entry
        self._update_email_lookup(uid, email, display_name, photo_url)
        
        return user_dict
    
    def _update_email_lookup(self, uid: str, email: str, display_name: str, photo_url: Optional[str]) -> None:
        """
        Phase 19.2: Update email lookup collection when user is created/updated.
        
        Args:
            uid: User ID
            email: User email
            display_name: User display name
            photo_url: User photo URL
        """
        try:
            from .email_lookup_repository import EmailLookupRepository
            email_lookup = EmailLookupRepository()
            email_lookup.set_user_email(
                email=email,
                user_id=uid,
                display_name=display_name,
                photo_url=photo_url
            )
        except Exception as e:
            # Don't fail user creation if email lookup fails
            logger.warning("Failed to update email lookup for %s: %s", email, e)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email address
        
        Args:
            email: User email
            
        Returns:
            User document or None
        """
        results = self.query(
            filters=[('email', '==', email)]
        )
        return results[0] if results else None
    
    def update_last_login(self, uid: str) -> None:
        """
        Update user's last login timestamp
        
        Args:
            uid: User ID
        """
        self.update(uid, {
            'last_login': datetime.utcnow().isoformat()
        })
