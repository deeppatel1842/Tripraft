"""
Migration Script: Populate Email Lookup Collection
Phase 19.2: Creates user_emails collection from existing users

Run this script once to backfill the email lookup collection with
existing user data. After this, new users will automatically be
added to the collection when they register.

Usage:
    python -m expense_engine.scripts.migrate_email_lookups

The script:
1. Reads all users from the 'users' collection
2. Creates email -> userId mappings in 'user_emails' collection
3. Reports progress and any errors
"""

import sys
import logging
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_email_lookups():
    """Migrate existing users to email lookup collection."""
    from expense_engine.repositories.user_repository import UserRepository
    from expense_engine.repositories.email_lookup_repository import EmailLookupRepository
    
    logger.info("Starting email lookup migration...")
    
    user_repo = UserRepository()
    email_lookup_repo = EmailLookupRepository()
    
    # Get all users
    logger.info("Fetching all users...")
    users_collection = user_repo.get_collection()
    users = [doc.to_dict() | {'id': doc.id} for doc in users_collection.stream()]
    
    logger.info("Found %d users to migrate", len(users))
    
    # Create email lookups
    success_count = 0
    error_count = 0
    skip_count = 0
    
    for i, user in enumerate(users):
        email = user.get('email')
        user_id = user.get('uid') or user.get('id')
        display_name = user.get('display_name', '')
        photo_url = user.get('photo_url', '')
        
        if not email:
            logger.warning("Skipping user %s - no email", user_id)
            skip_count += 1
            continue
        
        if not user_id:
            logger.warning("Skipping user with email %s - no user_id", email)
            skip_count += 1
            continue
        
        try:
            if email_lookup_repo.set_user_email(email, user_id, display_name, photo_url):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error("Error migrating %s: %s", email, e)
            error_count += 1
        
        # Progress update every 100 users
        if (i + 1) % 100 == 0:
            logger.info("Progress: %d/%d users processed", i + 1, len(users))
    
    logger.info("Migration complete!")
    logger.info("  Success: %d", success_count)
    logger.info("  Errors: %d", error_count)
    logger.info("  Skipped: %d", skip_count)
    
    return success_count, error_count, skip_count


if __name__ == '__main__':
    migrate_email_lookups()
