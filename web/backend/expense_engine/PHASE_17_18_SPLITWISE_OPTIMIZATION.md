# Phase 17-18: Splitwise-Level Optimization - MAX 10 API Calls Per Session

## Executive Summary

**Created:** December 2, 2025  
**Goal:** Reduce API calls per session from 20+ to MAX 10  
**Target:** Match Splitwise efficiency (4-5 API calls per action sequence)

---

## Current State Analysis (From Logs December 2, 2025)

### Critical Issues Found

| Issue | Evidence from Logs | Impact |
|-------|-------------------|--------|
| **Duplicate API calls** | `GET /user/groups` called 15+ times in session | 10x more calls than needed |
| **Parallel API calls to same data** | `mega-bootstrap` + `groups/full` called together | 2x redundant |
| **Cache miss after invalidation** | `[CACHE][-]` → `[FIRESTORE][R]` pattern | 100% cache miss on writes |
| **Frontend not waiting for mega-bootstrap** | Multiple requests before data arrives | Race conditions |
| **useGroupsQuery polling even when mega-bootstrap cached** | `refetchInterval: 30000` always active | Unnecessary API calls |

### API Call Counts from Log Analysis

| Endpoint | Calls in Session | Should Be |
|----------|------------------|-----------|
| `GET /user/groups` | 15+ | 1-2 |
| `GET /mega-bootstrap` | 8+ | 2-3 |
| `GET /groups/{id}/full` | 6+ | 0 (use mega-bootstrap) |
| `POST /expenses` | 1 | 1 |
| `DELETE /expenses` | 1 | 1 |
| **TOTAL** | **35+** | **10** |

### Firestore Operations from Logs

| Action | Current Firestore Ops | Target |
|--------|----------------------|--------|
| mega-bootstrap (cold) | 9R | 2R |
| Create expense | 4R + 3W = 7 | 0R + 2W = 2 |
| Delete expense | 3R + 1W = 4 | 0R + 1W = 1 |
| View group (cached) | 0R | 0R |
| **Session Total** | **80+** | **10-15** |

---

## Phase 1-16 Completion Status ✅

| Phase | Status | Evidence |
|-------|--------|----------|
| Phase 1-9 | ✅ COMPLETE | All core features working |
| Phase 10 | ✅ COMPLETE | Thread safety tests passing |
| Phase 11 | ✅ COMPLETE | Browser cache with React Query |
| Phase 12 | ✅ COMPLETE | Expense history tracking |
| Phase 13 | ✅ COMPLETE | Extended cache TTLs |
| Phase 14 | ✅ COMPLETE | Batch operations utility |
| Phase 15 | ✅ COMPLETE | Soft-delete members |
| Phase 16 | ✅ COMPLETE | Mega-bootstrap API exists |

### What's Missing from Phase 16

Despite mega-bootstrap being implemented, the frontend still makes redundant calls:

```
❌ PROBLEM: Frontend calls BOTH:
   GET /mega-bootstrap?active_group_id=XXX
   GET /groups/XXX/full              ← REDUNDANT!
   GET /user/groups                  ← REDUNDANT!
```

---

## Phase 17: Frontend Deduplication (HIGH PRIORITY)

### 17.1: Kill Redundant useGroupsQuery

**Current Problem:**
```javascript
// useExpenseQuery.js - CURRENT (BAD)
export function useGroupsQuery() {
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(1, 20),
    refetchInterval: hasCachedData ? false : 30 * 1000, // Still polls!
  });
}
```

**Solution:**
```javascript
// useExpenseQuery.js - FIXED
export function useGroupsQuery() {
  const queryClient = useQueryClient();
  
  // Check if mega-bootstrap already hydrated groups cache
  const megaData = queryClient.getQueryData(queryKeys.megaBootstrap());
  const groupsFromMega = megaData?.data?.groups;
  
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(1, 20),
    // DISABLE API call if mega-bootstrap already has groups
    enabled: !groupsFromMega,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: false, // NEVER auto-poll - use mega-bootstrap refresh
    initialData: groupsFromMega ? { success: true, groups: groupsFromMega } : undefined,
  });
}
```

