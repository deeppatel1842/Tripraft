# TripRaft — Project Overview

## What is TripRaft?

TripRaft is a full-stack, AI-powered collaborative travel planning and expense management platform. It solves the fragmented travel planning problem: groups currently juggle WhatsApp threads, spreadsheets, Google Docs, Splitwise, and browser bookmarks to plan a single trip. TripRaft consolidates every aspect of group travel — destination discovery, itinerary building, real-time collaboration, expense splitting, and AI-assisted suggestions — into one integrated product.

---

## Product Summary

| Dimension | Detail |
|-----------|--------|
| **Type** | SaaS Web Application (B2C, future B2B) |
| **Frontend** | React 18.2 + Vite 5 + TanStack Query + Socket.IO |
| **Backend** | Python 3.11 / Flask 2.3 + SQLAlchemy 2.0 + Celery 5.4 |
| **Database** | SQLite (dev) / PostgreSQL (prod) + read-only travel reference DB (16k+ places) |
| **Cache** | Redis (session store, rate limiter, task broker, response cache) |
| **Real-time** | Flask-SocketIO with gevent workers |
| **AI** | Local LLM via Ollama (Scout agent) + external Crew AI agent |
| **Auth** | JWT (HS256) + bcrypt + httpOnly cookies + CSRF double-submit |
| **Task Queue** | Celery with Redis broker, 5 periodic beat schedules |
| **Deployment** | Docker + Gunicorn (gevent) |

---

## Codebase Scale

| Metric | Count |
|--------|-------|
| Backend Python files | ~158 |
| Frontend JS/JSX files | ~80+ |
| API route files | 25 |
| REST endpoints | 100+ |
| Service classes | 26 |
| SQLAlchemy models | 45+ |
| Validation schemas | 52+ |
| Celery background tasks | 15+ |
| Database migrations | 9 Alembic versions |
| Test files | 40+ |
| Backend estimated LOC | ~30,000 |
| Frontend estimated LOC | ~15,000 |
| Total estimated LOC | ~45,000+ |

---

## Core Features (What Exists Today)

### 1. Place Discovery Engine
- Full-text search across 16,000+ places in 82 countries
- Hierarchical browsing: Country > State > City > Place
- Autocomplete with debounced suggestions (300ms)
- Filter by cost range, ratings, categories, features
- Sort by rank score, popularity, distance
- Place detail modal with photos, descriptions, map, tags
- ETag-based HTTP caching for search results

### 2. AI Trip Planner
- Single-user itinerary generation powered by Crew AI agents
- Input: city + duration (1-14 days) + pacing (Relaxed / Moderate / Packed)
- Tag-based filtering (exclude/require activity types)
- Output: day-by-day itinerary with stops, times, descriptions, coordinates
- Leaflet map visualization with day-by-day color coding
- Suggested places carousel, packing checklist, travel tips

### 3. Collaborative Group Planner
- Create travel groups with destination, dates, description, budget
- 6-tab interface:
  - **Itinerary** — Day-by-day plan with editable stops and duration tracking
  - **Library** — Saved places with collaborative voting system
  - **Logistics** — Transportation, accommodation, shared logistics
  - **Treasury** — Integrated expense tracking (links to expense engine)
  - **Pulse** — Activity feed with recent changes and notifications
  - **Circle** — Group members, online status, role management
- Invite members via email (7-day expiry, accept/decline/resend)
- Place voting and consensus building
- Group polls (single/multiple choice, optional expiration)
- Collaborative checklists with priority, categories, assignments
- Document vault (upload/download/delete shared files)
- Itinerary export: PDF, iCal
- Group cloning, join-by-code
- Leaflet map panel with day-colored markers and clustering

### 4. Real-time Chat with AI Agents
- WebSocket-powered group messaging (Flask-SocketIO)
- Message history with pagination
- Read receipts and unread counts
- `@scout` — Local LLM agent (Ollama) for place recommendations
  - Consent-gated: requires group opt-in before activation
  - Circuit breaker pattern with graceful fallback
  - Structured JSON output from LLM, validated before rendering
- `@crew` — External AI agent for trip logistics and planning
  - Multi-turn conversations with stateful context
  - Action cards (Question, Confirm, Place, Success)
  - Confirmable actions (delete place, create poll, etc.)
- Online presence tracking (join/leave events)

### 5. Expense Management Engine
- Personal and group expense tracking
- Split types: equal, exact amount, percentage, shares
- Multi-currency support
- Settlement engine:
  - Simplified debt algorithm (minimize transactions)
  - Balance tracking per user per group
  - Cross-group balance aggregation
