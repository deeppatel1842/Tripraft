# Trip Planner - Complete System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 🎯 USER STARTS TRIP PLANNER                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: City Name (e.g., "san diego", "bangkok")               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │  Data Exists?     │
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 │ NO                      │ YES
                 ↓                         ↓
    ┌──────────────────────┐    ┌──────────────────────┐
    │ 🔄 AUTO-FETCH DATA   │    │ ✓ Load existing JSON │
    │                      │    │   (e.g., san_diego.  │
    │ Call main_engine.py  │    │   json)              │
    │ - Geocode city       │    └──────────┬───────────┘
    │ - Search attractions │               │
    │ - Calculate scores   │               │
    │ - Save to JSON       │               │
    └──────────┬───────────┘               │
               └───────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: Trip Parameters                                         │
│  - Number of days (1-7)                                         │
│  - Pacing (R/M/P)                                               │
│  - Exclude types (optional)                                     │
│  - Require types (optional)                                     │
│  - Require specific places (optional)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  🆕 INPUT: Display Options                                      │
│  - Show detailed rankings table? [Y/n]                          │
│  - Show other top places? [Y/n]                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  🔧 PROCESSING: Enhance Data                                    │
│  1. Detect nested attractions (museums in parks)                │
│  2. Perform spatial clustering (group by 3km radius)            │
│  3. Add cluster_id to each place                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │ Show Rankings?    │
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 │ YES                     │ NO (skip)
                 ↓                         ↓
    ┌──────────────────────────────┐      │
    │ 📊 DISPLAY RANKINGS TABLE    │      │
    │                              │      │
    │ Rank | Name | Score | Rating│      │
    │   1  | Park | 0.967 | 4.8   │      │
    │   2  | Sea  | 0.897 | 4.4   │      │
    │  ... | ...  | ...   | ...   │      │
    │                              │      │
    │ Shows: Top 50 attractions    │      │
    │ Sorted by: rank_score DESC   │      │
    │ Includes: Cluster IDs        │      │
    └──────────────┬───────────────┘      │
                   └──────────┬───────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  🧠 GENERATE ITINERARY (Plan 1: City Only)                      │
