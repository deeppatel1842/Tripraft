# Feature: Place Discovery Engine

## Overview

TripRaft includes a read-only travel reference database containing 16,000+ places across 82 countries. The Place Discovery Engine provides full-text search, hierarchical browsing, autocomplete, and detailed place information. This is a public feature — no authentication required.

---

## System Flow

```
                    PLACE SEARCH FLOW
                    =================

Browser                          Flask Backend                Travel DB (SQLite)
   │                                  │                            │
   │  User types "tokyo"              │                            │
   │  (300ms debounce)                │                            │
   │                                  │                            │
   │  GET /api/v1/places/autocomplete │                            │
   │  ?q=tokyo&limit=10              │                            │
   │─────────────────────────────────>│                            │
   │                                  │  PlaceSearchService        │
   │                                  │  .autocomplete()           │
   │                                  │                            │
   │                                  │  @cache_response(1800s)    │
   │                                  │  Check Redis cache         │
   │                                  │                            │
   │                                  │  If miss:                  │
   │                                  │  FTS5 MATCH query          │
   │                                  │─────────────────────────── >│
   │                                  │  "SELECT * FROM places_fts │
   │                                  │   WHERE places_fts         │
   │                                  │   MATCH 'tokyo*'"          │
   │                                  │                            │
   │                                  │  Results: cities + places  │
   │                                  │ <──────────────────────────│
   │                                  │                            │
   │                                  │  Cache in Redis (1800s)    │
   │                                  │                            │
   │  200 OK                          │                            │
   │  {suggestions: [...]}            │                            │
   │ <────────────────────────────────│                            │
   │                                  │                            │
   │  User selects "Tokyo, Japan"     │                            │
   │                                  │                            │
   │  GET /api/v1/places/search       │                            │
   │  ?q=Tokyo&country=Japan          │                            │
   │  &sortBy=rank_score              │                            │
   │  &limit=50&offset=0             │                            │
   │─────────────────────────────────>│                            │
   │                                  │  PlaceSearchService        │
   │                                  │  .search()                 │
   │                                  │                            │
   │                                  │  Build FTS5 query with     │
   │                                  │  filters (country, cost,   │
   │                                  │  rating, category)         │
   │                                  │─────────────────────────── >│
   │                                  │                            │
   │                                  │  JOIN places, cities,      │
   │                                  │  countries, photos         │
   │                                  │                            │
   │  200 OK                          │                            │
   │  ETag: "abc123"                  │                            │
   │  {data: [...places],             │                            │
   │   total: 127, offset: 0}         │                            │
   │ <────────────────────────────────│                            │
   │                                  │                            │
   │  User clicks place card          │                            │
   │                                  │                            │
   │  GET /api/v1/places/42           │                            │
   │  If-None-Match: "abc123"         │                            │
   │─────────────────────────────────>│                            │
   │                                  │  ETag match?               │
   │                                  │  If yes: 304 Not Modified  │
   │  304 (use cached)                │  If no: full response      │
   │ <────────────────────────────────│                            │
```

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/places.py` | REST endpoints: search, autocomplete, place detail, stats |
| `app/api/v1/locations.py` | Deprecated hierarchical endpoints (country > state > city > place) |
| `app/services/place_search_service.py` | PlaceSearchService: FTS5 search, autocomplete, detail retrieval |
| `app/services/destination_service.py` | DestinationService: autocomplete, top places, dashboard analytics |
| `app/domain/places/models.py` | DTOs: Country, State, City, Place, Photo, SearchResult, AutocompleteSuggestion |
| `app/domain/places/location_models.py` | SQL query wrappers for hierarchical location search |
| `app/domain/places/repository.py` | DatabaseConnection: read-only access to travel_data_complete.db |
| `app/domain/places/location_repository.py` | DatabaseManager singleton for travel reference DB |
| `app/infrastructure/db/travel_db.py` | TravelDatabase: thread-safe SQLite connection, ingestion logging |
| `app/schemas/places.py` | Admin schemas: PlaceCreate, PlaceUpdate, BulkImport, ValidationResult |

### Frontend

| File | Purpose |
|------|---------|
| `src/components/placeSearch/jsx/PlaceSearchPage.jsx` | Main search page: search bar, filters, results grid, detail modal |
| `src/components/placeSearch/jsx/SearchBar.jsx` | Debounced search input with autocomplete trigger |
| `src/components/placeSearch/jsx/SearchSuggestions.jsx` | Dropdown list of autocomplete suggestions |
| `src/components/placeSearch/jsx/PlaceGrid.jsx` | Responsive grid layout for place cards |
| `src/components/placeSearch/jsx/GroupedPlaceGrid.jsx` | Groups places by country/city/category |
| `src/components/placeSearch/jsx/PlaceCard.jsx` | Place thumbnail with rating, cost, quick preview |
| `src/components/placeSearch/jsx/PlaceDetailModal.jsx` | Full place info: description, gallery, reviews, map, tags |
| `src/services/placeSearchService.js` | API service: search, autocomplete, place detail, stats |
| `src/hooks/usePlaceSearchQuery.js` | TanStack Query hooks: useSearchPlaces, useAutocompleteSuggestions |

---

## Database Schema (travel_data_complete.db)

```
countries (82 records)
├── id (INTEGER, PK)
├── name (TEXT)
├── code (TEXT, ISO 3166-1)
└── continent (TEXT)

