# Phase 7 Troubleshooting Guide

**Purpose**: Solve common issues during Places Engine deployment to Firebase Firestore

---

## 🔧 Common Issues & Solutions

### Issue 1: Firebase Admin SDK Import Error

**Error Message:**
```
ModuleNotFoundError: No module named 'firebase_admin'
```

**Cause:** Firebase Admin SDK not installed

**Solution:**
```bash
# Install the SDK
pip install firebase-admin

# Verify installation
python -c "import firebase_admin; print('✅ Firebase Admin SDK installed')"
```

---

### Issue 2: Firebase Credentials Not Found

**Error Message:**
```
FileNotFoundError: Credentials file not found: ./config/firebase-key.json
```

**Cause:** Service account JSON key not in expected location

**Solution:**
```bash
# 1. Download service account key from Firebase Console
#    - Go to Project Settings → Service Accounts
#    - Click "Generate New Private Key"

# 2. Place the JSON file in your project
cp ~/Downloads/serviceAccountKey.json ./config/firebase-key.json

# 3. Set environment variable
export FIREBASE_CREDENTIALS_PATH="./config/firebase-key.json"

# 4. Verify
echo $FIREBASE_CREDENTIALS_PATH
```

**Alternative**: Use FIREBASE_PROJECT_ID with Application Default Credentials
```bash
# If using Google Cloud credentials
export FIREBASE_PROJECT_ID="your-project-id"
gcloud auth application-default login
```

---

### Issue 3: Authentication/Permission Error

**Error Message:**
```
google.cloud.exceptions.PermissionDenied: 403 The caller does not have permission
```

**Cause:** Service account doesn't have Firestore permissions

**Solution:**
```bash
# 1. Go to Firebase Console
#    - Project Settings → Service Accounts

# 2. Find your service account email in the JSON file:
#    "client_email": "firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com"

# 3. Go to Google Cloud Console → IAM & Admin → IAM

# 4. Find the service account and click "Edit"

# 5. Add roles:
#    - Cloud Datastore Owner
#    - Cloud Firestore Owner
#    - Editor

# 6. Save and wait 5-10 minutes for permissions to propagate

# 7. Regenerate the service account key in Firebase Console
```

---

### Issue 4: Firestore Indexes Not Enabled

**Error Message:**
```
Composite index https://cloud.google.com/firestore/indexes/collections/..
is building and cannot be used yet.
```

**Cause:** Indexes still being built by Firebase

**Solution:**
```bash
# 1. Go to Firestore Database → Indexes tab

# 2. Check the status of each index:
#    - "Building" = Still processing (wait 2-5 minutes)
#    - "Enabled" = Ready to use
#    - "Error" = Failed, needs to be recreated

# 3. Wait for all indexes to reach "Enabled" state

# 4. Then run migration script:
python scripts/firebase_migrate_data.py
```

**If index shows "Error":**
```bash
# 1. Delete the failed index (using Firebase CLI)
firebase firestore:delete-index --collection=countries

# 2. Recreate the index through Firebase Console

# 3. Wait for rebuild
```

---

### Issue 5: Data Upload Fails Halfway Through

**Error Message:**
```
Error: Batch write failed after 3 retries
```

**Cause:** Network issue, timeout, or quota exceeded

**Solution:**
```bash
# 1. Check Firestore quota status
#    - Firebase Console → Settings → Usage & Billing → Quotas

# 2. If quota exceeded:
#    - Check daily quotas haven't been exceeded
#    - Wait for quota reset (usually midnight UTC)

# 3. If network issue:
#    - Check internet connection
#    - Try running script again (it will continue from where it stopped)

# 4. Check Firebase Console → Logs for detailed error

# 5. Verify data wasn't partially uploaded
python scripts/firebase_verify_deployment.py

# 6. Clean up duplicates if needed:
firebase firestore:delete countries --all-collections
python scripts/firebase_migrate_data.py
```

---

### Issue 6: Migration Script Hangs/Freezes

**Symptoms:**
```
Progress output stops, no new messages for several minutes
```

**Cause:** Network timeout, Firestore overload, or local system freeze

