# API Timing Analysis - December 3, 2025

## Summary from Captured Logs

Based on the `web/backend/logs/captured_logs.txt` file analysis.

---

## 🚨 CRITICAL ISSUE: Too Many API Calls Per Session

### Current State (Before Fix)
| Action | API Calls | Expected | Issue |
|--------|-----------|----------|-------|
| Page Load | 6-8 | 1-2 | Duplicate requests from desktop + mobile views |
| Create Expense | 3-5 | 1 | mega-bootstrap refetched multiple times |
| Update Expense | 3-4 | 1 | Cache invalidation triggers refetch |
| Delete Expense | 2-3 | 1 | Cache invalidation triggers refetch |
| Create Settlement | 4-5 | 1 | Multiple endpoints called |

**Total per session: 30-50+ API calls** (Target: ≤10)

---

## API Response Times by Endpoint

| Endpoint | Method | Avg Time (ms) | Max Time (ms) | Firestore Ops | Cache | Notes |
|----------|--------|---------------|---------------|---------------|-------|-------|
| `/api/expense/mega-bootstrap` | GET | 238-1634 | 2488 | 6-12R | HIT: 238ms, MISS: 1500ms+ | **PRIMARY BOTTLENECK** |
| `/api/expense/user/groups` | GET | 200-400 | 940 | 1-3R | Usually HIT | User's group list |
| `/api/expense/groups/{id}/full` | GET | 225-955 | 1853 | 1-8R | HIT: 225ms, MISS: 900ms+ | Full group data |
| `/api/expense/expenses` | POST | 1985-2088 | 2088 | 4R 3W | N/A | Create expense |
| `/api/expense/expenses/{id}` | PUT | 1715 | 1715 | 5R 3W | N/A | Update expense |
| `/api/expense/expenses/{id}` | DELETE | 1497 | 1497 | 3R 1W | N/A | Delete expense |
| `/api/expense/expenses/{id}/history` | GET | 461-585 | 585 | 3-4R | N/A | Edit history |
| `/api/expense/groups` | POST | 725 | 725 | 1R 3W | N/A | Create group |
| `/api/expense/invitations` | POST | 747 | 747 | 3R 1W | N/A | Send invitation |
| `/api/expense/invitations/{id}/accept` | POST | 1185 | 1185 | 5R 3W | N/A | Accept invitation |
| `/api/expense/settlements` | POST | 1107 | 1107 | 5R 0W | N/A | Create settlement |
| `/api/expense/settlements/group/{id}` | GET | 862 | 862 | 6R | N/A | Get settlements |
| OPTIONS (CORS) | OPTIONS | 0-2 | 2 | 0 | N/A | Fast preflight |

---

## 🔥 Firestore Operations Per Action

| Action | Reads | Writes | Total Ops | Cost Impact |
|--------|-------|--------|-----------|-------------|
| **mega-bootstrap (MISS)** | 8-12 | 0 | 8-12 | HIGH |
| **mega-bootstrap (HIT)** | 0 | 0 | 0 | LOW |
| Create Expense | 4 | 3 | 7 | MEDIUM |
| Update Expense | 5 | 3 | 8 | MEDIUM |
| Delete Expense | 3 | 1 | 4 | LOW |
| Create Group | 1 | 3 | 4 | LOW |
| Accept Invitation | 5 | 3 | 8 | MEDIUM |
| Create Settlement | 5 | 0 | 5 | MEDIUM |

### Firestore Read Breakdown (mega-bootstrap MISS)
```
expense_group_summaries/user_id     - 1 read
users/user_id                       - 1 read  
expense_user_expenses/user_id       - 1 read
expense_groups/group_id             - 1 read
expense_group_balances/group_id     - 2-3 reads (for each group)
expense_expenses (query)            - 1 query
expense_history (query)             - 1-2 queries
expense_invitations (query)         - 1 query
expense_settlements (query)         - 1 query
─────────────────────────────────────────────
TOTAL: 10-14 Firestore operations
```

---

## 📊 Cache Performance Analysis

### Cache Hit/Miss Rate by Endpoint

