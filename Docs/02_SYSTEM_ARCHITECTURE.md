# TripRaft -- System Architecture

This document maps every layer of the system: how the frontend talks to the backend, how requests flow through the middleware stack, which databases and caches are hit, and how each API section is organized.

---

## Big Picture

```mermaid
flowchart TD
    subgraph Client["Browser (React 18 SPA)"]
        A[App.jsx + React Router 7]
        B[AuthContext<br/>sqlAuthService.js]
        C[expenseApi.js]
        D[groupPlannerApi.js]
        E[placeSearchService.js]
        F[tripPlannerService.js]
    end

    subgraph Proxy["Vite Dev Proxy"]
        G["/api/* -> http://127.0.0.1:5000"]
    end

    subgraph Server["Flask Application (factory pattern)"]
        H[create_app]
        I[CORS + Compress + Security Headers]
        J[Request Logger Middleware]
        K[Rate Limiter<br/>Flask-Limiter]
        L[17 Blueprints<br/>135 Routes]
        M[Auth Decorators<br/>require_auth / optional_auth]
        N[Marshmallow + Pydantic<br/>Validation Layer]
        O[Service Layer<br/>15 service classes]
        P[Domain Models<br/>SQLAlchemy ORM]
    end

    subgraph Data["Data Stores"]
        Q[(tripraft.db<br/>SQLAlchemy<br/>Read-Write)]
        R[(travel_data_complete.db<br/>Raw sqlite3<br/>Read-Only)]
        S[(Redis Cloud<br/>30MB Free Tier)]
    end

    A --> G
    G --> H
    H --> I --> J --> K --> L
    L --> M --> N --> O --> P
    P --> Q
    O --> R
    L --> S

    C -->|"/api/expense/*"| L
    D -->|"/api/v2/group-planner/*"| L
    E -->|"/api/v1/place-search/*"| L
    F -->|"/api/trip-planner/*"| L
    B -->|"/api/expense/login,signup,me"| L
```

---

## Request Lifecycle (Step by Step)

Every API request passes through this exact sequence:

```mermaid
sequenceDiagram
    participant Browser
    participant Vite as Vite Dev Proxy<br/>(:5173 -> :5000)
    participant Flask
    participant CORS as CORS Middleware
    participant Logger as Request Logger
    participant Security as Security Headers
    participant RateLimit as Rate Limiter
    participant Auth as @require_auth
    participant Validate as Marshmallow/Pydantic
    participant Service as Service Layer
    participant DB as Database
    participant Cache as Redis Cache

    Browser->>Vite: GET /api/v1/place-search/search?q=tokyo
    Vite->>Flask: Forward to localhost:5000
    Flask->>CORS: Check Origin header against CORS_ORIGINS list
    CORS-->>Flask: Allow (or reject with 403)
    Flask->>Logger: log_request() -> record start_time in g
    Flask->>RateLimit: Check IP against configured limits
    RateLimit->>Cache: GET ratelimit:{ip}:{endpoint}
    
    alt Rate Limited
        Cache-->>RateLimit: Over limit
        RateLimit-->>Browser: 429 Rate limit exceeded
    else Allowed
        Flask->>Auth: Extract token from cookie or Authorization header
        Auth->>Auth: Decode JWT, verify type='access', check expiry
        Auth->>DB: Verify user exists (SELECT users WHERE id = ?)
        Auth->>Flask: Set g.current_user, g.user_id, g.user_email
        Flask->>Validate: Schema.load(request.json or request.args)
        Validate-->>Flask: Validated data (or 400/422 error)
        Flask->>Service: Call service method with validated data
        Service->>Cache: Check Redis for cached response
        Service->>DB: Query if cache miss
        Service->>Cache: Store result with TTL
        Service-->>Flask: Response data
        Flask->>Security: add_security_headers(response)
        Flask->>Logger: log_response() -> record duration
        Flask-->>Browser: JSON response + security headers
    end
```

---

## Application Factory (`create_app()`)

The Flask app is built in `app/api/factory.py` using the factory pattern. The initialization order matters:

