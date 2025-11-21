# Phase 4: Redis Caching Integration

## Current State ✅

### Infrastructure Ready
- ✅ Redis client configured (`cache_operations.py`)
- ✅ Connection pooling enabled (max 50 connections)
- ✅ Cache key patterns defined
- ✅ TTL configurations set
- ✅ JSON serialization/deserialization

### Currently Cached
1. **User Groups** (`get_user_groups`)
   - Cache key: `groupplanner:user_groups:{user_id}`
   - TTL: 3600s (1 hour)
   - Invalidation: On group create/delete/update

2. **Group Invalidation** (Partial)
   - On place add/update/delete
   - On poll add/update/delete
   - On place details update

## Phase 4 Tasks

### 1. Add Caching to Missing Endpoints (2 hours)

#### High-Priority Endpoints
- [ ] `GET /groups/{group_id}` - Single group details
- [ ] `GET /groups/{group_id}/places` - Group places list
- [ ] `GET /groups/{group_id}/polls` - Group polls list
- [ ] `GET /groups/{group_id}/members` - Group members list
- [ ] `GET /user/invitations` - User invitations list

#### Cache Strategy
- **Read-through cache**: Check cache first, fetch from DB on miss
- **Write-through cache**: Update cache immediately after DB write
- **Invalidation**: Selective invalidation on related updates

### 2. Smart Cache Invalidation (1 hour)

#### Granular Invalidation
- **Group update**: Only invalidate group cache, not all related caches
- **Place add**: Invalidate group cache + places cache
- **Poll add**: Invalidate group cache + polls cache
- **Member add**: Invalidate group cache + members cache + user_groups cache

#### Optimization
- Use Redis pipelines for batch invalidation
- Track cache dependencies
- Implement cache versioning for complex updates

### 3. Cache Warming (30 minutes)

#### On User Login
- Pre-load user's groups list
- Pre-load selected group details
- Background task for frequently accessed data

### 4. Monitoring & Metrics (30 minutes)

#### Cache Hit Rate Tracking
- Log cache hits/misses
- Track average response times
- Monitor Redis memory usage
- Alert on cache failures

## Implementation

### Step 1: Add Group Details Caching
```python
# In routes.py - get_group()
cache_ops = GroupPlannerCacheOperations()
cached_group = cache_ops.get_cached_group(group_id)
if cached_group:
    return jsonify({'success': True, 'data': cached_group}), 200

# Fetch from DB
group_data = firebase_ops.get_group(group_id)

# Cache for future requests
cache_ops.cache_group(group_id, group_data)
```

### Step 2: Add Places Caching
```python
# In routes.py - get_group_places()
cache_key = f"groupplanner:group_places:{group_id}"
cached_places = cache_ops.get(cache_key)
if cached_places:
    return jsonify({'success': True, 'data': cached_places}), 200

# Fetch from DB
places = firebase_ops.get_group_places(group_id)

# Cache with TTL
cache_ops.set(cache_key, places, ttl=1800)  # 30 minutes
```

### Step 3: Smart Invalidation
```python
# When place is added
cache_ops.invalidate_multiple([
    f"groupplanner:group:{group_id}",
    f"groupplanner:group_places:{group_id}",
    f"groupplanner:user_groups:{user_id}"
])
```

## Expected Performance Improvements

### Before Caching
- User groups list: ~200-300ms (Firestore query)
- Single group: ~150-200ms
- Places list: ~100-150ms
- **Total first load**: ~500-700ms

### After Caching
- User groups list: ~5-10ms (Redis lookup)
- Single group: ~3-5ms
- Places list: ~2-5ms
- **Total first load**: ~15-25ms

### Improvement: **95-97% reduction in response time** 🚀

## Redis Memory Usage Estimate

- Average group: ~2KB
- Average places list: ~5KB
- Average user_groups: ~1KB
- **100 active users**: ~800KB
- **1000 active users**: ~8MB

With 1-hour TTL, Redis will auto-evict old data, keeping memory usage low.

## Testing Plan

1. **Functional Testing**
   - Verify cache hits after first request
   - Verify cache invalidation on updates
   - Verify graceful degradation if Redis is down

2. **Performance Testing**
   - Measure response times before/after
   - Load test with 100 concurrent users
   - Monitor Redis CPU/memory usage

3. **Integration Testing**
   - Test with Firestore listeners
   - Test with optimistic updates
   - Test cache consistency

## Rollout Strategy

1. **Phase 4a**: Add caching to read endpoints (GET routes)
2. **Phase 4b**: Add smart invalidation to write endpoints
3. **Phase 4c**: Add cache warming and monitoring
4. **Phase 4d**: Performance testing and optimization

## Success Criteria

- ✅ All critical GET endpoints have caching
- ✅ Cache hit rate > 80% for user_groups
- ✅ Average response time < 50ms for cached requests
- ✅ Zero cache-related bugs in production
- ✅ Graceful degradation when Redis is unavailable
