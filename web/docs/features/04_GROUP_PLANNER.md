# Feature: Collaborative Group Planner

## Overview

The Group Planner is the core product feature of TripRaft. It enables groups of users to collaboratively plan trips in real-time: creating itineraries, voting on places, running polls, managing checklists, chatting with AI bots, tracking expenses, and sharing documents. It uses WebSocket connections for instant updates across all group members.

---

## System Flow (Group Lifecycle)

```
                    GROUP CREATION + COLLABORATION
                    ===============================

User A (Admin)                Flask + SocketIO               Database
     │                              │                            │
     │  POST /api/v1/gp/groups      │                            │
     │  {name, destination,         │                            │
     │   start_date, end_date,      │                            │
     │   description, budget}       │                            │
     │─────────────────────────────>│                            │
     │                              │  Create TravelGroup        │
     │                              │  Create TripMember (admin) │
     │                              │  Create linked expense     │
     │                              │  group (if budget set)     │
     │                              │──────────────────────────>│
     │                              │                            │
     │  201 Created {group}         │                            │
     │<─────────────────────────────│                            │
     │                              │                            │
     │  WSS: join_group {group_id}  │                            │
     │═════════════════════════════>│                            │
     │                              │  Verify membership         │
     │                              │  join_room(group:{id})     │
     │                              │                            │
     │  WSS: presence:update        │                            │
     │<═════════════════════════════│                            │
     │                              │                            │
     │  POST /api/v1/gp/invitations │                            │
     │  {group_id, email: "B@..."}  │                            │
     │─────────────────────────────>│                            │
     │                              │  Create TripInvitation     │
     │                              │  (7-day expiry)            │
     │                              │──────────────────────────>│
     │                              │                            │
     │                              │  send_invitation_email     │
     │                              │  .delay() → Celery         │
     │                              │                            │
     │  201 Created {invitation}    │                            │
     │<─────────────────────────────│                            │


User B (Invitee)              Flask + SocketIO               Database
     │                              │                            │
     │  POST /api/v1/gp/            │                            │
     │  invitations/{id}/accept     │                            │
     │─────────────────────────────>│                            │
     │                              │  Update invitation status  │
     │                              │  Create TripMember(member) │
     │                              │  Log GroupActivity         │
     │                              │──────────────────────────>│
     │                              │                            │
     │                              │  SocketIO emit to room:    │
     │                              │  member:joined             │
     │                              │  → All group members       │
     │                              │                            │
     │  200 OK {group}              │                            │
     │<─────────────────────────────│                            │
     │                              │                            │
     │  WSS: join_group {group_id}  │                            │
     │═════════════════════════════>│                            │
```

---

## 6-Tab Interface

```
┌────────────────────────────────────────────────────────────────────┐
│  GROUP PLANNER: "Barcelona Summer 2026"                  [Chat] ▶ │
├────────┬──────────┬───────────┬──────────┬──────────┬─────────────┤
│Itinerary│ Library  │ Logistics │ Treasury │  Pulse   │   Circle    │
├────────┴──────────┴───────────┴──────────┴──────────┴─────────────┤
│                                                                    │
│  [Active tab content renders here]                                │
│                                                                    │
│  + Map Panel (Leaflet) on the right side                          │
│    - Day-colored markers for all places                            │
│    - Click marker → details popup                                  │
│    - Cluster markers when zoomed out                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Tab Details

| Tab | Component | Description |
|-----|-----------|-------------|
| **Itinerary** | ItineraryTab.jsx | Day-by-day plan, editable stops, drag-reorder, duration tracking |
| **Library** | LibraryTab.jsx | Saved places with collaborative voting, bookmarks, place cards |
| **Logistics** | LogisticsTab.jsx | Transportation, accommodation, shared logistics notes |
| **Treasury** | TreasuryTab.jsx | Integrated expense tracking (links to Expense API), group budget |
| **Pulse** | PulseTab.jsx | Activity feed, recent changes, real-time notifications |
| **Circle** | CircleTab.jsx | Group members, online status (green dot), role management |

---

## Sub-Feature: Places and Voting

```
User A                       Flask Backend                 Database
   │                              │                            │
   │  POST /gp/groups/{id}/places │                            │
   │  {name, lat, lng, category,  │                            │
   │   visit_date, notes,         │                            │
   │   suggested_duration}        │                            │
   │─────────────────────────────>│                            │
   │                              │  PlaceService.add_place()  │
   │                              │  INSERT Place              │
   │                              │  Log GroupActivity          │
   │                              │──────────────────────────>│
   │                              │                            │
   │                              │  SocketIO: place:added     │
   │                              │  → room group:{id}         │
   │                              │                            │
   │  201 Created {place}         │                            │
   │<─────────────────────────────│                            │

