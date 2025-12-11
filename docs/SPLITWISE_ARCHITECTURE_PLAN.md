# 🚀 TripRaft Expense Engine - Splitwise Architecture Migration Plan

**Date:** November 24, 2025  
**Goal:** Reduce Firestore reads from ~100 to <15 per flow, achieve 90%+ cache hit rate  
**Approach:** Denormalize everything, precompute everything, cache everything

---

## 📊 CURRENT STATE ANALYSIS

### Current Firestore Structure (PROBLEMS)

```
users/                              # ✅ Shared collection
groups/                             # ❌ NO PREFIX - conflicts with Group Planner
  ├─ {group_id}
  └─ Fields: name, members[], owner_id, currency

group_members/                      # ❌ NO PREFIX
  └─ {group_id}_{user_id}

group_balances/                     # ❌ NO PREFIX
  └─ {group_id}
      └─ member_balances: {uid: balance}

expenses/                           # ❌ NO PREFIX - top level, NOT subcollection
  └─ {expense_id}
      └─ Fields: group_id, amount, paidBy, participants

settlements/                        # ❌ NO PREFIX
  └─ {settlement_id}

group_invitations/                  # ❌ NO PREFIX
  └─ {invitation_id}

group_summaries/                    # ❌ NO PREFIX (Phase 2.1 addition)
  └─ {user_id}_{group_id}
```

### Current Flow Issues

#### 1. **Heavy Reads on Group Load**
```python
GET /groups/full/{gid}
├─ groups/{gid} (1 read)
├─ group_members where group_id = gid (N reads for N members)
├─ users/{uid} for each member (N reads)
├─ expenses where group_id = gid (M reads for M expenses)
├─ settlements where group_id = gid (K reads)
└─ group_balances/{gid} (1 read)

Total: 1 + N + N + M + K + 1 = ~50-100 reads
```

#### 2. **Recalculation on Every Balance Request**
```python
# Current balance_manager.py
def get_group_balances(group_id):
    # Checks cache (good)
    # If miss → recalculates from ALL expenses (BAD)
    expenses = get_all_expenses(group_id)  # M reads
    for exp in expenses:
        calculate_splits()  # CPU intensive
    return balances
```

#### 3. **Repeated User Lookups**
```python
# get_user_groups called 57 times in logs
# Each call:
#   - Fetches group_members (N reads)
#   - Batch fetches groups (K reads)
#   - NO user display names cached
```

#### 4. **Delete Flow Chaos**
```python
# Cascade delete does:
# - Fetch group (1 read)
# - Fetch ALL expenses (M reads)
# - Delete each expense sequentially (M deletes)
# - Delete settlements (K reads + deletes)
# - Delete members (N deletes)
# - Delete balances (1 delete)
# Total: M+K+N+2 reads + M+K+N+2 deletes
```

#### 5. **No Pagination**
- Loads ALL expenses on group open
- 500 expenses = 500 reads + massive JSON payload
- No infinite scroll

---

## 🎯 SPLITWISE-STYLE ARCHITECTURE

### New Firestore Structure (WITH expense_ PREFIX)

```
users/                              # ✅ Shared (no prefix needed)

expense_groups/                     # ✨ NEW: Clear namespace
  └─ {group_id}
      ├─ name, currency, owner_id
      ├─ members: {uid: {role, joinedAt}}  # Denormalized map
      ├─ member_count: 5                   # Denormalized
      ├─ expense_count: 42                 # Denormalized
      ├─ total_spent: 1250.00              # Denormalized
      ├─ last_activity: timestamp          # For sorting
      └─ is_settled: false                 # Quick check

expense_group_balances/             # ✨ One doc per group
  └─ {group_id}
      ├─ balances: {uid: -25.5, uid2: 10.0}
      ├─ updatedAt: timestamp
      ├─ version: 42                       # Incremented on mutation
      └─ simplified_debts: [{from, to, amount}]

expense_group_summaries/            # ✨ One doc per user+group
  └─ {user_id}_{group_id}
      ├─ group_id, group_name
      ├─ my_balance: -25.5
      ├─ member_count: 5
      ├─ expense_count: 42
      ├─ last_activity: timestamp
      └─ updatedAt

expense_expenses/                   # ✨ Subcollection under groups
  └─ {group_id}/expenses/{expense_id}
      ├─ amount, description, category
      ├─ paid_by: uid
      ├─ split_type: "equal"
      ├─ participants: {uid: share}
      └─ createdAt

expense_settlements/                # ✨ Subcollection under groups
  └─ {group_id}/settlements/{settlement_id}

expense_invitations/                # ✨ Subcollection under users
  └─ {user_id}/invitations/{invite_id}
      ├─ group_id, status
      └─ invited_by
```

