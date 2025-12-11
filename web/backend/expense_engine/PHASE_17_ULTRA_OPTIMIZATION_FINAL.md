# Phase 17: Ultra-Optimization - 5-6 Firestore Ops Per Session

## Executive Summary

**Goal:** Achieve Splitwise-level efficiency with MAX 5-6 Firestore operations per complete user session  
**Timeline:** 2-3 weeks  
**Complexity:** High (architectural changes)  
**Risk:** Low (backward compatible)

---

## The Vision: How Splitwise Does It

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SPLITWISE ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   USER OPENS APP                                                             │
│   └── 1 API call → Returns EVERYTHING (groups, balances, expenses, friends) │
│   └── Cached for 5-10 minutes                                                │
│   └── 0 Firestore reads if cached                                            │
│                                                                              │
│   USER ADDS EXPENSE                                                          │
│   └── 1 API call → POST /expense                                             │
│   └── Server: 1 write (expense) + 1 write (balance delta)                    │
│   └── Response includes NEW balances (no refetch!)                           │
│   └── Frontend: Optimistic update, merge server response                     │
│   └── Total: 0 reads, 2 writes                                               │
│                                                                              │
│   USER VIEWS ANOTHER GROUP                                                   │
│   └── 0 API calls if prefetched                                              │
│   └── OR 1 API call → Returns full group from cache                          │
│                                                                              │
│   BACKGROUND SYNC (every 60s when tab visible)                               │
│   └── 1 API call → Delta sync only                                           │
│   └── "What changed since timestamp X?"                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current State vs Target State

### Current (From December 2, 2025 Logs)

| Action | API Calls | Firestore Ops | Time |
|--------|-----------|---------------|------|
| Dashboard load | 3-4 | 9R | 2000ms |
| View group | 2-3 | 7R | 1500ms |
| Create expense | 1 | 4R + 3W = 7 | 3200ms |
| Delete expense | 1 | 3R + 1W = 4 | 2400ms |
| **Full Session** | **35+** | **80+** | - |

### Target (Phase 17)

| Action | API Calls | Firestore Ops | Time |
|--------|-----------|---------------|------|
| Dashboard load | 1 | 0R (cache) or 2R (cold) | 100ms / 400ms |
| View group | 0 | 0R (prefetched) | 0ms |
| Create expense | 1 | 0R + 2W = 2 | 300ms |
| Delete expense | 1 | 0R + 1W = 1 | 200ms |
| **Full Session** | **5-7** | **5-6** | - |

---

## Is This Possible? YES - Here's How

### The 4 Pillars of Ultra-Optimization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      4 PILLARS OF ULTRA-OPTIMIZATION                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PILLAR 1: AGGRESSIVE CACHING (90%+ hit rate)                               │
│  ├── 3-Layer Cache: Browser (0ms) → Redis (5ms) → Firestore (200ms)         │
│  ├── Extended TTLs: 30 min for stable data, 5 min for volatile              │
│  ├── Write-through: Update cache on write, never invalidate                  │
│  └── Prefetch: Load adjacent groups in background                            │
│                                                                              │
│  PILLAR 2: ZERO READS ON WRITES                                              │
│  ├── Trust what you write (no read-after-write)                              │
│  ├── Request-scoped cache (no duplicate reads in same request)               │
│  ├── Delta balance updates (not full recompute)                              │
│  └── Return new state in mutation response                                   │
│                                                                              │
│  PILLAR 3: SINGLE API ENTRY POINT                                            │
│  ├── Mega-bootstrap returns EVERYTHING                                       │
│  ├── Frontend uses single data provider                                      │
│  ├── Hydrate all query caches from single response                           │
│  └── No parallel duplicate calls                                             │
│                                                                              │
│  PILLAR 4: OPTIMISTIC MUTATIONS                                              │
│  ├── Update UI immediately (before server confirms)                          │
│  ├── Server returns delta (new balances only)                                │
│  ├── Merge delta into cache (no full refetch)                                │
│  └── Rollback on error                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 17 Implementation Plan

### Week 1: Backend Zero-Read Writes

#### 17.1 Request-Scoped Document Cache

