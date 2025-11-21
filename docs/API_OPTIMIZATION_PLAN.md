# API Call Optimization Plan - Phase 6

## Problem Analysis

### Current State (❌ INEFFICIENT)
When user logs in and loads expense manager:
```
GET /api/expense/groups → 50 Firestore reads ⚠️ HIGH
  - 4 reads: Fetch group memberships
  - 4 reads: Fetch group documents  
  - 42 reads: Fetch member details for each group (1 read per member × 42 members across 4 groups)
```

**Total**: 50 Firestore reads just to display group list!

### Root Cause
The `get_user_groups()` function:
1. Fetches group memberships (4 reads)
2. Batch fetches groups (4 reads) ✅ Already optimized
3. **For each group**, fetches ALL member details (42 reads) ❌ INEFFICIENT

The problem is we're fetching full user profiles for every member in every group just to show group names.

---

## Solution: Progressive Loading Strategy

### Phase 6.1: Optimize Initial Load (1-2 calls)
**Goal**: Load only essential data on initial page load

#### New Endpoint: `GET /api/expense/groups?mode=summary`
Returns minimal group info without member details:
```json
{
  "groups": [
    {
      "id": "...",
      "name": "Trip to Paris",
      "currency": "USD",
      "member_count": 5,
      "created_at": "...",
      "owner_id": "..."
    }
  ],
  "total": 4
}
```

**Firestore Reads**: 8 total (4 memberships + 4 groups) ✅ 84% reduction (50→8)

---

### Phase 6.2: Lazy Load Group Details (1 call per group selection)
**Goal**: Fetch full details only when user selects a group

#### Enhanced Endpoint: `GET /api/expense/groups/{group_id}?include=members,balances,expenses,invitations`
Returns complete group data in single call:
```json
{
  "group": {
    "id": "...",
    "name": "Trip to Paris",
    "members": [
      {"user_id": "...", "display_name": "John", "email": "john@example.com"}
    ],
    "balances": [...],
    "expenses": [...],
    "invitations": [...]
  }
}
```

**Firestore Reads**: 
- 1 read: Group document
- 5 reads: Member user profiles (batch fetch)
- 1 read: Balances document
- 10 reads: Expenses (if not cached)
- 1 read: Invitations

**Total**: ~18 reads (but only when group is selected)

---

### Phase 6.3: Smart Caching (0 additional calls on subsequent visits)
**Goal**: Cache everything aggressively

#### Redis Cache Strategy:
```python
# Cache group list for 5 minutes
cache.set(f"user:{user_id}:groups:summary", groups, ttl=300)

# Cache full group data for 10 minutes  
cache.set(f"group:{group_id}:full", full_data, ttl=600)

# Cache member details for 30 minutes
cache.set(f"group:{group_id}:members", members, ttl=1800)
```

**Result**: Second visit = 0 Firestore reads if cache is warm ✅

---

## Implementation Plan

### Step 1: Create Summary Mode (30 mins)
- [ ] Add `mode=summary` parameter to `GET /api/expense/groups`
- [ ] Modify `get_user_groups()` to skip member fetching in summary mode
- [ ] Update frontend to use summary mode on initial load
- [ ] Test: Should see 8 reads instead of 50

### Step 2: Create Full Group Endpoint (45 mins)
- [ ] Create `GET /api/expense/groups/{group_id}/full` endpoint
- [ ] Batch fetch: group + members + balances + expenses + invitations
- [ ] Return everything in single response
- [ ] Update frontend to call this when group is selected
- [ ] Test: Should see ~18 reads per group selection

### Step 3: Enhanced Caching (30 mins)
- [ ] Add summary cache with 5-min TTL
- [ ] Add full group cache with 10-min TTL
- [ ] Invalidate caches on mutations (create/update/delete)
- [ ] Test: Second page load should be instant

### Step 4: Frontend Optimization (20 mins)
- [ ] Update `useExpense` hook to use new endpoints
- [ ] Add loading states for progressive loading
- [ ] Cache selected group data in React state
- [ ] Test: Verify smooth UX with loading indicators

---

## Expected Performance Gains

| Scenario | Current | After Phase 6 | Improvement |
|----------|---------|---------------|-------------|
| **Initial Load** | 50 reads | 8 reads | 84% ↓ |
| **Select Group** | 0 reads | 18 reads | N/A |
| **Switch Group** | 0 reads | 18 reads (or 0 if cached) | N/A |
| **Second Visit** | 50 reads | 0 reads (cached) | 100% ↓ |

**Total**: From 50 reads per page load → 8 reads + 18 reads per group = **26 reads max** (48% reduction)

With caching: **8 reads on first load, 0 reads on subsequent loads** 🚀

---

## Success Criteria
- ✅ Initial page load: ≤ 10 Firestore reads
- ✅ Group selection: ≤ 20 Firestore reads
- ✅ Subsequent visits: 0 reads (cache hit)
- ✅ Total load time: < 500ms (from current 1-2s)
- ✅ No degradation in UX (smooth loading states)

---

## Risk Mitigation
- **Risk**: Users won't see member names in group list
  - **Mitigation**: Show member count instead, fetch names on hover/selection
  
- **Risk**: Stale data in cache
  - **Mitigation**: Short TTL (5-10 mins) + invalidation on mutations

- **Risk**: Large payload for groups with many expenses
  - **Mitigation**: Paginate expenses (return last 50) or use `include` parameter

---

## Timeline
- **Step 1**: 30 mins
- **Step 2**: 45 mins  
- **Step 3**: 30 mins
- **Step 4**: 20 mins

**Total**: ~2 hours to complete Phase 6

---

## Next Steps
1. Review this plan
2. Start with Step 1 (summary mode)
3. Test after each step
4. Monitor Firestore usage in production
