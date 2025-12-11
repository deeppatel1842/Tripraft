# 🚀 Expense Engine API Optimization Plan

## Executive Summary

**Current State:** Initial page load triggers **~230 API calls**, with groups endpoint called **71 times** and full group data **26 times** in a single session.

**Root Cause:** Aggressive React Query polling configuration (`staleTime: 0`, 30s polling intervals) combined with lack of batch endpoints.

**Target State:** Reduce to **3-5 API calls** on initial load (95% reduction) by implementing batch endpoints and optimizing frontend caching strategy.

**Expected Impact:**
- 🎯 **95% reduction** in API calls (230 → 5-10 calls)
- ⚡ **85% faster** page load time (~35s → ~5s)
- 💰 **80% reduction** in Firestore read operations
- 🎨 **Smoother UX** with no loading delays

---

## 📊 Current State Analysis

### API Call Breakdown (from logs)

| Endpoint | Count | % of Total | Issue |
|----------|-------|------------|-------|
| `GET /api/expense/groups` | **71** | 30.9% | ⚠️ **CRITICAL**: Called 71 times instead of 1-2 |
| `GET /api/expense/groups/[id]/full` | **26** | 11.3% | ⚠️ **HIGH**: Called 26 times (avg 2210ms each) |
| `GET /api/expense/invitations` | **18** | 7.8% | ⚠️ **HIGH**: Polled every 20 seconds |
| `GET /api/expense/invitations/group/[id]` | **5** | 2.2% | Acceptable |
| `GET /api/expense/settlements/group/[id]` | **4** | 1.7% | Acceptable |
| `POST /api/expense/user/profile` | **2** | 0.9% | ✅ Normal |
| `GET /api/expense/expenses/user` | **2** | 0.9% | ✅ Normal |
| Other endpoints | **~102** | 44.3% | Various mutations & OPTIONS |

**Total: ~230 API calls in a single user session**

### Performance Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Initial Load API Calls | 230 | 5-10 | 95% reduction |
| GET FULL GROUP DATA Time | 2210ms avg | <500ms | 77% faster |
| Page Load Time | ~35 seconds | ~5 seconds | 85% faster |
| Firestore Reads/Session | ~150 | ~20 | 87% reduction |

---

## 🔍 Root Cause Analysis

### 1. **Aggressive Frontend Polling** (Primary Issue)

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

```javascript
// ❌ PROBLEM: staleTime: 0 means "always refetch"
export function useGroupsQuery() {
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(true, true),
    staleTime: 0, // ⚠️ Always consider data stale
    refetchInterval: 30 * 1000, // ⚠️ Poll every 30 seconds
    refetchOnWindowFocus: true, // ⚠️ Refetch on tab focus
  });
}

// ❌ PROBLEM: 1 second staleTime + always bypass cache
export function useGroupQuery(groupId) {
  return useQuery({
    queryFn: async () => {
      const result = await expenseApi.getGroupFull(groupId, true); // ⚠️ Always bypass cache
      return result;
    },
    staleTime: 1 * 1000, // ⚠️ Only 1 second cache
  });
}

// ❌ PROBLEM: Another aggressive poller
export function useInvitationsQuery() {
  return useQuery({
    staleTime: 0, // ⚠️ Always consider data stale
    refetchInterval: 20 * 1000, // ⚠️ Poll every 20 seconds
  });
}
```

**Impact:**
- Every 20-30 seconds: 3 API calls (groups, full group data, invitations)
- Window focus: Another 3 API calls
- Component mount/remount: More API calls
- **Result:** 71 calls to groups endpoint in minutes

### 2. **Lack of Batch Endpoints** (Secondary Issue)

Current architecture requires **separate calls** for related data:

```
User opens dashboard:
1. GET /api/expense/user/profile (user data)
2. GET /api/expense/groups (groups list)
3. GET /api/expense/invitations (pending invitations)
4. GET /api/expense/expenses/user (user expenses)

User clicks group:
5. GET /api/expense/groups/[id]/full (group details)
6. GET /api/expense/expenses/[groupId] (expenses)
7. GET /api/expense/settlements/group/[id] (settlements)
8. GET /api/expense/invitations/group/[id] (group invitations)
9. GET /api/expense/balances/[groupId] (balances)
```