**What:** Cache Firestore documents within a single HTTP request  
**Why:** Same document read 2-3x in one request (expense, group, balances)  
**Impact:** -40% Firestore reads

```python
# utils/request_cache.py
from flask import g
from functools import wraps

class RequestDocumentCache:
    """
    Per-request cache to prevent duplicate Firestore reads.
    Lives only for duration of single HTTP request.
    """
    
    def __init__(self):
        self._cache = {}
        self._stats = {'hits': 0, 'misses': 0, 'sets': 0}
    
    def get(self, collection: str, doc_id: str):
        key = f"{collection}/{doc_id}"
        if key in self._cache:
            self._stats['hits'] += 1
            return self._cache[key]
        self._stats['misses'] += 1
        return None
    
    def set(self, collection: str, doc_id: str, data: dict):
        key = f"{collection}/{doc_id}"
        self._cache[key] = data
        self._stats['sets'] += 1
    
    def get_stats(self):
        return self._stats


def get_request_cache():
    """Get or create request-scoped cache."""
    if not hasattr(g, '_request_doc_cache'):
        g._request_doc_cache = RequestDocumentCache()
    return g._request_doc_cache


def request_cached(func):
    """Decorator to cache repository get_by_id calls."""
    @wraps(func)
    def wrapper(self, doc_id: str, *args, **kwargs):
        cache = get_request_cache()
        cached = cache.get(self._collection_name, doc_id)
        if cached is not None:
            return cached
        
        result = func(self, doc_id, *args, **kwargs)
        if result:
            cache.set(self._collection_name, doc_id, result)
        return result
    return wrapper
```

**Apply to BaseRepository:**
```python
class BaseRepository:
    @request_cached
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        doc = self._collection.document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
```

---

#### 17.2 Trust-What-You-Write Pattern

**What:** Don't read a document after writing it  
**Why:** We already know what we wrote  
**Impact:** -30% Firestore reads on mutations

```python
# BEFORE (reads after write)
def create_expense(self, data):
    doc_ref = self.collection.document()
    doc_ref.set(data)
    return self.get_by_id(doc_ref.id)  # UNNECESSARY READ!

# AFTER (trust what we wrote)
def create_expense(self, data):
    doc_ref = self.collection.document()
    data['id'] = doc_ref.id
    data['expense_id'] = doc_ref.id
    data['created_at'] = datetime.utcnow().isoformat()
    doc_ref.set(data)
    return data  # Return what we wrote, no read needed
```

---

#### 17.3 Write-Through Cache (NOT Invalidate-Then-Read)

**What:** Update Redis cache with written value instead of deleting  
**Why:** Current: DELETE cache → next read = Firestore. New: SET cache → next read = Redis  
**Impact:** -60% cache misses after writes

```python
def _write_through_cache(expense_id: str, expense: dict, group_id: str, balances: dict):
    """
    Update caches with written data instead of invalidating.
    Next read will hit cache, not Firestore.
    """
    cache = get_cache_manager()
    if not cache or not cache.is_available():
        return
    
    # Update individual expense cache
    cache.set(
        f"expense:expense:{expense_id}",
        expense,
        ttl=300  # 5 minutes
    )
    
    # Update group balances cache
    cache.set(
        f"expense:group_balances:{group_id}",
        balances,
        ttl=300
    )
    
    # Update mega-bootstrap cache (append expense)
    # This is key - user sees new expense without API call
    _append_expense_to_mega_cache(group_id, expense, balances)


def _append_expense_to_mega_cache(group_id: str, expense: dict, balances: dict):
    """Append new expense to mega-bootstrap cache without full invalidation."""
    cache = get_cache_manager()
    
    # Get all user IDs in group (from group members)
    group = cache.get(f"expense:group:{group_id}")
    if not group:
        return
    
    member_ids = [m.get('user_id') for m in group.get('members', [])]
    
    for user_id in member_ids:
        cache_key = f"expense:mega_bootstrap:{user_id}:{group_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data and cached_data.get('data', {}).get('active_group'):
            # Prepend new expense to list
            expenses = cached_data['data']['active_group'].get('expenses', [])
            expenses.insert(0, expense)
            cached_data['data']['active_group']['expenses'] = expenses[:50]  # Keep 50
            
            # Update balances
            cached_data['data']['active_group']['balances'] = balances
            
            # Re-cache with same TTL
            cache.set(cache_key, cached_data, ttl=120)
```

