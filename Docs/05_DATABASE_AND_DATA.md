# TripRaft -- Database and Data

Every table, every column, every relationship, every cache key. Two databases, one cache layer, zero guesswork.

---

## The Two Database Architecture

TripRaft runs two completely separate SQLite databases with different purposes, access patterns, and connection strategies:

| Property | Application Database | Travel Reference Database |
|----------|---------------------|--------------------------|
| File | `web/database/tripraft.db` | `web/backend/data/travel_data_complete.db` |
| Engine | SQLAlchemy ORM (`create_engine`) | Raw `sqlite3` (standard library) |
| Access | Read-Write | Read-Only |
| Connection | Scoped session, `StaticPool` | Per-request open/close |
| Tables | 19 tables across 3 domains | 4 tables (countries, states, cities, places) |
| Data | User-generated (expenses, groups, votes) | Pre-curated travel reference (16,830 places) |
| Schema management | `Base.metadata.create_all()` | None (shipped as-is) |
| Connection file | `infrastructure/db/connection.py` | `infrastructure/db/travel_db.py` |

```mermaid
graph TB
    subgraph "Application Database (tripraft.db)"
        APPDB[(SQLAlchemy ORM<br/>Read-Write<br/>19 tables)]
        APPDB --> U["Users Domain<br/>users, user_sessions"]
        APPDB --> E["Expense Domain<br/>groups, group_members, expenses,<br/>expense_splits, settlements,<br/>group_balances, invitations,<br/>expense_history"]
        APPDB --> G["Group Planner Domain<br/>travel_groups, gp_group_members,<br/>gp_places, gp_place_votes,<br/>gp_polls, gp_poll_votes,<br/>gp_invitations, gp_checklist_items,<br/>gp_itinerary_documents,<br/>gp_group_activities"]
    end

    subgraph "Travel Reference Database"
        TRVDB[(Raw sqlite3<br/>Read-Only<br/>4 tables)]
        TRVDB --> CT["countries: 82"]
        TRVDB --> ST["states: 800+"]
        TRVDB --> CI["cities: 888"]
        TRVDB --> PL["places: 16,830"]
    end

    subgraph "Cache Layer"
        REDIS[(Redis Cloud<br/>30MB free tier)]
    end

    SVC["Service Layer"] -->|"SQLAlchemy Session"| APPDB
    SVC -->|"sqlite3.connect()"| TRVDB
    SVC <-->|"@cache_response decorator"| REDIS
```

### Why Two Databases?

1. **Travel data never changes at runtime.** It was curated offline, scored, and exported. No ORM overhead needed -- raw SQL is faster.
2. **App data changes constantly.** Every expense, vote, and invitation needs transaction management (`session.commit()` / `session.rollback()`).
3. **They scale independently.** The travel DB can be swapped for PostgreSQL full-text search or Meilisearch. The app DB migrates to PostgreSQL when concurrent writes matter.

---

## Application Database Connection (`infrastructure/db/connection.py`)

```mermaid
flowchart TD
    A["connection.py loads"] --> B["Resolve path: web/database/tripraft.db"]
    B --> C{"DATABASE_URL env var set?"}
    C -->|No| D["SQLite: StaticPool, check_same_thread=False"]
    C -->|Yes, starts with sqlite| D
    C -->|Yes, postgres://| E["PostgreSQL: pool_size=10, max_overflow=20, pool_pre_ping=True"]
    D --> F["PRAGMA foreign_keys=ON (event listener)"]
    F --> G["SessionLocal = sessionmaker(bind=engine)"]
    G --> H["db = scoped_session(SessionLocal)"]
    
    I["init_db() called from factory.py"] --> J["Import all domain models"]
    J --> K["users.models -> expenses.models -> group_planner.models"]
    K --> L["Base.metadata.create_all(bind=engine)"]
    L --> M["Register teardown: db.remove() on request end"]
```

