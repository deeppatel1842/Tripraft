# TripRaft Backend Architecture

Complete file structure, layer responsibilities, and data flow for the Flask backend.

---

## Directory Layout

```
web/backend/
  run.py                        # Entry point  starts Flask dev server
  pytest.ini                    # Test configuration
  requirements.txt              # Python dependencies
  app/
    __init__.py                 # Re-exports create_app from api.factory
    api/
      __init__.py               # Re-exports create_app
      factory.py                # Flask application factory (CORS, DB, Redis, blueprints)
      middleware.py             # Request/response logging hooks
      health.py                 # /api/health/* liveness & readiness probes
      route_viewer.py           # /api/routes  HTML/JSON route listing
      utils/
        database.py             # DatabaseManager for travel_data_complete.db (sqlite3)
        responses.py            # success_response, error_response, paginated_response
        validators.py           # validate_pagination, validate_search_query, sanitize_input
      v1/
        auth.py                 # /api/expense/*        legacy auth (signup/login/refresh)
        users.py                # /api/v1/users/*       user CRUD
        expenses.py             # /api/expense/expenses  expense CRUD
        expense_groups.py       # /api/expense/groups    expense group management
        expense_invitations.py  # /api/expense/invitations  expense group invites
        settlements.py          # /api/expense/settlements  debt settlements
        gp_groups.py            # /api/v2/group-planner/groups    travel group CRUD
        gp_places.py            # /api/v2/group-planner/*/places  group place voting
        gp_polls.py             # /api/v2/group-planner/*/polls   group polls
        gp_invitations.py       # /api/v2/group-planner/invitations  trip invites
        gp_checklist.py         # /api/v2/group-planner/*/checklist  packing/task lists
        gp_events.py            # /api/v2/group-planner/events   Ticketmaster events
        gp_destinations.py      # /api/v2/group-planner/destinations  autocomplete + places
        locations.py            # /api/v1/locations/*    country/state/city/place browse
        places.py               # /api/v1/place-search/* full-text place search
        trips.py                # /api/trip-planner/*    itinerary generator
    core/
      config.py                 # Config, DevelopmentConfig, ProductionConfig, TestingConfig
      exceptions.py             # AppError  ValidationError, AuthenticationError, etc.
      logging.py                # JSONFormatter, setup_logging
      rate_limiter.py           # Flask-Limiter wrapper (limit_api, limit_auth, limit_search)
      security.py               # Security headers, CORS fallback
    domain/
      users/
        models.py               # User, UserSession (SQLAlchemy ORM)
        repository.py           # UserRepository, UserSessionRepository
      expenses/
        models.py               # Group, GroupMember, Expense, ExpenseSplit, Settlement, etc.
      group_planner/
        models.py               # TravelGroup, TripMember, Place, Poll, ChecklistItem, etc.
      places/
        models.py               # Place, SearchResult, AutocompleteSuggestion (dataclasses)
        repository.py           # DatabaseConnection for travel_data_complete.db
        location_models.py      # PlacesModel  static query helpers
        location_repository.py  # DatabaseManager (duplicate of api/utils/database.py)
    infrastructure/
      auth/
        jwt.py                  # create_access_token, verify_token, set_auth_cookies
        password.py             # hash_password, verify_password (bcrypt)
        decorators.py           # @require_auth, @optional_auth, @require_refresh_token
      cache/
        redis.py                # RedisClient singleton, @cache_response decorator
      db/
        base.py                 # Shared SQLAlchemy declarative_base()
        connection.py           # Engine, SessionLocal, init_db, get_db_session (tripraft.db)
        travel_db.py            # TravelDatabase class (travel_data_complete.db)
      email/
        config.py               # EmailConfig toggle flags
        smtp.py                 # EmailService SMTP sender
      external/                 # Placeholder for third-party API clients
    schemas/
      common.py                 # Marshmallow schemas for request validation
      users.py                  # Pydantic models for user requests/responses
    services/
      user_service.py           # UserService  register, login, refresh, profile
      auth_service.py           # AuthService  legacy auth flows
      expense_service.py        # ExpenseServiceSQL  expense CRUD + history
      expense_group_service.py  # GroupServiceSQL  group CRUD + join by code
      expense_invite_service.py # InvitationServiceSQL  send/accept/decline
      settlement_service.py     # SettlementServiceSQL  settlements + balances
      travel_group_service.py   # GroupService  travel group CRUD + budget + itinerary
      travel_place_service.py   # PlaceService  add/vote/delete places in groups
      poll_service.py           # PollService  create/vote/delete polls
      trip_invite_service.py    # InvitationService  trip invitations
      checklist_service.py      # ChecklistService  checklist items
      events_service.py         # EventsService  Ticketmaster API wrapper
      destination_service.py    # DestinationService  autocomplete + place lookup
      place_search_service.py   # PlaceSearchService  full-text place search
      email_service.py          # EmailService  legacy SMTP sender
    workers/                    # Placeholder for background jobs
  tests/
    conftest.py                 # Fixtures: app, client, auth_headers, test_user, etc.
    test_api_*.py               # API-level tests (HTTP requests via Flask test client)
    test_service_*.py           # Service-level tests (direct function calls)
  database/
    tripraft.db                 # User/expense/group data (SQLAlchemy managed)
    travel_data_complete.db     # Read-only geographic data (150k+ places)
```

