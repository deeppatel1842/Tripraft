# Phase 17.5: API Timing Analysis & Optimization Status

**Last Updated:** December 3, 2025 (Session 4 - Post Phase 17.9 Bug Fixes)  
**Status:** ✅ Phase 17.9 Complete | Bug Fix Applied for Settlement Balance Updates

---

## Executive Summary

After implementing Phase 17.9 optimizations and bug fixes:
- **OPTIONS preflight**: Reduced to <5ms consistently (CORS caching working)
- **TTL increase**: Backend now caching for 300s (visible in logs)
- **Session 4 issue**: `/user/groups` called 33 times (regressed due to two users active)
- **Bug found**: Settlement receiver (owner) not seeing updated balances
- **Fix applied**: Now invalidate receiver's mega-bootstrap on settlement

---

## Session 4 Log Analysis (December 3, 2025)

### API Call Summary Table (Session 4 - Two Users Active)

| Endpoint | Method | Calls | Notes |
|----------|--------|-------|-------|
| `/api/expense/user/groups` | GET | **33** | Two users, multiple refreshes |
| `/api/expense/user/groups` | OPTIONS | 35 | CORS preflight |
| `/api/expense/mega-bootstrap` | GET | **13** | High due to cache invalidation |
| `/api/expense/mega-bootstrap` | OPTIONS | 13 | CORS preflight |
| `/api/expense/groups` | POST | 1 | Create group |
| `/api/expense/invitations` | POST | 1 | Send invitation |
| `/api/expense/invitations/{id}/accept` | POST | 1 | Accept invitation |
| `/api/expense/expenses` | POST | 2 | Add expenses |
| `/api/expense/expenses/{id}` | PUT | 1 | Update expense |
| `/api/expense/expenses/{id}` | DELETE | 1 | Delete expense |
| `/api/expense/settlements` | POST | 1 | Create settlement |
| `/api/expense/settlements/group/{id}` | GET | 1 | Get settlements |
| `/api/expense/groups/{id}/full` | GET | 1 | Get full group |
| `/api/expense/expenses/{id}/history` | GET | 2 | View expense history |
| `/api/expense/performance/cache` | GET | 4 | Debug endpoint |

### Total: 68 GET/POST/PUT/DELETE + 48 OPTIONS = **116 requests**

---

## Bug Fixed in Session 4

### Settlement Balance Bug

**Problem:** After settlement creation, the receiver (owner who was owed money) didn't see updated balances. The payer saw correct values.

**Root Cause:** In Phase 17.9, we removed ALL mega-bootstrap invalidation for settlements. But:
- **Payer**: Has optimistic update from frontend mutation - OK
- **Receiver**: No optimistic update, needs cache invalidation - BROKEN

**Fix Applied:** `settlement_service.py` - `_invalidate_settlement_cache()` now accepts `receiver_id` parameter and invalidates only the receiver's mega-bootstrap cache.

```python
# Phase 17.9 Fix: Only invalidate RECEIVER's mega-bootstrap
if receiver_id:
    cache.delete(f"expense:mega_bootstrap:{receiver_id}")
    cache.delete(f"expense:mega_bootstrap:{receiver_id}:{group_id}")
```

---

## Session Comparison Table

| Metric | Session 2 | Session 3 | Session 4 | Notes |
|--------|-----------|-----------|-----------|-------|
| `/user/groups` calls | 11 | 22 | **33** | Two users more active |
| `/user/groups` cache hit rate | 64% | 82% | ~85% | Improved |
| mega-bootstrap calls | 4 | 7 | **13** | Cache invalidation cascade |
| OPTIONS time | <5ms | <5ms | <1ms | CORS caching excellent |
| Settlement bug | - | - | **Fixed** | Receiver now sees updates |

---

## Post-Optimization Log Analysis (December 3, 2025 - Session 3)

### API Call Summary Table (After Phase 17.6-17.8)