**Impact:** -10 API calls per session

### 17.2: Disable useGroupQuery When Mega-Bootstrap Active

**Current Problem:**
```javascript
// Components call BOTH:
const { data: megaData } = useMegaBootstrap(groupId);
const { data: groupData } = useGroupQuery(groupId);  // REDUNDANT!
```

**Solution:**
```javascript
// useExpenseQuery.js - FIXED
export function useGroupQuery(groupId, options = {}) {
  const queryClient = useQueryClient();
  
  // Check if mega-bootstrap already has this group's data
  const megaData = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
  const groupFromMega = megaData?.data?.active_group;
  
  return useQuery({
    queryKey: queryKeys.group(groupId),
    queryFn: () => expenseApi.getGroupFull(groupId),
    // DISABLE if mega-bootstrap has the data
    enabled: !groupFromMega && !!groupId && options.enabled !== false,
    staleTime: 2 * 60 * 1000, // 2 minutes
    // Use mega-bootstrap data as initial data
    initialData: groupFromMega ? {
      success: true,
      group: groupFromMega.group,
      members: groupFromMega.members,
      balances: groupFromMega.balances,
      expenses: groupFromMega.expenses,
    } : undefined,
    ...options
  });
}
```

**Impact:** -6 API calls per session

### 17.3: Single Entry Point Component

**Problem:** Multiple components independently call APIs

**Solution:** Create a data provider that ensures single fetch

```javascript
// components/expenses/ExpenseDataProvider.jsx
import { createContext, useContext, useMemo } from 'react';
import { useMegaBootstrap } from '../../hooks/useExpenseQuery';

const ExpenseDataContext = createContext(null);

export function ExpenseDataProvider({ groupId, children }) {
  // SINGLE SOURCE OF TRUTH - only one API call
  const {
    data: megaData,
    isLoading,
    error,
    refetch
  } = useMegaBootstrap(groupId, {
    staleTime: 2 * 60 * 1000,  // 2 minutes
    gcTime: 10 * 60 * 1000,    // 10 minutes
    refetchOnWindowFocus: true,
    refetchOnMount: 'always'
  });

  const value = useMemo(() => ({
    // Dashboard data
    groups: megaData?.data?.groups || [],
    invitations: megaData?.data?.invitations || [],
    summary: megaData?.data?.summary || {},
    
    // Active group data (if groupId provided)
    activeGroup: megaData?.data?.active_group?.group,
    members: megaData?.data?.active_group?.members || [],
    balances: megaData?.data?.active_group?.balances || [],
    expenses: megaData?.data?.active_group?.expenses || [],
    settlements: megaData?.data?.active_group?.settlements || [],
    groupInvitations: megaData?.data?.active_group?.invitations || [],
    
    // Meta
    isLoading,
    error,
    refetch,
    lastFetched: megaData?.meta?.fetch_time_ms,
  }), [megaData, isLoading, error, refetch]);

  return (
    <ExpenseDataContext.Provider value={value}>
      {children}
    </ExpenseDataContext.Provider>
  );
}

export function useExpenseData() {
  const context = useContext(ExpenseDataContext);
  if (!context) {
    throw new Error('useExpenseData must be used within ExpenseDataProvider');
  }
  return context;
}
```

**Impact:** Guarantees single API call source

---

## Phase 17.4: Backend Request-Scoped Cache (Eliminate Duplicate Reads)

### Problem from Logs

```
[FIRESTORE][R] expense_groups/MlNbAUI4mJqhI4t1FDgl   ← Read 1
[FIRESTORE][R] expense_groups/MlNbAUI4mJqhI4t1FDgl   ← Read 2 (same doc!)
[FIRESTORE][Q] expense_groups [1 results]            ← Query 3 (same!)
```

