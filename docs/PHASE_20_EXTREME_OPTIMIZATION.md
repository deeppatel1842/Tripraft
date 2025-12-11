# Phase 20: Extreme Firestore Optimization

**Target:** Complete session in **10 total Firestore operations**  
**Session:** Create Group → Send Invitation → Accept Invitation → Create Expense → Edit Expense → View History → Create Settlement → View Settlements

---

## Test Results (December 5, 2025 - Latest Session)

### Actual Performance Measured (Full Session Analysis)

| Operation | Reads | Writes | Total | Duration | Target | Status |
|-----------|-------|--------|-------|----------|--------|--------|
| Create Group | 2 | 3 | 5 | 1538ms | 4 | +1 |
| Mega Bootstrap (after group) | 2 | 1 | 3 | 1726ms | 1 | +2 |
| Send Invitation | 6 | 1 | 7 | 1432ms | 6 | +1 |
| Accept Invitation | 4 | 4 | 8 | 1365ms | 7 | OK |
| Create Expense | 4 | 5 | 9 | 2803ms | 9 | MATCH |
| Edit Expense | 6 | 5 | 11 | 2407ms | 10 | +1 |
| Delete Expense | 6 | 3 | 9 | ~2000ms | - | - |
| Create Settlement | 5 | 1 | 6 | ~1500ms | 5 | +1 |
| Get Settlements | 6 | 0 | 6 | ~500ms | 1 | +5 |
| Remove Member | 2 | 2 | 4 | 699ms | - | OK |
| Delete Group | 4 | 3 | 7 | 1213ms | - | OK |
| **TOTAL SESSION** | **~47** | **~28** | **~75** | - | **~42** | **+78%** |

### Session Flow Breakdown

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Full Session Test (December 5, 2025)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Create Group         │ 2R 3W = 5 ops  │ 1538ms  │ Group + Member + Balance
│ 2. Mega Bootstrap       │ 2R 1W = 3 ops  │ 1726ms  │ Dashboard fetch + cache
│ 3. Send Invitation      │ 6R 1W = 7 ops  │ 1432ms  │ Validation + create
│ 4. Accept Invitation    │ 4R 4W = 8 ops  │ 1365ms  │ Token decode + member add
│ 5. Create Expense       │ 4R 5W = 9 ops  │ 2803ms  │ Expense + balance + history
│ 6. Edit Expense         │ 6R 5W = 11 ops │ 2407ms  │ Fetch + update + balance
│ 7. Delete Expense       │ 6R 3W = 9 ops  │ ~2000ms │ Fetch + delete + balance
│ 8. Create Settlement    │ 5R 1W = 6 ops  │ ~1500ms │ Balance check + create
│ 9. Get Settlements      │ 6R 0W = 6 ops  │ ~500ms  │ Query settlements
│ 10. Remove Member       │ 2R 2W = 4 ops  │ 699ms   │ Member cleanup
│ 11. Delete Group        │ 4R 3W = 7 ops  │ 1213ms  │ Group + member cleanup
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase Comparison: Historical vs Current vs Target

| Operation | Phase 19.5 | Phase 20 (Pre) | Phase 20 (Post) | Target | Gap |
|-----------|------------|----------------|-----------------|--------|-----|
| Login/Bootstrap | 12 | 3 | 3 | 1 | +2 |
| Create Group | 4 | 5 | 5 | 4 | +1 |
| Send Invitation | 6 | 7 | 7 | 6 | +1 |
| Accept Invitation | 7 | 8 | 8 | 7 | +1 |
| Create Expense | 9 | 9 | 9 | 9 | MATCH |
| Edit Expense | 10 | 11 | 11 | 10 | +1 |
| Create Settlement | 5 | 6 | 6 | 5 | +1 |
| Get Settlements | 1 | 6 | 6 | 1 | +5 |
| **TOTAL** | **54** | **55** | **55** | **43** | **+28%** |

### Key Findings

1. **Cache System Working**
   - `[CACHE][S]` = Cache SET (600s TTL for bootstrap, 60s for groups)
   - `[CACHE][+]` = Cache HIT (membership, group data, balances)
   - `[CACHE][-]` = Cache MISS (triggers Firestore read)
   - `[CACHE][X]` = Cache INVALIDATION (proper cleanup)

2. **Dashboard Pre-Warming Active**
   ```
   [PREWARM] Dashboard pre-warmed for user X in 336ms
   [PREWARM] Dashboard pre-warmed for user X in 315ms
   [PREWARM] Dashboard pre-warmed for user X in 312ms
   ```

3. **Snapshot Updates Working**
   - `Updated document: expense_bootstrap_snapshots/...`
   - Multiple updates per operation (opportunity to batch)

4. **Email Integration Working**
   - `Email sent successfully` after invitation

### Bugs/Issues Identified

#### Critical Issues

| Issue | Impact | Root Cause | Fix |
|-------|--------|------------|-----|
| Get Settlements: 6R vs 1R | +5 extra reads | Not using Redis cache | Use cached settlements |
| Edit Expense: Extra read | +1 extra read | Re-fetching after update | Return computed data |
| Bootstrap: 3 ops vs 1 | +2 extra ops | Multiple snapshot updates | Batch writes |

#### Warnings in Logs

```
WARNING: [WARN] Places database not found - Places API will not be available
WARNING: Group Planner not available: cannot import name 'group_planner_bp'
WARNING: Admin routes not available: No module named 'api.admin_routes'
UserWarning: Detected filter using positional arguments. Prefer using the 'filter' keyword argument instead.
```

#### Error: Accessing Deleted Group

```
WARNING: Error in get_group: Group has been deleted
```
This occurs when frontend retries after group deletion - needs better error handling.

#### Bug: Multiple Pre-Warm Calls

```
[PREWARM] Dashboard pre-warmed for user X in 336ms
[PREWARM] Dashboard pre-warmed for user X in 315ms
[PREWARM] Dashboard pre-warmed for user X in 312ms
[PREWARM] Dashboard pre-warmed for user X in 325ms
```
Multiple pre-warm calls in quick succession - needs debouncing

---

## Current State vs Target

