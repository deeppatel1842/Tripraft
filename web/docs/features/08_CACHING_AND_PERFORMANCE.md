# Feature: Caching, Rate Limiting, and Performance

## Overview

TripRaft implements a multi-layer caching strategy (browser IndexedDB + Redis), per-operation rate limiting, and several performance optimizations including ETag-based HTTP caching, code splitting, and virtual scrolling.

---

## Caching Layers

### Layer 1: Frontend (TanStack Query + IndexedDB)

```
React Component
     │
     │  useQuery(['groups', userId])
     │
     ▼
┌──────────────────────────────────┐
│  TanStack Query In-Memory Cache  │
│                                  │
│  staleTime: 5 minutes            │  ◄── Data considered fresh for 5 min
│  gcTime: 30 minutes              │  ◄── Keep in memory for 30 min
│                                  │
│  If fresh → return immediately   │
│  If stale → return + refetch bg  │
│  If missing → fetch from server  │
└────────────┬─────────────────────┘
             │ persist / restore
             ▼
┌──────────────────────────────────┐
│  IndexedDB Persister             │
│                                  │
│  maxAge: 60 minutes              │  ◄── Survives page refresh
│  Database: "tripraft-query"      │
│                                  │
│  Excluded keys:                  │
│  - auth, user-token              │
│  - realtime, websocket           │
│  - Any mutation keys             │
│                                  │
│  Benefit: ~70% fewer API calls   │
│  after initial load              │
└──────────────────────────────────┘
```

**Invalidation Triggers:**
1. Socket.IO event (server push) → `queryClient.invalidateQueries(key)`
2. Mutation success → automatic invalidation of related keys
3. Window focus → refetch stale queries
4. Manual user action (pull-to-refresh pattern)

### Layer 2: Backend (Redis Response Cache)

```
HTTP Request
     │
     ▼
┌──────────────────────────────────┐
│  @cache_response Decorator       │
│                                  │
│  1. Generate cache key:          │
│     {prefix}:{user_id}:          │
│     {route_params}:{query_hash}  │
│                                  │
│  2. Check Redis for key          │
│     If hit + ETag match:         │
│       → 304 Not Modified         │
│     If hit + no ETag:            │
│       → Return cached response   │
│     If miss:                     │
│       → Execute handler          │
│       → Store in Redis with TTL  │
│       → Return response + ETag   │
└──────────────────────────────────┘
```

**TTL Configuration (25 distinct values in config.py):**

| Endpoint Category | TTL | Rationale |
|------------------|-----|-----------|
| Autocomplete | 3600s (1h) | Rarely changes |
| Place search results | 1800s (30m) | Reference data is stable |
| User profile | 3600s (1h) | Infrequent updates |
| Group list | 300s (5m) | Changes on create/join/leave |
| Group detail | 300s (5m) | Moderate change frequency |
| Chat messages | 60s (1m) | Frequently changing |
| Balances | 120s (2m) | Changes on expense/settlement |
| Place detail | 3600s (1h) | Reference data |
| DB stats | 3600s (1h) | Rarely changes |

**Invalidation Patterns (config-driven):**

```
On expense create:
  → invalidate: expense:*, balance:*, expense_groups:*

On place add:
  → invalidate: places:group_id:*, group:id:*

On group update:
  → invalidate: group:id:*, groups:user_id:*

On settlement:
  → invalidate: balance:*, settlement:*, simplified_debts:*

On member join/leave:
  → invalidate: group:id:*, members:*, groups:*
```

**Graceful fallback:** If Redis is unavailable, all requests bypass cache and hit the database directly. No errors, just slower responses.

---

## Rate Limiting

### Configuration

```
Flask-Limiter with Redis backend
Per-user (authenticated) + per-IP (unauthenticated)
17 operation categories
```