### Solution: Request Document Cache

```python
# utils/request_cache.py
from flask import g
from typing import Dict, Optional, Any

class RequestDocumentCache:
    """
    Cache Firestore documents within a single HTTP request.
    Prevents duplicate reads of the same document.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._stats = {'hits': 0, 'misses': 0}
    
    def get(self, collection: str, doc_id: str) -> Optional[Dict]:
        key = f"{collection}/{doc_id}"
        if key in self._cache:
            self._stats['hits'] += 1
            return self._cache[key]
        self._stats['misses'] += 1
        return None
    
    def set(self, collection: str, doc_id: str, data: Dict):
        key = f"{collection}/{doc_id}"
        self._cache[key] = data
    
    def get_stats(self) -> Dict:
        return self._stats


def get_request_cache() -> RequestDocumentCache:
    """Get or create request-scoped document cache."""
    if not hasattr(g, '_doc_cache'):
        g._doc_cache = RequestDocumentCache()
    return g._doc_cache


# Apply to BaseRepository
class BaseRepository:
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        # Check request cache first
        cache = get_request_cache()
        cached = cache.get(self._collection_name, doc_id)
        if cached is not None:
            return cached
        
        # Fetch from Firestore
        doc = self._collection.document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            cache.set(self._collection_name, doc_id, data)
            return data
        return None
```

**Impact:** -40% Firestore reads per request

---

## Phase 17.5: Write-Through Cache (Not Invalidate-Then-Read)

### Current Pattern (Bad)

```
Write expense → DELETE Redis cache → Client refetches → Firestore READ → SET Redis
```

### New Pattern (Good)

```
Write expense → SET Redis with written data (skip Firestore read)
```

### Implementation

```python
# services/expense_service.py
def create_expense(self, expense_data: Dict) -> Tuple[Dict, Dict]:
    """
    Create expense with write-through cache.
    Returns (expense, new_balances) for frontend optimistic update.
    """
    # 1. Build complete expense object
    expense = self._build_expense(expense_data)
    
    # 2. Write to Firestore (single write)
    doc_ref = self.expense_repo.collection.document()
    expense['expense_id'] = doc_ref.id
    expense['id'] = doc_ref.id
    doc_ref.set(expense)
    
    # 3. Update balances incrementally (single read-modify-write)
    new_balances = self._update_balances_incremental(expense)
    
    # 4. WRITE-THROUGH CACHE - update with what we wrote
    _write_through_expense_cache(expense['id'], expense)
    _write_through_balances_cache(expense['group_id'], new_balances)
    
    # 5. Return both for frontend (no refetch needed!)
    return expense, new_balances


def _write_through_balances_cache(group_id: str, balances: Dict):
    """Update cache with new balances instead of invalidating."""
    cache = get_cache_manager()
    if not cache or not cache.is_available():
        return
    
    cache.set(
        redis_config.KEY_GROUP_BALANCES.format(gid=group_id),
        balances,
        ttl=redis_config.TTL_BALANCE
    )
```

**Impact:** -60% cache misses after writes

---

## Phase 17.6: API Response with Delta Data

### Current Response (Missing balances)

```json
{
  "success": true,
  "expense": { ... },
  "message": "Expense created"
}
```

### New Response (Include balances)

```json
{
  "success": true,
  "expense": { ... },
  "balances": {
    "user_a": 150.00,
    "user_b": -75.00,
    "user_c": -75.00
  },
  "message": "Expense created"
}
```

### Implementation

```python
# routes/expense_routes.py
@expense_bp.route('/expenses', methods=['POST'])
@require_auth
def create_expense():
    expense_data = request.get_json()
    
    service = ExpenseService()
    expense, balances = service.create_expense_with_balances(expense_data)
    
    return jsonify({
        'success': True,
        'expense': expense,
        'balances': balances,  # Frontend uses this directly!
        'message': 'Expense created successfully'
    }), 201
```

**Impact:** Zero refetch after mutations

---