### Current (After Phase 19.5)
| Operation | Reads | Writes | Total |
|-----------|-------|--------|-------|
| Login/Bootstrap | 12 | 0 | 12 |
| Create Group | 1 | 3 | 4 |
| Send Invitation | 5 | 1 | 6 |
| Accept Invitation | 4 | 3 | 7 |
| Create Expense | 4 | 5 | 9 |
| Edit Expense | 5 | 5 | 10 |
| View History | 2 | 0 | 2 |
| Create Settlement | 3 | 2 | 5 |
| View Settlements | 1 | 0 | 1 |
| **TOTAL** | **37** | **19** | **56** |

### Target: 10 TOTAL
This requires a **complete architectural change**.

---

## Architecture: Single-Document Pattern + Redis-First

### Core Concept: 1 READ on login, 1 WRITE per mutation, CACHE EVERYTHING

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ useMutation │  │ useQuery    │  │ Optimistic  │             │
│  │ (writes)    │  │ (reads)     │  │ Updates     │             │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘             │
└─────────┼────────────────┼──────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           REDIS CACHE (Source of Truth for READS)       │   │
│  │                                                          │   │
│  │  user:{uid}:dashboard    = ALL data for dashboard       │   │
│  │  user:{uid}:groups       = All groups + balances        │   │
│  │  user:{uid}:invitations  = Pending invitations          │   │
│  │  group:{gid}:expenses    = All expenses in group        │   │
│  │  group:{gid}:settlements = All settlements              │   │
│  │  group:{gid}:history     = Recent history               │   │
│  │                                                          │   │
│  │  TTL: 1 hour (or until mutation invalidates)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│         CACHE HIT        │         CACHE MISS                   │
│              │           │              │                       │
│              ▼           │              ▼                       │
│        Return data       │     ┌────────────────────┐          │
│        (0 Firestore)     │     │   FIRESTORE        │          │
│                          │     │   (1 READ)         │          │
│                          │     │   + Cache result   │          │
│                          │     └────────────────────┘          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MUTATION HANDLER (WRITES)                   │   │
│  │                                                          │   │
│  │  1. Validate input (no reads needed)                    │   │
│  │  2. SINGLE Firestore write (batched)                    │   │
│  │  3. Update Redis cache immediately                      │   │
│  │  4. Return computed data (no re-read)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Session Flow: 10 Operations

### Operation 1: LOGIN (1 Read)
```
User logs in → mega-bootstrap endpoint
├── Redis: Check cache → MISS (first time)
└── Firestore: 1 READ from user_dashboard collection
    └── Returns: ALL groups, balances, invitations, recent activity
    └── Cache in Redis (TTL: 1 hour)
```

### Operation 2: CREATE GROUP (1 Write)
```
User creates group → POST /groups
├── Validation: In-memory (user_id from JWT)
├── Firestore: 1 BATCH WRITE
│   ├── expense_groups/{new_id}
│   ├── expense_group_members/{gid}_{uid}
│   └── expense_balances/{gid}
├── Redis: Update user:{uid}:groups
└── Return: Computed group data (no re-read)
```

### Operation 3: SEND INVITATION (1 Write)
```
User sends invitation → POST /invitations
├── Validation: Check group membership from Redis cache
├── Firestore: 1 WRITE to expense_invitations
├── Redis: Update group:{gid}:invitations
└── Return: Invitation data (computed)
```

### Operation 4: ACCEPT INVITATION (1 Write)
```
User B accepts → POST /invitations/{id}/accept
├── Validation: Invitation exists (from Redis or JWT token)
├── Firestore: 1 BATCH WRITE
│   ├── expense_invitations/{id} → status: accepted
│   ├── expense_groups/{gid}.members[] += user_id
│   ├── expense_group_members/{gid}_{uid}
│   └── expense_balances/{gid}.{uid} = 0
├── Redis: 
│   ├── Invalidate inviter's cache
│   ├── Create invitee's group cache
└── Return: Group data (computed from write)
```

### Operation 5: CREATE EXPENSE (1 Write)
```
User creates expense → POST /expenses
├── Validation: Group membership from Redis
├── Firestore: 1 BATCH WRITE
│   ├── expense_expenses/{new_id}
│   ├── expense_balances/{gid} → updated balances
│   └── expense_history/{exp_id}_{version}
├── Redis:
│   ├── Update group:{gid}:expenses
│   ├── Update group:{gid}:balances
│   ├── Update all members' user:{uid}:groups
└── Return: Expense + balance_deltas (computed)
```

### Operation 6: EDIT EXPENSE (1 Write)
```
User edits expense → PUT /expenses/{id}
├── Validation: Group membership + expense exists (Redis)
├── Firestore: 1 BATCH WRITE
│   ├── expense_expenses/{id} → updated
│   ├── expense_balances/{gid} → recomputed
│   └── expense_history/{id}_{version}
├── Redis: Update all caches
└── Return: Updated expense + balance_deltas
```

### Operation 7: VIEW HISTORY (0 Reads - from cache)
```
User views history → GET /expenses/{id}/history
├── Redis: Return from group:{gid}:history
└── No Firestore read (already cached from expense operations)
```

### Operation 8: CREATE SETTLEMENT (1 Write)
```
User settles → POST /settlements
├── Validation: Group membership + balances (Redis)
├── Firestore: 1 BATCH WRITE
│   ├── expense_settlements/{new_id}
│   └── expense_balances/{gid} → updated
├── Redis: Update all caches
└── Return: Settlement + balance_deltas
```

### Operation 9: VIEW SETTLEMENTS (0 Reads - from cache)
```
User views settlements → GET /settlements/group/{id}
├── Redis: Return from group:{gid}:settlements
└── No Firestore read
```

### Operation 10: REFRESH (1 Read, only if needed)
```
If user refreshes after cache expired → 1 mega-bootstrap read
```

---

## Total: 10 Operations

| Action | Reads | Writes | Total |
|--------|-------|--------|-------|
| Login (mega-bootstrap) | 1 | 0 | 1 |
| Create Group | 0 | 1 | 1 |
| Send Invitation | 0 | 1 | 1 |
| Accept Invitation | 0 | 1 | 1 |
| Create Expense | 0 | 1 | 1 |
| Edit Expense | 0 | 1 | 1 |
| View History | 0 | 0 | 0 |
| Create Settlement | 0 | 1 | 1 |
| View Settlements | 0 | 0 | 0 |
| (Refresh if needed) | 1 | 0 | 1 |
| **TOTAL** | **2** | **7** | **9-10** |

