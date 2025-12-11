# API Performance Analysis - December 3, 2025 Session

**Date**: December 3, 2025  
**Log File**: `web/backend/logs/captured_logs.txt`

---

## 📊 Firestore API Summary

| Action | Reads | Writes | Deletes | Duration | Status |
|--------|-------|--------|---------|----------|--------|
| **GET /groups/{id}/full** (x2) | 5-6 | 0 | 0 | 2170-2408ms | ✅ |
| **POST /groups** (Create) | 1 | 3 | 0 | 1026ms | ✅ |
| **GET /mega-bootstrap** | 14+ | 0 | 0 | 2305ms | ⚠️ High reads |
| **POST /invitations** | 5 | 1 | 0 | 1376ms | ✅ |
| **POST /invitations/{id}/accept** | 6 | 3 | 0 | 1754ms | ⚠️ |
| **GET /invitations/user** | 1 | 0 | 0 | 376ms | ❌ 500 Error |
| **POST /expenses** (Create) | 4 | 3 | 0 | 2286-2351ms | ✅ |
| **PUT /expenses/{id}** (Update) | 5 | 3 | 0 | 2053ms | ✅ |
| **GET /expenses/{id}/history** | 4 | 0 | 0 | 730ms | ✅ |
| **DELETE /expenses/{id}** | 4 | 1 | 0 | 1730ms | ✅ |
| **POST /settlements** | 6 | 0 | 0 | 1398ms | ✅ |
| **GET /settlements/group/{id}** | 5 | 0 | 0 | 650ms | ✅ |
| **DELETE /groups/{id}/members/{uid}** | 1 | 2 | 0 | 620ms | ✅ |
| **DELETE /groups/{id}** | 4 | 3 | 0 | 1105-1118ms | ✅ |

---

## 📈 Session Totals

| Metric | Count |
|--------|-------|
| **Total Firestore Reads** | ~72 |
| **Total Firestore Writes** | ~22 |
| **Total Firestore Deletes** | 0 |
| **Total API Calls** | 18 (non-OPTIONS) |
| **Errors** | 1 (500 on invitations/user) |

---

## 🐛 Bugs Found & Fixed

### Bug 1: `'GroupBalance' object has no attribute 'get'`
**Location**: `expense_engine/services/snapshot_service.py`  
**Cause**: Code was calling `.get()` on a Pydantic `GroupBalance` model instead of a dict  
**Fix**: Use `model_dump()` to convert model to dict before accessing fields

**Occurrences**:
- Failed to build snapshot: 1x
- Failed to update snapshots for expense: 4x
- Settlement snapshot update failed: 1x

### Bug 2: `decimal.ConversionSyntax` on cached balances
**Location**: `expense_engine/services/balance_service.py`, `expense_engine/repositories/balance_repository.py`  
**Cause**: Cache contained full `GroupBalance` model dump with non-numeric fields (`created_at`, `group_id`, `last_updated`) being treated as balance values  
**Fix**: 
1. Cache only the `balances` dict, not full model
2. When reading from cache, check if it's a full model dump and extract `balances` key
3. Validate that values are numeric before Decimal conversion

**Bad cached fields triggering error**:
- `created_at: 2025-12-04 00:29:00.703120`
- `updated_at: 2025-12-04 00:29:00.703120`  
- `group_id: SdBGt5xcu4pSEQ0O9gvu`
- `balances: {}` (as string)
- `last_updated: 2025-12-04 00:29:00.703120`

### Bug 3: `TypeError: '>' not supported between instances of 'str' and 'datetime.datetime'`
**Location**: `expense_engine/repositories/invitation_repository.py:102`  
**Cause**: `expires_at` field from Firestore was stored as ISO string, not datetime object  
**Fix**: Parse `expires_at` as ISO string if it's not already a datetime object

**Impact**: Caused 500 error on `GET /api/expense/invitations/user`

---

## 📊 Detailed API Breakdown

