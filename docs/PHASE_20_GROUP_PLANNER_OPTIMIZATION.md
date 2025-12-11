# Phase 20: Group Planner Extreme Optimization

**Target:** Complete session in **10 total Firestore operations**  
**Session:** Login → Create Group → Set Destination → Get Places → Invite Member → Accept → Add Place to Plan → Vote on Place → View Map

---

## Current State Analysis

### Current Group Planner Operations (Estimated per session)

| Operation | Reads | Writes | Notes |
|-----------|-------|--------|-------|
| Login/Get Groups | 3+ | 0 | group_members query + N group reads |
| Create Group | 1 | 2 | create group + member doc |
| Get Group Details | 2 | 0 | group + members query |
| Search Places (destination) | 1-5 | 0 | places queries |
| Get Places for Group | 1 | 0 | travel_places query |
| Send Invitation | 2 | 1 | group check + create invitation |
| Accept Invitation | 3 | 2 | invitation + group update + member |
| Add Place to Plan | 1 | 1 | add to travel_places |
| Create Poll | 1 | 1 | add to travel_polls |
| Vote | 1 | 1 | update poll |
| **TOTAL (estimated)** | **16-20** | **8-10** | **~25-30 ops** |

### Target: 10 TOTAL Operations

---

## Architecture: Single-Document + Places Cache

### Core Concepts

1. **User Dashboard Document** - All user's trip data in ONE document
2. **Destination Places Cache** - Pre-fetched places by destination (Redis)
3. **Batched Writes** - Every mutation = 1 Firestore operation
4. **JWT Invitations** - No lookup needed for accept

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           REDIS CACHE (Source of Truth for READS)       │   │
│  │                                                          │   │
│  │  user:{uid}:trips        = All trips + groups           │   │
│  │  user:{uid}:invitations  = Pending invitations          │   │
│  │  places:{destination}    = Places for destination       │   │
│  │  group:{gid}:details     = Full group with places/polls │   │
│  │                                                          │   │
│  │  TTL: 1 hour for trips, 24 hours for places             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│         CACHE HIT        │         CACHE MISS                   │
│              │           │              │                       │
│              ▼           │              ▼                       │
│        Return data       │     ┌────────────────────┐          │
│        (0 Firestore)     │     │   FIRESTORE        │          │
│                          │     │   (1 READ)         │          │
│                          │     └────────────────────┘          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PLACES ENGINE (Pre-Cached)                  │   │
│  │                                                          │   │
│  │  - 16,885 places in Firestore                           │   │
│  │  - Pre-cached by city/state/country                     │   │
│  │  - 24-hour TTL in Redis                                 │   │
│  │  - 0 Firestore reads on cache hit                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Session Flow: 10 Operations

### Operation 1: LOGIN (1 Read)
```
User logs in → GET /api/group-planner-optimized/dashboard
├── Redis: Check cache → MISS (first time)
└── Firestore: 1 READ from trip_user_dashboards/{uid}
    └── Contains ALL:
        - All trip groups
        - All places in each group
        - All polls and votes
        - All members with details
        - Pending invitations
    └── Cache in Redis (TTL: 1 hour)
```

### Operation 2: CREATE GROUP (1 Write)
```
User creates trip group → POST /groups
├── Validation: In-memory (user from JWT)
├── Firestore: 1 BATCH WRITE
│   ├── travel_groups/{gid}
│   └── group_members/{gid}_{uid}
├── Redis: Update user:{uid}:trips
└── Return: Computed group data
```

### Operation 3: SET DESTINATION (0 ops - Redis only)
```
User sets destination "Bali, Indonesia"
├── This is a frontend/cache operation
├── Triggers places search (see next)
└── No Firestore write until group saved
```

### Operation 4: GET PLACES FOR DESTINATION (0 or 1 Read)
```
User searches places for "Bali"
├── Redis: Check places:bali → HIT (24h cache)
├── If HIT: Return top 20 places (0 Firestore)
├── If MISS: 1 Firestore query
│   └── places WHERE city_normalized == 'bali'
│   └── ORDER BY rank_score DESC LIMIT 20
│   └── Cache for 24 hours
└── Return: Places with lat/lng for map
```

### Operation 5: SEND INVITATION (1 Write)
```
User invites friend → POST /invitations
├── Validation: From dashboard cache
├── Firestore: 1 WRITE to group_invitations
├── Redis: Update invitations cache
└── Generate JWT token with all data
```

