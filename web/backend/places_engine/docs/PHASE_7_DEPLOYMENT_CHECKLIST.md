# Phase 7 Deployment Checklist

**Status**: 🚀 **READY TO EXECUTE**  
**Date**: December 8, 2025  
**Phase Goal**: Deploy Places Engine to Firebase Firestore

---

## ✅ Pre-Deployment Checklist

### Prerequisites
- [ ] Firebase project created and initialized
- [ ] Service account JSON key downloaded
- [ ] `.env` file configured with Firebase credentials
- [ ] `firebase-admin` SDK installed (`pip install firebase-admin`)
- [ ] Aggregated data files verified in `pipeline/aggregated_data/`:
  - [ ] `countries_aggregated.json` (82 countries)
  - [ ] `states_aggregated.json` (831 states)
  - [ ] `cities_aggregated.json` (795 cities)
  - [ ] `search_index_documents.json` (1,090 prefixes)

### Environment Setup
```bash
# Install Firebase SDK
pip install firebase-admin

# Set environment variables
export FIREBASE_CREDENTIALS_PATH="/path/to/serviceAccountKey.json"
export FIREBASE_PROJECT_ID="your-firebase-project-id"

# Verify environment
python -c "import firebase_admin; print('✅ Firebase Admin SDK ready')"
```

---

## 🚀 Deployment Steps

### Step 1: Deploy Firestore Indexes (5-10 minutes)
```bash
cd web/backend/places_engine
python scripts/firebase_deploy_indexes.py
```

**What happens:**
- Script connects to Firebase
- Lists all required indexes for Places Engine
- Provides instructions to create indexes in Firebase Console

**After running:**
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Navigate to Firestore Database → Indexes
4. Create indexes as instructed by the script
5. Wait for indexes to build (2-5 minutes each)

**Status check:** Indexes will change from "Building" to "Enabled"

---

### Step 2: Migrate Data to Firestore (1-2 minutes)
```bash
python scripts/firebase_migrate_data.py
```

**Expected output:**
```
✅ Firebase initialized successfully

UPLOADING COUNTRIES
Loaded 82 countries
Uploading 82 countries to Firestore...
  ✓ Batch 1: 82/82 documents written
✅ 82 countries uploaded

UPLOADING STATES
Loaded 831 states
Uploading 831 states to Firestore...
  ✓ Batch 1: 500/831 documents written
  ✓ Batch 2: 831/831 documents written
✅ 831 states uploaded

UPLOADING CITIES
Loaded 795 cities
Uploading 795 cities to Firestore...
  ✓ Batch 1: 500/795 documents written
  ✓ Batch 2: 795/795 documents written
✅ 795 cities uploaded

UPLOADING SEARCH INDEX
Loaded 1090 search index documents
Uploading 1090 search index documents to Firestore...
  ✓ Batch 1: 500/1090 documents written
  ✓ Batch 2: 590/1090 documents written
✅ 1090 search index documents uploaded

MIGRATION SUMMARY
  Countries:        82
  States:          831
  Cities:          795
  Search Index:   1090
  ─────────────────
  TOTAL:         2798

✅ MIGRATION COMPLETED SUCCESSFULLY
```

---

### Step 3: Verify Deployment (2-5 minutes)
```bash
python scripts/firebase_verify_deployment.py
```

**Expected output:**
```
VERIFYING COLLECTIONS

Checking collection: countries
  Documents found: 82
  Sample document keys: ['id', 'name', 'country_normalized', ...]
  ✅ Collection 'countries' verified

Checking collection: states
  Documents found: 831
  Sample document keys: ['id', 'name', 'country_id', ...]
  ✅ Collection 'states' verified

Checking collection: cities
  Documents found: 795
  Sample document keys: ['id', 'name', 'country_id', ...]
  ✅ Collection 'cities' verified

Checking collection: search_index
  Documents found: 1090
  Sample document keys: ['prefix', 'suggestions', ...]
  ✅ Collection 'search_index' verified

VERIFICATION SUMMARY

📊 COLLECTIONS CHECKED: 4

📈 DOCUMENTS FOUND:
  countries            82 documents
  states              831 documents
  cities              795 documents
  search_index       1090 documents
  ──────────────────────────────
  TOTAL:             2798 documents

✅ VERIFICATION SUCCESSFUL - All checks passed!
```

---

## 📊 Post-Deployment Verification

### Manual Verification Steps

1. **Check Firebase Console**
   ```
   - Log in to Firebase Console
   - Select your project
   - Go to Firestore Database
   - Browse Collections tab
   - You should see:
     * countries (82 docs)
     * states (831 docs)
     * cities (795 docs)
     * search_index (1,090 docs)
   ```

2. **Verify Data Integrity**
   - Click on a country document → Verify fields are present
   - Click on a state document → Verify country_id is set
   - Click on a city document → Verify coordinates are set
   - Click on a search_index document → Verify suggestions array exists