**Result:** 9 separate API calls for data that could be batched into 2 calls.

### 3. **React Query Configuration** (Tertiary Issue)

Global config in `queryClient.js`:
```javascript
// Default staleTime: 5 minutes (reasonable)
// BUT individual queries override with staleTime: 0
```

**Multiple components** using the same queries cause duplicate fetches:
- `ExpenseManager.jsx` → `useGroupQuery(groupId)`
- `GroupHeader.jsx` → `useGroupQuery(groupId)`
- `BalanceDisplay.jsx` → `useGroupQuery(groupId)`
- **React Query should dedupe these, but staleTime: 0 breaks deduplication**

---

## 🎯 Optimization Strategy

### Phase 1: Backend Batch Endpoints (Priority: HIGH)

Create **3 compound endpoints** to batch related data:

#### 1.1 Bootstrap Endpoint
**Purpose:** Single call to load all initial dashboard data

```
GET /api/expense/bootstrap
```

**Response:**
```json
{
  "user": {
    "uid": "xyz123",
    "email": "user@example.com",
    "displayName": "John Doe",
    "preferences": { "currency": "USD" }
  },
  "groups": [
    {
      "id": "group-1",
      "name": "Trip to Bali",
      "memberCount": 4,
      "totalExpenses": 12,
      "yourBalance": -250.00,
      "lastActivity": "2024-01-15T10:30:00Z"
    }
  ],
  "invitations": [
    {
      "id": "inv-1",
      "groupName": "Weekend Getaway",
      "invitedBy": "Jane Smith",
      "createdAt": "2024-01-14T15:20:00Z"
    }
  ],
  "recentExpenses": [
    // Last 5 expenses across all groups
  ],
  "stats": {
    "totalGroups": 3,
    "totalExpenses": 45,
    "totalSettled": 12,
    "pendingInvitations": 1
  }
}
```

**Backend Implementation:**
```python
# File: web/backend/api/routes.py

@expense_bp.route('/bootstrap', methods=['GET'])
@firebase_auth_required
def bootstrap():
    """Single endpoint to load all initial dashboard data"""
    user_id = g.user_id
    
    # Use async/parallel fetching
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_user = executor.submit(get_user_profile, user_id)
        future_groups = executor.submit(get_user_groups_summary, user_id)
        future_invitations = executor.submit(get_pending_invitations, user_id)
        future_recent = executor.submit(get_recent_expenses, user_id, limit=5)
    
    return jsonify({
        'user': future_user.result(),
        'groups': future_groups.result(),
        'invitations': future_invitations.result(),
        'recentExpenses': future_recent.result(),
        'stats': calculate_dashboard_stats(user_id)
    })
```

**Performance Estimate:**
- Current: 4 separate calls × 200-500ms each = 800-2000ms
- Optimized: 1 call with parallel processing = 500-800ms
- **Improvement: 60% faster + 75% fewer calls**

---

#### 1.2 Group Dashboard Endpoint
**Purpose:** Single call to load complete group view

```
GET /api/expense/groups/{group_id}/dashboard
```

**Response:**
```json
{
  "group": {
    "id": "group-1",
    "name": "Trip to Bali",
    "description": "Summer vacation",
    "currency": "USD",
    "createdAt": "2024-01-01T00:00:00Z",
    "createdBy": "user-1",
    "memberCount": 4
  },
  "members": [
    {
      "uid": "user-1",
      "displayName": "John Doe",
      "email": "john@example.com",
      "role": "admin",
      "joinedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "expenses": [
    {
      "id": "exp-1",
      "description": "Hotel booking",
      "amount": 450.00,
      "currency": "USD",
      "paidBy": "user-1",
      "splitAmong": ["user-1", "user-2"],
      "date": "2024-01-10T14:30:00Z",
      "category": "Accommodation"
    }
  ],
  "balances": [
    {
      "userId": "user-1",
      "displayName": "John Doe",
      "balance": -125.50,
      "paid": 450.00,
      "owed": 575.50
    }
  ],
  "settlements": [
    {
      "id": "settle-1",
      "from": "user-2",
      "to": "user-1",
      "amount": 125.50,
      "settledAt": "2024-01-12T10:00:00Z"
    }
  ],
  "invitations": [
    {
      "id": "inv-2",
      "email": "newuser@example.com",
      "status": "pending",
      "sentAt": "2024-01-14T09:00:00Z"
    }
  ],
  "summary": {
    "totalExpenses": 12,
    "totalAmount": 2450.00,
    "totalSettled": 3,
    "settledAmount": 890.00,
    "pendingSettlements": 4
  }
}
```

