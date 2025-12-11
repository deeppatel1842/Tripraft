# TripRaft Places API - Implementation Checklist

## Overview
Use this checklist to track your progress implementing the Places API.

**Estimated Total Time:** 2-3 weeks
**Estimated Cost:** $2-3/month for 10K users

---

## Phase 1: Setup & Configuration (Day 1)

### Firebase Setup
- [ ] Verify Firebase project exists
- [ ] Check Firebase Admin SDK credentials in `.env`
- [ ] Test Firebase connection from backend
- [ ] Review Firebase Console quotas/limits
- [ ] Set up billing alerts (optional but recommended)

**Environment Variables to Check:**
```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@your-project.iam.gserviceaccount.com
```

**Verification:**
```powershell
python -c "import firebase_admin; firebase_admin.initialize_app(); print('✅ Firebase OK')"
```

---

### Redis Setup
- [ ] Verify Redis is installed
- [ ] Test Redis connection (`redis-cli ping`)
- [ ] Check Redis configuration in `config.py`
- [ ] Consider Redis persistence options (RDB/AOF)
- [ ] Set up Redis monitoring (optional)

**Verification:**
```powershell
redis-cli ping  # Should return PONG
```

---

### Dependencies
- [ ] Python virtualenv activated
- [ ] All requirements installed (`pip install -r requirements.txt`)
- [ ] Firebase CLI installed (for deploying indexes)
- [ ] Test imports work

**Verification:**
```powershell
pip list | findstr firebase
pip list | findstr redis
pip list | findstr flask
```

---

## Phase 2: Dataset Preparation (Day 1-2)

### Pre-flight Checks
- [ ] Review dataset folder structure
- [ ] Count total countries (should be ~80)
- [ ] Spot-check 2-3 JSON files for format
- [ ] Backup dataset folder (copy to safe location)
- [ ] Review one complete JSON file structure

**Commands:**
```powershell
cd web\backend\dataset\countries
ls | Measure-Object  # Should show ~80 folders
```

---

### Apply Rank Scores
- [ ] Review `apply_rank_scores.py` script
- [ ] Understand ranking algorithm
- [ ] Run script on dataset
- [ ] Verify rank_score added to all places
- [ ] Check score distribution (most should be 0.5-0.9)

**Commands:**
```powershell
cd web\backend
python places_engine\apply_rank_scores.py
```

**Time:** ~2-5 minutes

---

### Add Wikimedia Photos (Optional)
- [ ] Review `add_wikimedia_photos.py` script
- [ ] Decide if you want to run this now or later
- [ ] Test on single file first
- [ ] Run on full dataset if desired
- [ ] Verify photos added with attribution

**Commands:**
```powershell
# Test on single file
python places_engine\add_wikimedia_photos.py dataset\countries\argentina\bariloche.json

# Run on all (takes 10-30 min)
python places_engine\add_wikimedia_photos.py dataset\countries\
```

**Time:** ~10-30 minutes (optional, can skip for now)

---

### Prepare Dataset
- [ ] Review `prepare_dataset.py` script
- [ ] Understand what it does (validation, normalization, ID generation)
- [ ] Run in dry-run mode first
- [ ] Review validation report
- [ ] Fix any validation errors
- [ ] Run with `--no-dry-run` to save prepared data
- [ ] Verify output files created

**Commands:**
```powershell
# Dry run (validation only)
python places_engine\prepare_dataset.py --dataset-path dataset

# Check validation report
cat dataset\prepared\validation_report.json

# Run for real
python places_engine\prepare_dataset.py --dataset-path dataset --no-dry-run
```

**Expected Output:**
- `dataset/prepared/places.json` (5000+ places)
- `dataset/prepared/cities.json` (350+ cities)
- `dataset/prepared/countries.json` (80+ countries)
- `dataset/prepared/validation_report.json`

**Time:** ~5-10 minutes

---

## Phase 3: Firestore Setup (Day 2)

### Deploy Firestore Indexes
- [ ] Copy `firestore.indexes.json` to backend root
- [ ] Review index definitions
- [ ] Deploy indexes using Firebase CLI
- [ ] Wait for indexes to build (5-10 minutes)
- [ ] Verify indexes in Firebase Console

**Commands:**
```powershell
cd web\backend
cp places_engine\firestore.indexes.json .
firebase deploy --only firestore:indexes
```