**Key implementation details:**
- `StaticPool` reuses a single connection for SQLite (thread-safe with `check_same_thread=False`)
- `PRAGMA foreign_keys=ON` enforced via SQLAlchemy event listener on every new connection
- `scoped_session` provides thread-local sessions (one session per request)
- `get_db()` context manager: auto-commits on success, auto-rollbacks on exception
- `init_db()` eagerly imports all 3 domain model modules so `create_all()` knows every table

### Session lifecycle per request:

```mermaid
sequenceDiagram
    participant Request
    participant Flask
    participant Session as scoped_session (db)
    participant SQLite as tripraft.db

    Request->>Flask: HTTP request arrives
    Flask->>Session: Route handler accesses db
    Session->>Session: Create thread-local Session if none exists
    Session->>SQLite: Execute queries
    
    alt Success
        Session->>SQLite: COMMIT
    else Exception
        Session->>SQLite: ROLLBACK
    end
    
    Flask->>Session: @app.teardown_appcontext
    Session->>Session: db.remove() -> close + return to pool
```

---

## Application Database Schema

### Users Domain (2 tables)

```mermaid
erDiagram
    users {
        int id PK "autoincrement"
        string email UK "unique, indexed, max 255"
        string password_hash "bcrypt, max 255"
        string display_name "max 100"
        text photo_url
        string phone "max 20"
        string default_currency "default USD, max 3"
        boolean is_active "default true"
        boolean email_verified "default false"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
        datetime last_login
    }

    user_sessions {
        int id PK "autoincrement"
        int user_id FK "users.id, CASCADE"
        string refresh_token "max 500, indexed"
        text device_info
        string ip_address "max 45"
        datetime expires_at "required"
        datetime created_at "func.now()"
        datetime last_used
    }

    users ||--o{ user_sessions : "has sessions"
```

**Indexes:** `idx_user_sessions_token` on `refresh_token`, `idx_user_sessions_user` on `user_id`.

### Expense Domain (8 tables)

```mermaid
erDiagram
    groups {
        int id PK "autoincrement"
        string name "required, max 100"
        text description
        string currency "default USD, max 3"
        int created_by FK "users.id"
        string group_code UK "max 20"
        string category "max 50 (trip, home, couple, friends)"
        text image_url
        boolean is_active "default true"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
    }

    group_members {
        int id PK "autoincrement"
        int group_id FK "groups.id, CASCADE"
        int user_id FK "users.id"
        string role "owner/admin/member, max 20"
        boolean is_active "default true"
        datetime joined_at "func.now()"
        datetime removed_at
        int removed_by FK "users.id"
    }

    expenses {
        int id PK "autoincrement"
        int group_id FK "groups.id, CASCADE, nullable"
        string description "required, max 500"
        numeric_12_2 amount "required"
        string currency "default USD"
        int paid_by FK "users.id"
        string split_type "equal/exact/percentage/shares/none"
        string category "max 50"
        text notes
        date expense_date "default today"
        text receipt_url
        boolean is_deleted "default false"
        boolean is_edited "default false"
        int created_by FK "users.id"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
        datetime deleted_at
        int deleted_by FK "users.id, nullable"
    }

    expense_splits {
        int id PK "autoincrement"
        int expense_id FK "expenses.id, CASCADE"
        int user_id FK "users.id"
        numeric_12_2 amount "required"
        numeric_5_2 percentage "nullable"
        int shares "nullable"
    }

    settlements {
        int id PK "autoincrement"
        int group_id FK "groups.id, CASCADE"
        int from_user_id FK "users.id"
        int to_user_id FK "users.id"
        numeric_12_2 amount "required"
        string currency "default USD"
        string method "default cash, max 50"
        text notes
        text proof_url
        int recorded_by FK "users.id"
        date settlement_date "default today"
        boolean is_deleted "default false"
        datetime created_at "func.now()"
    }

    group_balances {
        int id PK "autoincrement"
        int group_id FK "groups.id, CASCADE"
        int user_id FK "users.id"
        numeric_12_2 balance "default 0"
        datetime updated_at "func.now(), onupdate"
    }

    invitations {
        int id PK "autoincrement"
        int group_id FK "groups.id, CASCADE"
        string invitee_email "required, max 255"
        int invitee_user_id FK "users.id, nullable"
        int invited_by FK "users.id"
        string status "pending/accepted/declined/expired"
        datetime expires_at
        datetime created_at "func.now()"
        datetime responded_at
    }

    expense_history {
        int id PK "autoincrement"
        int expense_id FK "expenses.id, CASCADE"
        int group_id FK "groups.id, nullable"
        string action "created/updated/deleted/restored"
        int changed_by FK "users.id"
        json changes_json "field-level diff"
        json before_snapshot "full expense before"
        json after_snapshot "full expense after"
        datetime created_at "func.now()"
    }

    groups ||--o{ group_members : "has members"
    groups ||--o{ expenses : "contains"
    groups ||--o{ settlements : "has settlements"
    groups ||--o{ group_balances : "has balances"
    groups ||--o{ invitations : "has invitations"
    expenses ||--o{ expense_splits : "split into"
    expenses ||--o{ expense_history : "has history"
    users ||--o{ expenses : "paid_by"
    users ||--o{ expense_splits : "owes/owed"
    users ||--o{ settlements : "from/to"
    users ||--o{ group_members : "belongs to"
```

