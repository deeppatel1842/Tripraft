# Phase 4 -- Real-Time & Social Features

Right now, TripRaft is a "check back later" app. You add a place, your friend sees it next time they open the app. This phase makes it a "stay in the app" experience with real-time collaboration and social features.

---

## Why Real-Time Matters

```mermaid
flowchart TD
    A[Current: Request-Response] --> B["Alice adds a place<br/>Bob doesn't know until<br/>he refreshes the page"]
    
    C[Target: Real-Time] --> D["Alice adds a place<br/>Bob sees it appear instantly<br/>on his screen"]
    
    B --> E[Users leave the app<br/>Engagement drops]
    D --> F[Users stay in the app<br/>Feels like collaboration]
```

The difference between a planning tool and a collaboration platform is real-time. Google Docs didn't beat Word because it was better at formatting -- it won because two people could edit at the same time.

---

## WebSocket Architecture

```mermaid
flowchart TD
    subgraph "Client Side"
        A[React App] --> B[Socket.IO Client]
        B --> C[Event Handlers]
        C --> D[React Query Cache Updates]
    end
    
    subgraph "Server Side"
        E[Flask-SocketIO] --> F[Event Router]
        F --> G[Group Rooms]
        G --> H[Broadcast to<br/>Room Members]
    end
    
    subgraph "Infrastructure"
        I[Redis Pub/Sub] --> J[Cross-instance<br/>Message Passing]
    end
    
    B <-->|WebSocket| E
    E --> I
    I --> J
    J --> G
```

### Technology Choice

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Flask-SocketIO | Works with our Flask app, mature, easy | Requires eventlet/gevent | Best fit |
| FastAPI + WebSockets | Native async, fast | Requires rewriting all routes | Too much work |
| Separate Node.js WS server | Best WS performance | Two languages, two deploys | Overkill for now |
| Pusher (hosted) | Zero infrastructure | $49/mo at scale, vendor lock | Good fallback |

**Decision**: Flask-SocketIO with Redis as the message queue. It integrates directly with our existing Flask app and uses Redis (which we already have) for cross-instance communication.

### Room-Based Architecture

```mermaid
graph TD
    A[User connects] --> B[Authenticate via JWT]
    B --> C[Join rooms based on<br/>group memberships]
    
    C --> D[group:123]
    C --> E[group:456]
    C --> F[user:789 - personal]
    
    G[Event: expense_added<br/>in group 123] --> D
    D --> H[Broadcast to all<br/>members in group:123]
    
    I[Event: settlement_completed<br/>for user 789] --> F
    F --> J[Only user 789<br/>gets this notification]
```

Each user joins rooms for:
- Every group they belong to
- Their personal notification channel
- Any active poll they can vote in

---

## Real-Time Events

### What Gets Broadcast

| Event | Room | Payload | UI Update |
|-------|------|---------|-----------|
| expense_added | group:{id} | New expense data | Add to expense list, update balances |
| expense_updated | group:{id} | Updated expense | Refresh expense in list |
| expense_deleted | group:{id} | Expense ID | Remove from list, update balances |
| settlement_created | group:{id} | Settlement data | Add to settlements, update balances |
| member_joined | group:{id} | New member info | Add to member list |
| member_left | group:{id} | Member ID | Remove from member list |
| place_added | group:{id} | Place data | Add to shared places |
| place_removed | group:{id} | Place ID | Remove from places |
| poll_created | group:{id} | Poll data | Show poll notification |
| vote_cast | group:{id} | Anonymous vote count | Update poll results |
| checklist_updated | group:{id} | Item status | Toggle checkbox |
| itinerary_changed | group:{id} | Changed day/slot | Refresh itinerary view |
| typing_indicator | group:{id} | User ID + feature | Show "Alice is editing..." |

### Event Flow

