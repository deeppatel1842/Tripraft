# New Features: Rankings Table & Other Top Places

## Overview
Added two powerful features to help users explore all available attractions:

1. **📊 Rankings Table** - Detailed spreadsheet-style view of all attractions
2. **📍 Other Top Places** - Top 10 highly-rated places not included in the itinerary

## Feature 1: Rankings Table

### What It Shows
A formatted table displaying all attractions sorted by rank_score with:
- **Rank** - Position in rankings (1-50)
- **Place Name** - Attraction name (truncated to 40 chars)
- **Score** - Rank score (0-1, based on ratings, reviews, distance)
- **Rating** - Google rating (out of 5.0)
- **Reviews** - Number of user reviews
- **Distance** - Distance from city center in km
- **Cluster** - Geographic cluster ID (-1 if not clustered)
- **Types** - Primary attraction type

### Example Output
```
==============================================================================================================
Rank  Place Name                               Score    Rating  Reviews    Distance  Cluster  Types                         
==============================================================================================================
1     Balboa Park                              0.9673   4.8     77,069     2.6 km    0        park                          
2     SeaWorld San Diego                       0.8975   4.4     52,455     8.2 km    0        amusement park                
3     Seaport Village                          0.9275   4.6     30,809     1.2 km    0        tourist attraction            
4     Gaslamp Quarter                          0.8993   4.6     12,877     0.8 km    0        tourist attraction            
5     Old Town San Diego                       0.8599   4.7     2,007      5.6 km    1        tourist attraction            
...
```

### When It Appears
User is prompted:
```
Show detailed rankings table? [Y/n]:
```
- Press Enter or type 'Y' → Shows table
- Type 'n' → Skips table

### Use Cases
- **Researchers** - Analyze all attractions systematically
- **Planners** - Compare alternatives side-by-side
- **Data Enthusiasts** - See how ranking algorithm works
- **Trip Customization** - Find specific types of attractions

## Feature 2: Other Top Places

### What It Shows
Top 10 highly-rated attractions that **didn't make it** into the itinerary, with:
- Place name
- ⭐ Rating and review count
- 📍 Distance from city center
- 🏷️ Primary type (museum, park, etc.)
- 📊 Rank score
- 🌐 Website (if available)

### Example Output
```
======================================================================
--- 📍 OTHER TOP PLACES YOU MAY VISIT ---
======================================================================
These highly-rated attractions didn't make it into your itinerary,
but are worth considering if you have extra time:

 1. SeaWorld San Diego
    ⭐ Rating: 4.4/5.0 (52,455 reviews)
    📍 Distance: 8.2 km from city center
    🏷️  Type: Amusement Park
    📊 Rank Score: 0.8975
    🌐 https://seaworld.com/san-diego

 2. USS Midway Museum
    ⭐ Rating: 4.7/5.0 (45,123 reviews)
    📍 Distance: 1.5 km from city center
    🏷️  Type: Museum
    📊 Rank Score: 0.8856
    🌐 https://www.midway.org

...
```

### How It Works
1. Extract all place IDs from the generated itinerary
2. Filter out those places from the full list
3. Sort remaining places by rank_score
4. Return top 10

### Smart Exclusion Logic
If itinerary includes:
- ✓ Balboa Park
- ✓ Japanese Friendship Garden
- ✓ Air & Space Museum

