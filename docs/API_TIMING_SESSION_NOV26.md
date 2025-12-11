# API Timing Analysis - November 26, 2025 Session

## Executive Summary

**Test Duration:** ~10 minutes  
**Total API Calls:** 70+ requests  
**Cache Hit Rate:** 55% average  
**Slowest Operation:** POST /expenses (3961ms)  
**Fastest Cached:** GET /user/groups (264ms)

---

## Phase 1-11 Verification: ✅ ALL WORKING

| Phase | Feature | Evidence |
|-------|---------|----------|
| 1 | Models & Repos | CRUD operations succeed |
| 2 | Service Layer | Balance calculations correct |
| 3 | Security (RBAC) | Membership validation |
| 4 | Real-Time | Cache invalidation working |
| 5 | Redis Caching | `[CACHE][+]` hits visible |
| 6 | Denormalized | `expense_group_balances` used |
| 7 | API Routes | All endpoints responding |
| 8 | Bootstrap | `/groups/{id}/full` working |
| 9 | Testing | 150+ tests passing |
| 10 | Thread Safety | 36 tests passing |
| 11 | Browser Cache | 11 tests passing |

---

## Detailed API Timing

### READ Operations (GET)

| Endpoint | Cold (ms) | Warm (ms) | Firestore Reads | Cache |
|----------|-----------|-----------|-----------------|-------|
| `/user/groups` | 1847 | 264-370 | 1 | ✅ 60s TTL |
| `/invitations/user` | 2000 | 508-680 | 1 | ❌ None |
| `/groups/{id}/full` | 2227 | 372-552 | 6 | ✅ 30s TTL |
| `/settlements/group/{id}` | 1203 | 918 | 2 | ❌ None |
| `/invitations/group/{id}` | 1328 | 567-726 | 2 | ❌ None |

### WRITE Operations (POST/PUT/DELETE)

| Endpoint | Method | Time (ms) | Reads | Writes |
|----------|--------|-----------|-------|--------|
| `/groups` | POST | 1317 | 2 | 3 |
| `/invitations` | POST | 1934 | 6 | 1 |
| `/invitations/{id}/accept` | POST | 2310 | 6 | 3 |
| `/expenses` | POST | **3961** | 7 | 7 |
| `/expenses/{id}` | PUT | **3196** | 7 | 3 |
| `/expenses/{id}` | DELETE | **3433** | 7 | 3 |
| `/settlements` | POST | 2426 | 6 | 0 |
| `/groups/{id}/members/{uid}` | DELETE | 1460 | 3 | 2 |

---

## Cache Performance

### Hit/Miss Breakdown

```
expense:user_groups:{uid}
  Hits: 8 | Misses: 3 | Rate: 73% | TTL: 60s

expense:membership:{gid}:{uid}  
  Hits: 12 | Misses: 6 | Rate: 67% | TTL: 60s

expense:group_summary:{gid}
  Hits: 3 | Misses: 7 | Rate: 30% | TTL: 30s  ← Problem!

expense:group:{gid}
  Hits: 4 | Misses: 4 | Rate: 50% | TTL: 60s
```

### Cache Issues Identified

1. **`group_summary` TTL too short (30s)** - Causes 70% misses
2. **No cache for invitations** - Every request hits Firestore
3. **No cache for settlements** - Every request hits Firestore

---

## Firestore Operations Summary

### By Operation Type

| Type | Count | Unit Cost |
|------|-------|-----------|
| Reads (R) | 80+ | $0.036/100k |
| Writes (W) | 25+ | $0.108/100k |
| Queries (Q) | 20+ | $0.036/100k |

### Most Expensive Operations

| Operation | Reads | Writes | Total Ops |
|-----------|-------|--------|-----------|
| POST `/expenses` | 7 | 7 | **14** |
| PUT `/expenses/{id}` | 7 | 3 | 10 |
| DELETE `/expenses/{id}` | 7 | 3 | 10 |
| POST `/invitations/{id}/accept` | 6 | 3 | 9 |

---

## Redundant Frontend Calls

### Detected Patterns

```
Pattern 1: GET /user/groups called after EVERY mutation
  - After POST /groups
  - After POST /expenses  
  - After PUT /expenses
  - After DELETE /expenses
  - After POST /settlements
  → 15+ unnecessary calls

Pattern 2: Duplicate parallel requests
  - GET /groups/{id}/full called twice simultaneously
  - GET /invitations/user called twice
  → 4+ unnecessary calls

Pattern 3: OPTIONS preflight on every request
  - 40+ preflight requests
  → Expected (CORS), not fixable
```

### Impact

| Issue | Wasted Calls | Wasted Time | Fix |
|-------|--------------|-------------|-----|
| Refetch after mutation | 15+ | ~5000ms | Use optimistic updates |
| Duplicate parallel | 4+ | ~1500ms | Request deduplication |
| Total waste | ~20 | ~6500ms | **Frontend fixes** |

---

## Optimization Roadmap

### Immediate (Phase 12)

| Fix | Impact | Effort |
|-----|--------|--------|
| Batch Firestore writes | -50% expense time | Medium |
| Add invitations cache | -40% latency | Low |
| Add settlements cache | -40% latency | Low |
| Increase `group_summary` TTL | +40% hit rate | Low |

### Phase 14 (Ultra-Unified API)

Combine into single endpoint:
```
GET /api/expense/groups/{id}/dashboard
Returns: {
  group: {...},
  balances: [...],
  expenses: [...],
  settlements: [...],
  invitations: [...]
}
```

Current: 4 calls × 500ms = 2000ms  
After: 1 call × 800ms = 800ms  
**Savings: 60%**

### Phase 15 (Sub-Second Latency)

| Target | Current | Goal | Method |
|--------|---------|------|--------|
| POST /expenses | 3961ms | <1500ms | Batch writes |
| GET /groups/{id}/full | 2227ms | <800ms | Cache warming |
| GET /user/groups (cold) | 1847ms | <500ms | Preload on login |

---

## Test Scenarios Covered

| Scenario | Status | Notes |
|----------|--------|-------|
| Create group | ✅ | 1317ms |
| Invite member | ✅ | 1934ms |
| Accept invitation | ✅ | 2310ms |
| Add expense | ✅ | 3961ms |
| Edit expense | ✅ | 3196ms |
| Delete expense | ✅ | 3433ms |
| Record settlement | ✅ | 2426ms |
| Remove member | ✅ | 1460ms |
| Delete group | ✅ | ~1500ms |
| Cache hit | ✅ | 264-550ms |
| Cache miss | ✅ | 1200-2200ms |

---

## Conclusion

### What's Working Well
- ✅ All 11 phases functional
- ✅ Redis cache reducing latency by 70%+ on hits
- ✅ Denormalized balances working correctly
- ✅ Security/RBAC properly enforced

### What Needs Improvement
- ❌ Expense operations too slow (3-4s)
- ❌ Missing cache for invitations/settlements
- ❌ `group_summary` TTL too short
- ❌ Frontend making redundant calls

### Ready for Phase 12?
**YES** - Core functionality is solid. Phase 12 (Edit History) can proceed.

---

*Generated: November 26, 2025*
*Session: Phase 11 Completion*
