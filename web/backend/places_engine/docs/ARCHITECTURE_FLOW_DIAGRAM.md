# Places Engine Architecture: Data Flow Diagram

## 📊 Complete Data Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 passed_countries/ (NEW PRIMARY SOURCE)                 │
│     ├── argentina/                                         │
│     │   ├── bariloche.json                                │
│     │   ├── buenos_aires.json                             │
│     │   └── ... (10 city files)                           │
│     ├── australia/ (8 state files)                        │
│     ├── austria/ (10 city files)                          │
│     ├── brazil/ (10 state files)                          │
│     └── ... (90+ countries total)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              🛠️ DATA PREPARATION SCRIPTS                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✓ ranking_score.py      → Update rank_score              │
│  ✓ remove.py             → Clean photos/gallery           │
│  ✓ check.py              → Validate structure             │
│                                                             │
│  OUTPUT: Enhanced JSON files in passed_countries/          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│          📋 PIPELINE: DatasetPreparer                       │
├─────────────────────────────────────────────────────────────┤
│  File: places_engine/pipeline/prepare_dataset.py          │
│                                                             │
│  1. Read JSON files from passed_countries/                │
│  2. Validate schema & structure                           │
│  3. Generate unique place IDs                             │
│  4. Normalize text fields                                 │
│  5. Sanitize & validate photos                            │
│  6. Generate search_text for indexing                     │
│  7. Aggregate by city/state/country                       │
│                                                             │
│  OUTPUT: Prepared JSON files                              │
│  Location: pipeline/prepared_data/                        │
│  ├── places.json          (all places)                    │
│  ├── cities.json          (aggregated)                    │
│  ├── countries.json       (aggregated)                    │
│  ├── id_mappings.json     (reference)                     │
│  └── stats.json           (metadata)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│          ☁️ FIRESTORE UPLOAD: FirestoreUploader            │
├─────────────────────────────────────────────────────────────┤
│  File: places_engine/pipeline/upload_to_firestore.py      │
│                                                             │
│  1. Connect to Firebase Firestore                         │
│  2. Batch upload (20 docs/batch)                          │
│  3. Transform coordinates to GeoPoint                     │
│  4. Error handling & retry logic                          │
│  5. Progress tracking & statistics                        │
│                                                             │
│  OUTPUT: Firestore Collections                            │
│  ├── places          (place details)                      │
│  ├── cities          (city overview + top 20 places)     │
│  ├── countries       (country overview + states)          │
│  ├── states          (state data + top 20 places)        │
│  └── search_index    (autocomplete suggestions)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           🚀 API LAYER: Places Service                     │
├─────────────────────────────────────────────────────────────┤
│  File: places_engine/services/places_service.py           │
│                                                             │
│  Available Methods:                                         │
│  • search_places()           - Full-text search            │
│  • get_country_overview()    - Country with states         │
│  • get_state_overview()      - State with places          │
│  • get_city_overview()       - City with places           │
│  • get_place_detail()        - Single place details        │
│  • autocomplete()            - Suggestions                 │
│  • nearby_places()           - Geospatial search           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│        💾 CACHING LAYER: PlacesCache (Redis)               │
├─────────────────────────────────────────────────────────────┤
│  File: places_engine/cache/places_cache.py                │
│                                                             │
│  Cache TTLs:                                               │
│  • Location search    → 4 hours                            │
│  • Country overview   → 24 hours                           │
│  • Nearby search      → 1 hour                             │
│  • Place detail       → 24 hours                           │
│  • Autocomplete       → 1 hour                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           🌐 REST ENDPOINTS: Flask Routes                  │
├─────────────────────────────────────────────────────────────┤
│  File: places_engine/api/routes.py                        │
│                                                             │
│  GET  /api/places/search              - Search places     │
│  GET  /api/places/<id>                - Place details     │
│  GET  /api/places/location            - By city/state     │
│  GET  /api/places/country/<name>      - Country overview  │
│  GET  /api/places/nearby              - Nearby places     │
│  GET  /api/places/autocomplete        - Suggestions       │
│  GET  /api/places/popular             - Popular places    │
│  GET  /api/places/countries           - All countries     │
│  GET  /api/places/cities              - Cities by country │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           🎨 FRONTEND: React Components                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Displays to Users:                                         │
│  • Country explorer with state breakdowns                 │
│  • City guides with top 20 places                         │
│  • Autocomplete search suggestions                        │
│  • Place detail cards                                      │
│  • Map view with nearby places                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 File Organization