**Solution:**
```bash
# 1. Check if script is actually running
#    - Open another terminal and check process
ps aux | grep firebase_migrate_data.py

# 2. If frozen:
#    - Press Ctrl+C to stop the script
#    - Wait 30 seconds
#    - Run again to continue

# 3. Check network connectivity
ping www.google.com

# 4. Check Firestore status
#    - Go to Firebase Console
#    - Check for any maintenance messages

# 5. Run with verbose logging
export DEBUG=1
python scripts/firebase_migrate_data.py

# 6. If still hanging, run verification to see what was uploaded
python scripts/firebase_verify_deployment.py
```

---

### Issue 7: Verification Shows 0 Documents

**Error Message:**
```
Documents found: 0
```

**Cause:** Data wasn't uploaded, or collection doesn't exist

**Solution:**
```bash
# 1. Check if data files exist
ls -la pipeline/aggregated_data/

# 2. Verify file contents
python -c "
import json
with open('pipeline/aggregated_data/countries_aggregated.json') as f:
    data = json.load(f)
    print(f'Countries: {len(data) if isinstance(data, list) else 1}')
"

# 3. Check Firestore in Console
#    - Navigate to Firestore Database
#    - Check if collections exist (even if empty)

# 4. If collections don't exist, re-run migration
python scripts/firebase_migrate_data.py

# 5. Check migration logs
python scripts/firebase_migrate_data.py 2>&1 | tee migration.log
tail -100 migration.log
```

---

### Issue 8: Wrong Data in Firestore

**Symptoms:**
```
Data uploaded but values are incorrect or incomplete
```

**Cause:** Data file corruption or incorrect JSON structure

**Solution:**
```bash
# 1. Verify source data
python -c "
import json
with open('pipeline/aggregated_data/countries_aggregated.json') as f:
    data = json.load(f)
    if isinstance(data, list) and len(data) > 0:
        print('Sample country:')
        print(json.dumps(data[0], indent=2))
"

# 2. Check if data format is correct
#    Expected: List of dicts with 'id' and 'name' fields

# 3. If source data is corrupt:
#    - Re-generate data from original source
#    - Check pipeline/aggregated_data files for errors

# 4. Delete corrupted data from Firestore
#    - Go to Firestore Database
#    - Delete the corrupted collection

# 5. Upload fresh data
python scripts/firebase_migrate_data.py
```

---

### Issue 9: Firebase Credentials Expired

**Error Message:**
```
google.auth.exceptions.RefreshError: The credentials do not contain the necessary fields for ...
```

**Cause:** Service account key is invalid or expired

**Solution:**
```bash
# 1. Generate new service account key
#    - Firebase Console → Settings → Service Accounts
#    - Find your service account
#    - Click the three dots menu → "Create new key"
#    - Choose JSON format
#    - Save and download

# 2. Replace old credentials file
cp ~/Downloads/new-serviceAccountKey.json ./config/firebase-key.json

# 3. Update environment variable if path changed
export FIREBASE_CREDENTIALS_PATH="./config/firebase-key.json"

# 4. Test connection
python -c "
import os
from firebase_admin import credentials, initialize_app, firestore
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()
print('✅ Connection successful')
"

# 5. Run migration again
python scripts/firebase_migrate_data.py
```

---

### Issue 10: Query Performance Slow

**Symptoms:**
```
Query results returning in 50-100ms instead of <5ms
```

**Cause:** 
- Indexes not built yet
- Indexes not being used
- Firestore under heavy load

**Solution:**
```bash
# 1. Verify indexes are enabled
#    - Firebase Console → Firestore Database → Indexes
#    - Check all indexes show "Enabled" (not "Building")

# 2. Wait a few minutes and retry
#    - Indexes can take time to build and warm up

# 3. Check if queries are using indexes
#    - Firebase Console → Firestore Database → Indexes
#    - Look for "Query scope: COLLECTION"
#    - Verify field paths match your queries

# 4. Try a simple query first
python -c "
from firebase_admin import firestore, initialize_app, credentials
import os
import time
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()

# Simple query
start = time.time()
docs = db.collection('countries').limit(5).get()
elapsed = (time.time() - start) * 1000

print(f'Query time: {elapsed:.2f}ms')
print(f'Documents: {len(list(docs))}')
"

# 5. If still slow, check Firestore metrics
#    - Firebase Console → Usage & Billing → Billing
#    - Check for any quota alerts
```