**Key indexes:**
- `idx_expenses_group` on `(group_id, is_deleted, expense_date)`
- `idx_expenses_paid_by` on `(paid_by)`
- `idx_settlements_group` on `(group_id, is_deleted)`
- `idx_settlements_users` on `(from_user_id, to_user_id)`
- `idx_balances_group` on `(group_id)`
- `idx_balances_user` on `(user_id)`
- `idx_invitations_email` on `(invitee_email, status)`
- `idx_invitations_group` on `(group_id, status)`

**Unique constraints:**
- `uq_group_member` on `(group_id, user_id)`
- `uq_expense_split` on `(expense_id, user_id)`
- `uq_group_balance` on `(group_id, user_id)`
- `uq_invitation` on `(group_id, invitee_email)`

**Special patterns:**
- **Soft deletes:** `expenses.is_deleted` and `settlements.is_deleted` flag records as deleted without removing rows
- **Denormalized balances:** `group_balances` stores pre-computed balance per user per group, updated on every expense/settlement write. Enables O(1) balance reads instead of recomputing from all expenses
- **Audit trail:** `expense_history` stores field-by-field `changes_json` diffs plus full `before_snapshot` and `after_snapshot` for every create/update/delete

### Group Planner Domain (10 tables)

All Group Planner tables use the `gp_` prefix to avoid name collisions with Expense Engine tables.