---

## Implementation Plan

### Phase 20.1: User Dashboard Document
Create a single document per user that contains ALL their data:

```python
# Collection: expense_user_dashboards/{user_id}
{
    "userId": "abc123",
    "lastUpdated": "2025-12-04T10:00:00Z",
    
    # All groups with embedded data
    "groups": {
        "group1": {
            "name": "Trip to Paris",
            "currency": "EUR",
            "memberCount": 3,
            "yourBalance": 50.00,
            "totalSpent": 1500.00,
            "isSettled": false,
            "members": [
                {"userId": "abc", "displayName": "John"},
                {"userId": "def", "displayName": "Jane"}
            ],
            "recentExpenses": [...],  # Last 10
            "settlements": [...]  # Last 10
        }
    },
    
    # Pending invitations
    "pendingInvitations": [
        {"id": "inv1", "groupName": "Trip", "inviterName": "John", ...}
    ],
    
    # Global stats
    "totalOwed": 150.00,
    "totalOwes": 50.00
}
```

### Phase 20.2: Batched Writes
Every mutation uses a single Firestore batch:

```python
def create_expense_extreme(self, data):
    batch = firestore.client().batch()
    
    # Write expense
    expense_ref = db.collection('expense_expenses').document()
    batch.set(expense_ref, expense_data)
    
    # Update balances
    balance_ref = db.collection('expense_balances').document(group_id)
    batch.update(balance_ref, computed_balances)
    
    # Write history
    history_ref = db.collection('expense_history').document()
    batch.set(history_ref, history_data)
    
    # SINGLE commit = 1 write operation billing
    batch.commit()
    
    # Update Redis (no Firestore read)
    self._update_all_caches(group_id, expense_data, computed_balances)
    
    return computed_response  # No re-read needed
```

### Phase 20.3: Redis-First Architecture
All reads go through Redis, fallback to single Firestore read:

```python
def get_dashboard(self, user_id):
    # Try Redis
    cached = redis.get(f"user:{user_id}:dashboard")
    if cached:
        return cached  # 0 Firestore operations
    
    # Cache miss: Single Firestore read
    dashboard = db.collection('expense_user_dashboards').document(user_id).get()
    
    # Cache for 1 hour
    redis.setex(f"user:{user_id}:dashboard", 3600, dashboard)
    
    return dashboard  # 1 Firestore operation
```

### Phase 20.4: Invitation Token Pattern
Instead of looking up invitations, use signed JWT tokens:

```python
def send_invitation(self, group_id, email):
    # Create invitation JWT (contains all needed data)
    token = jwt.encode({
        'group_id': group_id,
        'group_name': group_name,  # From cache, no read
        'inviter_id': current_user.id,
        'inviter_name': current_user.name,
        'invitee_email': email,
        'exp': datetime.utcnow() + timedelta(days=7)
    }, SECRET_KEY)
    
    # 1 write to Firestore (for audit/list)
    db.collection('expense_invitations').add({...})
    
    # Send email with token
    send_invitation_email(email, token)
    
    return {'token': token}

def accept_invitation(self, token):
    # Decode token - NO FIRESTORE READ
    data = jwt.decode(token, SECRET_KEY)
    
    # 1 batch write
    batch = db.batch()
    batch.update(invitation_ref, {'status': 'accepted'})
    batch.update(group_ref, {'members': ArrayUnion([user_id])})
    batch.set(member_ref, member_data)
    batch.commit()
    
    # Update caches
    return computed_group_data
```

---

## Implementation Checklist

### Backend Changes

- [ ] **Create `expense_user_dashboards` collection**
  - Single document per user with all data
  - Updated on every mutation

- [ ] **Modify `get_bootstrap_data()` → `get_dashboard_single_read()`**
  - Read single document instead of multiple queries
  - Cache in Redis for 1 hour

- [ ] **Convert all mutations to batch writes**
  - `create_group()` → 1 batch write
  - `send_invitation()` → 1 batch write  
  - `accept_invitation()` → 1 batch write
  - `create_expense()` → 1 batch write
  - `update_expense()` → 1 batch write
  - `create_settlement()` → 1 batch write

- [ ] **Implement Redis cache invalidation**
  - On every write, update affected users' Redis cache
  - No Firestore reads to get "updated" data

- [ ] **Add invitation JWT tokens**
  - Encode all needed data in token
  - Accept without looking up invitation

### Frontend Changes

- [ ] **Update `useExpenseQuery.js`**
  - Single mega-bootstrap call on login
  - All subsequent reads from query cache
  - Optimistic updates for all mutations

- [ ] **Cache persistence**
  - Store last dashboard state in localStorage
  - Use stale data while revalidating

---

## Risks and Mitigations

### Risk 1: Document Size Limit (1MB)
**Mitigation:** 
- Limit `recentExpenses` to 10 per group
- Limit `settlements` to 10 per group
- Archive old data to separate collection

### Risk 2: Cache Invalidation Complexity
**Mitigation:**
- Use event-driven invalidation
- Each write knows which users to invalidate
- Redis pub/sub for multi-instance

### Risk 3: Consistency During Failures
**Mitigation:**
- Write to Firestore first, then cache
- On cache failure, next read will refresh
- Idempotent operations

---

## Migration Path

### Week 1: Create Dashboard Collection
- Build `expense_user_dashboards` collection
- Backfill from existing data
- Parallel read (old + new)

### Week 2: Switch Reads
- Update mega-bootstrap to read single document
- Keep old endpoints as fallback
- Monitor performance

### Week 3: Batch Writes
- Convert mutations one by one
- Verify cache invalidation
- Remove redundant reads

### Week 4: Remove Old Code
- Delete multi-read bootstrap
- Delete redundant snapshot logic
- Update documentation

---

## Summary

**Current:** 56 operations per session  
**Target:** 10 operations per session  
**Reduction:** 82%

**Key Architectural Changes:**
1. Single document per user (all data)
2. Every mutation = 1 batch write
3. Every read = Redis cache (0 Firestore)
4. JWT tokens for invitations (no lookup)
5. Computed responses (no re-reads)