### Redis Keys & TTL Strategy

```python
# User-level caches
user_groups:{uid}:summary          # List of user's groups + my_balance
TTL: 60s                           # Short (changes when invited/kicked)

user_invites:{uid}                 # Pending invitations
TTL: 30s                           # Very short (UX sensitive)

display_name:{uid}                 # User's display name
TTL: 3600s                         # Long (rarely changes)

# Group-level caches
group_summary:{gid}                # Group metadata + members + balances + last 5 expenses
TTL: 60s                           # Medium (balances change frequently)

group_balances:{gid}               # Balance map only
TTL: 300s                          # Can be longer (used for validation)

group_expenses:{gid}:p:{page}      # Paginated expenses (page 0, 1, 2...)
TTL: 120s                          # Medium (new expenses added)

group_members:{gid}                # Member list with display names
TTL: 300s                          # Longer (members don't change often)

# Idempotency keys
idempotency:{key}                  # Duplicate prevention
TTL: 86400s                        # 24 hours
```

### Optimized Endpoints

#### Before (Current)
```
GET /groups              → 50 reads (all groups + members + users)
GET /groups/{gid}/full   → 100 reads (everything)
POST /expenses           → 15 reads (validation + balance recalc)
DELETE /groups/{gid}     → 200 reads (cascade fetch all)
```

#### After (Splitwise-style)
```
GET /user/summary        → 0-2 reads (Redis → expense_group_summaries)
GET /groups/{gid}        → 0-3 reads (Redis → expense_groups + expense_group_balances)
GET /groups/{gid}/expenses?page=0  → 0-1 read (Redis → paginated)
POST /expenses           → 2-3 reads (validate + update balances)
DELETE /groups/{gid}     → 5-10 reads (batch delete)
```

---

## 📋 SPLITWISE BALANCE ENGINE

### Current Problem
```python
# balance_manager.py recalculates from scratch
def _recalculate_and_cache_balance(group_id):
    expenses = get_all_expenses(group_id)  # M reads
    balances = {}
    for exp in expenses:
        # Recalculate splits
        for participant in exp.participants:
            balances[uid] += calculate_share()
    cache_balances(balances)
```

### Splitwise Solution: Incremental Updates
```python
# NEVER recalculate - always update incrementally

def add_expense(expense_data):
    # 1. Create expense doc
    # 2. Update balance document (transaction)
    transaction:
        balance_doc = get(expense_group_balances/{gid})
        for participant in participants:
            if participant == paid_by:
                delta = amount - share
            else:
                delta = -share
            balance_doc.balances[uid] += delta
        balance_doc.version += 1
        balance_doc.updated_at = now()
        set(balance_doc)
    
    # 3. Update group summary for all members
    for uid in participants:
        update(expense_group_summaries/{uid}_{gid}, {
            my_balance: balance_doc.balances[uid],
            expense_count: increment(1),
            total_spent: increment(amount)
        })
    
    # 4. Invalidate caches
    redis.delete(group_summary:{gid})
    for uid in participants:
        redis.delete(user_groups:{uid}:summary)
```

### Delete Expense Flow
```python
def delete_expense(expense_id):
    # 1. Fetch expense
    expense = get_expense(expense_id)
    
    # 2. Reverse the balance changes (transaction)
    transaction:
        balance_doc = get(expense_group_balances/{gid})
        for participant in expense.participants:
            # Reverse the original delta
            if participant == expense.paid_by:
                delta = -(expense.amount - share)
            else:
                delta = share
            balance_doc.balances[uid] += delta
        balance_doc.version += 1
        set(balance_doc)
    
    # 3. Update summaries
    # 4. Delete expense
    # 5. Invalidate caches
```

---

## 🔄 CACHE INVALIDATION MATRIX

