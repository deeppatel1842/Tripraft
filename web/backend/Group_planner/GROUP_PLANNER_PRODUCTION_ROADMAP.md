# Group Planner Production Roadmap

## Executive Summary

Complete production-ready implementation for collaborative travel planning with:
- **Target**: 10 total Firestore operations per session
- **Real-time**: Instant updates across all group members
- **Integration**: Seamless Expense Engine and Places Engine connectivity
- **Architecture**: Professional folder structure with zero hardcoded values

---

## Current State Analysis

### Existing Endpoints (V1 - `/api/group-planner/`)

| Category | Endpoint | Method | Operations |
|----------|----------|--------|------------|
| **Auth** | `/auth/verify` | POST | 0 |
| **Auth** | `/health` | GET | 0 |
| **Groups** | `/groups` | POST | 3-4 |
| **Groups** | `/user/groups` | GET | 2-3 |
| **Groups** | `/groups/<id>` | GET | 1-2 |
| **Groups** | `/groups/<id>` | PUT | 2 |
| **Groups** | `/groups/<id>` | DELETE | 3-4 |
| **Invitations** | `/invitations` | POST | 2-3 |
| **Invitations** | `/invitations/<id>` | GET | 1 |
| **Invitations** | `/invitations/<id>/accept` | POST | 4-5 |
| **Invitations** | `/user/invitations` | GET | 2-3 |
| **Polls** | `/groups/<id>/polls` | POST | 2 |
| **Polls** | `/groups/<id>/polls/<id>/vote` | POST | 2 |
| **Polls** | `/groups/<id>/polls/<id>` | DELETE | 2 |
| **Places** | `/groups/<id>/places` | POST | 2 |
| **Places** | `/groups/<id>/places/<id>/vote` | POST | 2 |
| **Places** | `/groups/<id>/places/<id>` | DELETE | 2 |
| **Places** | `/groups/<id>/places/<id>/remarks` | PUT | 2 |
| **Places** | `/groups/<id>/places/<id>` | PATCH | 2 |
| **Checklist** | `/groups/<id>/checklist` | POST | 2 |
| **Checklist** | `/groups/<id>/checklist/<id>/toggle` | PATCH | 2 |
| **Checklist** | `/groups/<id>/checklist/<id>` | DELETE | 2 |
| **Budget** | `/groups/<id>/budget` | PATCH | 2 |
| **Itinerary** | `/groups/<id>/itinerary-document` | PUT | 2 |
| **Expense Link** | `/groups/<id>/link-expense` | POST | 5-8 |
| **Expense Link** | `/groups/<id>/unlink-expense` | POST | 4-6 |
| **Geocode** | `/geocode` | POST | 0 (external) |

**Current Session Total: 40-60+ operations**

### Current Collections

```
Firestore Collections:
├── travel_groups/{groupId}
│   ├── name, description, destination
│   ├── members[] (user IDs)
│   ├── member_details[] (enriched info)
│   ├── places[] (embedded)
│   ├── polls[] (embedded)
│   ├── checklist[] (embedded)
│   ├── itinerary_document (text)
│   ├── estimated_budget
│   └── expense_group_id (linked)
├── group_members/{docId}
│   ├── user_id, group_id, role
│   └── joined_at
├── group_invitations/{invitationId}
│   ├── group_id, invited_email
│   ├── status, expires_at
│   └── invited_by, group_name
└── users/{userId}
    ├── email, display_name
    └── username, avatar_url
```

---

## Phase 1: Foundation & Folder Structure

### 1.1 Professional Folder Structure

