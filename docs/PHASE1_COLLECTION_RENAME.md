# Phase 1: Collection Renaming - Detailed Action Plan

**Goal:** Rename all Firestore collections to use `expense_` prefix for clear namespace separation  
**Duration:** 2-3 hours  
**Risk Level:** Medium (requires data migration)  
**Status:** Ready to Execute

---

## 📋 OVERVIEW

### Why This Matters
1. **Namespace Clarity:** Expense Engine and Group Planner share Firestore
2. **Avoid Conflicts:** Current `groups` collection is ambiguous
3. **Future-Proof:** Easier to manage permissions and queries
4. **Industry Standard:** Splitwise, Venmo, etc. all use prefixed collections

### Current → New Mapping

| Current Collection | New Collection | Structure Change |
|-------------------|----------------|------------------|
| `groups` | `expense_groups` | Add denormalized fields |
| `group_members` | (embedded) | Move to `expense_groups.members` map |
| `group_balances` | `expense_group_balances` | Add version field |
| `expenses` | `expense_groups/{gid}/expenses` | Move to subcollection |
| `settlements` | `expense_groups/{gid}/settlements` | Move to subcollection |
| `group_invitations` | `expense_invitations` | Rename only |
| `group_summaries` | `expense_group_summaries` | Rename only |

---

## 🎯 STEP-BY-STEP ACTIONS

### Step 1: Update Constants (5 minutes)

**File:** `web/backend/expense_engine/constants.py`

**Current Code:**
```python
class FirebaseCollections:
    USERS = 'users'
    GROUPS = 'groups'  # TODO: Change to 'expense_groups' after migration
    GROUP_MEMBERS = 'group_members'
    GROUP_INVITATIONS = 'group_invitations'
    GROUP_SUMMARIES = 'group_summaries'
    EXPENSES = 'expenses'
    EXPENSE_SPLITS = 'expense_splits'
    SETTLEMENTS = 'settlements'
    BALANCES = 'balances'
    GROUP_BALANCES = 'group_balances'
```

**New Code:**
```python
class FirebaseCollections:
    USERS = 'users'  # Shared across systems - no prefix
    
    # Expense Engine collections
    GROUPS = 'expense_groups'
    GROUP_MEMBERS = 'expense_group_members'  # Will be embedded later
    GROUP_INVITATIONS = 'expense_invitations'
    GROUP_SUMMARIES = 'expense_group_summaries'
    EXPENSES = 'expense_expenses'  # Will move to subcollection later
    SETTLEMENTS = 'expense_settlements'  # Will move to subcollection later
    GROUP_BALANCES = 'expense_group_balances'
    
    # Legacy names (for migration script reference)
    LEGACY_GROUPS = 'groups'
    LEGACY_GROUP_MEMBERS = 'group_members'
    LEGACY_INVITATIONS = 'group_invitations'
    LEGACY_SUMMARIES = 'group_summaries'
    LEGACY_EXPENSES = 'expenses'
    LEGACY_SETTLEMENTS = 'settlements'
    LEGACY_BALANCES = 'group_balances'
```

**Action:**
```bash
# Edit constants.py
code web/backend/expense_engine/constants.py
# Update FirebaseCollections class as shown above
```

---

### Step 2: Update All Collection References (15 minutes)

**Files to Update:**
1. `web/backend/expense_engine/firebase_operations.py`
2. `web/backend/expense_engine/service.py`
3. `web/backend/expense_engine/balance_manager.py`
4. `web/backend/expense_engine/clear_all_expenses.py`
5. `web/backend/expense_engine/routes/*.py`

**Search Pattern:**
```python
# Find all .collection() calls
.collection('groups')
.collection('group_members')
.collection('group_invitations')
.collection('group_summaries')
.collection('expenses')
.collection('settlements')
.collection('group_balances')
```

**Replace With:**
```python
.collection(FirebaseCollections.GROUPS)
.collection(FirebaseCollections.GROUP_MEMBERS)
.collection(FirebaseCollections.GROUP_INVITATIONS)
.collection(FirebaseCollections.GROUP_SUMMARIES)
.collection(FirebaseCollections.EXPENSES)
.collection(FirebaseCollections.SETTLEMENTS)
.collection(FirebaseCollections.GROUP_BALANCES)
```