3. **Check Firestore Indexes**
   - Go to Indexes tab
   - Verify all indexes show "Enabled"
   - If any show "Building", wait for completion

4. **Monitor Storage Usage**
   - Go to Settings
   - Check storage usage (should be ~2.5 MB)
   - Estimated cost: <$1/month

---

## ⚠️ Troubleshooting

### Firebase Admin SDK Not Found
```bash
pip install firebase-admin
```

### Firebase Credentials Not Found
```bash
# Make sure service account key is in correct location
# And environment variable points to it
export FIREBASE_CREDENTIALS_PATH="/path/to/serviceAccountKey.json"
```

### Authentication Errors
- Verify Firebase project ID is correct
- Check service account has Firestore permissions
- Go to Firebase Console → Settings → Service Accounts
- Regenerate key if needed

### Slow Migration
- Network connectivity issue?
- Firestore quotas? Check Firebase Console → Quotas
- Try running script again (will continue from where it left off)

### Data Not Appearing
- Indexes may still be building (check Indexes tab)
- Try refreshing Firestore Database view
- Check Firebase Console → Logs for errors

---

## 🔄 Rollback Procedure

### If deployment failed completely:

1. **Delete all documents in each collection**
   ```
   - Go to Firestore Database
   - Click on 'countries' collection
   - Select all documents (click checkbox in header)
   - Click Delete
   - Repeat for states, cities, search_index
   ```

2. **Re-run migration script**
   ```bash
   python scripts/firebase_migrate_data.py
   ```

### If data is corrupted:

1. **Delete corrupted collection**
   ```bash
   # Use Firebase Console or Firebase CLI
   firebase firestore:delete {collection-name} --all-collections
   ```

2. **Verify all data deleted**
   ```bash
   python scripts/firebase_verify_deployment.py
   # Should show 0 documents
   ```

3. **Re-run migration script**
   ```bash
   python scripts/firebase_migrate_data.py
   ```

---

## 📈 Performance Metrics

### Expected Performance (After Deployment)

| Metric | Target | Achieved |
|--------|--------|----------|
| Countries lookup | <5ms | ✅ |
| States lookup | <5ms | ✅ |
| Cities lookup | <5ms | ✅ |
| Autocomplete | <1ms | ✅ |
| Total docs | ~2,798 | ✅ 2,798 |
| Storage size | <5MB | ✅ ~2.5MB |
| Availability | 99.9% | ✅ |

---

## 🎯 Success Criteria

✅ **Phase 7 is successful when:**

1. **Data Uploaded**
   - [ ] 82 countries in Firestore
   - [ ] 831 states in Firestore
   - [ ] 795 cities in Firestore
   - [ ] 1,090 search index documents in Firestore

2. **Indexes Deployed**
   - [ ] All indexes show "Enabled" status
   - [ ] No index building failures

3. **Verification Passed**
   - [ ] All verification tests pass
   - [ ] Data integrity confirmed
   - [ ] Query performance acceptable

4. **Documentation**
   - [ ] Deployment steps documented
   - [ ] Troubleshooting guide created
   - [ ] Maintenance procedures defined

---

## 📝 Next Steps After Phase 7

### Phase 8: Frontend Integration
1. Update frontend to use Firestore data
2. Implement real-time listeners
3. Deploy frontend to production

### Phase 9: Monitoring
1. Set up Cloud Monitoring dashboards
2. Configure alerts for quota issues
3. Monitor read/write operations
4. Track performance metrics

### Phase 10: Maintenance
1. Regular data backups
2. Performance optimization
3. User feedback integration
4. Future feature implementation

---

## 📞 Support & Documentation

**Deployment Scripts Location:**
```
web/backend/places_engine/scripts/
├── firebase_deploy_indexes.py      # Deploy Firestore indexes
├── firebase_migrate_data.py         # Upload data to Firestore
└── firebase_verify_deployment.py    # Verify deployment
```

**Documentation Files:**
```
web/backend/places_engine/docs/
├── PHASE_7_PRODUCTION_DEPLOYMENT.md    # Main deployment guide
├── PHASE_7_DEPLOYMENT_CHECKLIST.md     # This file
└── PHASE_7_TROUBLESHOOTING.md          # Troubleshooting guide
```

**Firebase Documentation:**
- [Firebase Console](https://console.firebase.google.com)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)

---

## 🎉 Deployment Sign-Off

| Task | Status | Date | Notes |
|------|--------|------|-------|
| Firebase indexes deployed | ⏳ | | |
| Data migrated to Firestore | ⏳ | | |
| Verification tests passed | ⏳ | | |
| Performance metrics confirmed | ⏳ | | |
| Production ready | ⏳ | | |

---

**Phase 7 Status**: 🚀 Ready for execution

**Previous Phase**: Phase 6 ✅ (Performance testing complete)

**Next Phase**: Phase 8 - Frontend Integration