```mermaid
flowchart TD
    A[create_app] --> B[Load Config<br/>get_config -> Dev/Prod/Test]
    B --> C[Setup Logging<br/>JSON in prod, text in dev]
    C --> D[Init Request Logger<br/>before_request + after_request hooks]
    D --> E[Configure CORS<br/>origins from CORS_ORIGINS env var]
    E --> F[Enable Gzip Compression<br/>Flask-Compress, level 6, min 500 bytes]
    F --> G[Init tripraft.db<br/>SQLAlchemy create_all]
    G --> H[Init travel_data_complete.db<br/>raw sqlite3 + location_repository]
    H --> I[Init Redis<br/>ping test, graceful fallback]
    I --> J[Init Rate Limiter<br/>Flask-Limiter with memory or Redis storage]
    J --> K[Register 17 Blueprints<br/>each in try/except for graceful degradation]
    K --> L[Register Middleware<br/>security headers, CORS fallback]
    L --> M[Register Error Handlers<br/>404, 405, 429, 500, generic Exception]
    M --> N[Register Root Endpoints<br/>/, /health]
    N --> O[Log Route Count<br/>135 routes registered]
    O --> P[Return app]
```

Each blueprint registration is wrapped in `try/except` so a broken module does not prevent the rest of the app from starting.

---

## Blueprint Map (All 17)

The backend has three distinct API sections, each with its own URL prefix and service layer:

### Expense Engine (`/api/expense/*`)

| Blueprint | File | Prefix | Routes | Purpose |
|-----------|------|--------|--------|---------|
| auth_bp | `v1/auth.py` | `/api/expense` | signup, login, logout, me, refresh, check-email | User authentication |
| groups_sql_bp | `v1/expense_groups.py` | `/api/expense` | groups CRUD, groups/:id/full, mega-bootstrap, extreme-dashboard | Expense groups |
| expenses_sql_bp | `v1/expenses.py` | `/api/expense` | expenses CRUD, expenses/:id/history, expenses/:id/splits | Expense records |
| settlements_sql_bp | `v1/settlements.py` | `/api/expense` | settlements CRUD, confirm, cancel, simplified debts | Debt settlements |
| invitations_sql_bp | `v1/expense_invitations.py` | `/api/expense` | invitations CRUD, accept, decline, group invitations | Email invitations |

### Group Planner (`/api/v2/group-planner/*`)

| Blueprint | File | Prefix | Routes | Purpose |
|-----------|------|--------|--------|---------|
| groups_bp | `v1/gp_groups.py` | `/api/v2/group-planner` | groups CRUD, members, budget, itinerary-document | Travel groups |
| places_bp | `v1/gp_places.py` | `/api/v2/group-planner` | places CRUD, vote, remarks | Group places + voting |
| polls_bp | `v1/gp_polls.py` | `/api/v2/group-planner` | polls CRUD, vote | Group polls |
| checklist_bp | `v1/gp_checklist.py` | `/api/v2/group-planner` | checklist items CRUD, toggle | Task checklists |
| invitations_bp | `v1/gp_invitations.py` | `/api/v2/group-planner` | invitations CRUD, accept, resend | Trip invitations |
| events_bp | `v1/gp_events.py` | `/api/v2/group-planner` | destination events | Ticketmaster integration |
| group_planner_v2 | `v1/gp_destinations.py` | `/api/v2/group-planner` | destination-search | Destination search |

### Platform Services (`/api/v1/*` and others)

| Blueprint | File | Prefix | Routes | Purpose |
|-----------|------|--------|--------|---------|
| users_bp | `v1/users.py` | `/api/v1/users` | register, login, profile, sessions | Clean auth (v1) |
| locations_bp | `v1/locations.py` | `/api/v1/locations` | countries, states, cities, autocomplete | Hierarchical location data |
| place_search_bp | `v1/places.py` | `/api/v1/place-search` | search, autocomplete, stats, place/:id | Place search engine |
| trip_planner_bp | `v1/trips.py` | `/api/trip-planner` | generate, cities, pacing-options | AI trip generation |
| health_bp | `health.py` | `/api/health` | health, detailed | Health checks |
| route_viewer_bp | `route_viewer.py` | `/api/routes` | list all registered routes | Debug |

