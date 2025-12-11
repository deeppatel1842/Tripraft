# 🚀 TripRaft Expense Engine Optimization - Executive Summary

**Created:** November 24, 2025  
**Goal:** Transform expense engine from 100+ reads per flow to <15 reads (Splitwise-level performance)  
**Approach:** Denormalize, precompute, cache everything

---

## 📚 DOCUMENTATION STRUCTURE

I've created a complete optimization plan split into focused documents:

### 1. **CURRENT_FLOW_ANALYSIS.md**
**What:** Detailed analysis of current system  
**Contains:**
- Current Firestore reads breakdown (95 reads per complete flow)
- Redis cache usage and hit rates (~40-50%)
- Balance calculation logic (recalculation issues)
- Delete flow problems (200+ operations)
- Pain points and bottlenecks

**Key Finding:** Even simple operations trigger 50+ Firestore reads

---

### 2. **SPLITWISE_ARCHITECTURE_PLAN.md**
**What:** Complete architectural blueprint following Splitwise patterns  
**Contains:**
- New Firestore structure with `expense_` prefix
- Redis key strategy with optimized TTLs
- Denormalized data patterns
- Incremental balance engine design
- Cache invalidation matrix
- 7 implementation phases

**Key Goal:** Reduce 95 reads → <15 reads (92% reduction)

---

### 3. **PHASE1_COLLECTION_RENAME.md**
**What:** Step-by-step action plan for Phase 1  
**Contains:**
- Detailed instructions for renaming collections
- Migration script code
- Backup procedures
- Verification steps
- Rollback plan

**Time:** 2-3 hours  
**Risk:** Medium (requires data migration)

---

## 🎯 THE SPLITWISE BLUEPRINT (Key Points)

### Core Principles
1. **Denormalize everything** → Store computed values, don't recalculate
2. **Precompute everything** → Update incrementally, never from scratch
3. **Cache everything** → 90%+ hit rate, aggressive invalidation

---

### Current Problems

#### ❌ Heavy Reads
```
GET /groups → 33 reads (fetches members + users for all groups)
GET /groups/{gid}/full → 24 reads (all expenses + settlements)
Total flow: 95+ reads
```

#### ❌ Balance Recalculation
```python
# Every 5 minutes or on cache miss:
expenses = fetch_all_expenses(group_id)  # N reads
for expense in expenses:
    recalculate_splits()  # CPU intensive
```

#### ❌ No Pagination
```
500 expenses in group = 500 Firestore reads on group open
```

#### ❌ Collection Name Conflicts
```
groups/          # Used by both Expense Engine AND Group Planner
group_members/   # Ambiguous ownership
```

---

### Splitwise Solution

#### ✅ New Structure
```
expense_groups/                     # Clear namespace
  └─ {gid}
      ├─ members: {uid: {role}}    # Denormalized map
      ├─ member_count: 5            # Precomputed
      ├─ expense_count: 42          # Precomputed
      ├─ total_spent: 1250.00       # Precomputed

expense_group_balances/             # One doc per group
  └─ {gid}
      ├─ balances: {uid: -25.5}    # Current balances
      ├─ version: 42                # Mutation counter
      └─ simplified_debts: [...]    # Precomputed settlements

expense_group_summaries/            # One doc per user+group
  └─ {user_id}_{group_id}
      ├─ my_balance: -25.5          # User's balance
      ├─ expense_count: 42          # Group stats
      └─ last_activity              # Sorting
```

#### ✅ Incremental Balances
```python
# NEVER recalculate from scratch
def add_expense(expense_data):
    # Update balance document (transaction)
    transaction:
        balances = get_current_balances()
        for participant in participants:
            delta = calculate_delta()
            balances[uid] += delta        # Increment only
        balances.version += 1
        save_balances()
```

#### ✅ Paginated Expenses
```
GET /groups/{gid}/expenses?page=0&limit=20
└─ Returns 20 expenses at a time
└─ Cached per page
```

#### ✅ Smart Caching
```python
# User opens app
user_groups:{uid}:summary → Redis hit (0 reads)

# Opens group
group_summary:{gid} → Redis hit (0 reads)

# Scrolls expenses
group_expenses:{gid}:p:0 → Redis hit (0 reads)

Total reads: 0 (after cache warm-up)
```

---

## 📊 EXPECTED RESULTS

### Performance Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Home load reads | 33 | 2-5 | **85-94% ↓** |
| Group load reads | 24 | 3-8 | **67-88% ↓** |
| Complete flow reads | 95 | <15 | **84-92% ↓** |
| Cache hit rate | 40% | 90%+ | **125% ↑** |
| P95 response time | 800ms | <200ms | **75% ↓** |

### Cost Reduction
```
Current: ~365 reads per flow × 1000 users/day = 365,000 reads
After: ~20 reads per flow × 1000 users/day = 20,000 reads

Savings: 345,000 reads/day = $0.21/day × 30 days = $6.30/month
For 10,000 users: $63/month savings
```

---

## 🎯 IMPLEMENTATION PHASES

### Phase 1: Collection Renaming ⏰ 2-3 hours
**Action:** Add `expense_` prefix to all collections  
**Impact:** No performance change (just clarity)  
**Risk:** Medium (data migration)  
**Document:** `PHASE1_COLLECTION_RENAME.md`