| Operation | Firestore Writes | Redis Keys to Delete |
|-----------|------------------|---------------------|
| Create group | `expense_groups/{gid}`<br>`expense_group_balances/{gid}`<br>`expense_group_summaries/{uid}_{gid}` | `user_groups:{uid}:summary` |
| Invite member | `expense_invitations/{uid}/{id}` | `user_invites:{uid}`<br>`user_groups:{uid}:summary` |
| Accept invite | `expense_groups/{gid}.members`<br>`expense_group_summaries/{uid}_{gid}` | `group_summary:{gid}`<br>`group_members:{gid}`<br>`user_groups:{uid}:summary` |
| Add expense | `expense_expenses/{gid}/{eid}`<br>`expense_group_balances/{gid}`<br>All `expense_group_summaries/{uid}_{gid}` | `group_summary:{gid}`<br>`group_balances:{gid}`<br>`group_expenses:{gid}:p:*`<br>All `user_groups:{uid}:summary` |
| Delete expense | Same as add | Same as add |
| Add settlement | `expense_settlements/{gid}/{sid}`<br>`expense_group_balances/{gid}`<br>2 `expense_group_summaries` | `group_summary:{gid}`<br>`group_balances:{gid}`<br>2 `user_groups:{uid}:summary` |
| Delete group | Delete all subcollections<br>Delete summaries<br>Delete invitations | `group_*:{gid}`<br>All member `user_groups:{uid}:summary` |

---

## 📈 EXPECTED PERFORMANCE

### Current vs. Splitwise Architecture

| Flow | Current Reads | After Reads | Improvement |
|------|--------------|-------------|-------------|
| Home load | 50-74 | 2-5 | **92% ↓** |
| Open group | 100+ | 3-8 | **95% ↓** |
| Add expense | 15-25 | 3-5 | **80% ↓** |
| Delete group | 200+ | 10-15 | **95% ↓** |
| **Total Flow** | **~365** | **~18-33** | **~91% ↓** |

### Cache Hit Rates (Projected)
- First load: 0% (expected)
- Subsequent loads: **90-95%**
- Navigation within group: **98%**

---

## 🎯 MIGRATION PHASES

### Phase 1: Collection Renaming (CRITICAL)
**Goal:** Add `expense_` prefix to all collections

**Actions:**
1. Update `FirebaseCollections` constants
2. Update all `.collection()` calls
3. Create Firestore migration script
4. Run migration (copy data to new collections)
5. Verify data integrity
6. Delete old collections

**Expected Duration:** 2-3 hours  
**Risk:** Medium (data migration)

---

### Phase 2: Denormalized Balances
**Goal:** Stop recalculating balances from expenses

**Actions:**
1. Add `expense_group_balances` collection
2. Create migration script to populate initial balances
3. Update `add_expense()` to increment balances
4. Update `delete_expense()` to reverse balances
5. Update `add_settlement()` to adjust balances
6. Remove `_recalculate_and_cache_balance()` calls

**Expected Duration:** 4-6 hours  
**Risk:** High (balance accuracy critical)

---

### Phase 3: Group Summaries Everywhere
**Goal:** One read per user to get all groups

**Actions:**
1. Ensure `expense_group_summaries` exists for all members
2. Update on every mutation (expense, settlement, member change)
3. Create `GET /user/summary` endpoint
4. Update `GET /groups` to use summaries first

**Expected Duration:** 3-4 hours  
**Risk:** Low (already partially implemented)

---

### Phase 4: Paginated Expenses
**Goal:** Load 20 expenses at a time, not 500

**Actions:**
1. Move expenses to subcollection: `expense_groups/{gid}/expenses/`
2. Add pagination to `GET /groups/{gid}/expenses?page=0&limit=20`
3. Update frontend to infinite scroll
4. Cache each page separately

**Expected Duration:** 4-5 hours  
**Risk:** Medium (structural change)

---

### Phase 5: Optimized Endpoints
**Goal:** Split heavy endpoints into focused ones

**New Endpoints:**
```
GET /user/summary                  # User's groups + balances
GET /groups/{gid}                  # Group metadata + members
GET /groups/{gid}/balances         # Balance calculations only
GET /groups/{gid}/expenses?page=N  # Paginated expenses
GET /groups/{gid}/settlements      # Settlements with pagination
```

**Expected Duration:** 3-4 hours  
**Risk:** Low (backend only)

---

### Phase 6: Redis Strategy Overhaul
**Goal:** 90%+ cache hit rate

**Actions:**
1. Implement read-through cache pattern
2. Aggressive invalidation on writes
3. Separate TTLs for different data types
4. Pre-warm cache on group create

**Expected Duration:** 2-3 hours  
**Risk:** Low (improves performance)

---

### Phase 7: Smart Delete Flow
**Goal:** Fast, safe group deletion

**Actions:**
1. Batch delete expenses (10 at a time)
2. Parallel delete summaries
3. Cleanup orphaned data
4. Archive instead of delete (optional)

**Expected Duration:** 2-3 hours  
**Risk:** Low

---

## 📊 COLLECTION RENAME DETAILS

### Current Collections → New Collections