| # | Endpoint | Method | Time (ms) | Cache | Firestore | Status |
|---|----------|--------|-----------|-------|-----------|--------|
| 1 | `/api/expense/expenses/{id}` | PUT | **1894** | MISS→SET | 5R 3W | 200 |
| 2 | `/api/expense/user/groups` | GET | 252 | HIT | 0 | 200 |
| 3 | `/api/expense/user/groups` | GET | 206 | HIT | 0 | 200 |
| 4 | `/api/expense/user/groups` | GET | 234 | HIT | 0 | 200 |
| 5 | `/api/expense/expenses/{id}/history` | GET | **959** | MISS | 4R | 200 |
| 6 | `/api/expense/expenses/{id}/history` | GET | 502 | HIT | 3R | 200 |
| 7 | `/api/expense/user/groups` | GET | 226 | HIT | 0 | 200 |
| 8 | `/api/expense/expenses` | POST | **2113** | - | 4R 3W | 201 |
| 9 | `/api/expense/user/groups` | GET | 232 | HIT | 0 | 200 |
| 10 | `/api/expense/user/groups` | GET | 208 | HIT | 0 | 200 |
| 11 | `/api/expense/expenses/{id}` | DELETE | **1646** | - | 3R 1W | 200 |
| 12 | `/api/expense/user/groups` | GET | 226 | HIT | 0 | 200 |
| 13 | `/api/expense/user/groups` | GET | 239 | HIT | 0 | 200 |
| 14 | `/api/expense/user/groups` | GET | 256 | HIT | 0 | 200 |
| 15 | `/api/expense/settlements` | POST | **1231** | - | 6R 0W | 201 |
| 16 | `/api/expense/mega-bootstrap` | GET | **1615** | MISS | 12R | 200 |
| 17 | `/api/expense/mega-bootstrap` | GET | **1459** | MISS | 12R | 200 |
| 18 | `/api/expense/settlements/group/{id}` | GET | 688 | MISS | 5R | 200 |
| 19 | `/api/expense/groups/{id}/members/{id}` | DELETE | 707 | - | 2R 2W | 200 |
| 20 | `/api/expense/mega-bootstrap` | GET | **1284** | MISS | 10R | 200 |
| 21 | `/api/expense/mega-bootstrap` | GET | **1220** | MISS | 10R | 200 |
| 22 | `/api/expense/user/groups` | GET | 371 | MISS | 1R | 200 |
| 23 | `/api/expense/user/groups` | GET | 223 | HIT | 0 | 200 |
| 24 | `/api/expense/user/groups` | GET | 227 | HIT | 0 | 200 |
| 25 | `/api/expense/user/groups` | GET | 218 | HIT | 0 | 200 |
| 26 | `/api/expense/groups/{id}` | DELETE | - | - | - | - |

### Aggregated Statistics (Post-Optimization)

| Endpoint | Method | Total Calls | Cache Hits | Cache Misses | Avg Time (ms) |
|----------|--------|-------------|------------|--------------|---------------|
| `/api/expense/user/groups` | GET | **22** | 18 | 4 | **232** |
| `/api/expense/mega-bootstrap` | GET | **7** | 0 | 7 | **1394** |
| `/api/expense/expenses/{id}` | PUT | 1 | - | - | **1894** |
| `/api/expense/expenses` | POST | 1 | - | - | **2113** |
| `/api/expense/expenses/{id}` | DELETE | 1 | - | - | **1646** |
| `/api/expense/settlements` | POST | 1 | - | - | **1231** |
| `/api/expense/settlements/group/{id}` | GET | 1 | - | - | **688** |
| `/api/expense/groups/{id}/members/{id}` | DELETE | 1 | - | - | **707** |
| `/api/expense/expenses/{id}/history` | GET | 2 | 1 | 1 | **730** |
| OPTIONS (preflight) | * | 32 | - | - | **<5** |

### Total API Calls: **37 GET/POST/PUT/DELETE** + 32 OPTIONS = **69 requests**

---

## Before vs After Comparison

| Metric | Before (Session 2) | After (Session 3) | Change |
|--------|-------------------|-------------------|--------|
| `/user/groups` calls | 11 | 22 | **+100%** (more activity) |
| `/user/groups` cache hit rate | 64% | 82% | **+18%** |
| `/user/groups` avg time | 398ms | 232ms | **-42%** |
| OPTIONS preflight time | 0.5ms | <5ms | Same |
| mega-bootstrap avg time | 1098ms | 1394ms | +27% (more misses) |
| TTL observed | 120s | **300s** | **+150%** (Phase 17.7 working) |
| Firestore ops per session | ~30 | ~50 | More activity |

### Key Improvements Observed:
1. ✅ **CORS preflight caching**: OPTIONS consistently <5ms
2. ✅ **TTL 300s applied**: `[TTL=300s]` visible in cache SET logs
3. ✅ **Cache hit rate improved**: `/user/groups` now 82% vs 64%
4. ✅ **Response time reduced**: `/user/groups` avg 232ms vs 398ms

### Remaining Issues:
1. ❌ **Excessive `/user/groups` calls**: 22 calls when target is 2-3
2. ❌ **mega-bootstrap cache miss rate**: 0% hits (all invalidated by mutations)
3. ❌ **Cache invalidation cascade**: Every mutation invalidates mega-bootstrap

---

## API Timing Analysis Table

### By Endpoint (From Logs Analysis)