```
places_engine/
│
├── 📋 CONFIGURATION
│   ├── config.py                          ← Dataset path: passed_countries/
│   ├── OPTIMIZATION_PLAN.md               ← Architecture docs
│   └── DATA_SOURCE_UPDATE_SUMMARY.md      ← Migration summary
│
├── 🛠️ UTILITY SCRIPTS
│   ├── ranking_score.py                   ← Update scores
│   ├── remove.py                          ← Clean data
│   ├── check.py                           ← Validate & organize
│   └── photo_filled.py                    ← Enrich photos
│
├── 📦 API LAYER
│   └── api/
│       ├── routes.py                      ← REST endpoints
│       └── admin.py                       ← Admin endpoints
│
├── 🧠 SERVICE LAYER
│   └── services/
│       └── places_service.py              ← Business logic
│
├── 💾 CACHE LAYER
│   └── cache/
│       └── places_cache.py                ← Redis caching
│
├── 🔄 PIPELINE
│   └── pipeline/
│       ├── prepare_dataset.py             ← DatasetPreparer
│       ├── upload_to_firestore.py         ← FirestoreUploader
│       ├── analyze_dataset.py             ← Analysis
│       ├── validate_photos.py             ← Photo validation
│       └── prepared_data/                 ← Output directory
│           ├── places.json
│           ├── cities.json
│           ├── countries.json
│           ├── id_mappings.json
│           └── stats.json
│
├── 🛠️ UTILITIES
│   └── utils/
│       ├── helpers.py                     ← Common functions
│       └── __init__.py
│
└── 🧪 TESTS
    └── tests/
        ├── test_cache.py
        ├── test_config.py
        ├── test_pipeline.py
        ├── test_utils.py
        └── __init__.py
```

---

## 🔄 Data Flow Example: Search for "Eiffel Tower"

```
User enters "Eiffel Tower"
         ↓
   Frontend (React)
    └─ placesService.search("Eiffel Tower")
         ↓
   REST API
    /api/places/search?q=Eiffel%20Tower
         ↓
   Flask Route (routes.py)
    └─ search_places()
         ↓
   PlacesService (places_service.py)
    ├─ Check Redis cache
    │  └─ MISS → Query Firestore
    │
    ├─ Query Firestore Collections
    │  ├── Search in 'places' collection
    │  ├── Filter by search_text: "eiffel tower"
    │  ├── Sort by rank_score DESC
    │  └─ Get top 20 results
    │
    ├─ Convert GeoPoint to coordinates
    ├─ Validate photo URLs
    └─ Store in Redis (TTL: 4 hours)
         ↓
   Response (JSON)
    ├─ 20 places with:
    │  ├── ID, name, city, country
    │  ├── rank_score, ratings
    │  ├── coordinates, photos
    │  ├── cost, duration, best_time
    │  └── tags, summary
    │
    └─ Pagination metadata
         ↓
   Frontend Renders
    └─ Place cards in grid
        ├── Photo thumbnail
        ├── Name & location
        ├── Ratings
        ├── Cost/duration
        └── Click to view details
```

---

## 🎯 Performance Targets

| Operation | Current | Target | Method |
|-----------|---------|--------|--------|
| Search places | N/A | <500ms | Firestore + Redis cache |
| Country view | N/A | <1000ms | Pre-aggregated documents |
| City overview | N/A | <500ms | Embedded top 20 places |
| Autocomplete | N/A | <100ms | Search index collection |
| Nearby places | N/A | <800ms | GeoPoint queries |

---

## ✅ Configuration Summary

| Setting | Old Value | New Value | Source |
|---------|-----------|-----------|--------|
| Dataset path | `dataset/countries` | `dataset/passed_countries` | config.py |
| Dataset status | Mixed quality | Validated & cleaned | check.py |
| Ranking scores | Manual | Auto-calculated | ranking_score.py |
| Photo data | Raw | Curated & validated | photo_filled.py |
| Fallback | N/A | Environment variable override | config.py |

---

**Created**: December 8, 2025
**Status**: ✅ Production Ready