User B (sees place:added via WebSocket)
   │                              │                            │
   │  POST /gp/groups/{id}/       │                            │
   │  places/{place_id}/vote      │                            │
   │  {vote: "up"}                │                            │
   │─────────────────────────────>│                            │
   │                              │  PlaceService.vote()       │
   │                              │  Toggle vote (up/down)     │
   │                              │──────────────────────────>│
   │                              │                            │
   │                              │  SocketIO: place:voted     │
   │                              │  → room group:{id}         │
   │  200 OK {votes}              │                            │
   │<─────────────────────────────│                            │
```

---

## Sub-Feature: Polls

```
User A                       Flask Backend                 Database
   │                              │                            │
   │  POST /gp/groups/{id}/polls  │                            │
   │  {question: "When to go?",   │                            │
   │   type: "single_choice",     │                            │
   │   options: ["Jun", "Jul"],   │                            │
   │   expires_at: "2026-05-01"}  │                            │
   │─────────────────────────────>│                            │
   │                              │  PollService.create()      │
   │                              │  INSERT Poll + options     │
   │                              │──────────────────────────>│
   │                              │                            │
   │  201 Created {poll}          │                            │
   │<─────────────────────────────│                            │

User B
   │  POST /gp/groups/{id}/       │                            │
   │  polls/{poll_id}/vote        │                            │
   │  {option_index: 0}           │                            │
   │─────────────────────────────>│                            │
   │                              │  PollService.vote()        │
   │                              │  Toggle vote               │
   │                              │  Emit poll:voted           │
   │                              │──────────────────────────>│
   │  200 OK {poll_results}       │                            │
   │<─────────────────────────────│                            │
```

---

## Sub-Feature: Checklists

```
User A                       Flask Backend                 Database
   │                              │                            │
   │  POST /gp/groups/{id}/       │                            │
   │  checklist                   │                            │
   │  {title: "Book flights",     │                            │
   │   priority: "high",          │                            │
   │   category: "logistics"}     │                            │
   │─────────────────────────────>│                            │
   │                              │  ChecklistService.create() │
   │                              │  INSERT ChecklistItem      │
   │                              │──────────────────────────>│
   │  201 Created {item}          │                            │
   │<─────────────────────────────│                            │

User B
   │  PATCH /gp/checklist/{id}    │                            │
   │  (toggle complete)           │                            │
   │─────────────────────────────>│                            │
   │                              │  ChecklistService.toggle() │
   │                              │  Emit checklist:toggled    │
   │  200 OK                      │                            │
   │<─────────────────────────────│                            │

User A
   │  POST /gp/checklist/{id}/    │                            │
   │  assign {user_id: "B"}       │                            │
   │─────────────────────────────>│                            │
   │                              │  Assign to member          │
   │  200 OK                      │                            │
   │<─────────────────────────────│                            │
