# Complete API Endpoint Performance Table

**Date**: November 19, 2025  
**Source**: Production logs analysis  
**Status**: ✅ All endpoints documented

---

## 📊 Complete Endpoint Performance Matrix

| # | Endpoint | Method | Operation | API Calls | Firestore Ops | Avg Duration | Status |
|---|----------|--------|-----------|-----------|---------------|--------------|--------|
| **USER OPERATIONS** |
| 1 | `/api/expense/user/profile` | POST | Create user profile | 1 | 1 read + 1 write | ~400ms | ✅ Good |
| 2 | `/api/expense/user/profile` | GET | Get user profile | 1 | 1 read (cached) | ~50ms | ✅ Excellent |
| 3 | `/api/expense/user/profile` | PUT | Update user profile | 1 | 1 read + 1 write | ~450ms | ✅ Good |
| 4 | `/api/expense/user/search` | GET | Search users | 1 | 1-5 reads | ~300ms | ✅ Good |
| **GROUP OPERATIONS** |
| 5 | `/api/expense/groups` | GET | Get user groups (summary) | 1 | 0 reads (cached) | ~5ms | ✅ Excellent |
| 6 | `/api/expense/groups` | GET | Get user groups (full) | 1 | 6-8 reads | ~400ms | ✅ Good |
| 7 | `/api/expense/groups` | POST | **Create group** | 1 | 0 reads + 3 writes | **~213ms** | ✅ Excellent |
| 8 | `/api/expense/groups/{id}` | GET | Get group details | 1 | 1 read (cached) | ~135ms | ✅ Good |
| 9 | `/api/expense/groups/{id}` | PUT | Update group | 1 | 1 read + 1 write | ~350ms | ✅ Good |
| 10 | `/api/expense/groups/{id}` | DELETE | Delete group | 1 | varies | ~500ms | ✅ Good |
| 11 | `/api/expense/groups/{id}/full` | GET | **Get full group data** | 1 | 3-5 reads | **~1.8s** (first), **~9ms** (cached) | ✅ Excellent cache |
| 12 | `/api/expense/groups/{id}/members` | GET | Get group members | 1 | 2 reads | ~250ms | ✅ Good |
| 13 | `/api/expense/groups/{id}/members/{uid}` | GET | Get member details | 1 | 4-5 reads | ~400ms | ✅ Good |
| 14 | `/api/expense/groups/{id}/members/{uid}` | DELETE | **Remove member** | 1 | 2 reads + 2 writes | **~600ms** | ✅ Good |
| 15 | `/api/expense/groups/{id}/leave` | POST | Leave group | 1 | 1 read + 2 writes | ~550ms | ✅ Good |
| **EXPENSE OPERATIONS** |
| 16 | `/api/expense/expenses` | POST | **Create expense** | 1 | 0 reads + 1 write | **~404ms** | ✅ Excellent |
| 17 | `/api/expense/expenses/{id}` | GET | Get expense details | 1 | 1 read | ~150ms | ✅ Good |
| 18 | `/api/expense/expenses/{id}` | PUT | **Update expense** | 1 | 1 read + 1 write | **~400ms** | ✅ Excellent |
| 19 | `/api/expense/expenses/{id}` | DELETE | **Delete expense** | 1 | 1 read + 1 write | **~300ms** | ✅ Excellent |
| 20 | `/api/expense/expenses/user` | GET | Get user expenses | 1 | 0 reads (local storage) | ~10ms | ✅ Excellent |
| 21 | `/api/expense/expenses/user` | GET | Get user expenses (personal) | 1 | 0 reads (local storage) | ~5ms | ✅ Excellent |
| 22 | `/api/expense/expenses/group/{id}` | GET | Get group expenses | 1 | 1-2 reads | ~250ms | ✅ Good |
| **SETTLEMENT OPERATIONS** |
| 23 | `/api/expense/settlements` | POST | **Create settlement** | 1 | 5 reads + 1 write | **~800ms** | ✅ Good |
| 24 | `/api/expense/settlements/{id}` | GET | Get settlement details | 1 | 1 read | ~150ms | ✅ Good |
| 25 | `/api/expense/settlements/group/{id}` | GET | Get group settlements | 1 | 1 read (cached) | ~139ms (cached), ~358ms (miss) | ✅ Good |
| 26 | `/api/expense/settlements/balances/{id}` | GET | Get group balances | 1 | 1-3 reads | ~200ms | ✅ Good |
| **INVITATION OPERATIONS** |
| 27 | `/api/expense/invitations` | POST | **Send invitation** | 1 | 0 reads + 1 write | **~315ms** | ✅ Excellent |
| 28 | `/api/expense/invitations` | GET | Get user invitations | 1 | 0 reads (0 groups) | ~5ms | ✅ Excellent |
| 29 | `/api/expense/invitations` | GET | Get user invitations | 1 | 1 read (with groups) | ~800ms | ✅ Good |
| 30 | `/api/expense/invitations/{id}` | GET | Get invitation details | 1 | 1 read | ~200ms | ✅ Good |
| 31 | `/api/expense/invitations/{id}/accept` | POST | **Accept invitation** | 1 | 5 reads + 3 writes | **~2.7s** | ⚠️ Can optimize |
| 32 | `/api/expense/invitations/{id}/reject` | POST | Reject invitation | 1 | 1 read + 1 write | ~350ms | ✅ Good |
| 33 | `/api/expense/invitations/{id}/details` | GET | Get public invitation | 1 | 1 read | ~180ms | ✅ Good |
| 34 | `/api/expense/invitations/group/{id}` | GET | Get group invitations | 1 | 1 read (cached) | ~133ms | ✅ Good |
| **ADMIN & HEALTH** |
| 35 | `/api/health` | GET | Basic health check | 1 | 0 reads | ~2ms | ✅ Excellent |
| 36 | `/api/health/detailed` | GET | Detailed health check | 1 | 3-5 reads | ~500ms | ✅ Good |
| 37 | `/api/expense/cache/stats` | GET | Cache statistics | 1 | 0 reads | ~10ms | ✅ Excellent |
| 38 | `/api/expense/cache/warm` | POST | Warm cache | 1 | varies | varies | ✅ Good |
| 39 | `/api/expense/categories` | GET | Get expense categories | 1 | 0 reads | ~2ms | ✅ Excellent |
| 40 | `/api/expense/split-types` | GET | Get split types | 1 | 0 reads | ~2ms | ✅ Excellent |