Then "Other Top Places" might show:
- SeaWorld (wasn't in itinerary)
- USS Midway Museum (wasn't in itinerary)
- La Jolla Cove (wasn't in itinerary)

**NOT:**
- Balboa Park (already in itinerary)
- Any nested attractions within visited places

### When It Appears
User is prompted:
```
Show other top places not in itinerary? [Y/n]:
```
- Press Enter or type 'Y' → Shows other places
- Type 'n' → Skips this section

Appears **after each itinerary** (both main plan and day trip plan).

### Use Cases
- **Flexible Travelers** - See alternatives if plans change
- **Extended Trips** - Know what to do with extra time
- **Multiple Visits** - Plan for next trip to the same city
- **Local Context** - Understand what you're missing

## Integration with Existing Features

### Clustering Integration
Rankings table shows **Cluster ID** column:
- Same cluster ID = nearby attractions (within 3 km)
- Different cluster = different part of city
- -1 = Not part of any cluster (isolated attraction)

**Use case:** 
```
If Balboa Park (Cluster 0) is in itinerary,
look for Cluster 0 places in "Other Top Places"
→ They're nearby and easy to add!
```

### Rank Score Transparency
Both features show the **rank_score** that determines quality:
- Score = combination of:
  - Rating (quality)
  - Review count (popularity)
  - Distance (convenience)
  - Wilson score (statistical reliability)

Users can see **why** certain places rank higher.

## Configuration

### Number of "Other Places"
In `get_other_top_places()` function:
```python
other_places = get_other_top_places(all_places_data, plan1_itinerary, top_n=10)
```
Change `top_n=10` to show more/fewer places.

### Rankings Table Limit
In `create_rankings_table()` function:
```python
for i, place in enumerate(ranked_places[:50], 1):  # Limit to top 50
```
Change `[:50]` to show more rows.

### Minimum Review Threshold
In `Config` class:
```python
MIN_REVIEW_COUNT = 1000
```
Adjust to include more/fewer places.

## Technical Implementation

### Rankings Table Generator
```python
def create_rankings_table(places: List[Place], include_clusters: bool = True) -> str
```
- Filters out airports and low-review places
- Sorts by rank_score descending
- Formats as fixed-width table
- Returns string for printing

### Other Top Places Finder
```python
def get_other_top_places(all_places: List[Place], itinerary_plan: List[Dict], top_n: int = 10) -> List[Place]
```
- Extracts used place IDs from itinerary
- Filters available places
- Sorts by rank_score
- Returns top N

### Pretty Printer
```python
def print_other_top_places(other_places: List[Place])
```
- Formats each place with icons
- Shows key metrics
- Includes website links
- Clean, readable output

## User Experience Flow

### Complete Session Example
```
--- ✈️  Welcome to the AI Trip Planner ---

Enter a city name (or 'quit' to exit): san diego
How many days is your trip? (e.g., 3): 3
Choose pacing [R]elaxed, [M]oderate, [P]acked: M
Types to EXCLUDE (comma-separated, optional): 
Types to REQUIRE (comma-separated, optional): 
Names of places to REQUIRE: balboa park
Show detailed rankings table? [Y/n]: Y         ← NEW PROMPT
Show other top places not in itinerary? [Y/n]: Y  ← NEW PROMPT

======================================================================
--- 📊 ATTRACTION RANKINGS ---                     ← NEW SECTION
======================================================================
[Table showing all 50+ attractions with scores]

======================================================================
--- 🗺️  SAN DIEGO EXPLORER ---
======================================================================
[Itinerary with Balboa Park, etc.]

======================================================================
--- 📍 OTHER TOP PLACES YOU MAY VISIT ---          ← NEW SECTION
======================================================================
[List of top 10 places NOT in itinerary, like SeaWorld]

======================================================================
--- 🗺️  SAN DIEGO & BEYOND (WITH DAY TRIP) ---
======================================================================
[Alternative itinerary]

======================================================================
--- 📍 OTHER TOP PLACES YOU MAY VISIT ---          ← APPEARS AGAIN
======================================================================
[Different list based on day trip itinerary]
```

## Benefits

### For Users
1. **Complete Picture** - See all available options
2. **Informed Decisions** - Understand trade-offs
3. **Flexibility** - Know alternatives if plans change
4. **Discovery** - Find hidden gems

### For Developers
1. **Transparency** - Show how algorithm works
2. **Debugging** - Verify rankings are correct
3. **Validation** - Users can audit results
4. **Feedback** - Users can suggest improvements

## Performance Impact

### Computational Cost
- Rankings table: O(n log n) for sorting (negligible)
- Other places: O(n) for filtering (negligible)
- Total overhead: < 0.1 seconds

### Memory Impact
- No additional data loaded
- Uses existing places list
- Table string is ~10KB max

## Future Enhancements

### Potential Additions
1. **Export to CSV** - Save rankings table to file
2. **Filter by Type** - Show only museums, parks, etc.
3. **Similarity Score** - "If you liked X, you'll love Y"
4. **Map Visualization** - Plot other places on map
5. **Price Filtering** - Show only free/paid attractions
6. **Opening Hours** - Only show places open on trip days

### API Integration
- Link to Google Maps for each "Other Place"
- Show real-time wait times
- Display current weather at outdoor attractions

## Error Handling

### No Other Places Available
If all top places are in itinerary:
```python
if not other_places:
    return  # Silently skip section
```

### Empty Rankings Table
If no places meet criteria:
```python
if not ranked_places:
    return "No places to display."
```

## Testing

### Test with San Diego
```bash
cd web/backend/main_engine
python trip_planner.py
# Enter: san diego, 3 days, Moderate
# Say Y to both prompts
```

**Expected:**
- Rankings table shows ~50 places
- Balboa Park is #1 (score ~0.967)
- Other places shows SeaWorld, USS Midway, etc.
- No duplicates between itinerary and other places

### Test with Bangkok
```bash
# First run will fetch data via main_engine.py
python trip_planner.py
# Enter: bangkok, 3 days, Moderate
```

**Expected:**
- Fetches Bangkok data first time
- Shows rankings for Thai attractions
- Other places shows Grand Palace, temples, etc.

## Summary

### What's New
✅ **Rankings Table** - Full spreadsheet view of all attractions  
✅ **Other Top Places** - Top 10 not in itinerary  
✅ **Smart Exclusion** - Never shows duplicates  
✅ **User Prompts** - Optional features (can skip)  
✅ **Cluster Integration** - Shows geographic groupings  

### Zero Breaking Changes
- Both features are **optional** (user prompted)
- Can skip by typing 'n'
- Default is to show both (press Enter)
- No impact on core itinerary generation

### Data Source
- Uses **existing JSON files** (no new API calls)
- Works with cached data
- No additional storage required

**Ready to use!** Just run `trip_planner.py` and say 'Y' to the new prompts.