```

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/gp_groups.py` | Group CRUD, members, budget, itinerary, activities (12 endpoints) |
| `app/api/v1/gp_places.py` | Place add/list/vote/update/delete/geocode (7 endpoints) |
| `app/api/v1/gp_polls.py` | Poll create/list/vote/delete (4 endpoints) |
| `app/api/v1/gp_checklist.py` | Checklist CRUD, toggle, assign, stats (7 endpoints) |
| `app/api/v1/gp_invitations.py` | Invitation create/accept/decline/resend/cancel (8 endpoints) |
| `app/api/v1/gp_vault.py` | Document upload/list/download/delete (4 endpoints) |
| `app/api/v1/gp_notifications.py` | Notification list/mark-read/bulk-read (3 endpoints) |
| `app/api/v1/gp_export.py` | PDF export, iCal export, group clone, join-by-code (4 endpoints) |
| `app/api/v1/gp_chat.py` | Chat send/list/delete/read/unread (5 endpoints + AI triggers) |
| `app/services/travel_group_service.py` | GroupService: group lifecycle, member roles, budget, activities |
| `app/services/travel_place_service.py` | PlaceService: add, vote, update, delete, geocode |
| `app/services/poll_service.py` | PollService: create, vote, delete, results |
| `app/services/checklist_service.py` | ChecklistService: create, toggle, assign, delete, stats |
| `app/services/trip_invite_service.py` | InvitationService: send, accept, decline, resend, cancel |
| `app/services/chat_service.py` | ChatService: send, history, mark_read, summary |
| `app/services/vault_service.py` | VaultService: upload, download, delete, list |
| `app/services/export_service.py` | ExportService: to_pdf, to_ical, clone_group |
| `app/services/notification_service.py` | NotificationService: create, mark_read, get_user_list |
| `app/domain/group_planner/models.py` | 15 SQLAlchemy models (TravelGroup, TripMember, Place, Poll, Chat, etc.) |
| `app/infrastructure/realtime/socketio_ext.py` | SocketIO initialization and event handlers |
| `app/infrastructure/realtime/events.py` | Event type constants |

### Frontend

| File | Purpose |
|------|---------|
| `src/components/groupPlanner/jsx/GroupPlannerPage.jsx` | Page wrapper (Header + Manager + Footer) |
| `src/components/groupPlanner/jsx/GroupPlannerManager.jsx` | Container: group selection, tab management, socket setup |
| `src/components/groupPlanner/jsx/CreateGroupModal.jsx` | Group creation dialog |
| `src/components/groupPlanner/jsx/tabs/ItineraryTab.jsx` | Day-by-day plan editor |
| `src/components/groupPlanner/jsx/tabs/LibraryTab.jsx` | Places library with voting |
| `src/components/groupPlanner/jsx/tabs/LogisticsTab.jsx` | Shared logistics |
| `src/components/groupPlanner/jsx/tabs/TreasuryTab.jsx` | Expense integration |
| `src/components/groupPlanner/jsx/tabs/PulseTab.jsx` | Activity feed |
| `src/components/groupPlanner/jsx/tabs/CircleTab.jsx` | Member management |
| `src/components/groupPlanner/jsx/chat/ChatPanel.jsx` | Real-time chat with @mentions |
| `src/components/groupPlanner/jsx/chat/CrewCards.jsx` | AI action cards |
| `src/components/groupPlanner/jsx/chat/ScoutConsentCard.jsx` | AI consent UI |
| `src/components/groupPlanner/jsx/map/MapPanel.jsx` | Leaflet map with markers |
| `src/components/groupPlanner/jsx/shared/GroupSelector.jsx` | Group dropdown |
| `src/services/groupPlannerApi.js` | All group planner REST calls |
| `src/services/chatApi.js` | Chat REST calls |
| `src/hooks/useGroupPlannerQuery.js` | TanStack Query hooks for groups, places, polls, members |
| `src/hooks/useChatQuery.js` | Infinite scroll chat + mutations |
| `src/hooks/useGroupSocket.js` | Real-time group event listeners |
| `src/hooks/useChatSocket.js` | Real-time chat event listeners |

---

## Real-time Events