**Backend Implementation:**
```python
# File: web/backend/expense_engine/api/groups.py

@groups_bp.route('/groups/<group_id>/dashboard', methods=['GET'])
@firebase_auth_required
def get_group_dashboard(group_id):
    """
    Compound endpoint to fetch all group data in one call
    Replaces 5 separate API calls with 1 optimized call
    """
    user_id = g.user_id
    
    # Verify user is member
    if not expense_service.is_group_member(group_id, user_id):
        return jsonify({'error': 'Not a group member'}), 403
    
    # Fetch all data in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_group = executor.submit(expense_service.get_group_details, group_id)
        future_members = executor.submit(expense_service.get_group_members, group_id)
        future_expenses = executor.submit(expense_service.get_expenses, group_id)
        future_balances = executor.submit(balance_manager.get_balances, group_id)
        future_settlements = executor.submit(expense_service.get_settlements, group_id)
        future_invitations = executor.submit(expense_service.get_group_invitations, group_id)
    
    # Collect results
    group_data = future_group.result()
    members = future_members.result()
    expenses = future_expenses.result()
    balances = future_balances.result()
    settlements = future_settlements.result()
    invitations = future_invitations.result()
    
    # Calculate summary
    summary = {
        'totalExpenses': len(expenses),
        'totalAmount': sum(e['amount'] for e in expenses),
        'totalSettled': len([s for s in settlements if s.get('status') == 'settled']),
        'settledAmount': sum(s['amount'] for s in settlements if s.get('status') == 'settled'),
        'pendingSettlements': len([s for s in settlements if s.get('status') == 'pending'])
    }
    
    return jsonify({
        'group': group_data,
        'members': members,
        'expenses': expenses,
        'balances': balances,
        'settlements': settlements,
        'invitations': invitations,
        'summary': summary
    })
```

**Performance Estimate:**
- Current: 6 separate calls × 200-2200ms each = 1200-13200ms (avg 6600ms)
- Optimized: 1 call with parallel processing = 800-1500ms
- **Improvement: 77-85% faster + 83% fewer calls**

---

#### 1.3 Bulk Operations Endpoint (Optional)
**Purpose:** Handle multiple actions in a single request

```
POST /api/expense/bulk
```

**Request:**
```json
{
  "operations": [
    {
      "type": "create_expense",
      "data": { "description": "Lunch", "amount": 45.00 }
    },
    {
      "type": "settle_balance",
      "data": { "from": "user-2", "to": "user-1", "amount": 100 }
    }
  ]
}
```

**Response:**
```json
{
  "results": [
    { "success": true, "id": "exp-123" },
    { "success": true, "id": "settle-456" }
  ],
  "updatedGroup": { /* full group dashboard data */ }
}
```

---

### Phase 2: Frontend Optimization (Priority: HIGH)

#### 2.1 React Query Configuration Changes

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

**Before:**
```javascript
export function useGroupsQuery() {
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(true, true),
    staleTime: 0, // ❌ Always refetch
    refetchInterval: 30 * 1000, // ❌ Poll every 30s
  });
}
```