This is achievable but requires significant refactoring. The ROI is excellent for apps with high user activity.

---

## Implementation Status Update (December 5, 2025)

### Completed Implementation

#### Backend Changes Made

| Component | Status | File(s) Modified |
|-----------|--------|------------------|
| Dashboard Service | CREATED | `expense_engine/services/dashboard_service.py` |
| Config Updates | DONE | `expense_engine/config.py` |
| Service Exports | DONE | `expense_engine/services/__init__.py` |
| Code Cleanup | DONE | `expense_engine/services/expense_service.py` |

#### Config Additions (`config.py`)

```python
# New collection
USER_DASHBOARDS = "expense_user_dashboards"

# Alias for consistency
BALANCES = GROUP_BALANCES  # Maps to "expense_group_balances"

# Cache keys
KEY_DASHBOARD = "dashboard:{user_id}"

# TTLs
TTL_DASHBOARD = 3600  # 1 hour for dashboard data
```

#### Dashboard Service Features (`dashboard_service.py`)

- `get_or_create_dashboard()` - Single document read with Redis caching
- `handle_group_created()` - Updates dashboard on group creation
- `handle_expense_created()` - Updates dashboard on expense creation
- `handle_settlement_created()` - Updates dashboard on settlement
- `invalidate_all_affected_caches()` - Batch cache invalidation
- `rebuild_dashboard()` - Full rebuild from Firestore

### Frontend Changes Made

| Component | Status | File(s) Modified |
|-----------|--------|------------------|
| Listener Naming | DONE | `firestoreListenerService.js` |
| Clear Prefixes | DONE | All logs now use `[EXPENSE-GROUP-LISTENER]` |

### Remaining Work

| Task | Priority | Complexity | Status |
|------|----------|------------|--------|
| JWT tokens for invitations | HIGH | Medium | DONE |
| Reduce invitation reads (7→3) | HIGH | Low | DONE |
| Dashboard pre-warming | HIGH | Low | DONE |
| Write-through cache | HIGH | Medium | DONE |
| Batch write consolidation | MEDIUM | Medium | PARTIAL |
| LocalStorage persistence | LOW | Low | NOT STARTED |
| Document size monitoring | LOW | Low | NOT STARTED |

---

## Phase 20.1-20.4 Implementation (December 5, 2025)

### Phase 20.1: JWT Invitation Tokens

**Files Created/Modified:**
- `expense_engine/utils/invitation_token.py` (NEW)
- `expense_engine/services/invitation_service.py` (MODIFIED)
- `expense_engine/routes/invitation_routes.py` (MODIFIED)
- `expense_engine/utils/__init__.py` (MODIFIED)

**How It Works:**

1. **Token Creation** (on send invitation):
```python
# In create_invitation():
token = create_invitation_token(
    invitation_id=invitation_id,
    group_id=group_id,
    group_name=group_name,
    inviter_id=inviter_id,
    inviter_name=inviter_name,
    invitee_email=invitee_email,
    role=role,
    expiry_days=7
)
```

2. **Token-Based Acceptance** (0 invitation reads):
```python
# In accept_invitation():
if invitation_token:
    token_data = decode_invitation_token(invitation_token)
    # All data from token - NO Firestore read!
    invitation_id = token_data['invitation_id']
    group_id = token_data['group_id']
    group_name = token_data['group_name']
```

**Expected Impact:**
| Operation | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Accept Invitation | 4R | 3R | -1 read |
| Send Invitation | 7R | 6R | -1 read (no re-read) |

### Phase 20.2: Combined Validation & Computed Responses

**Changes:**
- `create_invitation()` no longer calls `get_by_id()` at the end
- Returns computed response data instead of re-reading
- Response built from data already in memory

**Before:**
```python
# Old pattern (1 extra read)
self.invitation_repo.create(invitation_id, invitation.to_dict())
return self.invitation_repo.get_by_id(invitation_id)  # EXTRA READ
```

**After:**
```python
# New pattern (0 extra reads)
self.invitation_repo.create(invitation_id, invitation.to_dict())
return {
    'invitation_id': invitation_id,
    'group_id': group_id,
    'group_name': group_data.get('name'),
    # ... all data already in memory
}
```

**Expected Impact:**
| Operation | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Send Invitation | 7R | 6R | -1 read |

### Phase 20.3: Dashboard Pre-Warming on Login

**Files Modified:**
- `expense_engine/services/bootstrap_service.py` (MODIFIED)
- `expense_engine/middleware/auth.py` (MODIFIED)

**How It Works:**

1. **Auth Middleware** calls pre-warm after token verification:
```python
# In require_auth decorator:
bootstrap_service.prewarm_dashboard(
    user_id=decoded_token['uid'],
    user_email=decoded_token.get('email'),
    background=True  # Non-blocking
)
```

2. **Background Thread** fetches and caches all data:
```python
def prewarm_dashboard(self, user_id, user_email, background=True):
    # Runs in ThreadPoolExecutor
    self.get_bootstrap_data(
        user_id=user_id,
        user_email=user_email,
        force_refresh=True  # Ensure fresh data
    )
```

**Expected Impact:**
- First dashboard load: ~570ms (from cache, 1 read if miss)
- Subsequent loads: ~50ms (100% cache hit)
- Login response NOT blocked (background thread)

### Phase 20.4: Write-Through Cache Updates

**Files Created:**
- `expense_engine/utils/write_through_cache.py` (NEW)

**Key Functions:**
- `write_through_expense()` - Update expense cache after write
- `write_through_balances()` - Update balance cache after calculation
- `write_through_dashboard()` - Update dashboard cache after mutation
- `write_through_snapshot()` - Update snapshot cache after change

**Pattern:**
```python
# Old pattern: Invalidate + Re-read
firestore_write(data)
cache.delete(key)  # Invalidate
response = firestore_read(id)  # RE-READ (extra op!)

# New pattern: Write-through
firestore_write(data)
cache.set(key, data)  # Write-through (data already in memory)
response = data  # No re-read needed
```

**Expected Impact:**
| Operation | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Create Expense | 9 ops | 8 ops | -1 read |
| Edit Expense | 11 ops | 10 ops | -1 read |
| Create Settlement | 6 ops | 5 ops | -1 read |

---

## Expected Results After Phase 20.1-20.4