| Endpoint | Method | Avg Time (ms) | Cache Status | Firestore Ops | Frequency | Issue |
|----------|--------|---------------|--------------|---------------|-----------|-------|
| `/api/expense/mega-bootstrap` | GET | 1098-2368 | MISS first, HIT after | 10-12R | High | Cache invalidated too often |
| `/api/expense/user/groups` | GET | 241-1116 | Often HIT | 0-1R | **Very High (11x)** | Redundant calls |
| `/api/expense/groups` | POST | 1062 | - | 1R 3W | Low | Acceptable |
| `/api/expense/invitations` | POST | 1446 | - | 5R 1W | Low | Acceptable |

### Response Time Classification

| Category | Response Time | Examples |
|----------|---------------|----------|
| Fast | < 300ms | `user/groups` (cache hit: 241-281ms), `mega-bootstrap` (cache hit: 268ms) |
| Medium | 300-600ms | `user/groups` (first cache hit: 346-365ms) |
| Slow | 600-1200ms | `user/groups` (cache miss: 680-1116ms), `groups` POST (1062ms) |
| Very Slow | 1200-2000ms | `invitations` POST (1446ms), `mega-bootstrap` (miss: 1458ms) |
| Critical | > 2000ms | `mega-bootstrap` (cold: 2368ms) |

---

## Critical Problems Identified (Current Session)

### 1. Excessive `/user/groups` Calls - STILL AN ISSUE

**Evidence from logs:**
- **11 GET calls** to `/api/expense/user/groups` in a short session
- Called by BOTH User A (Android emulator) and User B (Windows desktop)
- 7 cache hits, but still making unnecessary network requests
- Most calls take 241-365ms even with cache hit (network overhead)

**Root Cause:** 
- Frontend components still triggering API calls despite React Query cache
- Every navigation/refresh triggers a new request
- Cache check happens server-side, not client-side

**Impact:** ~4.4 seconds wasted on redundant user/groups calls

### 2. mega-bootstrap Cache Miss Rate Too High

**Evidence from logs:**
- 4 GET calls to mega-bootstrap
- Only 1 cache HIT (25% hit rate)
- 3 MISS calls taking 1458-2368ms each

**Root Cause:**
- Cache invalidated on any mutation (invitation sent)
- TTL of 120s may still be too short
- Different users have separate caches (expected, but costly)

**Impact:** ~5.3 seconds spent on mega-bootstrap misses

### 3. Dual User Scenario Multiplies API Load

**Evidence from logs:**
- Two distinct User-Agents detected:
  - User A: `Mozilla/5.0 (Linux; Android 6.0; Nexus 5...)` - Mobile emulator
  - User B: `Mozilla/5.0 (Windows NT 10.0; Win64; x64...)` - Desktop
- Each user making independent API calls
- Cache invalidation affects both users' caches

### 4. OPTIONS Requests Add Overhead

**Evidence from logs:**
- Every API call preceded by OPTIONS preflight
- 11 OPTIONS requests for user/groups alone
- While fast (0-1ms), they double the request count

---

## Cache Performance Analysis

### Redis Cache Legend
- `[CACHE][+]` = Cache HIT (data returned from Redis)
- `[CACHE][-]` = Cache MISS (no data, will fetch from Firestore)
- `[CACHE][S]` = Cache SET (storing data with TTL)
- `[CACHE][X]` = Cache DELETE/INVALIDATE

### Current Session Cache Stats

| Cache Key Pattern | Hits | Misses | Hit Rate | Notes |
|-------------------|------|--------|----------|-------|
| `expense:user_groups:{uid}` | 7 | 4 | **64%** | Should be 95%+ |
| `expense:mega_bootstrap:{uid}:{gid}` | 1 | 3 | **25%** | Far below target |
| `expense:group:{gid}` | 1 | 1 | 50% | Acceptable |
| `expense:group_balances:{gid}` | 0 | 2 | **0%** | Always misses |
| `expense:group_settlements:{gid}` | 1 | 1 | 50% | Acceptable |
| `expense:group_invites:{gid}` | 0 | 2 | **0%** | Invalidated on invite |

---

## Target vs Current Performance

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| API calls per session | **5-10** | **16** | 6-11 calls over |
| user/groups calls per session | **1-2** | **11** | 9 calls over |
| mega-bootstrap cache hit rate | **90%+** | **25%** | 65% below |
| user_groups cache hit rate | **95%+** | **64%** | 31% below |
| Average response time (cache hit) | **<100ms** | **~265ms** | Network overhead |
| Average response time (cache miss) | **<500ms** | **~1300ms** | Firestore latency |

---

## Action Plan to Achieve Target

