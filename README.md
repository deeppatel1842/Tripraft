# TripRaft

An AI-powered group travel planning and expense management platform. Search 16,830+ places across 82 countries, plan trips collaboratively with real-time chat and polls, split expenses with smart balance tracking, and generate day-by-day itineraries with AI agents.

**Live Landing Page:** [tripraft.vercel.app](https://tripraft.vercel.app)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, React Router 7, React Query 5 |
| Backend | Python 3.11, Flask (factory pattern) |
| Databases | SQLite (app data) + SQLite (16,830 places read-only) |
| Cache | Redis (response caching, rate limiter state, Celery broker) |
| Real-time | Flask-SocketIO (gevent), Socket.IO Client |
| AI | Ollama (self-hosted LLM), circuit breaker pattern |
| Background | Celery 5.4 + Redis broker |
| Auth | JWT (httpOnly cookies + CSRF double-submit), bcrypt 12 rounds |
| Maps | Leaflet + OpenStreetMap |
| Charts | Recharts |
| Validation | Marshmallow schemas (backend), custom (frontend) |
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

### AI Agents
- **Scout Agent**: @scout mention in chat triggers place recommendations from travel DB + web search
- **Crew Agent**: @crew mention for multi-turn conversations (itinerary suggestions, poll creation, budget optimization)
- Explicit user consent required before any AI interaction
- Circuit breaker pattern for LLM resilience (auto-fallback on failure)
- Ollama-based (self-hosted, zero API costs, full data control)

### Real-Time Chat
- WebSocket-based group chat via Flask-SocketIO
- Message reactions, read receipts, typing indicators
- @mention AI agents directly in conversation
- AI responses rendered as interactive cards (place cards, itineraries)

### Document Vault
- Per-group file uploads (images, PDFs, documents)
- Secure file storage with access control
- Download and preview

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
├── backend/                 Python/Flask REST API (5-layer architecture)
│   ├── app/
│   │   ├── api/v1/          25 route blueprints, ~135 endpoints
│   │   ├── core/            Config, DB engine, auth decorators, error handlers
│   │   ├── domain/          4 bounded contexts (users, expenses, groups, ai)
│   │   ├── infrastructure/  auth, cache, db, email, llm, realtime, search
│   │   ├── schemas/         15 Marshmallow validation modules
│   │   ├── services/        25 stateless service classes
│   │   └── workers/         Celery tasks (email, AI, chat, cleanup)
│   ├── alembic/             Database migrations
│   ├── scripts/             DB seeding and migration scripts
│   ├── tests/               Pytest test suite
│   ├── run.py               Entry point
│   └── requirements.txt
│
├── frontend/                React SPA (Vite, code-split routes)
│   └── src/
│       ├── components/      UI organized by feature domain
│       ├── context/         AuthContext (JWT + CSRF + refresh)
│       ├── hooks/           Custom hooks (expense, chat, group, AI)
│       ├── services/        API client modules (axios interceptors)
│       ├── lib/             TanStack Query + IndexedDB persister
│       ├── config/          Environment config
│       ├── styles/          Global CSS
│       └── utils/           Shared helpers
│
├── database/
│   └── travel_data_complete.db  Read-only reference (16,830 places, FTS5)
│
docs/                        Technical documentation
├── PROJECT_OVERVIEW.md
├── ARCHITECTURE.md
├── HLD.md                   High-Level Design with system diagrams
└── features/
    ├── 01_AUTHENTICATION.md
    ├── 02_PLACE_DISCOVERY.md
    ├── 03_AI_TRIP_PLANNER.md
    ├── 04_GROUP_PLANNER.md
    ├── 05_EXPENSE_ENGINE.md
    ├── 06_AI_AGENTS.md
    ├── 07_REALTIME_AND_BACKGROUND.md
    └── 08_CACHING_AND_PERFORMANCE.md
```

---

## API Routes

| Prefix | Module | Auth | Description |
|--------|--------|------|-------------|
| `/api/expense/*` | Expense Engine | JWT | Auth, expense/group/settlement CRUD |
| `/api/groups/*` | Group Planner | JWT | Trip groups, places, polls, checklist |
| `/api/v1/chat/*` | Chat | JWT | Real-time messaging, reactions, read receipts |
| `/api/v1/ai/*` | AI Agents | JWT | Scout/Crew agents, consent management |
| `/api/v1/vault/*` | Vault | JWT | File uploads and document management |
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

Full technical documentation is in the [docs/](docs/) folder:

| Document | What It Covers |
|----------|---------------|
| [Project Overview](docs/PROJECT_OVERVIEW.md) | Feature walkthrough with backend/frontend/DB/cache flows |
| [Architecture](docs/ARCHITECTURE.md) | 5-layer stack, request lifecycle, blueprints, route map |
| [High-Level Design](docs/HLD.md) | System diagrams, data flow, component interactions, deployment |
| [Auth System](docs/features/01_AUTHENTICATION.md) | JWT + CSRF double-submit, token refresh, session management |
| [Place Discovery](docs/features/02_PLACE_DISCOVERY.md) | FTS5 search, autocomplete, place details, statistics |
| [AI Trip Planner](docs/features/03_AI_TRIP_PLANNER.md) | Itinerary generation, pacing modes, PDF export |
| [Group Planner](docs/features/04_GROUP_PLANNER.md) | 6-tab architecture, polls, checklist, map, invitations |
| [Expense Engine](docs/features/05_EXPENSE_ENGINE.md) | 4 split types, settlements, simplified debts, analytics |
| [AI Agents](docs/features/06_AI_AGENTS.md) | Scout and Crew agents, consent architecture, circuit breaker |
| [Realtime & Background](docs/features/07_REALTIME_AND_BACKGROUND.md) | WebSocket events, Celery tasks, beat schedule |
| [Caching & Performance](docs/features/08_CACHING_AND_PERFORMANCE.md) | Redis + IndexedDB dual-layer caching, ETag strategy |

---

## Project Status

**Current state:** Feature-complete, security hardened, production-ready.

| Module | Status |
|--------|--------|
| Place Search | Complete (16,830 places, FTS5, 82 countries) |
| Trip Planner | Complete (rule-based + AI, 3 pacing modes, PDF export) |
| Expense Engine | Complete (4 split types, settlements, analytics, PDF) |
| Group Planner | Complete (6 tabs: places, polls, checklist, chat, vault, events) |
| AI Agents | Complete (Scout + Crew, consent-gated, Ollama, circuit breaker) |
| Real-Time Chat | Complete (SocketIO, reactions, read receipts, AI mentions) |
| Auth System | Complete (JWT + CSRF, httpOnly cookies, auto-refresh) |
| Redis Cache | Complete (dual-layer caching, rate limiter, Celery broker) |
| Background Jobs | Complete (Celery workers + beat scheduler) |

### Roadmap

- Booking engine (flights, hotels)
- Payment integration (Stripe)
- Mobile app (React Native)
- Multi-currency support
- Collaborative real-time editing

---

## Repository Structure

```
.
├── docs/           Technical documentation + HLD
├── web/
│   ├── backend/    Flask REST API (Python, 5-layer architecture)
│   ├── frontend/   React SPA (Vite, code-split routes)
│   └── database/   Travel reference database (SQLite, read-only)
└── README.md
```

---

## License

This project is proprietary. All rights reserved.