---

### Phase 2: Denormalized Balances ⏰ 4-6 hours
**Action:** Implement incremental balance updates  
**Impact:** Eliminate balance recalculation (save 10-20 reads)  
**Risk:** High (balance accuracy critical)

**Changes:**
- Create `expense_group_balances` collection
- Update `add_expense()` to increment balances
- Update `delete_expense()` to reverse balances
- Remove `_recalculate_and_cache_balance()`

---

### Phase 3: Group Summaries Everywhere ⏰ 3-4 hours
**Action:** Maintain `expense_group_summaries` for every member  
**Impact:** One read per user to get all groups  
**Risk:** Low (already partially implemented)

**Changes:**
- Update summaries on every mutation
- Create `GET /user/summary` endpoint
- Update `GET /groups` to use summaries first

---

### Phase 4: Paginated Expenses ⏰ 4-5 hours
**Action:** Load 20 expenses at a time  
**Impact:** Save 480+ reads for groups with 500 expenses  
**Risk:** Medium (structural change)

**Changes:**
- Move expenses to subcollection: `expense_groups/{gid}/expenses/`
- Add `?page=N&limit=20` parameters
- Implement infinite scroll in frontend
- Cache per page

---

### Phase 5: Optimized Endpoints ⏰ 3-4 hours
**Action:** Split heavy endpoints into focused ones  
**Impact:** Reduce payload size, allow selective loading  
**Risk:** Low (backend only)

**New Endpoints:**
```
GET /user/summary                  # User's groups + balances
GET /groups/{gid}                  # Group metadata + members
GET /groups/{gid}/balances         # Balance calculations only
GET /groups/{gid}/expenses?page=N  # Paginated expenses
```

---

### Phase 6: Redis Strategy ⏰ 2-3 hours
**Action:** Optimize TTLs and invalidation  
**Impact:** 90%+ cache hit rate  
**Risk:** Low

**Changes:**
- Implement read-through cache
- Tune TTLs per data type
- Aggressive invalidation on writes

---

### Phase 7: Smart Delete Flow ⏰ 2-3 hours
**Action:** Batch deletions and parallel operations  
**Impact:** Reduce delete time from 3s to <500ms  
**Risk:** Low

**Changes:**
- Batch delete expenses (10 at a time)
- Parallel delete summaries
- Add cleanup verification

---

## 📋 COLLECTION RENAME QUICK START

Since you asked specifically about renaming collections, here's the immediate action:

### Step 1: Update Constants (5 min)
Edit `web/backend/expense_engine/constants.py`:
```python
class FirebaseCollections:
    GROUPS = 'expense_groups'              # Changed
    GROUP_MEMBERS = 'expense_group_members'  # Changed
    GROUP_BALANCES = 'expense_group_balances'  # Changed
    # ... etc
```

### Step 2: Update Code References (15 min)
Run PowerShell script:
```powershell
.\update_collection_names.ps1
```

### Step 3: Create Migration Script (30 min)
See full script in `PHASE1_COLLECTION_RENAME.md`

### Step 4: Test on Dev (30 min)
```bash
python -m expense_engine.migrations.rename_collections --dry-run
python -m expense_engine.migrations.rename_collections --execute
```

### Step 5: Execute on Production (20 min)
```bash
# Backup first!
firebase firestore:backup gs://your-bucket/backups/$(date +%Y%m%d)

# Then migrate
python -m expense_engine.migrations.rename_collections --execute
```

---

## 🚨 IMPORTANT NOTES

### Before Starting
1. **Backup Firestore** - Always backup before migrations
2. **Test on Dev** - Never run migrations directly on production
3. **Coordinate with Team** - Notify everyone before changes
4. **Monitor Logs** - Watch for errors during/after migration

### During Migration
- Keep old collections for 24-48 hours
- Monitor error rates
- Check cache hit rates
- Verify balance accuracy

### After Migration
- Run full test suite
- Check production metrics
- Delete old collections only after verification
- Document any issues

---

## 📞 SUPPORT

### Questions?
1. Check `PHASE1_COLLECTION_RENAME.md` for detailed steps
2. Check `SPLITWISE_ARCHITECTURE_PLAN.md` for design decisions
3. Check `CURRENT_FLOW_ANALYSIS.md` for understanding current issues

### Need Help?
Contact the team with:
- Which phase you're on
- Error messages (if any)
- Current metric values
- Expected vs actual behavior

---

## ✅ SUCCESS CRITERIA

### Phase 1 Complete When:
- [ ] All collections renamed to `expense_*`
- [ ] Backend code updated
- [ ] Migration script tested
- [ ] Production migrated
- [ ] All tests passing
- [ ] No errors in logs

### Full Project Complete When:
- [ ] <15 reads per complete flow
- [ ] 90%+ cache hit rate
- [ ] <200ms P95 response time
- [ ] $60+/month cost savings
- [ ] All 7 phases completed

---

## 🎯 GET STARTED

**Right now, you can:**

1. **Review the plans** - Read all 3 documents
2. **Ask questions** - Clarify anything unclear
3. **Start Phase 1** - Follow `PHASE1_COLLECTION_RENAME.md`

**I recommend starting with Phase 1** since it's the foundation for all other phases.

---

**Ready to optimize? Let's make TripRaft as fast as Splitwise! 🚀**