```mermaid
erDiagram
    travel_groups {
        int id PK "autoincrement"
        string name "required, max 100"
        text description
        string destination "max 255"
        float destination_lat
        float destination_lng
        string destination_type "country/state/city"
        string destination_id "max 50"
        string group_code UK "max 20, indexed"
        text group_image
        int created_by FK "users.id"
        date start_date
        date end_date
        numeric_12_2 estimated_budget
        string budget_currency "default USD"
        int expense_group_id "link to expense groups.id"
        boolean is_active "default true"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
    }

    gp_group_members {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        int user_id FK "users.id"
        string role "creator/admin/member"
        boolean is_active "default true"
        datetime joined_at "func.now()"
        datetime removed_at
        int removed_by FK "users.id"
    }

    gp_places {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        string name "required, max 255"
        text description
        text address
        float latitude
        float longitude
        string category "restaurant/attraction/hotel/activity"
        date visit_date
        string suggested_duration "max 50"
        text remarks
        text photo_url
        text website
        float rating
        int added_by FK "users.id"
        boolean is_deleted "default false"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
    }

    gp_place_votes {
        int id PK "autoincrement"
        int place_id FK "gp_places.id, CASCADE"
        int user_id FK "users.id"
        datetime created_at "func.now()"
    }

    gp_polls {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        string name "required, max 255"
        json options "list of option strings"
        boolean is_multiple_choice "default false"
        datetime expires_at
        int created_by FK "users.id"
        boolean is_deleted "default false"
        datetime created_at "func.now()"
    }

    gp_poll_votes {
        int id PK "autoincrement"
        int poll_id FK "gp_polls.id, CASCADE"
        int user_id FK "users.id"
        string option "max 255, the selected option text"
        datetime created_at "func.now()"
    }

    gp_invitations {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        string invitee_email "required, max 255"
        int invitee_user_id FK "users.id, nullable"
        int invited_by FK "users.id"
        string status "pending/accepted/declined/expired"
        datetime expires_at
        datetime created_at "func.now()"
        datetime responded_at
    }

    gp_checklist_items {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        string item "required, max 500"
        boolean completed "default false"
        int completed_by FK "users.id, nullable"
        datetime completed_at
        int author_id FK "users.id"
        boolean is_deleted "default false"
        datetime created_at "func.now()"
    }

    gp_itinerary_documents {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE, unique"
        text content "Markdown, default empty"
        int last_edited_by FK "users.id"
        int version "default 1"
        datetime created_at "func.now()"
        datetime updated_at "func.now(), onupdate"
    }

    gp_group_activities {
        int id PK "autoincrement"
        int group_id FK "travel_groups.id, CASCADE"
        int user_id FK "users.id"
        string action "place_added/poll_created/member_joined/etc"
        string entity_type "place/poll/member/checklist"
        int entity_id
        json details
        datetime created_at "func.now()"
    }

    travel_groups ||--o{ gp_group_members : "has members"
    travel_groups ||--o{ gp_places : "has places"
    travel_groups ||--o{ gp_polls : "has polls"
    travel_groups ||--o{ gp_invitations : "has invitations"
    travel_groups ||--o{ gp_checklist_items : "has checklist"
    travel_groups ||--|| gp_itinerary_documents : "has itinerary"
    travel_groups ||--o{ gp_group_activities : "has activity log"
    gp_places ||--o{ gp_place_votes : "has votes"
    gp_polls ||--o{ gp_poll_votes : "has votes"
    users ||--o{ gp_group_members : "belongs to"
    users ||--o{ gp_places : "added_by"
    users ||--o{ gp_place_votes : "voted"
```

**Key indexes:**
- `idx_gp_group_members_user` on `(user_id, is_active)`
- `idx_gp_group_members_group` on `(group_id, is_active)`
- `idx_gp_places_group` on `(group_id, is_deleted)`
- `idx_gp_polls_group` on `(group_id, is_deleted)`
- `idx_gp_poll_votes` on `(poll_id, user_id)`
- `idx_gp_invitations_email` on `(invitee_email, status)`
- `idx_gp_invitations_group` on `(group_id, status)`
- `idx_gp_checklist_group` on `(group_id, is_deleted)`
- `idx_gp_activities_group` on `(group_id, created_at)`

**Unique constraints:**
- `uq_gp_group_member` on `(group_id, user_id)`
- `uq_gp_place_vote` on `(place_id, user_id)` -- one vote per user per place
- `uq_gp_poll_vote` on `(poll_id, user_id, option)` -- one vote per option per user
- `uq_gp_invitation` on `(group_id, invitee_email)`

**Cross-domain link:** `travel_groups.expense_group_id` references `groups.id` (expense engine). This is an integer field, not a foreign key constraint -- allowing the two domains to be loosely coupled. A travel group can optionally link to an expense group for budget tracking.

---

