# Phase 18: API Call Reduction Plan

**Date:** December 3, 2025  
**Goal:** Reduce API calls from 116 to ~20-30 per session  
**Status:** In Progress - Partial Improvement

---

## Current State After Phase 18.1-18.5 (Session 5)

| Endpoint | Before | After | Change |
|----------|--------|-------|--------|
| `/user/groups` GET | 33 | **25** | -24% |
| `/mega-bootstrap` GET | 13 | **17** | +31% (worse) |
| OPTIONS preflight | 48 | **26** | -46% |
| **Total** | **116** | **~110** | -5% |

### Issues Found:
1. mega-bootstrap calls INCREASED - caching not working as expected
2. Remove member 500 error - document update failing
3. Deduplication working (see logs) but React Query still triggering fetches

---

## Fixes Applied

### Fix 1: Remove Member 500 Error
Changed `update()` to `set(..., merge=True)` in `group_repository.py` to handle missing documents.

### Fix 2: mega-bootstrap Cache Check in queryFn
Added double-check inside queryFn to return cached data if available.

---

## Original Plan

**Problem:** `/user/groups` called 33 times - React Query refetching on window focus, mount, etc.

**Root Cause:** Default React Query settings trigger refetch on:
- Window focus (`refetchOnWindowFocus: true` - default)
- Component mount (`refetchOnMount: true` - default)  
- Network reconnect (`refetchOnReconnect: true` - default)
- Every navigation between components

### Solution: Disable aggressive refetching

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

```javascript
// Add to useUserGroupsQuery
export function useUserGroupsQuery(page = 1, limit = 20) {
  return useQuery({
    queryKey: queryKeys.userGroups(page, limit),
    queryFn: () => expenseApi.getUserGroups(page, limit),
    staleTime: 5 * 60 * 1000,      // 5 minutes - data stays fresh
    gcTime: 30 * 60 * 1000,        // 30 minutes - keep in cache
    refetchOnWindowFocus: false,   // DON'T refetch on tab switch
    refetchOnMount: false,         // DON'T refetch on component mount if data exists
    refetchOnReconnect: false,     // DON'T refetch on network reconnect
    retry: 1,                      // Only 1 retry on failure
  });
}
```

**Expected Result:** `/user/groups` calls: 33 → 3-5

---

## Phase 18.2: Prevent Duplicate Parallel Requests

**Problem:** Multiple components requesting same data simultaneously on app load.

**Root Cause:** Dashboard, Sidebar, and ExpenseManager all call `/user/groups` independently.

### Solution: Use React Query's built-in deduplication + shared query

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

```javascript
// Ensure all components use the SAME query key
const queryKeys = {
  userGroups: (page = 1, limit = 20) => ['userGroups', page, limit],
  // ... other keys
};

// Add networkMode to prevent parallel duplicate requests
export function useUserGroupsQuery(page = 1, limit = 20) {
  return useQuery({
    queryKey: queryKeys.userGroups(page, limit),
    queryFn: () => expenseApi.getUserGroups(page, limit),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: 'always',      // Only fetch if no data exists
    refetchOnReconnect: false,
    networkMode: 'offlineFirst',   // Use cache first, then network
  });
}
```

**Expected Result:** Parallel requests deduplicated automatically

---

## Phase 18.3: Optimize mega-bootstrap Caching

**Problem:** `/mega-bootstrap` called 13 times - cache invalidated too often.

**Root Cause:** Every expense/settlement/invitation mutation invalidates mega-bootstrap.

### Solution A: Longer staleTime on frontend

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

```javascript
export function useMegaBootstrapQuery(activeGroupId, options = {}) {
  return useQuery({
    queryKey: queryKeys.megaBootstrap(activeGroupId),
    queryFn: () => expenseApi.getMegaBootstrap(activeGroupId),
    staleTime: 10 * 60 * 1000,     // 10 minutes - mega data stays fresh longer
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    ...options,
  });
}
```

### Solution B: Don't invalidate mega-bootstrap on mutations

The frontend already has optimistic updates. After mutation success, DON'T invalidate mega-bootstrap - let the optimistic data stand until natural cache expiry or manual refresh.

**File:** `web/frontend/src/hooks/useExpenseQuery.js` - mutation onSuccess handlers

```javascript
// Remove these lines from mutation onSuccess:
// queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
```

**Expected Result:** `/mega-bootstrap` calls: 13 → 1-2