### Operation Comparison

| Operation | Phase 19.5 | Phase 20 (Before) | Phase 20.1-20.4 | Target |
|-----------|------------|-------------------|-----------------|--------|
| Login/Bootstrap | 12 | 1 | 0-1 | 1 |
| Create Group | 4 | 5 | 4 | 1 |
| Send Invitation | 6 | 8 | **5** | 1 |
| Accept Invitation | 7 | 8 | **5** | 1 |
| Create Expense | 9 | 9 | **8** | 1 |
| Edit Expense | 10 | 11 | **9** | 1 |
| Create Settlement | 5 | 6 | **5** | 1 |
| View History | 2 | 3 | 0-1 | 0 |
| View Settlements | 1 | 5 | 0-1 | 0 |
| **TOTAL** | **56** | **~66** | **~40** | **10** |

### Summary of Improvements

| Phase | Feature | Reads Saved | Notes |
|-------|---------|-------------|-------|
| 20.1 | JWT Tokens | 2/session | Accept + send invitation |
| 20.2 | Computed Responses | 2/session | No re-reads after writes |
| 20.3 | Pre-Warming | 1-12/session | Depends on cache state |
| 20.4 | Write-Through | 3-5/session | Per write operation |
| **Total** | | **8-21/session** | ~30% reduction |

### Files Changed Summary

| File | Changes |
|------|---------|
| `utils/invitation_token.py` | NEW: HMAC-SHA256 signed tokens |
| `utils/write_through_cache.py` | NEW: Write-through cache manager |
| `utils/__init__.py` | Exports for new modules |
| `services/invitation_service.py` | Token support + computed responses |
| `services/bootstrap_service.py` | Pre-warm functions |
| `middleware/auth.py` | Pre-warm on login |
| `routes/invitation_routes.py` | Token-based accept endpoint |

### Remaining Gap to Target

**Current:** ~40 operations/session  
**Target:** 10 operations/session  
**Gap:** 30 operations (75% of target)

**To Close the Gap:**
1. Implement single-document dashboard pattern (requires schema change)
2. Convert all mutations to single batch writes
3. Add Redis pub/sub for multi-instance cache invalidation
4. Implement invitation JWT for direct group join (skip invitation lookup)

---

*Document created: December 4, 2025*  
*Last updated: December 5, 2025 - Added Phase 20.1-20.4 implementation details + Full test results*

---

## Next Steps: Closing the Gap (Target vs Actual)

### Current Status

| Metric | Value |
|--------|-------|
| Current Total Ops | ~55/session |
| Target Total Ops | ~43/session |
| Gap | +28% (12 extra ops) |
| Status | **NEEDS OPTIMIZATION** |

### Priority 1: Fix Get Settlements (6R → 1R) - Save 5 reads

**Problem:** Get settlements not using Redis cache, doing 6 Firestore reads.

**Solution:**
```python
# In settlement_service.py - get_group_settlements()
def get_group_settlements(self, group_id, user_id):
    # Check Redis first
    cache_key = f"expense:group_settlements:{group_id}"
    cached = self.cache_manager.get(cache_key) if CACHE_ENABLED else None
    
    if cached:
        return cached  # 0 Firestore reads
    
    # Cache miss - fetch and cache
    settlements = self._fetch_settlements(group_id)
    self.cache_manager.set(cache_key, settlements, ttl=300)
    return settlements
```

**Expected Impact:** -5 reads per "Get Settlements" call

### Priority 2: Debounce Pre-Warm Calls - Save 2-3 ops

**Problem:** Multiple pre-warm calls in quick succession (4 calls in 1 second).

**Solution:**
```python
# In auth.py - Add debounce
_prewarm_timestamps = {}

def should_prewarm(user_id):
    last = _prewarm_timestamps.get(user_id, 0)
    now = time.time()
    if now - last > 60:  # Only prewarm every 60 seconds
        _prewarm_timestamps[user_id] = now
        return True
    return False
```

**Expected Impact:** -2-3 ops per session

### Priority 3: Return Computed Data on Edit - Save 1 read

**Problem:** Edit expense re-reads expense after update.

**Solution:**
```python
# In expense_service.py - update_expense()
def update_expense(self, expense_id, update_data, user_id):
    # ... update logic ...
    
    # Don't re-read, return computed
    return {
        'expense': {**existing_expense, **update_data},
        'balance_deltas': calculated_deltas,
        'updated_at': datetime.utcnow().isoformat()
    }
```

**Expected Impact:** -1 read per edit

### Priority 4: Batch Snapshot Updates - Save 2 writes

**Problem:** Multiple snapshot updates per operation.

**Solution:**
```python
# Consolidate snapshot updates into single batch
def update_snapshot_batch(self, updates: list):
    batch = db.batch()
    for update in updates:
        ref = db.collection('expense_bootstrap_snapshots').document(update['user_id'])
        batch.update(ref, update['data'])
    batch.commit()  # Single write operation
```

**Expected Impact:** -2 writes per mutation

### Priority 5: Use Invitation Token for Accept - Save 1-2 reads

**Problem:** Token-based accept not being used by frontend.

**Solution:**
- Frontend should send token in accept request body
- Backend already supports `/accept-by-token` endpoint

**Expected Impact:** -1-2 reads per invitation accept

### Summary: Expected Impact After Fixes

| Fix | Reads Saved | Writes Saved | Priority |
|-----|-------------|--------------|----------|
| Get Settlements Cache | -5 | 0 | HIGH |
| Debounce Pre-Warm | -2 | -1 | HIGH |
| Computed Edit Response | -1 | 0 | MEDIUM |
| Batch Snapshots | 0 | -2 | MEDIUM |
| Token-Based Accept | -2 | 0 | LOW |
| **TOTAL** | **-10** | **-3** | |

### Projected Performance After Fixes

| Operation | Current | After Fixes | Target |
|-----------|---------|-------------|--------|
| Bootstrap | 3 | 1 | 1 |
| Create Group | 5 | 4 | 4 |
| Send Invitation | 7 | 6 | 6 |
| Accept Invitation | 8 | 6 | 7 |
| Create Expense | 9 | 9 | 9 |
| Edit Expense | 11 | 10 | 10 |
| Create Settlement | 6 | 5 | 5 |
| Get Settlements | 6 | **1** | 1 |
| **TOTAL** | **55** | **42** | **43** |

