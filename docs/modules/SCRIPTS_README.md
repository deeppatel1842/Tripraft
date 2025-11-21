# TripRaft Database Scripts

Essential scripts for building and managing the TripRaft places database.

## 📁 Active Scripts

### 1. `normalize-data-structure.js`
**Purpose**: Standardize JSON structure across all regions/countries  
**Usage**:
```bash
cd web/backend
npm run normalize
```
- Converts different data structures to unified format
- Adds standardized fields (region_id, country_code)
- Validates basic structure
- Outputs to `places_database/countries/`

### 2. `validate-data.js`
**Purpose**: Quality checks and data validation  
**Usage**:
```bash
node scripts/validate-data.js path/to/data.json
```
- Checks for missing required fields
- Validates coordinates, ratings, costs
- Reports data quality issues

### 3. `verify-database.js`
**Purpose**: Comprehensive database verification  
**Usage**:
```bash
node scripts/verify-database.js
```
- Verifies entire database integrity
- Checks for duplicates
- Validates relationships

### 4. `database-builder.js`
**Purpose**: Build and compile final database  
**Usage**:
```bash
node scripts/database-builder.js
```
- Compiles normalized data
- Creates search indexes
- Generates metadata files

## � Python Enhancement Scripts

Located in `web/backend/world_database/USA/`:

### 1. `photo_enhancement.py`
**Purpose**: Add Wikipedia and Wikimedia Commons photos  
**Usage**:
```bash
# Single file
python photo_enhancement.py --input data.json --output enhanced.json

# Entire directory
python photo_enhancement.py --input-dir ./data --output-dir ./enhanced
```

### 2. `ranking.py`
**Purpose**: Calculate and add ranking scores to places  
**Usage**:
```bash
# Single file
python ranking.py path/to/file.json

# Entire directory
python ranking.py path/to/folder
```

### 3. `finalize_database.py`
**Purpose**: Complete database preparation (ranking + photos)  
**Usage**:
```bash
# Full finalization
python finalize_database.py --input-dir ./raw_data --output-dir ./final_database

# Ranking only
python finalize_database.py --input-dir ./data --output-dir ./ranked --ranking-only

# Photos only
python finalize_database.py --input-dir ./data --output-dir ./photos --photos-only
```

## 🚀 Complete Workflow

### For Final Database Creation:

1. **Normalize data structure**:
   ```bash
   npm run normalize
   ```

2. **Validate data quality**:
   ```bash
   node scripts/validate-data.js places_database/countries/*.json
   ```

3. **Finalize database** (ranking + photos):
   ```bash
   cd world_database/USA
   python finalize_database.py --input-dir ../../places_database/countries --output-dir ../../final_database
   ```

4. **Build search indexes**:
   ```bash
   node scripts/database-builder.js
   ```

5. **Final verification**:
   ```bash
   node scripts/verify-database.js
   ```

## 📊 Database Structure

```
web/backend/
├── world_database/         # Original raw data
├── places_database/        # Normalized data
│   └── countries/
│       ├── usa-california.json
│       └── argentina.json
├── final_database/         # Ranked + photos
│   └── countries/
│       └── [finalized files]
└── scripts/                # Build scripts
```

## 🎯 Key Features

**Ranking System**:
- Tourist priority (45%)
- Traveler experience (25%)
- Tags & categories (15%)
- Duration optimization (10%)
- Cost consideration (5%)

**Photo Enhancement**:
- Primary photo from Wikipedia
- Gallery from Wikimedia Commons
- Automatic fallback to placeholders
- License and attribution tracking

**Data Quality**:
- Coordinate validation
- Missing field detection
- Duplicate prevention
- Structure consistency

## 💡 Notes

- Run scripts in order for best results
- Always validate before finalizing
- Keep backups of raw data
- Photo enhancement requires internet connection
- Rate limiting applies to Wikipedia/Commons APIs (1 req/sec)

**Input:**
- `world_database_2/argentina.json`
- `world_database/USA/california.json`

**Output:**
- `places_database/countries/argentina.json`
- `places_database/countries/usa-california.json`

---

### Step 2: Validate Data (Optional but Recommended)

Check for errors and warnings:

```bash
npm run validate
```

**What it checks:**
- Required fields present
- Valid coordinates (-90 to 90 lat, -180 to 180 lng)
- Valid tags and ratings
- Duplicate place IDs
- Photo URLs present
- AI summaries present

**Output:**
- Console summary
- `*.validation.txt` files for each country with issues

---

### Step 3: Build Search Index

Create optimized search index:

```bash
npm run build-index
```

**What it does:**
- Extracts key fields from all places
- Generates search keywords
- Creates lightweight index (< 5MB target)
- Builds country/region metadata

**Output:**
- `places_database/search-index.json` (~2-5 MB)
- `places_database/metadata.json` (~50-200 KB)

---