```
Group_planner/
├── __init__.py                    # Package exports
├── config.py                      # Configuration (no hardcoding)
├── constants.py                   # Enums, status codes
├── exceptions.py                  # Custom exceptions
├── logger.py                      # Centralized logging
│
├── models/
│   ├── __init__.py
│   ├── group.py                   # TravelGroup model
│   ├── member.py                  # GroupMember model
│   ├── invitation.py              # GroupInvitation model
│   ├── place.py                   # Place model
│   ├── poll.py                    # Poll model
│   ├── checklist.py               # ChecklistItem model
│   ├── document.py                # TripDocument model
│   └── dashboard.py               # UserDashboard model
│
├── repositories/
│   ├── __init__.py
│   ├── base_repository.py         # Abstract base
│   ├── dashboard_repository.py    # Single-document pattern
│   ├── group_repository.py        # Group CRUD
│   ├── member_repository.py       # Member operations
│   ├── invitation_repository.py   # Invitation operations
│   └── cache_repository.py        # Redis cache layer
│
├── services/
│   ├── __init__.py
│   ├── group_service.py           # Group business logic
│   ├── invitation_service.py      # Invitation workflow
│   ├── poll_service.py            # Poll operations
│   ├── place_service.py           # Place management
│   ├── checklist_service.py       # Checklist operations
│   ├── itinerary_service.py       # Document management
│   ├── expense_link_service.py    # Expense Engine integration
│   ├── places_integration.py      # Places Engine integration
│   ├── batched_write_service.py   # Batch Firestore writes
│   ├── realtime_service.py        # Real-time updates
│   └── email_service.py           # Email notifications
│
├── routes/
│   ├── __init__.py
│   ├── v1/                        # Legacy routes
│   │   ├── __init__.py
│   │   └── routes.py              # Current implementation
│   └── v2/                        # Optimized routes
│       ├── __init__.py
│       ├── dashboard_routes.py    # Dashboard endpoint
│       ├── group_routes.py        # Group CRUD
│       ├── invitation_routes.py   # Invitations
│       ├── poll_routes.py         # Polls
│       ├── place_routes.py        # Places
│       ├── checklist_routes.py    # Checklist
│       ├── itinerary_routes.py    # Documents
│       └── realtime_routes.py     # SSE/WebSocket
│
├── middleware/
│   ├── __init__.py
│   ├── auth_middleware.py         # Token verification
│   ├── rate_limiter.py            # Rate limiting
│   └── validation_middleware.py   # Request validation
│
├── utils/
│   ├── __init__.py
│   ├── validators.py              # Input validation
│   ├── formatters.py              # Response formatting
│   └── helpers.py                 # Utility functions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_group_service.py
│   ├── test_invitation_service.py
│   ├── test_poll_service.py
│   ├── test_place_service.py
│   └── integration/
│       ├── test_dashboard_api.py
│       └── test_realtime_api.py
│
└── docs/
    ├── API_REFERENCE.md
    ├── ARCHITECTURE.md
    └── DEPLOYMENT.md
```

### 1.2 Configuration System

```python
# config.py - Environment-based configuration
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class GroupPlannerConfig:
    # Firestore Collections
    TRAVEL_GROUPS_COLLECTION: str = "travel_groups"
    GROUP_MEMBERS_COLLECTION: str = "group_members"
    GROUP_INVITATIONS_COLLECTION: str = "group_invitations"
    USER_DASHBOARDS_COLLECTION: str = "trip_user_dashboards"
    
    # Cache Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    CACHE_TTL_DASHBOARD: int = 600  # 10 minutes
    CACHE_TTL_PLACES: int = 86400   # 24 hours
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Invitation Settings
    INVITATION_EXPIRY_DAYS: int = 7
    MAX_GROUP_MEMBERS: int = 50
    MAX_PLACES_PER_GROUP: int = 100
    MAX_POLLS_PER_GROUP: int = 20
    
    # Email Settings
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "true").lower() == "true"
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")
    
    # Feature Flags
    ENABLE_REALTIME: bool = os.getenv("ENABLE_REALTIME", "true").lower() == "true"
    ENABLE_PLACES_ENGINE: bool = os.getenv("ENABLE_PLACES_ENGINE", "true").lower() == "true"

config = GroupPlannerConfig()
```

### 1.3 Deliverables

- [ ] Create folder structure
- [ ] Implement base configuration
- [ ] Set up logging system
- [ ] Create base repository pattern
- [ ] Write unit tests for config

---

## Phase 2: Single-Document Dashboard Pattern

### 2.1 Dashboard Schema

```json
{
  "collection": "trip_user_dashboards",
  "document": "{userId}",
  "schema": {
    "userId": "string",
    "createdAt": "timestamp",
    "lastUpdated": "timestamp",
    "version": "number",
    
    "groups": {
      "{groupId}": {
        "groupId": "string",
        "name": "string",
        "description": "string",
        "destination": "string",
        "destinationCoordinates": {
          "lat": "number",
          "lng": "number"
        },
        "tripDates": {
          "startDate": "string",
          "endDate": "string"
        },
        "budgetRange": {
          "min": "number",
          "max": "number",
          "currency": "string"
        },
        "createdBy": "string",
        "createdAt": "timestamp",
        "memberCount": "number",
        "role": "string",
        
        "members": [{
          "userId": "string",
          "email": "string",
          "displayName": "string",
          "avatarUrl": "string",
          "role": "string",
          "joinedAt": "timestamp"
        }],
        
        "places": [{
          "placeId": "string",
          "name": "string",
          "coordinates": { "lat": "number", "lng": "number" },
          "category": "string",
          "votes": ["userId"],
          "remarks": "string",
          "visitDate": "string",
          "duration": "string",
          "addedBy": "string",
          "addedAt": "timestamp"
        }],
        
        "polls": [{
          "pollId": "string",
          "question": "string",
          "options": ["string"],
          "votes": { "option": ["userId"] },
          "createdBy": "string",
          "createdAt": "timestamp",
          "expiresAt": "timestamp"
        }],
        
        "checklist": [{
          "itemId": "string",
          "text": "string",
          "completed": "boolean",
          "assignedTo": "string",
          "addedBy": "string",
          "addedAt": "timestamp"
        }],
        
        "itineraryDocument": "string",
        "estimatedBudget": "number",
        "expenseGroupId": "string"
      }
    },
    
    "invitations": [{
      "invitationId": "string",
      "groupId": "string",
      "groupName": "string",
      "destination": "string",
      "inviterName": "string",
      "inviterEmail": "string",
      "createdAt": "timestamp",
      "expiresAt": "timestamp",
      "status": "string"
    }],
    
    "placesCache": {
      "{destination}": {
        "places": [...],
        "fetchedAt": "timestamp",
        "expiresAt": "timestamp"
      }
    },
    
    "preferences": {
      "defaultCurrency": "string",
      "notificationsEnabled": "boolean",
      "emailDigestFrequency": "string"
    }
  }
}
```