---

#### 17.4 Incremental Balance Updates

**What:** Update balances with delta, not full recomputation  
**Why:** Currently reads ALL expenses to recalculate. New: just apply +/- delta  
**Impact:** N reads → 1 read

```python
def update_balances_incremental(self, group_id: str, expense: dict, operation: str = 'add'):
    """
    Update balances incrementally without reading all expenses.
    
    Args:
        group_id: Group ID
        expense: The expense being added/removed
        operation: 'add' or 'remove'
    """
    # 1. Read current balances (1 Firestore read, cached after)
    current_balances = self.get_group_balances(group_id)
    
    # 2. Calculate delta (in memory, 0 reads)
    multiplier = 1 if operation == 'add' else -1
    amount = float(expense.get('amount', 0))
    paid_by = expense.get('paid_by')
    splits = expense.get('splits', [])
    
    # Payer gets credit
    current_balances[paid_by] = current_balances.get(paid_by, 0) + (amount * multiplier)
    
    # Each split participant gets debit
    for split in splits:
        user_id = split.get('user_id')
        split_amount = float(split.get('amount', 0))
        current_balances[user_id] = current_balances.get(user_id, 0) - (split_amount * multiplier)
    
    # 3. Write updated balances (1 Firestore write)
    self.balance_repo.set_group_balances(group_id, current_balances)
    
    # 4. Write-through cache
    cache = get_cache_manager()
    if cache:
        cache.set(f"expense:group_balances:{group_id}", current_balances, ttl=300)
    
    return current_balances
```

---

#### 17.5 Mutation Response with New State

**What:** Return new balances in expense creation response  
**Why:** Frontend doesn't need to refetch to see updated balances  
**Impact:** -1 API call per mutation

```python
# routes/expense_routes.py
@expense_bp.route('/expenses', methods=['POST'])
@require_auth
def create_expense():
    data = request.get_json()
    service = ExpenseService()
    
    # Create expense and get updated balances in one operation
    expense, new_balances = service.create_expense_with_balances(data)
    
    return jsonify({
        'success': True,
        'expense': expense,
        'balances': new_balances,  # Frontend uses directly!
        'message': 'Expense created'
    }), 201
```

---

### Week 2: Frontend Single Entry Point

#### 17.6 ExpenseDataProvider - Single Source of Truth

**What:** All expense data flows through one provider  
**Why:** Prevents multiple components from making duplicate API calls  
**Impact:** 4 parallel calls → 1 call

```jsx
// context/ExpenseDataContext.jsx
import { createContext, useContext, useMemo, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useMegaBootstrap, queryKeys } from '../hooks/useExpenseQuery';

const ExpenseDataContext = createContext(null);

export function ExpenseDataProvider({ activeGroupId, children }) {
  const queryClient = useQueryClient();
  
  // SINGLE API CALL - everything comes from here
  const {
    data: megaData,
    isLoading,
    error,
    refetch
  } = useMegaBootstrap(activeGroupId, {
    staleTime: 2 * 60 * 1000,      // 2 minutes fresh
    gcTime: 10 * 60 * 1000,        // 10 minutes in cache
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

  // Memoized data selectors
  const value = useMemo(() => ({
    // Dashboard data
    groups: megaData?.data?.groups || [],
    invitations: megaData?.data?.invitations || [],
    summary: megaData?.data?.summary || {},
    user: megaData?.data?.user,
    
    // Active group data
    activeGroup: megaData?.data?.active_group?.group || null,
    members: megaData?.data?.active_group?.members || [],
    allMembersMap: megaData?.data?.active_group?.all_members_map || {},
    balances: megaData?.data?.active_group?.balances || [],
    expenses: megaData?.data?.active_group?.expenses || [],
    settlements: megaData?.data?.active_group?.settlements || [],
    groupInvitations: megaData?.data?.active_group?.invitations || [],
    
    // Pagination
    expensesPagination: megaData?.data?.active_group?.expenses_pagination,
    
    // State
    isLoading,
    error,
    
    // Actions
    refetch,
    
    // Meta
    fetchTime: megaData?.meta?.fetch_time_ms,
    cacheHit: megaData?.cache_stats?.hits > 0,
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

---

#### 17.7 Disable Redundant Queries

**What:** Disable individual queries when mega-bootstrap has data  
**Why:** Prevents `useGroupsQuery`, `useGroupQuery` from making duplicate calls

```javascript
// hooks/useExpenseQuery.js