### Timeline

| Week | Task | Impact |
|------|------|--------|
| Week 1 | Fix Get Settlements caching | -5 reads |
| Week 1 | Add pre-warm debouncing | -3 ops |
| Week 2 | Computed edit responses | -1 read |
| Week 2 | Batch snapshot updates | -2 writes |
| Week 3 | Frontend token integration | -2 reads |
| Week 3 | Testing & verification | - |

---

## Appendix: Log Analysis Details

### Cache Key Legend

| Key Pattern | Description | TTL |
|-------------|-------------|-----|
| `expense:bootstrap:{user_id}` | User dashboard data | 600s |
| `expense:group:{group_id}` | Group details | 60s |
| `expense:group_balances:{group_id}` | Balance calculations | 60s |
| `expense:membership:{group_id}:{user_id}` | Membership check | 300s |
| `expense:group_invites:{group_id}` | Group invitations | 300s |
| `expense:group_settlements:{group_id}` | Settlements list | 300s |
| `expense:mega_bootstrap:{user_id}` | Full bootstrap data | 600s |

### Log Symbol Legend

| Symbol | Meaning |
|--------|---------|
| `[CACHE][+]` | Cache HIT |
| `[CACHE][-]` | Cache MISS |
| `[CACHE][S]` | Cache SET |
| `[CACHE][X]` | Cache INVALIDATION |
| `[PREWARM]` | Dashboard pre-warming |
| `NR NW ND` | N Reads, N Writes, N Deletes |

---

## PHASE 21: TRUE 10-OPERATION ARCHITECTURE

### The Problem: Why 55 Operations Instead of 10

Current system makes **individual Firestore calls** for every piece of data:

| What Happens Now | Reads | Why |
|------------------|-------|-----|
| Bootstrap: Fetch user | 1 | user document |
| Bootstrap: Query groups | 1+ | expense_groups query |
| Bootstrap: Query invitations | 1 | expense_invitations query |
| Create Group: Check user exists | 1 | validation read |
| Create Group: Write group | - | 1 write |
| Create Group: Write member | - | 1 write |
| Create Group: Write balance | - | 1 write |
| Send Invitation: Check membership | 1 | membership lookup |
| Send Invitation: Check invitee user | 1 | user lookup |
| Send Invitation: Check email | 1 | email lookup |
| Accept: Read invitation | 1 | invitation document |
| Accept: Read group | 1 | group document |
| Create Expense: Check membership | 1 | membership lookup |
| Create Expense: Read balance | 1 | balance document |
| Edit Expense: Read expense | 1 | expense document |
| Get Settlements: Query settlements | 1 | settlements query |
| Get Settlements: Read members | N | member lookups |

**Total: 55+ operations per typical session**

---

### The Solution: Single Document Pattern

