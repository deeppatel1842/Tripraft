# TripRaft Places API - Complete Architecture Plan

## Executive Summary

Build a self-hosted, scalable Places API to replace Google Places API, using your existing dataset of 80+ countries with rich place information.

**Current Assets:**
- 80+ country folders with structured JSON files
- ~1000+ place entries with complete metadata
- Existing scripts: `add_wikimedia_photos.py`, `apply_rank_scores.py`
- Backend: Python/Flask + Redis + Firebase Firestore

---

## 1. DATABASE OPTIONS ANALYSIS

### Option A: Firebase Firestore (RECOMMENDED) ✅

**Why Choose This:**
- Already integrated in your stack
- Free tier: 50K reads/day, 20K writes/day, 1GB storage
- Scales automatically to millions of users
- Real-time capabilities built-in
- No server management needed

**Structure:**
```
/places
  /{placeId}
    - name
    - country
    - state
    - city
    - coordinates (GeoPoint)
    - tags (array)
    - rank_score
    - cost
    - ratings {...}
    - opening_hours {...}
    - photos {...}
    - created_at
    - updated_at

/cities
  /{cityId}
    - name
    - country
    - state
    - nearest_airport {...}
    - place_ids (array)

/countries
  /{countryId}
    - name
    - city_ids (array)
```

**Costs at Scale:**
- Up to 100K daily users: FREE
- 1M reads/day: ~$0.36/day (~$11/month)
- Storage (10GB): FREE
- Bandwidth (10GB): FREE

**Indexes Needed:**
```javascript
// firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "country", "order": "ASCENDING" },
        { "fieldPath": "city", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "tags", "arrayConfig": "CONTAINS" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "city", "order": "ASCENDING" },
        { "fieldPath": "cost", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    }
  ]
}
```

---

### Option B: MongoDB Atlas

**Pros:**
- Free tier: 512MB storage
- Flexible schema
- Powerful geospatial queries
- Good for complex aggregations

**Cons:**
- Additional service to manage
- Free tier limited (not enough for 80+ countries)
- Paid tier: $9+/month for production

**Cost:**
- Free: Up to 512MB (insufficient)
- Shared M2: $9/month (2GB)
- Dedicated M10: $57/month (10GB)

---

### Option C: PostgreSQL + PostGIS (Self-hosted)

**Pros:**
- Complete control
- Excellent geospatial queries
- JSON support (JSONB)
- Free if self-hosted

**Cons:**
- Requires server management
- VPS costs: $5-20/month minimum
- Backup/scaling responsibility
- More DevOps work

**Hosting Options:**
- Railway.app: $5/month (1GB storage)
- DigitalOcean: $6/month droplet
- Supabase: Free tier (500MB)

---

### Option D: Supabase (PostgreSQL + Real-time)

**Pros:**
- Free tier: 500MB database, 1GB file storage
- Built-in Auth, Storage, Real-time
- RESTful API auto-generated
- PostGIS support

**Cons:**
- Free tier might be tight for 80+ countries
- Learning curve
- Pro: $25/month for 8GB

---

## 2. RECOMMENDED ARCHITECTURE

### **Choice: Firebase Firestore + Redis Cache** ✅

**Why:**
1. Already in your stack (no new dependencies)
2. Best free tier for your scale
3. Auto-scaling built-in
4. Geospatial queries supported
5. Real-time updates if needed later

**Architecture Diagram:**
```
┌─────────────┐
│   Client    │
│  (React)    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Flask API      │
│  /api/places/*  │
└────┬────────┬───┘
     │        │
     ▼        ▼
┌─────────┐ ┌──────────────┐
│  Redis  │ │  Firestore   │
│  Cache  │ │  (Primary)   │
└─────────┘ └──────────────┘
```

**Caching Strategy:**
- **Popular queries**: 1-hour cache
- **Place details**: 24-hour cache
- **Search results**: 15-minute cache
- **City lists**: 6-hour cache

---

## 3. DATABASE PIPELINE PLAN

