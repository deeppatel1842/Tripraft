# Web Folder Comprehensive Audit Report

**Date:** 2026-02-10  
**Scope:** `web/backend/` and `web/frontend/src/`

---

## 1. COMPLETE FILE INVENTORY

### 1A. Backend Files (96 files)

```
web/backend/
├── .dockerignore
├── .env.example
├── .gitignore
├── .llm
├── .pylintrc
├── Dockerfile
├── email_config.py                    # Email notification toggle config
├── package.json                       # (Node — probably leftover / unused by Python)
├── package-lock.json                  # (Node — leftover)
├── pytest.ini
├── requirements.txt
├── run.py                             # Flask entry point (python run.py)
├── travel_data_complete.db            # ⚠ STALE COPY — real one is in database/
│
├── api/                               # Core Flask app package
│   ├── __init__.py                    # Exports create_app, get_config
│   ├── .llm
│   ├── app.py                         # Application factory + blueprint registration
│   ├── health.py                      # /api/health endpoints
│   ├── route_viewer.py                # /api/routes styled listing
│   ├── config/
│   │   ├── __init__.py                # Re-exports Config, get_config
│   │   └── settings.py                # Centralised Config class (env vars)
│   ├── middleware/
│   │   ├── __init__.py                # Exports init_request_logger
│   │   └── request_logger.py          # Before/after request logging
│   ├── models/
│   │   ├── __init__.py                # Barrel → PlacesModel, CitiesModel, etc.
│   │   └── places.py                  # Raw-SQL query models for travel_data_complete.db
│   ├── routes/
│   │   ├── __init__.py                # Barrel → locations_bp, trip_planner_bp
│   │   ├── locations.py               # /api/v1/locations/* (1042 lines, unified search)
│   │   └── trip_planner.py            # /api/trip-planner/* (429 lines, itinerary gen)
│   └── utils/
│       ├── __init__.py                # Barrel → error_response, init_database, etc.
│       ├── database.py                # DatabaseManager class (raw sqlite3)
│       ├── responses.py               # Standard JSON response helpers
│       └── validators.py              # Input validation helpers
│
├── cache/
│   ├── .llm
│   └── redis_client.py                # RedisClient singleton + @cached decorator
│
├── database/                          # ← THE ACTUAL DB FILES
│   ├── travel_data_complete.db        # 16,830 places, 889 cities, 837 states, 82 countries
│   └── tripraft.db                    # Users, expenses, groups, travel planning
│
├── expense_engine/                    # Splitwise-style expense splitting
│   ├── __init__.py                    # Package metadata (v2.0.0)
│   ├── .llm
│   ├── README.md
│   ├── auth/
│   │   ├── __init__.py                # Barrel → JWT + password + decorators
│   │   ├── decorators.py              # ⚠ SHIM — re-exports from shared_db.auth
│   │   ├── jwt_handler.py             # JWT create/verify/decode (HS256)
│   │   └── password.py                # bcrypt hash/verify
│   ├── database/
│   │   ├── __init__.py                # Barrel → all ORM models + init_db
│   │   ├── connection.py              # ⚠ SHIM — re-exports from shared_db.connection
│   │   └── models.py                  # Group, GroupMember, Expense, Settlement, etc.
│   ├── routes/
│   │   ├── __init__.py                # Barrel → auth_bp, groups_sql_bp, etc.
│   │   ├── auth_routes.py             # /api/expense/auth/*
│   │   ├── expenses_sql_routes.py     # /api/expense/expenses/*
│   │   ├── groups_sql_routes.py       # /api/expense/groups/*
│   │   ├── invitations_sql_routes.py  # /api/expense/invitations/*
│   │   └── settlements_sql_routes.py  # /api/expense/settlements/*
│   └── services/
│       ├── __init__.py                # Barrel → all service singletons
│       ├── auth_service.py            # Signup/login/token refresh logic
│       ├── email_service.py           # SendGrid email dispatch
│       ├── expense_service_sql.py     # CRUD + splitting logic
│       ├── group_service_sql.py       # Group CRUD + membership
│       ├── invitation_service_sql.py  # Invitation create/accept/decline
│       └── settlement_service_sql.py  # Settlement record + balance calc
│
├── Group_planner/                     # Collaborative trip planning
│   ├── __init__.py                    # Barrel → create_app, all blueprints (v3.0.0)
│   ├── .llm
│   ├── README.md
│   ├── app.py                         # ⚠ STANDALONE Flask factory (REDUNDANT)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py              # ⚠ SHIM — re-exports from shared_db.connection
│   │   └── models.py                  # TravelGroup, Place, Poll, TripMember, etc.
│   ├── routes/
│   │   ├── __init__.py                # Barrel → all GP blueprints
│   │   ├── checklist_routes.py        # /api/v2/group-planner/groups/<id>/checklist
│   │   ├── events_routes.py           # /api/v2/group-planner/groups/<id>/events
│   │   ├── groups_routes.py           # /api/v2/group-planner/groups/*
│   │   ├── invitations_routes.py      # /api/v2/group-planner/groups/<id>/invite
│   │   ├── optimized_routes.py        # /api/v2/group-planner/* (destinations, auth verify)
│   │   ├── places_routes.py           # /api/v2/group-planner/groups/<id>/places
│   │   └── polls_routes.py            # /api/v2/group-planner/groups/<id>/polls
│   └── services/
│       ├── __init__.py                # Barrel → all GP services
│       ├── checklist_service.py
│       ├── events_service.py
│       ├── group_service.py
│       ├── invitation_service.py
│       ├── place_service.py           # ⚠ CRUD for user-added places in a trip
│       ├── places_service.py          # ⚠ Destination lookup from travel_data_complete.db
│       └── poll_service.py
│
├── middleware/
│   ├── __init__.py                    # Exports limiter, RATE_LIMITS
│   ├── .llm
│   └── rate_limiter.py                # Flask-Limiter with user/IP bucketing
│
├── place_search/                      # Independent place search module
│   ├── __init__.py                    # Exports place_search_bp, PlaceSearchService
│   ├── .llm
│   ├── README.md
│   ├── config.py                      # PlaceSearchConfig (limits, sort fields)
│   ├── database.py                    # ⚠ SEPARATE DatabaseConnection (raw sqlite3)
│   ├── models.py                      # Dataclass models (Country, State, City, Place)
│   ├── routes.py                      # /api/v1/place-search/*
│   └── services.py                    # PlaceSearchService (search, autocomplete, detail)
│
└── shared_db/                         # Shared database infrastructure
    ├── __init__.py                    # Barrel → connection, models, auth
    ├── .llm
    ├── auth.py                        # ⚠ SINGLE SOURCE OF TRUTH for auth decorators
    ├── connection.py                  # ⚠ SINGLE SOURCE OF TRUTH for SQLAlchemy engine
    ├── models.py                      # Base, User, UserSession
    └── schemas.py                     # Marshmallow validation schemas
```