---

## Four-Layer Architecture

```mermaid
flowchart TD
    subgraph "Layer 1: API Routes"
        A[17 Blueprint files in app/api/v1/]
        A1["HTTP concerns only:<br/>parse request, call service, return JSON"]
    end
    
    subgraph "Layer 2: Validation"
        B[app/schemas/common.py<br/>Marshmallow schemas]
        B2[app/schemas/users.py<br/>Pydantic models]
        B3["Validates: types, lengths, ranges, enums<br/>Returns: clean dict or 422 error"]
    end
    
    subgraph "Layer 3: Services"
        C[app/services/<br/>15 service files]
        C1["Business logic only:<br/>calculations, authorization checks,<br/>transaction coordination"]
    end
    
    subgraph "Layer 4: Domain + Infrastructure"
        D[app/domain/<br/>Models + Repositories]
        D2[app/infrastructure/<br/>Auth, Cache, DB, Email]
        D3["Data access:<br/>ORM queries, raw SQL,<br/>Redis get/set, SMTP send"]
    end

    A --> B --> C --> D
    A --> B2 --> C
    C --> D2
```

### Layer Responsibilities

| Layer | Files | Does | Does NOT |
|-------|-------|------|----------|
| Routes | `app/api/v1/*.py` | Parse HTTP, call schema, call service, format response | Query DB, contain business logic, access Redis directly |
| Schemas | `app/schemas/*.py` | Validate types, enforce constraints, sanitize input | Access any external system |
| Services | `app/services/*.py` | Business logic, authorization, transaction coordination | Know about HTTP, parse request objects |
| Domain | `app/domain/*/models.py` | Define table structure, relationships, `to_dict()` | Contain business logic |
| Infrastructure | `app/infrastructure/*` | DB connections, auth, cache, email | Contain business logic |

---

## Two Database Architecture

```mermaid
flowchart LR
    subgraph AppDB["tripraft.db (SQLAlchemy ORM)"]
        direction TB
        U[users + user_sessions]
        E[expenses + expense_splits<br/>+ group_balances + settlements<br/>+ expense_invitations + expense_history]
        G[gp_groups + gp_members<br/>+ gp_places + gp_place_votes<br/>+ gp_polls + gp_poll_options<br/>+ gp_poll_votes + gp_checklist_items<br/>+ gp_activities + gp_invitations]
    end

    subgraph TravelDB["travel_data_complete.db (raw sqlite3)"]
        direction TB
        C[countries -> states -> cities -> places]
        D["16,830 places<br/>82 countries<br/>888 cities"]
    end

    subgraph Connection["Connection Patterns"]
        ORM["SQLAlchemy ORM<br/>SessionLocal + scoped_session<br/>StaticPool for SQLite<br/>PRAGMA foreign_keys=ON"]
        RAW["Raw sqlite3<br/>TravelDatabase singleton<br/>connect-per-request<br/>Row factory enabled"]
    end

    AppDB --- ORM
    TravelDB --- RAW
```

**Why two databases:**
- `tripraft.db` is read-write, holds user-generated data, uses ORM for relationships and migrations
- `travel_data_complete.db` is read-only reference data, uses raw sqlite3 for performance, no ORM overhead

**Connection management:**
- App DB: `scoped_session` (thread-safe), `StaticPool` (single connection for SQLite), `PRAGMA foreign_keys=ON` enforced on every connection
- Travel DB: `TravelDatabase` singleton class, opens/closes connection per request, `Row factory = sqlite3.Row` for dict-like access

---

## Cache Architecture

```mermaid
flowchart TD

    %% ============================
    %% READ PATH (GET requests)
    %% ============================

    A[API Request GET] --> B{Route has cache_response}
    B -->|Yes| C[Build cache key: MD5 path plus query]
    C --> D{Key exists in Redis}

    D -->|Hit| E[Return cached JSON with X-Cache HIT]
    D -->|Miss| F[Execute route handler]
    F --> G[Serialize response to JSON]
    G --> H[Set key with TTL in Redis]
    H --> E

    B -->|No| F

    %% ============================
    %% WRITE PATH (POST PUT DELETE)
    %% ============================

    I[Write Operation POST PUT DELETE] --> J[Service performs mutation]
    J --> K[Invalidate cache patterns]
    K --> L[Redis delete pattern e.g. expense_groups:*]
    L --> M[Next GET triggers fresh DB query]

```

