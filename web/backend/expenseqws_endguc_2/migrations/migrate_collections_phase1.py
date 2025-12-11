"""
Phase 1: Firestore Collection Migration Script
Migrates all expense engine collections to use expense_ prefix

USAGE:
    # Activate environment first
    .\wayfinder\Scripts\Activate.ps1
    
    # Dry run (no changes)
    python -m expense_engine.migrations.migrate_collections_phase1 --dry-run
    
    # Execute migration
    python -m expense_engine.migrations.migrate_collections_phase1 --execute
    
    # Delete old collections (only after verification!)
    python -m expense_engine.migrations.migrate_collections_phase1 --cleanup

SAFETY:
    - Always backup Firestore before running
    - Test on dev environment first
    - Keep old collections for 24-48 hours before cleanup
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from firebase_admin import firestore
from expense_engine.constants import FirebaseCollections

# Initialize Firestore client
db = firestore.client()

# Migration mapping (legacy_name -> new_name)
MIGRATION_MAP = {
    FirebaseCollections.LEGACY_GROUPS: FirebaseCollections.GROUPS,
    FirebaseCollections.LEGACY_GROUP_MEMBERS: FirebaseCollections.GROUP_MEMBERS,
    FirebaseCollections.LEGACY_GROUP_BALANCES: FirebaseCollections.GROUP_BALANCES,
    FirebaseCollections.LEGACY_GROUP_SUMMARIES: FirebaseCollections.GROUP_SUMMARIES,
    FirebaseCollections.LEGACY_GROUP_INVITATIONS: FirebaseCollections.GROUP_INVITATIONS,
    FirebaseCollections.LEGACY_EXPENSES: FirebaseCollections.EXPENSES,
    FirebaseCollections.LEGACY_SETTLEMENTS: FirebaseCollections.SETTLEMENTS,
}


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80 + "\n")


def count_documents(collection_name: str) -> int:
    """Count documents in a collection"""
    try:
        # Limit to 1000 for performance
        docs = db.collection(collection_name).limit(1000).stream()
        count = sum(1 for _ in docs)
        return count
    except Exception as e:
        print(f"   ⚠️  Error counting {collection_name}: {e}")
        return 0


def copy_collection(source: str, destination: str, batch_size: int = 500, dry_run: bool = True) -> Tuple[int, List[str]]:
    """
    Copy all documents from source collection to destination
    
    Args:
        source: Source collection name
        destination: Destination collection name
        batch_size: Number of documents per batch (max 500)
        dry_run: If True, only count documents
        
    Returns:
        Tuple of (documents_copied, error_list)
    """
    print(f"\n📦 {'[DRY RUN] Would copy' if dry_run else 'Copying'}: {source} → {destination}")
    
    errors = []
    total_copied = 0
    
    try:
        # Get all documents from source
        docs = db.collection(source).stream()
        
        if dry_run:
            # Just count documents
            count = sum(1 for _ in docs)
            print(f"   📊 Found {count} documents to migrate")
            return count, []
        
        # Execute actual copy
        batch = db.batch()
        batch_count = 0
        
        for doc in docs:
            try:
                # Copy to new collection with same document ID
                dest_ref = db.collection(destination).document(doc.id)
                doc_data = doc.to_dict()
                
                # Preserve timestamps if they exist
                if doc_data:
                    batch.set(dest_ref, doc_data)
                    batch_count += 1
                    
                    # Commit batch when full
                    if batch_count >= batch_size:
                        batch.commit()
                        total_copied += batch_count
                        print(f"   ✅ Committed batch: {total_copied} documents")
                        batch = db.batch()
                        batch_count = 0
                        
            except Exception as e:
                error_msg = f"Error copying document {doc.id}: {e}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
        
        # Commit remaining documents
        if batch_count > 0:
            batch.commit()
            total_copied += batch_count
            print(f"   ✅ Committed final batch: {total_copied} documents")
        
        if errors:
            print(f"   ⚠️  Completed with {len(errors)} errors")
        else:
            print(f"   ✅ Success: {total_copied} documents migrated")
            
        return total_copied, errors
        
    except Exception as e:
        error_msg = f"Fatal error copying collection: {e}"
        print(f"   ❌ {error_msg}")
        return total_copied, [error_msg]


def verify_migration(source: str, destination: str) -> bool:
    """
    Verify that migration was successful
    
    Args:
        source: Source collection name
        destination: Destination collection name
        
    Returns:
        True if verification passed
    """
    print(f"\n🔍 Verifying: {source} → {destination}")
    
    try:
        # Count documents in both collections
        source_count = count_documents(source)
        dest_count = count_documents(destination)
        
        if source_count == dest_count:
            print(f"   ✅ Counts match: {source_count} documents")
            return True
        else:
            print(f"   ❌ Count mismatch: source={source_count}, dest={dest_count}")
            return False
            
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False


def delete_collection(collection_name: str, batch_size: int = 500, dry_run: bool = True) -> int:
    """
    Delete all documents in a collection
    
    Args:
        collection_name: Collection to delete
        batch_size: Number of documents per batch
        dry_run: If True, only count documents
        
    Returns:
        Number of documents deleted
    """
    print(f"\n🗑️  {'[DRY RUN] Would delete' if dry_run else 'Deleting'}: {collection_name}")
    
    if dry_run:
        count = count_documents(collection_name)
        print(f"   📊 Found {count} documents to delete")
        return count
    
    try:
        docs = db.collection(collection_name).limit(batch_size).stream()
        deleted = 0
        
        while True:
            batch = db.batch()
            count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
            
            if count == 0:
                break
            
            batch.commit()
            deleted += count
            print(f"   Deleted {deleted} documents...")
            
            # Get next batch
            docs = db.collection(collection_name).limit(batch_size).stream()
        
        print(f"   ✅ Total deleted: {deleted} documents")
        return deleted
        
    except Exception as e:
        print(f"   ❌ Error deleting collection: {e}")
        return 0


def run_migration(dry_run: bool = True):
    """
    Execute the full migration process
    
    Args:
        dry_run: If True, only show what would be done
    """
    print_header("PHASE 1: FIRESTORE COLLECTION MIGRATION")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else '🚨 EXECUTION MODE 🚨'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    if not dry_run:
        print("\n⚠️  WARNING: This will copy data to new collections!")
        response = input("\nType 'MIGRATE' to proceed: ")
        if response != 'MIGRATE':
            print("❌ Migration cancelled")
            return
    
    start_time = time.time()
    total_docs = 0
    all_errors = []
    
    # Execute migrations
    print_header("MIGRATING COLLECTIONS")
    
    for source, destination in MIGRATION_MAP.items():
        docs_copied, errors = copy_collection(source, destination, dry_run=dry_run)
        total_docs += docs_copied
        all_errors.extend(errors)
        
        if not dry_run and docs_copied > 0:
            time.sleep(0.5)  # Rate limiting
    
    # Summary
    duration = time.time() - start_time
    print_header("MIGRATION SUMMARY")
    print(f"Total documents: {total_docs}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Errors: {len(all_errors)}")
    
    if all_errors:
        print("\n❌ Errors encountered:")
        for error in all_errors[:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(all_errors) > 10:
            print(f"   ... and {len(all_errors) - 10} more")
    
    if not dry_run:
        print("\n✅ Migration complete!")
        print("\n🔍 IMPORTANT: Verify the migration before cleanup:")
        print("   1. Test all expense engine endpoints")
        print("   2. Check Firestore console for new collections")
        print("   3. Verify data integrity")
        print("   4. Wait 24-48 hours before running cleanup")
        print("\n📝 To cleanup old collections:")
        print("   python -m expense_engine.migrations.migrate_collections_phase1 --cleanup")
    else:
        print("\n💡 To execute migration, run:")
        print("   python -m expense_engine.migrations.migrate_collections_phase1 --execute")


def run_verification():
    """Verify all migrations"""
    print_header("VERIFYING MIGRATIONS")
    
    all_passed = True
    
    for source, destination in MIGRATION_MAP.items():
        if not verify_migration(source, destination):
            all_passed = False
    
    print_header("VERIFICATION SUMMARY")
    if all_passed:
        print("✅ All verifications passed!")
        print("\n✅ Safe to proceed with cleanup")
    else:
        print("❌ Some verifications failed!")
        print("\n⚠️  DO NOT run cleanup until issues are resolved")


def run_cleanup(dry_run: bool = True):
    """
    Delete old collections after successful migration
    
    Args:
        dry_run: If True, only show what would be deleted
    """
    print_header("PHASE 1: CLEANUP OLD COLLECTIONS")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else '🚨 DELETION MODE 🚨'}")
    
    if not dry_run:
        print("\n⚠️  WARNING: This will permanently delete old collections!")
        print("⚠️  Make sure you have:")
        print("   1. Verified the migration")
        print("   2. Tested all endpoints")
        print("   3. Waited 24-48 hours")
        print("   4. Have a backup")
        
        response = input("\nType 'DELETE' to proceed: ")
        if response != 'DELETE':
            print("❌ Cleanup cancelled")
            return
    
    total_deleted = 0
    
    for source, destination in MIGRATION_MAP.items():
        deleted = delete_collection(source, dry_run=dry_run)
        total_deleted += deleted
        
        if not dry_run and deleted > 0:
            time.sleep(0.5)  # Rate limiting
    
    print_header("CLEANUP SUMMARY")
    print(f"Total documents deleted: {total_deleted}")
    
    if not dry_run:
        print("\n✅ Cleanup complete!")
        print("   Old collections have been removed")
    else:
        print("\n💡 To execute cleanup, run:")
        print("   python -m expense_engine.migrations.migrate_collections_phase1 --cleanup --execute")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Phase 1: Migrate Firestore collections to expense_ prefix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help='Show what would be done (no changes)')
    group.add_argument('--execute', action='store_true', help='Execute migration')
    group.add_argument('--verify', action='store_true', help='Verify migration')
    group.add_argument('--cleanup', action='store_true', help='Delete old collections')
    
    args = parser.parse_args()
    
    try:
        if args.verify:
            run_verification()
        elif args.cleanup:
            run_cleanup(dry_run=not args.execute)
        else:
            run_migration(dry_run=not args.execute)
            
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
