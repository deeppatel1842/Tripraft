# Quick Start: Places Engine with passed_countries

## 🚀 Getting Started

### 1. Verify Data Source
```bash
# Check that passed_countries exists and has data
ls -la web/backend/dataset/passed_countries/ | head -20

# Expected output: 90+ country folders (argentina, australia, austria, etc.)
```

### 2. Prepare Environment
```bash
cd web/backend/places_engine

# Install dependencies
pip install -r requirements.txt

# Verify config points to passed_countries
python -c "from config import PlacesEngineConfig; print(PlacesEngineConfig().dataset_path)"
# Output: .../dataset/passed_countries
```

### 3. Data Quality Pipeline (Optional)

Run these scripts to maintain data quality:

```bash
# Step 1: Update ranking scores
python ranking_score.py
# Updates rank_score (0-1) for all places based on AI summary keywords

# Step 2: Clean photos
python remove.py
# Resets all 'photos' to {} and removes old 'gallery' fields

# Step 3: Validate structure
python check.py
# Validates JSON, moves invalid files to failed_countries/
```

### 4. Prepare Dataset for Upload
```bash
# Test without uploading
python -m places_engine.pipeline.run_full_pipeline --dry-run

# Full preparation (generates prepared_data/)
python -m places_engine.pipeline.run_full_pipeline --skip-upload
```

### 5. Upload to Firestore
```bash
# Requires Firebase credentials (.env file)
python -m places_engine.pipeline.run_full_pipeline

# With specific credentials file
python -m places_engine.pipeline.run_full_pipeline --credentials /path/to/serviceAccountKey.json
```

### 6. Test API
```bash
# Start backend
cd web/backend
python app.py

# In another terminal, test endpoints
curl "http://localhost:5000/api/places/search?q=Eiffel%20Tower&limit=5"

curl "http://localhost:5000/api/places/autocomplete?q=paris"

curl "http://localhost:5000/api/places/country/france"
```

---

## 📊 Data Statistics

From `passed_countries/`:

```
Total Countries:        90+
Total City/Region Files: 1000+
Total Places:           50,000+
Average per Country:    200-500
Average per City:       20-50
```

### Sample Countries
- Argentina (10 cities)
- Australia (8 states)
- Austria (10 cities)
- Belgium (10 cities)
- Brazil (10 states)
- Canada (13 provinces)
- China (31 provinces)
- France (multiple regions)
- Germany (16 states)
- India (28 states)
- Japan (47 prefectures)
- USA (50 states)
- ... and 78 more

---

## 🔧 Configuration

### Default Settings
```python
# File: places_engine/config.py

# Dataset path (can be overridden with PLACES_DATASET_PATH env var)
dataset_path = BACKEND_DIR / 'dataset' / 'passed_countries'

# Output directory for prepared data
output_path = ENGINE_DIR / 'pipeline' / 'prepared_data'

# Firestore collections
COLLECTION_PLACES = 'places'
COLLECTION_CITIES = 'cities'
COLLECTION_COUNTRIES = 'countries'
COLLECTION_SEARCH_INDEX = 'search_index'
```

### Environment Variables
```bash
# Override dataset path
export PLACES_DATASET_PATH=/custom/path/to/dataset

# Firebase credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json

# Optional: Override prepared data output
export PLACES_OUTPUT_PATH=/custom/output/path
```

---

## 📋 File Structure in passed_countries

Each country has a folder with city/region JSON files:

```
argentina/
├── bariloche.json          # Patagonia region
├── buenos_aires.json       # Capital
├── cordoba.json            # Central region
├── el_calafate.json        # Glacier region
├── iguazu.json             # Waterfall region
├── mendoza.json            # Wine region
├── rosario.json            # River city
├── salta.json              # Mountain region
├── san_juan.json           # Desert region
└── ushuaia.json            # Southernmost city

australia/
├── Australian_Capital_Territory.json
├── New_South_Wales.json
├── Northern_Territory.json
├── Queensland.json
├── South_Australia.json
├── Tasmania.json
├── Victoria.json
└── Western_Australia.json
```