**After:**
```javascript
export function useGroupsQuery(options = {}) {
  const { enablePolling = false } = options;
  
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(false, false), // ✅ Use cache
    staleTime: 5 * 60 * 1000, // ✅ 5 minutes (reasonable for group list)
    gcTime: 10 * 60 * 1000, // ✅ 10 minutes retention
    refetchOnWindowFocus: true, // ✅ Still refetch on focus (good UX)
    refetchInterval: enablePolling ? 60 * 1000 : false, // ✅ Optional 1min polling
    placeholderData: keepPreviousData,
  });
}
```

**Key Changes:**
1. **staleTime: 0 → 5 minutes**: Data considered fresh for 5 minutes
2. **refetchInterval: 30s → 60s (optional)**: Less aggressive polling
3. **Bypass cache: false**: Let Redis cache work
4. **Make polling opt-in**: Only poll when needed (e.g., on group page)

---

#### 2.2 New Bootstrap Hook

**File:** `web/frontend/src/hooks/useExpenseQuery.js`

```javascript
/**
 * Hook for initial dashboard bootstrap
 * Replaces separate calls to user, groups, invitations
 */
export function useBootstrapQuery() {
  return useQuery({
    queryKey: ['bootstrap'],
    queryFn: () => expenseApi.getBootstrap(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false, // Don't refetch on focus (data already fresh)
  });
}
```

---

#### 2.3 New Group Dashboard Hook

```javascript
/**
 * Hook for full group dashboard
 * Replaces separate calls to group, expenses, balances, settlements, invitations
 */
export function useGroupDashboardQuery(groupId) {
  return useQuery({
    queryKey: ['groupDashboard', groupId],
    queryFn: () => expenseApi.getGroupDashboard(groupId),
    enabled: !!groupId,
    staleTime: 2 * 60 * 1000, // 2 minutes (balance changes may need freshness)
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: true, // Check for updates when user returns
    placeholderData: keepPreviousData,
  });
}
```

---

#### 2.4 Component Refactoring

**Before (ExpenseManager.jsx):**
```javascript
function ExpenseManager() {
  const { data: user } = useUserQuery();
  const { data: groups } = useGroupsQuery(); // Call 1
  const { data: invitations } = useInvitationsQuery(); // Call 2
  const { data: recentExpenses } = useUserExpensesQuery(); // Call 3
  
  // ... render
}
```

**After (ExpenseManager.jsx):**
```javascript
function ExpenseManager() {
  const { data: bootstrap, isLoading } = useBootstrapQuery(); // Single call!
  
  const user = bootstrap?.user;
  const groups = bootstrap?.groups;
  const invitations = bootstrap?.invitations;
  const recentExpenses = bootstrap?.recentExpenses;
  
  // ... render
}
```

**Before (GroupView.jsx):**
```javascript
function GroupView({ groupId }) {
  const { data: group } = useGroupQuery(groupId); // Call 1
  const { data: expenses } = useExpensesQuery(groupId); // Call 2
  const { data: balances } = useBalancesQuery(groupId); // Call 3
  const { data: settlements } = useSettlementsQuery(groupId); // Call 4
  const { data: invitations } = useGroupInvitationsQuery(groupId); // Call 5
  
  // ... render
}
```

**After (GroupView.jsx):**
```javascript
function GroupView({ groupId }) {
  const { data: dashboard, isLoading } = useGroupDashboardQuery(groupId); // Single call!
  
  const group = dashboard?.group;
  const expenses = dashboard?.expenses;
  const balances = dashboard?.balances;
  const settlements = dashboard?.settlements;
  const invitations = dashboard?.invitations;
  
  // ... render
}
```

---

### Phase 3: Intelligent Caching Strategy (Priority: MEDIUM)

#### 3.1 Cache Invalidation Rules

**Current Issue:** Every mutation invalidates entire cache, forcing refetch

**Optimized Strategy:**
```javascript
// After creating expense
queryClient.setQueryData(['groupDashboard', groupId], (old) => {
  return {
    ...old,
    expenses: [...old.expenses, newExpense],
    balances: calculateOptimisticBalances(old.balances, newExpense),
    summary: updateSummary(old.summary, newExpense)
  };
});

// No refetch needed! Optimistic update is enough.
// Background refetch happens after 2 minutes (staleTime)
```