│                                                                 │
│  For each day:                                                  │
│    1. Select seed attraction (highest rank in cluster)          │
│    2. Find nearby places in same cluster                        │
│    3. Check opening hours & travel time                         │
│    4. Add to schedule if fits within pacing constraints         │
│    5. Prioritize: parent → children → nearby cluster members    │
│    6. Insert lunch break around 12:00                           │
│    7. Stop when max_hours or max_activities reached             │
│                                                                 │
│  Smart naming:                                                  │
│    - Group activities by cluster_id                             │
│    - Name day after dominant cluster                            │
│    - Example: "Balboa Park Campus Area" not just "Balboa Park" │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  🗺️ DISPLAY ITINERARY (Plan 1)                                 │
│                                                                 │
│  === SAN DIEGO EXPLORER ===                                     │
│                                                                 │
│  Day 1: Exploring Balboa Park Campus                            │
│    [09:00] Balboa Park                                          │
│    [12:30] Air & Space Museum (within park)                     │
│    [14:00] Japanese Garden (within park)                        │
│    [16:00] Seaport Village (nearby)                             │
│                                                                 │
│  Day 2: Exploring Downtown & Waterfront Area                    │
│    [09:00] Gaslamp Quarter                                      │
│    [11:30] USS Midway Museum                                    │
│    [14:00] Embarcadero                                          │
│                                                                 │
│  Day 3: Exploring Coastal Parks Area                            │
│    [09:00] Old Town San Diego                                   │
│    [12:00] Cabrillo National Monument                           │
│    [15:00] Sunset Cliffs (same coastal route)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │ Show Other Places?│
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 │ YES                     │ NO (skip)
                 ↓                         ↓
    ┌──────────────────────────────┐      │
    │ 📍 FIND OTHER TOP PLACES     │      │
    │                              │      │
    │ 1. Extract place IDs from    │      │
    │    itinerary (Plan 1)        │      │
    │ 2. Filter out those places   │      │
    │ 3. Sort remaining by score   │      │
    │ 4. Take top 10               │      │
    └──────────────┬───────────────┘      │
                   ↓                       │
    ┌──────────────────────────────┐      │
    │ 📍 DISPLAY OTHER PLACES      │      │
    │                              │      │
    │ 1. SeaWorld San Diego        │      │
    │    ⭐ 4.4/5 (52,455 reviews) │      │
    │    📍 8.2 km from center     │      │
    │    🏷️ Amusement Park         │      │
    │                              │      │
    │ 2. USS Midway Museum         │      │
    │    ⭐ 4.7/5 (45,123 reviews) │      │
    │    📍 1.5 km from center     │      │
    │    🏷️ Museum                 │      │
    │                              │      │
    │ ... (up to 10 total)         │      │
    └──────────────┬───────────────┘      │
                   └──────────┬───────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │ Far Places Exist? │
                    │ (>50km away)      │
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 │ NO (skip)               │ YES
                 ↓                         ↓
                 │          ┌──────────────────────────────┐
                 │          │ 🧠 GENERATE ITINERARY        │
                 │          │    (Plan 2: With Day Trip)   │
                 │          │                              │
                 │          │ Day 2 becomes day trip to    │
                 │          │ far attraction (e.g., wine   │
                 │          │ country, beach town)         │
                 │          └──────────────┬───────────────┘
                 │                         ↓
                 │          ┌──────────────────────────────┐
                 │          │ 🗺️ DISPLAY ITINERARY        │
                 │          │    (Plan 2)                  │
                 │          │                              │
                 │          │ === SAN DIEGO & BEYOND ===   │
                 │          │                              │
                 │          │ Day 1: [same as Plan 1]      │
                 │          │ Day 2: Day Trip to Temecula  │
                 │          │ Day 3: [rest of city]        │
                 │          └──────────────┬───────────────┘
                 │                         ↓
                 │          ┌──────────────────────────────┐
                 │          │ 📍 DISPLAY OTHER PLACES      │
                 │          │    (for Plan 2)              │
                 │          │                              │
                 │          │ [Different list based on     │
                 │          │  Plan 2's itinerary]         │
                 │          └──────────────┬───────────────┘
                 └──────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ✅ COMPLETE - User has:                                        │
│  - Full itinerary (1-2 plans)                                   │
│  - Rankings table (optional)                                    │
│  - Other top places list (optional)                             │
│  - Smart routing (clustered)                                    │
│  - Realistic timing (pacing-aware)                              │
│  - No redundancy (nested places together)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components Explained

### 🔄 Auto-Fetch Data
- Triggered when JSON file doesn't exist
- Calls `subprocess.run([sys.executable, "main_engine.py", city_input])`
- Shows progress and errors clearly
- Verifies file creation after fetch

### 🧠 Spatial Clustering
- Groups attractions within 3km radius
- Uses DBSCAN algorithm
- Assigns `cluster_id` to each place
- Same cluster = visit on same day

### 🎯 Nested Detection
- Finds "parent" locations (parks, campuses)
- Identifies attractions within 500m
- Marks parent-child relationships
- Schedules together automatically

### 📊 Rankings Table
- Shows top 50 attractions
- Sorted by `rank_score` (0-1)
- Includes cluster IDs
- User can skip with 'n'

### 📍 Other Top Places
- Extracts used place IDs from itinerary
- Filters out those places
- Shows top 10 remaining
- Prevents duplicates

### 🗺️ Itinerary Generation
**Improved logic:**
1. **Cluster-aware** - Prefers same-cluster places
2. **Parent-child aware** - Museums follow their parks
3. **Time-constrained** - Respects max_hours per pacing
4. **Opening hours** - Only schedules when open
5. **Smart naming** - Names by dominant cluster

## Data Flow

```
JSON File → Load → Cluster → Detect Nesting → Generate Itinerary
                                                       ↓
                                              Extract Used Places
                                                       ↓
                                              Filter Remaining
                                                       ↓
                                              Show Top 10
```

## Error Handling

```
Try to load JSON
  ↓
File not found?
  ↓
Run main_engine.py
  ↓
Success? → Continue
  ↓
Failure? → Show error + troubleshooting
```

## Performance

```
Load JSON:        ~0.1s
Clustering:       ~1-2s  (O(n²) for n attractions)
Nesting:          ~1s    (O(n²) worst case)
Itinerary:        ~0.5s  (greedy algorithm)
Rankings:         ~0.1s  (sorting)
Other Places:     ~0.1s  (filtering)
─────────────────────────
Total:            ~3-5s for 200 attractions
```

## Memory Usage

```
Places JSON:      ~1-2 MB
Loaded data:      ~5-10 MB (in-memory)
Clustering:       ~1 MB (distance matrix)
Rankings table:   ~10 KB (string output)
─────────────────────────
Total:            ~10-15 MB per city
```

---

**This complete flow ensures users get intelligent, well-organized itineraries with full transparency about all available options!**
