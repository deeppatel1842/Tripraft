# TripRaft

An AI-powered group travel planning and expense management platform. Search 16,830+ places across 82 countries, plan trips collaboratively with polls and checklists, split expenses with smart balance tracking, and generate day-by-day itineraries.

**Live Landing Page:** [tripraft.vercel.app](https://tripraft.vercel.app)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, React Router 7, React Query 5 |
| Backend | Python 3.11, Flask (factory pattern) |
| Databases | SQLite (app data) + SQLite (16,830 places read-only) |
| Cache | Redis Cloud (response caching, rate limiter state) |
| Auth | JWT (httpOnly cookies + Bearer), bcrypt 12 rounds |
| Maps | Leaflet + OpenStreetMap |
| Charts | Recharts |
| Validation | Marshmallow + Pydantic (backend), custom (frontend) |
| Email | SMTP (Gmail) for invitations |

---

## Features

### Place Search Engine
- Full-text search across 16,830 places, 889 cities, 82 countries
- Autocomplete with debounced suggestions
- Category and budget filters
- Place detail cards with ratings, descriptions, and map pins
- City-level and country-level statistics

### Group Trip Planner
- Create trip groups with invite codes and email invitations
- Add/vote on destination places with interactive map
- Polls for group decision-making (single/multi-choice)
- Shared packing/todo checklist
- Trip events via Ticketmaster integration
- Notes with auto-save (1s debounce)
- Budget tracking per group

### Expense Splitting Engine
- 4 split types: equal, exact, percentage, shares
- Real-time balance calculation with simplified debt algorithm
- Settlement tracking and history
- Group-level analytics with charts
- PDF export for expense reports
- Invitation system for expense groups

### Trip Itinerary Generator
- Day-by-day itinerary from selected places
- 3 pacing modes (relaxed, moderate, packed)
- Map visualization with numbered markers
- PDF export for offline use

### Authentication
- JWT with dual delivery (httpOnly cookies + Bearer header fallback)
- Access tokens (1hr) + refresh tokens (30d)
- Auto-refresh before expiry
- 15-minute inactivity timeout with warning
- bcrypt password hashing (12 rounds)

---

## Architecture

```
web/
├── backend/             Python/Flask REST API
│   ├── app/
│   │   ├── api/         Flask app factory, blueprints, middleware
│   │   ├── core/        Shared DB layer (SQLAlchemy engine, auth decorators)
│   │   ├── domain/      Domain modules (expenses, groups, places)
│   │   ├── infrastructure/  Redis cache, rate limiter
│   │   ├── schemas/     Marshmallow validation schemas
│   │   ├── services/    Business logic layer
│   │   └── workers/     Background tasks
│   ├── run.py           Entry point
│   └── requirements.txt
│
├── frontend/            React SPA (Vite)
│   └── src/
│       ├── components/  UI organized by feature domain
│       ├── context/     React contexts (Auth, GroupPlanner)
│       ├── hooks/       Custom React hooks
│       ├── services/    API client modules
│       ├── config/      Environment config
│       ├── styles/      Global CSS
│       └── utils/       Shared helpers
│
├── database/
│   ├── tripraft.db              App data (users, expenses, groups, polls)
│   └── travel_data_complete.db  Read-only reference (16,830 places)
│
Docs/                    Full product documentation
├── 01_PRODUCT_OVERVIEW.md
├── 02_SYSTEM_ARCHITECTURE.md
├── 03_BACKEND_DEEP_DIVE.md
├── 04_FRONTEND_DEEP_DIVE.md
├── 05_DATABASE_AND_DATA.md
├── 06_PLACES_ENGINE.md
├── 07_EXPENSE_ENGINE.md
├── 08_GROUP_PLANNER.md
├── 09_WHAT_WE_COMPLETED.md
├── B2C/                 Consumer product roadmap
└── B2B/                 Enterprise/white-label roadmap
```

---

## API Routes

| Prefix | Module | Auth | Description |
|--------|--------|------|-------------|
| `/api/expense/*` | Expense Engine | JWT | Auth, expense/group/settlement CRUD |
| `/api/groups/*` | Group Planner | JWT | Trip groups, places, polls, checklist |
| `/api/v2/group-planner/*` | Group Planner | JWT | Dashboard, destination search |
| `/api/v1/locations/*` | Locations | None | Hierarchical place browsing (cached) |
| `/api/v1/place-search/*` | Place Search | None | Full-text place search, autocomplete |
| `/api/trip-planner/*` | Trip Planner | None | Itinerary generation |
| `/api/health/*` | Health | None | Health checks, metrics |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional, falls back gracefully)

