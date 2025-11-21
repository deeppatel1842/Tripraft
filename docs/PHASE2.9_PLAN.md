# Phase 2.9: React Query Migration

**Goal**: Replace manual state management with React Query hooks for 50% fewer API calls

**Status**: 🚧 In Progress

---

## Migration Strategy

### Current Architecture (Manual State):
```
ExpenseManager.jsx uses custom hooks:
├── useExpenseApi() - Auth state
├── useUserGroups() - Groups list with manual reload
├── useUserExpenses() - Personal expenses with manual reload
└── useGroup(groupId) - Single group with manual reload

Problems:
- Manual reload() calls everywhere
- useEffect dependencies cause redundant fetches
- No request deduplication
- No automatic cache invalidation
```

### Target Architecture (React Query):
```
ExpenseManager.jsx uses React Query hooks:
├── useExpenseApi() - Auth state (keep as-is)
├── useGroupsQuery() - Automatic caching, deduplication
├── useExpensesQuery(groupId) - Automatic refetch on stale
├── useGroupQuery(groupId) - Smart cache with 30s stale time
└── Mutations - Auto-invalidate related queries

Benefits:
- Zero manual reload() calls needed
- Automatic request deduplication  
- Smart cache invalidation
- Retry logic included
```

---

## Step-by-Step Migration Plan

### Phase 2.9A: Prepare Migration (30 min)
- [x] Create React Query hooks (done in Phase 2.8)
- [ ] Add React Query DevTools for debugging
- [ ] Document current API call count (baseline)

### Phase 2.9B: Migrate Group Operations (1 hour)
- [ ] Replace `useUserGroups()` with `useGroupsQuery()`
- [ ] Replace `useGroup(groupId)` with `useGroupQuery(groupId)`
- [ ] Remove manual `reloadGroups()` calls
- [ ] Update create/delete group to use mutations

### Phase 2.9C: Migrate Expense Operations (1 hour)
- [ ] Replace expense creation with `useCreateExpenseMutation()`
- [ ] Replace expense updates with `useUpdateExpenseMutation()`
- [ ] Replace expense deletion with `useDeleteExpenseMutation()`
- [ ] Remove manual `reload()` calls after mutations

### Phase 2.9D: Migrate Settlement Operations (30 min)
- [ ] Replace settlement creation with `useCreateSettlementMutation()`
- [ ] Update `handleSettlementSuccess` to use mutation
- [ ] Remove manual settlement reload calls

### Phase 2.9E: Testing & Verification (30 min)
- [ ] Measure API call reduction (target: 50%)
- [ ] Test cache invalidation works correctly
- [ ] Verify optimistic updates still function
- [ ] Check all features work without errors

---

## Detailed Implementation

### 1. Add React Query DevTools

**File**: `web/frontend/src/App.jsx`

```jsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export default function App() {
  return (
    <AuthProvider>
      <GroupPlannerProvider>
        <Routes>
          {/* ...routes */}
        </Routes>
        <ReactQueryDevtools initialIsOpen={false} />
      </GroupPlannerProvider>
    </AuthProvider>
  );
}
```

Benefits:
- See all queries and their status
- Inspect cache contents
- Debug stale/fresh queries
- Monitor network activity

---

### 2. Migrate useUserGroups → useGroupsQuery

**Before (Manual State)**:
```jsx
const { groups, loading, reload: reloadGroups, createGroup, deleteGroup } = useUserGroups();

// Manual reload needed after actions
await createGroup(data);
await reloadGroups();
```

**After (React Query)**:
```jsx
const { data: groups = [], isLoading: groupsLoading } = useGroupsQuery();
const createGroupMutation = useCreateGroupMutation();
const deleteGroupMutation = useDeleteGroupMutation();

// Auto-refresh after mutation (no manual reload!)
await createGroupMutation.mutateAsync(data);
// ✅ groups list automatically refreshed
```

---

### 3. Migrate useGroup → useGroupQuery

**Before (Manual State)**:
```jsx
const { 
  group, 
  members, 
  expenses, 
  balances, 
  reload: reloadActiveGroup 
} = useGroup(state.activeGroupId);

// Manual reload with cache bypass
await reloadActiveGroup(true);
```

**After (React Query)**:
```jsx
const { 
  data: groupData, 
  isLoading 
} = useGroupQuery(state.activeGroupId);

// Extract data (React Query manages it)
const group = groupData?.group;
const members = groupData?.members || [];
const expenses = groupData?.expenses || [];
const balances = groupData?.balances || [];

// Force refetch with cache bypass
queryClient.invalidateQueries({ queryKey: queryKeys.group(groupId) });
```

---

### 4. Migrate Expense Mutations