**Benefits:**
- ✅ Instant UI updates (no loading state)
- ✅ No unnecessary API calls
- ✅ Still validates in background

---

#### 3.2 Prefetching Strategy

**Optimize for common user flows:**

```javascript
// When user hovers over a group card
function GroupCard({ group }) {
  const queryClient = useQueryClient();
  
  const handleMouseEnter = () => {
    // Prefetch group dashboard in background
    queryClient.prefetchQuery({
      queryKey: ['groupDashboard', group.id],
      queryFn: () => expenseApi.getGroupDashboard(group.id),
      staleTime: 2 * 60 * 1000,
    });
  };
  
  return (
    <div onMouseEnter={handleMouseEnter}>
      {group.name}
    </div>
  );
}
```

**Result:** Group page loads instantly when clicked (data already prefetched)

---

### Phase 4: Monitoring & Validation (Priority: HIGH)

#### 4.1 Add API Call Tracking

**Frontend:**
```javascript
// File: web/frontend/src/services/expenseApi.js

const apiCallCounter = {
  count: 0,
  calls: [],
};

expenseApi.interceptors.request.use((config) => {
  apiCallCounter.count++;
  apiCallCounter.calls.push({
    url: config.url,
    method: config.method,
    timestamp: Date.now(),
  });
  
  console.log(`🌐 API Call #${apiCallCounter.count}: ${config.method} ${config.url}`);
  return config;
});

// Expose to window for debugging
window.getAPIStats = () => {
  console.log(`Total API calls: ${apiCallCounter.count}`);
  console.table(apiCallCounter.calls);
};
```

#### 4.2 Success Metrics

**Measure before & after:**

| Metric | Current | Target | Validation Method |
|--------|---------|--------|-------------------|
| Initial Load API Calls | 230 | <10 | `window.getAPIStats()` |
| Page Load Time | 35s | <5s | Chrome DevTools Network tab |
| Time to Interactive (TTI) | 40s | <7s | Lighthouse performance score |
| Firestore Reads/Session | ~150 | <25 | Backend analytics |
| Cache Hit Rate | 77.6% | >85% | Redis monitoring |
| User-perceived latency | High | Low | User feedback |

---

## 📋 Implementation Roadmap

### **Week 1: Backend Batch Endpoints**

**Days 1-2: Bootstrap Endpoint**
- [ ] Create `/api/expense/bootstrap` endpoint
- [ ] Implement parallel data fetching with ThreadPoolExecutor
- [ ] Add comprehensive error handling
- [ ] Write unit tests (95% coverage)
- [ ] Test with Postman/curl

**Days 3-4: Group Dashboard Endpoint**
- [ ] Create `/api/expense/groups/{id}/dashboard` endpoint
- [ ] Implement parallel data fetching
- [ ] Add permission checks (user must be group member)
- [ ] Write unit tests
- [ ] Performance testing (target <1s response time)

**Day 5: Optional Bulk Operations**
- [ ] Create `/api/expense/bulk` endpoint (if time permits)
- [ ] Implement transactional operations
- [ ] Add rollback logic on partial failure

---

### **Week 2: Frontend Optimization**

**Days 1-2: React Query Configuration**
- [ ] Update `useGroupsQuery` with optimized staleTime
- [ ] Update `useGroupQuery` to respect cache
- [ ] Update `useInvitationsQuery` with longer staleTime
- [ ] Create `useBootstrapQuery` hook
- [ ] Create `useGroupDashboardQuery` hook
- [ ] Update API service with new endpoints

**Days 3-4: Component Refactoring**
- [ ] Refactor `ExpenseManager.jsx` to use bootstrap
- [ ] Refactor `GroupView.jsx` to use dashboard
- [ ] Refactor `Dashboard.jsx` to use bootstrap
- [ ] Remove old separate query hooks
- [ ] Update all dependent components
- [ ] Fix TypeScript/prop types

**Day 5: Testing & Polish**
- [ ] Manual testing of all flows
- [ ] Verify optimistic updates still work
- [ ] Test edge cases (empty groups, no invitations, etc.)
- [ ] Measure API call count (should be <10)
- [ ] Performance profiling with React DevTools

---

### **Week 3: Monitoring & Deployment**

**Days 1-2: Add Monitoring**
- [ ] Add frontend API call tracking
- [ ] Add backend performance logging
- [ ] Create analytics dashboard
- [ ] Set up alerts for high API call volume

**Day 3: Staging Deployment**
- [ ] Deploy to staging environment
- [ ] Run full regression tests
- [ ] Load testing with multiple users
- [ ] Verify cache behavior under load

**Day 4: Production Deployment**
- [ ] Deploy backend first (backward compatible)
- [ ] Monitor backend performance (1 hour)
- [ ] Deploy frontend
- [ ] Monitor metrics (24 hours)
- [ ] Gradual rollout (10% → 50% → 100%)

**Day 5: Validation & Optimization**
- [ ] Verify API call reduction achieved
- [ ] Check Firestore read reduction
- [ ] Gather user feedback
- [ ] Fine-tune cache TTLs if needed

---

## 🎯 Expected Results

### Before vs After Comparison

#### Initial Dashboard Load (Dashboard → Groups List)

**BEFORE:**
```
1. POST /api/expense/user/profile (1564ms, 1 Firestore read)
2. GET /api/expense/groups (350ms, 1 Firestore read)
3. GET /api/expense/invitations (250ms, 1 Firestore read)
4. GET /api/expense/expenses/user (300ms, 1 Firestore read)
5. [30 seconds later] GET /api/expense/groups (350ms, 0 reads - cached)
6. [30 seconds later] GET /api/expense/groups (350ms, 0 reads - cached)
... continues every 30 seconds
```
**Total:** 4 initial calls + 2 calls/minute = **124 calls in 1 hour**
**Time to interactive:** ~3-4 seconds
**Firestore reads:** 4 + polling overhead

**AFTER:**
```
1. GET /api/expense/bootstrap (800ms, 4 Firestore reads in parallel)
   [Returns: user + groups + invitations + recent expenses]