### Phase 17.6: Frontend API Consolidation (HIGH PRIORITY) ✅ COMPLETED

**Goal:** Reduce API calls from 16 to 5-10 per session

**Status: IMPLEMENTED December 3, 2025**

#### Changes Made:

**1. `useMegaBootstrap` Hook Updated**
```javascript
// useExpenseQuery.js - useMegaBootstrap
{
  staleTime: 5 * 60 * 1000,    // 5 minutes (was 30 seconds)
  gcTime: 30 * 60 * 1000,      // 30 minutes (was 5 minutes)
  refetchOnWindowFocus: false, // Disabled (was true)
  refetchOnMount: hasCachedData ? false : true, // Skip if cached
  refetchInterval: false,      // No automatic polling
}
```

**2. `useGroupsQuery` Hook (Already Optimized)**
```javascript
{
  staleTime: 5 * 60 * 1000,    // 5 minutes
  gcTime: 30 * 60 * 1000,      // 30 minutes
  refetchOnWindowFocus: false,
  refetchOnMount: hasCachedData ? false : true,
  refetchInterval: false,
}
```

**3. `useInvitationsQuery` Hook (Already Optimized)**
```javascript
{
  staleTime: 5 * 60 * 1000,    // 5 minutes
  gcTime: 30 * 60 * 1000,      // 30 minutes
  refetchOnWindowFocus: false,
  refetchOnMount: hasCachedData ? false : true,
  refetchInterval: false,
}
```

**Expected Impact:**
- Reduce API calls per session from 16 to ~8
- Eliminate window focus refetch storms
- 5-minute stale time reduces redundant fetches

### Phase 17.7: Backend Cache Optimization (MEDIUM PRIORITY) ✅ COMPLETED

**Goal:** Increase cache hit rate to 90%+

**Status: IMPLEMENTED December 3, 2025**

#### Changes Made:

**1. Mega-Bootstrap TTL Increased**
```python
# bootstrap_service.py - get_mega_bootstrap()
# BEFORE: ttl=120 (2 minutes)
# AFTER:  ttl=300 (5 minutes)

self._cache.set(cache_key, response, ttl=300)  # 5 minute TTL (Phase 17.7)
```

**Expected Impact:**
- Cache hit rate increase from 25% to ~75%+
- Fewer Firestore reads per session
- Better match with frontend 5-minute staleTime

### Phase 17.8: Network Optimization (LOW PRIORITY) ✅ COMPLETED

**Status: IMPLEMENTED December 3, 2025**

#### Changes Made:

**1. CORS Preflight Caching (24 hours)**
```python
# app.py - CORS configuration
CORS(app, 
     resources={r"/api/*": {"origins": config.CORS_ORIGINS}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
     max_age=86400)  # 24 hours - cache CORS preflight responses
```

**Expected Impact:**
- Browser caches OPTIONS preflight for 24 hours
- Eliminates ~50% of OPTIONS requests after first visit
- Reduces total request count significantly

#### 2. Response Compression
- Already enabled (gzip, level 6)
- Consider Brotli for better compression

#### 3. HTTP/2 Server Push (Future)
- Push related resources proactively

---

## Problem Areas Identified

### 1. Excessive `/user/groups` Calls

**Evidence from logs:**
- 30+ calls to `/api/expense/user/groups` in single session
- Called by BOTH User A (Windows) and User B (Android/Mobile)
- Many show `[CACHE][+]` (cache hit) but still making network request

**Root Cause:** Frontend hooks calling API even when React Query cache is populated

**Status: FIXED in Phase 17.5**
- Modified `useGroupsQuery` to check cache before API call
- Modified `useGroupQuery` to use cached data as fallback
- Modified `usePrefetchGroups` to only prefetch on hover if cache empty

### 2. Duplicate mega-bootstrap + user/groups

**Evidence from logs:**
```
GET /api/expense/mega-bootstrap?active_group_id=...
GET /api/expense/user/groups?page=1&limit=20
```
Both called simultaneously on page load.

**Root Cause:** Separate hooks triggering independently

**Status: FIXED in Phase 17.5**
- mega-bootstrap hydrates `['groups']` query cache
- `useGroupsQuery` now checks if cache exists before fetching

### 3. Cache Invalidation Cascade

**Evidence from logs:**
```
[CACHE][X] expense:mega_bootstrap:R0aghH2MVAh1Pf8CH2UQZN3wIjN2
[CACHE][X] expense:mega_bootstrap:R0aghH2MVAh1Pf8CH2UQZN3wIjN2:9DWIWTWoYlMXEPSCdlJF
[CACHE][X] expense:mega_bootstrap:iJol3n5TFrVHdH79hS32WLCI2EK2
[CACHE][X] expense:mega_bootstrap:iJol3n5TFrVHdH79hS32WLCI2EK2:9DWIWTWoYlMXEPSCdlJF
```
All users' caches invalidated on any mutation.

