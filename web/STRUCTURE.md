# TripRaft — Project Structure

## Architecture Overview

```
web/
├── backend/           Python/Flask REST API (single process)
│   ├── api/           Core Flask app, entry point, shared middleware
│   ├── shared_db/     Single source of truth for DB connections & base models
│   ├── expense_engine/ Splitwise-style expense tracking (domain module)
│   ├── Group_planner/  Collaborative trip planning (domain module)
│   ├── place_search/   Place search engine (domain module)
│   ├── cache/          Redis client wrapper
│   ├── middleware/      Rate limiter, request logging
│   └── database/       SQLite files (tripraft.db, travel_data_complete.db)
│
└── frontend/          React.js SPA (Vite build)
    └── src/
        ├── components/   UI organized by feature domain
        ├── context/      React contexts (Auth, GroupPlanner)
        ├── hooks/        Custom React hooks
        ├── services/     API client modules (one per backend domain)
        ├── config/       Environment config
        ├── styles/       Global CSS
        └── utils/        Shared helpers
```

---

## Backend — Python/Flask

### Entry Point

- `run.py` → starts the Flask dev server
- `api/app.py` → `create_app()` factory, registers all blueprints

### Databases (2 SQLite files)

| Database | Purpose | Access Layer |
|---|---|---|
| `database/tripraft.db` | User data, expenses, groups, trips, polls | `shared_db/connection.py` (SQLAlchemy ORM) |
| `database/travel_data_complete.db` | Read-only reference data (16k places, 889 cities, 82 countries) | `api/utils/database.py` (raw SQL) + `place_search/database.py` |

### Module Map

```
api/                         Flask core
├── app.py                   App factory, blueprint registration, error handlers
├── config/settings.py       Environment-based config (dev/prod)
├── health.py                /health, /metrics endpoints
├── route_viewer.py          /api/routes endpoint (lists all routes)
├── middleware/               Request logger
├── routes/
│   ├── locations.py         /api/v1/locations/* — hierarchical place browsing (cached)
│   └── trip_planner.py      /api/trip-planner/* — itinerary generation
├── models/places.py         Query models for travel_data_complete.db
└── utils/
    ├── database.py          DatabaseManager for travel_data_complete.db
    ├── responses.py         Standard JSON response helpers
    └── validators.py        Input validation utilities

shared_db/                   Shared database layer (single source of truth)
├── connection.py            SQLAlchemy engine, session factory, init_db()
├── models.py                Base, User, UserSession (shared across modules)
├── schemas.py               Marshmallow validation schemas for all modules
└── auth.py                  JWT auth decorators (require_auth, get_current_user_id)

expense_engine/              Expense tracking domain
├── database/
│   ├── connection.py        Re-exports from shared_db + reset_db()
│   └── models.py            Group, Expense, ExpenseSplit, Settlement, etc.
├── auth/
│   ├── jwt_handler.py       JWT token creation/verification
│   ├── password.py          Bcrypt password hashing
│   └── decorators.py        Re-exports shared_db.auth decorators
├── routes/
│   ├── auth_routes.py       /api/expense/signup, login, logout
│   ├── expenses_sql_routes.py  /api/expense/expenses CRUD
│   ├── groups_sql_routes.py    /api/expense/groups CRUD
│   ├── invitations_sql_routes.py  /api/expense/invitations
│   └── settlements_sql_routes.py  /api/expense/settlements
└── services/
    ├── auth_service.py         User registration, login, sessions
    ├── expense_service_sql.py  Expense CRUD, split calculation, balances
    ├── group_service_sql.py    Group CRUD, membership
    ├── invitation_service_sql.py  Invitations
    ├── settlement_service_sql.py  Settlements, balance computation
    └── email_service.py        Invitation emails

Group_planner/               Trip planning domain
├── database/
│   ├── connection.py        Re-exports from shared_db + init_db()
│   └── models.py            TravelGroup, TripMember, Place, Poll, Checklist, etc.
├── routes/
│   ├── groups_routes.py     /api/groups/* CRUD
│   ├── places_routes.py     /api/groups/<id>/places (saved places in a trip)
│   ├── polls_routes.py      /api/groups/<id>/polls (group voting)
│   ├── invitations_routes.py  /api/groups/<id>/invite
│   ├── checklist_routes.py  /api/groups/<id>/checklist
│   ├── events_routes.py     /api/groups/<id>/events
│   └── optimized_routes.py  /api/v2/group-planner/* (destination search, dashboard)
└── services/
    ├── group_service.py         Group CRUD
    ├── place_service.py         Group place CRUD (add/vote/remove places in a trip)
    ├── destination_service.py   Destination lookup from travel_data_complete.db
    ├── poll_service.py          Poll CRUD + voting
    ├── invitation_service.py    Trip invitations
    ├── checklist_service.py     Packing/todo checklist
    └── events_service.py        Trip event management

place_search/                Place search engine
├── config.py                Database path config
├── database.py              DatabaseConnection for travel_data_complete.db
├── models.py                Search query models
├── routes.py                /api/v1/place-search/* endpoints
└── services.py              Search, autocomplete, stats

cache/redis_client.py        Redis wrapper (graceful fallback to no-cache)
middleware/rate_limiter.py   Flask-Limiter with Redis/memory backend
```