**Verification:**
- Open Firebase Console → Firestore → Indexes
- Should see 7 composite indexes
- Status should be "Building" then "Enabled"

**Time:** ~5-10 minutes (plus waiting for build)

---

### Deploy Firestore Rules
- [ ] Review current `firestore.rules`
- [ ] Add rules for places collections
- [ ] Deploy rules
- [ ] Test read access (should be public)
- [ ] Test write access (should be admin-only)

**Rules to Add:**
```javascript
// Public read for places
match /places/{placeId} {
  allow read: if true;
  allow write: if request.auth != null && request.auth.token.admin == true;
}

match /cities/{cityId} {
  allow read: if true;
  allow write: if false;
}

match /countries/{countryId} {
  allow read: if true;
  allow write: if false;
}
```

**Commands:**
```powershell
firebase deploy --only firestore:rules
```

---

### Upload to Firestore
- [ ] Review `upload_to_firestore.py` script
- [ ] Run in dry-run mode first
- [ ] Review what would be uploaded
- [ ] Run with `--no-dry-run` to actually upload
- [ ] Monitor progress (should take 5-15 minutes)
- [ ] Verify upload report
- [ ] Check Firebase Console for documents

**Commands:**
```powershell
# Dry run
python places_engine\upload_to_firestore.py --prepared-data-path dataset\prepared

# Upload for real
python places_engine\upload_to_firestore.py --prepared-data-path dataset\prepared --no-dry-run
```

**Expected Output:**
```
UPLOADING COUNTRIES
✅ Countries uploaded: 80/80

UPLOADING CITIES
✅ Cities uploaded: 350/350

UPLOADING PLACES
✅ Places uploaded: 5000/5000
```

**Verification:**
- Open Firebase Console → Firestore
- Check `countries` collection (should have ~80 docs)
- Check `cities` collection (should have ~350 docs)
- Check `places` collection (should have ~5000 docs)
- Spot-check a few documents

**Time:** ~5-15 minutes

---

## Phase 4: API Implementation (Day 3-4)

### Create Services
- [ ] Review `services/places_service.py`
- [ ] Understand service methods
- [ ] Test imports work
- [ ] Verify Redis integration
- [ ] Check Firestore client initialization

**Verification:**
```powershell
python -c "from services.places_service import PlacesService; print('✅ Service imports OK')"
```

---

### Create API Routes
- [ ] Review `api/places_routes.py`
- [ ] Understand endpoint definitions
- [ ] Check parameter validation
- [ ] Verify error handling

**Verification:**
```powershell
python -c "from api.places_routes import places_bp; print('✅ Routes import OK')"
```

---

### Update run.py
- [ ] Add Places service initialization
- [ ] Register Places blueprint
- [ ] Test server starts without errors
- [ ] Check logs for startup messages

**Code to Add to `run.py`:**
```python
from api.places_routes import places_bp, init_places_service
from firebase_admin import firestore
from cache.redis_cache import RedisCache

# After Firebase initialization
db = firestore.client()
cache = RedisCache()

# Initialize Places service
init_places_service(db, cache)

# Register blueprint
app.register_blueprint(places_bp)
```

**Verification:**
```powershell
python run.py  # Should start without errors
```

---

## Phase 5: Testing (Day 4)

### Health Check
- [ ] Test health endpoint
- [ ] Verify database connection
- [ ] Verify cache connection
- [ ] Check response format

**Command:**
```powershell
curl http://localhost:5000/api/v1/places/health
```

**Expected Response:**
```json
{
  "success": true,
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "countries_count": 80
}
```

---

### Basic Endpoints
- [ ] Test get all countries
- [ ] Test get cities by country
- [ ] Test place detail by ID
- [ ] Verify GeoPoint conversion
- [ ] Check response times

**Commands:**
```powershell
# Get all countries
curl http://localhost:5000/api/v1/countries

# Get cities in Argentina
curl "http://localhost:5000/api/v1/cities?country=Argentina"

# Get place details
curl http://localhost:5000/api/v1/places/argentina_san_carlos_de_bariloche_cerro_catedral
```

---

### Search Endpoints
- [ ] Test text search
- [ ] Test city filter
- [ ] Test country filter
- [ ] Test tags filter
- [ ] Test cost filter
- [ ] Test rating filter
- [ ] Test pagination
- [ ] Verify cache behavior (hit/miss)

