# TripRaft Backend Architecture

## Overview
Clean, enterprise-grade Flask backend following the structure.

## Directory Layout

```
backend/
├── .env                          # Environment variables (secrets, API keys)
├── run.py                        # Main entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build
│
├── app/                          # Application root
│   ├── __init__.py               # Re-exports create_app
│   │
│   ├── core/                     # Framework-agnostic core
│   │   ├── config.py             # Settings from .env (Config, DevelopmentConfig, ProductionConfig)
│   │   ├── logging.py            # Structured JSON logging (production) / colored (dev)
│   │   ├── exceptions.py         # AppError -> ValidationError, AuthenticationError, NotFoundError, etc.
│   │   ├── rate_limiter.py       # Flask-Limiter with per-operation limits
│   │   └── security.py           # Security headers, CORS middleware
│   │
│   ├── infrastructure/           # Technical concerns & external integrations
│   │   ├── db/
│   │   │   ├── base.py           # Shared SQLAlchemy declarative Base
│   │   │   ├── connection.py     # ONE engine for tripraft.db (SessionLocal, get_db)
│   │   │   └── travel_db.py      # Read-only sqlite3 for travel_data_complete.db
│   │   ├── cache/
│   │   │   └── redis.py          # RedisClient singleton, JSON helpers, @cache_response
│   │   ├── auth/
│   │   │   ├── jwt.py            # JWT access/refresh token helpers
│   │   │   ├── password.py       # bcrypt hash/verify
│   │   │   └── decorators.py     # @require_auth, @require_refresh_token, @optional_auth
│   │   ├── email/
│   │   │   ├── smtp.py           # SMTP email service
│   │   │   └── config.py         # Email type enable/disable
│   │   └── external/             # Third-party API clients (future)
│   │
│   ├── domain/                   # Business entities (no Flask dependency)
│   │   ├── users/
│   │   │   ├── models.py         # User, UserSession (SQLAlchemy)
│   │   │   └── repository.py     # UserRepository, UserSessionRepository
│   │   ├── expenses/
│   │   │   └── models.py         # Group, GroupMember, Expense, ExpenseSplit,
│   │   │                         # Settlement, GroupBalance, Invitation, ExpenseHistory
│   │   ├── group_planner/
│   │   │   └── models.py         # TravelGroup, TripMember, Place, PlaceVote, Poll,
│   │   │                         # PollVote, TripInvitation, ChecklistItem,
│   │   │                         # ItineraryDocument, GroupActivity
│   │   └── places/
│   │       ├── models.py         # Dataclass models (Country, City, Place, etc.)
│   │       ├── repository.py     # DatabaseConnection for place search
│   │       ├── location_models.py    # PlacesModel, CitiesModel for locations API
│   │       └── location_repository.py # DatabaseManager for location queries
│   │
│   ├── services/                 # Use-case orchestration
│   │   ├── user_service.py       # User register, login, profile, password
│   │   ├── auth_service.py       # Legacy auth (signup/login/refresh/logout)
│   │   ├── expense_group_service.py  # Expense group CRUD
│   │   ├── expense_service.py    # Expense create/edit/delete/split
│   │   ├── settlement_service.py # Settlement recording, balance recalc
│   │   ├── expense_invite_service.py # Expense group invitations
│   │   ├── email_service.py      # Email notification logic
│   │   ├── travel_group_service.py   # Travel group CRUD, membership
│   │   ├── travel_place_service.py   # Place suggestions, voting
│   │   ├── poll_service.py       # Poll creation and voting
│   │   ├── trip_invite_service.py    # Trip invitations
│   │   ├── checklist_service.py  # Pre-trip checklist
│   │   ├── events_service.py     # Ticketmaster event search
│   │   ├── destination_service.py    # Destination autocomplete
│   │   └── place_search_service.py   # Place full-text search
│   │
│   ├── api/                      # Flask REST API layer
│   │   ├── factory.py            # create_app() -- THE app factory
│   │   ├── health.py             # /api/health/* endpoints
│   │   ├── middleware.py         # Request/response logging
│   │   ├── route_viewer.py       # Styled route listing at /api/routes
│   │   ├── utils/
│   │   │   ├── responses.py      # success_response, error_response, paginated_response
│   │   │   ├── validators.py     # validate_pagination, validate_search_query
│   │   │   └── database.py       # DatabaseManager for travel_data_complete.db
│   │   └── v1/                   # Versioned route blueprints
│   │       ├── users.py          # /api/v1/users/*
│   │       ├── auth.py           # /api/expense/*
│   │       ├── expense_groups.py # /api/expense/groups/*
│   │       ├── expenses.py       # /api/expense/expenses/*
│   │       ├── settlements.py    # /api/expense/settlements/*
│   │       ├── expense_invitations.py # /api/expense/invitations/*
│   │       ├── gp_groups.py      # /api/v2/group-planner/* (groups)
│   │       ├── gp_places.py      # /api/v2/group-planner/* (places)
│   │       ├── gp_polls.py       # /api/v2/group-planner/* (polls)
│   │       ├── gp_invitations.py # /api/v2/group-planner/* (invitations)
│   │       ├── gp_checklist.py   # /api/v2/group-planner/* (checklist)
│   │       ├── gp_events.py      # /api/v2/group-planner/* (events)
│   │       ├── gp_destinations.py# /api/v2/group-planner/* (destination search)
│   │       ├── locations.py      # /api/v1/locations/*
│   │       ├── places.py         # /api/v1/place-search/*
│   │       └── trips.py          # /api/trip-planner/*
│   │
│   ├── schemas/                  # Validation
│   │   ├── users.py              # Pydantic user auth schemas
│   │   └── common.py             # Marshmallow expense/GP validation schemas
│   │
│   └── workers/                  # Background jobs (future)
│
├── database/                     # SQLite database files
│   ├── tripraft.db               # Main app DB (users, expenses, groups)
│   └── travel_data_complete.db   # Read-only geographic data
│
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
└── unwanted/                     # Archived old code (pre-migration)
```