**Root Cause:** `_invalidate_expense_cache()` invalidated all group members

**Status: FIXED in Phase 17.5**
- Added `current_user_id` parameter to `_invalidate_expense_cache()`
- Skips invalidating current user's cache (they have optimistic update)

### 4. Short mega-bootstrap TTL

**Evidence from logs:**
```
[CACHE][S] expense:mega_bootstrap:...:... [TTL=60s]  # Too short!
```

**Status: FIXED in Phase 17.5**
- Increased TTL from 60s to 120s

### 5. invitation/details Called 3x ✅ FIXED

**Evidence from logs:**
```
GET /api/expense/invitations/Xkx2AUBCGl8UMODfm3qS/details  469.30ms
GET /api/expense/invitations/Xkx2AUBCGl8UMODfm3qS/details  283.38ms
GET /api/expense/invitations/Xkx2AUBCGl8UMODfm3qS/details  296.54ms
```
Same invitation details fetched 3 times.

**Root Cause:** Multiple components (InvitationAccept → Login → Signup) all calling `getInvitationDetails` independently

**Status: FIXED in Phase 17.5**
- `InvitationAccept.jsx` caches `invitationEmail` in localStorage after first fetch
- `Login.jsx` checks localStorage cache before making API call
- `Signup.jsx` checks localStorage cache before making API call
- Result: 1 API call instead of 3

---

## Cache Hit/Miss Analysis

### Redis Cache Legend
- `[CACHE][+]` = Cache HIT (data returned from Redis)
- `[CACHE][-]` = Cache MISS (no data, will fetch from Firestore)
- `[CACHE][S]` = Cache SET (storing data with TTL)
- `[CACHE][X]` = Cache DELETE/INVALIDATE

### Session Cache Performance

From analyzed logs (approx 2500 lines):

| Cache Key Pattern | Hits | Misses | Hit Rate |
|-------------------|------|--------|----------|
| `expense:user_groups:{uid}` | 28 | 8 | 78% |
| `expense:mega_bootstrap:{uid}:{gid}` | 12 | 15 | 44% |
| `expense:group:{gid}` | 10 | 8 | 56% |
| `expense:group_balances:{gid}` | 3 | 12 | 20% |
| `expense:membership:{gid}:{uid}` | 8 | 4 | 67% |

**Observation:** Balance cache has very low hit rate due to frequent invalidation

---

## API Call Count per Action

### Scenario: Complete User Session (From Logs)

| Action | User A (Windows) | User B (Android) | Combined |
|--------|------------------|------------------|----------|
| Dashboard load | 3 | 3 | 6 |
| View group | 2 | 2 | 4 |
| Create group | - | 2 | 2 |
| Send invitation | - | 2 | 2 |
| Accept invitation | 2 | - | 2 |
| Create expense | 2 | 2 | 4 |
| Edit expense | 2 | 2 | 4 |
| View history | 2 | 2 | 4 |
| Delete expense | 2 | 2 | 4 |
| Create settlement | - | 2 | 2 |
| Remove member | - | 2 | 2 |
| Navigation/refresh | 10+ | 10+ | 20+ |
| **TOTAL** | ~25 | ~30 | **~56** |

**Target:** 5-10 API calls per session

---

## Phase 17.5 Changes Implemented

### Backend Changes

1. **`expense_service.py`**
   - `_invalidate_expense_cache()` now accepts `current_user_id` parameter
   - Skips invalidating current user's mega_bootstrap cache

2. **`bootstrap_service.py`**
   - mega_bootstrap TTL increased: 60s → 120s → **300s** (Phase 17.7)

3. **`history_helpers.py`** (from Phase 17)
   - Added `create_history_entry()` helper
   - Returns history_entry in mutation responses

4. **`app.py`** (Phase 17.8)
   - Added `max_age=86400` to CORS for 24-hour preflight caching

### Frontend Changes

1. **`useExpenseQuery.js`**
   - `useGroupsQuery`: Skip API if mega-bootstrap populated cache
   - `useGroupQuery`: Use cached group data, skip redundant fetch
   - `usePrefetchGroups`: Only prefetch on hover if cache empty
   - `useInvitationsQuery`: Skip API if cache exists
   - Added `useExpenseHistory` hook
   - Added `useGroupHistory` hook
   - **Phase 17.6:** `useMegaBootstrap` staleTime 30s → 5min, refetchOnWindowFocus disabled

2. **`expenseMutations.js`**
   - All mutations apply `applyBalanceDeltas()` from server response
   - Instant UI updates without refetch