## Travel Reference Database (`infrastructure/db/travel_db.py`)

### Connection Pattern

```mermaid
flowchart TD
    A["Service calls travel_db.execute_query()"] --> B["TravelDatabase._validate()<br/>Check file exists (once)"]
    B --> C["sqlite3.connect(str(db_path))"]
    C --> D["conn.row_factory = sqlite3.Row"]
    D --> E["cursor.execute(query, params)"]
    E --> F["fetchall() -> list of dicts"]
    F --> G["conn.close()"]
    G --> H["Return results"]
```

**Key design:** Each call opens and closes its own connection. No connection pooling. This is safe because:
- The database is read-only (no write contention)
- SQLite read operations are very fast
- The `TravelDatabase` singleton validates the file path once (lazy `_validated` flag)

### Schema

```mermaid
erDiagram
    countries {
        string country_name PK
        string iso_code
        string continent
        string currency
        string language
        int total_places
    }

    states {
        int id PK
        string state_name
        string country_name FK
        int total_places
    }

    cities {
        int id PK
        string city_name
        string state_name FK
        string country_name FK
        float latitude
        float longitude
        int total_places
    }

    places {
        int id PK
        string place_name
        string city_name FK
        string state_name
        string country_name FK
        float latitude
        float longitude
        float rating
        string category
        string tags
        string summary
        string photo_url
        string photo_attribution
        float rank_score
        string cost_indicator
        string opening_hours
        string best_time_to_visit
        string sunrise_sunset
    }

    countries ||--o{ states : "contains"
    countries ||--o{ places : "has places"
    states ||--o{ cities : "contains"
    cities ||--o{ places : "contains"
```

### Data Quality

| Metric | Value |
|--------|-------|
| Total countries | 82 |
| Total states | 800+ |
| Total cities | 888 |
| Total places | 16,830 |
| Places with photos | ~70% (11,781) |
| Places with ratings | ~85% |
| Places with coordinates | ~95% |
| Places with descriptions | ~90% |

### How the Travel DB is Queried

The `TravelDatabase` class provides three methods:

| Method | Returns | Use Case |
|--------|---------|----------|
| `execute_query(sql, params)` | `List[Dict]` | Multi-row results (search, list) |
| `execute_one(sql, params)` | `Optional[Dict]` | Single-row lookup (place details) |
| `execute_count(sql, params)` | `int` | Count queries (stats, pagination) |

**Example: Place search query path:**

```mermaid
sequenceDiagram
    participant Route as /api/v1/place-search/search
    participant Service as PlaceSearchService
    participant TravelDB as travel_db (singleton)
    participant SQLite as travel_data_complete.db

    Route->>Service: search_places("tokyo", limit=20, sort_by="rank_score")
    Service->>Service: Build SQL: SELECT * FROM places<br/>WHERE place_name LIKE ? OR city_name LIKE ?<br/>ORDER BY rank_score DESC LIMIT ?
    Service->>TravelDB: execute_query(sql, ("%tokyo%", "%tokyo%", 20))
    TravelDB->>SQLite: sqlite3.connect() -> cursor.execute() -> fetchall()
    SQLite-->>TravelDB: Raw sqlite3.Row objects
    TravelDB->>TravelDB: Convert to list of dicts
    TravelDB-->>Service: [{place_name: "Tokyo Tower", rank_score: 9.2, ...}, ...]
    Service->>Service: Filter bad photos, format response
    Service-->>Route: {places: [...], total_count: 42}
```

---

## Caching Architecture (`infrastructure/cache/redis.py`)

### Redis Client Implementation

```mermaid
flowchart TD
    A["factory.py: redis_client.init_app(app)"] --> B["Lazy import redis package"]
    B --> C{"redis installed?"}
    C -->|No| D["Log warning, cache disabled"]
    C -->|Yes| E["redis.from_url(REDIS_URL,<br/>max_connections=50,<br/>socket_timeout=5,<br/>decode_responses=True)"]
    E --> F["client.ping()"]
    F -->|Success| G["_available = True"]
    F -->|Failure| H["_available = False, log warning"]
```