### Cache Key Strategy

| Prefix | Source | TTL | Example Key |
|--------|--------|-----|-------------|
| `route:` | `@cache_response` decorator | Varies | `route:a3f8b2c1d4e5` |
| `places:` | Place search results | 5 min | `places:search:tokyo:500` |
| `locations:` | Autocomplete + lists | 5-60 min | `locations:autocomplete:par:city` |
| `expense_groups:` | Group balances/data | 30s-1min | `expense_groups:5:balances` |

### Redis Client Architecture

`RedisClient` is a singleton (`redis_client`) initialized in `app/infrastructure/cache/redis.py`:

- **Lazy import:** Redis package imported only when needed
- **Graceful fallback:** If Redis unavailable, all get/set/delete return None/False/0 (no crashes)
- **JSON serialization:** `get_json()` / `set_json()` methods handle JSON encoding/decoding
- **Pattern delete:** `delete_pattern("prefix:*")` for bulk invalidation using KEYS + DELETE
- **Properties:** `redis_client.available` to check if Redis is connected

---

## Auth Architecture

```mermaid
flowchart TD
    A[Incoming Request] --> B[get_access_token]
    B --> C{Authorization header?}
    C -->|Yes| D[Extract Bearer token]
    C -->|No| E{access_token cookie?}
    E -->|Yes| F[Use cookie value]
    E -->|No| G[Return 401]
    
    D --> H[_decode_jwt]
    F --> H
    H --> I{Valid JWT?<br/>type = 'access'?}
    I -->|Yes| J[Set g.current_user<br/>g.user_id, g.user_email]
    I -->|No| K{Try Firebase fallback}
    K -->|Valid| J
    K -->|Invalid| G
    
    J --> L[_ensure_user_exists]
    L --> M{User in DB?}
    M -->|Yes| N[Continue to route handler]
    M -->|No| O[CREATE user row<br/>then continue]
```

### Three Auth Decorators

| Decorator | Used By | Behavior |
|-----------|---------|----------|
| `@require_auth` | All protected routes | 401 if no valid token. Sets `g.current_user` |
| `@require_refresh_token` | `/api/expense/refresh` | Expects refresh token in cookie or body |
| `@optional_auth` | Some read endpoints | Sets `g.current_user` if token present, continues either way |

### Dual Token Delivery

The backend sends tokens both as httpOnly cookies AND in the JSON response body:

```
Set-Cookie: access_token=eyJ...; HttpOnly; Secure; SameSite=Lax; Max-Age=3600
Set-Cookie: refresh_token=eyJ...; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000
Body: { "access_token": "eyJ...", "refresh_token": "eyJ..." }
```

Web clients use cookies (XSS-safe). Mobile/API clients use Bearer header from the body.

---

## Security Layers

```mermaid
flowchart LR
    A[Request] --> B[CORS<br/>Explicit origins only]
    B --> C[Rate Limiter<br/>IP-based limits]
    C --> D[JWT Verification<br/>HS256 signature check]
    D --> E[Input Validation<br/>Marshmallow/Pydantic]
    E --> F[SQL Parameterization<br/>ORM prevents injection]
    F --> G[Response]
    G --> H[Security Headers<br/>X-Frame-Options: DENY<br/>X-XSS-Protection: 1<br/>HSTS: 31536000<br/>Referrer-Policy: strict-origin]
```

### Security Headers (every response)

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-XSS-Protection | 1; mode=block | Browser XSS filter |
| Referrer-Policy | strict-origin-when-cross-origin | Control referer leaking |
| Permissions-Policy | camera=(), microphone=(), geolocation=(self) | Restrict browser APIs |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | Force HTTPS |