### Backend Setup

```bash
cd web/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values (SECRET_KEY, JWT_SECRET_KEY, etc.)

# Run the server
python run.py
```

The backend starts at `http://localhost:5000`.

### Frontend Setup

```bash
cd web/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if needed (defaults point to localhost:5000)

# Run dev server
npm run dev
```

The frontend starts at `http://localhost:5173`.

### Environment Variables

**Backend** (`.env`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Flask secret key |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CORS_ORIGINS` | No | `localhost:5173,5174,3000` | Allowed CORS origins |
| `SMTP_USER` | No | - | Gmail address for invitations |
| `SMTP_PASSWORD` | No | - | Gmail app password |
| `TICKETMASTER_API_KEY` | No | - | Events API key |

**Frontend** (`.env.local`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | Yes | `http://localhost:5000` | Backend API URL |
| `VITE_FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for redirects |

---

## Documentation

Full technical documentation is in the [Docs/](Docs/) folder:

| Document | What It Covers |
|----------|---------------|
| [Product Overview](Docs/01_PRODUCT_OVERVIEW.md) | Feature-by-feature walkthrough with backend/frontend/DB/cache flows |
| [System Architecture](Docs/02_SYSTEM_ARCHITECTURE.md) | 4-layer stack, request lifecycle, blueprints, route map |
| [Backend Deep Dive](Docs/03_BACKEND_DEEP_DIVE.md) | Factory pattern, dual-DB, JWT auth, Redis, rate limiting, validation |
| [Frontend Deep Dive](Docs/04_FRONTEND_DEEP_DIVE.md) | React 18 architecture, routing, AuthContext, service layer, component tree |
| [Database and Data](Docs/05_DATABASE_AND_DATA.md) | 19 tables across 3 domains, travel DB schema, cache TTLs |
| [Places Engine](Docs/06_PLACES_ENGINE.md) | Search, autocomplete, place details, statistics, trip generation |
| [Expense Engine](Docs/07_EXPENSE_ENGINE.md) | CRUD, settlements, balances, simplified debts, analytics |
| [Group Planner](Docs/08_GROUP_PLANNER.md) | Groups, places, voting, polls, checklist, invitations, events |
| [What We Completed](Docs/09_WHAT_WE_COMPLETED.md) | Phase 0/1A/1B changelog with code-level detail |

---

## Project Status

**Current state:** MVP complete, security hardened, production-ready.

| Module | Status |
|--------|--------|
| Place Search | Working (16,830 places, 82 countries) |
| Trip Planner | Working (rule-based, 3 pacing modes) |
| Expense Engine | Working (4 split types, settlements, analytics) |
| Group Planner | Working (polls, checklist, map, invitations) |
| Auth System | Working (JWT, httpOnly cookies, auto-refresh) |
| Redis Cache | Working (response caching, rate limiter) |

### Roadmap

- Agentic AI integration (smart itinerary generation, chat)
- Real-time collaboration (WebSocket)
- Booking engine (flights, hotels)
- Payment integration (Stripe)
- Mobile app
- Multi-currency support

---

## Repository Structure

```
.
├── Docs/           Product and technical documentation
├── web/
│   ├── backend/    Flask REST API (Python)
│   ├── frontend/   React SPA (Vite)
│   └── database/   SQLite database files
└── README.md
```

---

## License

This project is proprietary. All rights reserved.
