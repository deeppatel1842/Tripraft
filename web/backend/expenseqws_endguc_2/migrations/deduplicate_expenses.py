"""
Migration Script: Deduplicate Expenses
Migrates from per-user expense storage to centralized expense storage
Run this once to clean up existing duplicated data

BEFORE:
users/{user_id}.json contains expenses[] (duplicated across users)

AFTER:
expenses/{expense_id}.json (single source of truth)
expense_participants/{expense_id}.json (who's involved)
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DATABASE_BASE_PATH = Path(__file__).parent.parent.parent / 'database' / 'expense_database'

def migrate_expenses():
    """Migrate expenses from per-user storage to centralized storage"""
    
    users_dir = DATABASE_BASE_PATH / 'users'
    expenses_dir = DATABASE_BASE_PATH / 'expenses'
    participants_dir = DATABASE_BASE_PATH / 'expense_participants'
    
    # Create new directories
    expenses_dir.mkdir(parents=True, exist_ok=True)
    participants_dir.mkdir(parents=True, exist_ok=True)
    
    # Track unique expenses
    unique_expenses = {}
    expense_participants = {}
    
    logger.info("=" * 80)
    logger.info("STARTING EXPENSE DEDUPLICATION MIGRATION")
    logger.info("=" * 80)
    
    # Step 1: Collect all unique expenses from all user files
    total_duplicates = 0
    total_unique = 0
    
    if users_dir.exists():
        for user_file in users_dir.glob('*.json'):
            user_id = user_file.stem
            logger.info(f"\nProcessing user: {user_id}")
            
            try:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                
                expenses = user_data.get('expenses', [])
                logger.info(f"  Found {len(expenses)} expenses in user file")
                
                for expense in expenses:
                    expense_id = expense.get('expense_id') or expense.get('id')
                    
                    if not expense_id:
                        logger.warning(f"  ⚠️  Skipping expense without ID")
                        continue
                    
                    # Track which users have this expense
                    if expense_id not in expense_participants:
                        expense_participants[expense_id] = []
                    expense_participants[expense_id].append(user_id)
                    
                    # Store unique expense (first occurrence)
                    if expense_id not in unique_expenses:
                        unique_expenses[expense_id] = expense
                        total_unique += 1
                        logger.info(f"  ✓ New expense: {expense_id} - {expense.get('description')}")
                    else:
                        total_duplicates += 1
                        logger.info(f"  ➜ Duplicate: {expense_id} (already stored)")
                
            except Exception as e:
                logger.error(f"  ✗ Error processing {user_file}: {e}")
    
    # Step 2: Save unique expenses to central storage
    logger.info(f"\n{'=' * 80}")
    logger.info(f"SAVING UNIQUE EXPENSES TO CENTRAL STORAGE")
    logger.info(f"{'=' * 80}\n")
    
    for expense_id, expense_data in unique_expenses.items():
        try:
            expense_file = expenses_dir / f"{expense_id}.json"
            with open(expense_file, 'w') as f:
                json.dump(expense_data, f, indent=2, default=str)
            logger.info(f"✓ Saved: {expense_id}")
        except Exception as e:
            logger.error(f"✗ Error saving expense {expense_id}: {e}")
    
    # Step 3: Save participant mappings
    logger.info(f"\n{'=' * 80}")
    logger.info(f"SAVING PARTICIPANT MAPPINGS")
    logger.info(f"{'=' * 80}\n")
    
    for expense_id, participants in expense_participants.items():
        try:
            participant_file = participants_dir / f"{expense_id}.json"
            participant_data = {
                'expense_id': expense_id,
                'participants': list(set(participants)),  # Remove any duplicates
                'participant_count': len(set(participants)),
                'migrated_at': datetime.utcnow().isoformat()
            }
            with open(participant_file, 'w') as f:
                json.dump(participant_data, f, indent=2)
            logger.info(f"✓ Saved participants for {expense_id}: {len(set(participants))} users")
        except Exception as e:
            logger.error(f"✗ Error saving participants for {expense_id}: {e}")
    
    # Step 4: Clean up user files (remove expenses array, keep profile)
    logger.info(f"\n{'=' * 80}")
    logger.info(f"CLEANING UP USER FILES")
    logger.info(f"{'=' * 80}\n")
    
    if users_dir.exists():
        for user_file in users_dir.glob('*.json'):
            try:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                
                # Keep profile, remove expenses
                if 'expenses' in user_data:
                    expense_count = len(user_data['expenses'])
                    del user_data['expenses']
                    user_data['expenses_migrated'] = True
                    user_data['migration_date'] = datetime.utcnow().isoformat()
                    
                    with open(user_file, 'w') as f:
                        json.dump(user_data, f, indent=2, default=str)
                    
                    logger.info(f"✓ Cleaned {user_file.stem}: removed {expense_count} expenses")
            except Exception as e:
                logger.error(f"✗ Error cleaning {user_file}: {e}")
    
    # Step 5: Generate migration report
    logger.info(f"\n{'=' * 80}")
    logger.info(f"MIGRATION SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"")
    logger.info(f"Total unique expenses: {total_unique}")
    logger.info(f"Total duplicates removed: {total_duplicates}")
    logger.info(f"Storage reduction: {(total_duplicates / (total_unique + total_duplicates) * 100):.1f}%")
    logger.info(f"")
    logger.info(f"New structure:")
    logger.info(f"  • {expenses_dir}: {len(list(expenses_dir.glob('*.json')))} expense files")
    logger.info(f"  • {participants_dir}: {len(list(participants_dir.glob('*.json')))} participant files")
    logger.info(f"")
    logger.info(f"{'=' * 80}")
    logger.info(f"MIGRATION COMPLETE ✓")
    logger.info(f"{'=' * 80}\n")
    
    # Save migration report
    report_file = DATABASE_BASE_PATH / 'migration_report.json'
    report = {
        'migration_date': datetime.utcnow().isoformat(),
        'unique_expenses': total_unique,
        'duplicates_removed': total_duplicates,
        'storage_reduction_percent': (total_duplicates / (total_unique + total_duplicates) * 100) if (total_unique + total_duplicates) > 0 else 0,
        'expenses_migrated': list(unique_expenses.keys()),
        'status': 'completed'
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Migration report saved to: {report_file}")
    
    return {
        'success': True,
        'unique_expenses': total_unique,
        'duplicates_removed': total_duplicates,
        'report_file': str(report_file)
    }


def rollback_migration():
    """Rollback migration (restore from backup if needed)"""
    logger.warning("Rollback not implemented - create backup before migration!")
    logger.info("To rollback: restore from backup of database/expense_database/users/")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        print("\n⚠️  WARNING: This will restructure your expense storage!")
        print("Make sure you have a backup of database/expense_database/")
        print("\nPress Enter to continue, or Ctrl+C to cancel...")
        try:
            input()
            result = migrate_expenses()
            print(f"\n✅ Migration completed successfully!")
            print(f"   Unique expenses: {result['unique_expenses']}")
            print(f"   Duplicates removed: {result['duplicates_removed']}")
        except KeyboardInterrupt:
            print("\n\nMigration cancelled by user.")