### Phase 1: Data Preparation & Validation

**Script: `prepare_dataset.py`**
```python
# Features:
# 1. Validate JSON schema for all files
# 2. Add missing fields (photos, rank_score)
# 3. Generate unique place IDs
# 4. Normalize coordinates
# 5. Extract city/country metadata
# 6. Create summary statistics
```

### Phase 2: Firestore Upload Pipeline

**Script: `upload_to_firestore.py`**
```python
# Features:
# 1. Batch uploads (500 docs at a time)
# 2. Progress tracking
# 3. Error handling & retry logic
# 4. Duplicate detection
# 5. Dry-run mode
# 6. Rollback capability
```

### Phase 3: Photo Enhancement

**Enhanced: `add_wikimedia_photos.py`**
```python
# Current + New features:
# 1. Upload photos to Firebase Storage (CDN)
# 2. Generate multiple thumbnail sizes
# 3. Update Firestore with photo URLs
# 4. Fallback to Wikimedia if needed
# 5. Batch processing with rate limits
```

### Phase 4: Continuous Sync

**Script: `sync_dataset.py`**
```python
# Features:
# 1. Watch dataset folder for changes
# 2. Auto-update Firestore on file changes
# 3. Validate before syncing
# 4. Slack/email notifications
# 5. Git integration (commit tracking)
```

---

## 4. API DESIGN

### RESTful Endpoints

```python
# PLACES
GET    /api/v1/places/search?query=eiffel&city=paris
GET    /api/v1/places/{place_id}
GET    /api/v1/places/nearby?lat=48.8584&lng=2.2945&radius=5000
GET    /api/v1/places/city/{city_name}
GET    /api/v1/places/country/{country_name}
GET    /api/v1/places/autocomplete?q=eiffel

# CITIES
GET    /api/v1/cities?country=france
GET    /api/v1/cities/{city_id}
GET    /api/v1/cities/{city_id}/places

# COUNTRIES
GET    /api/v1/countries
GET    /api/v1/countries/{country_id}
GET    /api/v1/countries/{country_id}/cities

# SEARCH & FILTERS
GET    /api/v1/search?q=beach&tags=nature,sunset&cost=free&rating_min=4
GET    /api/v1/popular?country=france&limit=20
GET    /api/v1/trending?days=7&limit=10

# ADMIN (future)
POST   /api/v1/admin/places
PUT    /api/v1/admin/places/{place_id}
DELETE /api/v1/admin/places/{place_id}
POST   /api/v1/admin/sync
```

### Request/Response Examples

**Search Places:**
```bash
GET /api/v1/places/search?query=cathedral&city=bariloche&limit=5

Response:
{
  "success": true,
  "count": 1,
  "places": [
    {
      "id": "arg_bariloche_cerro_catedral",
      "name": "Cerro Catedral Ski Resort",
      "city": "San Carlos de Bariloche",
      "country": "Argentina",
      "rank_score": 0.819,
      "coordinates": {
        "lat": -41.1717,
        "lng": -71.4397
      },
      "tags": ["Nature", "Mountain", "Skiing"],
      "cost": "Paid",
      "ratings": {
        "tourist_priority": 5,
        "traveler_experience": 5
      },
      "thumbnail": "https://storage.googleapis.com/.../cerro_catedral_800.jpg"
    }
  ],
  "cache_hit": false,
  "response_time_ms": 145
}
```

**Nearby Places (Geospatial):**
```bash
GET /api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=10000&limit=10

Response:
{
  "success": true,
  "count": 10,
  "radius_km": 10,
  "center": {"lat": -41.1456, "lng": -71.3103},
  "places": [
    {
      "id": "arg_bariloche_civic_center",
      "name": "Civic Center & Lake Nahuel Huapi",
      "distance_m": 523,
      "rank_score": 0.8065,
      ...
    }
  ]
}
```

---

## 5. IMPLEMENTATION PHASES

### Phase 1: Core Infrastructure (Week 1)

