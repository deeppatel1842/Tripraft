# TripRaft -- Product Documentation

This is the single source of truth for everything about TripRaft. What it is, how it works today, and where it's going.

Written by the team, for the team (and for anyone doing due diligence).

---

## What's Inside

### Current Product (How Things Work Today)

Every doc below includes detailed backend, frontend, database, and cache flow explanations with Mermaid sequence diagrams.

| Doc | What It Covers |
|-----|---------------|
| [01_PRODUCT_OVERVIEW.md](01_PRODUCT_OVERVIEW.md) | Product overview with feature-by-feature backend/frontend/DB/cache flows for all 5 engines |
| [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | Full architecture: 4-layer stack, request lifecycle, 15 blueprints, 135 routes, module map |
| [03_BACKEND_DEEP_DIVE.md](03_BACKEND_DEEP_DIVE.md) | Every backend component: factory, config, dual-DB connections, JWT auth, Redis, rate limiting, validation, email, middleware |
| [04_FRONTEND_DEEP_DIVE.md](04_FRONTEND_DEEP_DIVE.md) | React 18 architecture: routing, AuthContext, 5 service files, React Query hooks, component tree, all major flows |
| [05_DATABASE_AND_DATA.md](05_DATABASE_AND_DATA.md) | 19 tables across 3 domains (exact columns from SQLAlchemy models), travel DB schema, cache TTLs, end-to-end data flows |
| [06_PLACES_ENGINE.md](06_PLACES_ENGINE.md) | 6 complete flows: search, autocomplete, place details, statistics, trip generation, city search |
| [07_EXPENSE_ENGINE.md](07_EXPENSE_ENGINE.md) | 11 complete flows: CRUD expenses, settlements, balances, simplified debts, history, mega-bootstrap |
| [08_GROUP_PLANNER.md](08_GROUP_PLANNER.md) | 11 complete flows: groups, places, voting, polls, checklist, itinerary, invitations, events, expense linking |
| [09_WHAT_WE_COMPLETED.md](09_WHAT_WE_COMPLETED.md) | Phase 0/1A/1B changes with code-level detail: 22 files secured, 1,604 lines removed, Redis caching, 15 schemas, httpOnly cookies |

### Future Plans

| Folder | What It Covers |
|--------|---------------|
| [B2C/](B2C/) | Consumer product roadmap -- phases, features, AI, monetization |
| [B2B/](B2B/) | Business/enterprise play -- white-label, API, corporate travel |

### Research & Business

| Doc | What It Covers |
|-----|---------------|
| [INDUSTRY_RESEARCH.md](INDUSTRY_RESEARCH.md) | Travel tech market analysis, competitor landscape, opportunity sizing |
| [LAUNCH_COST_ANALYSIS.md](LAUNCH_COST_ANALYSIS.md) | What it actually costs to go live and scale |
| [MONETIZATION_STRATEGY.md](MONETIZATION_STRATEGY.md) | How we make money, pricing tiers, revenue projections |

---

## Quick Context

- **Stack**: React 18 + Vite 5 frontend, Python/Flask backend (135 routes, 15 blueprints), SQLite databases (2), Redis cache (30MB)
- **Live Features**: Places search (16,830 places, 82 countries), Group planner with voting/polls/checklist, Expense splitting with 4 split types, Trip planner with day-by-day itinerary
- **Auth**: JWT with httpOnly cookies + Bearer header dual delivery, bcrypt 12 rounds, 1hr access / 30d refresh
- **Status**: MVP complete, security hardened (Phase 0), code consolidated (Phase 1A), production-ready (Phase 1B)
- **Next**: AI integration, booking engine, real-time collaboration, payment integration