- Expense groups with member management, join-by-code
- Invitation system (email + in-app, 7-day expiry)
- Expense history with full audit trail (who changed what, when)
- Soft deletes with archive capability
- PDF export of expense reports
- 30-second smart polling with instant socket updates

### 6. Authentication and User Management
- Email/password registration with strength validation (8+ chars, mixed case, digit, special)
- JWT access tokens (15-min expiry) + refresh tokens (30-day expiry)
- httpOnly cookie storage + Bearer header fallback
- CSRF double-submit protection
- 15-minute inactivity auto-logout
- Session management (logout single device, logout all)
- Email verification flow
- Profile management (display name, avatar)
- User search for invitations

### 7. Analytics Dashboard
- Personal spending trends and breakdowns
- Group spending comparisons
- Recharts-powered visualizations
- Admin-level organizational analytics

### 8. Admin Data Management
- Place CRUD (create, update, delete)
- Bulk import/export (CSV/JSON)
- Data validation pipeline
- Ingestion audit logging
- Country/State/City/Photo/Tag management

---

## Infrastructure Features

### Caching Strategy
- Redis response caching with `@cache_response` decorator
- 25 distinct cache TTL configurations (per endpoint type)
- Pattern-based cache invalidation on write operations
- Graceful fallback when Redis is unavailable
- IndexedDB persistence on frontend (60-min TTL, reduces API calls ~70%)

### Rate Limiting
- Per-operation rate limits (17 categories)
- Per-user and per-IP bucketing
- Redis-backed with Flask-Limiter

### Background Processing (Celery)
- Email delivery (invitations, verification, password reset, notifications)
- Chat message archival
- AI mention processing (Scout + Crew)
- Session cleanup (expired tokens)
- Analytics aggregation (daily metrics)
- Search cache warmup
- Soft-delete record archival
- Agent log purging

### Resilience
- Circuit breaker pattern (pybreaker) for external services (Ollama, APIs)
- Exponential backoff retries on 5xx responses
- Idempotency key support for safe request retries
- Dead-letter queue for failed Celery tasks

### Security
- Security headers middleware
- Input sanitization (HTML/SQL)
- bcrypt password hashing (12 rounds)
- JWT key rotation support
- CORS configuration with explicit origins
- Rate limiting on all endpoints
- Request/response structured logging

### Database Architecture
- Primary database: `tripraft.db` (SQLite dev / PostgreSQL prod)
  - 26 tables with UUIDv7 primary keys
  - Foreign key enforcement
  - Composite indexes for common query patterns
  - Materialized views for expensive aggregations (PostgreSQL)
  - Date-range partitioning for large tables (PostgreSQL)
- Travel reference database: `travel_data_complete.db` (read-only SQLite)
  - 16k+ places across 82 countries
  - Full-text search (FTS5) index
  - Thread-safe connection management

---

## Market Research

### The Problem
Travel planning for groups is fragmented. A typical group trip involves:
- 5-10 browser tabs for destination research
- A shared Google Doc or Notes app for itinerary drafts
- WhatsApp/Telegram threads that bury important decisions
- Splitwise or a spreadsheet for expenses
- Doodle or group polls for dates/activities
- Google Maps for location bookmarking
- No single source of truth; plans get lost, conflicts arise

### Target Market
| Segment | Size | TripRaft Fit |
|---------|------|------------|
| **Millennial/Gen-Z group travelers** | 600M+ globally | Primary segment. Groups of 3-10 friends planning weekend/vacation trips |
| **Family vacation planners** | 150M+ households (US/EU) | Multi-generational trips with shared budgets and logistics |
| **Corporate team retreats** | $50B+ market (offsites, retreats) | Future B2B play with team collaboration features |
| **Digital nomad communities** | 35M+ globally | Collaborative trip planning for remote workers traveling together |
| **Study abroad / backpacker groups** | 30M+ annual outbound students | Budget-conscious, itinerary-heavy use case |

### Market Size
| Metric | Value |
|--------|-------|
| Global travel market (2025) | $1.1T+ |
| Online travel market | $520B (growing 9% CAGR) |
| Travel planning tools TAM | $12B |
| Group travel planning SAM | $3.5B |
| Expense splitting apps market | $2.1B |
| **TripRaft SOM (Year 1 target)** | **$5-10M ARR at 50K paid users** |