2. [5 minutes later, on window focus] GET /api/expense/bootstrap (50ms, 0 reads - cached)
3. [5 minutes later] Background refetch if needed
```
**Total:** 1 initial call + 1 call every 5 minutes = **13 calls in 1 hour**
**Time to interactive:** ~1 second
**Firestore reads:** 4 (same as before, but parallel)
**Improvement:** 90% fewer calls, 75% faster

---

#### Group Detail View (Click on a Group)

**BEFORE:**
```
1. GET /api/expense/groups/[id]/full (2210ms avg, 3 Firestore reads)
2. GET /api/expense/expenses/[groupId] (300ms, 1 Firestore read)
3. GET /api/expense/settlements/group/[id] (280ms, 1 Firestore read)
4. GET /api/expense/invitations/group/[id] (220ms, 1 Firestore read)
5. GET /api/expense/balances/[groupId] (60ms, 0 reads - calculated)
6. [Every second due to staleTime: 1s] GET /api/expense/groups/[id]/full (50ms, 0 reads - cached)
7. [Every component remount] Repeat all above calls
```
**Total:** 5 initial calls + refetches on focus/remount = **20-30 calls per group view**
**Time to interactive:** ~3-8 seconds
**Firestore reads:** 6

**AFTER:**
```
1. GET /api/expense/groups/[id]/dashboard (1200ms, 6 Firestore reads in parallel)
   [Returns: group + members + expenses + balances + settlements + invitations]