**PowerShell Script (Already Exists):**
```powershell
# Run the existing script
.\update_collection_names.ps1
```

**Manual Verification:**
```bash
# Search for any remaining hardcoded collection names
grep -r "\.collection\('group" web/backend/expense_engine/
grep -r "\.collection\(\"group" web/backend/expense_engine/
grep -r "\.collection\('expense" web/backend/expense_engine/
```

---

### Step 3: Create Firestore Migration Script (30 minutes)

**File:** `web/backend/expense_engine/migrations/rename_collections.py`

```python
"""
Firestore Collection Migration Script
Renames all expense engine collections to use expense_ prefix

USAGE:
    python -m expense_engine.migrations.rename_collections --dry-run
    python -m expense_engine.migrations.rename_collections --execute

CAUTION: This copies data to new collections and optionally deletes old ones
"""

import time
import argparse
from firebase_admin import firestore
from typing import Dict, List

# Import constants
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from expense_engine.constants import FirebaseCollections

db = firestore.client()


def copy_collection(source: str, destination: str, batch_size: int = 500):
    """
    Copy all documents from source collection to destination
    
    Args:
        source: Source collection name
        destination: Destination collection name
        batch_size: Number of documents per batch (max 500)
    """
    print(f"\n📦 Copying {source} → {destination}")
    
    # Get all documents from source
    docs = db.collection(source).stream()
    
    total_copied = 0
    batch = db.batch()
    batch_count = 0
    
    for doc in docs:
        # Copy to new collection with same document ID
        dest_ref = db.collection(destination).document(doc.id)
        batch.set(dest_ref, doc.to_dict())
        batch_count += 1
        
        # Commit batch when full
        if batch_count >= batch_size:
            batch.commit()
            total_copied += batch_count
            print(f"   ✅ Committed batch: {total_copied} documents")
            batch = db.batch()
            batch_count = 0
    
    # Commit remaining documents
    if batch_count > 0:
        batch.commit()
        total_copied += batch_count
        print(f"   ✅ Committed final batch: {total_copied} documents")
    
    print(f"   ✅ Total: {total_copied} documents copied")
    return total_copied


def copy_subcollection_for_all_parents(parent_collection: str, subcollection_name: str, 
                                      new_parent: str, new_subcollection: str):
    """
    Copy subcollections from all parent documents
    
    Example: Copy expenses/{id} for all expense documents
    """
    print(f"\n📦 Copying subcollections: {parent_collection}/{subcollection_name}")
    
    parents = db.collection(parent_collection).stream()
    total_copied = 0
    
    for parent_doc in parents:
        parent_id = parent_doc.id
        subcol_docs = db.collection(parent_collection).document(parent_id)\
                        .collection(subcollection_name).stream()
        
        batch = db.batch()
        batch_count = 0
        
        for doc in subcol_docs:
            dest_ref = db.collection(new_parent).document(parent_id)\
                        .collection(new_subcollection).document(doc.id)
            batch.set(dest_ref, doc.to_dict())
            batch_count += 1
            
            if batch_count >= 500:
                batch.commit()
                total_copied += batch_count
                batch = db.batch()
                batch_count = 0
        
        if batch_count > 0:
            batch.commit()
            total_copied += batch_count
    
    print(f"   ✅ Total: {total_copied} subcollection documents copied")
    return total_copied


def delete_collection(collection_name: str, batch_size: int = 500):
    """
    Delete all documents in a collection
    
    CAUTION: This is irreversible!
    """
    print(f"\n🗑️  Deleting {collection_name}")
    
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


def migrate_collections(dry_run: bool = True, delete_old: bool = False):
    """
    Main migration function
    
    Args:
        dry_run: If True, only show what would be done
        delete_old: If True, delete old collections after copying
    """
    print("=" * 80)
    print("FIRESTORE COLLECTION MIGRATION")
    print("=" * 80)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    else:
        print("\n⚠️  EXECUTION MODE - Collections will be copied!")
        if delete_old:
            print("⚠️  OLD COLLECTIONS WILL BE DELETED!")
        response = input("\nType 'CONFIRM' to proceed: ")
        if response != 'CONFIRM':
            print("❌ Migration cancelled")
            return
    
    start_time = time.time()
    
    # Migration mapping
    migrations = [
        ('groups', FirebaseCollections.GROUPS),
        ('group_members', FirebaseCollections.GROUP_MEMBERS),
        ('group_invitations', FirebaseCollections.GROUP_INVITATIONS),
        ('group_summaries', FirebaseCollections.GROUP_SUMMARIES),
        ('expenses', FirebaseCollections.EXPENSES),
        ('settlements', FirebaseCollections.SETTLEMENTS),
        ('group_balances', FirebaseCollections.GROUP_BALANCES),
    ]
    
    total_docs = 0
    
    if not dry_run:
        for source, destination in migrations:
            count = copy_collection(source, destination)
            total_docs += count
            time.sleep(1)  # Rate limiting
        
        if delete_old:
            print("\n" + "=" * 80)
            print("DELETING OLD COLLECTIONS")
            print("=" * 80)
            response = input("\nType 'DELETE' to confirm deletion: ")
            if response == 'DELETE':
                for source, _ in migrations:
                    delete_collection(source)
                    time.sleep(1)
            else:
                print("❌ Deletion cancelled - old collections preserved")
    else:
        print("\nWould copy:")
        for source, destination in migrations:
            # Count documents
            count = len(list(db.collection(source).limit(1000).stream()))
            print(f"   {source} → {destination} ({count} documents)")
            total_docs += count
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Total documents: {total_docs}")
    print(f"Duration: {duration:.2f} seconds")
    
    if dry_run:
        print("\n💡 To execute migration, run:")
        print("   python -m expense_engine.migrations.rename_collections --execute")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate Firestore collections')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--execute', action='store_true', help='Execute migration')
    parser.add_argument('--delete-old', action='store_true', help='Delete old collections after copying')
    
    args = parser.parse_args()
    
    if args.execute:
        migrate_collections(dry_run=False, delete_old=args.delete_old)
    else:
        migrate_collections(dry_run=True)
```