## Phase 18: Splitwise-Level Architecture

### Target: MAX 10 API Calls Per Complete Session

| Action | API Calls | Firestore Ops |
|--------|-----------|---------------|
| Initial login/dashboard | 1 (mega-bootstrap) | 2R (cache miss) or 0R (cache hit) |
| View first group | 0 (already in mega-bootstrap) | 0 |
| Switch to group 2 | 1 (mega-bootstrap with new group_id) | 1R (cache miss) or 0R |
| Create expense | 1 | 2W |
| Edit expense | 1 | 2W |
| Delete expense | 1 | 1W |
| Create settlement | 1 | 2W |
| Refresh data | 1 (mega-bootstrap) | 0-2R |
| **TOTAL** | **8** | **5R + 7W = 12** |

### Frontend State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND STATE MACHINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  INITIAL → LOADING → READY                                   │
│      │         │        │                                    │
│      │         │        ├── User views group → Use cached   │
│      │         │        │                                    │
│      │         │        ├── User switches group             │
│      │         │        │   └── IF cached → Use cached      │
│      │         │        │   └── ELSE → fetch mega-bootstrap │
│      │         │        │                                    │
│      │         │        ├── User creates expense            │
│      │         │        │   └── Optimistic update           │
│      │         │        │   └── POST /expenses              │
│      │         │        │   └── Merge server response       │
│      │         │        │   └── NO REFETCH                  │
│      │         │        │                                    │
│      │         │        └── Tab hidden → Pause polling      │
│      │         │                                            │
│      │         └── mega-bootstrap response                  │
│      │             └── Hydrate all query caches             │
│      │                                                       │
│      └── App mount                                          │
│          └── GET /mega-bootstrap (single call)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 17 (Week 1-2)

- [ ] **17.1** Frontend: Disable useGroupsQuery when mega-bootstrap cached
- [ ] **17.2** Frontend: Disable useGroupQuery when mega-bootstrap has group
- [ ] **17.3** Frontend: Create ExpenseDataProvider as single data source
- [ ] **17.4** Backend: Implement RequestDocumentCache
- [ ] **17.5** Backend: Write-through cache for expenses and balances
- [ ] **17.6** Backend: Include balances in expense mutation responses

### Phase 18 (Week 3-4)

- [ ] **18.1** Frontend: Enforce single mega-bootstrap entry point
- [ ] **18.2** Backend: Incremental balance updates (not recompute)
- [ ] **18.3** Backend: Extended cache TTLs (30 min for stable data)
- [ ] **18.4** Frontend: Remove all refetchOnSuccess triggers
- [ ] **18.5** Frontend: Implement proper cache hydration from mega-bootstrap
- [ ] **18.6** Add metrics/logging for API call counts

---

## Testing Checklist

### Before Optimization

Run test session and count:
- [ ] API calls: _____ (target: <35)
- [ ] Firestore reads: _____ (target: <50)
- [ ] Firestore writes: _____ (target: <20)
- [ ] Cache hit rate: _____% (target: >60%)

### After Optimization

- [ ] API calls: _____ (target: <10)
- [ ] Firestore reads: _____ (target: <15)
- [ ] Firestore writes: _____ (target: <10)
- [ ] Cache hit rate: _____% (target: >90%)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Stale data after other user's changes | Background polling every 60s when tab visible |
| Optimistic update rollback confusion | Show toast on rollback with retry option |
| Cache hydration race conditions | Use React Query's `initialData` not `setQueryData` in query |
| Extended TTLs causing stale reads | Write-through ensures cache always has latest |

---

## Success Criteria

✅ **Phase 17 Complete When:**
- API calls per session < 15
- No duplicate API calls to same endpoint
- Cache hit rate > 80%
- All 276 backend tests passing

✅ **Phase 18 Complete When:**
- API calls per session < 10
- Firestore ops per session < 15
- Cache hit rate > 90%
- User perceives instant updates (< 100ms UI response)