### Step 4: Run All (Normalize + Validate + Index)

```bash
npm run build-all
```

Runs all three scripts in sequence.

---

## 📊 Data Format

### Standardized Country File

```json
{
  "country": "Argentina",
  "country_code": "AR",
  "regions": [
    {
      "region_id": "buenos-aires",
      "name": "Buenos Aires",
      "name_english": "Buenos Aires",
      "type": "state",
      "coordinates": { "lat": -34.6037, "lng": -58.3816 },
      "nearest_airport": {
        "name": "Ministro Pistarini International Airport",
        "iata": "EZE",
        "city": "Ezeiza"
      },
      "places": [
        {
          "id": "place_001",
          "name_english": "Obelisco de Buenos Aires",
          "name_native": "Obelisco",
          "coordinates": { "lat": -34.6037, "lng": -58.3816 },
          "rating_tourist_priority": 8,
          "tags": ["landmark", "monument", "photo_spot"],
          "photos": { ... },
          "ai_summary": "...",
          "opening_hours": "...",
          "suggested_duration": "30 minutes",
          "cost": "Free"
        }
      ]
    }
  ],
  "metadata": {
    "enhanced_at": "2025-10-28T00:00:00Z",
    "total_places": 130,
    "total_regions": 5,
    "version": "4.0_standardized"
  }
}
```

### Search Index Format

```json
{
  "places": [
    {
      "id": "place_001",
      "name": "Obelisco de Buenos Aires",
      "slug": "obelisco-de-buenos-aires",
      "country": "Argentina",
      "country_code": "AR",
      "region": "Buenos Aires",
      "region_id": "buenos-aires",
      "coordinates": { "lat": -34.6037, "lng": -58.3816 },
      "rating": 8,
      "tags": ["landmark", "monument"],
      "photo": "https://upload.wikimedia.org/...",
      "keywords": "obelisco buenos aires argentina landmark monument icon",
      "duration": "30 minutes",
      "cost": "Free"
    }
  ],
  "total_places": 15000,
  "countries": 70,
  "last_updated": "2025-10-28T00:00:00Z"
}
```

### Metadata Format

```json
{
  "countries": [
    {
      "name": "Argentina",
      "code": "AR",
      "slug": "argentina",
      "total_places": 130,
      "regions": [
        {
          "id": "buenos-aires",
          "name": "Buenos Aires",
          "type": "state",
          "place_count": 20,
          "coordinates": { "lat": -34.6037, "lng": -58.3816 },
          "airport": "EZE"
        }
      ]
    }
  ],
  "total_countries": 70,
  "total_places": 15000,
  "last_updated": "2025-10-28T00:00:00Z"
}
```

---

## 🔧 Customization

### Adding New Countries

1. Place your country JSON file in `world_database/` or `world_database_2/`
2. Update `normalize-data-structure.js`:
   - Add country code to `COUNTRY_CODES` object
   - Add normalization function if structure is different
3. Run `npm run build-all`

### Modifying Validation Rules

Edit `validate-data.js`:
- `REQUIRED_FIELDS` - Required field names
- `VALID_TAGS` - Allowed tag values
- Add custom validation functions

### Optimizing Search Index

Edit `build-search-index.js`:
- `generateKeywords()` - Customize search keywords
- `createIndexEntry()` - Change indexed fields
- Reduce fields to decrease file size

---

## 🐛 Troubleshooting

### "Input directory not found"

Run `npm run normalize` first to create `places_database/countries/`.

### "Validation failed"

Check `*.validation.txt` files in `places_database/countries/` for details.

### Search index > 5MB

Options:
1. Remove verbose keywords
2. Reduce photo thumbnail URLs
3. Skip low-priority places (rating < 3)
4. Use pagination (split into multiple indexes)

### Duplicate place IDs

Find duplicates in validation report and update IDs to be unique:
```javascript
// Use format: {country}_{region}_{placename}
"id": "ar_buenos-aires_obelisco"
```

---

## 📦 Next Steps

After running these scripts:

1. **Copy to Frontend**:
   ```bash
   cp -r places_database/* ../frontend/public/data/
   ```

2. **Test in React**:
   ```javascript
   // Load search index
   const response = await fetch('/data/search-index.json');
   const index = await response.json();
   
   // Search
   const results = index.places.filter(p => 
     p.keywords.includes('museum')
   );
   ```

3. **Deploy to Cloudflare Pages**:
   ```bash
   git add .
   git commit -m "Add place database"
   git push origin main
   ```

---

## 📚 Documentation

- See `IMPLEMENTATION_STEPS.md` for full implementation plan
- See `HYBRID_ARCHITECTURE_FINAL.md` for architecture details

---

## 🤝 Contributing

To add more countries:
1. Ensure data follows one of the supported structures
2. Run normalization
3. Validate data quality
4. Submit PR with validated JSON

---

## 📝 License

MIT