---

## Phase 18.4: Reduce OPTIONS Preflight Requests

**Problem:** 48 OPTIONS requests - one for each unique API call.

**Root Cause:** Browser sends preflight for every unique endpoint.

### Solution: Already implemented (CORS Access-Control-Max-Age)

The backend already returns `Access-Control-Max-Age: 86400` (24 hours). Browser should cache preflight responses.

**Why still seeing OPTIONS?**
1. Different query parameters = different preflight (expected)
2. Browser cache cleared between tests
3. Different browsers handle CORS caching differently

### Additional Fix: Consolidate API endpoints

Instead of calling multiple endpoints, use mega-bootstrap which returns everything in one call.

**Expected Result:** OPTIONS calls will naturally reduce with fewer GET calls

---

## Phase 18.5: Implement Request Deduplication Layer

**Problem:** Same request fired multiple times before first one completes.

### Solution: Add request deduplication in API layer

**File:** `web/frontend/src/services/expenseApi.js`

```javascript
// Add at top of file
const pendingRequests = new Map();

function deduplicateRequest(key, requestFn) {
  if (pendingRequests.has(key)) {
    console.log(`[API] Deduplicating request: ${key}`);
    return pendingRequests.get(key);
  }
  
  const promise = requestFn().finally(() => {
    pendingRequests.delete(key);
  });
  
  pendingRequests.set(key, promise);
  return promise;
}

// Usage in getUserGroups:
getUserGroups: (page = 1, limit = 20) => {
  const key = `getUserGroups:${page}:${limit}`;
  return deduplicateRequest(key, () => 
    apiClient.get(`/expense/user/groups`, { params: { page, limit } })
      .then(res => res.data)
  );
},
```

**Expected Result:** Parallel duplicate requests eliminated

---

## Phase 18.6: Smart Invalidation Strategy

**Problem:** Backend cache invalidation triggers frontend refetch cascade.

### Current Flow (Bad):
1. User adds expense
2. Backend invalidates Redis cache for user
3. Frontend mutation succeeds
4. Frontend invalidates React Query cache
5. React Query refetches → triggers new API call
6. API call misses Redis cache → hits Firestore

### Optimized Flow:
1. User adds expense
2. Frontend applies optimistic update
3. Backend processes mutation
4. Backend returns updated data in response
5. Frontend uses response data (no refetch needed)
6. Redis cache invalidated for OTHER users only

### Implementation:

**Backend:** Return full updated data in mutation responses

```python
# expense_routes.py - create_expense endpoint
return jsonify({
    'success': True,
    'expense': expense_data,
    'balances': updated_balances,  # Include updated balances
    'group_summary': updated_summary  # Include updated summary
}), 201
```

**Frontend:** Use response data instead of refetching

```javascript
// useExpenseQuery.js - useCreateExpenseMutation
onSuccess: (data, variables) => {
  // Instead of invalidating, use the response data directly
  if (data.balances) {
    queryClient.setQueryData(queryKeys.megaBootstrap(variables.group_id), (old) => {
      if (!old) return old;
      return {
        ...old,
        data: {
          ...old.data,
          active_group: {
            ...old.data.active_group,
            balances: data.balances,
          }
        }
      };
    });
  }
  // DON'T invalidate - we already have the fresh data
}
```

---

## Implementation Priority

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| 18.1 | Low | High | **P0** - Do first |
| 18.2 | Low | Medium | **P0** - Do first |
| 18.3 | Low | High | **P1** - Do second |
| 18.5 | Medium | Medium | **P1** - Do second |
| 18.4 | N/A | Auto | Automatic |
| 18.6 | High | High | **P2** - Future |

---

## Expected Results After Implementation

| Endpoint | Before | After Phase 18.1-18.3 | After Phase 18.5-18.6 |
|----------|--------|----------------------|----------------------|
| `/user/groups` GET | 33 | 5-8 | 2-3 |
| `/mega-bootstrap` GET | 13 | 3-5 | 1-2 |
| OPTIONS | 48 | 15-20 | 5-10 |
| **Total** | **116** | **~35** | **~20** |

---

## Quick Win: Phase 18.1 Implementation

The fastest fix is adding these options to the React Query hooks:

```javascript
{
  staleTime: 5 * 60 * 1000,      // 5 minutes
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  refetchOnReconnect: false,
}
```

This alone should reduce `/user/groups` from 33 to ~5 calls.
