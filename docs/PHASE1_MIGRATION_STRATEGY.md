# Phase 1 Migration Strategy

## Current Problem
Routes.py stores places, polls, checklist, etc. as ARRAYS inside the group document, then replicates to every member:
```python
# WRONG: Stores as array in group doc
group_data['places'] = [...]
group_data['polls'] = [...]

# Then tries to replicate to ALL members
for member_id in members:
    member_doc.update({'places': places, 'polls': polls})  # N writes!
```

## Solution Approach

Since firebase_operations.py was designed for separate collections but routes.py uses embedded arrays, we have two options:

### Option A: Keep Shared Group Document with Arrays (SIMPLER - RECOMMENDED FOR PHASE 1)
- Store places/polls/checklist as arrays in the shared `travel_groups/{groupId}` document
- Remove replication to member documents (key fix!)
- Everyone reads from the same shared document
- Single write, N reads (efficient with caching)

**Pros:**
- Minimal code changes
- Maintains current data structure
- Works immediately

**Cons:**
- Large groups with many places/polls = large documents
- Firestore 1MB document limit could be hit
- Updating a single place = update entire array

### Option B: Separate Collections (BETTER LONG-TERM, MORE COMPLEX)
- Create separate collections: `travel_places`, `travel_polls`, `travel_checklist`
- Each item is its own document with `group_id` field
- Query by `where('group_id', '==', groupId)`

**Pros:**
- Scalable to unlimited items
- Fine-grained updates
- Better for real-time listeners
- Follows firebase_operations.py design

**Cons:**
- More code changes
- More complex queries
- More reads per request (without caching)

## Recommendation for Phase 1

**Use Option A** for immediate fix:
1. Keep places/polls/checklist as arrays in shared `travel_groups` document
2. Remove all member replication logic  
3. Add access checks using `firebase_ops.is_group_member()`
4. This fixes the core problem (N writes per update) with minimal changes

**Plan Option B for Phase 2** (after real-time and optimistic updates working):
- Migration script to move arrays to separate collections
- Update operations to work with separate docs
- Better for production scale

## Implementation

### Step 1: Replace all nested access patterns
```python
# OLD:
group_doc = db.collection('users').document(g.user_id).collection('groups').document(group_id).get()

# NEW:
from firebase_admin import firestore
db = firestore.client()
group_ref = db.collection('travel_groups').document(group_id)
group_doc = group_ref.get()

# Verify access
from .firebase_operations import GroupPlannerFirebaseOperations
firebase_ops = GroupPlannerFirebaseOperations()
if not firebase_ops.is_group_member(group_id, g.user_id):
    return jsonify({'success': False, 'error': 'Access denied'}), 403
```

### Step 2: Remove member replication
```python
# OLD:
for member_id in members:
    if member_id != g.user_id:
        member_group_ref = db.collection('users').document(member_id).collection('groups').document(group_id)
        member_group_ref.update({'places': places})  # DELETE THIS

# NEW:
# Just update the shared document once - all members read from it
group_ref.update({'places': places})  # Single write!
```

### Step 3: Invalidate cache after mutations
```python
# After any update
try:
    from .cache_operations import GroupPlannerCacheOperations
    cache_ops = GroupPlannerCacheOperations()
    cache_ops.invalidate_group(group_id)
    # Don't need to invalidate per-member caches anymore!
except Exception as e:
    logger.warning("Failed to invalidate cache: %s", e)
```

This approach gives us:
- ✅ Single source of truth (shared document)
- ✅ 1 write instead of N writes
- ✅ All members see same data instantly
- ✅ Real-time listeners will work
- ✅ 90% less code to change
- ✅ Can do Option B later without breaking anything