### Competitive Landscape

| Competitor | Strength | TripRaft Advantage |
|-----------|----------|-------------------|
| **Splitwise** | Expense splitting standard | TripRaft integrates expenses INTO the trip planning flow. Not a separate app. |
| **TripIt** | Itinerary organization | No collaboration, no expenses, no real-time editing. |
| **Wanderlog** | Trip planning + maps | Limited group features, no expense splitting, no AI agents. |
| **Google Travel** | Brand + data moat | No group collaboration, no expenses, no chat. |
| **Notion/Docs** | Flexible templates | No travel-specific features, no expense engine, no maps, no AI. |
| **WhatsApp Groups** | Ubiquitous messaging | Messages get buried, no structured data, no expense tracking. |

### TripRaft Differentiators
1. **All-in-one**: Discovery + Planning + Collaboration + Expenses + AI — no app switching
2. **Real-time collaboration**: WebSocket-powered group editing, chat, presence
3. **AI agents in context**: @scout and @crew live inside the group chat, not a separate tool
4. **Consent-gated AI**: Users opt-in to AI features per group (privacy-first)
5. **Expense engine embedded**: Treasury tab inside the group planner, not an afterthought
6. **16k+ place database**: Rich discovery without relying solely on Google APIs
7. **Offline-capable caching**: IndexedDB persistence reduces API dependency

### Revenue Model (Planned)
| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 2 groups, 5 members/group, basic place search, manual itinerary |
| **Pro** | $9.99/mo | Unlimited groups, AI agents, PDF/iCal export, advanced analytics |
| **Team** | $24.99/mo | 50 members, admin controls, priority support, API access |
| **Enterprise** | Custom | SSO, custom integrations, SLA, dedicated support |

---

## Future Roadmap

### Phase 5 — AI Enhancement (Next)
- [ ] Multi-modal AI: image recognition for receipts (expense auto-capture)
- [ ] AI itinerary optimization (reorder stops by proximity, opening hours)
- [ ] AI budget prediction based on destination + group size + duration
- [ ] Natural language trip modification ("Move the museum to Day 3")
- [ ] AI-generated packing lists based on destination weather + activities

### Phase 6 — Mobile & Offline
- [ ] React Native mobile app (iOS + Android)
- [ ] Full offline mode with background sync
- [ ] Push notifications (Firebase Cloud Messaging)
- [ ] Location-based reminders (nearby saved places)

### Phase 7 — Social & Community
- [ ] Public trip templates (share itineraries with community)
- [ ] Travel blog integration
- [ ] Friend connections and trip history
- [ ] Reputation system (trip reviews, place contributions)

### Phase 8 — Monetization & Scale
- [ ] Stripe payment integration for Pro/Team tiers
- [ ] Affiliate partnerships (hotels, flights, activities)
- [ ] B2B API for travel agencies and corporate travel managers
- [ ] White-label solution for travel companies

### Phase 9 — Data & Intelligence
- [ ] PostgreSQL migration for production (materialized views, partitioning already scripted)
- [ ] Recommendation engine (collaborative filtering on user behavior)
- [ ] Dynamic pricing data integration
- [ ] Weather and event correlation for trip timing suggestions

### Phase 10 — Platform
- [ ] Plugin marketplace for third-party extensions
- [ ] Webhook API for external integrations
- [ ] Multi-language support (i18n)
- [ ] Accessibility (WCAG 2.1 AA compliance)

---

## Tech Debt & Known Gaps

| Area | Issue | Priority |
|------|-------|----------|
| Auth | Firebase fallback code still present (legacy migration) | Medium |
| Locations API | ~1000-line deprecated routes in `locations.py` | Low (FTS replaces) |
| Users API | Parallel `users.py` and `auth.py` routes (legacy compat) | Medium |
| Testing | Frontend test coverage is minimal | High |
| Email | SMTP disabled by default (EMAIL_ENABLED=false) | Medium |
| Mobile | No responsive optimization for mobile browsers | High |
| Monitoring | No APM or error tracking (Sentry, Datadog) | High |
| CI/CD | No automated pipeline (GitHub Actions not configured) | High |

---

## How to Run Locally

### Backend
```bash
cd web/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python run.py
```

### Frontend
```bash
cd web/frontend
npm install
cp .env.example .env.local
npm run dev
```

### Redis (required for cache + Celery)
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Celery Worker (background tasks)
```bash
cd web/backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

---

*TripRaft — Discover. Plan. Explore.*