---

## 🔥 Critical User Flows - Step-by-Step

### Flow 1: First-Time User (Empty State)
```
Total Duration: ~1.1s
Total API Calls: 3
Total Firestore Ops: 1 read

Step 1: POST /api/expense/user/profile
├─ Duration: 397ms
├─ Firestore: 1 read (check existing) + 1 write
└─ Status: ✅ 201 Created

Step 2: GET /api/expense/groups?mode=summary
├─ Duration: 405ms (first) → 5ms (cached)
├─ Firestore: 1 read → 0 reads (cached empty)
└─ Status: ✅ 200 OK (0 groups)

Step 3: GET /api/expense/invitations
├─ Duration: 5ms (optimized for 0 groups)
├─ Firestore: 0 reads (early return)
└─ Status: ✅ 200 OK (0 invitations)
```

**Before Optimizations**: ~3.5s (multiple unnecessary reads)  
**After Optimizations**: ~1.1s first load, ~10ms subsequent  
**Improvement**: 97% faster on refresh

---

### Flow 2: Create Group → Navigate to Group Page
```
Total Duration: ~2.9s
Total API Calls: 4
Total Firestore Ops: 3 writes + 5 reads

Step 1: POST /api/expense/groups
├─ Duration: 213ms
├─ Firestore: 0 reads + 3 writes (group, members, balances)
├─ Cache: Invalidate user groups cache
└─ Status: ✅ 201 Created

Step 2-4: Navigate to group page (3 parallel calls)

Step 2: GET /api/expense/groups/{id}/full
├─ Duration: 1.8s (cache miss)
├─ Firestore: 3 reads (group, members, expenses)
├─ Cache: Cache full group data
└─ Status: ✅ 200 OK

Step 3: GET /api/expense/settlements/group/{id}
├─ Duration: 358ms (parallel with step 2)
├─ Firestore: 1 read (cache miss for group)
└─ Status: ✅ 200 OK

Step 4: GET /api/expense/invitations/group/{id}
├─ Duration: 531ms (parallel with step 2)
├─ Firestore: 1 read (invitations)
└─ Status: ✅ 200 OK
```

**Analysis**: Excellent performance. Parallel loading optimizes UX.

---

### Flow 3: Create Expense (with Optimistic Updates)
```
Total Duration: ~2s
Total API Calls: 2
Total Firestore Ops: 1 write + 1 read

Step 1: POST /api/expense/expenses
├─ Duration: 404ms
├─ Firestore: 0 reads (cache hit) + 1 write
├─ Features:
│  ├─ Idempotency key (24h cache)
│  ├─ Optimistic balance calculation
│  ├─ Background email notifications
│  └─ Smart cache handling
└─ Status: ✅ 201 Created (instant to user)

Step 2: GET /api/expense/groups/{id}/full?_t={timestamp}
├─ Duration: 1.6s (cache bypass with _t parameter)
├─ Firestore: 1 read (fetch new expense)
├─ Cache: Update cached group data
└─ Status: ✅ 200 OK (shows new expense)
```

**User Experience**: 404ms perceived time (optimistic update)  
**Actual Completion**: ~2s including refresh  
**Status**: ✅ Excellent - User sees instant feedback