### 2.2 Dashboard Repository

```python
# repositories/dashboard_repository.py
class TripDashboardRepository:
    """
    Single-document pattern for trip planning.
    
    Target: 1 READ for entire dashboard, 1 WRITE per mutation.
    """
    
    def get_full_dashboard(self, user_id: str) -> Dict:
        """1 Firestore READ - Returns everything"""
        pass
    
    def get_or_create_dashboard(self, user_id: str) -> Dict:
        """1 READ or 1 WRITE"""
        pass
    
    def add_group_to_dashboard(self, user_id: str, group_data: Dict) -> bool:
        """1 WRITE - Add new group"""
        pass
    
    def update_group_in_dashboard(self, user_id: str, group_id: str, updates: Dict) -> bool:
        """1 WRITE - Update group data"""
        pass
    
    def add_place_to_group(self, user_id: str, group_id: str, place: Dict) -> bool:
        """1 WRITE - Add place"""
        pass
    
    def vote_on_place(self, user_id: str, group_id: str, place_id: str) -> bool:
        """1 WRITE - Toggle vote"""
        pass
    
    def add_poll_to_group(self, user_id: str, group_id: str, poll: Dict) -> bool:
        """1 WRITE - Add poll"""
        pass
    
    def vote_on_poll(self, user_id: str, group_id: str, poll_id: str, option: str) -> bool:
        """1 WRITE - Vote on poll"""
        pass
```

### 2.3 Deliverables

- [ ] Create dashboard model
- [ ] Implement dashboard repository
- [ ] Build migration script (existing data → dashboard)
- [ ] Add cache layer for dashboard
- [ ] Write integration tests

---

## Phase 3: V2 API Endpoints

### 3.1 Endpoint Specification

All endpoints prefixed with `/api/group-planner/v2/`

#### Dashboard Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/dashboard` | GET | 1 READ | Full dashboard load |
| `/dashboard/initialize` | POST | N (one-time) | Build from existing data |
| `/dashboard/sync` | POST | 1 WRITE | Sync optimistic updates |

#### Group Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups` | POST | 1 WRITE | Create group (batched) |
| `/groups/{id}` | PUT | 1 WRITE | Update group |
| `/groups/{id}` | DELETE | 1 WRITE | Delete group |
| `/groups/{id}/members/{uid}` | DELETE | 1 WRITE | Remove member |

#### Invitation Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/invitations` | POST | 1 WRITE | Send invitation |
| `/invitations/{id}/accept` | POST | 1 WRITE | Accept (batched) |
| `/invitations/{id}/decline` | POST | 1 WRITE | Decline invitation |

#### Place Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups/{id}/places` | POST | 1 WRITE | Add place |
| `/groups/{id}/places/{pid}` | DELETE | 1 WRITE | Remove place |
| `/groups/{id}/places/{pid}/vote` | POST | 1 WRITE | Toggle vote |
| `/groups/{id}/places/{pid}/remarks` | PUT | 1 WRITE | Update remarks |
| `/groups/{id}/places/{pid}` | PATCH | 1 WRITE | Update details |

#### Poll Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups/{id}/polls` | POST | 1 WRITE | Create poll |
| `/groups/{id}/polls/{pid}` | DELETE | 1 WRITE | Delete poll |
| `/groups/{id}/polls/{pid}/vote` | POST | 1 WRITE | Vote on poll |

#### Checklist Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups/{id}/checklist` | POST | 1 WRITE | Add item |
| `/groups/{id}/checklist/{cid}` | DELETE | 1 WRITE | Delete item |
| `/groups/{id}/checklist/{cid}/toggle` | PATCH | 1 WRITE | Toggle complete |

#### Document Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups/{id}/itinerary` | PUT | 1 WRITE | Update document |
| `/groups/{id}/budget` | PATCH | 1 WRITE | Update budget |

#### Places Engine Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/places/search` | GET | 0-1 READ | Search (24h cache) |
| `/places/nearby` | GET | 0-1 READ | Nearby (24h cache) |
| `/places/geocode` | POST | 0 | Geocode place name |