**ONE document per user contains EVERYTHING:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│           expense_user_dashboards/{user_id}                             │
│                                                                         │
│  {                                                                      │
│    "user_id": "abc123",                                                 │
│    "updated_at": "2025-12-05T12:00:00Z",                               │
│                                                                         │
│    "groups": {                                                          │
│      "grp_001": {                                                       │
│        "name": "Trip to Paris",                                         │
│        "currency": "EUR",                                               │
│        "created_by": "abc123",                                          │
│        "members": [                                                     │
│          {"user_id": "abc123", "name": "John", "role": "owner"},        │
│          {"user_id": "def456", "name": "Jane", "role": "member"}        │
│        ],                                                               │
│        "balances": {"abc123": 50.00, "def456": -50.00},                 │
│        "total_spent": 1500.00,                                          │
│        "is_settled": false,                                             │
│        "recent_expenses": [...20 items...],                             │
│        "recent_settlements": [...10 items...],                          │
│        "recent_history": [...20 items...]                               │
│      }                                                                  │
│    },                                                                   │
│                                                                         │
│    "pending_invitations": [                                             │
│      {                                                                  │
│        "id": "inv_001",                                                 │
│        "group_name": "Beach Trip",                                      │
│        "inviter_name": "Mike",                                          │
│        "token": "eyJ...",   // JWT for zero-read accept                 │
│        "expires_at": "..."                                              │
│      }                                                                  │
│    ],                                                                   │
│                                                                         │
│    "summary": {                                                         │
│      "total_owed_to_you": 150.00,                                       │
│      "total_you_owe": 50.00,                                            │
│      "group_count": 3                                                   │
│    }                                                                    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

**Result:**
- Login: **1 READ** (this document)
- All other reads: **0 READS** (from Redis cache)
- All writes: **1 BATCH** each (updates this + source documents)

---

### 10-Operation Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         10-OPERATION SESSION                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: LOGIN (1 READ)                                                 │
│  ─────────────────────                                                  │
│  API: GET /api/expense/dashboard/extreme                                │
│  Firestore: expense_user_dashboards/{uid}.get()  → 1 READ              │
│  Redis: SET dashboard:{uid} → cache for 1 hour                          │
│  Response: ALL groups, members, balances, expenses, invitations         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Frontend receives EVERYTHING in ONE response                     │   │
│  │ → Hydrates ALL React Query caches                                │   │
│  │ → NO more API calls needed for reads                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 2-7: MUTATIONS (1 WRITE EACH)                                     │
│  ──────────────────────────────────                                     │
│                                                                         │
│  CREATE GROUP (1 Write)                                                 │
│  ├── Validate from Redis cache (0 reads)                               │
│  ├── batch.set(expense_groups/{new_id})                                │
│  ├── batch.set(expense_group_members/{gid}_{uid})                      │
│  ├── batch.set(expense_group_balances/{gid})                           │
│  ├── batch.update(expense_user_dashboards/{uid})                       │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
│  SEND INVITATION (1 Write)                                              │
│  ├── Validate membership from Redis (0 reads)                          │
│  ├── Generate JWT token with all data                                  │
│  ├── batch.set(expense_invitations/{new_id})                           │
│  ├── batch.update(expense_user_dashboards/{invitee})                   │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
│  ACCEPT INVITATION (1 Write)                                            │
│  ├── Decode JWT token (0 reads) → has group_id, inviter, etc.         │
│  ├── batch.update(expense_invitations/{id})                            │
│  ├── batch.set(expense_group_members/{gid}_{uid})                      │
│  ├── batch.update(expense_group_balances/{gid})                        │
│  ├── batch.update(expense_user_dashboards/{new_member})                │
│  ├── batch.update(expense_user_dashboards/{each_existing_member})      │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
│  CREATE EXPENSE (1 Write)                                               │
│  ├── Validate membership from Redis (0 reads)                          │
│  ├── Calculate balances in memory (0 reads)                            │
│  ├── batch.set(expense_expenses/{new_id})                              │
│  ├── batch.update(expense_group_balances/{gid})                        │
│  ├── batch.set(expense_history/{hist_id})                              │
│  ├── batch.update(expense_user_dashboards/{each_member})               │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
│  EDIT EXPENSE (1 Write)                                                 │
│  ├── Get expense from Redis (0 reads)                                  │
│  ├── Recalculate balances in memory (0 reads)                          │
│  ├── batch.update(expense_expenses/{id})                               │
│  ├── batch.update(expense_group_balances/{gid})                        │
│  ├── batch.set(expense_history/{hist_id})                              │
│  ├── batch.update(expense_user_dashboards/{each_member})               │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
│  CREATE SETTLEMENT (1 Write)                                            │
│  ├── Validate balances from Redis (0 reads)                            │
│  ├── batch.set(expense_settlements/{new_id})                           │
│  ├── batch.update(expense_group_balances/{gid})                        │
│  ├── batch.update(expense_user_dashboards/{payer})                     │
│  ├── batch.update(expense_user_dashboards/{payee})                     │
│  └── batch.commit() → 1 WRITE                                          │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 8: ALL READS (0 Operations)                                       │
│  ─────────────────────────────────                                      │
│  Get Groups → Redis cache → 0 Firestore                                 │
│  Get Expenses → Redis cache → 0 Firestore                               │
│  Get Settlements → Redis cache → 0 Firestore                            │
│  Get Invitations → Redis cache → 0 Firestore                            │
│  Get History → Redis cache → 0 Firestore                                │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 9: REFRESH IF NEEDED (1 Read max)                                 │
│  ───────────────────────────────────────                                │
│  If cache expired after 1 hour → re-read dashboard                      │
│  In practice: most sessions < 1 hour = 0 extra reads                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Operation Count Summary

| Action | Reads | Writes | Total |
|--------|-------|--------|-------|
| Login | **1** | 0 | 1 |
| View Groups | 0 | 0 | 0 |
| View Group Details | 0 | 0 | 0 |
| Create Group | 0 | **1** | 1 |
| Send Invitation | 0 | **1** | 1 |
| Accept Invitation | 0 | **1** | 1 |
| View Expenses | 0 | 0 | 0 |
| Create Expense | 0 | **1** | 1 |
| Edit Expense | 0 | **1** | 1 |
| View Settlements | 0 | 0 | 0 |
| Create Settlement | 0 | **1** | 1 |
| View History | 0 | 0 | 0 |
| Refresh (if needed) | 1 | 0 | 1 |
| **TOTAL** | **2** | **7** | **9-10** |

---

### Implementation Checklist

#### Backend (Python/Flask)

- [ ] **Phase 21.1: Dashboard Document Schema**
  ```python
  # Create expense_user_dashboards collection
  # Migration script to populate from existing data
  # Document size monitoring (1MB limit)
  ```

- [ ] **Phase 21.2: Extreme Bootstrap Endpoint**
  ```python
  # GET /api/expense/dashboard/extreme
  # Single document read
  # Returns ALL user data
  ```

- [ ] **Phase 21.3: Zero-Read Mutations**
  ```python
  # ExtremeGroupService.create_group() - 1 batch write
  # ExtremeExpenseService.create_expense() - 1 batch write  
  # ExtremeSettlementService.create_settlement() - 1 batch write
  # ExtremeInvitationService.accept_invitation() - 1 batch write
  ```

- [ ] **Phase 21.4: Write-Through Dashboard Updates**
  ```python
  # Every mutation updates ALL affected users' dashboards
  # Redis updated immediately after batch commit
  # Response includes computed data (no re-read)
  ```

#### Frontend (React)

- [ ] **Phase 21.5: Extreme Bootstrap Hook**
  ```javascript
  // useExtremeMegaBootstrap() - single API call
  // Hydrates ALL React Query caches
  // staleTime: Infinity (mutations update cache)
  ```

- [ ] **Phase 21.6: Optimistic Updates**
  ```javascript
  // All mutations update cache immediately
  // No refetch needed after mutation
  // Rollback on error
  ```

- [ ] **Phase 21.7: Remove Legacy Endpoints**
  ```javascript
  // Remove individual GET calls
  // Remove duplicate bootstrap calls
  // Single source of truth: extreme dashboard
  ```

---

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Document size limit (1MB) | Limit recent_expenses to 20, settlements to 10 |
| Stale data after cache miss | Instant refresh via dashboard re-read |
| Batch write failures | Transaction rollback, retry with exponential backoff |
| Dashboard update conflicts | Use field-level updates, not full document replace |
| Migration complexity | Parallel read (old + new) during transition |

---

### Timeline to 10 Operations

| Week | Milestone | Ops Saved |
|------|-----------|-----------|
| Week 1 | Dashboard document + extreme bootstrap | -30 reads |
| Week 2 | Zero-read mutations (batch writes) | -10 reads |
| Week 3 | Write-through cache integration | -5 reads |
| Week 4 | Frontend integration + cleanup | -10 reads |
| **Result** | **10 total operations** | **-55 ops** |

---

### Comparison: Before vs After

| Metric | Current (Phase 20) | Target (Phase 21) | Improvement |
|--------|-------------------|-------------------|-------------|
| Login reads | 3 | 1 | 67% |
| Mutation reads | 4-6 each | 0 | 100% |
| Total reads/session | ~47 | ~2 | 96% |
| Total writes/session | ~28 | ~7 | 75% |
| **Total ops/session** | **~75** | **~10** | **87%** |
| Firestore cost | $X | $0.13X | **87% reduction** |

---

## PHASE 21 IMPLEMENTATION STATUS (December 2025)

### Phase 21.1: Dashboard Document Schema - COMPLETED

**Files Created:**
- `expense_engine/services/extreme_dashboard_service.py` (NEW - 640 lines)
- `expense_engine/scripts/migrate_to_extreme_dashboard.py` (NEW - 400 lines)

**ExtremeDashboardService Methods:**
| Method | Purpose | Status |
|--------|---------|--------|
| `get_extreme_dashboard()` | Single document read, Redis-first | DONE |
| `_build_dashboard_from_existing_data()` | Build from source collections | DONE |
| `rebuild_user_dashboard()` | Public API for rebuilding | DONE |
| `invalidate_dashboard_cache()` | Cache invalidation | DONE |
| `update_dashboard_write_through()` | Write-through pattern | DONE |
| `batch_update_dashboards()` | Update multiple users | DONE |
| `check_document_size_limit()` | Monitor 1MB limit | DONE |

**Document Structure:**
```python
{
    "user_id": "abc123",
    "updated_at": "2025-12-XX",
    "groups": {
        "group_id": {
            "group_id": "...",
            "name": "...",
            "currency": "...",
            "members": [...],          # Embedded
            "balances": {...},          # Embedded
            "recent_expenses": [...],   # Last 20
            "recent_settlements": [...] # Last 10
        }
    },
    "pending_invitations": [...],
    "summary": {
        "total_owed_to_you": 0.0,
        "total_you_owe": 0.0,
        "net_balance": 0.0,
        "group_count": 0
    }
}
```

**Migration Script Features:**
- Batch migration with configurable batch size
- Dry-run mode for testing
- Progress tracking via JSON file
- Resume capability for partial migrations
- Document size validation (<1MB)

---

### Phase 21.2: Extreme Bootstrap Endpoint - COMPLETED

**Files Modified:**
- `expense_engine/routes/bootstrap_routes.py` (MODIFIED)
- `expense_engine/services/__init__.py` (MODIFIED)

**New Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/expense/extreme-dashboard` | GET | Single document read |
| `/api/expense/extreme-dashboard/rebuild` | POST | Force rebuild |

**Extreme Dashboard Route:**
```python
GET /api/expense/extreme-dashboard
Query params:
  - force_refresh: bool (bypass cache)

Response:
{
    "success": true,
    "data": {
        "user_id": "...",
        "groups": {...},
        "pending_invitations": [...],
        "summary": {...}
    },
    "meta": {
        "source": "cache" | "firestore",
        "read_count": 0 | 1,
        "fetch_time_ms": 50
    }
}
```

**Expected Performance:**
- Cache hit: 0 Firestore reads, ~50ms response
- Cache miss: 1 Firestore read, ~200-500ms response

---

### Phase 21.3: Zero-Read Mutations - NOT STARTED

**Planned Services:**
- `ExtremeGroupService` - 1 batch write for group creation
- `ExtremeExpenseService` - 1 batch write for expense CRUD
- `ExtremeSettlementService` - 1 batch write for settlement creation
- `ExtremeInvitationService` - 1 batch write for invitation accept

**Key Pattern:**
```python
def create_expense_extreme(self, data):
    batch = db.batch()
    
    # Write to source collections
    batch.set(expense_ref, expense_data)
    batch.update(balance_ref, computed_balances)
    batch.set(history_ref, history_data)
    
    # Update ALL affected users' dashboards
    for member_id in group_members:
        dashboard_ref = db.collection('expense_user_dashboards').document(member_id)
        batch.update(dashboard_ref, dashboard_updates)
    
    # SINGLE commit = 1 write operation billing
    batch.commit()
    
    # Update Redis (no Firestore read)
    for member_id in group_members:
        cache.update(f"extreme_dashboard:{member_id}", updates)
    
    return computed_response  # No re-read
```

---

### Phase 21.4: Frontend Integration - NOT STARTED

**Planned Changes:**
- `useExtremeDashboard()` hook - single API call on login
- Hydrate all React Query caches from extreme dashboard
- Remove redundant API calls
- Optimistic updates for all mutations

---

### Implementation Progress

| Phase | Task | Status | Impact |
|-------|------|--------|--------|
| 21.1 | Dashboard Document Schema | DONE | Foundation |
| 21.1 | ExtremeDashboardService | DONE | Core service |
| 21.1 | Migration Script | DONE | Data migration |
| 21.2 | Extreme Bootstrap Route | DONE | 1 read endpoint |
| 21.2 | Rebuild Route | DONE | Repair capability |
| 21.2 | Services __init__ | DONE | Exports |
| 21.3 | ExtremeGroupService | NOT STARTED | 1 write creates |
| 21.3 | ExtremeExpenseService | NOT STARTED | 1 write expenses |
| 21.3 | ExtremeSettlementService | NOT STARTED | 1 write settlements |
| 21.3 | ExtremeInvitationService | NOT STARTED | 1 write accepts |
| 21.4 | useExtremeDashboard | NOT STARTED | Frontend hook |
| 21.4 | Remove Legacy | NOT STARTED | Cleanup |

---

### Files Changed in Phase 21

| File | Change Type | Lines |
|------|-------------|-------|
| `services/extreme_dashboard_service.py` | NEW | ~640 |
| `scripts/migrate_to_extreme_dashboard.py` | NEW | ~400 |
| `routes/bootstrap_routes.py` | MODIFIED | +170 |
| `services/__init__.py` | MODIFIED | +3 |
| `config.py` | EXISTING | USER_DASHBOARDS already defined |

---

### Next Steps

1. **Run Migration Script** (Week 1)
   ```bash
   cd expense_engine/scripts
   python migrate_to_extreme_dashboard.py --dry-run
   python migrate_to_extreme_dashboard.py --batch-size 10
   ```

2. **Test Extreme Dashboard** (Week 1)
   - Call `GET /api/expense/extreme-dashboard`
   - Verify single read on cache miss
   - Verify 0 reads on cache hit

3. **Implement Phase 21.3** (Week 2)
   - Create ExtremeGroupService with batch writes
   - Update dashboard on every mutation
   - Test end-to-end flow

4. **Frontend Integration** (Week 3)
   - Create useExtremeDashboard hook
   - Remove legacy bootstrap calls
   - Test full session with 10 operations

---

*Last updated: December 2025 - Phase 21.1-21.2 completed*