3. **`TransactionList.jsx`**
   - Added "Syncing" badge for optimistic updates
   - Shows spinning animation for `_optimistic` flagged items

4. **`ExpenseManager.css`**
   - Added `.syncing-badge` styles
   - Added `@keyframes spin` animation

---

## Remaining Issues (December 3, 2025)

### 1. Double-Click Required for Group Delete ✅ FIXED (Complete)
**Symptom:** First click shows Firestore permission errors, second click works
**Root Cause:** Multiple Firestore real-time listeners still subscribed to deleted group:
- `expenseFirestoreListener.js` - expense-related listeners
- `firestoreListenerService.js` - group planner listeners
- `GroupPlannerContext.jsx` - context listeners

**Fix Applied:**
- Added `unsubscribeFromGroup(groupId)` method to `expenseFirestoreListener.js`
- Updated `handleDeleteGroup` in `ExpenseManager.jsx` to call cleanup on BOTH:
  - `expenseFirestoreListener.unsubscribeFromGroup(groupId)`
  - `firestoreListenerService.stopListeningToGroup(groupId)`
- Updated `deleteGroup` in `GroupPlannerContext.jsx` to call `firestoreListenerService.stopListeningToGroup()` before API call

### 2. Slow Deleted History Load ✅ ACCEPTABLE
**Symptom:** History tab loads slowly after expense deletion (585-660ms)
**Investigation Result:** This is within acceptable range due to Firestore queries
**Status:** Not a bug - normal query latency for history retrieval

### 3. User B Doesn't See Pending Invitations ✅ FIXED
**Symptom:** User A sends invite, User B doesn't see it immediately
**Root Cause:** 
- mega-bootstrap cache not invalidated for the INVITEE (who is not a group member yet)
- Email case sensitivity could cause lookup mismatches
**Fix Applied:**
- `_invalidate_invitation_cache()` in `invitation_service.py` now looks up invitee by email and invalidates their mega-bootstrap cache
- Added email normalization (lowercase, strip) to invitation creation and lookup
- Added expired invitation filtering to `get_user_invitations()` in repository

### 4. Date Timezone Issue in Edit History ✅ FIXED
**Symptom:** Edited expense shows date one day previous
**Root Cause:** `new Date("2025-01-15")` parses as UTC midnight, which displays as previous day in local timezone
**Fix Applied:**
- Updated `formatValue()` in `ExpenseHistoryModal.jsx` to parse date-only strings (YYYY-MM-DD) using component values to avoid timezone conversion

---

## Performance Metrics After Phase 17.5-17.8

### Improvements Summary (Updated with Session 3 Data)

| Metric | Before 17.5 | After 17.5 | After 17.6-17.8 (Actual) | Target |
|--------|-------------|------------|--------------------------|--------|
| API calls/session | 50-60 | 16-27 | **37** | 5-10 |
| mega-bootstrap cache hit | 44% | 25% | **0%** (aggressive invalidation) | 90%+ |
| user_groups cache hit | 78% | 64% | **82%** ✅ | 95%+ |
| Duplicate API calls | Many | Some | **Still occurring** | Zero |
| Cache TTL (mega) | 60s | 120s | **300s ✅** | 300s |
| Frontend staleTime | 30s | 30s | **300s ✅** | 300s |
| CORS preflight cache | 0 | 0 | **24h ✅** | 24h |
| UI update latency | 200-500ms | <50ms | **<50ms** ✅ | <50ms |
| OPTIONS preflight time | 0.5ms | 0.5ms | **<5ms** ✅ | <5ms |
| `/user/groups` avg response | 398ms | 398ms | **232ms** ✅ | <200ms |

### What Phase 17.6-17.8 Achieved

| Phase | Goal | Result |
|-------|------|--------|
| 17.6 | Reduce frontend refetch storms | ✅ Partial - staleTime works but cache invalidation overrides it |
| 17.7 | Increase cache hit rate | ⚠️ TTL increased but aggressive invalidation prevents hits |
| 17.8 | Reduce OPTIONS requests | ✅ OPTIONS consistently <5ms after first request |

### What Still Needs Fixing (Phase 17.9)

| Issue | Current | Target | Gap |
|-------|---------|--------|-----|
| `/user/groups` calls per session | 22 | 2-3 | 19 over |
| mega-bootstrap cache hit rate | 0% | 90%+ | 90% below |
| Total API calls | 37 | 5-10 | 27-32 over |

### Phase 17.6-17.8 Implementation Summary (December 3, 2025)