**Tasks:**
1. ✅ Design Firestore schema
2. ✅ Create indexes configuration
3. ✅ Build `prepare_dataset.py` script
4. ✅ Validate all JSON files
5. ✅ Generate place IDs

**Deliverables:**
- `firestore_schema.md`
- `prepare_dataset.py`
- `validation_report.json`

---

### Phase 2: Data Pipeline (Week 1-2)

**Tasks:**
1. Build `upload_to_firestore.py`
2. Upload all countries (batch processing)
3. Enhance `add_wikimedia_photos.py`
4. Set up Firebase Storage for photos
5. Create indexes in Firestore

**Deliverables:**
- `upload_to_firestore.py`
- `photo_pipeline.py`
- Firestore populated with all places
- Upload progress report

---

### Phase 3: API Development (Week 2)

**Tasks:**
1. Create Flask blueprint for Places API
2. Implement core endpoints:
   - `/search`
   - `/places/{id}`
   - `/places/nearby`
   - `/cities`
3. Add Redis caching layer
4. Write API tests

**Deliverables:**
- `api/places_routes.py`
- `services/places_service.py`
- `cache/places_cache.py`
- API documentation (Swagger)

---

### Phase 4: Advanced Features (Week 3)

**Tasks:**
1. Autocomplete endpoint
2. Trending places (analytics)
3. User favorites (if needed)
4. Photo CDN optimization
5. Search filters (tags, cost, ratings)

**Deliverables:**
- Enhanced search capabilities
- Performance benchmarks
- Load testing results

---

### Phase 5: Maintenance & Monitoring (Ongoing)

**Tasks:**
1. Create `sync_dataset.py` for auto-updates
2. Set up monitoring/alerts
3. API usage analytics
4. Cost tracking dashboard
5. Documentation

**Deliverables:**
- Sync automation
- Monitoring dashboard
- Admin panel (optional)

---

## 6. COST PROJECTIONS

### Firebase Firestore (Recommended)

**Assumptions:**
- 100,000 places in database
- 10,000 active daily users
- Average 5 searches per user
- 50% cache hit rate

**Monthly Costs:**

| Metric | Usage | Cost |
|--------|-------|------|
| **Storage** | 2GB | FREE (under 1GB) |
| **Reads** | 750K/day (22.5M/month) | $13.50 |
| **Writes** | 1K/day (30K/month) | $0.54 |
| **Network** | 5GB/month | FREE |
| **Total** | - | **~$14/month** |

**With Redis Cache (95% hit rate):**
- Firestore reads reduced to 37.5K/day
- Monthly cost: **~$2-3/month**

**Scaling:**
- 100K users: ~$20/month
- 1M users: ~$150/month
- Always cheaper than Google Places API

---

## 7. PERFORMANCE TARGETS

| Operation | Target | Strategy |
|-----------|--------|----------|
| **Place Details** | < 50ms | Redis cache (24h TTL) |
| **Search Query** | < 200ms | Firestore index + cache |
| **Nearby Search** | < 300ms | GeoPoint queries + cache |
| **City List** | < 100ms | Cache (6h TTL) |
| **Autocomplete** | < 100ms | In-memory trie + cache |

---

## 8. DATA FLOW DIAGRAM

```
┌───────────────────────────────────────────────────────┐
│  DATASET PIPELINE                                     │
└───────────────────────────────────────────────────────┘

[JSON Files (80+ countries)]
          │
          ▼
[prepare_dataset.py]
  - Validate schema
  - Generate IDs
  - Normalize data
          │
          ▼
[add_wikimedia_photos.py]
  - Fetch photos
  - Upload to Firebase Storage
  - Generate thumbnails
          │
          ▼
[apply_rank_scores.py]
  - Calculate scores
  - Add metadata
          │
          ▼
[upload_to_firestore.py]
  - Batch upload (500/batch)
  - Create indexes
  - Verify integrity
          │
          ▼
┌─────────────────────┐
│  FIRESTORE DB       │
│  - places           │
│  - cities           │
│  - countries        │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  FLASK API          │
│  + Redis Cache      │
└─────────────────────┘
          │
          ▼
    [React Frontend]
```