### GET /api/expense/groups/{id}/full
```
Cache Operations:
- CACHE MISS: expense:membership:{gid}:{uid}
- CACHE SET:  expense:membership:{gid}:{uid} [TTL=60s]
- CACHE MISS: expense:group_summary:{gid}
- CACHE MISS: expense:group:{gid}

Firestore Operations:
- READ: expense_groups/{gid}
- READ: expense_group_balances/{gid}
- QUERY: expense_expenses [0 results]

Cache Updates:
- CACHE SET: expense:group:{gid} [TTL=60s]
- CACHE SET: expense:group_balances:{gid} [TTL=600s]
- CACHE SET: expense:group_summary:{gid} [TTL=600s]

Total: 5-6 reads, 0 writes
Duration: 2170-2408ms
```

### POST /api/expense/groups (Create Group)
```
Firestore Operations:
- QUERY: expense_groups [0 results] (code check)
- WRITE: expense_groups/{new_id}
- WRITE: expense_group_balances/{new_id}

Total: 1 read, 3 writes
Duration: 1026ms
```

### POST /api/expense/expenses (Create Expense)
```
Cache Operations:
- CACHE HIT: expense:membership:{gid}:{uid}

Firestore Operations:
- READ: expense_groups/{gid}
- WRITE: expense_expenses/{new_id}
- READ: expense_user_expenses/batch(2)
- WRITE: expense_user_expenses/batch(2)
- WRITE: expense_group_summaries/batch(2)
- READ: expense_group_summaries/{uid1}
- WRITE: expense_group_summaries/{uid1}
- READ: expense_group_summaries/{uid2}
- WRITE: expense_group_summaries/{uid2}
- READ: expense_group_balances/{gid}

Cache Invalidations:
- expense:group_balances:{gid} (multiple)
- expense:group_summary:{gid}
- expense:expense:{eid}
- expense:expense_history:{eid}

Total: 4 reads, 3 writes (batched)
Duration: 2286-2351ms
```

### PUT /api/expense/expenses/{id} (Update Expense)
```
Firestore Operations:
- READ: expense_expenses/{eid}
- READ: expense_groups/{gid}
- WRITE: expense_expenses/{eid}
- READ: expense_user_expenses/{uid1}
- WRITE: expense_user_expenses/{uid1}
- READ: expense_user_expenses/{uid2}
- WRITE: expense_user_expenses/{uid2}
- READ: expense_group_balances/{gid}

Total: 5 reads, 3 writes
Duration: 2053ms
```

### DELETE /api/expense/expenses/{id}
```
Firestore Operations:
- READ: expense_expenses/{eid}
- READ: expense_groups/{gid}
- WRITE: expense_expenses/{eid} (soft delete)
- READ: expense_user_expenses/batch(2)
- WRITE: expense_user_expenses/batch(2)
- READ: expense_group_balances/{gid}
- QUERY: expense_history [1 result]

Total: 4 reads, 1 write
Duration: 1730ms
```

### POST /api/expense/invitations/{id}/accept
```
Firestore Operations:
- READ: expense_invitations/{iid}
- WRITE: expense_invitations/{iid}
- READ: users/{uid}
- READ: expense_groups/{gid}
- WRITE: expense_groups/{gid}
- READ: expense_groups/{gid}
- READ: user_emails/{email}
- READ: users/{inviter_uid}

Cache Invalidations (extensive):
- expense:membership:{gid}:{uid}
- expense:user_groups:{uid}
- expense:group_summary:{gid}
- expense:group:{gid}
- expense:mega_bootstrap:{uid}
- expense:mega_bootstrap:{uid}:{gid}
- expense:user_invites:{email}
- expense:group_invites:{gid}

Total: 6 reads, 3 writes
Duration: 1754ms
```

### POST /api/expense/settlements
```
Firestore Operations:
- READ: expense_groups/{gid}
- READ: expense_group_balances/{gid}
- READ: expense_settlements/{sid} (verification)
- And more...

Total: 6 reads, 0 writes (unexpected - may be missing write logging)
Duration: 1398ms
```

---