| Operation | Limit | Applies To |
|-----------|-------|-----------|
| `default` | 100/minute | All endpoints (fallback) |
| `auth_login` | 10/minute per IP | Login attempts |
| `auth_signup` | 5/minute per IP | Registration |
| `password_change` | 3/minute | Password changes |
| `email_verify` | 3/minute | Verification resends |
| `create` | 30/minute | POST endpoints (create resources) |
| `read` | 120/minute | GET endpoints |
| `update` | 30/minute | PUT/PATCH endpoints |
| `delete` | 15/minute | DELETE endpoints |
| `search` | 60/minute | Search/autocomplete |
| `upload` | 10/minute | File uploads |
| `export` | 5/minute | PDF/iCal exports |
| `invite` | 20/minute | Invitation sends |
| `ai_mention` | 10/minute | @scout/@crew triggers |
| `settlement` | 15/minute | Settlement recording |
| `bulk` | 5/minute | Bulk operations (admin) |
| `health` | 30/minute | Health check endpoints |

### Implementation

```python
from app.core.rate_limiter import limit_api

@chat_bp.route('/groups/<group_id>/messages', methods=['POST'])
@require_auth
@limit_api('create')  # 30/minute per user
def send_message(group_id):
    ...
```

Rate limit exceeded returns 429 with `Retry-After` header.

---

## Performance Optimizations

### Frontend

| Optimization | Implementation | Impact |
|-------------|---------------|--------|
| Code splitting | React.lazy() + Suspense on all routes | Initial bundle ~60% smaller |
| Virtual scrolling | TanStack React Virtual for long lists | Renders only visible rows |
| Debounced search | 300ms delay before API call | Reduces search API calls ~80% |
| Optimistic mutations | TanStack Query mutate with rollback | UI feels instant |
| Infinite scroll | Cursor-based pagination for chat/expenses | Load 20 items at a time |
| IndexedDB persistence | Query cache survives page refresh | ~70% fewer API calls |
| Lazy Leaflet loading | CDN injection on demand (not in bundle) | Saves ~200KB initial load |
| Image placeholders | Skeleton loaders for cards/grids | Perceived performance |

### Backend

| Optimization | Implementation | Impact |
|-------------|---------------|--------|
| FTS5 index | Full-text search on travel DB | Sub-millisecond place search |
| Composite indexes | On frequently queried column pairs | 5-10x query speedup |
| Connection pooling | SQLAlchemy with pool_size=10 | Reused connections |
| ETag caching | Hash-based HTTP caching | 304 responses save bandwidth |
| Redis decorators | Route-level response caching | Skip DB entirely for cached data |
| Materialized views | Pre-computed aggregations (PostgreSQL) | Complex queries in milliseconds |
| Date partitioning | Partition large tables by month (PostgreSQL) | Faster range queries |
| Gevent workers | Async I/O for concurrent WebSocket+HTTP | Handle 1000+ concurrent connections |
| Worker recycling | Gunicorn recycles workers every 1000 requests | Prevent memory leaks |
| Brotli compression | Flask-Compress with Brotli algorithm | ~30% smaller responses than gzip |

### Database

| Optimization | Implementation |
|-------------|---------------|
| UUIDv7 PKs | Time-ordered inserts (no random I/O) |
| Composite indexes | group_id + created_at, user_id + group_id |
| Soft deletes | is_deleted filter (indexed) avoids full scans |
| Read-only travel DB | Separate file, no write lock contention |
| Thread-safe connections | Each request opens/closes own travel DB connection |
| JSON/JSONB columns | Flexible metadata without schema changes |

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/infrastructure/cache/redis.py` | RedisClient, @cache_response, invalidate_cache |
| `app/core/rate_limiter.py` | init_rate_limiter, @limit_api decorator |
| `app/core/config.py` | 25 cache TTL values, 17 rate limit values |
| `app/core/idempotency.py` | Idempotency-Key header support |
| `app/core/resilience.py` | Circuit breaker + retry patterns |

### Frontend

| File | Purpose |
|------|---------|
| `src/lib/queryClientPersist.js` | QueryClient config: staleTime, gcTime, persister |
| `src/lib/indexedDBPersister.js` | IndexedDB adapter for TanStack Query |
| `src/utils/apiClient.js` | Retry logic with exponential backoff (5xx on GET) |