---

## Layered Architecture

The backend follows a **four-layer architecture**. Each layer only depends on layers below it.

```
  Routes (api/v1/*.py)          Thin HTTP handlers, request parsing, response formatting
    |
  Services (services/*.py)      Business logic, validation, orchestration
    |
  Domain (domain/*/models.py)   ORM models, dataclasses, repository patterns
    |
  Infrastructure               Database connections, auth, cache, email
    (infrastructure/*/)
```

### Layer Rules

| Layer | Knows about | Does NOT know about |
|-------|------------|---------------------|
| Routes (api/v1) | Services, Schemas, Infrastructure Auth decorators | Domain models directly |
| Services | Domain models, Infrastructure (DB, auth, email) | Flask request/response |
| Domain | SQLAlchemy Base only | Services, Routes, Infrastructure |
| Infrastructure | Core config only | Domain, Services, Routes |

---

## Two Database Systems

### 1. tripraft.db (SQLAlchemy ORM)

Managed by `infrastructure/db/connection.py`. All tables created via `Base.metadata.create_all()`.

**Tables** (defined across domain models):

| Table | Model | Module |
|-------|-------|--------|
| `users` | `User` | `domain/users/models.py` |
| `user_sessions` | `UserSession` | `domain/users/models.py` |
| `groups` | `Group` | `domain/expenses/models.py` |
| `group_members` | `GroupMember` | `domain/expenses/models.py` |
| `expenses` | `Expense` | `domain/expenses/models.py` |
| `expense_splits` | `ExpenseSplit` | `domain/expenses/models.py` |
| `settlements` | `Settlement` | `domain/expenses/models.py` |
| `group_balances` | `GroupBalance` | `domain/expenses/models.py` |
| `invitations` | `Invitation` | `domain/expenses/models.py` |
| `expense_history` | `ExpenseHistory` | `domain/expenses/models.py` |
| `gp_travel_groups` | `TravelGroup` | `domain/group_planner/models.py` |
| `gp_trip_members` | `TripMember` | `domain/group_planner/models.py` |
| `gp_places` | `Place` | `domain/group_planner/models.py` |
| `gp_place_votes` | `PlaceVote` | `domain/group_planner/models.py` |
| `gp_polls` | `Poll` | `domain/group_planner/models.py` |
| `gp_poll_votes` | `PollVote` | `domain/group_planner/models.py` |
| `gp_trip_invitations` | `TripInvitation` | `domain/group_planner/models.py` |
| `gp_checklist_items` | `ChecklistItem` | `domain/group_planner/models.py` |
| `gp_itinerary_documents` | `ItineraryDocument` | `domain/group_planner/models.py` |
| `gp_group_activities` | `GroupActivity` | `domain/group_planner/models.py` |

### 2. travel_data_complete.db (Read-Only SQLite)

Pre-populated geographic database. Accessed via raw `sqlite3` connections.

**Tables**: `countries`, `states`, `cities`, `places`, `photos`, `opening_hours`, `tags`, `place_tags`

**Accessed by three managers** (all point to the same file):
- `api/utils/database.py` -- `DatabaseManager` (used by locations blueprint)
- `domain/places/repository.py` -- `DatabaseConnection` (used by place search service)
- `infrastructure/db/travel_db.py` -- `TravelDatabase` (general-purpose)

---

## Request Flow

```
HTTP Request
  |
  v
Flask App (factory.py)
  |-- CORS check
  |-- Rate limiter
  |-- Request logger (middleware.py)
  |
  v
Blueprint Route (api/v1/*.py)
  |-- @require_auth decorator (checks JWT token or Firebase ID token)
  |   Sets g.user_id, g.user_email, g.current_user
  |-- Request validation (schemas/common.py or inline)
  |
  v
Service Layer (services/*.py)
  |-- Business logic validation
  |-- Database operations via get_db_session()
  |-- Domain model CRUD
  |
  v
Response
  |-- jsonify({'success': True/False, 'data': ...})
  |-- Security headers (core/security.py)
  |-- Compression (flask-compress)
```