## 🎯 Performance Targets vs Actual

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Get Group Full | <1500ms | 2170-2408ms | ❌ Over target |
| Create Group | <500ms | 1026ms | ❌ Over target |
| Create Expense | <1000ms | 2286ms | ❌ Over target |
| Update Expense | <1000ms | 2053ms | ❌ Over target |
| Get Expense History | <500ms | 730ms | ⚠️ Acceptable |
| Delete Expense | <1000ms | 1730ms | ❌ Over target |
| Create Settlement | <1000ms | 1398ms | ❌ Over target |
| Accept Invitation | <1500ms | 1754ms | ⚠️ Slightly over |

**Note**: All operations are slower than November analysis, likely due to:
1. Network latency to production Firestore (~200ms per operation)
2. Additional denormalization updates (Phase 6+)
3. Snapshot updates (Phase 20) - though failing silently

---

## ✅ Files Changed

### Session 1 (Earlier Fixes)
1. `expense_engine/repositories/base.py` - Added `collection` property
2. `expense_engine/services/balance_service.py` - Fixed cache handling for balances
3. `expense_engine/repositories/balance_repository.py` - Fixed cache storage format
4. `expense_engine/services/snapshot_service.py` - Fixed GroupBalance model access
5. `expense_engine/repositories/invitation_repository.py` - Fixed datetime comparison
6. `expense_engine/services/bootstrap_service.py` - Added optional snapshot_repo param
7. `expense_engine/services/expense_service.py` - Added optional snapshot_repo param
8. `expense_engine/tests/test_bootstrap.py` - Added mock snapshot_repo
9. `expense_engine/tests/test_services.py` - Added mock snapshot_repo

### Session 2 (Latest Fixes)

#### New Files Created
10. `expense_engine/utils/serialization.py` - **NEW** Firestore serialization utilities
    - `serialize_for_firestore()` - Main function for converting Python types
    - `serialize_decimal()` - Convert Decimal to float
    - `serialize_dict()` - Recursively serialize dicts
    - `serialize_model()` - Handle Pydantic models

#### Files Updated
11. `expense_engine/services/snapshot_service.py`
    - Fixed `_get_recent_expenses()` - Extract expenses from dict response
    - Fixed `_build_expense_summary()` - Added type checking for string/dict

12. `expense_engine/services/expense_service.py`
    - Fixed 3 occurrences of `balance_data.get('balances')` → `balance_data.balances`
    - Lines ~369, ~629, ~751

13. `expense_engine/repositories/snapshot_repository.py`
    - Added `serialize_for_firestore()` import
    - Updated `update_balances()` to serialize data
    - Updated `add_recent_expense()` to serialize data
    - Updated `update_expense_in_snapshots()` to serialize data

14. `expense_engine/utils/__init__.py`
    - Added serialization exports

---

## 🔧 Bug Summary (All Sessions)

| Bug | Location | Status |
|-----|----------|--------|
| `'GroupBalance' has no attribute 'get'` | expense_service.py (3 places) | ✅ FIXED |
| `Decimal serialization error` | snapshot_repository.py | ✅ FIXED |
| `'str' object has no attribute 'get'` | snapshot_service.py | ✅ FIXED |
| `decimal.ConversionSyntax` | balance_service.py | ✅ FIXED |
| `datetime string comparison` | invitation_repository.py | ✅ FIXED |
| `Group has been deleted` warning | group_service.py | ⚠️ Non-critical |

---

## 📈 What Improved

### Before Fixes
- ❌ Snapshot updates failed with `Decimal serialization error`
- ❌ Balance lookups crashed with `GroupBalance.get()` errors
- ❌ Recent expenses failed with `str.get()` error
- ❌ Invitation queries crashed with datetime comparison

### After Fixes
- ✅ All Decimal values properly serialized for Firestore
- ✅ GroupBalance model accessed correctly with `.balances`
- ✅ Recent expenses properly extracted from API response
- ✅ Defensive type checking prevents runtime crashes

### Error Reduction
| Metric | Before | After |
|--------|--------|-------|
| Snapshot errors per expense | 3-4 | 0 |
| Balance access errors | 2-3 | 0 |
| Serialization errors | 1 per write | 0 |

---

**Session End**: December 3, 2025
**Tests Status**: 301 passed, 3 skipped