### Rate Limits

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Auth (login, signup) | 5 | per minute |
| Search | 30 | per minute |
| Write (create, update) | 20 | per minute |
| Delete | 10 | per minute |
| General read | 100 | per minute |

Rate limit state is stored in Redis (or in-memory fallback). Key pattern: `ratelimit:{ip}:{endpoint}`.

---

## Error Handling

### Exception Hierarchy

```mermaid
classDiagram
    class AppError {
        +status_code: 500
        +message: str
        +payload: dict
        +to_dict()
    }
    class ValidationError {
        +status_code: 400
    }
    class AuthenticationError {
        +status_code: 401
    }
    class AuthorizationError {
        +status_code: 403
    }
    class NotFoundError {
        +status_code: 404
    }
    class ConflictError {
        +status_code: 409
    }
    class RateLimitError {
        +status_code: 429
    }
    class ExternalServiceError {
        +status_code: 502
    }

    AppError <|-- ValidationError
    AppError <|-- AuthenticationError
    AppError <|-- AuthorizationError
    AppError <|-- NotFoundError
    AppError <|-- ConflictError
    AppError <|-- RateLimitError
    AppError <|-- ExternalServiceError
```

### Standardized Response Format

Every API response follows this structure:

```json
// Success
{
    "success": true,
    "message": "Success",
    "data": { ... },
    "pagination": { "total": 100, "limit": 50, "offset": 0, "has_more": true }
}

// Error
{
    "success": false,
    "message": "Validation failed",
    "data": null,
    "errors": { "email": ["Not a valid email address"] }
}
```

Response helpers in `app/api/utils/responses.py`: `success_response()`, `error_response()`, `paginated_response()`, `not_found_response()`.

---

## Frontend-Backend Data Flow Summary

```mermaid
flowchart TD
    subgraph "Frontend Services"
        A[sqlAuthService.js<br/>POST /api/expense/login,signup,refresh]
        B[expenseApi.js<br/>All /api/expense/* routes<br/>Singleton with getFreshToken]
        C[groupPlannerApi.js<br/>All /api/v2/group-planner/* routes<br/>Singleton with getFreshToken]
        D[placeSearchService.js<br/>GET /api/v1/place-search/* routes<br/>No auth required]
        E[tripPlannerService.js<br/>POST /api/trip-planner/generate<br/>GET /api/trip-planner/cities]
    end

    subgraph "Backend Blueprints"
        F[auth_bp + groups_sql_bp<br/>+ expenses_sql_bp + settlements_sql_bp<br/>+ invitations_sql_bp]
        G[groups_bp + places_bp<br/>+ polls_bp + checklist_bp<br/>+ invitations_bp + events_bp<br/>+ destinations_bp]
        H[place_search_bp<br/>+ locations_bp]
        I[trip_planner_bp]
    end

    A --> F
    B --> F
    C --> G
    D --> H
    E --> I
```

Each frontend service class:
1. Gets a fresh JWT token via `sqlAuthService.getIdToken()`
2. Attaches it as `Authorization: Bearer {token}` header
3. Sets `credentials: 'include'` to send httpOnly cookies
4. Uses `handleResponse()` to parse JSON and throw on HTTP errors

---

## Deployment Architecture (Current)

```mermaid
flowchart LR
    subgraph Dev["Development"]
        A[Vite :5173<br/>React + HMR] -->|proxy /api/*| B[Flask :5000<br/>debug mode]
        B --> C[tripraft.db<br/>local file]
        B --> D[travel_data_complete.db<br/>local file]
        B --> E[Redis Cloud<br/>remote 30MB]
    end
```

| Component | Dev | Production Target |
|-----------|-----|-------------------|
| Frontend | Vite dev server :5173 | Vercel static hosting |
| Backend | Flask dev server :5000 | Docker + Gunicorn (4 workers) |
| App DB | SQLite local file | PostgreSQL (planned) |
| Travel DB | SQLite local file | Keep as-is or Meilisearch |
| Cache | Redis Cloud 30MB | Redis Cloud or self-hosted |
| Proxy | Vite dev proxy | Nginx reverse proxy |