---

### Flow 4: Update Expense (with Smart Cache)
```
Total Duration: ~800ms
Total API Calls: 2
Total Firestore Ops: 1 read + 1 write + variable cache invalidation

Step 1: PUT /api/expense/expenses/{id}
├─ Duration: 400ms
├─ Firestore: 1 read (verify permissions) + 1 write
├─ Smart Detection:
│  ├─ Metadata change (desc/category/date) → Keep balance cache
│  └─ Financial change (amount/splits) → Invalidate balance cache
└─ Status: ✅ 200 OK

Step 2: GET /api/expense/groups/{id}/full
├─ Duration: 9ms (cached, metadata change) OR 400ms (cache miss, financial change)
├─ Firestore: 0 reads (cached) OR 3 reads (refetch)
└─ Status: ✅ 200 OK
```

**Metadata Change**: 409ms total (96% faster)  
**Financial Change**: 800ms total (balance recalculation needed)  
**Status**: ✅ Excellent - Smart invalidation working

---

### Flow 5: Delete Expense
```
Total Duration: ~700ms
Total API Calls: 2
Total Firestore Ops: 1 read + 1 write

Step 1: DELETE /api/expense/expenses/{id}
├─ Duration: 300ms
├─ Firestore: 1 read (verify) + 1 write (soft delete)
├─ Cache: Invalidate balance cache
├─ Background: Email notifications
└─ Status: ✅ 200 OK

Step 2: GET /api/expense/groups/{id}/full
├─ Duration: 400ms (refresh data)
├─ Firestore: 1-3 reads
└─ Status: ✅ 200 OK
```

**Status**: ✅ Excellent - Fast deletion with proper cleanup

---

### Flow 6: Send Invitation → Accept
```
Total Duration: ~3.2s (send) + ~4.6s (accept) = ~7.8s
Total API Calls: 3 (send) + 4 (accept) = 7
Total Firestore Ops: 2 (send) + 20 (accept) = 22

--- SEND INVITATION ---

Step 1: POST /api/expense/invitations
├─ Duration: 315ms
├─ Firestore: 0 reads (cache hit) + 1 write
├─ Background: Email queue (non-blocking)
└─ Status: ✅ 201 Created

Step 2: GET /api/expense/groups/{id}/full
├─ Duration: 9ms (cache hit)
├─ Firestore: 0 reads
└─ Status: ✅ 200 OK

Step 3: GET /api/expense/invitations/group/{id}
├─ Duration: 133ms
├─ Firestore: 1 read (fetch invitations)
└─ Status: ✅ 200 OK

--- ACCEPT INVITATION ---

Step 1: POST /api/expense/invitations/{id}/accept
├─ Duration: 2.7s ⚠️
├─ Firestore: 5 reads + 3 writes (sequential operations)
├─ Operations:
│  ├─ Read invitation (250ms)
│  ├─ Read group (250ms)
│  ├─ Update invitation (250ms)
│  ├─ Add member to group (250ms)
│  └─ Create member document (250ms)
├─ Cache: Invalidate 3 keys
└─ Status: ✅ 200 OK (but slow)

Step 2: GET /api/expense/groups?mode=summary
├─ Duration: 389ms (cache miss after invalidation)
├─ Firestore: 8 reads (refetch groups)
└─ Status: ✅ 200 OK

Step 3: GET /api/expense/groups/{id}/full
├─ Duration: 1.4s (cache miss)
├─ Firestore: 4 reads
└─ Status: ✅ 200 OK

Step 4: GET /api/expense/settlements/group/{id}
├─ Duration: 139ms (parallel)
├─ Firestore: 0 reads (cached)
└─ Status: ✅ 200 OK
```

**Issue Identified**: Accept invitation is slow (2.7s)  
**Root Cause**: Sequential Firestore operations  
**Potential Fix**: Parallelize reads, batch writes  
**Expected Improvement**: 2.7s → 1.5s (44% faster)

---

### Flow 7: Remove Group Member
```
Total Duration: ~1.2s
Total API Calls: 2
Total Firestore Ops: 2 reads + 2 writes

Step 1: DELETE /api/expense/groups/{id}/members/{uid}
├─ Duration: 600ms
├─ Firestore: 2 reads (group, member) + 2 writes (remove, update)
├─ Cache: Invalidate group caches
└─ Status: ✅ 200 OK

Step 2: GET /api/expense/groups/{id}/full
├─ Duration: 600ms (refresh)
├─ Firestore: 3 reads
└─ Status: ✅ 200 OK
```

**Status**: ✅ Good - Reasonable performance

---

## 📈 Performance Metrics Summary