| Phase | Change | File | Status |
|-------|--------|------|--------|
| 17.6 | `useMegaBootstrap` staleTime 30s → 5min | `useExpenseQuery.js` | ✅ Done |
| 17.6 | `useMegaBootstrap` refetchOnWindowFocus: false | `useExpenseQuery.js` | ✅ Done |
| 17.6 | `useMegaBootstrap` refetchOnMount: conditional | `useExpenseQuery.js` | ✅ Done |
| 17.6 | `useMegaBootstrap` gcTime 5min → 30min | `useExpenseQuery.js` | ✅ Done |
| 17.7 | mega-bootstrap TTL 120s → 300s | `bootstrap_service.py` | ✅ Done |
| 17.8 | CORS max_age=86400 (24 hours) | `app.py` | ✅ Done |

### Immediate Action Items (Updated December 3, 2025)

| Priority | Action | Effort | Impact | Status |
|----------|--------|--------|--------|--------|
| ~~HIGH~~ | ~~Add `refetchOnMount: false` to useMegaBootstrap~~ | 1 hour | -5 API calls | ✅ Done |
| ~~HIGH~~ | ~~Add `staleTime: 5min` to mega-bootstrap~~ | 2 hours | -3 API calls | ✅ Done |
| ~~HIGH~~ | ~~Increase mega-bootstrap TTL to 300s~~ | 30 min | +40% cache hits | ✅ Done |
| ~~LOW~~ | ~~CORS preflight caching (24h)~~ | 1 hour | Fewer OPTIONS | ✅ Done |
| MEDIUM | Audit duplicate useGroupsQuery hooks | 4 hours | -2 API calls | Pending |
| MEDIUM | Smart cache invalidation (affected users only) | 4 hours | +30% cache hits | Pending |

### Bug Fixes Summary (Phase 17.5)

| Bug | Status | Files Modified |
|-----|--------|----------------|
| Double-click delete group | ✅ Fixed | `expenseFirestoreListener.js`, `ExpenseManager.jsx` |
| Slow history load | ✅ Acceptable | N/A - normal latency |
| Invitations not visible | ✅ Fixed | `invitation_service.py`, `bootstrap_service.py`, `invitation_repository.py` |
| Date timezone in history | ✅ Fixed | `ExpenseHistoryModal.jsx` |

### Next Steps

1. ~~Fix 4 reported bugs~~ ✅ All fixed
2. ~~Investigate invitation/details triple call~~ ✅ Fixed
3. ~~Increase mega-bootstrap TTL to 300s~~ ✅ Done (Phase 17.7)
4. ~~Add CORS preflight caching~~ ✅ Done (Phase 17.8)
5. ~~Frontend staleTime optimization~~ ✅ Done (Phase 17.6)
6. **Run new log capture session to verify improvements** ✅ Done (Session 3)
7. Add debouncing to prevent rapid API calls (if still needed)
8. Implement Firestore listener cleanup on navigation

---

## Phase 17.9: Address Remaining Performance Gaps (NEXT)

### Problem Statement (From Session 3 Analysis)

Despite Phase 17.6-17.8 implementations:
- `/user/groups` still called **22 times** (target: 2-3)
- mega-bootstrap cache hit rate: **0%** (all invalidated by mutations)
- Total API calls: **37** (target: 5-10)

### Root Cause Analysis

1. **Cache Invalidation is Too Aggressive**
   - Every expense create/update/delete invalidates ALL related caches
   - mega-bootstrap cache invalidated for ALL group members
   - Result: Cache barely survives between mutations

2. **Frontend Still Making Redundant Calls**
   - React Query `staleTime` works, but cache is being manually invalidated
   - `queryClient.invalidateQueries()` called after mutations
   - Firestore listeners trigger refetch on any change

3. **Dual User Scenario Amplifies Problem**
   - User A mutation → Invalidates User B cache → User B refetches
   - Both users making independent calls for same data

### Proposed Solutions for Phase 17.9

#### Option A: Selective Cache Invalidation (RECOMMENDED)
```python
# Instead of invalidating all caches, only invalidate affected ones
def _invalidate_expense_cache(self, group_id, expense_id, current_user_id):
    # Only invalidate group-level caches
    self._cache.delete(f"expense:group_balances:{group_id}")
    self._cache.delete(f"expense:group_summary:{group_id}")
    
    # DON'T invalidate mega-bootstrap for other users
    # Let them get updates via Firestore listener instead
```

#### Option B: Real-time Updates Replace API Calls
```javascript
// Frontend: Use Firestore listeners as source of truth
// Don't refetch on mutation - let listener update cache

const handleExpenseUpdate = (updatedExpense) => {
  // Update React Query cache directly from Firestore listener
  queryClient.setQueryData(['expenses', groupId], (old) => ({
    ...old,
    expenses: old.expenses.map(e => 
      e.id === updatedExpense.id ? updatedExpense : e
    )
  }));
};
```