### 1B. Frontend Files (160 files)

```
web/frontend/src/
├── App.jsx                            # Root router — all routes defined here
├── main.jsx                           # ReactDOM entry with QueryClient
├── styles.css                         # Global overrides
│
├── components/
│   ├── .llm
│   ├── auth/
│   │   ├── index.js                   # Barrel
│   │   ├── css/
│   │   │   ├── Login.css
│   │   │   └── Signup.css
│   │   └── jsx/
│   │       ├── AuthPage.jsx           # Combined login/signup page
│   │       ├── InactivityTracker.jsx  # Auto-logout after 15 min
│   │       ├── Login.jsx
│   │       ├── ProtectedRoute.jsx     # Auth guard wrapper
│   │       └── Signup.jsx
│   │
│   ├── common/
│   │   ├── index.js                   # Barrel
│   │   ├── css/
│   │   │   ├── AnimatedBackground.css
│   │   │   ├── DestinationAutocomplete.css
│   │   │   ├── ErrorBoundary.css
│   │   │   ├── Toast.css
│   │   │   └── UserAvatar.css
│   │   └── jsx/
│   │       ├── AnimatedBackground.jsx # Gradient canvas effect
│   │       ├── DestinationAutocomplete.jsx  # Shared destination picker
│   │       ├── ErrorBoundary.jsx
│   │       ├── Toast.jsx              # Notification system
│   │       └── UserAvatar.jsx
│   │
│   ├── expenses/
│   │   ├── index.js                   # Barrel (16 components)
│   │   ├── css/
│   │   │   ├── ExpenseAnalytics.css
│   │   │   ├── ExpenseHistoryModal.css
│   │   │   ├── ExpenseManager.css
│   │   │   ├── SettlementHistoryModal.css
│   │   │   └── SettlementModal.css
│   │   └── jsx/
│   │       ├── ExpenseAnalytics.jsx   # Charts and visualisations
│   │       ├── ExpenseHistoryModal.jsx
│   │       ├── ExpenseManager.jsx     # Core expense CRUD UI
│   │       ├── ExpenseSummary.jsx
│   │       ├── GroupBalances.jsx
│   │       ├── GroupManager.jsx       # Group create/join UI
│   │       ├── GroupSummaryCards.jsx
│   │       ├── MemberSpending.jsx
│   │       ├── ModeToggle.jsx         # Personal vs Group toggle
│   │       ├── PendingInvitations.jsx
│   │       ├── PersonalTabbedView.jsx
│   │       ├── SettlementHistoryModal.jsx
│   │       ├── SettlementModal.jsx
│   │       ├── TabbedGroupView.jsx
│   │       ├── TransactionList.jsx
│   │       └── TransactionModal.jsx
│   │
│   ├── groupPlanner/
│   │   ├── index.js                   # Barrel (25+ components)
│   │   ├── css/ (18 CSS files, one per component)
│   │   └── jsx/
│   │       ├── CreateChecklistModal.jsx
│   │       ├── CreateGroupModal.jsx
│   │       ├── CreatePollModal.jsx
│   │       ├── EditBudgetModal.jsx
│   │       ├── EditChecklistModal.jsx
│   │       ├── EditItineraryModal.jsx
│   │       ├── EditPollModal.jsx
│   │       ├── GroupPlannerPage.jsx    # Main group planner view
│   │       ├── InvitationAcceptPage.jsx
│   │       ├── MapSection.jsx         # Leaflet map
│   │       ├── MembersModal.jsx
│   │       ├── MembersPanel.jsx
│   │       ├── NotesSection.jsx
│   │       ├── PendingModal.jsx
│   │       ├── PlacesSidebar.jsx
│   │       ├── RightSidebar.jsx
│   │       ├── SidebarComponent.jsx
│   │       ├── TripCommandCenter.jsx
│   │       └── TripPlannerHeader.jsx
│   │
│   ├── layout/
│   │   ├── index.js                   # Barrel
│   │   ├── css/
│   │   │   ├── Footer.css
│   │   │   └── Header.css
│   │   └── jsx/
│   │       ├── Footer.jsx
│   │       └── Header.jsx
│   │
│   ├── pages/
│   │   ├── index.js                   # Barrel
│   │   ├── css/ (8 CSS files)
│   │   └── jsx/
│   │       ├── About.jsx
│   │       ├── Analytics.jsx
│   │       ├── Contact.jsx
│   │       ├── ExpenseAnalytics.jsx   # ⚠ DUPLICATE name (see expenses/)
│   │       ├── ExpensePage.jsx        # Wrapper page for expense system
│   │       ├── GroupTripPage.jsx      # ⚠ UNUSED — GroupPlannerPage handles this
│   │       ├── HomePage.jsx
│   │       ├── InvitationAccept.jsx   # ⚠ UNUSED — SmartInvitationHandler replaced it
│   │       ├── Pricing.jsx
│   │       ├── SmartInvitationHandler.jsx
│   │       └── TripPlanner.jsx        # Solo trip planner page
│   │
│   ├── placeSearch/
│   │   ├── index.js                   # Barrel
│   │   ├── mockData.js               # Test data (should be in tests/)
│   │   ├── placeSearchService.js      # ⚠ RE-EXPORT SHIM from services/
│   │   ├── css/ (7 CSS files)
│   │   └── jsx/
│   │       ├── GroupedPlaceGrid.jsx
│   │       ├── PlaceCard.jsx
│   │       ├── PlaceDetailModal.jsx
│   │       ├── PlaceGrid.jsx
│   │       ├── PlaceSearchPage.jsx
│   │       ├── SearchBar.jsx
│   │       └── SearchSuggestions.jsx
│   │
│   └── tripPlanner/
│       ├── index.js                   # Barrel
│       ├── css/
│       │   └── TripPlanner.css
│       └── jsx/
│           ├── Checklist.jsx
│           ├── Icon.jsx
│           ├── Itinerary.jsx
│           ├── ItineraryStop.jsx
│           ├── SuggestedPlaces.jsx
│           ├── TripForm.jsx
│           ├── TripMap.jsx
│           ├── TripPlanCard.jsx
│           └── TripTips.jsx
│
├── config/
│   ├── .llm
│   ├── globalConfig.js                # API_BASE_URL, feature flags
│   └── groupPlannerConfig.js          # Group planner specific config
│
├── context/
│   ├── .llm
│   ├── AuthContext.jsx                # Global auth state (SQL JWT)
│   └── GroupPlannerContext.jsx         # Group planner state management
│
├── hooks/
│   ├── .llm
│   └── useExpenseQuery.js             # React Query hook for expenses
│
├── lib/
│   ├── .llm
│   ├── indexedDBPersister.js           # IndexedDB for React Query cache
│   └── queryClientPersist.js           # React Query persistence setup
│
├── services/
│   ├── .llm
│   ├── expenseApi.js                  # ExpenseApiService class
│   ├── groupPlannerApi.js             # GroupPlannerApiService class
│   ├── groupPlannerService.js         # ⚠ RE-EXPORT SHIM → groupPlannerApi.js
│   ├── pdfExportService.js            # jsPDF report generation
│   ├── placeSearchService.js          # Place search API client
│   ├── sqlAuthService.js              # JWT auth service (login/signup/refresh)
│   └── tripPlannerService.js          # Trip planner API client
│
├── styles/
│   └── global.css                     # Global CSS variables and resets
│
└── utils/
    ├── .llm
    ├── apiClient.js                   # Generic fetch wrapper with logging
    ├── apiLogger.js                   # Console log formatting for API calls
    └── timezoneUtils.js               # Timezone conversion helpers
```