```mermaid
sequenceDiagram
    participant Alice as Alice's Browser
    participant WS as WebSocket Server
    participant API as REST API
    participant DB as Database
    participant Bob as Bob's Browser
    participant Carol as Carol's Browser

    Alice->>API: POST /api/v1/expenses<br/>$50 for lunch
    API->>DB: Insert expense
    API->>WS: Emit 'expense_added'<br/>to room group:123
    API-->>Alice: HTTP 201 Created
    
    par Broadcast
        WS->>Bob: expense_added event
        WS->>Carol: expense_added event
    end
    
    Bob->>Bob: React Query cache<br/>automatically updated
    Carol->>Carol: Toast: "Alice added<br/>$50 for lunch"
```

---

## Group Chat

### Why Chat (When WhatsApp Exists)

Fair question. Everyone already uses WhatsApp or iMessage for group travel chat. But our chat has context:

- Messages can reference places ("Has anyone been to this restaurant?" with the place card inline)
- Messages can reference expenses ("I just paid for dinner" with the expense attached)
- Messages can reference itinerary items ("Should we move this to Tuesday?")
- Trip-specific chat that doesn't get lost in your regular WhatsApp chats

### Chat Architecture

```mermaid
flowchart TD
    A[Chat Message] --> B{Type}
    
    B -->|Text| C[Regular message]
    B -->|Place Reference| D[Message + place card preview]
    B -->|Expense Reference| E[Message + expense summary]
    B -->|Itinerary Reference| F[Message + day/time slot]
    B -->|Image| G[Message + image upload]
    B -->|Poll Quick-create| H[Message becomes a mini-poll]
    
    C --> I[Store in DB]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J[Broadcast via WebSocket]
    J --> K[All group members<br/>see it in real-time]
```

### Data Model

```mermaid
erDiagram
    CHAT_MESSAGE {
        int id PK
        int group_id FK
        int sender_id FK
        string content
        string message_type
        int reference_id
        string reference_type
        datetime created_at
        boolean is_edited
        datetime edited_at
    }
    
    CHAT_REACTION {
        int id PK
        int message_id FK
        int user_id FK
        string emoji
    }
    
    CHAT_READ_RECEIPT {
        int id PK
        int group_id FK
        int user_id FK
        int last_read_message_id FK
        datetime read_at
    }
    
    CHAT_MESSAGE ||--o{ CHAT_REACTION : "has reactions"
    CHAT_MESSAGE ||--o{ CHAT_READ_RECEIPT : "tracked by"
```

### Features

| Feature | Phase | Notes |
|---------|-------|-------|
| Text messages | 4A | Basic chat |
| Place/expense references | 4A | Context-aware chat |
| Image sharing | 4A | Upload to S3/R2 |
| Emoji reactions | 4A | Quick feedback |
| Read receipts | 4A | Unread count badge |
| Message search | 4B | Full-text search |
| @mentions | 4B | Notify specific members |
| Mini-polls in chat | 4B | Quick decisions |
| AI trip assistant in chat | 4C | Ask AI questions in group context |

---

## Live Collaboration: Itinerary Editing

The most complex real-time feature: multiple people editing the itinerary simultaneously.

```mermaid
sequenceDiagram
    participant Alice
    participant Server
    participant Bob

    Note over Alice, Bob: Both viewing Day 2 itinerary

    Alice->>Server: Lock: Morning slot
    Server->>Bob: "Alice is editing Morning"
    Bob->>Bob: Morning slot shows<br/>"Being edited by Alice"
    
    Alice->>Server: Update: Morning = Museum visit
    Server->>Alice: Confirmed
    Server->>Bob: Morning updated: Museum visit
    Server->>Server: Release lock
    
    Bob->>Server: Lock: Afternoon slot
    Server->>Alice: "Bob is editing Afternoon"
    Bob->>Server: Update: Afternoon = Food tour
    Server->>Bob: Confirmed
    Server->>Alice: Afternoon updated: Food tour
```

### Conflict Resolution Strategy

We use optimistic locking with slot-level granularity:

```mermaid
flowchart TD
    A[Edit Request] --> B{Is slot locked<br/>by someone else?}
    B -->|No| C[Lock slot<br/>Start editing]
    B -->|Yes| D[Show: 'Alice is editing this'<br/>Wait or edit different slot]
    
    C --> E[Save changes]
    E --> F[Release lock]
    F --> G[Broadcast update<br/>to all viewers]
    
    H[Lock timeout: 30 seconds] --> I[Auto-release<br/>prevent abandoned locks]
```

We're not building Google Docs-level operational transforms. The itinerary has natural slot boundaries (morning/afternoon/evening per day) that make simple locking practical.

---

## Push Notifications

### Channels

```mermaid
flowchart TD
    A[Notification Event] --> B{Priority}
    
    B -->|High| C[Push Notification<br/>+ In-app + Email]
    B -->|Medium| D[In-app + Email digest]
    B -->|Low| E[In-app only]
    
    C --> F[Trip cancelled]
    C --> G[Date changed]
    C --> H[Travel alert for destination]
    
    D --> I[New expense added]
    D --> J[Poll created]
    D --> K[Settlement requested]
    
    E --> L[Place suggestion]
    E --> M[Checklist item done]
    E --> N[Chat message]
```

### Implementation

| Platform | Technology | Push Service |
|----------|-----------|-------------|
| Web | Service Worker + Push API | Web Push (free) |
| iOS (future) | APNs | Apple Push Notification Service |
| Android (future) | FCM | Firebase Cloud Messaging |

For web-only launch, the Push API combined with service workers handles it. No native app needed.

---

## Presence & Activity

Show who's online and what they're doing:

```mermaid
graph TD
    A[Active Users Panel] --> B["Alice 🟢 Online<br/>Viewing Day 3 itinerary"]
    A --> C["Bob 🟢 Online<br/>Adding an expense"]
    A --> D["Carol 🟡 Away<br/>Last seen 10 min ago"]
    A --> E["Dave ⚫ Offline<br/>Last seen yesterday"]
```

Implementation:
- Heartbeat every 30 seconds via WebSocket
- Status transitions: online → away (5 min) → offline (disconnect)
- Activity tracking: which page/feature the user is on
- Stored in Redis (ephemeral, no need for persistence)

---

## Implementation Timeline

```mermaid
gantt
    title Phase 4: Real-Time & Social
    dateFormat YYYY-MM-DD
    
    section Phase 4A: Foundation
    Flask-SocketIO setup       :a1, 2027-01-01, 7d
    Room management            :a2, after a1, 5d
    Real-time expense updates  :a3, after a2, 7d
    Real-time itinerary sync   :a4, after a3, 10d
    Basic group chat           :a5, after a4, 14d
    
    section Phase 4B: Enhancement
    Presence system            :b1, after a5, 5d
    Push notifications (web)   :b2, after b1, 7d
    Chat features (reactions, mentions) :b3, after b2, 7d
    Live itinerary co-editing  :b4, after b3, 10d
    
    section Phase 4C: Intelligence
    AI assistant in chat       :c1, after b4, 14d
    Smart notifications        :c2, after c1, 7d
```

**Phase 4A total: ~6 weeks**
**Phase 4B total: ~4 weeks**
**Phase 4C total: ~3 weeks**

Phase 4A alone transforms the app from feel-slow to feel-alive. That's the critical milestone.

---

## Infrastructure Impact

| Resource | Current | After Phase 4 |
|----------|---------|--------------|
| WebSocket connections | 0 | 100-10,000 concurrent |
| Redis memory | ~30MB (cache) | ~100MB (cache + pub/sub + presence) |
| Server CPU | Low (REST only) | Medium (REST + WS + event routing) |
| Bandwidth | Low | Medium (WS keepalive + events) |
| Database writes | Low | Medium (chat messages) |

Redis Cloud free tier (30MB) will likely not be sufficient once chat + presence is active. Budget for $5-10/mo Redis upgrade.