| Current | New | Notes |
|---------|-----|-------|
| `groups` | `expense_groups` | Add denormalized fields |
| `group_members` | Remove | Embed in `expense_groups.members` |
| `group_balances` | `expense_group_balances` | Add version field |
| `expenses` | `expense_groups/{gid}/expenses` | Move to subcollection |
| `settlements` | `expense_groups/{gid}/settlements` | Move to subcollection |
| `group_invitations` | `expense_invitations` | Keep flat for easy queries |
| `group_summaries` | `expense_group_summaries` | Already good structure |

### Denormalization Additions

**expense_groups:**
```python
{
    'name': 'Seattle Trip',
    'members': {
        'uid1': {'role': 'admin', 'joined_at': timestamp},
        'uid2': {'role': 'member', 'joined_at': timestamp}
    },
    'member_count': 2,              # NEW
    'expense_count': 15,            # NEW
    'total_spent': 450.00,          # NEW
    'last_activity': timestamp,     # NEW
    'is_settled': False             # NEW
}
```

**expense_group_balances:**
```python
{
    'group_id': 'gid',
    'balances': {
        'uid1': -25.50,
        'uid2': 10.00,
        'uid3': 15.50
    },
    'version': 42,                  # NEW - incremented on each mutation
    'updated_at': timestamp,
    'simplified_debts': [           # Precomputed
        {'from': 'uid1', 'to': 'uid3', 'amount': 25.50}
    ]
}
```

---

## 🔧 IMPLEMENTATION CHECKLIST

### Pre-Migration
- [ ] Backup Firestore database
- [ ] Notify users of maintenance window (if prod)
- [ ] Test migration script on dev environment

### Phase 1: Collection Rename
- [ ] Update `constants.py` FirebaseCollections
- [ ] Update all `firebase_operations.py` collection references
- [ ] Update `balance_manager.py` collection references
- [ ] Create migration script `migrate_collections.py`
- [ ] Run migration script
- [ ] Verify data in new collections
- [ ] Update frontend API calls (if needed)
- [ ] Delete old collections

### Phase 2: Balance Engine
- [ ] Create `expense_group_balances` migration script
- [ ] Update `add_expense()` to use incremental updates
- [ ] Update `delete_expense()` to reverse balances
- [ ] Update `add_settlement()` to adjust balances
- [ ] Remove recalculation logic
- [ ] Add balance version tracking
- [ ] Test all balance scenarios

### Phase 3: Summaries
- [ ] Ensure summaries exist for all members
- [ ] Update on every group mutation
- [ ] Create `GET /user/summary` endpoint
- [ ] Update `GET /groups` to use summaries
- [ ] Test summary accuracy

### Phase 4: Pagination
- [ ] Move expenses to subcollections
- [ ] Add pagination parameters to endpoints
- [ ] Implement frontend infinite scroll
- [ ] Cache paginated results
- [ ] Test with large expense lists

### Phase 5: Endpoints
- [ ] Create focused GET endpoints
- [ ] Split heavy endpoints
- [ ] Update frontend to use new endpoints
- [ ] Remove old endpoints (deprecate first)

### Phase 6: Redis
- [ ] Implement read-through pattern
- [ ] Add cache invalidation on all writes
- [ ] Tune TTLs per data type
- [ ] Monitor cache hit rates

### Phase 7: Delete Flow
- [ ] Batch delete expenses
- [ ] Parallel delete summaries
- [ ] Add cleanup verification
- [ ] Optional: Implement soft delete

---

## 🚨 RISKS & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during migration | Medium | Critical | Backup before migration, test on dev first |
| Balance calculation errors | High | Critical | Extensive testing, version tracking |
| Cache inconsistency | Medium | High | Aggressive invalidation, short TTLs initially |
| Frontend breaking changes | Low | Medium | Version API endpoints, gradual rollout |
| Performance regression | Low | Low | Monitor metrics, rollback plan |

---

## 📈 SUCCESS METRICS

### Before Migration
- Average reads per user session: **~365**
- Cache hit rate: **~40%**
- P95 response time: **800-1200ms**
- Firestore cost per 1000 users: **$15-25/day**

### After Migration (Target)
- Average reads per user session: **<30** (92% reduction)
- Cache hit rate: **>90%** (125% increase)
- P95 response time: **<200ms** (80% faster)
- Firestore cost per 1000 users: **<$3/day** (85% cost reduction)

---

## 🎯 NEXT STEPS

1. **Review this plan** with team
2. **Choose Phase 1 start date**
3. **Setup test environment**
4. **Create Phase 1 detailed tasks**
5. **Begin collection rename migration**

---

**Note:** This is a comprehensive plan. Each phase can be broken down further into sub-tasks during implementation.