---

## 9. MIGRATION CHECKLIST

### Pre-Migration
- [ ] Backup all JSON files to Git
- [ ] Create Firebase project (if new)
- [ ] Set up Firebase Admin SDK
- [ ] Configure Firestore indexes
- [ ] Test with sample data (1 country)

### Migration
- [ ] Run `prepare_dataset.py` on all files
- [ ] Validate schema compliance (100% pass)
- [ ] Run `upload_to_firestore.py` (dry-run)
- [ ] Upload to production Firestore
- [ ] Verify upload (spot checks)
- [ ] Run photo enhancement pipeline
- [ ] Create composite indexes

### Post-Migration
- [ ] Test API endpoints
- [ ] Load test (100 concurrent users)
- [ ] Set up monitoring
- [ ] Configure Redis cache
- [ ] Document API usage
- [ ] Create sync automation

---

## 10. ALTERNATIVE: HYBRID APPROACH

If Firestore limits become an issue, consider:

```
┌──────────────────────────────────────┐
│  Firestore (Metadata only)           │
│  - Place IDs, names, coordinates     │
│  - Cities, countries                 │
└──────────────────────────────────────┘
              +
┌──────────────────────────────────────┐
│  Firebase Storage (Full JSON)        │
│  - Complete place details            │
│  - Served via CDN                    │
└──────────────────────────────────────┘
              +
┌──────────────────────────────────────┐
│  Redis (Hot cache)                   │
│  - Popular places                    │
│  - Search results                    │
└──────────────────────────────────────┘
```

**Benefits:**
- Reduce Firestore reads by 90%
- Store complete JSON files in Storage
- Ultra-fast CDN delivery
- Cost: ~$1-2/month

---

## 11. MONITORING & ANALYTICS

### Key Metrics to Track

```python
# Implement in API
metrics = {
    "api_calls": {
        "total": Counter(),
        "by_endpoint": Counter(),
        "by_country": Counter()
    },
    "performance": {
        "avg_response_time": Gauge(),
        "cache_hit_rate": Gauge(),
        "firestore_reads": Counter()
    },
    "errors": {
        "total": Counter(),
        "by_type": Counter()
    },
    "popular_places": TopK(k=100)
}
```

### Tools
- **Flask-Prometheus**: Export metrics
- **Grafana**: Visualize metrics
- **Firebase Console**: Monitor usage/costs
- **Redis Insight**: Cache analysis

---

## 12. SECURITY CONSIDERATIONS

### Firestore Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Public read for places
    match /places/{placeId} {
      allow read: if true;
      allow write: if request.auth != null 
                   && request.auth.token.admin == true;
    }
    
    // Public read for cities/countries
    match /cities/{cityId} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

### API Rate Limiting
```python
# Use Flask-Limiter
@app.route('/api/v1/places/search')
@limiter.limit("100 per minute")
def search_places():
    pass
```

---

## 13. NEXT STEPS

1. **Review this plan** - Approve approach
2. **Set up Firebase** - Create project, configure
3. **Run Phase 1** - Prepare & validate dataset
4. **Build pipeline** - Upload scripts
5. **Develop API** - Flask endpoints + cache
6. **Test & Deploy** - Load testing, go live

---

## CONCLUSION

**Recommended Path:**
- **Database**: Firebase Firestore (best free tier, auto-scaling)
- **Cache**: Redis (95% hit rate = 20x cost reduction)
- **Photos**: Firebase Storage + Wikimedia fallback
- **API**: Flask + caching + geospatial queries

**Total Cost (10K daily users):**
- Firestore: ~$3/month
- Redis: Free (local) or $5/month (hosted)
- Firebase Storage: FREE
- **Total: $3-8/month** vs $200+/month for Google Places API

**Timeline:** 2-3 weeks for full implementation

**ROI:** Break-even after Month 1, savings of $2,400+/year