**Action:**
```bash
# Create the migration script
code web/backend/expense_engine/migrations/rename_collections.py
# Copy the script above
```

---

### Step 4: Backup Firestore (10 minutes)

**Using Firebase Console:**
1. Go to https://console.firebase.google.com
2. Select your project
3. Go to Firestore Database
4. Click "Import/Export" tab
5. Click "Export"
6. Select all collections
7. Export to Cloud Storage bucket
8. Wait for export to complete
9. Download backup to local machine

**OR Using Firebase CLI:**
```bash
# Install Firebase CLI if needed
npm install -g firebase-tools

# Login
firebase login

# Export Firestore
firebase firestore:backup gs://your-bucket/backups/$(date +%Y%m%d_%H%M%S)
```

---

### Step 5: Test Migration on Dev (30 minutes)

**Prerequisites:**
1. Have a separate Firebase project for testing
2. Copy production data to dev project (optional but recommended)

**Actions:**
```bash
# 1. Switch to dev Firebase config
export GOOGLE_APPLICATION_CREDENTIALS="path/to/dev-service-account.json"

# 2. Activate virtual environment
.\wayfinder\Scripts\Activate.ps1

# 3. Run dry-run to verify
python -m expense_engine.migrations.rename_collections --dry-run

# 4. Execute migration
python -m expense_engine.migrations.rename_collections --execute

# 5. Verify data
python -m expense_engine.migrations.verify_migration

# 6. Run backend tests
pytest web/backend/expense_engine/tests/
```

**Verification Checklist:**
- [ ] All documents copied correctly
- [ ] No data loss
- [ ] Document IDs preserved
- [ ] Timestamps preserved
- [ ] Backend can read from new collections
- [ ] API endpoints work

---

### Step 6: Execute Production Migration (20 minutes)

