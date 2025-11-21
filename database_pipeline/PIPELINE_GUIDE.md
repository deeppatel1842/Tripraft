# 🚀 TripRaft Database Processing Pipeline

**Professional, Fully Automated Database Enrichment System**

Transform raw place data into production-ready, enriched database files with ranking scores and high-quality photos.

---

## 📋 Overview

The TripRaft Database Pipeline is a fully automated system that processes JSON files through:

1. **Ranking Calculation** - Intelligent scoring based on multiple factors
2. **Photo Enhancement** - Automatic fetching from Wikipedia/Wikimedia Commons
3. **Data Validation** - Structure and quality checks
4. **Metadata Enrichment** - Comprehensive tracking and attribution

### Architecture

```
┌─────────────────┐
│  Raw JSON File  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      DATABASE PIPELINE              │
│  ┌───────────────────────────────┐  │
│  │  1. Load & Validate           │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  2. Ranking Engine            │  │
│  │     - Calculate scores        │  │
│  │     - Sort by relevance       │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  3. Photo Engine              │  │
│  │     - Fetch Wikipedia photos  │  │
│  │     - Build gallery           │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  4. Metadata Enrichment       │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  5. Save Enriched Data        │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Enriched Database  │
│  - Ranked           │
│  - With Photos      │
│  - Production Ready │
└─────────────────────┘
```

---

## 🎯 Features

### Ranking Engine
- **Multi-factor scoring algorithm**
  - Tourist Priority: 45%
  - Traveler Experience: 25%
  - Tags & Categories: 15%
  - Duration Optimization: 10%
  - Cost Consideration: 5%
- **Automatic sorting** by rank score
- **Component breakdown** for debugging

### Photo Engine
- **Primary photo** from Wikipedia
- **Photo gallery** from Wikimedia Commons
- **Automatic fallback** to placeholders
- **Full attribution** and licensing info
- **Rate limiting** (respects API guidelines)

### Processing Features
- **Flexible input**: Single file or directory
- **Watch mode**: Auto-process new files
- **Archive system**: Moves processed files
- **Comprehensive logging**: Detailed logs for every run
- **Error handling**: Graceful failure recovery
- **Progress tracking**: Real-time updates

---

## 📁 Directory Structure

```
database_pipeline/
├── processor.py              # Main pipeline orchestrator
├── ranking_engine.py         # Ranking calculation module
├── photo_engine.py          # Photo fetching module
├── input/                   # Drop JSON files here
│   └── processed/           # Auto-archived after processing
├── output/                  # Enriched files saved here
├── logs/                    # Detailed processing logs
├── demo_input.json         # Demo file for testing
├── PIPELINE_GUIDE.md       # This file
└── README.md               # Quick start guide
```

---

## 🚀 Quick Start

### 1. Setup

```powershell
cd database_pipeline

# Install dependencies (if needed)
pip install requests
```

### 2. Run Demo

```powershell
# Process the demo file
python processor.py --input demo_input.json
```

This will:
- ✅ Load demo_input.json
- ✅ Calculate ranking scores for 3 places
- ✅ Fetch photos from Wikipedia/Commons
- ✅ Save enriched output to `output/demo_input.json`
- ✅ Show detailed progress logs

### 3. Check Output

```powershell
# View the enriched file
cat output/demo_input.json
```

You'll see each place now has:
- `rank_score` (0-1)
- `_rank_components` (score breakdown)
- `photos` object with primary and gallery
- Sorted by rank_score (highest first)

---

## 💼 Usage Modes

### Mode 1: Single File Processing

```powershell
python processor.py --input path/to/your-file.json
```

**When to use**: One-time processing of a specific file

### Mode 2: Batch Processing

```powershell
# Process all JSON files in input/ directory
python processor.py

# Or specify custom directories
python processor.py --input-dir ./my_data --output-dir ./enriched_data
```

**When to use**: Process multiple files at once

### Mode 3: Watch Mode (Automated)

```powershell
# Auto-process any new JSON files dropped into input/
python processor.py --watch

# Custom watch interval (default: 10 seconds)
python processor.py --watch --watch-interval 5
```

**When to use**: Continuous processing, production deployment

---

## 📊 Example Output

### Input (Raw)
```json
{
  "name_english": "Golden Gate Bridge",
  "rating_tourist_priority": 5.0,
  "rating_traveler_experience": 4.8,
  "cost": "Free",
  "suggested_duration": "1-2 hours",
  "tags": ["Landmark", "Iconic", "Photo Spot"]
}
```

### Output (Enriched)
```json
{
  "name_english": "Golden Gate Bridge",
  "rank_score": 0.8745,
  "_rank_components": {
    "Rt": 1.0,
    "Re": 0.96,
    "C": 1.0,
    "D": 0.72,
    "T": 0.22
  },
  "photos": {
    "primary": {
      "url": "https://upload.wikimedia.org/.../Golden_Gate_Bridge.jpg",
      "source": "wikipedia",
      "title": "Golden Gate Bridge",
      "attribution": "Image from Wikipedia article: Golden Gate Bridge"
    },
    "gallery": [
      {
        "url": "https://upload.wikimedia.org/.../Golden_Gate_Sunset.jpg",
        "source": "wikimedia_commons",
        "width": 800,
        "height": 600
      }
    ]
  },
  "rating_tourist_priority": 5.0,
  "rating_traveler_experience": 4.8,
  "cost": "Free",
  "suggested_duration": "1-2 hours",
  "tags": ["Landmark", "Iconic", "Photo Spot"]
}
```

---

## 🎬 Production Workflow

### Step 1: Upload Raw Data

```powershell
# Copy your JSON files to input directory
cp path/to/california.json database_pipeline/input/
cp path/to/texas.json database_pipeline/input/
```

### Step 2: Start Pipeline

```powershell
cd database_pipeline

# Option A: Process once
python processor.py

# Option B: Continuous monitoring
python processor.py --watch
```

### Step 3: Deploy Enriched Data

```powershell
# Enriched files are in output/
cp output/*.json ../web/backend/final_database/
```

### Step 4: Verify

```powershell
# Check output files
ls output/

# View processed files archive
ls input/processed/

# Check logs for any errors
cat logs/pipeline_*.log | Select-String "ERROR"
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Ranking Speed | ~100 places/sec |
| Photo Fetching | ~1 place/sec |
| API Rate Limit | 1 req/sec |

**Example**: 1000 places = ~20 minutes total

---

## 🛠️ Troubleshooting

### Issue: "No places found"

**Solution**: Check JSON structure. Pipeline supports:
- `cities[].places[]`
- `regions[].places[]`
- `places[]`
- `top_places[]`

### Issue: "Photos not downloading"

**Causes**:
- No internet connection
- Wikipedia API rate limiting
- Place name not found in Wikipedia

**Solution**: Pipeline automatically adds placeholders. Check logs for details.

### Issue: "Import errors"

**Solution**: 
```powershell
# Ensure you're in the correct directory
cd database_pipeline

# Run from here
python processor.py --input demo_input.json
```

---

## 💡 Tips & Best Practices

- **Always backup** raw data before processing
- **Use watch mode** for production deployments
- **Monitor logs** for API errors or rate limiting
- **Test with demo file** before processing large datasets
- **Archive processed files** are kept in `input/processed/`
- **Check statistics** in pipeline summary for quality metrics

---

**🎉 You're ready to build a world-class travel database!**
