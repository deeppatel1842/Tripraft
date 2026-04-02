# TripRaft — High-Level Design Document

## 1. System Context

```
                              ┌──────────────────────────────────────────┐
                              │             EXTERNAL SYSTEMS             │
                              │                                          │
                              │  ┌──────────┐  ┌──────────┐  ┌───────┐  │
                              │  │  Ollama   │  │  SMTP    │  │  Web  │  │
                              │  │  (LLM)   │  │  Server  │  │ Search│  │
                              │  └─────┬────┘  └────┬─────┘  └───┬───┘  │
                              └───────┼─────────────┼─────────────┼──────┘
                                      │             │             │
┌────────────────┐           ┌────────┴─────────────┴─────────────┴──────┐
│                │  HTTPS    │                                           │
│   React SPA    ├──────────►│              Flask Backend                │
│   (Browser)    │◄──────────┤              Port 5000                    │
│                │  WS/WSS   │                                           │
│  Port 5173     ├──────────►│  ┌─────────┐  ┌──────────┐  ┌─────────┐  │
│  (Vite dev)    │           │  │  REST   │  │ SocketIO │  │ Celery  │  │
│                │           │  │  API    │  │  Events  │  │ Workers │  │
└────────────────┘           │  └────┬────┘  └────┬─────┘  └────┬────┘  │
                              │       │            │              │       │
                              │  ┌────┴────────────┴──────────────┴───┐  │
                              │  │          Service Layer              │  │
                              │  └────────────────┬───────────────────┘  │
                              │                   │                      │
                              │  ┌────────────────┴───────────────────┐  │
                              │  │          Domain Layer               │  │
                              │  │    (Models, Repositories)           │  │
                              │  └────────────────┬───────────────────┘  │
                              └───────────────────┼──────────────────────┘
                                                  │
                       ┌──────────────────────────┼──────────────────────┐
                       │                          │                      │
                  ┌────┴─────┐           ┌────────┴────────┐    ┌───────┴──────┐
                  │ Primary  │           │   Travel Ref    │    │    Redis     │
                  │   DB     │           │      DB         │    │   Cache +    │
                  │ (SQLite/ │           │ (SQLite, R/O)   │    │   Broker     │
                  │  Postgres│           │  16k+ places    │    │              │
                  │  26 tbl) │           │  FTS5 index     │    │              │
                  └──────────┘           └─────────────────┘    └──────────────┘
```

---

## 2. Component Architecture