**Commands:**
```powershell
# Text search
curl "http://localhost:5000/api/v1/places/search?query=cathedral"

# City filter
curl "http://localhost:5000/api/v1/places/search?city=San Carlos de Bariloche&limit=10"

# Multiple filters
curl "http://localhost:5000/api/v1/places/search?country=Argentina&cost=Free&rating_min=4"

# Pagination
curl "http://localhost:5000/api/v1/places/search?city=Bariloche&limit=5&offset=5"
```

---

### Geospatial Endpoints
- [ ] Test nearby places
- [ ] Verify distance calculation
- [ ] Test different radius values
- [ ] Check coordinate validation
- [ ] Verify results sorted by distance

**Commands:**
```powershell
# Nearby places (Bariloche civic center)
curl "http://localhost:5000/api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=10000&limit=10"

# Small radius (1km)
curl "http://localhost:5000/api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=1000"

# Large radius (50km)
curl "http://localhost:5000/api/v1/places/nearby?lat=-41.1456&lng=-71.3103&radius=50000"
```

---

### Popular Places
- [ ] Test popular without filters
- [ ] Test popular by country
- [ ] Verify rank_score ordering
- [ ] Check limit parameter

**Commands:**
```powershell
# Top 20 popular places worldwide
curl "http://localhost:5000/api/v1/popular?limit=20"

# Top 10 in Argentina
curl "http://localhost:5000/api/v1/popular?country=Argentina&limit=10"
```

---

## Phase 6: Performance Testing (Day 5)

### Cache Performance
- [ ] Test cold cache (first request)
- [ ] Test warm cache (second request)
- [ ] Verify cache hit indicators
- [ ] Check Redis memory usage
- [ ] Measure response time improvements

**Commands:**
```powershell
# First request (cache miss)
curl http://localhost:5000/api/v1/countries

# Second request (cache hit)
curl http://localhost:5000/api/v1/countries  # Should be much faster
```

**Expected:**
- Cold: ~100-200ms
- Hot: ~10-30ms
- cache_hit: false → true

---

### Load Testing
- [ ] Install load testing tool (optional)
- [ ] Run 100 concurrent requests
- [ ] Monitor response times
- [ ] Check error rates
- [ ] Verify cache hit rate improves

**Tools:**
- Apache Bench (`ab`)
- K6
- Locust
- Artillery

**Example (if you have `ab`):**
```powershell
ab -n 1000 -c 10 http://localhost:5000/api/v1/countries
```

---

### Database Monitoring
- [ ] Check Firestore usage in Firebase Console
- [ ] Verify read counts are low (due to cache)
- [ ] Monitor query performance
- [ ] Check index usage
- [ ] Set up cost alerts

**Firebase Console Checks:**
- Firestore → Usage tab
- Should see low read counts after cache warms up
- Index usage should be green

---

## Phase 7: Frontend Integration (Week 2)

### API Client
- [ ] Create API client service in React
- [ ] Add environment variables for API URL
- [ ] Implement error handling
- [ ] Add loading states
- [ ] Test CORS configuration

**React Example:**
```javascript
// services/placesApi.js
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';

export const searchPlaces = async (params) => {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(`${API_BASE}/places/search?${query}`);
  return response.json();
};
```

---

### Search Component
- [ ] Create search input component
- [ ] Add filter controls (city, country, cost, rating)
- [ ] Implement debounced search
- [ ] Show search results
- [ ] Add pagination controls

---

### Place Details
- [ ] Create place detail page/modal
- [ ] Display all place information
- [ ] Show photos (if available)
- [ ] Add Google Maps integration (using coordinates)
- [ ] Display opening hours, tips, etc.

---

### Map Integration
- [ ] Create map component
- [ ] Plot places as markers
- [ ] Implement nearby places on map
- [ ] Add place clustering for zoom levels
- [ ] Click marker to show details

---

### Popular Places
- [ ] Create popular places widget
- [ ] Filter by country
- [ ] Show rank scores visually
- [ ] Link to place details

---

## Phase 8: Optimization (Week 3)

### Performance
- [ ] Optimize bundle size
- [ ] Lazy load components
- [ ] Implement virtualization for long lists
- [ ] Add request caching in frontend
- [ ] Optimize images

---