---

## Authentication Flow

Two parallel auth systems exist (both use the same `users` table):

### Modern Auth (/api/v1/users/*)
```
Register -> UserService.register() -> hash password -> create User + UserSession
Login    -> UserService.login()    -> verify password -> create access + refresh tokens
Refresh  -> UserService.refresh()  -> verify refresh token -> rotate tokens
```

### Legacy Auth (/api/expense/*)
```
Signup   -> AuthService.signup()   -> hash password -> create User + UserSession
Login    -> AuthService.login()    -> verify password -> create tokens + set cookies
Refresh  -> AuthService.refresh()  -> verify refresh token -> rotate tokens
```

Both systems create JWT tokens with the same secret key. The `@require_auth` decorator accepts tokens from either system.

**Token delivery**: Access token via `Authorization: Bearer <token>` header or `access_token` cookie. Refresh token via request body or `refresh_token` cookie.

---

## API Route Map

### Auth & Users
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/expense/signup` | No | Create account (legacy) |
| POST | `/api/expense/login` | No | Login (legacy) |
| POST | `/api/expense/refresh` | No | Refresh tokens (legacy) |
| GET | `/api/expense/me` | Yes | Current user (legacy) |
| POST | `/api/v1/users/register` | No | Create account |
| POST | `/api/v1/users/login` | No | Login |
| POST | `/api/v1/users/refresh` | No | Refresh tokens |
| GET | `/api/v1/users/me` | Yes | Current user |
| PATCH | `/api/v1/users/me` | Yes | Update profile |

### Expense Groups
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/expense/groups` | Yes | Create group |
| GET | `/api/expense/groups` | Yes | List groups |
| GET | `/api/expense/groups/<id>` | Yes | Get group |
| PUT | `/api/expense/groups/<id>` | Yes | Update group |
| DELETE | `/api/expense/groups/<id>` | Yes | Delete group |
| POST | `/api/expense/groups/join` | Yes | Join by code |
| GET | `/api/expense/groups/<id>/members` | Yes | List members |

### Expenses
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/expense/expenses` | Yes | Create expense |
| GET | `/api/expense/expenses` | Yes | List expenses |
| GET | `/api/expense/expenses/<id>` | Yes | Get expense |
| PUT | `/api/expense/expenses/<id>` | Yes | Update expense |
| DELETE | `/api/expense/expenses/<id>` | Yes | Delete expense |
| GET | `/api/expense/expenses/group/<id>` | Yes | Group expenses |

### Settlements
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/expense/settlements` | Yes | Create settlement |
| GET | `/api/expense/settlements/group/<id>` | Yes | Group settlements |
| GET | `/api/expense/settlements/group/<id>/balances` | Yes | Group balances |
| GET | `/api/expense/settlements/group/<id>/simplified` | Yes | Simplified debts |

### Expense Invitations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/expense/invitations` | Yes | Send invitation |
| GET | `/api/expense/invitations/my` | Yes | My invitations |
| POST | `/api/expense/invitations/<id>/accept` | Yes | Accept |
| POST | `/api/expense/invitations/<id>/decline` | Yes | Decline |

### Travel Groups (Group Planner)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/group-planner/groups` | Yes | Create travel group |
| GET | `/api/v2/group-planner/user/groups` | Yes | List groups |
| GET | `/api/v2/group-planner/groups/<id>` | Yes | Get group |
| PUT | `/api/v2/group-planner/groups/<id>` | Yes | Update group |
| DELETE | `/api/v2/group-planner/groups/<id>` | Yes | Delete group |
| PUT | `/api/v2/group-planner/groups/<id>/budget` | Yes | Update budget |
| PUT | `/api/v2/group-planner/groups/<id>/itinerary` | Yes | Update itinerary |
| GET | `/api/v2/group-planner/groups/<id>/members` | Yes | List members |
| GET | `/api/v2/group-planner/groups/<id>/expense-summary` | Yes | Expense summary |

### Group Places
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/group-planner/groups/<id>/places` | Yes | Add place |
| GET | `/api/v2/group-planner/groups/<id>/places` | Yes | List places |
| POST | `/api/v2/group-planner/groups/<id>/places/<pid>/vote` | Yes | Vote |
| DELETE | `/api/v2/group-planner/groups/<id>/places/<pid>` | Yes | Delete |

### Group Polls
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/group-planner/groups/<id>/polls` | Yes | Create poll |
| GET | `/api/v2/group-planner/groups/<id>/polls` | Yes | List polls |
| POST | `/api/v2/group-planner/groups/<id>/polls/<pid>/vote` | Yes | Vote |
| DELETE | `/api/v2/group-planner/groups/<id>/polls/<pid>` | Yes | Delete |

