# Places UI Filters - Quick Reference

## Filter Controls

### 1. Sort By Dropdown
```
┌─────────────────────────┐
│ 🔽 Sort By              │
├─────────────────────────┤
│ ● Expert Ranking        │  ← Default, uses rank_score
│   Highest Rating        │  ← Sorts by Google rating
│   Most Reviews          │  ← Sorts by review count
└─────────────────────────┘
```

### 2. Distance Slider
```
📍 Distance: 50 km

10 km ├──────●──────────┤ 120 km
```
- **Purpose**: Filter places by distance from searched city
- **Range**: 10 km to 120 km
- **Uses**: `distance_to_query` field (not shown to users)
- **Display**: Shows "All" when at 120 km

### 3. Rating Slider
```
⭐ Min Rating: 4.0+

0 ├──────────●──────┤ 5
```
- **Purpose**: Show only places above minimum rating
- **Range**: 0 to 5 stars (0.5 step)
- **Display**: Shows "All" when at 0

### 4. Results Counter & Reset
```
┌─────────────────────────────┐
│ 🔍 45 of 60 places          │
├─────────────────────────────┤
│     ↻ Reset Filters         │
└─────────────────────────────┘
```

## Complete Filter Section

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         🎨 Purple Gradient Background                     ║
║                                                                           ║
║  ┌──────────────┐  ┌─────────────────────┐  ┌─────────────────────┐    ║
║  │ 🔽 Sort By   │  │ 📍 Distance: 50 km  │  │ ⭐ Min Rating: 4.0+ │    ║
║  │              │  │                     │  │                     │    ║
║  │ Expert       │  │ 10 ●──────── 120 km│  │ 0 ──────●───── 5   │    ║
║  │ Ranking  ▼   │  │                     │  │                     │    ║
║  └──────────────┘  └─────────────────────┘  └─────────────────────┘    ║
║                                                                           ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │ 🔍 45 of 60 places                                              │    ║
║  │ ┌─────────────────────────┐                                     │    ║
║  │ │   ↻ Reset Filters       │                                     │    ║
║  │ └─────────────────────────┘                                     │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

## Usage Examples

### Example 1: Default View
```
City: Pattaya
Sort: Expert Ranking
Distance: All (120 km)
Rating: All (0+)
Result: 60 places from Bangkok hub, sorted by rank_score
```

### Example 2: Nearby Top-Rated
```
City: Pattaya
Sort: Highest Rating
Distance: 30 km
Rating: 4.5+
Result: 12 places within 30 km, rated 4.5+, sorted by rating
```

### Example 3: Popular Destinations
```
City: Bangkok
Sort: Most Reviews
Distance: All (120 km)
Rating: 0 (All)
Result: 60 places sorted by review count (most popular first)
```

## Color Scheme

### Filter Section
- **Background**: Linear gradient purple (#667eea → #764ba2)
- **Accent**: Gold (#fbbf24) for icons and highlights
- **Text**: White with various opacity levels
- **Borders**: Semi-transparent white

### Interactive Elements
- **Dropdowns**: White background (#ffffff)
- **Sliders**: Gold thumb (#fbbf24) on white track
- **Buttons**: Frosted glass effect (backdrop-filter: blur)
- **Hover**: Slight scale and shadow increase

## Responsive Behavior

### Desktop (>768px)
```
┌─────────────────────────────────────────────────────────┐
│  [Sort ▼]    [Distance Slider]    [Rating Slider]       │
│                                                          │
│              [Results Counter]  [Reset Button]          │
└─────────────────────────────────────────────────────────┘
```

### Mobile (<768px)
```
┌───────────────────┐
│ Results Counter   │
│ Reset Button      │
├───────────────────┤
│ Sort Dropdown     │
├───────────────────┤
│ Distance Slider   │
│ (full width)      │
├───────────────────┤
│ Rating Slider     │
│ (full width)      │
└───────────────────┘
```

## Technical Details

### State Management
```javascript
// Filter States
const [sortBy, setSortBy] = useState('rank_score');
const [distanceFilter, setDistanceFilter] = useState(120);
const [minRating, setMinRating] = useState(0);

// Derived State
const [filteredPlaces, setFilteredPlaces] = useState([]);
```

### Filter Logic Flow
```
User changes filter
       ↓
useEffect triggers
       ↓
applyFiltersAndSort()
       ↓
1. Copy places array
2. Filter by distance
3. Filter by rating
4. Sort by selected criteria
       ↓
Update filteredPlaces
       ↓
UI re-renders with new results
```

### Data Fields Used
```javascript
place = {
  distance_to_query: 45.2,      // Used for distance filter
  rating: 4.6,                   // Used for rating filter
  userRatingCount: 15234,        // Used for review count sort
  rank_score: 0.87,              // Used for expert ranking sort
  // ... other fields
}
```

## Accessibility

### Keyboard Navigation
- ✅ All controls focusable via Tab
- ✅ Dropdowns operable with arrow keys
- ✅ Sliders adjustable with arrow keys
- ✅ Enter/Space activates buttons

### Screen Readers
- ✅ Labels properly associated with inputs
- ✅ Slider values announced
- ✅ Result count announced
- ✅ Icons have aria-hidden (decorative)

## Performance

### No API Calls
```
Filter change → Client-side computation → Update UI
    (~0ms)            (~10ms)              (~16ms)

Total: ~26ms (instant to user)
```

### Comparison (if API was used)
```
Filter change → API call → Wait → Parse → Update UI
    (~0ms)       (200-500ms)       (~10ms)  (~16ms)

Total: 226-526ms (noticeable delay)
```

## Quick Test Commands

### In Browser Console
```javascript
// Check current filtered places count
console.log(filteredPlaces.length);

// Check filter states
console.log({ sortBy, distanceFilter, minRating });

// Manually trigger filter
applyFiltersAndSort();

// Reset filters programmatically
setSortBy('rank_score');
setDistanceFilter(120);
setMinRating(0);
```

## Common Issues & Solutions

### Issue: Filters not working
**Check**: Is `distance_to_query` present in place data?
**Solution**: Ensure backend returns this field

### Issue: No results after filtering
**Check**: Are filter values too restrictive?
**Solution**: Click "Reset Filters" or adjust values

### Issue: Sort not changing order
**Check**: Do places have the field being sorted?
**Solution**: Add fallback values (|| 0) in sort logic

### Issue: Mobile sliders hard to use
**Check**: Thumb size too small?
**Solution**: Already set to 20px (good touch target)

## Summary

The filter system provides:
- ✅ **3 sort options** (Expert, Rating, Reviews)
- ✅ **Distance filter** (10-120 km range)
- ✅ **Rating filter** (0-5 stars)
- ✅ **Real-time updates** (no API calls)
- ✅ **Visual feedback** (counters, animations)
- ✅ **Easy reset** (one-click default)
- ✅ **Mobile friendly** (responsive design)
- ✅ **Fast performance** (client-side only)

Perfect for users who want to customize their place discovery experience!