export function useGroupsQuery() {
  const queryClient = useQueryClient();
  
  // Check if mega-bootstrap already hydrated this
  const megaGroups = queryClient.getQueryData(queryKeys.megaBootstrap())?.data?.groups;
  
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(1, 20),
    // DISABLED if mega-bootstrap has groups
    enabled: !megaGroups,
    staleTime: 5 * 60 * 1000,
    refetchInterval: false, // NEVER auto-poll
    initialData: megaGroups ? { success: true, groups: megaGroups } : undefined,
  });
}

export function useGroupQuery(groupId, options = {}) {
  const queryClient = useQueryClient();
  
  // Check if mega-bootstrap has this group
  const megaGroup = queryClient.getQueryData(queryKeys.megaBootstrap(groupId))?.data?.active_group;
  
  return useQuery({
    queryKey: queryKeys.group(groupId),
    queryFn: () => expenseApi.getGroupFull(groupId),
    // DISABLED if mega-bootstrap has this group
    enabled: !megaGroup && !!groupId && options.enabled !== false,
    staleTime: 2 * 60 * 1000,
    initialData: megaGroup ? {
      success: true,
      group: megaGroup.group,
      members: megaGroup.members,
      balances: megaGroup.balances,
      expenses: megaGroup.expenses,
    } : undefined,
  });
}
```

---

#### 17.8 Optimistic Mutations with Server Delta

**What:** Update UI immediately, merge server response (not refetch)  
**Why:** User sees instant feedback, no loading spinner

```javascript
export function useCreateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (expenseData) => expenseApi.createExpense(expenseData),
    
    onMutate: async (newExpense) => {
      const groupId = newExpense.group_id;
      
      // Cancel in-flight queries
      await queryClient.cancelQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      
      // Snapshot for rollback
      const previousData = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      
      // OPTIMISTIC UPDATE - show immediately
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        const optimisticExpense = {
          ...newExpense,
          id: `temp_${Date.now()}`,
          expense_id: `temp_${Date.now()}`,
          created_at: new Date().toISOString(),
          _optimistic: true,
        };
        
        // Add expense to front of list
        const newExpenses = [optimisticExpense, ...old.data.active_group.expenses];
        
        // Calculate optimistic balances
        const newBalances = calculateOptimisticBalances(
          old.data.active_group.balances,
          newExpense
        );
        
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              expenses: newExpenses,
              balances: newBalances,
            }
          }
        };
      });
      
      return { previousData, groupId };
    },
    
    onSuccess: (serverResponse, variables, context) => {
      // MERGE server response (not refetch!)
      queryClient.setQueryData(queryKeys.megaBootstrap(context.groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        // Replace temp expense with real one
        const newExpenses = old.data.active_group.expenses.map(exp =>
          exp._optimistic ? serverResponse.expense : exp
        );
        
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              expenses: newExpenses,
              balances: serverResponse.balances, // Use server balances
            }
          }
        };
      });
    },
    
    onError: (err, variables, context) => {
      // ROLLBACK on error
      if (context?.previousData) {
        queryClient.setQueryData(
          queryKeys.megaBootstrap(context.groupId),
          context.previousData
        );
      }
    },
  });
}


