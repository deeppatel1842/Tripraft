# TripRaft Places API - Quick Start Guide

## Overview

Self-hosted Places API using your dataset of 80+ countries. Replaces Google Places API with zero ongoing costs for small-medium scale.

**Tech Stack:**
- Database: Firebase Firestore
- Cache: Redis
- Backend: Python/Flask
- Dataset: 80+ countries, 1000+ places

---

## Step-by-Step Implementation

### Phase 1: Prepare Dataset (30 minutes)

**1. Run Dataset Preparation:**
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\backend

# Activate virtualenv
& C:\Users\Kashyap\Documents\Deep\Travel\wayfinder\Scripts\Activate.ps1

# Dry run first (validation only)
python places_engine/prepare_dataset.py --dataset-path dataset

# Check validation report
cat dataset/prepared/validation_report.json

# If validation passes, run for real
python places_engine/prepare_dataset.py --dataset-path dataset --no-dry-run
```

**What this does:**
- Validates all JSON files against schema
- Generates unique IDs for each place
- Normalizes coordinates, tags, costs
- Creates `dataset/prepared/` with:
  - `places.json` (all places)
  - `cities.json` (all cities)
  - `countries.json` (all countries)
  - `validation_report.json` (stats)

---

### Phase 2: Upload to Firestore (20 minutes)

**1. Verify Firebase credentials in `.env`:**
```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@your-project.iam.gserviceaccount.com
```

**2. Create Firestore indexes:**
```powershell
# Copy indexes configuration
cp places_engine/firestore.indexes.json .

# Deploy indexes (requires Firebase CLI)
firebase deploy --only firestore:indexes
```

**3. Upload data:**
```powershell
# Dry run first
python places_engine/upload_to_firestore.py --prepared-data-path dataset/prepared

# Check what would be uploaded, then run for real
python places_engine/upload_to_firestore.py --prepared-data-path dataset/prepared --no-dry-run
```

**Expected output:**
```
UPLOADING COUNTRIES
✅ Countries uploaded: 80/80

UPLOADING CITIES
✅ Cities uploaded: 350/350

UPLOADING PLACES
✅ Places uploaded: 5000/5000

Total time: ~5-10 minutes
```

---

### Phase 3: Enable Places API (10 minutes)

**1. Update `run.py` to register Places API:**
```python
# Add to run.py
from api.places_routes import places_bp, init_places_service
from firebase_admin import firestore
from cache.redis_cache import RedisCache

# Initialize Firestore
db = firestore.client()

# Initialize Redis cache
cache = RedisCache()

# Initialize Places service
init_places_service(db, cache)

# Register blueprint
app.register_blueprint(places_bp)
```

**2. Start backend server:**
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\backend
python run.py
```

---

### Phase 4: Test API (5 minutes)

**Test endpoints:**

1. **Health check:**
```powershell
curl http://localhost:5000/api/v1/places/health
```

2. **Get all countries:**
```powershell
curl http://localhost:5000/api/v1/countries
```

3. **Search places:**
```powershell
curl "http://localhost:5000/api/v1/places/search?city=San Carlos de Bariloche&limit=5"
```

4. **Get place details:**
```powershell
curl http://localhost:5000/api/v1/places/argentina_san_carlos_de_bariloche_cerro_catedral
```

5. **Nearby places:**
```powershell
curl "http://localhost:5000/api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=10000"
```

6. **Popular places:**
```powershell
curl "http://localhost:5000/api/v1/popular?country=Argentina&limit=10"
```

---

## Firestore Indexes Configuration

Create `firestore.indexes.json`:

```json
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
        { "fieldPath": "city", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "country", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "cost", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "rating_tourist_priority", "order": "DESCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    }
  ]
}
```

Deploy:
```powershell
firebase deploy --only firestore:indexes
```

---

## Firestore Rules

Update `firestore.rules`:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Public read access for places
    match /places/{placeId} {
      allow read: if true;
      allow write: if request.auth != null 
                   && get(/databases/$(database)/documents/users/$(request.auth.uid)).data.admin == true;
    }
    
    // Public read access for cities
    match /cities/{cityId} {
      allow read: if true;
      allow write: if false;
    }
    
    // Public read access for countries
    match /countries/{countryId} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

Deploy:
```powershell
firebase deploy --only firestore:rules
```

---

## API Documentation

### Base URL
```
http://localhost:5000/api/v1
```

### Endpoints

#### 1. Search Places
```
GET /places/search
```