#### Expense Integration Endpoints

| Endpoint | Method | Firestore Ops | Description |
|----------|--------|---------------|-------------|
| `/groups/{id}/expense/link` | POST | 2 WRITE | Link to expense |
| `/groups/{id}/expense/unlink` | POST | 2 WRITE | Unlink expense |

### 3.2 Response Format

```json
{
  "success": true,
  "data": { ... },
  "operations": {
    "reads": 1,
    "writes": 0
  },
  "meta": {
    "timestamp": "2025-12-04T10:30:00Z",
    "version": "2.0",
    "cached": false
  }
}
```

### 3.3 Deliverables

- [ ] Create route blueprints
- [ ] Implement all V2 endpoints
- [ ] Add request validation
- [ ] Add rate limiting
- [ ] Write API documentation
- [ ] Create Postman collection

---

## Phase 4: Real-Time Updates

### 4.1 Real-Time Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    REAL-TIME FLOW                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User A (Browser)         Server           User B (Browser)  │
│       │                     │                    │           │
│       │  1. Add Place       │                    │           │
│       │─────────────────────>│                   │           │
│       │                     │                    │           │
│       │  2. Optimistic UI   │                    │           │
│       │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │                    │           │
│       │                     │                    │           │
│       │                     │  3. Batch Write    │           │
│       │                     │  (Firestore)       │           │
│       │                     │                    │           │
│       │                     │  4. Pub/Sub Event  │           │
│       │                     │─────────────────────>          │
│       │                     │                    │           │
│       │                     │  5. SSE Push       │           │
│       │                     │─────────────────────>          │
│       │                     │                    │           │
│       │                     │                    │  6. UI    │
│       │                     │                    │  Update   │
│       │                     │                    │           │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Event Types

```python
class GroupPlannerEventType(Enum):
    # Group Events
    GROUP_CREATED = "group.created"
    GROUP_UPDATED = "group.updated"
    GROUP_DELETED = "group.deleted"
    
    # Member Events
    MEMBER_JOINED = "member.joined"
    MEMBER_LEFT = "member.left"
    MEMBER_REMOVED = "member.removed"
    
    # Place Events
    PLACE_ADDED = "place.added"
    PLACE_REMOVED = "place.removed"
    PLACE_VOTED = "place.voted"
    PLACE_UPDATED = "place.updated"
    
    # Poll Events
    POLL_CREATED = "poll.created"
    POLL_VOTED = "poll.voted"
    POLL_CLOSED = "poll.closed"
    POLL_DELETED = "poll.deleted"
    
    # Checklist Events
    CHECKLIST_ITEM_ADDED = "checklist.item_added"
    CHECKLIST_ITEM_TOGGLED = "checklist.item_toggled"
    CHECKLIST_ITEM_DELETED = "checklist.item_deleted"
    
    # Document Events
    ITINERARY_UPDATED = "itinerary.updated"
    BUDGET_UPDATED = "budget.updated"
    
    # Invitation Events
    INVITATION_RECEIVED = "invitation.received"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_DECLINED = "invitation.declined"
```

### 4.3 SSE Endpoint

```python
@group_planner_v2.route('/realtime/subscribe', methods=['GET'])
@require_auth
def subscribe_to_updates():
    """
    Server-Sent Events for real-time updates.
    
    Subscribe to updates for all user's groups.
    """
    def event_stream():
        user_id = request.user['user_id']
        pubsub = redis_client.pubsub()
        
        # Subscribe to user's channel
        pubsub.subscribe(f"user:{user_id}:updates")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                yield f"event: {event_data['type']}\n"
                yield f"data: {json.dumps(event_data['payload'])}\n\n"
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )
```

### 4.4 Frontend Integration