**Graceful fallback:** Every `get`, `set`, `delete`, `exists` method checks `self.available` first. If Redis is down, all operations return safe defaults (`None`, `False`, `0`). No exceptions ever bubble up from cache operations.

### The `@cache_response` Decorator

This is the primary caching mechanism, applied to Flask route functions:

```mermaid
flowchart TD
    A["GET /api/v1/place-search/search?q=tokyo&limit=20"] --> B{Redis available?}
    B -->|No| C["Execute route function directly"]
    B -->|Yes| D["Build cache key"]
    D --> E["key_data = '/api/v1/place-search/search:q=tokyo&limit=20'"]
    E --> F["key_hash = MD5(key_data)[:12]"]
    F --> G["cache_key = 'places:a1b2c3d4e5f6'"]
    G --> H["redis_client.get(cache_key)"]
    H --> I{Hit?}
    I -->|Yes| J["Return cached JSON<br/>X-Cache: HIT<br/>~1ms"]
    I -->|No| K["Execute route function<br/>50-800ms"]
    K --> L["redis_client.set(cache_key, response_json, ex=ttl)"]
    L --> M["Return response<br/>X-Cache: MISS"]
```

**Key generation:** `MD5(request.path + ":" + query_string)[:12]` -- first 12 hex characters of the MD5 hash. The `key_prefix` argument is prepended (e.g., `places:`, `locations:`, `groups:`).

### Cache TTLs by Data Type

| Data Type | Key Prefix | TTL | Rationale |
|-----------|-----------|-----|-----------|
| Place search results | `places:` | 300s (5 min) | Travel data is static; short TTL for variety |
| Autocomplete suggestions | `autocomplete:` | 300s (5 min) | Same static data |
| Country/state/city lists | `locations:` | 1800-3600s (30-60 min) | Hierarchical data rarely changes |
| Group details | `groups:` | 60s (1 min) | Changes with member actions |
| Expense balances | `balances:` | 30s | Changes with every expense/settlement |
| Destination events | `events:` | 300s (5 min) | External API data |

### Cache Invalidation

```mermaid
flowchart TD
    A["Write operation<br/>(create expense, add place, etc.)"] --> B["Service completes DB write"]
    B --> C["invalidate_cache('balances:*')"]
    C --> D["redis_client.delete_pattern('balances:*')"]
    D --> E["KEYS balances:* -> DELETE matching keys"]
    E --> F["Next read triggers fresh query + cache fill"]
```

`invalidate_cache(pattern)` calls `redis_client.delete_pattern(pattern)` which uses `KEYS pattern` + `DELETE`. This is acceptable for a small dataset but would need `SCAN` at scale.

### Redis Memory Usage

| Category | Approx. Size |
|----------|-------------|
| Place search results (cached JSON) | 4-6 MB |
| Location hierarchies | 1-2 MB |
| Rate limiter state (Flask-Limiter) | 0.5-1 MB |
| Session-related data | 0.5-1 MB |
| **Total** | **~8-12 MB of 30 MB** |

---

## End-to-End Data Flows

### Flow 1: Creating an Expense

Shows how data moves through all layers -- frontend, backend, database, and cache:

```mermaid
sequenceDiagram
    participant User
    participant React as ExpenseManager.jsx
    participant Hook as useExpenseQuery
    participant API as expenseApi.js
    participant Flask as /api/expense/expenses
    participant Service as ExpenseService
    participant DB as tripraft.db
    participant Redis

    User->>React: Fill form: "Dinner", $120, equal split, 3 people
    React->>Hook: createExpenseMutation.mutate(data)
    Hook->>Hook: Optimistic update: add expense to React Query cache
    Hook->>API: createExpense({group_id, description, amount, split_type, splits})
    API->>API: getFreshToken() -> check JWT expiry
    API->>Flask: POST /api/expense/expenses<br/>Authorization: Bearer eyJ...<br/>{description: "Dinner", amount: 120, split_type: "equal", ...}
    
    Flask->>Flask: @require_auth -> verify JWT -> g.current_user
    Flask->>Flask: ExpenseCreateSchema().load(data) -> validate
    Flask->>Service: create_expense(user_id, validated_data)
    
    Service->>DB: BEGIN TRANSACTION
    Service->>DB: INSERT INTO expenses (description, amount, paid_by, split_type, ...)
    Service->>DB: INSERT INTO expense_splits (expense_id, user_id, amount) x3
    Service->>DB: INSERT INTO expense_history (action='created', changes_json, after_snapshot)
    Service->>DB: UPDATE group_balances SET balance = balance + computed_delta (for each user)
    Service->>DB: COMMIT
    
    Service->>Redis: invalidate_cache('balances:*')
    Service->>Redis: invalidate_cache('groups:*')
    
    Service-->>Flask: expense.to_dict(include_splits=True)
    Flask-->>API: {id: 42, description: "Dinner", amount: 120.00, splits: [...]}
    API-->>Hook: Success
    Hook->>Hook: Confirm optimistic update (or rollback on failure)
    Hook-->>React: Re-render with new expense in list
```

### Flow 2: Place Search with Cache

```mermaid
sequenceDiagram
    participant User
    participant React as PlaceSearchPage.jsx
    participant Service as placeSearchService.js
    participant Flask as /api/v1/place-search/search
    participant Redis
    participant TravelDB as travel_data_complete.db

    User->>React: Types "tokyo" in SearchBar
    React->>React: Debounce 300ms
    React->>Service: searchPlaces("tokyo", {limit: 500, sortBy: "rank_score"})
    Service->>Flask: GET /search?q=tokyo&limit=500&sort_by=rank_score&sort_order=desc
    
    Flask->>Flask: @cache_response(key_prefix='places', ttl=300)
    Flask->>Redis: GET places:a1b2c3d4e5f6
    
    alt Cache Hit (97% of the time)
        Redis-->>Flask: Cached JSON string
        Flask-->>Service: Response (X-Cache: HIT, ~1ms)
    else Cache Miss
        Redis-->>Flask: None
        Flask->>TravelDB: SELECT * FROM places WHERE (place_name LIKE '%tokyo%' OR city_name LIKE '%tokyo%') ORDER BY rank_score DESC LIMIT 500
        TravelDB-->>Flask: Raw rows
        Flask->>Flask: Format, filter bad photos, build response JSON
        Flask->>Redis: SET places:a1b2c3d4e5f6 {json} EX 300
        Flask-->>Service: Response (X-Cache: MISS, ~200ms)
    end
    
    Service-->>React: {places: [...], total_count: 42}
    React->>React: GroupedPlaceGrid groups by country > city
    React-->>User: PlaceCards with photos, ratings, categories
```

### Flow 3: Group Planner Load with All Data