function calculateOptimisticBalances(currentBalances, expense) {
  const newBalances = [...currentBalances];
  const amount = parseFloat(expense.amount) || 0;
  const paidBy = expense.paid_by;
  const splits = expense.splits || [];
  
  return newBalances.map(b => {
    let newBalance = b.balance;
    
    // Payer gets credit
    if (b.user_id === paidBy) {
      newBalance += amount;
    }
    
    // Split participants get debit
    const split = splits.find(s => s.user_id === b.user_id);
    if (split) {
      newBalance -= parseFloat(split.amount) || 0;
    }
    
    return { ...b, balance: newBalance, net_balance: newBalance };
  });
}
```

---

### Week 3: Extended Cache Strategy

#### 17.9 Cache TTL Strategy

| Data Type | TTL | Invalidation Strategy | Why |
|-----------|-----|----------------------|-----|
| `membership` | 30 min | On member add/remove only | Rarely changes |
| `user_groups` | 30 min | On join/leave group | Rarely changes |
| `group` | 10 min | On group settings change | Moderately stable |
| `group_balances` | 5 min | Write-through on mutations | Frequently changes |
| `group_expenses` | 5 min | Append-only on create | Changes on CRUD |
| `mega_bootstrap` | 2 min | Write-through on mutations | Composite cache |
| `display_names` | 1 hour | Never (names rarely change) | Very stable |

```python
# config.py - Updated TTLs
@dataclass
class RedisConfig:
    # Extended TTLs for stable data
    TTL_MEMBERSHIP: int = 1800      # 30 minutes
    TTL_USER_GROUPS: int = 1800     # 30 minutes
    TTL_GROUP: int = 600            # 10 minutes
    TTL_DISPLAY_NAME: int = 3600    # 1 hour
    
    # Moderate TTLs for volatile data (but write-through)
    TTL_GROUP_BALANCES: int = 300   # 5 minutes
    TTL_GROUP_EXPENSES: int = 300   # 5 minutes
    TTL_GROUP_SUMMARY: int = 300    # 5 minutes
    
    # Short TTLs for composite caches
    TTL_MEGA_BOOTSTRAP: int = 120   # 2 minutes