### Group Checklist
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/group-planner/groups/<id>/checklist` | Yes | Add item |
| GET | `/api/v2/group-planner/groups/<id>/checklist` | Yes | List items |
| POST | `/api/v2/group-planner/checklist/<item_id>/toggle` | Yes | Toggle done |
| DELETE | `/api/v2/group-planner/groups/<id>/checklist/<item_id>` | Yes | Delete |
| GET | `/api/v2/group-planner/groups/<id>/checklist/stats` | Yes | Stats |

### Trip Invitations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/group-planner/invitations` | Yes | Invite member |
| POST | `/api/v2/group-planner/invitations/<id>/accept` | Yes | Accept |
| POST | `/api/v2/group-planner/invitations/<id>/decline` | Yes | Decline |
| GET | `/api/v2/group-planner/user/invitations` | Yes | My invitations |

### Events
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v2/group-planner/events` | No | Search events |
| GET | `/api/v2/group-planner/groups/<id>/events` | No | Group destination events |

### Destinations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/group-planner/destinations/autocomplete` | No | Autocomplete |
| GET | `/api/v2/group-planner/destinations/<dest>/places` | No | Destination places |

### Place Search
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/place-search/search?q=...` | No | Full-text search |
| GET | `/api/v1/place-search/autocomplete?q=...` | No | Autocomplete |
| GET | `/api/v1/place-search/place/<id>` | No | Place details |
| GET | `/api/v1/place-search/stats` | No | DB statistics |

### Location Browse
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/locations/countries` | No | List countries |
| GET | `/api/v1/locations/cities/search?q=...` | No | Search cities |
| GET | `/api/v1/locations/cities/<id>/places` | No | Places in city |
| GET | `/api/v1/locations/autocomplete?q=...` | No | Autocomplete |

### Trip Planner
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/trip-planner/generate` | No | Generate itinerary |
| GET | `/api/trip-planner/cities` | No | List cities |
| GET | `/api/trip-planner/cities/search?q=...` | No | Search cities |

### Health & System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health/` | No | Health check |
| GET | `/api/health/ready` | No | Readiness (DB + Redis) |
| GET | `/api/routes` | No | Route listing |

---

## Service-to-Model Dependencies

```
user_service.py        --> User, UserSession
auth_service.py        --> User, UserSession

expense_service.py     --> Expense, ExpenseSplit, ExpenseHistory, Group, GroupBalance, GroupMember, User
expense_group_service  --> Group, GroupMember, GroupBalance, User
expense_invite_service --> Group, GroupMember, GroupBalance, Invitation, User
settlement_service     --> Group, GroupMember, GroupBalance, Settlement, User

travel_group_service   --> TravelGroup, TripMember, GroupActivity, ItineraryDocument, User
travel_place_service   --> Place, PlaceVote, TravelGroup, TripMember, GroupActivity, User
poll_service           --> Poll, PollVote, TravelGroup, TripMember, GroupActivity
trip_invite_service    --> TravelGroup, TripMember, TripInvitation, GroupActivity, User
checklist_service      --> ChecklistItem, TravelGroup, TripMember, GroupActivity

events_service         --> (external: Ticketmaster API only)
destination_service    --> (raw SQL: travel_data_complete.db)
place_search_service   --> Place, SearchResult, AutocompleteSuggestion (dataclasses)
```

---

## Configuration

All config lives in `app/core/config.py`. Key settings:

| Setting | Default (Dev) | Source |
|---------|---------------|--------|
| `DATABASE_URL` | `sqlite:///database/tripraft.db` | `DATABASE_URL` env var |
| `TRAVEL_DATABASE_PATH` | `database/travel_data_complete.db` | Computed from `DATABASE_DIR` |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | `SECRET_KEY` env var |
| `JWT_SECRET_KEY` | Same as SECRET_KEY | `JWT_SECRET_KEY` env var |
| `ACCESS_TOKEN_EXPIRES` | 24 hours | Hardcoded |
| `REFRESH_TOKEN_EXPIRES` | 30 days | Hardcoded |
| `REDIS_URL` | `redis://localhost:6379/0` | `REDIS_URL` env var |
| `CORS_ORIGINS` | `localhost:5173,5174,3000` | `CORS_ORIGINS` env var |
| `RATE_LIMIT_DEFAULT` | `200/hour` | Hardcoded |

---

## How to Run

```bash
# Development
cd web/backend
python run.py

# Tests
python -m pytest tests/ -q

# With virtual environment
.\wayfinder\Scripts\activate
python run.py
```

Server starts on `http://localhost:5000` with 135 registered routes.