#### Option C: Debounce API Calls
```javascript
// Group multiple rapid calls into one
const debouncedFetch = useMemo(
  () => debounce(() => queryClient.invalidateQueries(['groups']), 1000),
  []
);
```

### Priority for Phase 17.9

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| HIGH | Stop invalidating other users' mega-bootstrap | -50% API calls | 2 hours |
| HIGH | Use Firestore listener for real-time instead of refetch | -30% API calls | 4 hours |
| MEDIUM | Debounce rapid successive API calls | -10% API calls | 2 hours |
| MEDIUM | Audit manual `queryClient.invalidateQueries()` calls | -10% API calls | 3 hours |

---

## Cache Key Reference (Updated December 3, 2025)

| Key Pattern | TTL (Before) | TTL (After 17.7) | Description |
|-------------|--------------|------------------|-------------|
| `expense:user_groups:{user_id}` | 300s | 300s | User's group list |
| `expense:mega_bootstrap:{uid}` | 120s | **300s** | User's full data (dashboard) |
| `expense:mega_bootstrap:{uid}:{gid}` | 120s | **300s** | User's full data (group view) |
| `expense:group:{group_id}` | 60s | 60s | Single group details |
| `expense:group_balances:{group_id}` | 300s | 300s | Group balance matrix |
| `expense:group_settlements:{group_id}` | 300s | 300s | Group settlements |
| `expense:group_invites:{group_id}` | 120s | 120s | Group invitations |
| `expense:expense:{expense_id}` | 120s | 120s | Single expense |
| `expense:membership:{gid}:{uid}` | 60s | 60s | Membership check |

### Frontend Cache Settings (After Phase 17.6)

| Hook | staleTime | gcTime | refetchOnWindowFocus | refetchOnMount |
|------|-----------|--------|---------------------|----------------|
| `useMegaBootstrap` | **5min** | 30min | false | conditional |
| `useGroupsQuery` | 5min | 30min | false | conditional |
| `useGroupQuery` | 5min | 5min | false | conditional |
| `useInvitationsQuery` | 5min | 30min | false | conditional |
| `useExpensesQuery` | 1min | - | - | - |
| `useSettlementsQuery` | 1min | - | - | - |

---

## Firestore Query Patterns

### High Frequency Queries

| Collection | Filter | Purpose |
|------------|--------|---------|
| `expense_groups` | `member == {uid}` | User's groups |
| `expense_invitations` | `group_id == X` | Group invitations |
| `expense_expenses` | `group_id == X` | Group expenses |
| `expense_history` | `expense_id == X` | Expense history |

### Optimization Opportunities

1. Batch `expense_history` queries into single call
2. Use composite index for `expense_expenses` + `created_at`
3. Consider denormalizing user names into expenses

---

## Session Timeline (December 3, 2025)

```
11:59:23 - Log capture started
11:59:24 - Server initialized (Firebase, Redis, Flask)
11:59:25 - Rate limiting, compression, blueprints registered

REQUEST FLOW:
────────────────────────────────────────────────────────────
User A (Android) loads app:
  → OPTIONS /user/groups (1ms)
  → GET /user/groups - CACHE MISS (1116ms) ← First load penalty
  
User A navigates:
  → GET /user/groups - CACHE HIT (365ms) ← Still slow due to network
  
User A creates group "y":
  → POST /groups (1062ms) ← 1R 3W Firestore ops
  
User A views group:
  → GET /user/groups - CACHE HIT (346ms)
  → GET /mega-bootstrap - CACHE MISS (2368ms) ← 12 Firestore reads!
  
User A sends invitation:
  → POST /invitations (1446ms) ← 5R 1W, invalidates caches

User B (Windows) arrives (invited user):
  → GET /user/groups - CACHE MISS (726ms) ← Cache was invalidated
  → GET /user/groups - CACHE MISS (681ms) ← Duplicate call!

User A checks updates:
  → GET /mega-bootstrap - CACHE MISS (1458ms) ← Cache was invalidated
  
Subsequent requests (both users):
  → Multiple GET /user/groups - CACHE HIT (241-282ms)
  → GET /mega-bootstrap - CACHE HIT (269ms)
────────────────────────────────────────────────────────────

TOTAL TIME SPENT: ~10.2 seconds on API calls
WASTED TIME: ~5.5 seconds on redundant/duplicate calls
```

---

*Analysis based on `captured_logs.txt` session from December 3, 2025 (11:59:23 start)*
*Total lines analyzed: ~500 (partial session before interruption)*