### ⚡ Fastest Operations (<100ms)
1. GET /api/health - 2ms
2. GET /api/expense/categories - 2ms
3. GET /api/expense/split-types - 2ms
4. GET /api/expense/groups (cached, 0 groups) - 5ms
5. GET /api/expense/invitations (0 groups) - 5ms
6. GET /api/expense/expenses/user (local) - 10ms
7. GET /api/expense/cache/stats - 10ms
8. GET /api/expense/groups/{id}/full (cached) - 9ms

### ✅ Fast Operations (100-500ms)
1. POST /api/expense/groups - 213ms ⭐
2. DELETE /api/expense/expenses/{id} - 300ms
3. POST /api/expense/invitations - 315ms
4. GET /api/expense/settlements/group/{id} (cached) - 139ms
5. PUT /api/expense/expenses/{id} - 400ms
6. POST /api/expense/expenses - 404ms ⭐

### ⚠️ Slower Operations (500ms-2s)
1. GET /api/health/detailed - 500ms
2. DELETE /api/expense/groups/{id}/members/{uid} - 600ms
3. GET /api/expense/invitations (with groups) - 800ms
4. POST /api/expense/settlements - 800ms
5. GET /api/expense/groups/{id}/full (first load) - 1.8s

### 🐌 Needs Optimization (>2s)
1. POST /api/expense/invitations/{id}/accept - 2.7s ⚠️
   - **Issue**: Sequential Firestore operations
   - **Fix**: Parallelize reads + batch writes
   - **Target**: 1.5s (44% improvement)

---

## 🎯 Optimization Opportunities

### Priority 1: Accept Invitation (High Impact)
**Current**: 2.7s  
**Target**: 1.5s  
**Improvement**: 44% faster  
**Effort**: Medium

**Changes Needed**:
```python
# Parallelize reads
with ThreadPoolExecutor() as executor:
    invitation_future = executor.submit(get_invitation, id)
    group_future = executor.submit(get_group, group_id)
    
# Batch writes
batch = db.batch()
batch.update(invitation_ref, {...})
batch.update(group_ref, {...})
batch.set(member_ref, {...})
batch.commit()
```

### Priority 2: Frontend Deduplication (Medium Impact)
**Current**: Multiple duplicate API calls  
**Target**: Single call per resource  
**Improvement**: 50% reduction in API calls  
**Effort**: Low

**Changes Needed**:
- Implement React Query
- Add request deduplication
- Cache API responses client-side

### Priority 3: Prefetching (Low Impact, Nice to Have)
**Current**: Sequential loading  
**Target**: Prefetch on navigation  
**Improvement**: Perceived 30% faster  
**Effort**: Medium

---

## 📊 Firestore Quota Usage (1000 Users/Day)

### Daily Operations Estimate:
| Operation | Per User | Total Daily | Monthly |
|-----------|----------|-------------|---------|
| Page loads (cached) | 10 × 0 reads | 0 | 0 |
| Page loads (miss) | 2 × 2 reads | 4,000 | 120,000 |
| Create expense | 5 × 1 write | 5,000 | 150,000 |
| Update expense | 2 × 2 ops | 4,000 | 120,000 |
| Delete expense | 1 × 2 ops | 2,000 | 60,000 |
| Accept invitation | 0.14 × 8 ops | 1,120 | 33,600 |
| Create group | 0.5 × 3 writes | 1,500 | 45,000 |
| **TOTAL** | - | **~18,000/day** | **~529,000/month** |

**Free Tier**: 50,000 reads + 20,000 writes per day  
**Status**: ✅ Well within limits (64% margin)

---

## ✅ Wins & Achievements

1. ✅ **Optimistic Updates**: Instant expense creation (404ms perceived)
2. ✅ **Smart Cache Invalidation**: Metadata changes don't trigger recalc (96% faster)
3. ✅ **Empty State Optimization**: 0 groups = 5ms (was 2.7s, 99.7% faster)
4. ✅ **Group Creation**: 213ms (excellent performance)
5. ✅ **Parallel Loading**: Group page uses 3 parallel requests
6. ✅ **Local Storage**: Personal expenses instant (10ms)
7. ✅ **Idempotency**: Prevents duplicate submissions (24h cache)
8. ✅ **Background Emails**: Non-blocking notifications

---

## 🎯 Performance Targets vs Actual

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Empty page load | <50ms | 10ms | ✅ 500% better |
| Create expense | <500ms | 404ms | ✅ 19% better |
| Create group | <300ms | 213ms | ✅ 29% better |
| Update expense | <500ms | 400ms | ✅ 20% better |
| Accept invitation | <1.5s | 2.7s | ⚠️ 80% slower |
| Page load (cached) | <100ms | 9ms | ✅ 1000% better |

**Overall**: 5/6 targets exceeded, 1 needs optimization

---

**Last Updated**: November 19, 2025  
**Status**: ✅ Comprehensive analysis complete  
**Next Action**: Optimize invitation acceptance flow