## Database Architecture

### tripraft.db (SQLAlchemy ORM)
Single unified database for all transactional data:

| Domain | Tables |
|--------|--------|
| Users | `users`, `user_sessions` |
| Expenses | `groups`, `group_members`, `expenses`, `expense_splits`, `settlements`, `group_balances`, `invitations`, `expense_history` |
| Group Planner | `travel_groups`, `gp_group_members`, `gp_places`, `gp_place_votes`, `gp_polls`, `gp_poll_votes`, `gp_invitations`, `gp_checklist_items`, `gp_itinerary_documents`, `gp_group_activities` |

### travel_data_complete.db (Read-only, raw sqlite3)
Geographic reference data:
- `countries`, `states`, `cities`, `places`, `photos`, `tags`, `opening_hours`, `place_tags`

## API Endpoints

| Prefix | Module | Description |
|--------|--------|-------------|
| `/api/expense/*` | Expense Engine | Auth, groups, expenses, settlements, invitations |
| `/api/v2/group-planner/*` | Group Planner | Travel groups, places, polls, checklist, events |
| `/api/v1/locations/*` | Locations | Countries, states, cities, places hierarchy |
| `/api/v1/place-search/*` | Place Search | Autocomplete, full-text search |
| `/api/trip-planner/*` | Trip Planner | Trip planning and itinerary |
| `/api/v1/users/*` | Users | Clean auth (register, login, profile) |
| `/api/health/*` | Health | System health checks |

## Key Principles
- **Single Base**: All SQLAlchemy models share one `Base` from `infrastructure/db/base.py`
- **Single Engine**: One `engine` in `infrastructure/db/connection.py` for `tripraft.db`
- **Single Auth**: All routes use decorators from `infrastructure/auth/decorators.py`
- **No print()**: All output goes through `logging` module
- **No hardcoded values**: Everything from `.env` via `core/config.py`