### Operation 6: ACCEPT INVITATION (1 Write)
```
Friend accepts → POST /invitations/{id}/accept
├── Decode JWT token (0 reads)
├── Firestore: 1 BATCH WRITE
│   ├── group_invitations/{id} → accepted
│   ├── travel_groups/{gid} → add member
│   └── group_members/{gid}_{uid}
├── Redis: Update both users' caches
└── Return: Group data from batch
```

### Operation 7: ADD PLACE TO PLAN (1 Write)
```
User adds place to trip → POST /groups/{id}/places
├── Place data already in frontend (from step 4)
├── Firestore: 1 WRITE to travel_places
├── Redis: Update group cache
└── Return: Updated places list
```

### Operation 8: CREATE POLL (1 Write)
```
User creates "Where to eat?" poll → POST /polls
├── Firestore: 1 WRITE to travel_polls
├── Redis: Update group cache
└── Return: Poll data
```

### Operation 9: VOTE ON POLL (1 Write)
```
User votes → POST /polls/{id}/vote
├── Firestore: 1 WRITE (update poll)
├── Redis: Update group cache
└── Return: Updated poll results
```

### Operation 10: VIEW MAP (0 Reads)
```
User opens map view
├── All places already in frontend state
├── lat/lng from places data
├── No additional Firestore reads
└── Render pins from cached data
```

---

## Total: 10 Operations

| Action | Reads | Writes | Total |
|--------|-------|--------|-------|
| Login (dashboard) | 1 | 0 | 1 |
| Create Group | 0 | 1 | 1 |
| Set Destination | 0 | 0 | 0 |
| Get Places | 0-1 | 0 | 0-1 |
| Send Invitation | 0 | 1 | 1 |
| Accept Invitation | 0 | 1 | 1 |
| Add Place to Plan | 0 | 1 | 1 |
| Create Poll | 0 | 1 | 1 |
| Vote | 0 | 1 | 1 |
| View Map | 0 | 0 | 0 |
| **TOTAL** | **1-2** | **7** | **8-9** |

Buffer for refresh: +1-2 reads = **10 total**

---

## New Collections

### `trip_user_dashboards/{user_id}`

```javascript
{
  "userId": "abc123",
  "lastUpdated": "2025-12-04T10:00:00Z",
  
  "groups": {
    "trip_001": {
      "groupId": "trip_001",
      "name": "Bali Adventure",
      "destination": "Bali, Indonesia",
      "destinationCoordinates": {
        "latitude": -8.4095,
        "longitude": 115.1889
      },
      "tripDates": {
        "startDate": "2025-03-15",
        "endDate": "2025-03-22"
      },
      "budgetRange": {
        "min": 1500,
        "max": 3000,
        "currency": "USD"
      },
      "createdBy": "abc123",
      "memberCount": 3,
      
      "members": [
        {"userId": "abc123", "displayName": "John", "email": "john@x.com", "role": "creator"},
        {"userId": "def456", "displayName": "Jane", "email": "jane@x.com", "role": "member"}
      ],
      
      "places": [
        {
          "placeId": "PL3A8F2C",
          "name": "Tanah Lot Temple",
          "coordinates": {"latitude": -8.6214, "longitude": 115.0868},
          "category": "attraction",
          "addedBy": "abc123",
          "votes": 3,
          "status": "planned"
        }
      ],
      
      "polls": [
        {
          "pollId": "poll_001",
          "question": "Where should we eat on Day 1?",
          "options": [
            {"id": 1, "text": "Warung Babi Guling", "votes": ["abc123", "def456"]},
            {"id": 2, "text": "Made's Warung", "votes": []}
          ],
          "createdBy": "abc123",
          "status": "active"
        }
      ],
      
      "checklist": [
        {"id": "item1", "text": "Book flights", "completed": true, "assignee": "abc123"},
        {"id": "item2", "text": "Reserve hotel", "completed": false}
      ]
    }
  },
  
  "pendingInvitations": [
    {
      "id": "inv_001",
      "groupId": "trip_002",
      "groupName": "Japan Trip",
      "inviterName": "Alice",
      "destination": "Tokyo, Japan",
      "createdAt": "2025-12-03T10:00:00Z"
    }
  ],
  
  "stats": {
    "activeTrips": 2,
    "upcomingTrips": 1,
    "totalPlacesPlanned": 15
  }
}
```