---

## 2. MODULE PURPOSE SUMMARY

### Backend Modules

| Module | Purpose | Database | Auth |
|--------|---------|----------|------|
| **api/** | Flask app factory, locations API, trip planner | `travel_data_complete.db` (raw sqlite3) | None (public) |
| **expense_engine/** | Splitwise-style expense splitting (groups, expenses, settlements) | `tripraft.db` (SQLAlchemy via shared_db) | JWT via shared_db.auth |
| **Group_planner/** | Collaborative trip planning (places, polls, checklists, events) | `tripraft.db` (SQLAlchemy via shared_db) | JWT via shared_db.auth |
| **place_search/** | Independent place search with filters & autocomplete | `travel_data_complete.db` (raw sqlite3) | None (public) |
| **shared_db/** | Shared SQLAlchemy engine, User model, auth decorators | `tripraft.db` | JWT + Firebase fallback |
| **cache/** | Redis caching with graceful fallback | N/A | N/A |
| **middleware/** | Rate limiting (Flask-Limiter) | N/A | N/A |

### Frontend Modules

| Module | Purpose |
|--------|---------|
| **components/auth/** | Login, Signup, AuthPage, ProtectedRoute, InactivityTracker |
| **components/common/** | Shared UI: ErrorBoundary, Toast, UserAvatar, AnimatedBackground, DestinationAutocomplete |
| **components/expenses/** | Full expense management UI (16 components) |
| **components/groupPlanner/** | Collaborative trip planning UI (19 components) |
| **components/layout/** | Header, Footer |
| **components/pages/** | Top-level page wrappers (11 components) |
| **components/placeSearch/** | Place search & explore UI (7 components) |
| **components/tripPlanner/** | Solo trip itinerary UI (9 components) |
| **services/** | API client classes for each backend module |
| **context/** | AuthContext (global auth), GroupPlannerContext |
| **hooks/** | useExpenseQuery (React Query) |
| **lib/** | IndexedDB persister for React Query cache |
| **config/** | globalConfig, groupPlannerConfig |
| **utils/** | apiClient, apiLogger, timezoneUtils |

---

## 3. IDENTIFIED DUPLICATES AND REDUNDANCIES

### 3A. Database Connections (CRITICAL - 5 SEPARATE CONNECTION PATTERNS)

| # | File | Type | Target DB | Pattern |
|---|------|------|-----------|---------|
| 1 | `shared_db/connection.py` | **SOURCE OF TRUTH** | `tripraft.db` | SQLAlchemy engine + scoped session |
| 2 | `expense_engine/database/connection.py` | Shim | Re-exports #1 | Adds `reset_db()` |
| 3 | `Group_planner/database/connection.py` | Shim | Re-exports #1 | Adds `init_db()` with local model import |
| 4 | `api/utils/database.py` | **INDEPENDENT** | `travel_data_complete.db` | Raw sqlite3 `DatabaseManager` class |
| 5 | `place_search/database.py` | **INDEPENDENT** | `travel_data_complete.db` | Raw sqlite3 `DatabaseConnection` class |
| 6 | `api/routes/trip_planner.py` | **INLINE** | `travel_data_complete.db` | Raw sqlite3 `_get_connection()` inside route file |
| 7 | `Group_planner/services/places_service.py` | **INLINE** | `travel_data_complete.db` | Raw sqlite3 `get_connection()` inside service |

**Verdict:** `#4`, `#5`, `#6`, and `#7` all independently connect to the same `travel_data_complete.db` with nearly identical `sqlite3.connect()` + `row_factory = sqlite3.Row` boilerplate. These should be consolidated into a single read-only connection manager.

---

### 3B. Authentication (2 LAYERS, WELL CONSOLIDATED)

| # | File | Role |
|---|------|------|
| 1 | `shared_db/auth.py` | **SOURCE OF TRUTH** — `require_auth`, `optional_auth`, `get_current_user` |
| 2 | `expense_engine/auth/decorators.py` | **SHIM** — re-exports from `shared_db.auth` |
| 3 | `expense_engine/auth/jwt_handler.py` | JWT token create/verify (used by `shared_db/auth.py`) |
| 4 | `expense_engine/auth/password.py` | bcrypt password utilities |

**Verdict:** Auth is reasonably consolidated. The `expense_engine/auth/decorators.py` shim is harmless for backward compat. However, `jwt_handler.py` and `password.py` logically belong in `shared_db/` since auth is shared across both engines.

---

### 3C. Model Definitions (3 MODEL LAYERS)

| # | File | Models | Base |
|---|------|--------|------|
| 1 | `shared_db/models.py` | `User`, `UserSession`, `Base` | Declarative Base (SQLAlchemy) |
| 2 | `expense_engine/database/models.py` | `Group`, `GroupMember`, `Expense`, `ExpenseSplit`, `Settlement`, `GroupBalance`, `Invitation`, `ExpenseHistory` | Imports Base from #1 |
| 3 | `Group_planner/database/models.py` | `TravelGroup`, `TripMember`, `Place`, `PlaceVote`, `Poll`, `PollVote`, `TripInvitation`, `ChecklistItem`, `ItineraryDocument`, `GroupActivity` | Imports Base from #1 |
| 4 | `api/models/places.py` | `PlacesModel`, `CitiesModel`, `StatesModel`, `CountriesModel` | **RAW SQL** (no ORM) |
| 5 | `place_search/models.py` | `Country`, `State`, `City`, `Place`, `Photo`, `OpeningHours`, `SearchResult` | **Dataclasses** (no ORM) |

**Verdict:**
- `#1`, `#2`, `#3` share the same Base and engine cleanly.
- `#4` and `#5` define overlapping "Place/City/State/Country" models using different patterns for the **same database**. These should be unified.

---

### 3D. Duplicate Route Patterns

| Functionality | Route 1 | Route 2 | Overlap |
|--------------|---------|---------|---------|
| **Place search** | `/api/v1/locations/search` (locations.py) | `/api/v1/place-search/search` (place_search/routes.py) | BOTH search `travel_data_complete.db` for places by name |
| **City search** | `/api/v1/locations/cities/search` (locations.py) | `/api/trip-planner/cities/search` (trip_planner.py) | BOTH query cities from same DB |
| **Destination search** | `/api/v2/group-planner/destinations/search` (optimized_routes.py) | `/api/v1/locations/search` (locations.py) | BOTH return destination/place data |
| **Health check** | `/health` (app.py) | `/api/health` (health.py) | `/api/v2/group-planner/health` (optimized_routes.py) | 3 health endpoints |

**Verdict:** Three independent place/location search APIs exist that all query the same SQLite database. The frontend uses different ones for different features. These should be a single API.

---

### 3E. Frontend Duplicates

| # | Duplicate | Original | Type |
|---|-----------|----------|------|
| 1 | `services/groupPlannerService.js` | `services/groupPlannerApi.js` | **SHIM** — re-exports groupPlannerApi |
| 2 | `components/placeSearch/placeSearchService.js` | `services/placeSearchService.js` | **SHIM** — re-exports from services/ |
| 3 | `components/pages/jsx/ExpenseAnalytics.jsx` | `components/expenses/jsx/ExpenseAnalytics.jsx` | **DUPLICATE NAME** — may be different views |
| 4 | `components/pages/jsx/InvitationAccept.jsx` | `components/pages/jsx/SmartInvitationHandler.jsx` | **LIKELY DEAD** — SmartInvitationHandler replaced it |
| 5 | `components/pages/jsx/GroupTripPage.jsx` | `components/groupPlanner/jsx/GroupPlannerPage.jsx` | **LIKELY DEAD** — not referenced in App.jsx routes |

**Verdict:** Items `#4` and `#5` appear unused in routing. The shims (`#1`, `#2`) are harmless but add clutter.

---

### 3F. Standalone Flask App in Group_planner

`Group_planner/app.py` contains a full `create_app()` factory with its own CORS, error handlers, and blueprint registration. This is **never used** in production — the main `api/app.py` imports Group_planner blueprints directly. This file is dead code from when Group Planner was a standalone microservice.

---

### 3G. Stale Database Copy

`web/backend/travel_data_complete.db` (root level) is a **stale copy** of `web/backend/database/travel_data_complete.db`. The root copy is 0 bytes or outdated — all modules resolve the path to `database/` folder.

---

### 3H. Node.js Artifacts in Backend

`web/backend/package.json` and `web/backend/package-lock.json` exist in a Python backend. These are almost certainly leftover from an earlier architecture and should be removed.

---

## 4. CURRENT vs CLEAN STRUCTURE

### Current Structure (Problems)

```
web/backend/
├── api/utils/database.py         ← sqlite3 wrapper for travel data
├── place_search/database.py      ← ANOTHER sqlite3 wrapper for same DB
├── api/routes/trip_planner.py    ← INLINE sqlite3 connection for same DB
├── Group_planner/services/places_service.py ← ANOTHER inline sqlite3 for same DB
├── api/models/places.py          ← Raw SQL models for places
├── place_search/models.py        ← Dataclass models for same places
├── Group_planner/app.py          ← Dead standalone Flask app
├── travel_data_complete.db       ← Stale DB copy at root
├── package.json                  ← Node artifact in Python project
```

### Recommended Clean Structure

```
web/backend/
├── run.py
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── api/                           # Flask app factory + API routes
│   ├── __init__.py
│   ├── app.py
│   ├── config/
│   │   └── settings.py
│   ├── middleware/
│   │   ├── request_logger.py
│   │   └── rate_limiter.py        ← MOVE from middleware/ (top-level is odd)
│   ├── routes/
│   │   ├── locations.py           ← KEEP (unified location API)
│   │   └── trip_planner.py        ← REFACTOR to use shared travel_db
│   ├── models/
│   │   └── places.py              ← REFACTOR to use shared travel_db
│   └── utils/
│       ├── responses.py
│       └── validators.py
│       # DELETE database.py → use shared travel_db
│
├── shared_db/                     # ALL database infrastructure
│   ├── connection.py              # SQLAlchemy for tripraft.db (KEEP)
│   ├── travel_db.py               # NEW: Single sqlite3 manager for travel_data_complete.db
│   ├── models.py                  # User, UserSession (KEEP)
│   ├── schemas.py
│   └── auth.py
│
├── shared_auth/                   # MOVE from expense_engine/auth/
│   ├── jwt_handler.py
│   ├── password.py
│   └── decorators.py              # DELETE (use shared_db.auth directly)
│
├── expense_engine/                # KEEP as-is (well structured)
│   ├── database/
│   │   ├── connection.py          # Shim (acceptable)
│   │   └── models.py
│   ├── routes/
│   └── services/
│
├── group_planner/                 # RENAME from Group_planner (PEP 8)
│   ├── database/
│   │   ├── connection.py          # Shim (acceptable)
│   │   └── models.py
│   ├── routes/
│   │   # DELETE optimized_routes.py → merge into groups_routes.py
│   └── services/
│       ├── place_service.py       # KEEP (CRUD for user-added places)
│       # DELETE places_service.py → use shared travel_db
│       └── ...
│
├── place_search/                  # REFACTOR
│   ├── routes.py
│   ├── services.py                # REFACTOR to use shared travel_db
│   ├── models.py                  # KEEP dataclasses for response shapes
│   # DELETE database.py → use shared travel_db
│   └── config.py
│
├── cache/
│   └── redis_client.py
│
├── database/                      # Database files only
│   ├── travel_data_complete.db
│   └── tripraft.db
│
# DELETE:
#   travel_data_complete.db (root stale copy)
#   package.json, package-lock.json
#   Group_planner/app.py (dead standalone factory)
#   email_config.py → move into api/config/
```

---

## 5. CONSOLIDATION RECOMMENDATIONS

### Priority 1: Eliminate Duplicate Database Connections

Create `shared_db/travel_db.py`:
```python
"""Single connection manager for travel_data_complete.db (read-only)"""
class TravelDatabase:
    def get_connection(self): ...
    def execute_query(self, sql, params): ...
    def execute_one(self, sql, params): ...

travel_db = TravelDatabase()  # singleton
```

Then update these 4 files to use it:
- `api/utils/database.py` → DELETE, replace imports with `shared_db.travel_db`
- `place_search/database.py` → DELETE, replace imports with `shared_db.travel_db`
- `api/routes/trip_planner.py` → Remove inline `_get_connection()`, use `shared_db.travel_db`
- `Group_planner/services/places_service.py` → Remove inline `get_connection()`, use `shared_db.travel_db`

### Priority 2: Unify Place/Location Search APIs

Currently 3 endpoints search the same data:
- `/api/v1/locations/search` — locations.py (used by frontend PlaceSearchPage)
- `/api/v1/place-search/search` — place_search/routes.py (used by placeSearchService.js)
- `/api/v2/group-planner/destinations/search` — optimized_routes.py (used by GroupPlanner)

**Recommendation:** Keep ONE search API (the most full-featured one, likely `place_search/`), have others redirect or share the same service.

### Priority 3: Delete Dead Code

| File | Reason |
|------|--------|
| `Group_planner/app.py` | Standalone Flask factory, never used |
| `backend/travel_data_complete.db` (root) | Stale copy |
| `backend/package.json` | Node artifact |
| `backend/package-lock.json` | Node artifact |
| `frontend/components/pages/jsx/InvitationAccept.jsx` | Replaced by SmartInvitationHandler |
| `frontend/components/pages/jsx/GroupTripPage.jsx` | Not in any route |

### Priority 4: Rename & Convention Fixes

| Current | Fix |
|---------|-----|
| `Group_planner/` | `group_planner/` (PEP 8: lowercase with underscores) |
| `expense_engine/auth/decorators.py` | Delete — direct imports from `shared_db.auth` |
| `services/groupPlannerService.js` | Delete shim — update remaining imports |
| `components/placeSearch/placeSearchService.js` | Delete shim — update barrel index |

### Priority 5: Move Misplaced Files

| File | Current Location | Should Be |
|------|-----------------|-----------|
| `middleware/rate_limiter.py` | Top-level `middleware/` | `api/middleware/rate_limiter.py` |
| `email_config.py` | Backend root | `api/config/email_config.py` |
| `expense_engine/auth/jwt_handler.py` | expense_engine | `shared_db/` or `shared_auth/` |
| `expense_engine/auth/password.py` | expense_engine | `shared_db/` or `shared_auth/` |
| `placeSearch/mockData.js` | Component folder | `__tests__/` or `__mocks__/` |

---

## 6. SUMMARY COUNTS

| Metric | Count |
|--------|-------|
| Total backend Python files | ~75 (excluding .llm, .md) |
| Total frontend JS/JSX files | ~85 (excluding .css, .llm) |
| Total CSS files | ~40 |
| Duplicate DB connection patterns | **4** (for travel_data_complete.db) |
| Duplicate search APIs | **3** (all querying same DB) |
| Dead/unused files identified | **6** |
| Re-export shims | **4** (2 backend, 2 frontend) |
| Convention violations | **1** (`Group_planner` casing) |
| Misplaced files | **5** |

The codebase is architecturally sound with a clear separation between expense_engine, group_planner, and place_search. The main issue is **organic duplication** where the same travel database is accessed through 4 different connection patterns and 3 different search APIs. Consolidating these would reduce ~300 lines of boilerplate and eliminate a class of bugs where one connection pattern differs from another.