### API Route Groups

| Prefix | Module | Auth | Description |
|---|---|---|---|
| `/api/expense/*` | expense_engine | JWT | User auth + expense/group/settlement CRUD |
| `/api/groups/*` | Group_planner | JWT | Trip group CRUD, places, polls, checklist |
| `/api/v2/group-planner/*` | Group_planner (optimized) | JWT | Dashboard, destination search |
| `/api/v1/locations/*` | api.routes.locations | None | Hierarchical place browsing (cached) |
| `/api/v1/place-search/*` | place_search | None | Full-text place search |
| `/api/trip-planner/*` | api.routes.trip_planner | None | Itinerary generation |
| `/api/health/*` | api.health | None | Health checks, metrics |

---

## Frontend — React.js (Vite)

### Component Organization

Each feature has a folder with `jsx/`, `css/`, and `index.js` (barrel):

```
src/components/
├── auth/                Login, signup forms
├── common/              Shared UI (ErrorBoundary, LoadingStates, Toast, etc.)
├── expenses/            ExpenseManager, TransactionModal, GroupBalances, etc.
├── groupPlanner/        GroupPlannerPage, TripDashboard, PollManager, etc.
├── layout/              Header, Footer, Navigation
├── pages/               Route-level page wrappers
│   └── jsx/
│       ├── HomePage.jsx
│       ├── ExpensePage.jsx
│       ├── TripPlanner.jsx
│       ├── About.jsx, Contact.jsx, Pricing.jsx
│       ├── Analytics.jsx, ExpenseAnalytics.jsx
│       └── SmartInvitationHandler.jsx
├── placeSearch/         PlaceSearchPage, SearchBar, PlaceCard
└── tripPlanner/         TripPlannerForm, ItineraryView, DayPlan
```

### Services (API Clients)

| File | Backend Module | Description |
|---|---|---|
| `expenseApi.js` | expense_engine | Full expense CRUD, groups, settlements, analytics |
| `groupPlannerApi.js` | Group_planner | Trip groups, places, polls, invitations |
| `placeSearchService.js` | place_search | Place search, autocomplete, stats |
| `tripPlannerService.js` | api.routes.trip_planner | Itinerary generation |
| `sqlAuthService.js` | expense_engine.auth | Login, signup, token management |
| `pdfExportService.js` | (client-only) | PDF export for itineraries |

### Context Providers

| Context | Purpose |
|---|---|
| `AuthContext.jsx` | User auth state, login/logout, token refresh |
| `GroupPlannerContext.jsx` | (Unused — GroupPlannerPage manages its own state) |