**Query Parameters:**
- `query` (string, optional) - Text search
- `city` (string, optional) - Filter by city
- `country` (string, optional) - Filter by country
- `tags` (string, optional) - Comma-separated tags
- `cost` (string, optional) - "Free" or "Paid"
- `rating_min` (number, optional) - Minimum rating (1-5)
- `limit` (number, optional) - Results per page (default 20, max 100)
- `offset` (number, optional) - Pagination offset (default 0)

**Example:**
```bash
GET /api/v1/places/search?query=museum&city=Bariloche&limit=5
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "places": [
    {
      "id": "argentina_bariloche_civic_center",
      "name": "Civic Center & Lake Nahuel Huapi",
      "city": "San Carlos de Bariloche",
      "country": "Argentina",
      "rank_score": 0.8065,
      "coordinates": {
        "latitude": -41.1456,
        "longitude": -71.3103
      },
      "tags": ["Landmark", "Lake", "Culture"],
      "cost": "Free",
      "ratings": {
        "tourist_priority": 5,
        "traveler_experience": 4
      }
    }
  ],
  "cache_hit": false,
  "response_time_ms": 145
}
```

---

#### 2. Get Place Details
```
GET /places/{place_id}
```

**Example:**
```bash
GET /api/v1/places/argentina_bariloche_cerro_catedral
```

---

#### 3. Nearby Places
```
GET /places/nearby
```

**Query Parameters:**
- `lat` (number, required) - Latitude
- `lng` (number, required) - Longitude
- `radius` (number, optional) - Radius in meters (default 5000)
- `limit` (number, optional) - Max results (default 20, max 100)

**Example:**
```bash
GET /api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=10000
```

---

#### 4. Popular Places
```
GET /popular
```

**Query Parameters:**
- `country` (string, optional) - Filter by country
- `limit` (number, optional) - Max results (default 20, max 100)

**Example:**
```bash
GET /api/v1/popular?country=Argentina&limit=10
```

---

#### 5. Get All Countries
```
GET /countries
```

---

#### 6. Get Cities by Country
```
GET /cities
```

**Query Parameters:**
- `country` (string, required) - Country name

**Example:**
```bash
GET /api/v1/cities?country=Argentina
```

---

## Performance Optimization

### Redis Caching

Cache TTLs:
- Place details: 24 hours
- Search results: 15 minutes
- City lists: 6 hours
- Popular places: 1 hour

**Cache hit rates:**
- Cold start: 0%
- After 1 hour: ~70%
- Steady state: ~95%

**Cost savings:**
- Without cache: ~$15/month (10K users)
- With cache: ~$2/month (10K users)

---

## Monitoring

### Key Metrics

1. **API Performance:**
   - Place details: < 50ms (cached)
   - Search: < 200ms
   - Nearby: < 300ms

2. **Cache Performance:**
   - Hit rate: > 90%
   - Memory usage: < 500MB

3. **Firestore Usage:**
   - Reads/day: Track in Firebase Console
   - Target: < 50K reads/day with cache

---

## Troubleshooting

### Issue: "Places service not initialized"
**Solution:** Add `init_places_service()` call in `run.py` before registering blueprint.

### Issue: "Firebase credentials not found"
**Solution:** Check `.env` file has correct `FIREBASE_*` variables.

### Issue: "Firestore index required"
**Solution:** Deploy indexes with `firebase deploy --only firestore:indexes`.

### Issue: "Cache not working"
**Solution:** Check Redis is running: `redis-cli ping` should return `PONG`.

---

## Cost Estimation

### Firebase Firestore (10K daily users)

| Metric | Usage | Cost |
|--------|-------|------|
| Reads (with 95% cache) | ~37K/day | $2/month |
| Writes | ~1K/day | $0.50/month |
| Storage (2GB) | 2GB | FREE |
| **Total** | | **~$2.50/month** |

### Comparison to Google Places API

| Service | Cost (10K users) | Cost (100K users) |
|---------|------------------|-------------------|
| **TripRaft API** | $2.50/month | $20/month |
| Google Places | $200/month | $2,000/month |
| **Savings** | **98.7%** | **99%** |

---

## Next Steps

1. ✅ **Week 1:** Complete data preparation and upload
2. ✅ **Week 2:** API development and testing
3. **Week 3:** Frontend integration
4. **Week 4:** Performance optimization and monitoring

---

## Additional Features (Future)

- [ ] Autocomplete endpoint
- [ ] User favorites
- [ ] Place reviews/ratings
- [ ] Photo upload/management
- [ ] Admin panel
- [ ] Analytics dashboard
- [ ] Export/backup automation

---

## Support

For issues or questions, check:
1. `docs/PLACES_API_ARCHITECTURE_PLAN.md` - Full architecture
2. Validation report: `dataset/prepared/validation_report.json`
3. Upload report: `dataset/prepared/upload_report.json`
