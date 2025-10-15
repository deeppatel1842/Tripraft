# Quick Reference - What's New

## 🔧 Fixes Applied

| Issue | Status | Details |
|-------|--------|---------|
| NumPy/SciPy compatibility | ✅ Fixed | Installed numpy<1.28.0 |
| Bangkok data fetch error | ✅ Fixed | Improved error handling, auto-fetch |
| Location redundancy | ✅ Fixed | Nested attraction detection |
| Inefficient routing | ✅ Fixed | DBSCAN clustering (3km radius) |
| Pacing mismatch | ✅ Fixed | Moderate = 10h, Relaxed = 7h, Packed = 13h |
| Poor day naming | ✅ Fixed | Cluster-based naming |
| Duplicate hours | ✅ Fixed | De-duplication filter |

## ✨ New Features

### 1. Rankings Table
**Shows:** All attractions sorted by rank_score  
**Columns:** Rank, Name, Score, Rating, Reviews, Distance, Cluster, Type  
**Prompt:** `Show detailed rankings table? [Y/n]:`  
**Use:** Research all options, compare alternatives  

### 2. Other Top Places  
**Shows:** Top 10 places NOT in your itinerary  
**Details:** Rating, reviews, distance, type, website  
**Prompt:** `Show other top places not in itinerary? [Y/n]:`  
**Use:** Know alternatives if plans change  

## 🚀 How to Use

### Quick Start
```bash
cd web/backend/main_engine
python trip_planner.py
```

### Example Session
```
Enter city: san diego
Days: 3
Pacing: M
Show rankings? Y    ← NEW
Show other places? Y  ← NEW

→ Rankings table (50 attractions)
→ Your itinerary (Balboa Park, etc.)
→ Other top 10 (SeaWorld, USS Midway, etc.)
```

### Test Auto-Fetch
```
Enter city: bangkok    ← No data yet

→ Automatically fetches via main_engine.py
→ Creates bangkok.json
→ Generates itinerary
```

## 📋 What You'll See

### Before (Old Version)
```
Enter a city: bangkok
No local data for 'Bangkok'. Running data engine...
ERROR: Data engine failed for 'bangkok'. Error:
[Confusing numpy error message]
```

### After (New Version)  
```
Enter a city: bangkok

======================================================================
No local data for 'Bangkok'.
Running data engine to fetch attractions...
======================================================================

✓ Data for 'Bangkok' fetched successfully!

Show detailed rankings table? [Y/n]: Y

======================================================================
--- 📊 ATTRACTION RANKINGS ---
======================================================================
Rank  Place Name                Score    Rating  Reviews    Distance  Cluster
1     Grand Palace              0.9856   4.9     125,432    1.2 km    0
2     Wat Pho                   0.9745   4.8     98,765     1.5 km    0
...

======================================================================
--- 🗺️  BANGKOK EXPLORER ---
======================================================================
--- Day 1: Exploring Grand Palace Area ---
[09:00] ● Arrive at: Grand Palace
...

======================================================================
--- 📍 OTHER TOP PLACES YOU MAY VISIT ---
======================================================================
 1. Chatuchak Weekend Market
    ⭐ Rating: 4.5/5.0 (45,231 reviews)
    📍 Distance: 8.3 km from city center
    🏷️  Type: Market
    📊 Rank Score: 0.8923
```

## 🎯 Key Features

| Feature | What It Does | When to Use |
|---------|-------------|-------------|
| **Auto-fetch** | Calls main_engine.py for new cities | Automatic - no action needed |
| **Rankings table** | Shows all 50 places with scores | Research phase, comparing options |
| **Other places** | Shows top 10 not in itinerary | Planning flexibility, extended trips |
| **Clustering** | Groups nearby attractions | Automatic - improves routing |
| **Nested detection** | Parks + museums scheduled together | Automatic - fixes redundancy |

## 💡 Tips

### Skip Optional Features
```
Show detailed rankings table? [Y/n]: n    ← Type 'n' to skip
Show other top places? [Y/n]: n           ← Type 'n' to skip
```

### See Full Rankings
Rankings table shows top 50 by default. To see more, edit `trip_planner.py`:
```python
for i, place in enumerate(ranked_places[:50], 1):  
# Change [:50] to [:100] for more
```

### Adjust "Other Places" Count
Default is 10. To change, edit `trip_planner.py`:
```python
other_places = get_other_top_places(..., top_n=10)
# Change top_n=10 to top_n=20 for more
```

### Filter by Cluster
Look at rankings table cluster column:
- Same cluster number = nearby attractions
- Visit places in same cluster on same day
- Minimize driving time

## 🧪 Test Commands

### Verify NumPy Fix
```bash
python -c "from scipy.spatial import KDTree; print('✓ OK')"
```
Should print `✓ OK` with no errors

### Test Import
```bash
python -c "from trip_planner import create_rankings_table, get_other_top_places; print('✓ OK')"
```
Should print `✓ OK` with no errors

### Test with San Diego
```bash
python trip_planner.py
# san diego, 3, M, Y, Y
```
Should show rankings + itinerary + other places

### Test with Bangkok (auto-fetch)
```bash
python trip_planner.py  
# bangkok, 3, M, Y, Y
```
Should auto-fetch data, then show everything

## 📁 Files Changed

**Modified:**
- `web/backend/main_engine/trip_planner.py` (all improvements)

**Created:**
- `docs/TRIP_PLANNER_IMPROVEMENTS.md`
- `docs/IMPROVEMENTS_SUMMARY.md`
- `docs/QUICK_FIX_GUIDE.md`
- `docs/NEW_FEATURES_RANKINGS.md`
- `docs/IMPLEMENTATION_SUMMARY.md`
- `docs/QUICK_REFERENCE.md` (this file)
- `web/backend/main_engine/test_improvements.py`

## ❓ Troubleshooting

### "main_engine.py not found"
**Solution:** Make sure you're in the correct directory:
```bash
cd web/backend/main_engine
python trip_planner.py
```

### NumPy error persists
**Solution:** Reinstall with version constraint:
```bash
pip install "numpy>=1.21.6,<1.28.0" --force-reinstall
```

### No data shows up
**Solution:** Check if JSON file exists:
```bash
ls adaptive_database_5/hubs/
# Should show: san_diego.json, seattle.json, etc.
```

### Rankings table too wide
**Solution:** Maximize terminal window or redirect to file:
```bash
python trip_planner.py > output.txt
```

## 📞 Support

### Check Logs
```bash
# Look for error messages in console output
# Enable debug logging if needed
```

### Verify Environment
```bash
python --version    # Should be 3.11+
pip list | grep numpy    # Should show <1.28.0
pip list | grep scipy    # Should be installed
```

---

## 🎉 Summary

**Everything is ready!** Just run:
```bash
cd web/backend/main_engine
python trip_planner.py
```

**Two new prompts will ask:**
1. Show rankings table? → See all attractions
2. Show other places? → See what you're missing

**Both are optional** - press Enter to see, or type 'n' to skip.

**Works with existing data** - No new API calls needed!