**Pre-Migration Checklist:**
- [ ] Backup completed
- [ ] Dev migration tested successfully
- [ ] All team members notified
- [ ] Maintenance window scheduled (optional)
- [ ] Rollback plan ready

**Actions:**
```bash
# 1. Switch to production Firebase config
export GOOGLE_APPLICATION_CREDENTIALS="path/to/prod-service-account.json"

# 2. Activate virtual environment
.\wayfinder\Scripts\Activate.ps1

# 3. Run dry-run to verify
python -m expense_engine.migrations.rename_collections --dry-run

# 4. Execute migration (DO NOT DELETE OLD YET)
python -m expense_engine.migrations.rename_collections --execute

# 5. Verify new collections exist
# (Check Firebase Console)

# 6. Deploy updated backend code
git add .
git commit -m "Phase 1: Rename collections to expense_ prefix"
git push

# 7. Deploy to production
# (Your deployment process here)
```

---

### Step 7: Verify Production (15 minutes)

**Health Checks:**
```bash
# 1. Check API health
curl https://your-api.com/api/expense/health

# 2. Test key endpoints
curl -H "Authorization: Bearer $TOKEN" https://your-api.com/api/expense/groups

# 3. Check Firestore operations
# (Monitor Firebase Console for read/write patterns)

# 4. Check error logs
# (Your logging service)
```

**Manual Testing:**
1. Login to app
2. View groups list
3. Open a group
4. Add an expense
5. Delete an expense
6. Create a new group
7. Delete a group

**Success Criteria:**
- [ ] All API endpoints return 200
- [ ] Groups load correctly
- [ ] Expenses can be created
- [ ] Balances calculate correctly
- [ ] No errors in logs

---

### Step 8: Delete Old Collections (10 minutes)

**ONLY AFTER VERIFYING EVERYTHING WORKS!**

```bash
# Wait 24-48 hours of production traffic to be sure

# Then delete old collections
python -m expense_engine.migrations.rename_collections --execute --delete-old
```

**OR manually in Firebase Console:**
1. Go to Firestore Database
2. Select old collection (e.g., `groups`)
3. Click "Delete collection"
4. Confirm deletion
5. Repeat for all old collections

---

## 📊 EXPECTED IMPACT

### Database Structure
```
Before:
  groups/ (500 docs)
  group_members/ (1200 docs)
  expenses/ (5000 docs)
  ...

After:
  expense_groups/ (500 docs)
  expense_group_members/ (1200 docs)
  expense_expenses/ (5000 docs)
  ...
```

### Code Changes
- Files modified: ~8
- Lines changed: ~100
- New files: 1 (migration script)

### Performance
- No change (same structure, just renamed)
- Cache invalidated (will warm up within minutes)

### Cost
- Migration: ~10,000 reads + 10,000 writes = $0.10
- Ongoing: No change

---

## 🚨 ROLLBACK PLAN

### If Migration Fails

**Option 1: Keep both collections temporarily**
```python
# In constants.py, switch back to old names
GROUPS = 'groups'  # Revert
```

**Option 2: Restore from backup**
```bash
# Restore from Cloud Storage backup
firebase firestore:restore gs://your-bucket/backups/TIMESTAMP
```

**Option 3: Run reverse migration**
```bash
# Copy new collections back to old names
python -m expense_engine.migrations.rename_collections --reverse
```

---

## ✅ COMPLETION CHECKLIST

### Code Updates
- [ ] Constants updated
- [ ] All `.collection()` calls updated
- [ ] Migration script created
- [ ] Verification script created

### Migration Execution
- [ ] Backup completed
- [ ] Dev migration tested
- [ ] Production migration executed
- [ ] New collections verified
- [ ] Backend deployed
- [ ] Frontend tested (if needed)

### Cleanup
- [ ] Old collections deleted (after 48h)
- [ ] Legacy constants removed
- [ ] Documentation updated
- [ ] Team notified

---

## 🎯 NEXT PHASE

After Phase 1 completes, proceed to:
**Phase 2: Denormalized Balances** (see `SPLITWISE_ARCHITECTURE_PLAN.md`)

This will implement incremental balance updates to eliminate recalculations.

---

**Questions? Issues? Contact the team!**