| Endpoint | HIT Rate | MISS Rate | Issue |
|----------|----------|-----------|-------|
| `user_groups` | 70% | 30% | Good - TTL=300s |
| `mega_bootstrap` | 40% | 60% | **TOO LOW** - invalidated too often |
| `group_summary` | 60% | 40% | Good |
| `group_balances` | 50% | 50% | Invalidated on every mutation |
| `membership` | 80% | 20% | Good - TTL=60s |

### Cache Invalidation Pattern (PROBLEM)
```
POST /expenses  →  Invalidates:
  - expense:group_balances:{group_id}
  - expense:group_summary:{group_id}
  - expense:mega_bootstrap:{user_id}
  - expense:mega_bootstrap:{user_id}:{group_id}
  - expense:mega_bootstrap:{other_user_id}  (for each group member!)
  
Result: 5-8 cache keys invalidated per expense create
```

---

## 🔧 Phase 17 Optimization Results

### What Was Fixed
1. **Mutation cooldown timing** - `startMutationCooldown()` now called BEFORE mutation
2. **Firestore listeners** - Now update cache directly instead of invalidating
3. **Removed cascade invalidation** - Firestore no longer triggers mega-bootstrap refetch

### Expected Improvement
| Metric | Before | After (Expected) |
|--------|--------|------------------|
| API calls per session | 30-50+ | 5-10 |
| mega-bootstrap calls per expense | 3-5 | 1 |
| Cache hit rate | 40% | 80%+ |
| UI update latency | 1500-2500ms | <50ms |

---

## 🎯 Recommendations to Reduce API Calls

### 1. Remove Duplicate Endpoint Calls
**Problem**: Both `/groups/{id}/full` and `/mega-bootstrap` are called simultaneously.

**Fix**: Use ONLY `mega-bootstrap` - it includes all data in one call.

```javascript
// BAD - 2 API calls
const group = await getGroupFull(groupId);
const bootstrap = await getMegaBootstrap(groupId);

// GOOD - 1 API call  
const bootstrap = await getMegaBootstrap(groupId);
// Group data is in: bootstrap.data.active_group
```

### 2. Reduce Cache Invalidation Scope
**Problem**: One expense create invalidates 5-8 cache keys.

**Fix**: Only invalidate the minimum necessary keys.

```python
# BAD - invalidates everyone's bootstrap
cache.invalidate_pattern(f"expense:mega_bootstrap:*:{group_id}")

# GOOD - only invalidate the specific user's cache
cache.invalidate(f"expense:mega_bootstrap:{user_id}:{group_id}")
```

### 3. Use balance_deltas Instead of Full Refetch
**Status**: ✅ Implemented in Phase 17

Backend returns `balance_deltas` in mutation responses. Frontend applies deltas to cache without API call.

### 4. Increase Cache TTL for Stable Data
| Cache Key | Current TTL | Recommended TTL |
|-----------|-------------|-----------------|
| `user_groups` | 300s | 600s |
| `mega_bootstrap` | 60s | 120s |
| `group_summary` | 300s | 600s |
| `membership` | 60s | 120s |

---

## 📈 Performance Goals

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| API calls per session | 30-50 | ≤10 | 🔄 In Progress |
| mega-bootstrap time (HIT) | 238ms | <200ms | ✅ Achieved |
| mega-bootstrap time (MISS) | 1500-2500ms | <1000ms | ❌ Needs Work |
| Expense create time | 1985ms | <1500ms | ❌ Needs Work |
| Cache hit rate | 40% | 80%+ | 🔄 In Progress |
| UI perceived latency | 1500ms | <50ms | 🔄 In Progress |

---

## Raw Timing Distribution

```
0-100ms:    ~35% (CORS preflight, cache hits)
100-500ms:  ~30% (cached GET requests)
500-1000ms: ~20% (cache miss, simple queries)
1000ms+:    ~15% (mutations, complex operations)
```

---

## Action Items

### Immediate (Phase 17 Fixes Applied)
- [x] Fix mutation cooldown timing
- [x] Firestore listeners update cache directly
- [x] Remove `debouncedInvalidateMegaBootstrap` cascade

### Next Phase
- [ ] Remove duplicate `/groups/{id}/full` calls
- [ ] Reduce cache invalidation scope
- [ ] Increase cache TTL values
- [ ] Optimize Firestore read batching in mega-bootstrap