**Before (Manual API calls)**:
```jsx
const handleSaveTransaction = async (transactionData) => {
  if (isEditing) {
    await expenseApi.updateExpense(id, data);
  } else {
    await expenseApi.createExpense(data);
  }
  
  // Manual reload
  if (state.mode === 'group') {
    await reloadActiveGroup(true); // Bypass cache
  } else {
    await reloadPersonalExpenses();
  }
};
```

**After (React Query Mutations)**:
```jsx
const createExpense = useCreateExpenseMutation();
const updateExpense = useUpdateExpenseMutation();

const handleSaveTransaction = async (transactionData) => {
  if (isEditing) {
    await updateExpense.mutateAsync({ expenseId: id, data });
  } else {
    await createExpense.mutateAsync(data);
  }
  
  // ✅ No manual reload needed!
  // React Query auto-invalidates group/expenses queries
};
```

---

### 5. Migrate Settlement Creation

**Before (Manual)**:
```jsx
const handleSettlementSuccess = async (settlementData) => {
  setOptimisticBalances(null);
  setOptimisticExpenses([]);
  
  await expenseApi.createSettlement(settlementData);
  
  await Promise.all([
    loadSettlements(state.activeGroupId),
    reloadActiveGroup(true) // Force cache bypass
  ]);
};
```

**After (React Query)**:
```jsx
const createSettlement = useCreateSettlementMutation();

const handleSettlementSuccess = async (settlementData) => {
  setOptimisticBalances(null);
  setOptimisticExpenses([]);
  
  await createSettlement.mutateAsync(settlementData);
  
  // ✅ Mutation automatically:
  // - Invalidates group query
  // - Invalidates settlements query
  // - Refetches with cache bypass
};
```

---

## Expected Performance Improvements

### API Call Reduction:

**Current Behavior (Manual State)**:
```
User switches to Group A:
1. GET /groups/:id/full
2. GET /settlements/:id
3. GET /invitations/:id

User switches to Group B:
4. GET /groups/:id/full
5. GET /settlements/:id
6. GET /invitations/:id

User switches back to Group A:
7. GET /groups/:id/full (redundant!)
8. GET /settlements/:id (redundant!)
9. GET /invitations/:id (redundant!)

Total: 9 API calls
```

**With React Query**:
```
User switches to Group A:
1. GET /groups/:id/full
2. GET /settlements/:id
3. GET /invitations/:id

User switches to Group B:
4. GET /groups/:id/full
5. GET /settlements/:id
6. GET /invitations/:id

User switches back to Group A:
(Cached - no API calls!)

Total: 6 API calls
Reduction: 33% fewer calls
```

**With Multiple Components**:
```
Current: 3 components request same group = 3 API calls
React Query: 3 components request same group = 1 API call
Reduction: 66% fewer calls
```

**Overall Expected**: 40-60% reduction in API calls

---

## Migration Checklist

### Phase 2.9A - Preparation:
- [ ] Install React Query DevTools
- [ ] Document baseline API call count
- [ ] Test current functionality works

### Phase 2.9B - Groups:
- [ ] Replace `useUserGroups` with `useGroupsQuery`
- [ ] Replace `useGroup` with `useGroupQuery`
- [ ] Update group creation to use mutation
- [ ] Update group deletion to use mutation
- [ ] Remove all manual `reloadGroups()` calls

### Phase 2.9C - Expenses:
- [ ] Replace expense create with `useCreateExpenseMutation`
- [ ] Replace expense update with `useUpdateExpenseMutation`
- [ ] Replace expense delete with `useDeleteExpenseMutation`
- [ ] Remove all manual expense reload calls

### Phase 2.9D - Settlements:
- [ ] Replace settlement create with `useCreateSettlementMutation`
- [ ] Update settlement success handler
- [ ] Remove manual settlement reload calls

### Phase 2.9E - Testing:
- [ ] Verify all CRUD operations work
- [ ] Confirm cache invalidation works
- [ ] Measure API call reduction
- [ ] Check no regression in functionality

---

## Risk Mitigation

### Potential Issues:

1. **Cache invalidation timing**
   - Risk: UI shows stale data after mutation
   - Solution: Mutations configured to invalidate + refetch

2. **Optimistic updates conflict**
   - Risk: Optimistic state overrides fresh cache data
   - Solution: Clear optimistic state before mutation

3. **Loading states**
   - Risk: `isLoading` vs `loading` naming differences
   - Solution: Consistent renaming in migration

4. **Error handling**
   - Risk: Different error format from React Query
   - Solution: Wrap mutations in try-catch, same as before

---

## Success Criteria

✅ **Phase 2.9 Complete When**:
- [ ] 50%+ reduction in API calls (measured)
- [ ] All features work identically to before
- [ ] No console errors
- [ ] Cache hit rate > 70%
- [ ] Optimistic updates still instant
- [ ] Tests pass

---

**Estimated Time**: 3-4 hours  
**Complexity**: Medium (mostly find-replace with testing)  
**Impact**: High (major performance improvement)
