# TripRaft — High-Level System Architecture

## System Context

```
                         ┌───────────────────────────────────────┐
                         │            End Users                  │
                         │   (Browser / Future: Mobile App)      │
                         └───────────────┬───────────────────────┘
                                         │
                              HTTPS (443) │ WSS (WebSocket)
                                         │
                         ┌───────────────▼───────────────────────┐
                         │          Reverse Proxy / CDN          │
                         │     (Nginx / Cloudflare — future)     │
                         └───────────────┬───────────────────────┘
                                         │
                    ┌────────────────────┴─────────────────────┐
                    │                                          │
           ┌───────▼────────┐                        ┌────────▼────────┐
           │  Static Assets │                        │   API Gateway   │
           │  (Vite Build)  │                        │   /api/v1/*     │
           │  React SPA     │                        │   Flask App     │
           └────────────────┘                        └────────┬────────┘
                                                              │
                         ┌────────────────────────────────────┼──────────────────────┐
                         │                                    │                      │
                ┌────────▼────────┐               ┌──────────▼──────────┐   ┌───────▼───────┐
                │  Redis Cluster  │               │   Primary Database  │   │ Travel DB     │
                │                 │               │   (SQLite/Postgres) │   │ (Read-Only    │
                │  - Cache        │               │   tripraft.db       │   │  SQLite)      │
                │  - Session      │               │   26 tables         │   │  16k+ places  │
                │  - Rate Limits  │               │   UUIDv7 PKs        │   │  FTS5 index   │
                │  - Celery Broker│               └─────────────────────┘   └───────────────┘
                └───────┬────────┘
                        │
               ┌────────▼────────┐
               │  Celery Workers  │
               │  + Beat Schedule │
               │                  │
               │  7 task modules  │
               │  5 periodic jobs │
               └────────┬────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
    ┌──────▼──────┐ ┌──▼───────┐ ┌──▼──────────┐
    │ SMTP Server │ │ Ollama   │ │ External    │
    │ (Email)     │ │ (Local   │ │ APIs        │
    │             │ │  LLM)    │ │ Ticketmaster│
    └─────────────┘ └──────────┘ │ Crew AI     │
                                 │ DuckDuckGo  │
                                 └─────────────┘
```

---

## Layered Architecture (Backend)