```

---

#### 17.10 Prefetch Adjacent Groups

**What:** When user views group list, prefetch top 3 groups in background  
**Why:** Instant navigation to any group

```javascript
// hooks/useExpenseQuery.js
export function usePrefetchGroups(groups, prefetchCount = 3) {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    if (!groups?.length) return;
    
    // Prefetch top N groups
    groups.slice(0, prefetchCount).forEach(group => {
      const groupId = group.group_id || group.id;
      
      // Only prefetch if not already cached
      if (!queryClient.getQueryData(queryKeys.megaBootstrap(groupId))) {
        queryClient.prefetchQuery({
          queryKey: queryKeys.megaBootstrap(groupId),
          queryFn: () => expenseApi.getMegaBootstrap({ activeGroupId: groupId }),
          staleTime: 2 * 60 * 1000,
        });
      }
    });
  }, [groups, prefetchCount, queryClient]);
}
```

---

## Final Architecture: 5-6 Ops Per Session

### Complete Session Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ULTRA-OPTIMIZED SESSION FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. USER OPENS APP (Dashboard)                                               │
│     └── Frontend: GET /mega-bootstrap                                        │
│     └── Backend: Check Redis cache                                           │
│         ├── HIT → Return cached (0 Firestore ops)                           │
│         └── MISS → 2 Firestore reads (groups, user)                         │
│     └── Cache result for 2 minutes                                           │
│     └── Prefetch top 3 groups in background                                  │
│                                                                              │
│     Firestore: 0R (cache) or 2R (cold)                                      │
│                                                                              │
│  2. USER VIEWS GROUP                                                         │
│     └── Frontend: Data already in mega-bootstrap cache                       │
│     └── OR: GET /mega-bootstrap?active_group_id=XXX (if not prefetched)     │
│     └── Backend: Check Redis cache                                           │
│         ├── HIT → Return cached (0 Firestore ops)                           │
│         └── MISS → 1 Firestore read (group_full)                            │
│                                                                              │
│     Firestore: 0R (cache/prefetch) or 1R (cold)                             │
│                                                                              │
│  3. USER CREATES EXPENSE                                                     │
│     └── Frontend: Optimistic update (instant UI)                             │
│     └── Frontend: POST /expenses                                             │
│     └── Backend:                                                             │
│         ├── Request cache: group already loaded (0R)                         │
│         ├── Write expense (1W)                                               │
│         ├── Incremental balance update (1W)                                  │
│         ├── Write-through cache (update, not delete)                         │
│         └── Return expense + new balances                                    │
│     └── Frontend: Merge server response (no refetch)                         │
│                                                                              │
│     Firestore: 0R + 2W = 2 ops                                              │
│                                                                              │
│  4. USER DELETES EXPENSE                                                     │
│     └── Same pattern as create                                               │
│     └── Firestore: 0R + 1W = 1 op                                           │
│                                                                              │
│  5. USER CREATES SETTLEMENT                                                  │
│     └── Firestore: 0R + 2W = 2 ops                                          │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│  TOTAL SESSION (typical): 0-3R + 3-5W = 3-6 Firestore ops                   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Operation Count

### Scenario: User adds 2 expenses, deletes 1, views 2 groups

| Action | API Calls | Firestore Reads | Firestore Writes | Total Ops |
|--------|-----------|-----------------|------------------|-----------|
| Dashboard load (cached) | 1 | 0 | 0 | 0 |
| View group 1 (prefetched) | 0 | 0 | 0 | 0 |
| Create expense 1 | 1 | 0 | 2 | 2 |
| Create expense 2 | 1 | 0 | 2 | 2 |
| Delete expense | 1 | 0 | 1 | 1 |
| View group 2 (prefetched) | 0 | 0 | 0 | 0 |
| Background sync (60s) | 1 | 0 | 0 | 0 |
| **TOTAL** | **5** | **0** | **5** | **5** |

### Worst Case: Cold cache, everything misses

| Action | API Calls | Firestore Reads | Firestore Writes | Total Ops |
|--------|-----------|-----------------|------------------|-----------|
| Dashboard load (cold) | 1 | 2 | 0 | 2 |
| View group 1 (cold) | 1 | 1 | 0 | 1 |
| Create expense 1 | 1 | 0 | 2 | 2 |
| **TOTAL** | **3** | **3** | **2** | **5** |

---

## Implementation Checklist

### Week 1: Backend

- [ ] 17.1 Request-scoped document cache
- [ ] 17.2 Trust-what-you-write pattern in repositories
- [ ] 17.3 Write-through cache functions
- [ ] 17.4 Incremental balance updates
- [ ] 17.5 Return balances in mutation responses

### Week 2: Frontend

- [ ] 17.6 ExpenseDataProvider context
- [ ] 17.7 Disable redundant queries
- [ ] 17.8 Optimistic mutations with server delta merge
- [ ] Update all components to use ExpenseDataProvider

### Week 3: Cache & Testing

- [ ] 17.9 Update cache TTLs
- [ ] 17.10 Implement prefetch for adjacent groups
- [ ] Add metrics/logging for operation counts
- [ ] Performance testing
- [ ] Update all 276 tests

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| API calls/session | 35+ | ≤7 | Frontend network tab |
| Firestore reads/session | 50+ | ≤5 | Backend logs |
| Firestore writes/session | 30+ | ≤5 | Backend logs |
| Cache hit rate | 60% | ≥95% | Redis stats |
| Avg response time | 500ms | ≤100ms | Backend logs |
| Time to interactive | 2s | ≤400ms | Lighthouse |

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Stale data after other user changes | Medium | Medium | Background sync every 60s |
| Optimistic update rollback confusion | Low | Low | Toast notification with retry |
| Cache memory pressure | Low | Low | 10 min gcTime, LRU eviction |
| Race conditions on parallel updates | Low | High | Request-scoped cache prevents |

---

## Conclusion

**Yes, 5-6 Firestore ops per session is absolutely achievable.**

The key insights:
1. **Cache aggressively** - Most data doesn't change often
2. **Trust what you write** - Don't read back what you just wrote
3. **Update, don't invalidate** - Write-through cache eliminates re-reads
4. **Single entry point** - One API call returns everything
5. **Optimistic + merge** - UI updates instantly, no refetch needed

This matches how Splitwise achieves their efficiency, and our architecture already has most of the pieces in place. Phase 17 connects them properly.