---

### Issue 11: Duplicate Documents in Firestore

**Symptoms:**
```
Running verification shows more documents than expected
```

**Cause:** Migration script ran multiple times, creating duplicates

**Solution:**
```bash
# 1. Check current document count
python scripts/firebase_verify_deployment.py

# 2. If duplicates exist:
#    Option A: Delete and re-upload
#    - Backup current data
#    - Delete collections:
#      - Firestore Database → Right-click collection → Delete
#    - Re-run migration:
python scripts/firebase_migrate_data.py

#    Option B: Keep duplicates (if only a few)
#    - They won't affect queries
#    - Consider cleaning up later if needed

# 3. To prevent future duplicates:
#    - Check document count before uploading
#    - Don't run migration script multiple times
#    - Verify data before running
```

---

### Issue 12: Firestore Database Disabled

**Error Message:**
```
No database found for project 'project-id'
```

**Cause:** Firestore database hasn't been created yet

**Solution:**
```bash
# 1. Go to Firebase Console
#    - Select your project
#    - Click "Create Database" (or "Firestore Database")

# 2. Choose settings:
#    - Location: Choose region closest to users
#    - Start in "Production mode" (not development)

# 3. Click "Create" and wait for initialization (2-5 minutes)

# 4. Once created, try migration script
python scripts/firebase_migrate_data.py
```

---

## 🚨 Critical Issues

### If everything is broken:

```bash
# 1. Get detailed error information
export DEBUG=1
python scripts/firebase_migrate_data.py 2>&1 > error_log.txt

# 2. Check Firebase status
#    - Firebase Status Page: https://status.firebase.google.com/
#    - Google Cloud Status: https://status.cloud.google.com/

# 3. Review error logs
cat error_log.txt

# 4. Check Firebase Console Logs
#    - Firebase Console → Logs (bell icon)

# 5. If still stuck, consider:
#    - Recreating the database from scratch
#    - Checking Firebase support (if on paid plan)
#    - Reviewing Google Cloud documentation

# 6. Temporary workaround (use JSON files)
#    - Keep using JSON file-based search
#    - Try Firebase deployment again later
#    - Set FIRESTORE_ENABLED=false in config
```

---

## 📊 Debugging Commands

```bash
# List all collections
python -c "
from firebase_admin import firestore, initialize_app, credentials
import os
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()
collections = db.collections()
for col in collections:
    count = len(list(db.collection(col.id).limit(1000).get()))
    print(f'{col.id}: {count} documents')
"

# Get document count
python -c "
from firebase_admin import firestore, initialize_app, credentials
import os
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()

# Rough count (limited to 10,000)
for col_name in ['countries', 'states', 'cities', 'search_index']:
    count = len(list(db.collection(col_name).limit(10000).get()))
    print(f'{col_name}: ~{count} documents')
"

# Test a query
python -c "
from firebase_admin import firestore, initialize_app, credentials
import os, time
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()

start = time.time()
docs = db.collection('countries').limit(10).get()
elapsed = (time.time() - start) * 1000

print(f'Countries query: {elapsed:.2f}ms')
print(f'Results: {len(list(docs))} documents')
"

# Delete a collection
python -c "
from firebase_admin import firestore, initialize_app, credentials
import os
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()

# WARNING: This deletes all documents!
# collection_name = 'countries'
# docs = db.collection(collection_name).limit(10000).get()
# deleted = 0
# for doc in docs:
#     doc.reference.delete()
#     deleted += 1
# print(f'Deleted {deleted} documents from {collection_name}')
"
```

---

## 📞 Getting Help

**If troubleshooting doesn't work:**

1. Check Firebase Logs:
   - Firebase Console → Logs (bell icon)

2. Review error details:
   - Save full error output to file
   - Check timestamps in logs

3. Check Firebase Status:
   - https://status.firebase.google.com/

4. Google Cloud Documentation:
   - https://cloud.google.com/firestore/docs

5. Firebase Support:
   - https://firebase.google.com/support

---

**Last Updated**: December 8, 2025