The backend follows a strict 5-layer architecture. Each layer only talks to the layer directly below it. No layer skipping.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                            │
│                                                                          │
│  app/api/v1/*.py        25 Blueprint files, 100+ endpoints              │
│  app/api/factory.py     Flask app factory (CORS, middleware, blueprints) │
│  app/api/middleware.py   Request/response logging, request IDs           │
│  app/api/health.py       Kubernetes health probes                        │
│  app/api/utils/          Response envelope helpers, validators           │
│                                                                          │
│  Responsibilities:                                                       │
│  - HTTP request parsing and response formatting                          │
│  - Authentication/authorization via decorators                           │
│  - Rate limiting                                                         │
│  - Input validation (delegates to schemas)                               │
│  - Response caching (decorator-based)                                    │
│                                                                          │
│  Convention:  @require_auth > @require_group_role > @limit_api > handler │
│  Response:    Always uses success_response() / error_response() envelope │
├──────────────────────────────────────────────────────────────────────────┤
│                           VALIDATION LAYER                               │
│                                                                          │
│  app/schemas/*.py        15 schema files, 52+ Pydantic/Marshmallow      │
│                                                                          │
│  Responsibilities:                                                       │
│  - Request body validation (type, length, format)                        │
│  - Response serialization contracts                                      │
│  - Email format validation (EmailStr)                                    │
│  - Field constraints (min/max length, ranges, enums)                     │
├──────────────────────────────────────────────────────────────────────────┤
│                            SERVICE LAYER                                 │
│                                                                          │
│  app/services/*.py       26 service files, all @staticmethod             │
│                                                                          │
│  Responsibilities:                                                       │
│  - Business logic orchestration                                          │
│  - Cross-domain coordination (e.g., group + expenses)                    │
│  - Transaction boundaries (commit/rollback)                              │
│  - AI agent processing                                                   │
│  - External API integration                                              │
│                                                                          │
│  Convention:  All methods return Tuple[bool, Dict]                       │
│               Stateless — no instance variables                          │
│               Uses get_db_session() context manager                      │
├──────────────────────────────────────────────────────────────────────────┤
│                            DOMAIN LAYER                                  │
│                                                                          │
│  app/domain/users/       User, UserSession, AuditLog                     │
│  app/domain/expenses/    Group, Expense, Settlement, Balance, etc.       │
│  app/domain/group_planner/  TravelGroup, Place, Poll, Chat, Vault, etc. │
│  app/domain/ai/          AIConsent, AIPreferenceProfile, AIAgentLog      │
│  app/domain/places/      DTOs + query wrappers for travel reference DB   │
│                                                                          │
│  Responsibilities:                                                       │
│  - Entity definitions (SQLAlchemy ORM models)                            │
│  - Relationships and constraints                                         │
│  - to_dict() serialization                                               │
│  - Repository pattern for complex queries                                │
│                                                                          │
│  Convention:  UUIDv7 primary keys, created_at/updated_at timestamps      │
│               Soft deletes (is_deleted flag, never hard delete)           │
│               back_populates for all relationships                       │
├──────────────────────────────────────────────────────────────────────────┤
│                         INFRASTRUCTURE LAYER                             │
│                                                                          │
│  app/infrastructure/db/        SQLAlchemy engine, sessions, UUIDv7       │
│  app/infrastructure/auth/      JWT, bcrypt, decorators                   │
│  app/infrastructure/cache/     Redis client, cache decorators            │
│  app/infrastructure/email/     SMTP client, email config                 │
│  app/infrastructure/realtime/  Flask-SocketIO, event handlers            │
│  app/infrastructure/llm/       Ollama client, prompt templates           │
│  app/infrastructure/search/    DuckDuckGo web search fallback            │
│  app/core/                     Config, exceptions, logging, security     │
│                                                                          │
│  Responsibilities:                                                       │
│  - Database connection management                                        │
│  - External service integration                                          │
│  - Token creation/verification                                           │
│  - Cache read/write/invalidate                                           │
│  - Circuit breakers and retry logic                                      │
│  - Structured logging                                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            REACT APPLICATION                             │
│                                                                          │
│  React 18.2 + React Router 7 + TanStack Query 5                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                         ROUTING LAYER                              │  │
│  │  App.jsx — React.lazy() code splitting with Suspense boundaries   │  │
│  │                                                                    │  │
│  │  Public:  /, /about, /contact, /pricing, /login, /signup          │  │
│  │  Public:  /places, /place-search, /trip-planner                   │  │
│  │  Auth:    /expenses, /group-planner/:groupId, /analytics          │  │
│  │  Special: /invitation/:id, /accept-invitation                     │  │
│  │                                                                    │  │
│  │  ProtectedRoute wraps auth-required routes                        │  │
│  │  InactivityTracker (15-min auto-logout) wraps entire app          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                       STATE MANAGEMENT                             │  │
│  │                                                                    │  │
│  │  Server State:  TanStack Query (react-query)                      │  │
│  │    - 5min staleTime, 30min gcTime                                 │  │
│  │    - IndexedDB persistence (60min TTL)                            │  │
│  │    - Event-driven invalidation on socket updates                  │  │
│  │    - Optimistic mutations with rollback                           │  │
│  │                                                                    │  │
│  │  Auth State:  React Context (AuthContext.jsx)                     │  │
│  │    - currentUser, signIn/signOut, token management                │  │
│  │    - Token refresh on activity, auto-logout on inactivity         │  │
│  │                                                                    │  │
│  │  Local State:  React useState/useReducer (component-level)        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    FEATURE COMPONENTS (6 domains)                  │  │
│  │                                                                    │  │
│  │  src/components/placeSearch/    Place discovery UI                 │  │
│  │  src/components/tripPlanner/    AI trip generation UI              │  │
│  │  src/components/groupPlanner/   Collaborative planning (6 tabs)   │  │
│  │  src/components/expenses/       Expense tracking UI               │  │
│  │  src/components/auth/           Login / Signup / Protected routes  │  │
│  │  src/components/pages/          Static pages (Home, About, etc.)  │  │
│  │  src/components/common/         Shared UI (Toast, Avatar, etc.)   │  │
│  │  src/components/layout/         Header, Footer                    │  │
│  │                                                                    │  │
│  │  Each feature folder:  jsx/ (components), css/ (styles)           │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      HOOKS LAYER                                   │  │
│  │                                                                    │  │
│  │  useExpenseQuery.js       Expense CRUD + groups + settlements     │  │
│  │  useGroupPlannerQuery.js  Groups + places + polls + members       │  │
│  │  useChatQuery.js          Infinite scroll chat + mutations        │  │
│  │  useTripPlannerQuery.js   AI trip generation mutation             │  │
│  │  usePlaceSearchQuery.js   Search + autocomplete + detail          │  │
│  │  useAiConsentQuery.js     AI consent get/submit/revoke            │  │
│  │  useGroupSocket.js        Real-time group events                  │  │
│  │  useChatSocket.js         Real-time chat events                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      SERVICE LAYER                                 │  │
│  │                                                                    │  │
│  │  apiClient.js            HTTP client (JWT, CSRF, retries)         │  │
│  │  expenseApi.js           Expense REST calls                       │  │
│  │  groupPlannerApi.js      Group planner REST calls                 │  │
│  │  chatApi.js              Chat REST calls                          │  │
│  │  tripPlannerService.js   Trip generation REST calls               │  │
│  │  placeSearchService.js   Place search REST calls                  │  │
│  │  aiConsentApi.js         AI consent REST calls                    │  │
│  │  sqlAuthService.js       Auth abstraction (login, register, etc.) │  │
│  │  pdfExportService.js     Client-side PDF generation (jsPDF)       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow (Example: Send Chat Message)

```
Browser                   Flask                    Service              Database
  │                         │                        │                    │
  │  POST /api/v1/gp/      │                        │                    │
  │  groups/{id}/chat       │                        │                    │
  │ ───────────────────────>│                        │                    │
  │  (JWT + CSRF headers)   │                        │                    │
  │                         │                        │                    │
  │                    ┌────┴────┐                   │                    │
  │                    │Middleware│                   │                    │
  │                    │ - Log   │                   │                    │
  │                    │ - ReqID │                   │                    │
  │                    └────┬────┘                   │                    │
  │                         │                        │                    │
  │                    ┌────┴────────┐               │                    │
  │                    │@require_auth│               │                    │
  │                    │ verify JWT  │               │                    │
  │                    │ set g.user_id               │                    │
  │                    └────┬────────┘               │                    │
  │                         │                        │                    │
  │                    ┌────┴──────────────┐         │                    │
  │                    │@require_group_role│         │                    │
  │                    │ verify membership │         │                    │
  │                    └────┬──────────────┘         │                    │
  │                         │                        │                    │
  │                    ┌────┴───────┐                │                    │
  │                    │@limit_api  │                │                    │
  │                    │ check rate │                │                    │
  │                    └────┬───────┘                │                    │
  │                         │                        │                    │
  │                         │  ChatService           │                    │
  │                         │  .send_message()       │                    │
  │                         │───────────────────────>│                    │
  │                         │                        │  INSERT INTO       │
  │                         │                        │  chat_messages     │
  │                         │                        │──────────────────>│
  │                         │                        │                    │
  │                         │                        │  Check @mentions   │
  │                         │                        │  (@scout? @crew?)  │
  │                         │                        │                    │
  │                         │                        │  If @scout:        │
  │                         │                        │  process_scout_    │
  │                         │                        │  mention.delay()   │
  │                         │                        │  ──> Celery task   │
  │                         │                        │                    │
  │                         │  (success, result)     │                    │
  │                         │<───────────────────────│                    │
  │                         │                        │                    │
  │                    SocketIO emit                  │                    │
  │                    'chat:message'                 │                    │
  │                    to room group:{id}             │                    │
  │                         │                        │                    │
  │  201 Created            │                        │                    │
  │  {data: message_dict}   │                        │                    │
  │ <───────────────────────│                        │                    │
  │                         │                        │                    │
  │  WSS 'chat:message'     │                        │                    │
  │ <═══════════════════════│  (all group members)   │                    │
  │                         │                        │                    │
  │  QueryClient.invalidate │                        │                    │
  │  ('chat', groupId)      │                        │                    │
  │  UI updates instantly    │                        │                    │
```

---

## Database Schema Overview

### Primary Database (tripraft.db / PostgreSQL)

```
┌─────────────────────┐
│       users          │
│─────────────────────│        ┌─────────────────────┐
│ id (UUIDv7) PK      │───────>│    user_sessions     │
│ email (unique, idx)  │        │─────────────────────│
│ password_hash        │        │ id (UUIDv7) PK      │
│ display_name         │        │ user_id FK           │
│ is_verified          │        │ refresh_token        │
│ created_at           │        │ device_info          │
│ updated_at           │        │ expires_at           │
└──────┬──────────────┘        └─────────────────────┘
       │
       │ (user participates in groups via membership tables)
       │
       ├──────────────────────────────────────────────┐
       │                                              │
       ▼                                              ▼
┌─────────────────────┐                    ┌─────────────────────────┐
│  EXPENSE ENGINE      │                    │  GROUP PLANNER           │
│─────────────────────│                    │─────────────────────────│
│                      │                    │                          │
│ ┌─────────────┐     │                    │ ┌─────────────────┐     │
│ │   groups     │     │                    │ │  travel_groups   │     │
│ │ (expense)    │     │    linked via      │ │                  │     │
│ │ id, name,    │◄────┼────────────────────┤ │ id, name, dest,  │     │
│ │ currency     │     │  expense_group_id  │ │ start/end_date,  │     │
│ └──────┬───────┘     │                    │ │ budget, status   │     │
│        │             │                    │ └────────┬─────────┘     │
│        ▼             │                    │          │               │
│ ┌──────────────┐     │                    │ ┌────────▼─────────┐    │
│ │group_members │     │                    │ │  trip_members     │    │
│ │ user_id FK   │     │                    │ │  user_id FK       │    │
│ │ role         │     │                    │ │  role (admin/     │    │
│ │ joined_at    │     │                    │ │   member)         │    │
│ └──────────────┘     │                    │ └──────────────────┘    │
│        │             │                    │          │               │
│        ▼             │                    │          ▼               │
│ ┌──────────────┐     │                    │ ┌──────────────────┐    │
│ │  expenses    │     │                    │ │     places        │    │
│ │ id, amount,  │     │                    │ │ name, lat, lng,   │    │
│ │ description, │     │                    │ │ visit_date,       │    │
│ │ category,    │     │                    │ │ category, notes   │    │
│ │ paid_by FK   │     │                    │ │ added_by FK       │    │
│ │ split_type   │     │                    │ └─────────┬────────┘    │
│ │ is_deleted   │     │                    │           │             │
│ └──────┬───────┘     │                    │           ▼             │
│        │             │                    │ ┌──────────────────┐    │
│        ▼             │                    │ │  place_votes     │    │
│ ┌──────────────┐     │                    │ │  user_id FK      │    │
│ │expense_splits│     │                    │ │  vote (up/down)  │    │
│ │ user_id FK   │     │                    │ └──────────────────┘    │
│ │ amount       │     │                    │                         │
│ │ percentage   │     │                    │ ┌──────────────────┐    │
│ └──────────────┘     │                    │ │     polls        │    │
│        │             │                    │ │ question, type,  │    │
│        ▼             │                    │ │ expires_at       │    │
│ ┌──────────────┐     │                    │ └─────────┬────────┘    │
│ │ settlements  │     │                    │           ▼             │
│ │ payer FK     │     │                    │ ┌──────────────────┐    │
│ │ payee FK     │     │                    │ │  poll_votes      │    │
│ │ amount       │     │                    │ │  user_id FK      │    │
│ └──────────────┘     │                    │ │  option_index    │    │
│        │             │                    │ └──────────────────┘    │
│        ▼             │                    │                         │
│ ┌──────────────┐     │                    │ ┌──────────────────┐    │
│ │group_balances│     │                    │ │ checklist_items  │    │
│ │ user_id FK   │     │                    │ │ title, priority, │    │
│ │ balance      │     │                    │ │ assigned_to FK,  │    │
│ │ (Decimal)    │     │                    │ │ is_completed     │    │
│ └──────────────┘     │                    │ └──────────────────┘    │
│                      │                    │                         │
│ ┌──────────────┐     │                    │ ┌──────────────────┐    │
│ │ invitations  │     │                    │ │  chat_messages   │    │
│ │ (expense)    │     │                    │ │ sender_id FK,    │    │
│ │ email, status│     │                    │ │ content, type,   │    │
│ │ expires_at   │     │                    │ │ metadata (JSON)  │    │
│ └──────────────┘     │                    │ └──────────────────┘    │
│                      │                    │                         │
│ ┌──────────────┐     │                    │ ┌──────────────────┐    │
│ │expense_history│    │                    │ │  trip_invitations │    │
│ │ (audit trail)│     │                    │ │  email, status,   │    │
│ └──────────────┘     │                    │ │  expires_at       │    │
│                      │                    │ └──────────────────┘    │
└─────────────────────┘                    │                         │
                                           │ ┌──────────────────┐    │
                                           │ │ vault_documents   │    │
                                           │ │ filename, path,   │    │
                                           │ │ uploaded_by FK    │    │
                                           │ └──────────────────┘    │
                                           │                         │
                                           │ ┌──────────────────┐    │
                                           │ │group_activities   │    │
                                           │ │ action, actor FK, │    │
                                           │ │ metadata (JSON)   │    │
                                           │ └──────────────────┘    │
                                           │                         │
                                           │ ┌──────────────────┐    │
                                           │ │ notifications     │    │
                                           │ │ user_id FK, type, │    │
                                           │ │ is_read, data     │    │
                                           │ └──────────────────┘    │
                                           │                         │
                                           │ ┌──────────────────┐    │
                                           │ │itinerary_documents│   │
                                           │ │ content (JSON),    │   │
                                           │ │ version            │   │
                                           │ └──────────────────┘    │
                                           └─────────────────────────┘

┌─────────────────────────┐
│       AI MODULE          │
│─────────────────────────│
│ ┌──────────────────┐    │
│ │  ai_consent      │    │
│ │  group_id FK,    │    │
│ │  user_id FK,     │    │
│ │  consented (bool)│    │
│ └──────────────────┘    │
│ ┌──────────────────┐    │
│ │ai_preference_    │    │
│ │profile           │    │
│ │ user_id FK,      │    │
│ │ preferences JSON │    │
│ └──────────────────┘    │
│ ┌──────────────────┐    │
│ │  ai_agent_log    │    │
│ │  agent_type,     │    │
│ │  input, output,  │    │
│ │  latency_ms      │    │
│ └──────────────────┘    │
└─────────────────────────┘
```

### Travel Reference Database (travel_data_complete.db — Read-Only)

```
┌─────────────┐     ┌──────────┐     ┌─────────┐     ┌──────────────┐
│  countries   │────>│  states   │────>│  cities  │────>│   places     │
│  82 records  │     │           │     │          │     │  16k+ records│
│  name, code  │     │  name     │     │  name,   │     │  name, desc, │
│              │     │  country_ │     │  state_  │     │  lat, lng,   │
│              │     │  id FK    │     │  id FK   │     │  rating,     │
└──────────────┘     └──────────┘     └──────────┘     │  cost, tags, │
                                                        │  category    │
                                                        └──────┬───────┘
                                                               │
                                                     ┌─────────┴───────┐
                                                     │                 │
                                              ┌──────▼──────┐  ┌──────▼──────┐
                                              │   photos     │  │opening_hours│
                                              │  url, credit │  │ day, open,  │
                                              │              │  │ close       │
                                              └─────────────┘  └─────────────┘

FTS5 Virtual Table: places_fts (full-text search on name, description, tags)
```

---

## Authentication Flow

```
┌────────────┐                    ┌────────────┐                ┌──────────┐
│   Browser   │                    │   Flask     │                │ Database │
└──────┬─────┘                    └──────┬─────┘                └────┬─────┘
       │                                 │                           │
       │  POST /auth/signup              │                           │
       │  {email, password, name}        │                           │
       │────────────────────────────────>│                           │
       │                                 │  Validate schema          │
       │                                 │  hash_password(bcrypt 12) │
       │                                 │  INSERT user              │
       │                                 │──────────────────────────>│
       │                                 │  CREATE session           │
       │                                 │──────────────────────────>│
       │                                 │  create_access_token()    │
       │                                 │  create_refresh_token()   │
       │                                 │                           │
       │  Set-Cookie: access (httpOnly)  │                           │
       │  Set-Cookie: refresh (httpOnly) │                           │
       │  Body: {user, tokens}           │                           │
       │<────────────────────────────────│                           │
       │                                 │                           │
       │  --- 15 MINUTES LATER ---       │                           │
       │                                 │                           │
       │  POST /auth/refresh             │                           │
       │  Cookie: refresh_token          │                           │
       │────────────────────────────────>│                           │
       │                                 │  verify refresh token     │
       │                                 │  check session exists     │
       │                                 │──────────────────────────>│
       │                                 │  rotate refresh token     │
       │                                 │──────────────────────────>│
       │                                 │  new access + refresh     │
       │  Set-Cookie: new tokens         │                           │
       │<────────────────────────────────│                           │
       │                                 │                           │
       │  --- PROTECTED REQUEST ---      │                           │
       │                                 │                           │
       │  GET /api/v1/gp/groups          │                           │
       │  Cookie: access_token           │                           │
       │  X-CSRF-Token: {token}          │                           │
       │────────────────────────────────>│                           │
       │                                 │  @require_auth            │
       │                                 │  1. Extract token         │
       │                                 │     (cookie or Bearer)    │
       │                                 │  2. verify_token()        │
       │                                 │  3. Check user exists     │
       │                                 │──────────────────────────>│
       │                                 │  4. Set g.user_id         │
       │                                 │  5. Set g.user_email      │
       │                                 │  6. Proceed to route      │
       │                                 │                           │
       │  200 OK {data: [...groups]}     │                           │
       │<────────────────────────────────│                           │
```

---

## Caching Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND CACHE (Browser)                         │
│                                                                      │
│  TanStack Query Cache                                                │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  In-Memory Cache                                     │           │
│  │  staleTime: 5 min    gcTime: 30 min                  │           │
│  │  Keys: ['groups', userId], ['chat', groupId], etc.   │           │
│  └──────────────────┬───────────────────────────────────┘           │
│                     │ persist/restore                                │
│  ┌──────────────────▼───────────────────────────────────┐           │
│  │  IndexedDB Persister                                  │           │
│  │  maxAge: 60 min                                       │           │
│  │  Excludes: auth, tokens, websocket keys               │           │
│  │  Survives page refresh, reduces API calls ~70%        │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                      │
│  Cache Invalidation Triggers:                                        │
│  1. Socket event (place:added, chat:message, etc.)                   │
│  2. Mutation success (optimistic update + server confirm)            │
│  3. Window focus (stale data refetch)                                │
│  4. Manual invalidation (user action)                                │
└──────────────────────────────────────────────────────────────────────┘

                              │ HTTP Request (on cache miss/stale)
                              ▼

┌──────────────────────────────────────────────────────────────────────┐
│                      BACKEND CACHE (Redis)                           │
│                                                                      │
│  @cache_response Decorator                                           │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  ETag-based (If-None-Match → 304 Not Modified)       │           │
│  │  Key: prefix:user_id:route_params:query_hash         │           │
│  │  TTLs (from config, 25 distinct values):              │           │
│  │    - User profile: 3600s (1 hour)                     │           │
│  │    - Group list: 300s (5 min)                         │           │
│  │    - Place search: 1800s (30 min)                     │           │
│  │    - Chat messages: 60s (1 min)                       │           │
│  │    - Autocomplete: 3600s (1 hour)                     │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                      │
│  Cache Invalidation (pattern-based):                                 │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  On expense create → invalidate: expense:*, balance:* │           │
│  │  On place add → invalidate: places:group_id:*         │           │
│  │  On group update → invalidate: group:id:*, groups:*   │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                      │
│  Graceful: If Redis down → skip cache, serve from DB directly       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Real-time Communication

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Client A   │  │  Client B   │  │  Client C   │
│  (browser)  │  │  (browser)  │  │  (browser)  │
└──────┬─────┘  └──────┬─────┘  └──────┬─────┘
       │               │               │
       │  WSS connect  │  WSS connect  │  WSS connect
       │  + JWT auth   │  + JWT auth   │  + JWT auth
       │               │               │
       ▼               ▼               ▼
┌──────────────────────────────────────────────┐
│           Flask-SocketIO Server               │
│                                               │
│  Rooms:                                       │
│    group:{group_id}  ← All group members     │
│                                               │
│  Events (Client → Server):                    │
│    join_group    │ leave_group                 │
│    chat:send     │ place:add                   │
│    poll:vote     │ checklist:toggle            │
│                                               │
│  Events (Server → Client):                    │
│    presence:update  │ chat:message             │
│    place:added      │ place:voted              │
│    poll:voted       │ checklist:toggled        │
│    member:joined    │ member:left              │
│    itinerary:updated│ typing:start/stop        │
│                                               │
│  Auth: JWT verified on handshake              │
│  Rooms: Membership verified before join       │
└──────────────────────────────────────────────┘
```

---

## Background Processing (Celery)

```
┌─────────────────────────────────────────────────────────────────┐
│                     CELERY ARCHITECTURE                          │
│                                                                  │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐   │
│  │ Flask App   │     │ Redis Broker  │     │ Celery Workers │   │
│  │ (producer)  │────>│ (message bus) │────>│ (consumers)    │   │
│  └─────────────┘     └──────────────┘     └────────────────┘   │
│                                                                  │
│  Task Modules:                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ email_tasks.py         │ Send invitation, verification, │    │
│  │                        │ password reset, expense notif.  │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ notification_tasks.py  │ WebSocket notification delivery │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ chat_tasks.py          │ Message archival, AI mentions   │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ ai_tasks.py            │ Scout agent processing,         │    │
│  │                        │ chat summary, log cleanup       │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ crew_tasks.py          │ Crew agent execution            │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ cleanup_tasks.py       │ Session expiry, record archival │    │
│  ├────────────────────────┼─────────────────────────────────┤    │
│  │ analytics_tasks.py     │ Cache warmup, metrics aggregation│   │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Beat Schedule (Periodic):                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Every 6h   │ Search cache warmup                     │       │
│  │ Every 1h   │ Expired session cleanup                 │       │
│  │ Every 24h  │ Daily metrics aggregation               │       │
│  │ Every 24h  │ Soft-deleted record archival            │       │
│  │ Every 7d   │ AI agent log purge                      │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  Resilience:                                                     │
│  - Retry: exponential backoff (60s → 600s max)                  │
│  - Max retries: 3 per task                                       │
│  - Soft timeout: 120s, hard timeout: 180s                        │
│  - Worker recycling: every 1000 tasks                            │
│  - Dead-letter queue: redis:celery:dead_letters                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## AI Agent Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        AI AGENT SYSTEM                                │
│                                                                       │
│  Trigger: User types "@scout" or "@crew" in group chat               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                    CONSENT GATE                              │     │
│  │  1. Check ai_consent table for group_id + user_id           │     │
│  │  2. If no consent → show ScoutConsentCard in chat           │     │
│  │  3. If consented → proceed to agent processing              │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                        │
│              ┌───────────────┴───────────────┐                       │
│              ▼                               ▼                       │
│  ┌───────────────────────┐     ┌───────────────────────────┐        │
│  │    SCOUT AGENT         │     │      CREW AGENT            │        │
│  │   (Local LLM)         │     │   (External Service)       │        │
│  │                        │     │                            │        │
│  │  Ollama Client         │     │  Crew AI API               │        │
│  │  ┌──────────────┐     │     │  ┌────────────────────┐   │        │
│  │  │ Circuit       │     │     │  │ HTTP POST to       │   │        │
│  │  │ Breaker       │     │     │  │ crew_api_url       │   │        │
│  │  │ (pybreaker)   │     │     │  │                    │   │        │
│  │  │ 5 failures →  │     │     │  │ Multi-turn         │   │        │
│  │  │ open 60s      │     │     │  │ conversation       │   │        │
│  │  └──────┬───────┘     │     │  │ state management   │   │        │
│  │         ▼              │     │  └────────┬───────────┘   │        │
│  │  ┌──────────────┐     │     │           │               │        │
│  │  │ Prompt        │     │     │           ▼               │        │
│  │  │ Templates     │     │     │  Response Types:          │        │
│  │  │ (Jinja2)      │     │     │  - Question card          │        │
│  │  └──────┬───────┘     │     │  - Confirm card            │        │
│  │         ▼              │     │  - Place suggestion card   │        │
│  │  ┌──────────────┐     │     │  - Success card            │        │
│  │  │ Output        │     │     │                            │        │
│  │  │ Validator     │     │     │  Confirmable Actions:      │        │
│  │  │ (JSON Schema) │     │     │  - Delete place            │        │
│  │  └──────┬───────┘     │     │  - Create poll             │        │
│  │         ▼              │     │  - Add event               │        │
│  │  Place suggestions     │     │  - Modify itinerary        │        │
│  │  rendered as chat      │     │                            │        │
│  │  message cards         │     │                            │        │
│  └───────────────────────┘     └───────────────────────────┘        │
│                                                                       │
│  Logging: All agent interactions → ai_agent_log table                │
│  Metrics: latency_ms, token_count, success/failure                   │
│  Cleanup: Agent logs purged every 7 days (Celery beat)               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture (Production Target)

```
┌───────────────────────────────────────────────────────────────────┐
│                        PRODUCTION STACK                            │
│                                                                    │
│  ┌─────────────────┐                                              │
│  │   Cloudflare     │  CDN + WAF + DDoS protection                │
│  │   (or Nginx)     │  SSL termination                            │
│  └────────┬────────┘                                              │
│           │                                                        │
│  ┌────────▼────────┐  ┌──────────────────┐                        │
│  │  Frontend SPA    │  │  Gunicorn         │                        │
│  │  (Vite build)    │  │  + Flask-SocketIO │                        │
│  │  Static files    │  │                   │                        │
│  │  served by CDN   │  │  9-12 gevent      │                        │
│  │                   │  │  workers          │                        │
│  └──────────────────┘  │                   │                        │
│                         │  Worker recycling │                        │
│                         │  every 1000 reqs  │                        │
│                         └────────┬─────────┘                        │
│                                  │                                  │
│           ┌──────────────────────┼──────────────────────┐          │
│           │                      │                      │          │
│  ┌────────▼────────┐  ┌─────────▼────────┐  ┌─────────▼────────┐ │
│  │  PostgreSQL      │  │  Redis Cluster    │  │  Celery Workers  │ │
│  │                   │  │                   │  │  + Beat           │ │
│  │  - Materialized   │  │  - Session cache  │  │                   │ │
│  │    views          │  │  - Rate limits    │  │  3 workers        │ │
│  │  - Partitioned    │  │  - Celery broker  │  │  + 1 beat         │ │
│  │    tables         │  │  - Response cache │  │  scheduler        │ │
│  │  - JSONB columns  │  │                   │  │                   │ │
│  └──────────────────┘  └───────────────────┘  └───────────────────┘ │
│                                                                      │
│  ┌──────────────────┐  ┌───────────────────┐                        │
│  │  Ollama Server    │  │  SMTP Relay       │                        │
│  │  (Local LLM)     │  │  (SendGrid/SES)   │                        │
│  └──────────────────┘  └───────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **UUIDv7 primary keys** | Sortable (time-ordered), distributed-safe, no sequential ID exposure |
| **Dual database strategy** | Separate read-only travel data from transactional app data; different access patterns |
| **JWT in httpOnly cookies** | XSS-safe token storage; CSRF double-submit for mutation safety |
| **Celery for async** | Email, AI processing, cleanup are too slow for request cycle |
| **Circuit breaker for LLM** | Ollama/Crew may be down; app must function without AI |
| **IndexedDB persistence** | Reduces API calls ~70%; survives page refresh; improves perceived performance |
| **Soft deletes** | Audit trail; data recovery; compliance readiness |
| **Tuple[bool, Dict] returns** | Consistent service contract; no exception-based control flow in business logic |
| **Feature-based frontend folders** | Scales better than type-based (components/hooks/services); colocated concerns |
| **TanStack Query over Redux** | Server-state management is the primary need; Query handles caching, invalidation, mutations natively |