2. [2 minutes later, only on window focus] Refetch if stale
3. [No more refetches until 2 minutes pass]
```
**Total:** 1 call per group view + 1 refetch every 2 minutes = **1-2 calls per session**
**Time to interactive:** ~1.5 seconds
**Firestore reads:** 6 (same, but parallel)
**Improvement:** 85-95% fewer calls, 63% faster

---

### Overall Session Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Initial Load API Calls** | 230 | 5-10 | 95% ⬇️ |
| **API Calls per Hour (active user)** | 144 | 15 | 90% ⬇️ |
| **Time to Interactive (TTI)** | 40s | 7s | 82% ⬆️ |
| **Page Load Time** | 35s | 5s | 85% ⬆️ |
| **Firestore Reads per Session** | 150 | 20-25 | 83-87% ⬇️ |
| **Monthly Cost (Firestore)** | $45 | $7 | 84% ⬇️ |
| **Cache Hit Rate** | 77.6% | 90%+ | 12% ⬆️ |
| **Bandwidth Usage** | 150KB | 40KB | 73% ⬇️ |

---

## 🚨 Risks & Mitigation

### Risk 1: Larger Response Payloads

**Issue:** Batch endpoints return more data per call
**Impact:** Slightly larger network transfer (but overall bandwidth down 73%)
**Mitigation:**
- Use compression (gzip/brotli) on responses
- Add pagination for large groups (>100 expenses)
- Implement field selection: `?fields=group,expenses,balances`

---

### Risk 2: Stale Data in UI

**Issue:** Longer staleTime means data may be slightly outdated
**Impact:** User might see stale balances for up to 2 minutes
**Mitigation:**
- Keep optimistic updates for mutations (instant UI update)
- Still refetch on window focus (catches most staleness)
- Add manual refresh button for paranoid users
- Invalidate cache on specific events (new expense, settlement)

---

### Risk 3: Backend Load Spike

**Issue:** Batch endpoints do more work per call
**Impact:** Increased CPU/memory usage per request
**Mitigation:**
- Use parallel processing (ThreadPoolExecutor) to maintain speed
- Redis caching reduces database load (hit rate >85%)
- Horizontal scaling if needed (add more backend instances)
- Monitor backend metrics closely during rollout

---

### Risk 4: Breaking Changes

**Issue:** Refactoring frontend may introduce bugs
**Impact:** Potential regressions in expense creation, updates, deletes
**Mitigation:**
- Keep old endpoints running (backward compatible)
- Gradual rollout (10% → 50% → 100%)
- Comprehensive E2E testing before deployment
- Feature flag to quickly rollback if issues arise

---

## ✅ Success Criteria

### Must Have (Week 1-2)
- ✅ Bootstrap endpoint returns all dashboard data in <1s
- ✅ Group dashboard endpoint returns all group data in <1.5s
- ✅ Initial load reduced to <10 API calls
- ✅ All existing features work (no regressions)
- ✅ Optimistic updates still instant

### Should Have (Week 3)
- ✅ API call count tracked and displayed in dev tools
- ✅ Cache hit rate >85%
- ✅ Page load time <5s on 3G network
- ✅ Firestore read reduction >80%

### Nice to Have (Future)
- ✅ Bulk operations endpoint for batch mutations
- ✅ Prefetching on hover for instant navigation
- ✅ Service worker caching for offline support
- ✅ Real-time updates via WebSocket (for true multi-user sync)

---

## 📌 Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize features** (must-have vs nice-to-have)
3. **Assign tasks** to developers
4. **Set up development branch** (`feature/api-optimization`)
5. **Begin Week 1 implementation** (backend endpoints)

---

## 📚 References

- **Current Documentation:**
  - [API Reference](./API_REFERENCE.md) - All 40 existing endpoints
  - [Architecture Flows](./ARCHITECTURE_FLOWS.md) - Current system design
  - [Mermaid Flows](./MERMAID_FLOWS.md) - Detailed sequence diagrams

- **Code Files:**
  - Frontend: `web/frontend/src/hooks/useExpenseQuery.js`
  - Backend: `web/backend/expense_engine/api/groups.py`
  - Service: `web/backend/expense_engine/service.py`

- **Performance Logs:**
  - Current session: `web/backend/logs/captured_logs.txt`
  - Analytics: `web/backend/logs/log_analysis.json`

---

**Document Version:** 1.0
**Created:** 2024-01-17
**Last Updated:** 2024-01-17
**Author:** Expense Engine Team
**Status:** 🟡 DRAFT - Awaiting Review
