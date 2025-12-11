# Phase 3: Intelligent Search Service - Quick Reference

## Service Overview

Professional service layer for intelligent query detection and unified search.

## Core Classes

### IntelligentSearchService

```python
from services.intelligent_search import IntelligentSearchService

# Initialize
service = IntelligentSearchService(data_store=aggregated_data)

# Intelligent search with automatic type detection
result = service.intelligent_search('Paris')
result.query_type  # QueryType.CITY
result.display_mode  # 'top_destinations'

# Search with type override
result = service.intelligent_search('Paris', type_override='city')

# Autocomplete
autocomplete = service.autocomplete('par', limit=10)
```

### QueryNormalizer

```python
from services.intelligent_search import QueryNormalizer

normalizer = QueryNormalizer()

# Normalize query
normalized = normalizer.normalize('New York!!')  # 'new york'

# Convert to slug
slug = normalizer.to_slug('Eiffel Tower')  # 'eiffel-tower'
```

### QueryDetector

```python
from services.intelligent_search import QueryDetector, QueryType

detector = QueryDetector(data_store=data)

# Detect query type
query_type, match_id = detector.detect_type('Paris')
# (QueryType.CITY, 'paris')

# Check if types match
if query_type == QueryType.COUNTRY:
    print("Country search")
```

## Response Objects

### SearchResult

```python
@dataclass
class SearchResult:
    success: bool              # Operation succeeded
    query: str                 # Original query
    query_type: QueryType      # Detected type
    display_mode: str          # How to display results
    match_id: Optional[str]    # Matched location ID
    match_name: Optional[str]  # Matched location name
    location_hierarchy: Dict   # Country/State/City path
    places: List[Dict]         # List of places
    sections: Optional[List]   # Grouped results (countries)
    firestore_reads: int       # API calls made
    response_time_ms: float    # Execution time
    cache_hit: bool           # Was result cached
    error: Optional[str]      # Error message

# Convert to JSON
result_dict = result.to_dict()
```

### AutocompleteResult

```python
@dataclass
class AutocompleteResult:
    success: bool              # Operation succeeded
    query: str                 # Search prefix
    suggestions: List[Dict]    # Suggested locations
    firestore_reads: int       # API calls made
    response_time_ms: float    # Execution time
    cache_hit: bool           # Was result cached
    error: Optional[str]      # Error message

# Convert to JSON
result_dict = result.to_dict()
```

## Query Types

```python
from services.intelligent_search import QueryType

QueryType.COUNTRY    # Searching for countries
QueryType.STATE      # Searching for states/regions
QueryType.CITY       # Searching for cities
QueryType.PLACE      # Searching for attractions
QueryType.UNKNOWN    # Type couldn't be determined
```

## Display Modes

```
country_sections   # Country with all states and places
top_destinations   # State/City with top-ranked places
single_place       # Detailed view of single attraction
error              # Error response
```

## Common Usage Patterns

### Search by Country

```python
result = service.intelligent_search('France')
# result.query_type = QueryType.COUNTRY
# result.display_mode = 'country_sections'
# result.sections = [state1, state2, ...]
# result.places = all places in France
```

### Search by City

```python
result = service.intelligent_search('Paris')
# result.query_type = QueryType.CITY
# result.display_mode = 'top_destinations'
# result.places = top 20 places in Paris
# result.location_hierarchy = {country, state, city}
```

### Search by Attraction

```python
result = service.intelligent_search('Eiffel Tower')
# result.query_type = QueryType.PLACE
# result.display_mode = 'single_place'
# result.places = [eiffel_tower_data]
```

### Autocomplete

```python
result = service.autocomplete('par', limit=5)
# result.suggestions = [
#     {'name': 'Paris', 'type': 'city', 'rank': 0.95},
#     {'name': 'Paris, Texas', 'type': 'city', 'rank': 0.7},
#     ...
# ]
```

### Error Handling

```python
result = service.intelligent_search('')
if not result.success:
    print(f"Error: {result.error}")
    # "Query cannot be empty"

result = service.intelligent_search('Unknown Place')
if not result.success:
    print(f"Error: {result.error}")
    # "No results found for 'Unknown Place'"
```

## Testing

```bash
# Run all Phase 3 tests
pytest tests/test_phase3_intelligent_search.py -v

# Run specific test class
pytest tests/test_phase3_intelligent_search.py::TestIntelligentSearchService -v

# Run with coverage
pytest tests/test_phase3_intelligent_search.py --cov=services.intelligent_search
```

## Test Classes

- `TestQueryNormalizer` - 8 tests for text normalization
- `TestQueryDetector` - 10 tests for type detection
- `TestSearchResult` - 4 tests for response object
- `TestIntelligentSearchService` - 15 tests for main service
- `TestAutocomplete` - 8 tests for autocomplete
- `TestIntegration` - 5 tests for workflows

**Total: 50 tests, 100% passing**

## Performance Metrics

All responses include:
- `response_time_ms` - Query execution time
- `firestore_reads` - Number of database calls
- `cache_hit` - Whether result was cached

**Target performance:**
- Search: < 100ms
- Autocomplete: < 50ms
- Firestore reads: 1 per search

## Error Messages

```
"Query cannot be empty"
"Query too short"
"Invalid type override: {type}"
"No results found for '{query}'"
"Search error: {details}"
"Autocomplete error: {details}"
```

## Imports

```python
from services.intelligent_search import (
    IntelligentSearchService,
    QueryType,
    SearchResult,
    AutocompleteResult,
    QueryNormalizer,
    QueryDetector,
)
```

## Data Store Format

```python
data_store = {
    'countries': [
        {
            'id': 'country-slug',
            'name': 'Country Name',
            'states': [...]  # State objects with top_places
        }
    ],
    'states': [
        {
            'id': 'state-slug',
            'name': 'State Name',
            'country_name': 'Country Name',
            'top_places': [...]  # Place objects
        }
    ],
    'cities': [
        {
            'id': 'city-slug',
            'name': 'City Name',
            'country_name': 'Country Name',
            'state_name': 'State Name',
            'top_places': [...]  # Place objects
        }
    ],
    'places': [
        {
            'id': 'place-slug',
            'name': 'Place Name',
            'city': 'City Name',
            'state': 'State Name',
            'country': 'Country Name',
            'coordinates': {'lat': 0.0, 'lng': 0.0},
            # ... other place fields
        }
    ],
    'search_index': {
        'prefix': {
            'prefix': 'pre',
            'suggestions': [
                {'name': 'Place', 'id': 'place-id', 'type': 'place', 'rank': 0.9}
            ]
        }
    }
}
```

## Configuration

All settings through `PlacesEngineConfig`:
- Data store location
- Cache backend (Redis)
- Logging level
- Performance thresholds

## Status

✅ Phase 3 Complete
- 850+ lines of production code
- 50 comprehensive tests
- 100% test passing rate
- Professional error handling
- Performance tracking
- Zero hardcoding