---

## 📈 Data Flow Summary

```
passed_countries/
    ↓ (JSON files)
ranking_score.py      ← Update scores
remove.py             ← Clean photos
check.py              ← Validate
    ↓ (Enhanced JSON)
run_full_pipeline.py
    ├─ prepare_dataset.py    ← Normalize & prepare
    ├─ upload_to_firestore.py ← Upload to Firestore
    └─ prepare_data/          ← Output directory
         (places.json, cities.json, countries.json)
    ↓
Firestore Collections
    ├─ places
    ├─ cities
    ├─ countries
    ├─ states
    └─ search_index
    ↓
API Routes (REST)
    ├─ /api/places/search
    ├─ /api/places/<id>
    ├─ /api/places/location
    ├─ /api/places/country/<name>
    └─ ... (8 total routes)
    ↓
React Frontend
    └─ Display to Users
```

---

## ✅ Checklist

- [ ] Verified `passed_countries` folder exists
- [ ] Verified data contains 90+ countries
- [ ] Updated `config.py` (should be auto-done: `dataset/passed_countries`)
- [ ] Ran `ranking_score.py` (optional but recommended)
- [ ] Ran `remove.py` (optional but recommended)
- [ ] Ran `check.py` (validates structure)
- [ ] Prepared dataset with `--dry-run` first
- [ ] Uploaded to Firestore
- [ ] Tested API endpoints
- [ ] Frontend loads places correctly
- [ ] Searched for a place and got results
- [ ] Autocomplete works
- [ ] Country view shows all states

---

## 🆘 Troubleshooting

### Q: "passed_countries folder not found"
```bash
# Check if it exists
ls -la web/backend/dataset/passed_countries/

# If missing, run check.py to organize files from countries/
cd web/backend/places_engine
python check.py
```

### Q: "No places found in search"
```bash
# Verify data was uploaded to Firestore
# Check Firestore console for collections:
# - places
# - cities
# - countries

# Test with a simple query
curl "http://localhost:5000/api/places/countries"
# Should return list of all countries
```

### Q: "Cache not working"
```bash
# Requires Redis running
# Check Redis status:
redis-cli ping
# Should return: PONG

# If not installed:
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
# Windows: Use Docker or WSL
```

### Q: "Firestore upload slow"
```bash
# Reduce batch size if hitting quota
# Edit: places_engine/pipeline/upload_to_firestore.py
BATCH_SIZE = 10  # Reduced from 20

# Or increase delay between batches
BATCH_DELAY = 5.0  # Increased from 3.0
```

### Q: "Photos not showing"
```bash
# Run photo enrichment
cd places_engine
python pipeline/photo_filled.py

# Or reset and re-enrich
python remove.py
# Then run full pipeline again
```

---

## 📚 Documentation Files

- **OPTIMIZATION_PLAN.md** - Architecture & performance goals
- **DATA_SOURCE_UPDATE_SUMMARY.md** - Migration details
- **ARCHITECTURE_FLOW_DIAGRAM.md** - System flow diagrams
- **QUICK_START.md** - This file

---

## 🎯 Next Steps

1. ✅ Run data quality scripts (ranking, clean, validate)
2. ✅ Prepare dataset
3. ✅ Upload to Firestore
4. ✅ Test API endpoints
5. ✅ Verify frontend loads places
6. ✅ Monitor performance metrics
7. ✅ Optimize if needed

---

## 📞 Support

For issues:
1. Check the troubleshooting section above
2. Review log files in `places_engine/logs/`
3. Check Firestore console for data
4. Run analysis: `python pipeline/analyze_dataset.py`

---

**Version**: 2.0.0  
**Data Source**: `dataset/passed_countries/`  
**Last Updated**: December 8, 2025  
**Status**: ✅ Production Ready