---

## Places Engine Integration

### Pre-Cached Destinations (Redis)

```python
# Key: places:destination:{normalized_destination}
# TTL: 24 hours
# Contains top 20 places for that destination

{
  "destination": "Bali, Indonesia",
  "normalized": "bali_indonesia",
  "coordinates": {"latitude": -8.4095, "longitude": 115.1889},
  "places": [
    {
      "id": "PL3A8F2C",
      "name": "Tanah Lot Temple",
      "coordinates": {"latitude": -8.6214, "longitude": 115.0868},
      "rankScore": 0.95,
      "category": "attraction",
      "photos": {"thumbnail_url": "..."},
      "aiSummary": "Iconic sea temple..."
    },
    // ... 19 more places
  ],
  "cachedAt": "2025-12-04T10:00:00Z"
}
```

### Places Search Flow

```
User types "Bali" in destination field
         │
         ▼
┌─────────────────────────────────┐
│  Check Redis: places:bali       │
└─────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
  HIT      MISS
    │         │
    ▼         ▼
Return    Query Firestore (1 read)
cached    WHERE city_normalized == 'bali'
places    ORDER BY rank_score DESC
          LIMIT 20
              │
              ▼
         Cache in Redis
         TTL: 24 hours
              │
              ▼
         Return places
```

---

## Implementation Files

### Backend

```
Group_planner/
├── repositories/
│   └── dashboard_repository.py      # Single-document pattern
├── services/
│   ├── batched_write_service.py     # Batch operations
│   └── places_integration.py        # Places Engine cache
└── routes/
    └── optimized_routes.py          # New /api/v2/group-planner
```

### Frontend Changes

```javascript
// hooks/useGroupPlannerQuery.js
// - Single dashboard query on login
// - All mutations return computed data
// - Optimistic updates for all operations

// services/placesApi.js
// - Destination search with cache
// - Returns places with lat/lng for map
```

---

## Map Integration

### Showing Places on Map

```javascript
// Places already loaded from dashboard or destination search
const placesWithCoords = trip.places.map(place => ({
  id: place.placeId,
  name: place.name,
  position: {
    lat: place.coordinates.latitude,
    lng: place.coordinates.longitude
  },
  status: place.status,  // 'planned', 'visited', 'skipped'
  category: place.category
}));

// Render on map (no additional API calls)
<GoogleMap>
  {placesWithCoords.map(place => (
    <Marker
      key={place.id}
      position={place.position}
      label={place.name}
      icon={getCategoryIcon(place.category)}
    />
  ))}
</GoogleMap>
```

### Destination Coordinates

```python
# When user sets destination, we get coordinates from places
def get_destination_coordinates(destination: str) -> dict:
    """
    Get lat/lng for a destination.
    Uses places database - 0 extra reads if cached.
    """
    places = search_places_by_destination(destination, limit=1)
    if places:
        return places[0]['coordinates']
    
    # Fallback: Use geocoding API (external, not Firestore)
    return geocode_destination(destination)
```

---

## Migration Path

### Week 1: Create Dashboard Collection
- Build `trip_user_dashboards` collection
- Migrate existing groups/places/polls
- Add places coordinates

### Week 2: Places Cache Layer
- Implement 24-hour Redis cache for places
- Pre-warm cache for popular destinations
- Add rank_score ordering

### Week 3: Batch Writes
- Convert all mutations to batched
- Update dashboard on every write
- Test cache invalidation

### Week 4: Frontend Integration
- Update context to use single dashboard
- Implement map component
- Remove individual Firestore listeners

---

## Summary

| Metric | Current | Phase 20 | Improvement |
|--------|---------|----------|-------------|
| Reads per session | ~20 | **2** | **90%** |
| Writes per session | ~10 | **7** | **30%** |
| Total ops | ~30 | **9-10** | **67%** |
| Map load | N reads | **0** | **100%** |
| Places search | 1-5 reads | **0-1** | **80%** |

**Key wins:**
1. Single dashboard document = 1 read gets ALL data
2. Places pre-cached by destination = 0 reads
3. Map uses cached coordinates = 0 reads
4. Batched writes = each action costs 1 op
5. JWT invitations = 0 lookup reads

---

*Document created: December 4, 2025*