### User Experience
- [ ] Add loading skeletons
- [ ] Implement error boundaries
- [ ] Add retry logic for failed requests
- [ ] Show helpful error messages
- [ ] Add empty states

---

### SEO (if applicable)
- [ ] Add meta tags for place pages
- [ ] Implement schema.org markup
- [ ] Generate sitemap
- [ ] Add robots.txt
- [ ] Server-side rendering (if needed)

---

## Phase 9: Production Readiness (Week 3)

### Security
- [ ] Review Firestore rules
- [ ] Add rate limiting to API
- [ ] Implement API key authentication (if needed)
- [ ] Enable HTTPS
- [ ] Set up CORS properly

---

### Monitoring
- [ ] Set up error tracking (Sentry?)
- [ ] Add application metrics
- [ ] Monitor API response times
- [ ] Track cache hit rates
- [ ] Set up alerts for errors/slowness

---

### Documentation
- [ ] API documentation (Swagger/OpenAPI?)
- [ ] README with setup instructions
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Troubleshooting guide

---

### Deployment
- [ ] Set up production environment
- [ ] Configure production Firebase project
- [ ] Deploy backend (Heroku/Railway/GCP?)
- [ ] Deploy frontend (Vercel/Netlify?)
- [ ] Configure custom domain
- [ ] Set up SSL certificates
- [ ] Test production deployment

---

## Phase 10: Maintenance (Ongoing)

### Regular Tasks
- [ ] Monitor Firestore costs weekly
- [ ] Check Redis memory usage
- [ ] Review error logs
- [ ] Update dataset as needed
- [ ] Add new countries/cities

---

### Dataset Updates
- [ ] Process: Update JSON → Prepare → Upload
- [ ] Use `--allow-duplicates` flag to overwrite
- [ ] Verify updates in production
- [ ] Clear relevant cache keys

---

### Performance Review
- [ ] Monthly performance audit
- [ ] Review cache hit rates
- [ ] Analyze slow queries
- [ ] Optimize indexes if needed
- [ ] Scale resources if needed

---

## Success Metrics

### Technical Metrics
- [ ] API response time < 200ms (cold)
- [ ] API response time < 50ms (hot)
- [ ] Cache hit rate > 90%
- [ ] Firestore reads < 50K/day (with cache)
- [ ] Error rate < 0.1%
- [ ] Uptime > 99.9%

### Business Metrics
- [ ] Monthly cost < $5
- [ ] 10K+ users supported
- [ ] Search success rate > 95%
- [ ] User satisfaction score > 4/5

---

## Troubleshooting Checklist

### API Not Starting
- [ ] Check Python version (3.8+)
- [ ] Verify virtualenv activated
- [ ] Check all dependencies installed
- [ ] Review error logs
- [ ] Verify Firebase credentials
- [ ] Check Redis is running

### Slow Queries
- [ ] Check if indexes are enabled
- [ ] Verify cache is working
- [ ] Monitor Firestore Console
- [ ] Check network latency
- [ ] Review query complexity

### High Costs
- [ ] Check Firestore read counts
- [ ] Verify cache hit rate
- [ ] Look for query patterns
- [ ] Optimize indexes
- [ ] Increase cache TTLs

---

## Resources

### Documentation
- [ ] `docs/PLACES_API_ARCHITECTURE_PLAN.md` - Full architecture
- [ ] `docs/PLACES_API_QUICK_START.md` - Quick start guide
- [ ] `docs/DATABASE_OPTIONS_COMPARISON.md` - Database comparison
- [ ] `places_engine/README.md` - Pipeline tools
- [ ] This checklist

### Tools
- Firebase Console: https://console.firebase.google.com
- Firestore pricing: https://firebase.google.com/pricing
- Redis docs: https://redis.io/documentation

---

## Completion Status

**Progress:** ___/100 tasks completed

**Estimated Completion Date:** __________

**Blockers/Issues:**
1. 
2. 
3. 

**Notes:**
- 
- 
- 

---

## Sign-off

**Phase 1 Complete:** [ ] Date: ________
**Phase 2 Complete:** [ ] Date: ________
**Phase 3 Complete:** [ ] Date: ________
**Phase 4 Complete:** [ ] Date: ________
**Phase 5 Complete:** [ ] Date: ________
**Production Ready:** [ ] Date: ________

**Total Time Spent:** _____ hours
**Total Cost:** $_____ /month

---

Good luck with your implementation! 🚀