```javascript
// services/groupPlannerRealtime.js
class GroupPlannerRealtimeService {
  constructor() {
    this.eventSource = null;
    this.handlers = new Map();
  }
  
  connect(token) {
    this.eventSource = new EventSource(
      `${API_URL}/group-planner/v2/realtime/subscribe`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    
    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.dispatch(event.type, data);
    };
  }
  
  on(eventType, handler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType).push(handler);
  }
  
  dispatch(eventType, data) {
    const handlers = this.handlers.get(eventType) || [];
    handlers.forEach(handler => handler(data));
  }
  
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

### 4.5 Deliverables

- [ ] Implement Redis Pub/Sub
- [ ] Create SSE endpoint
- [ ] Build event dispatcher
- [ ] Create frontend realtime service
- [ ] Add reconnection logic
- [ ] Write integration tests

---

## Phase 5: Places Engine Integration

### 5.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 PLACES ENGINE INTEGRATION                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Group Planner                Places Engine                 │
│       │                            │                        │
│       │  1. Search "Tokyo"         │                        │
│       │───────────────────────────>│                        │
│       │                            │                        │
│       │                            │  2. Check Redis        │
│       │                            │     (24h TTL)          │
│       │                            │                        │
│       │  3. Return Places          │                        │
│       │<───────────────────────────│                        │
│       │                            │                        │
│       │  4. User Selects Place     │                        │
│       │                            │                        │
│       │  5. Add to Group           │                        │
│       │  (with coordinates)        │                        │
│       │                            │                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Places Integration Service

```python
# services/places_integration.py
class PlacesIntegrationService:
    """
    Integrate Places Engine with Group Planner.
    
    Features:
    - Search places by destination
    - Get nearby places from coordinates
    - Cache results for 24 hours
    - Zero Firestore ops for cached results
    """
    
    def __init__(self):
        self.places_service = PlacesService()
        self.cache = RedisCache()
    
    def get_places_for_destination(
        self,
        destination: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        Get suggested places for a destination.
        
        1. Check Redis cache (24h TTL)
        2. If miss, query Places Engine
        3. Cache and return results
        
        Firestore: 0-1 READ
        """
        cache_key = f"places:{destination}:{category or 'all'}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'places': cached,
                'from_cache': True,
                'coordinates': cached[0].get('coordinates') if cached else None
            }
        
        # Get destination coordinates
        coordinates = self.geocode_destination(destination)
        
        # Query Places Engine
        places = self.places_service.search_places(
            lat=coordinates['lat'],
            lng=coordinates['lng'],
            category=category,
            limit=limit
        )
        
        # Cache for 24 hours
        self.cache.set(cache_key, places, ttl=86400)
        
        return {
            'places': places,
            'from_cache': False,
            'coordinates': coordinates
        }
    
    def geocode_destination(self, destination: str) -> Dict:
        """
        Get coordinates for destination name.
        Uses Nominatim with caching.
        """
        cache_key = f"geocode:{destination}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Call Nominatim
        result = self._call_nominatim(destination)
        
        # Cache indefinitely
        self.cache.set(cache_key, result)
        
        return result
```

### 5.3 Deliverables

- [ ] Create places integration service
- [ ] Implement geocoding with cache
- [ ] Add nearby places endpoint
- [ ] Create category filtering
- [ ] Write integration tests

---

## Phase 6: Expense Engine Integration

### 6.1 Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 EXPENSE ENGINE INTEGRATION                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Group Planner                 Expense Engine               │
│       │                              │                      │
│       │  1. Link Expense             │                      │
│       │─────────────────────────────>│                      │
│       │                              │                      │
│       │                              │  2. Create Group     │
│       │                              │  (same name/members) │
│       │                              │                      │
│       │  3. Return expense_group_id  │                      │
│       │<─────────────────────────────│                      │
│       │                              │                      │
│       │  4. Store Link               │                      │
│       │  (dashboard update)          │                      │
│       │                              │                      │
│       │  5. View Expenses            │                      │
│       │─────────────────────────────>│                      │
│       │                              │                      │
│       │  6. Return Balance/Expenses  │                      │
│       │<─────────────────────────────│                      │
│       │                              │                      │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Expense Link Service

```python
# services/expense_link_service.py
class ExpenseLinkService:
    """
    Link Group Planner groups to Expense Engine.
    
    Operations:
    - Link: Create expense group with same members
    - Unlink: Remove link (optionally delete expense group)
    - Sync: Keep members in sync
    """
    
    def link_expense_group(
        self,
        group_id: str,
        user_id: str
    ) -> Dict:
        """
        Create linked expense group.
        
        Firestore: 2 WRITES (GP dashboard + Expense group)
        """
        # Get group data
        group = self.dashboard_repo.get_group(user_id, group_id)
        
        # Create expense group
        expense_group = self.expense_service.create_group(
            name=group['name'],
            created_by=user_id,
            description=f"Linked from Group Planner",
            currency='USD'
        )
        
        # Add members
        for member in group['members']:
            if member['userId'] != user_id:
                self.expense_service.add_member(
                    expense_group['group_id'],
                    member['userId']
                )
        
        # Update dashboard
        self.dashboard_repo.update_group_in_dashboard(
            user_id=user_id,
            group_id=group_id,
            updates={'expenseGroupId': expense_group['group_id']}
        )
        
        return expense_group
    
    def sync_members(
        self,
        group_id: str,
        expense_group_id: str
    ) -> bool:
        """
        Sync members between GP and Expense groups.
        Called when member joins/leaves GP group.
        """
        pass
```

### 6.3 Deliverables

- [ ] Create expense link service
- [ ] Implement link/unlink endpoints
- [ ] Add member sync logic
- [ ] Handle unlink cleanup
- [ ] Write integration tests

---

## Phase 7: Frontend Optimization

### 7.1 Optimized Context

```jsx
// context/GroupPlannerContextV2.jsx
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';

const GroupPlannerContextV2 = createContext(null);

export const useGroupPlannerV2 = () => {
  const context = useContext(GroupPlannerContextV2);
  if (!context) {
    throw new Error('useGroupPlannerV2 must be used within GroupPlannerProviderV2');
  }
  return context;
};

export const GroupPlannerProviderV2 = ({ children }) => {
  const { user, getIdToken } = useAuth();
  
  // Single dashboard state
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [operationCount, setOperationCount] = useState({ reads: 0, writes: 0 });
  
  // Real-time connection
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  
  // Cache
  const [placesCache, setPlacesCache] = useState({});
  
  // Load dashboard on mount
  const loadDashboard = useCallback(async (forceRefresh = false) => {
    // Check localStorage cache
    if (!forceRefresh) {
      const cached = localStorage.getItem('gp_dashboard_v2');
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < 10 * 60 * 1000) { // 10 min TTL
          setDashboard(data);
          return data;
        }
      }
    }
    
    // Fetch from API
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/group-planner/v2/dashboard`, {
        headers: { Authorization: `Bearer ${await getIdToken()}` }
      });
      const result = await response.json();
      
      setDashboard(result.data);
      setOperationCount(prev => ({
        reads: prev.reads + (result.operations?.reads || 0),
        writes: prev.writes + (result.operations?.writes || 0)
      }));
      
      // Cache
      localStorage.setItem('gp_dashboard_v2', JSON.stringify({
        data: result.data,
        timestamp: Date.now()
      }));
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getIdToken]);
  
  // Optimistic update helper
  const optimisticUpdate = useCallback((updateFn, apiCall) => {
    // Apply optimistic update
    setDashboard(prev => updateFn(prev));
    
    // Execute API call
    apiCall().catch(err => {
      // Rollback on error
      loadDashboard(true);
      setError(err.message);
    });
  }, [loadDashboard]);
  
  // ... rest of the context
};
```

### 7.2 Component Updates

```jsx
// components/Group_planner/PlanTabContentV2.jsx
import { useGroupPlannerV2 } from '../../context/GroupPlannerContextV2';

export default function PlanTabContentV2({ groupId }) {
  const { 
    dashboard,
    addPlace,
    voteOnPlace,
    deletePlace,
    searchPlaces,
    operationCount
  } = useGroupPlannerV2();
  
  const group = dashboard?.groups?.[groupId];
  const places = group?.places || [];
  
  // Use Places Engine for suggestions
  const [suggestions, setSuggestions] = useState([]);
  
  const handleSearchPlaces = async () => {
    if (group?.destination) {
      const result = await searchPlaces(group.destination);
      setSuggestions(result.places);
    }
  };
  
  return (
    <div className="plan-tab-v2">
      {/* Operation counter for debugging */}
      <div className="operation-counter">
        Ops: {operationCount.reads}R / {operationCount.writes}W
      </div>
      
      {/* Places list with instant updates */}
      <PlacesList 
        places={places}
        onVote={voteOnPlace}
        onDelete={deletePlace}
      />
      
      {/* Places Engine suggestions */}
      <PlacesSuggestions
        suggestions={suggestions}
        onAdd={addPlace}
        onSearch={handleSearchPlaces}
      />
    </div>
  );
}
```

### 7.3 Deliverables

- [ ] Create V2 context
- [ ] Update all components
- [ ] Add optimistic updates
- [ ] Implement localStorage cache
- [ ] Add operation counter

---

## Phase 8: Testing Suite

### 8.1 Test Structure

```
tests/
├── conftest.py                    # Fixtures
├── unit/
│   ├── test_dashboard_repo.py
│   ├── test_group_service.py
│   ├── test_invitation_service.py
│   ├── test_poll_service.py
│   ├── test_place_service.py
│   └── test_validators.py
├── integration/
│   ├── test_dashboard_api.py
│   ├── test_group_api.py
│   ├── test_invitation_api.py
│   ├── test_realtime_api.py
│   └── test_places_integration.py
└── e2e/
    ├── test_complete_flow.py
    └── test_multi_user.py
```

### 8.2 Test Fixtures

```python
# conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_firestore():
    """Mock Firestore client"""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document
    
    return mock_db

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock_client = MagicMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    return mock_client

@pytest.fixture
def sample_dashboard():
    """Sample dashboard data"""
    return {
        'userId': 'test-user-123',
        'groups': {
            'group-1': {
                'groupId': 'group-1',
                'name': 'Test Trip',
                'destination': 'Tokyo',
                'members': [
                    {'userId': 'test-user-123', 'role': 'creator'}
                ],
                'places': [],
                'polls': [],
                'checklist': []
            }
        },
        'invitations': []
    }

@pytest.fixture
def auth_headers():
    """Mock auth headers"""
    return {'Authorization': 'Bearer test-token'}
```

### 8.3 Sample Tests

```python
# tests/unit/test_dashboard_repo.py
import pytest
from Group_planner.repositories.dashboard_repository import TripDashboardRepository

class TestDashboardRepository:
    
    def test_get_full_dashboard_returns_all_data(self, mock_firestore, sample_dashboard):
        """Dashboard should return all groups, invitations in 1 read"""
        mock_firestore.collection().document().get().to_dict.return_value = sample_dashboard
        
        repo = TripDashboardRepository(db=mock_firestore)
        result = repo.get_full_dashboard('test-user-123')
        
        assert result is not None
        assert 'groups' in result
        assert 'invitations' in result
        mock_firestore.collection().document().get.assert_called_once()
    
    def test_add_place_uses_single_write(self, mock_firestore, sample_dashboard):
        """Adding place should use exactly 1 write"""
        repo = TripDashboardRepository(db=mock_firestore)
        
        repo.add_place_to_group(
            user_id='test-user-123',
            group_id='group-1',
            place={'name': 'Tokyo Tower', 'coordinates': {'lat': 35.6, 'lng': 139.7}}
        )
        
        mock_firestore.collection().document().update.assert_called_once()
```

### 8.4 Deliverables

- [ ] Set up pytest configuration
- [ ] Create all fixtures
- [ ] Write unit tests (>80% coverage)
- [ ] Write integration tests
- [ ] Set up CI/CD pipeline

---

## Phase 9: Deployment & Monitoring

### 9.1 Environment Configuration

```yaml
# config/production.yaml
firebase:
  project_id: ${FIREBASE_PROJECT_ID}
  credentials_path: ${GOOGLE_APPLICATION_CREDENTIALS}

redis:
  host: ${REDIS_HOST}
  port: ${REDIS_PORT}
  password: ${REDIS_PASSWORD}

rate_limiting:
  enabled: true
  requests_per_minute: 60
  requests_per_hour: 1000

features:
  realtime_enabled: true
  places_engine_enabled: true
  email_notifications: true

monitoring:
  log_level: INFO
  operation_tracking: true
  performance_metrics: true
```

### 9.2 Monitoring Setup

```python
# middleware/monitoring.py
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def track_operations(f):
    """Track Firestore operations for monitoring"""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        
        result = f(*args, **kwargs)
        
        duration = (time.time() - start_time) * 1000
        operations = result.get('operations', {}) if isinstance(result, dict) else {}
        
        logger.info(
            "[METRICS] Endpoint: %s | Duration: %.2fms | Reads: %d | Writes: %d",
            request.endpoint,
            duration,
            operations.get('reads', 0),
            operations.get('writes', 0)
        )
        
        return result
    
    return decorated
```

### 9.3 Health Check Endpoint

```python
@group_planner_v2.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check"""
    checks = {
        'firestore': check_firestore(),
        'redis': check_redis(),
        'places_engine': check_places_engine(),
        'expense_engine': check_expense_engine()
    }
    
    all_healthy = all(c['status'] == 'healthy' for c in checks.values())
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'version': '2.0.0',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if all_healthy else 503
```

### 9.4 Deliverables

- [ ] Create environment configs
- [ ] Set up monitoring
- [ ] Create health checks
- [ ] Set up alerting
- [ ] Write runbook

---

## Operation Count Summary

### Target: 10 Operations Per Session

| Action | V1 Ops | V2 Ops |
|--------|--------|--------|
| Login/Load Dashboard | 5-8 | 1 |
| Create Group | 3-4 | 1 |
| Add Place | 2 | 1 |
| Vote on Place | 2 | 1 |
| Create Poll | 2 | 1 |
| Vote on Poll | 2 | 1 |
| Add Checklist Item | 2 | 1 |
| Accept Invitation | 4-5 | 1 |
| Search Places | 1-2 | 0-1 |
| Refresh/Tab Switch | 5-8 | 0 |
| **Session Total** | **40-60** | **6-10** |

### Typical Session Flow

```
1. User Login
   └── Dashboard Load: 1 READ

2. View Trip "Tokyo"
   └── Already in dashboard: 0 ops

3. Add Place "Tokyo Tower"
   └── Dashboard Update: 1 WRITE

4. Vote on Place
   └── Dashboard Update: 1 WRITE

5. Create Poll "When to visit?"
   └── Dashboard Update: 1 WRITE

6. Accept Invitation
   └── Batch Update: 1 WRITE

7. Search Nearby Places
   └── Cache Hit: 0 ops
   └── Cache Miss: 1 READ (then cached 24h)

8. Refresh Page
   └── localStorage Cache: 0 ops

SESSION TOTAL: 5-7 operations
```

---

## Timeline

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1: Foundation | 2 days | High |
| Phase 2: Dashboard Pattern | 3 days | High |
| Phase 3: V2 API | 4 days | High |
| Phase 4: Real-Time | 3 days | Medium |
| Phase 5: Places Integration | 2 days | Medium |
| Phase 6: Expense Integration | 2 days | Medium |
| Phase 7: Frontend | 3 days | High |
| Phase 8: Testing | 3 days | High |
| Phase 9: Deployment | 2 days | High |

**Total: ~24 days**

---

## Success Metrics

1. **Operation Count**: ≤10 per session
2. **Cache Hit Rate**: ≥90%
3. **API Response Time**: <200ms (P95)
4. **Real-Time Latency**: <100ms
5. **Test Coverage**: ≥80%
6. **Zero Hardcoded Values**: ✓

---

## Appendix A: Collection Migration Script

```python
# scripts/migrate_to_dashboard.py
def migrate_user_to_dashboard(user_id: str):
    """
    Migrate existing user data to single-document dashboard.
    One-time migration script.
    """
    db = firestore.client()
    
    # Get all user's groups
    groups = db.collection('travel_groups').where('members', 'array_contains', user_id).get()
    
    # Get all invitations
    invitations = db.collection('group_invitations').where('invited_email', '==', user_email).where('status', '==', 'pending').get()
    
    # Build dashboard document
    dashboard = {
        'userId': user_id,
        'createdAt': datetime.utcnow(),
        'lastUpdated': datetime.utcnow(),
        'groups': {},
        'invitations': [],
        'placesCache': {}
    }
    
    for group_doc in groups:
        group_data = group_doc.to_dict()
        dashboard['groups'][group_doc.id] = {
            'groupId': group_doc.id,
            'name': group_data.get('name'),
            'destination': group_data.get('destination'),
            'members': group_data.get('member_details', []),
            'places': group_data.get('places', []),
            'polls': group_data.get('polls', []),
            'checklist': group_data.get('checklist', []),
            # ... rest of fields
        }
    
    for inv_doc in invitations:
        inv_data = inv_doc.to_dict()
        dashboard['invitations'].append({
            'invitationId': inv_doc.id,
            'groupId': inv_data.get('group_id'),
            'groupName': inv_data.get('group_name'),
            # ... rest of fields
        })
    
    # Write dashboard document
    db.collection('trip_user_dashboards').document(user_id).set(dashboard)
    
    print(f"Migrated user {user_id}: {len(dashboard['groups'])} groups, {len(dashboard['invitations'])} invitations")
```

---

## Appendix B: API Quick Reference

### Authentication
```
POST /api/group-planner/v2/auth/verify
GET  /api/group-planner/v2/health
```

### Dashboard
```
GET  /api/group-planner/v2/dashboard
POST /api/group-planner/v2/dashboard/initialize
POST /api/group-planner/v2/dashboard/sync
```

### Groups
```
POST   /api/group-planner/v2/groups
PUT    /api/group-planner/v2/groups/{id}
DELETE /api/group-planner/v2/groups/{id}
DELETE /api/group-planner/v2/groups/{id}/members/{uid}
```

### Invitations
```
POST /api/group-planner/v2/invitations
POST /api/group-planner/v2/invitations/{id}/accept
POST /api/group-planner/v2/invitations/{id}/decline
```

### Places
```
POST   /api/group-planner/v2/groups/{id}/places
DELETE /api/group-planner/v2/groups/{id}/places/{pid}
POST   /api/group-planner/v2/groups/{id}/places/{pid}/vote
PUT    /api/group-planner/v2/groups/{id}/places/{pid}/remarks
PATCH  /api/group-planner/v2/groups/{id}/places/{pid}
```

### Polls
```
POST   /api/group-planner/v2/groups/{id}/polls
DELETE /api/group-planner/v2/groups/{id}/polls/{pid}
POST   /api/group-planner/v2/groups/{id}/polls/{pid}/vote
```

### Checklist
```
POST   /api/group-planner/v2/groups/{id}/checklist
DELETE /api/group-planner/v2/groups/{id}/checklist/{cid}
PATCH  /api/group-planner/v2/groups/{id}/checklist/{cid}/toggle
```

### Documents
```
PUT   /api/group-planner/v2/groups/{id}/itinerary
PATCH /api/group-planner/v2/groups/{id}/budget
```

### Places Engine
```
GET  /api/group-planner/v2/places/search?destination=X&category=Y
GET  /api/group-planner/v2/places/nearby?lat=X&lng=Y&radius=Z
POST /api/group-planner/v2/places/geocode
```

### Expense Integration
```
POST /api/group-planner/v2/groups/{id}/expense/link
POST /api/group-planner/v2/groups/{id}/expense/unlink
```

### Real-Time
```
GET /api/group-planner/v2/realtime/subscribe (SSE)
```

---

*Document Version: 1.0*
*Last Updated: December 4, 2025*
*Author: TripRaft Engineering Team*