```mermaid
sequenceDiagram
    participant User
    participant React as GroupPlanner.jsx
    participant API as groupPlannerApi.js
    participant Flask as /api/v2/group-planner/groups/:id
    participant Service as GroupService
    participant DB as tripraft.db

    User->>React: Navigate to /group-planner/42
    React->>API: getGroup(42)
    API->>Flask: GET /api/v2/group-planner/groups/42<br/>Authorization: Bearer eyJ...
    
    Flask->>Flask: @require_auth -> verify membership in group 42
    Flask->>Service: get_group(42)
    
    Service->>DB: SELECT travel_groups WHERE id=42
    Service->>DB: Eager load: members (gp_group_members JOIN users)
    Service->>DB: Eager load: places (gp_places WHERE is_deleted=false)
    Service->>DB: Eager load: place_votes (gp_place_votes for each place)
    Service->>DB: Eager load: polls (gp_polls WHERE is_deleted=false)
    Service->>DB: Eager load: poll_votes (gp_poll_votes for each poll)
    Service->>DB: Eager load: checklist (gp_checklist_items WHERE is_deleted=false)
    Service->>DB: Eager load: itinerary (gp_itinerary_documents)
    Service->>DB: Eager load: activities (gp_group_activities ORDER BY created_at DESC LIMIT 50)
    
    Service-->>Flask: group.to_dict(include_members=True, include_places=True, include_polls=True)
    Flask-->>API: {id: 42, name: "Paris Trip", members: [...], places: [...], polls: [...], checklist: [...], itinerary: {...}, activities: [...]}
    API-->>React: Full group data
    React->>React: Render: MapSection (Leaflet markers), PlacesSidebar, RightSidebar (polls, checklist, notes)
```

### Flow 4: Balance Recalculation on Expense Update

```mermaid
flowchart TD
    A["User edits expense: $120 -> $150"] --> B["ExpenseService.update_expense()"]
    B --> C["BEGIN TRANSACTION"]
    C --> D["Snapshot current expense as before_snapshot"]
    D --> E["UPDATE expenses SET amount=150, is_edited=true"]
    E --> F["DELETE old expense_splits"]
    F --> G["INSERT new expense_splits with recalculated amounts"]
    G --> H["Compute changes_json: [{field: 'amount', old: 120, new: 150}]"]
    H --> I["INSERT expense_history (action='updated', before_snapshot, after_snapshot, changes_json)"]
    I --> J["BalanceService.recalculate_group_balances(group_id)"]
    J --> K["Query ALL non-deleted expenses + splits for group"]
    K --> L["For each member: net = sum(paid) - sum(owed)"]
    L --> M["Query ALL non-deleted settlements for group"]
    M --> N["Adjust balances: net += settlements_received - settlements_paid"]
    N --> O["UPSERT group_balances for each member"]
    O --> P["COMMIT"]
    P --> Q["invalidate_cache('balances:*')<br/>invalidate_cache('groups:*')"]
```

The `group_balances` table stores the **net position** of each member:
- **Positive balance** = this person is owed money (they paid more than their share)
- **Negative balance** = this person owes money (they were covered by others)
- **Zero balance** = fully settled

---

## Migration Plan: SQLite to PostgreSQL

```mermaid
flowchart TD
    A["Current: SQLite (StaticPool)"] --> B["Step 1: Set DATABASE_URL=postgres://..."]
    B --> C["Step 2: connection.py auto-selects<br/>PostgreSQL engine config<br/>(pool_size=10, max_overflow=20)"]
    C --> D["Step 3: Base.metadata.create_all()<br/>creates identical tables in PostgreSQL"]
    D --> E["Step 4: Export SQLite data with sqlite3 CLI"]
    E --> F["Step 5: Import via psycopg2 or pg_restore"]
    F --> G["Step 6: Validate foreign keys and indexes"]
    G --> H["Target: PostgreSQL with connection pooling"]

    I["travel_data_complete.db"] --> J{Decision}
    J -->|"Option A"| K["Keep as SQLite read-only<br/>(works fine, no changes needed)"]
    J -->|"Option B"| L["Import to PostgreSQL<br/>with tsvector full-text search"]
    J -->|"Option C"| M["Move to Meilisearch<br/>for better autocomplete + typo tolerance"]
```

The SQLAlchemy ORM means the migration is mostly a config change. `connection.py` already has the PostgreSQL branch:

```python
# Already in connection.py:
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, poolclass=StaticPool, ...)
else:
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
```

The travel database is a separate decision. It works fine as read-only SQLite. PostgreSQL `tsvector` or Meilisearch would only be needed for fuzzy search and typo tolerance -- features not yet required.