### 2.1 Frontend (React SPA)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REACT APPLICATION                              │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      App.jsx (Router)                             │  │
│  │  React.lazy() code-split routes:                                  │  │
│  │    /            → HomePage                                        │  │
│  │    /login       → AuthPage                                        │  │
│  │    /places      → PlaceSearchPage                                 │  │
│  │    /planner     → GroupPlannerPage                                │  │
│  │    /expenses    → ExpensePage                                     │  │
│  │    /trip        → TripPlanner                                     │  │
│  │    /analytics   → ExpenseAnalytics                                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │   Services   │  │    Hooks     │  │   Context   │  │    Lib     │  │
│  │              │  │              │  │             │  │            │  │
│  │ sqlAuthApi   │  │ useExpense   │  │ AuthContext │  │ queryClient│  │
│  │ expenseApi   │  │ useChat      │  │ (JWT +     │  │ Persist    │  │
│  │ chatApi      │  │ useGroup     │  │  CSRF +    │  │ (IndexedDB)│  │
│  │ groupApi     │  │ usePlaces    │  │  refresh)  │  │            │  │
│  │ placeSearch  │  │ useSocket    │  │             │  │ indexedDB  │  │
│  │ aiConsent    │  │ useAiConsent │  │             │  │ Persister  │  │
│  │ tripPlanner  │  │ useTripQuery │  │             │  │            │  │
│  │ pdfExport    │  │ useAutoSave  │  │             │  │            │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  └────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              apiClient.js (HTTP + Retry + Auth Interceptor)       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              TanStack Query Cache (staleTime: 5min, gc: 30min)   │  │
│  │              IndexedDB Persister (maxAge: 60min)                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Backend (Flask 5-Layer Architecture)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION (api/v1/*.py)                                   │
│  25 route blueprints, ~135 endpoints                                    │
│  Decorators: @require_auth → @require_group_role → @limit_api          │
│  Response format: { success, data, error, meta }                        │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 2: VALIDATION (schemas/*.py)                                     │
│  15 Marshmallow schema modules                                          │
│  Input sanitization (bleach), type coercion, nested validation          │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 3: SERVICE (services/*.py)                                       │
│  25 stateless service classes                                           │
│  Return pattern: Tuple[bool, Dict] — (success, result_or_error)        │
│  Transaction boundary: each service method = one DB transaction         │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 4: DOMAIN (domain/*/models.py)                                   │
│  4 bounded contexts: users, expenses, group_planner, ai                 │
│  45+ SQLAlchemy models with UUIDv7 PKs                                  │
│  Repositories for complex queries                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 5: INFRASTRUCTURE (infrastructure/*/)                            │
│  auth/ — JWT + bcrypt + CSRF decorators                                 │
│  cache/ — Redis with ETag and config-driven invalidation                │
│  db/ — SQLAlchemy engine + read-only travel DB + UUIDv7                 │
│  email/ — SMTP delivery                                                 │
│  llm/ — Ollama client + prompt templates + output validation            │
│  realtime/ — Flask-SocketIO + event handlers                            │
│  search/ — Web search adapter                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Architecture

### 3.1 Primary Database Schema (26 Tables)

```
┌──────────────────────┐       ┌──────────────────────────┐
│       users           │       │      user_sessions       │
│───────────────────────│       │──────────────────────────│
│ id          UUID7  PK │◄──┐  │ id            UUID7   PK │
│ email       VARCHAR   │   │  │ user_id       UUID7   FK │──►
│ display_name VARCHAR  │   │  │ refresh_token VARCHAR    │
│ password_hash VARCHAR │   │  │ ip_address    VARCHAR    │
│ is_verified  BOOLEAN  │   │  │ expires_at    TIMESTAMP  │
│ created_at  TIMESTAMP │   │  └──────────────────────────┘
│ updated_at  TIMESTAMP │   │
└───────────┬───────────┘   │  ┌──────────────────────────┐
            │               │  │      audit_logs           │
            │               │  │──────────────────────────│
            │               └──│ user_id       UUID7   FK │
            │                  │ action        VARCHAR    │
            │                  │ resource      VARCHAR    │
            │                  │ details       JSONB      │
            │                  └──────────────────────────┘
            │
    ┌───────┴───────────────────────────────────────────┐
    │                       │                           │
    ▼                       ▼                           ▼
┌────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│  EXPENSE   │    │  GROUP PLANNER   │    │     AI DOMAIN        │
│  CONTEXT   │    │    CONTEXT       │    │                      │
│────────────│    │──────────────────│    │──────────────────────│
│ groups     │    │ travel_groups    │    │ ai_consent           │
│ members    │    │ trip_members     │    │ agent_logs           │
│ expenses   │    │ places           │    │ conversation_states  │
│ splits     │    │ polls            │    └──────────────────────┘
│ settlements│    │ poll_votes       │
│ invitations│    │ checklist_items  │
└────────────┘    │ events           │
                  │ chat_messages    │
                  │ reactions        │
                  │ read_receipts    │
                  │ notifications    │
                  │ vault_files      │
                  │ invitations      │
                  └──────────────────┘
```

### 3.2 Travel Reference Database (Read-Only)

```
┌────────────────────────────────┐
│        places (16,000+)        │
│────────────────────────────────│
│ id              INTEGER     PK │
│ name            TEXT           │
│ state           TEXT           │
│ city            TEXT           │
│ type            TEXT           │   ┌─────────────────────────────┐
│ significance    TEXT           │   │      places_fts (FTS5)      │
│ description     TEXT           │──►│                             │
│ best_time       TEXT           │   │ Full-text index on:         │
│ latitude        REAL           │   │  name, state, city, type,   │
│ longitude       REAL           │   │  significance, description  │
│ rating          REAL           │   │                             │
│ image_url       TEXT           │   │ Sub-millisecond search      │
│ source          TEXT           │   └─────────────────────────────┘
│ ingested_at     TIMESTAMP      │
└────────────────────────────────┘
```

---

## 4. Request Flow

### 4.1 Authenticated API Request

```
Browser                    Flask                      Service              DB
  │                          │                           │                  │
  │  POST /api/v1/expenses   │                           │                  │
  │  Cookie: access_token    │                           │                  │
  │  X-CSRF-Token: ...       │                           │                  │
  │─────────────────────────►│                           │                  │
  │                          │                           │                  │
  │                     ┌────┴────┐                      │                  │
  │                     │Middleware│                      │                  │
  │                     │ - Log   │                      │                  │
  │                     │ - Timer │                      │                  │
  │                     └────┬────┘                      │                  │
  │                          │                           │                  │
  │                     ┌────┴─────────┐                 │                  │
  │                     │ @require_auth│                  │                  │
  │                     │ decode JWT   │                  │                  │
  │                     │ verify CSRF  │                  │                  │
  │                     │ set g.user_id│                  │                  │
  │                     └────┬─────────┘                 │                  │
  │                          │                           │                  │
  │                     ┌────┴──────┐                    │                  │
  │                     │ @limit_api│                    │                  │
  │                     │  30/min   │                    │                  │
  │                     └────┬──────┘                    │                  │
  │                          │                           │                  │
  │                     ┌────┴────────────┐              │                  │
  │                     │ Schema.load()   │              │                  │
  │                     │ validate+sanitize│              │                  │
  │                     └────┬────────────┘              │                  │
  │                          │                           │                  │
  │                          │  service.create(data)     │                  │
  │                          │──────────────────────────►│                  │
  │                          │                           │                  │
  │                          │                           │  session.add()   │
  │                          │                           │─────────────────►│
  │                          │                           │                  │
  │                          │                           │  session.commit()│
  │                          │                           │─────────────────►│
  │                          │                           │                  │
  │                          │     (True, result_dict)   │                  │
  │                          │◄──────────────────────────│                  │
  │                          │                           │                  │
  │  201 Created             │                           │                  │
  │  { success: true,        │                           │                  │
  │    data: {...} }         │                           │                  │
  │◄─────────────────────────│                           │                  │
```

### 4.2 Real-Time Chat Message with AI Mention

```
Browser              SocketIO           ChatService         Celery          Ollama
  │                     │                    │                 │               │
  │  chat:send          │                    │                 │               │
  │  { content:         │                    │                 │               │
  │  "@scout best       │                    │                 │               │
  │   places in Goa" }  │                    │                 │               │
  │────────────────────►│                    │                 │               │
  │                     │                    │                 │               │
  │                     │  send_message()    │                 │               │
  │                     │───────────────────►│                 │               │
  │                     │                    │                 │               │
  │                     │                    │─── save to DB   │               │
  │                     │                    │                 │               │
  │                     │                    │─── detect @scout│               │
  │                     │                    │                 │               │
  │                     │                    │  ai_task.delay() │              │
  │                     │                    │────────────────►│               │
  │                     │                    │                 │               │
  │                     │  chat:new_message  │                 │               │
  │◄────────────────────│  (user message)    │                 │               │
  │                     │                    │                 │               │
  │                     │                    │                 │  POST /api/   │
  │                     │                    │                 │  generate     │
  │                     │                    │                 │──────────────►│
  │                     │                    │                 │               │
  │                     │                    │                 │  AI response  │
  │                     │                    │                 │◄──────────────│
  │                     │                    │                 │               │
  │                     │                    │◄────────────────│               │
  │                     │                    │  save AI msg    │               │
  │                     │                    │                 │               │
  │                     │  chat:new_message  │                 │               │
  │◄────────────────────│  (scout response   │                 │               │
  │                     │   with place cards)│                 │               │
```

---

## 5. Authentication Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                      JWT + CSRF Double-Submit                        │
│                                                                      │
│   SIGNUP/LOGIN                                                       │
│   ┌──────┐    POST /auth/login    ┌──────────┐                      │
│   │Client│───────────────────────►│  Server  │                      │
│   │      │                        │          │                      │
│   │      │  Set-Cookie:           │  Verify  │                      │
│   │      │  access_token (httpOnly│  pwd     │                      │
│   │      │  secure, SameSite=Lax) │  Create  │                      │
│   │      │                        │  tokens  │                      │
│   │      │  Set-Cookie:           │          │                      │
│   │      │  refresh_token(httpOnly│          │                      │
│   │      │  secure, path=/refresh)│          │                      │
│   │      │                        │          │                      │
│   │      │  Body:                 │          │                      │
│   │      │  { csrf_token: "..." } │          │                      │
│   │      │◄───────────────────────│          │                      │
│   └──────┘                        └──────────┘                      │
│                                                                      │
│   PROTECTED REQUEST                                                  │
│   ┌──────┐    GET /api/v1/groups  ┌──────────┐                      │
│   │Client│───────────────────────►│  Server  │                      │
│   │      │  Cookie: access_token  │          │                      │
│   │      │  X-CSRF-Token: "..."   │  Decode  │                      │
│   │      │                        │  JWT     │                      │
│   │      │                        │  Match   │                      │
│   │      │  200 OK { data }       │  CSRF    │                      │
│   │      │◄───────────────────────│          │                      │
│   └──────┘                        └──────────┘                      │
│                                                                      │
│   TOKEN REFRESH (automatic, transparent)                             │
│   ┌──────┐   POST /auth/refresh   ┌──────────┐                     │
│   │Client│───────────────────────►│  Server  │                      │
│   │      │  Cookie: refresh_token │          │                      │
│   │      │                        │  Verify  │                      │
│   │      │  New access_token      │  session │                      │
│   │      │  New csrf_token        │  Rotate  │                      │
│   │      │◄───────────────────────│  tokens  │                      │
│   └──────┘                        └──────────┘                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Caching Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         CACHE LAYERS                                 │
│                                                                       │
│  LAYER 1: Browser (TanStack Query)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  In-Memory Cache                  IndexedDB Persister           │ │
│  │  ┌─────────────────────┐         ┌─────────────────────┐       │ │
│  │  │ staleTime: 5 min    │────────►│ maxAge: 60 min      │       │ │
│  │  │ gcTime: 30 min      │◄────────│ DB: tripraft-query  │       │ │
│  │  │                     │         │                     │       │ │
│  │  │ Invalidation:       │         │ Excluded:           │       │ │
│  │  │ - SocketIO events   │         │ - auth keys         │       │ │
│  │  │ - Mutation success  │         │ - realtime keys     │       │ │
│  │  │ - Window focus      │         │ - mutation keys     │       │ │
│  │  └─────────────────────┘         └─────────────────────┘       │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  LAYER 2: Server (Redis)                                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  @cache_response(ttl=config.CACHE_TTL_*)                        │ │
│  │                                                                   │ │
│  │  Key format: {prefix}:{user_id}:{route}:{query_hash}            │ │
│  │                                                                   │ │
│  │  ┌──────────────────┬────────┐                                   │ │
│  │  │ Endpoint         │  TTL   │                                   │ │
│  │  ├──────────────────┼────────┤                                   │ │
│  │  │ autocomplete     │ 3600s  │                                   │ │
│  │  │ place search     │ 1800s  │                                   │ │
│  │  │ user profile     │ 3600s  │                                   │ │
│  │  │ group list       │  300s  │                                   │ │
│  │  │ group detail     │  300s  │                                   │ │
│  │  │ chat messages    │   60s  │                                   │ │
│  │  │ balances         │  120s  │                                   │ │
│  │  └──────────────────┴────────┘                                   │ │
│  │                                                                   │ │
│  │  Invalidation: config-driven write-op → cache-key mapping        │ │
│  │  Fallback: if Redis down, bypass cache, hit DB directly          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 7. Background Processing

```
┌───────────────────────────────────────────────────────────────────────┐
│                    CELERY WORKER ARCHITECTURE                        │
│                                                                       │
│  ┌──────────────┐         ┌──────────────┐       ┌──────────────┐   │
│  │  Flask App   │  .delay()│  Redis       │       │  Celery      │   │
│  │  (Producer)  │─────────►│  Broker      │──────►│  Worker      │   │
│  │              │         │  Queue        │       │  (Consumer)  │   │
│  └──────────────┘         └──────────────┘       └──────┬───────┘   │
│                                                          │           │
│                           ┌──────────────────────────────┘           │
│                           │                                          │
│              ┌────────────┼────────────┬────────────┐               │
│              ▼            ▼            ▼            ▼               │
│  ┌───────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ email_tasks   │ │ ai_tasks │ │ chat     │ │ cleanup  │         │
│  │               │ │          │ │ _tasks   │ │ _tasks   │         │
│  │ - invitation  │ │ - scout  │ │ - enrich │ │ - expire │         │
│  │ - verify      │ │   mention│ │ - archive│ │   session│         │
│  │ - password    │ │ - process│ │          │ │ - old msg│         │
│  │   reset       │ │          │ │          │ │          │         │
│  └───────────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                       │
│  ┌───────────────┐ ┌───────────┐ ┌────────────────────────┐         │
│  │ crew_tasks    │ │ notify    │ │ analytics_tasks        │         │
│  │               │ │ _tasks    │ │                        │         │
│  │ - multi-turn  │ │ - push    │ │ - group_activity       │         │
│  │   conversation│ │ - digest  │ │ - expense_summary      │         │
│  │ - confirm     │ │           │ │                        │         │
│  │   action      │ │           │ │                        │         │
│  └───────────────┘ └───────────┘ └────────────────────────┘         │
│                                                                       │
│  BEAT SCHEDULE (periodic):                                           │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │ cleanup_expired_sessions  │ every 6 hours                 │      │
│  │ archive_old_messages      │ daily at 3:00 AM              │      │
│  │ refresh_materialized_views│ every 30 minutes              │      │
│  │ generate_daily_analytics  │ daily at 2:00 AM              │      │
│  │ send_digest_notifications │ daily at 9:00 AM              │      │
│  └───────────────────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 8. AI Agent Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                      AI AGENT SYSTEM                                 │
│                                                                       │
│  CONSENT GATE                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Every AI interaction checked against ai_consent table          │ │
│  │  User must opt-in per agent type before any LLM call            │ │
│  │  No data sent to AI without explicit user consent               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────────────────┐    ┌──────────────────────────┐       │
│  │     SCOUT AGENT          │    │     CREW AGENT           │       │
│  │──────────────────────────│    │──────────────────────────│       │
│  │ Trigger: @scout in chat  │    │ Trigger: @crew in chat   │       │
│  │                          │    │                          │       │
│  │ Flow:                    │    │ Flow:                    │       │
│  │ 1. Check consent         │    │ 1. Check consent         │       │
│  │ 2. Parse user query      │    │ 2. Load conversation     │       │
│  │ 3. Search travel DB      │    │    state (context window)│       │
│  │ 4. Search web (fallback) │    │ 3. Construct prompt      │       │
│  │ 5. Build LLM prompt      │    │ 4. Call LLM              │       │
│  │ 6. Call Ollama            │    │ 5. Parse output          │       │
│  │ 7. Validate JSON output  │    │ 6. Extract actions       │       │
│  │ 8. Return place cards    │    │ 7. Return cards +        │       │
│  │                          │    │    confirmable actions   │       │
│  │ Circuit Breaker:         │    │                          │       │
│  │ ┌──────┐  ┌──────┐      │    │ Actions require user     │       │
│  │ │Closed│─►│ Open │      │    │ confirmation before      │       │
│  │ │      │  │5 fail│      │    │ execution (e.g., add     │       │
│  │ │Normal│  │30s   │      │    │ place, create poll)      │       │
│  │ │ flow │  │wait  │      │    │                          │       │
│  │ │      │  │      │      │    │ Card Types:              │       │
│  │ │      │◄─│Half  │      │    │ - place_recommendation   │       │
│  │ │      │  │Open  │      │    │ - itinerary_suggestion   │       │
│  │ └──────┘  └──────┘      │    │ - poll_creation          │       │
│  └──────────────────────────┘    │ - budget_optimization   │       │
│                                  └──────────────────────────┘       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 9. Production Deployment

```
                        ┌──────────────────────┐
                        │   Cloudflare / CDN    │
                        │   SSL Termination     │
                        │   DDoS Protection     │
                        └──────────┬───────────┘
                                   │
                        ┌──────────┴───────────┐
                        │   Nginx Reverse      │
                        │   Proxy              │
                        │   - Static files     │
                        │   - WebSocket proxy  │
                        │   - Brotli compress  │
                        └──────────┬───────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                  │
        ┌────────┴──────┐  ┌──────┴──────┐  ┌───────┴──────┐
        │  Gunicorn     │  │  Gunicorn   │  │  Gunicorn    │
        │  Worker 1     │  │  Worker 2   │  │  Worker N    │
        │  (gevent)     │  │  (gevent)   │  │  (gevent)    │
        │               │  │             │  │              │
        │  Flask +      │  │  Flask +    │  │  Flask +     │
        │  SocketIO     │  │  SocketIO   │  │  SocketIO    │
        └───────┬───────┘  └──────┬──────┘  └───────┬──────┘
                │                 │                  │
                └─────────────────┼──────────────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                 │
          ┌──────┴──────┐ ┌──────┴──────┐ ┌───────┴──────┐
          │ PostgreSQL  │ │   Redis     │ │   Celery     │
          │  Primary    │ │ Cache +     │ │  Workers     │
          │  26 tables  │ │ Broker +    │ │  + Beat      │
          │  UUIDv7 PKs │ │ Sessions    │ │  Scheduler   │
          └─────────────┘ └─────────────┘ └──────────────┘
```

---

## 10. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary keys | UUIDv7 | Time-ordered, no central sequence, safe for distributed systems |
| Auth tokens | JWT in httpOnly cookies | XSS-immune token storage, automatic browser attachment |
| CSRF protection | Double-submit pattern | Stateless, no server-side CSRF state needed |
| Caching | Redis + IndexedDB | Server-side for shared data, client-side for offline capability |
| Real-time | Socket.IO (gevent) | Room-based events, automatic reconnection, fallback to polling |
| Background jobs | Celery + Redis | Proven Python task queue, Redis already available as broker |
| AI integration | Ollama (self-hosted) | No API costs, full data control, circuit breaker for resilience |
| Database | SQLite dev / PostgreSQL prod | Zero-config dev, production-grade in deployment |
| Frontend state | TanStack Query | Server-state management with caching, no Redux complexity |
| Code splitting | React.lazy + Suspense | Route-level splits reduce initial bundle by ~60% |
| Search | SQLite FTS5 | Sub-millisecond full-text search, no Elasticsearch dependency |
| Validation | Marshmallow schemas | Declarative, composable, automatic error messages |
| Rate limiting | Flask-Limiter + Redis | Per-operation granularity, distributed rate state |
| Error handling | Custom exception hierarchy | Typed errors map directly to HTTP status codes |

---

## 11. Non-Functional Requirements

| Requirement | Target | Implementation |
|------------|--------|----------------|
| Response time (P95) | < 200ms | Redis caching, DB indexes, connection pooling |
| Concurrent users | 1,000+ | Gevent workers, async I/O, connection pooling |
| Search latency | < 10ms | FTS5 index, pre-built trigram lookups |
| Cache hit ratio | > 70% | Dual-layer caching, aggressive staleTime |
| Uptime | 99.9% | Health checks, worker recycling, circuit breakers |
| Security | OWASP Top 10 | Input sanitization, CSRF, rate limiting, httpOnly cookies |
| Data integrity | ACID transactions | SQLAlchemy session management per service call |

---

## 12. Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND          │  BACKEND           │  INFRASTRUCTURE      │
│────────────────────┼────────────────────┼──────────────────────│
│  React 18.2        │  Python 3.11       │  Redis 7+            │
│  Vite 5            │  Flask 2.3         │  PostgreSQL 15+      │
│  TanStack Query 5  │  SQLAlchemy 2.0    │  Nginx               │
│  React Router 7    │  Celery 5.4        │  Gunicorn (gevent)   │
│  Socket.IO Client  │  Flask-SocketIO    │  Ollama (LLM)        │
│  Leaflet 1.9       │  Marshmallow 3.23  │  SMTP (email)        │
│  Recharts 3.6      │  PyJWT 2.10        │  Cloudflare (CDN)    │
│  jsPDF 4.0         │  bcrypt 5.0        │                      │
│  Lucide React      │  Alembic 1.18      │                      │
│                    │  pybreaker         │                      │
└─────────────────────────────────────────────────────────────────┘
```