| Event | Direction | Trigger | Data |
|-------|-----------|---------|------|
| `join_group` | Client → Server | Component mount | `{group_id}` |
| `leave_group` | Client → Server | Component unmount | `{group_id}` |
| `presence:update` | Server → Client | Join/leave | `{online_members: [...]}` |
| `chat:message` | Server → Client | New message | `{message_dict}` |
| `place:added` | Server → Client | Place created | `{place_dict}` |
| `place:voted` | Server → Client | Vote cast | `{place_id, votes}` |
| `poll:voted` | Server → Client | Poll vote | `{poll_id, results}` |
| `checklist:toggled` | Server → Client | Item toggled | `{item_id, completed}` |
| `itinerary:updated` | Server → Client | Itinerary edit | `{itinerary_dict}` |
| `member:joined` | Server → Client | Member accepted invite | `{member_dict}` |
| `member:left` | Server → Client | Member left group | `{user_id}` |

---

## Database Models

```
travel_groups
├── id (UUIDv7, PK)
├── name (String)
├── destination (String)
├── description (Text)
├── start_date, end_date (Date)
├── budget (Decimal)
├── currency (String, default "USD")
├── status (String: planning, active, completed, archived)
├── expense_group_id (FK → groups.id, nullable)
├── invite_code (String, unique)
├── created_by (FK → users.id)
└── created_at, updated_at

trip_members
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── user_id (FK → users.id)
├── role (String: admin, member)
└── joined_at

places
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── name, description, category
├── latitude, longitude
├── visit_date, suggested_duration
├── photo_url, rating
├── notes, remarks
├── added_by (FK → users.id)
└── created_at

place_votes
├── id (UUIDv7, PK)
├── place_id (FK → places.id)
├── user_id (FK → users.id)
├── vote (String: up/down)
└── created_at

polls
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── question (String)
├── poll_type (String: single_choice, multiple_choice)
├── options (JSON)
├── expires_at (DateTime, nullable)
├── created_by (FK → users.id)
└── created_at

poll_votes
├── id (UUIDv7, PK)
├── poll_id (FK → polls.id)
├── user_id (FK → users.id)
├── option_index (Integer)
└── created_at

checklist_items
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── title (String)
├── category (String)
├── priority (String: low, medium, high)
├── is_completed (Boolean)
├── assigned_to (FK → users.id, nullable)
├── created_by (FK → users.id)
└── created_at

chat_messages
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── sender_id (FK → users.id)
├── content (Text)
├── message_type (String: text, system, ai_response, ai_card)
├── metadata (JSON, nullable)
├── is_deleted (Boolean)
└── created_at

trip_invitations
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── invited_by (FK → users.id)
├── email (String)
├── status (String: pending, accepted, declined, expired)
├── expires_at (DateTime, default +7 days)
└── created_at

vault_documents
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── filename (String)
├── file_path (String)
├── file_size (Integer)
├── mime_type (String)
├── uploaded_by (FK → users.id)
└── created_at

group_activities
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── actor_id (FK → users.id)
├── action (String: place_added, poll_created, member_joined, etc.)
├── metadata (JSON)
└── created_at

itinerary_documents
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── content (JSON)
├── version (Integer)
└── updated_at

notifications
├── id (UUIDv7, PK)
├── user_id (FK → users.id)
├── group_id (FK → travel_groups.id)
├── type (String)
├── title, message (String)
├── data (JSON)
├── is_read (Boolean)
└── created_at

message_reads
├── id (UUIDv7, PK)
├── message_id (FK → chat_messages.id)
├── user_id (FK → users.id)
└── read_at

chat_summaries
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── summary (Text)
├── start_message_id, end_message_id (FK)
└── created_at
```

---

## API Endpoint Summary

| Category | Count | Base Path |
|----------|-------|-----------|
| Groups | 12 | `/gp/groups` |
| Places | 7 | `/gp/groups/{id}/places` |
| Polls | 4 | `/gp/groups/{id}/polls` |
| Checklist | 7 | `/gp/groups/{id}/checklist` |
| Chat | 5 | `/gp/groups/{id}/chat` |
| Invitations | 8 | `/gp/invitations` |
| Vault | 4 | `/gp/groups/{id}/vault` |
| Notifications | 3 | `/gp/notifications` |
| Export | 4 | `/gp/groups/{id}/export` |
| **Total** | **54** | |