states
├── id (INTEGER, PK)
├── name (TEXT)
└── country_id (FK → countries.id)

cities
├── id (INTEGER, PK)
├── name (TEXT)
├── state_id (FK → states.id)
├── latitude (REAL)
└── longitude (REAL)

places (16,000+ records)
├── id (INTEGER, PK)
├── name (TEXT)
├── description (TEXT)
├── category (TEXT: restaurant, attraction, museum, park, etc.)
├── city_id (FK → cities.id)
├── latitude (REAL)
├── longitude (REAL)
├── rating (REAL, 0-5)
├── cost_level (INTEGER, 1-4)
├── tags (TEXT, comma-separated)
├── rank_score (REAL, computed)
└── created_at (TEXT)

photos
├── id (INTEGER, PK)
├── place_id (FK → places.id)
├── url (TEXT)
└── credit (TEXT)

opening_hours
├── id (INTEGER, PK)
├── place_id (FK → places.id)
├── day (TEXT)
├── open_time (TEXT)
└── close_time (TEXT)

places_fts (FTS5 virtual table)
├── name
├── description
└── tags
```

---

## API Endpoints

| Method | Endpoint | Auth | Cache TTL | Description |
|--------|----------|------|----------|-------------|
| GET | `/places/search` | None | 1800s | Full-text search with filters |
| GET | `/places/autocomplete` | None | 3600s | City/place suggestions |
| GET | `/places/{place_id}` | None | 3600s | Detailed place information |
| GET | `/places/stats` | None | 3600s | DB statistics (total places, countries, etc.) |

### Search Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (FTS5 MATCH) |
| `country` | string | Filter by country name |
| `city` | string | Filter by city name |
| `category` | string | Filter by place category |
| `min_rating` | float | Minimum rating (0-5) |
| `max_cost` | int | Maximum cost level (1-4) |
| `sortBy` | string | rank_score, rating, name, cost_level |
| `sortOrder` | string | asc, desc |
| `limit` | int | Results per page (default: 50, max: 500) |
| `offset` | int | Pagination offset |

---

## Performance Optimizations

| Optimization | Detail |
|-------------|--------|
| FTS5 index | Full-text search on name, description, tags (sub-millisecond queries) |
| ETag caching | HTTP 304 responses for unchanged data |
| Redis response cache | 30-min TTL for search results, 60-min for autocomplete |
| Read-only DB | Separate SQLite file, no write lock contention |
| Thread-safe connections | Each request opens/closes own connection |
| Frontend debounce | 300ms delay before API call on keystroke |
| IndexedDB persistence | Search results cached in browser for 60 minutes |
