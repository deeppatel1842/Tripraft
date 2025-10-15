import os
import re
import json
import math
import copy
import logging
import unicodedata
import subprocess
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Set
from collections import Counter, defaultdict

# =============================================================================
# INITIALIZATION & LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================
class Location(TypedDict):
    latitude: float
    longitude: float

class DisplayName(TypedDict):
    text: str
    languageCode: str

class Place(TypedDict, total=False):
    id: str
    location: Location
    displayName: DisplayName
    types: List[str]
    rating: float
    userRatingCount: int
    regularOpeningHours: Dict
    routingSummary: Dict
    rank_score: float
    distance_to_query: float
    websiteUri: str

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================
class Config:
    # Database folder is outside main_engine
    BASE_DIR = Path(__file__).parent.parent  # Go up to backend/
    DB_DIR = BASE_DIR / "database" / "adaptive_database"
    GEOCODE_DIR = BASE_DIR / "database" / "geocode_database"
    HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
    GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
    TRIP_DATABASE_DIR = BASE_DIR / "database" / "trip_database"  # Save trip plans here
    MIN_REVIEW_COUNT = 1000

PACING_OPTIONS = {
    "R": {"name": "Relaxed", "start_hour": 10, "end_hour": 17, "max_activities": 3, "max_hours": 6},
    "M": {"name": "Moderate", "start_hour": 9, "end_hour": 17, "max_activities": 4, "max_hours": 7},
    "P": {"name": "Packed", "start_hour": 8, "end_hour": 20, "max_activities": 5, "max_hours": 10}
}

# Distance thresholds for filtering attractions
CITY_RADIUS_KM = 30.0  # Max distance for city attractions
DAY_TRIP_MIN_KM = 40.0  # Min distance to qualify as day trip
DAY_TRIP_MAX_KM = 120.0  # Max distance for day trips

# --- Ensure Dirs Exist ---
for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.HUB_ATTRACTIONS_DIR, Config.TRIP_DATABASE_DIR]:
    path.mkdir(exist_ok=True)

# =============================================================================
# --- HELPER FUNCTIONS ---
# =============================================================================
def normalize_city_name(s: str, for_filename: bool = False) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if for_filename:
        return s.replace(" ", "_")
    return s

### --- Smart Travel Time Estimation Functions --- ###

def haversine_distance_meters(loc1: Location, loc2: Location) -> float:
    R = 6371000  # Radius of Earth in meters
    lat1, lon1 = math.radians(loc1['latitude']), math.radians(loc1['longitude'])
    lat2, lon2 = math.radians(loc2['latitude']), math.radians(loc2['longitude'])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_average_speed_mps(place_data: Place) -> float:
    try:
        summary = place_data["routingSummary"]["legs"][0]
        distance_m = summary["distanceMeters"]
        duration_s = int(summary["duration"].replace('s', ''))
        return distance_m / duration_s if duration_s > 0 else 8.3
    except (KeyError, IndexError, ValueError):
        return 8.3  # Fallback to ~30 km/h

def estimate_travel_time_between_places(place_a: Place, place_b: Place) -> int:
    """
    Estimate travel time with traffic buffer (1.5x multiplier for realistic urban traffic).
    """
    speed_a_mps = get_average_speed_mps(place_a)
    speed_b_mps = get_average_speed_mps(place_b)
    average_speed_mps = (speed_a_mps + speed_b_mps) / 2
    distance_between_m = haversine_distance_meters(place_a['location'], place_b['location'])
    
    # GLOBAL FIX: 1.5x traffic buffer (Bangkok, NYC, Paris, etc. all have traffic)
    estimated_seconds = (distance_between_m * 1.5) / average_speed_mps
    return math.ceil(estimated_seconds / 60)

### --- Intelligent Visit Duration & Robust Opening Hours Functions --- ###

def calculate_visit_duration(place_data: Place) -> int:
    """Calculate realistic visit duration based on place type and popularity."""
    base_duration = 60
    types = place_data.get('types', [])
    rating_count = place_data.get('userRatingCount', 0)
    name = place_data.get('displayName', {}).get('text', '').lower()
    
    # Adjust base duration by type
    if any(t in types for t in ["amusement_park", "zoo"]): 
        base_duration = 240
    elif any(t in types for t in ["national_park"]): 
        base_duration = 180
    elif any(t in types for t in ["museum", "art_gallery", "aquarium"]): 
        base_duration = 120
    elif any(t in types for t in ["tourist_attraction", "historical_landmark"]): 
        base_duration = 90
    elif "park" in types: 
        base_duration = 60
    elif any(t in types for t in ["market", "shopping_mall"]): 
        base_duration = 90
    elif any(t in types for t in ["place_of_worship", "church", "temple", "mosque", "shrine"]): 
        base_duration = 45
    
    # GLOBAL FIX: Open spaces should be brief stops (walk through, not destination)
    open_space_keywords = ['field', 'square', 'plaza', 'lawn', 'green', 'common', 'esplanade', 'luang', 'piazza', 'promenade']
    if any(keyword in name for keyword in open_space_keywords):
        base_duration = 30  # Reduced from 60 to 30 minutes
    
    # Adjust by popularity (more popular = spend more time)
    if rating_count > 50000: 
        base_duration += 30
    elif rating_count > 10000: 
        base_duration += 15
    
    return base_duration

def parse_opening_hours_robust(place: Place) -> Dict[int, List[Tuple[time, time]]]:
    """
    Calculates the MOST COMMON opening and closing times to create a "typical day"
    schedule, making the planner robust against missing or incorrect daily data.
    """
    if not place.get('regularOpeningHours') or not place['regularOpeningHours'].get('periods'):
        # Fallback for places with no hours data at all (e.g., parks, beaches)
        always_open = [(time.min, time.max)]
        return {i: always_open for i in range(7)}

    open_times = []
    close_times = []

    # Collect all opening and closing times from the weekly schedule
    for period in place['regularOpeningHours']['periods']:
        try:
            # We only care about the time, not the day, for calculating the average
            if 'open' in period and 'hour' in period['open'] and 'minute' in period['open']:
                 open_times.append((period['open']['hour'], period['open']['minute']))
            if 'close' in period and 'hour' in period['close'] and 'minute' in period['close']:
                 close_times.append((period['close']['hour'], period['close']['minute']))
        except KeyError:
            continue

    if not open_times or not close_times:
        always_open = [(time.min, time.max)]
        return {i: always_open for i in range(7)}

    # Find the most common (mode) open and close time
    most_common_open_tuple = Counter(open_times).most_common(1)[0][0]
    most_common_close_tuple = Counter(close_times).most_common(1)[0][0]

    # Create time objects from the most common times
    typical_open_time = time(most_common_open_tuple[0], most_common_open_tuple[1])
    typical_close_time = time(most_common_close_tuple[0], most_common_close_tuple[1])

    typical_hours = [(typical_open_time, typical_close_time)]

    # Return a schedule where every day has these "typical" hours
    return {i: typical_hours for i in range(7)}


def is_open(arrival_time: datetime, visit_duration_mins: int, daily_hours: List[Tuple[time, time]]) -> bool:
    if not daily_hours:
        return False
    departure_time = (arrival_time + timedelta(minutes=visit_duration_mins)).time()
    arrival_t = arrival_time.time()
    for open_period in daily_hours:
        open_time, close_time = open_period
        # Handle overnight case where close_time is smaller than open_time (e.g. 22:00-02:00)
        if open_time > close_time:
            if arrival_t >= open_time or departure_time <= close_time:
                return True
        else: # Standard day case
            if arrival_t >= open_time and departure_time <= close_time:
                return True
    return False

def geocode_city_locally(city_name: str) -> Optional[Dict[str, float]]:
    city_key = normalize_city_name(city_name)
    try:
        with sqlite3.connect(Config.GEOCODE_DB_FILE) as conn:
            row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
        return {"latitude": row[0], "longitude": row[1]} if row else None
    except sqlite3.Error as e:
        logging.error(f"Database error fetching geocode for '{city_key}': {e}")
        return None

def find_nearest_airport(places: List[Place], city_coords: Dict[str, float]) -> Optional[Place]:
    """Find the nearest airport to the city center."""
    airports = [p for p in places if 'airport' in p.get('types', [])]
    if not airports:
        return None
    
    # Sort by distance to city center
    airports_with_distance = []
    for airport in airports:
        distance = haversine_km(
            city_coords['latitude'], city_coords['longitude'],
            airport['location']['latitude'], airport['location']['longitude']
        )
        airports_with_distance.append((airport, distance))
    
    # Return nearest airport
    airports_with_distance.sort(key=lambda x: x[1])
    return airports_with_distance[0][0] if airports_with_distance else None

def find_special_time_places(places: List[Place]) -> Dict[str, List[Place]]:
    """
    Find places suitable for special times of day:
    - Early morning (sunrise spots, parks)
    - Late night (night views, rooftops, bars)
    """
    special_places = {
        "early_morning": [],  # Sunrise, parks, temples
        "late_night": []      # Night views, rooftops, bars
    }
    
    early_morning_keywords = ['sunrise', 'morning', 'dawn', 'temple', 'park', 'garden', 'observatory']
    late_night_keywords = ['sunset', 'night', 'view', 'rooftop', 'bar', 'tower', 'skyline', 'observation']
    late_night_types = ['bar', 'night_club', 'tourist_attraction']
    
    for place in places:
        name = place.get('displayName', {}).get('text', '').lower()
        types = place.get('types', [])
        rating = place.get('rating', 0)
        reviews = place.get('userRatingCount', 0)
        
        # Skip low-rated or unpopular places
        if rating < 4.2 or reviews < 1000:
            continue
        
        # Early morning places (sunrise, temples, parks)
        if any(kw in name for kw in early_morning_keywords) or 'park' in types or 'place_of_worship' in types:
            if place.get('distance_to_query', 0) <= CITY_RADIUS_KM:
                special_places['early_morning'].append(place)
        
        # Late night places (views, rooftops, bars)
        if any(kw in name for kw in late_night_keywords) or any(t in types for t in late_night_types):
            if place.get('distance_to_query', 0) <= CITY_RADIUS_KM:
                special_places['late_night'].append(place)
    
    # Sort by rank score and limit to top 3
    special_places['early_morning'] = sorted(
        special_places['early_morning'], 
        key=lambda p: p.get('rank_score', 0), 
        reverse=True
    )[:3]
    
    special_places['late_night'] = sorted(
        special_places['late_night'], 
        key=lambda p: p.get('rank_score', 0), 
        reverse=True
    )[:3]
    
    return special_places

# =============================================================================
# --- CLUSTERING & SPATIAL ANALYSIS ---
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two coordinates."""
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

def detect_nested_attractions(places: List[Place]) -> Dict[str, List[str]]:
    """
    Detect when attractions are nested within each other (e.g., Temple inside Palace, Museums inside Parks).
    Works globally by analyzing proximity + name similarity + type relationships + popularity.
    Returns a dict mapping parent_id -> [child_id1, child_id2, ...]
    
    Key principle: The more popular/larger venue is usually the parent.
    """
    nested_relationships = defaultdict(list)
    NESTING_DISTANCE_KM = 0.35  # Very close proximity = likely same complex
    
    # Universal parent types (large venues that contain smaller attractions)
    parent_types = {
        'palace', 'historical_landmark', 'cultural_landmark',
        'park', 'national_park', 'amusement_park', 'zoo', 'aquarium',
        'shopping_mall', 'museum', 'art_gallery', 'university',
        'stadium', 'airport', 'tourist_attraction', 'establishment'
    }
    
    # Universal child types (specific attractions within larger complexes)
    child_types = {
        'place_of_worship', 'church', 'temple', 'shrine', 'mosque',
        'restaurant', 'store', 'cafe', 'art_gallery', 'museum'
    }
    
    # Keywords that indicate a parent venue
    parent_keywords = {
        'palace', 'complex', 'center', 'campus', 'plaza', 'square',
        'district', 'village', 'mall', 'park', 'gardens'
    }
    
    # Build proximity matrix and check relationships
    for i, parent_candidate in enumerate(places):
        parent_name = parent_candidate.get('displayName', {}).get('text', '').lower()
        parent_place_types = set(parent_candidate.get('types', []))
        parent_rating_count = parent_candidate.get('userRatingCount', 0)
        
        # Check if this looks like a parent
        has_parent_type = bool(parent_types & parent_place_types)
        has_parent_keyword = any(kw in parent_name for kw in parent_keywords)
        
        # Skip if clearly not a parent (unless extremely popular)
        if not has_parent_type and not has_parent_keyword and parent_rating_count < 20000:
            continue
            
        parent_loc = parent_candidate['location']
        
        for j, child_candidate in enumerate(places):
            if i == j:
                continue
                
            child_name = child_candidate.get('displayName', {}).get('text', '').lower()
            child_place_types = set(child_candidate.get('types', []))
            child_rating_count = child_candidate.get('userRatingCount', 0)
            child_loc = child_candidate['location']
            
            # Calculate distance
            distance_km = haversine_km(
                parent_loc['latitude'], parent_loc['longitude'],
                child_loc['latitude'], child_loc['longitude']
            )
            
            # Skip if too far apart
            if distance_km > NESTING_DISTANCE_KM:
                continue
            
            # Check various nesting indicators
            is_nested = False
            
            # 1. CRITICAL: Parent must be more popular OR have parent keywords/types
            #    (Grand Palace 72K reviews > Temple 40K reviews = Palace is parent)
            if distance_km < NESTING_DISTANCE_KM:
                # Parent has significantly more reviews = likely the container
                if parent_rating_count > child_rating_count * 1.3:
                    # And child has a "child type" (temple, museum, etc.)
                    if child_types & child_place_types:
                        is_nested = True
                
                # Or child name contains parent name (explicit relationship)
                stopwords = {'the', 'of', 'a', 'an', 'and', 'or', 'in', 'at', 'to', 'for', 'within'}
                parent_words = {w for w in parent_name.split() if w not in stopwords and len(w) > 3}
                child_words = {w for w in child_name.split() if w not in stopwords and len(w) > 3}
                
                if parent_words & child_words and distance_km < 0.3:
                    is_nested = True
                
                # Or parent has strong parent indicators + child is close
                if (has_parent_keyword or 'historical_landmark' in parent_place_types or 'cultural_landmark' in parent_place_types):
                    if distance_km < 0.25 and (child_types & child_place_types):
                        is_nested = True
            
            if is_nested:
                nested_relationships[parent_candidate['id']].append(child_candidate['id'])
    
    return dict(nested_relationships)

def simple_clustering(places: List[Place], eps_km: float = 3.0, min_samples: int = 2) -> Dict[str, int]:
    """
    Simple DBSCAN-style clustering of places by proximity.
    Returns a dict mapping place_id -> cluster_id.
    """
    if not places:
        return {}
    
    # Build distance matrix
    n = len(places)
    visited = [False] * n
    cluster_assignments = {}
    cluster_id = 0
    
    def get_neighbors(idx: int) -> List[int]:
        """Get all places within eps_km of place at idx."""
        neighbors = []
        loc1 = places[idx]['location']
        for j in range(n):
            if idx == j:
                continue
            loc2 = places[j]['location']
            dist = haversine_km(
                loc1['latitude'], loc1['longitude'],
                loc2['latitude'], loc2['longitude']
            )
            if dist <= eps_km:
                neighbors.append(j)
        return neighbors
    
    def expand_cluster(idx: int, neighbors: List[int], cluster_id: int):
        """Expand cluster from seed point."""
        cluster_assignments[places[idx]['id']] = cluster_id
        
        i = 0
        while i < len(neighbors):
            neighbor_idx = neighbors[i]
            
            if not visited[neighbor_idx]:
                visited[neighbor_idx] = True
                new_neighbors = get_neighbors(neighbor_idx)
                
                if len(new_neighbors) >= min_samples:
                    neighbors.extend([n for n in new_neighbors if n not in neighbors])
            
            if places[neighbor_idx]['id'] not in cluster_assignments:
                cluster_assignments[places[neighbor_idx]['id']] = cluster_id
            
            i += 1
    
    # DBSCAN algorithm
    for i in range(n):
        if visited[i]:
            continue
            
        visited[i] = True
        neighbors = get_neighbors(i)
        
        if len(neighbors) < min_samples:
            # Noise point - assign to its own cluster
            cluster_assignments[places[i]['id']] = -1
        else:
            expand_cluster(i, neighbors, cluster_id)
            cluster_id += 1
    
    return cluster_assignments

def get_cluster_name(places_in_cluster: List[Place]) -> str:
    """
    Generate a meaningful name for a cluster based on its attractions.
    """
    if not places_in_cluster:
        return "Unknown Area"
    
    # Extract keywords from place names
    name_words = []
    for place in places_in_cluster:
        name = place.get('displayName', {}).get('text', '')
        # Remove common words
        words = [w for w in name.split() if w.lower() not in ['the', 'and', 'of', 'a', 'an']]
        name_words.extend(words)
    
    # Find most common significant words
    if name_words:
        word_counts = Counter(name_words)
        # Get the most common word that appears in multiple places
        common_words = [word for word, count in word_counts.most_common(5) if count >= 2]
        
        if common_words:
            return f"{common_words[0]} Area"
    
    # Fallback: use the highest-rated place name
    best_place = max(places_in_cluster, key=lambda p: p.get('rank_score', 0))
    return f"{best_place.get('displayName', {}).get('text', 'Unknown')} Area"

# =============================================================================
# --- ITINERARY PLANNER ---
# =============================================================================
def create_final_itinerary(
    places: List[Place], num_days: int, pacing: str, city_coords: Dict[str, float],
    city_name: str, exclude_types: List[str] = [],
    require_types: List[str] = [], force_city_only: bool = False,
    require_names: List[str] = []
) -> List[Dict]:
    # Filter candidate pool - START WITH DISTANCE FILTERING
    candidate_pool_all = [
        p for p in places 
        if 'airport' not in p.get('types', []) 
        and p.get('userRatingCount', 0) >= Config.MIN_REVIEW_COUNT 
        and p.get('location')
        and p.get('distance_to_query', 0) <= DAY_TRIP_MAX_KM  # Max 120km radius
    ]
    
    # Detect nested attractions GLOBALLY (works for all cities)
    nested_map = detect_nested_attractions(candidate_pool_all)
    
    # Remove children from main pool if parent exists (schedule them together)
    children_ids = set()
    for parent_id, children in nested_map.items():
        children_ids.update(children)
    
    # Filter out standalone children (they'll be added when parent is scheduled)
    candidate_pool = [
        p for p in candidate_pool_all 
        if p['id'] not in children_ids or p['id'] in nested_map  # Keep if parent or not a child
    ]
    
    # Perform spatial clustering
    cluster_assignments = simple_clustering(candidate_pool, eps_km=3.0, min_samples=2)
    
    # Add cluster info to each place
    for place in candidate_pool:
        place['cluster_id'] = cluster_assignments.get(place['id'], -1)
        place['is_parent'] = place['id'] in nested_map
        place['parent_id'] = None
    
    place_pool, used_ids = [], set()

    # 1. Prioritize specific required names - THIS IS THE HIGHEST PRIORITY
    if require_names:
        forced_places = []
        for name_to_force in require_names:
            for place in candidate_pool:
                normalized_display_name = normalize_city_name(place.get('displayName', {}).get('text', ''))
                if name_to_force in normalized_display_name and place['id'] not in used_ids:
                    forced_places.append(place)
                    used_ids.add(place['id'])
                    
                    # If this is a parent, mark children as used (they'll be scheduled together)
                    if place['id'] in nested_map:
                        for child_id in nested_map[place['id']]:
                            used_ids.add(child_id)
                    break
        place_pool.extend(sorted(forced_places, key=lambda p: p.get('rank_score', 0), reverse=True))

    # 2. Prioritize required types
    if require_types:
        required_places = sorted([p for p in candidate_pool if any(req_type in p.get('types', []) for req_type in require_types)], key=lambda p: p.get('rank_score', 0), reverse=True)
        for p in required_places:
            if p['id'] not in used_ids:
                place_pool.append(p)
                used_ids.add(p['id'])
                # Mark children as used
                if p['id'] in nested_map:
                    for child_id in nested_map[p['id']]:
                        used_ids.add(child_id)

    # 3. Add remaining places from the candidate pool
    for p in sorted(candidate_pool, key=lambda p: p.get('rank_score', 0), reverse=True):
        if p['id'] not in used_ids:
            place_pool.append(p)
            # Mark children as used
            if p['id'] in nested_map:
                for child_id in nested_map[p['id']]:
                    used_ids.add(child_id)

    # Split by distance: city attractions vs day trip candidates
    near_places = [p for p in place_pool if p.get('distance_to_query', 0) <= CITY_RADIUS_KM]
    far_places = sorted(
        [p for p in place_pool if DAY_TRIP_MIN_KM <= p.get('distance_to_query', 0) <= DAY_TRIP_MAX_KM], 
        key=lambda p: p.get('rank_score', 0), 
        reverse=True
    )
    itinerary_plan, start_date = [], datetime.now()
    city_center_as_place: Place = {'id': 'city_center', 'location': city_coords, 'displayName': {'text': 'City Center'}, 'routingSummary': {'legs': [{'distanceMeters': 0, 'duration': '0s'}]}}

    for day_num in range(1, num_days + 1):
        pacing_info = PACING_OPTIONS[pacing]
        daily_activities = []
        last_place_obj = city_center_as_place
        is_day_trip = (day_num == 2 and num_days >= 3 and far_places and not force_city_only)
        current_day = start_date + timedelta(days=day_num - 1)
        theme = ""
        day_start_time = current_day.replace(hour=pacing_info["start_hour"], minute=0)
        day_max_hours = pacing_info["max_hours"]
        
        if is_day_trip:
            # Select day trip seed (furthest high-rated place)
            day_seed = far_places.pop(0)
            day_seed_name = day_seed['displayName']['text']
            day_seed_distance = day_seed.get('distance_to_query', 0)
            
            # Build day trip pool: places near the seed location (within 20km of seed)
            day_candidate_pool = []
            seed_loc = day_seed['location']
            
            for place in far_places[:]:  # Check remaining far places
                dist_to_seed = haversine_km(
                    seed_loc['latitude'], seed_loc['longitude'],
                    place['location']['latitude'], place['location']['longitude']
                )
                if dist_to_seed <= 20:  # Within 20km of day trip destination
                    day_candidate_pool.append(place)
                    far_places.remove(place)
            
            # Add the seed itself
            day_candidate_pool.insert(0, day_seed)
            
            # GLOBAL FIX: Better day trip titles using area/region names
            # Extract area name (e.g., "Pattaya" from "Sanctuary of Truth Museum")
            # Look for common area descriptors in nearby place names
            area_name = None
            area_keywords = []
            for p in day_candidate_pool[:5]:  # Check first 5 places for common location
                place_name = p.get('displayName', {}).get('text', '')
                # Extract capitalized words (likely place names)
                words = [w for w in place_name.split() if w and w[0].isupper() and len(w) > 3]
                area_keywords.extend(words)
            
            # Find most common area name
            if area_keywords:
                from collections import Counter
                most_common = Counter(area_keywords).most_common(1)
                if most_common:
                    area_name = most_common[0][0]
            
            # Fallback: use distance-based description
            if not area_name or area_name.lower() in day_seed_name.lower():
                if day_seed_distance < 60:
                    area_descriptor = "Nearby"
                elif day_seed_distance < 90:
                    area_descriptor = "Coastal"
                else:
                    area_descriptor = "Regional"
                area_name = f"{area_descriptor} Area"
            
            theme = f"Day Trip to {area_name}"
            
            # GLOBAL FIX: Earlier start for day trips (7 AM) to maximize time
            early_start = current_day.replace(hour=7, minute=0)
            travel_time_to_destination = math.ceil(day_seed_distance * 1.5)  # 1.5 min/km with traffic
            current_time = early_start + timedelta(minutes=travel_time_to_destination)
            day_end_time = current_time + timedelta(hours=day_max_hours + 2)  # Extra 2 hours for day trips
        else:
            theme = f"{city_name.title()} Exploration"
            current_time = day_start_time
            day_end_time = day_start_time + timedelta(hours=day_max_hours)
            day_candidate_pool = near_places
        
        # Track which clusters we've visited today to group attractions better
        visited_clusters_today = set()
        current_cluster = None
        
        lunch_taken = False
        while current_time < day_end_time and len(daily_activities) < pacing_info["max_activities"] and day_candidate_pool:
            if not lunch_taken and current_time.hour >= 12 and daily_activities:
                current_time += timedelta(minutes=60); lunch_taken = True; continue

            # Prefer places in the same cluster as current location
            def get_place_priority(p: Place) -> float:
                base_score = p.get('rank_score', 0)
                travel_time = estimate_travel_time_between_places(last_place_obj, p)
                travel_penalty = travel_time * 0.01
                
                # Bonus for same cluster
                cluster_bonus = 0.0
                if current_cluster is not None and p.get('cluster_id') == current_cluster:
                    cluster_bonus = 0.3
                elif p.get('cluster_id') in visited_clusters_today:
                    cluster_bonus = 0.1
                
                # Major bonus for parent locations (schedule parent + all children together)
                if p.get('is_parent'):
                    cluster_bonus += 0.4
                
                return base_score + cluster_bonus - travel_penalty
            
            day_candidate_pool.sort(key=get_place_priority, reverse=True)
            
            best_place_found = None
            best_place_hours = []
            candidate_hours = {p['id']: parse_opening_hours_robust(p) for p in day_candidate_pool}
            
            for i, place in enumerate(day_candidate_pool):
                visit_duration = calculate_visit_duration(place)
                
                # If this is a parent with nested children, add extra time for children
                children_to_visit = []
                if place['id'] in nested_map:
                    for child_id in nested_map[place['id']]:
                        child_place = next((p for p in candidate_pool_all if p['id'] == child_id), None)
                        if child_place:
                            children_to_visit.append(child_place)
                            visit_duration += calculate_visit_duration(child_place) // 2  # Half time for nested attractions
                
                travel_time = estimate_travel_time_between_places(last_place_obj, place)
                arrival_time = current_time + timedelta(minutes=travel_time)
                hours_for_arrival_day = candidate_hours[place['id']].get(arrival_time.weekday(), [])
                
                if hours_for_arrival_day and is_open(arrival_time, visit_duration, hours_for_arrival_day) and (arrival_time + timedelta(minutes=visit_duration)) <= day_end_time:
                    best_place_found = day_candidate_pool.pop(i)
                    best_place_hours = hours_for_arrival_day
                    break
            
            if best_place_found:
                travel_time = estimate_travel_time_between_places(last_place_obj, best_place_found)
                visit_duration = calculate_visit_duration(best_place_found)
                current_time += timedelta(minutes=travel_time)
                
                # GLOBAL FIX: Add lunch break for long visits (4+ hours like theme parks)
                needs_lunch_break = visit_duration >= 240  # 4+ hours
                
                # Filter duplicate opening hours (00:00-23:59 repetitions)
                unique_hours = []
                seen_times = set()
                for start, end in best_place_hours:
                    time_tuple = (start.strftime('%H:%M'), end.strftime('%H:%M'))
                    if time_tuple not in seen_times:
                        unique_hours.append((start, end))
                        seen_times.add(time_tuple)
                
                hours_str = ", ".join([f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}" for start, end in unique_hours])
                if not unique_hours: 
                    hours_str = "Closed"
                
                # Build place name with nested children
                place_display_name = best_place_found['displayName']['text']
                if best_place_found['id'] in nested_map:
                    nested_children = nested_map[best_place_found['id']]
                    if nested_children:
                        child_names = []
                        for child_id in nested_children:
                            child_place = next((p for p in candidate_pool_all if p['id'] == child_id), None)
                            if child_place:
                                child_names.append(child_place['displayName']['text'])
                        if child_names:
                            place_display_name += f" (includes {', '.join(child_names)})"
                
                daily_activities.append({
                    "place_name": place_display_name,
                    "start_time": current_time.strftime('%H:%M'),
                    "opening_hours": hours_str,
                    "visit_duration_mins": visit_duration,
                    "place_obj": best_place_found,
                    "cluster_id": best_place_found.get('cluster_id', -1),
                    "needs_lunch_break": needs_lunch_break,  # Mark for lunch break display
                    "website": best_place_found.get('websiteUri', None)  # Add website link
                })
                
                current_time += timedelta(minutes=visit_duration)
                last_place_obj = best_place_found
                
                # Update cluster tracking
                if best_place_found.get('cluster_id', -1) != -1:
                    visited_clusters_today.add(best_place_found['cluster_id'])
                    current_cluster = best_place_found['cluster_id']
            else:
                break
        
        # Generate smart theme based on clusters visited
        if daily_activities and not is_day_trip:
            # Group activities by cluster
            cluster_groups = defaultdict(list)
            for activity in daily_activities:
                cluster_id = activity.get('cluster_id', -1)
                cluster_groups[cluster_id].append(activity)
            
            # Find dominant cluster
            if cluster_groups:
                dominant_cluster = max(cluster_groups.items(), key=lambda x: len(x[1]))[0]
                places_in_cluster = [a['place_obj'] for a in cluster_groups[dominant_cluster]]
                theme = f"Exploring {get_cluster_name(places_in_cluster)}"
        
        if daily_activities: 
            itinerary_plan.append({"day": day_num, "theme": theme, "activities": daily_activities})
    
    # Add travel times between activities
    for day in itinerary_plan:
        for i in range(len(day['activities'])):
            is_last_activity = (i == len(day['activities']) - 1)
            day['activities'][i]['is_last'] = is_last_activity
            if not is_last_activity:
                current_act_obj = day['activities'][i]['place_obj']
                next_act_obj = day['activities'][i+1]['place_obj']
                day['activities'][i]['travel_to_next_mins'] = estimate_travel_time_between_places(current_act_obj, next_act_obj)
    
    return itinerary_plan

### --- Fancy Itinerary Printer --- ###
def print_itinerary(itinerary_json: Dict, plan_title: str):
    print(f"\n{'='*70}\n   {plan_title.upper()}\n{'='*70}\n")
    if not itinerary_json.get('itinerary'):
        print("Could not generate a valid itinerary with the given constraints.")
        return
    for day in itinerary_json['itinerary']:
        print(f"--- Day {day['day']}: {day['theme']} ---")
        lunch_printed = False
        for activity in day['activities']:
            start_dt = datetime.strptime(activity['start_time'], '%H:%M')
            print(f"[{activity['start_time']}] >> Arrive at: {activity['place_name']}")
            print(f"  |-- Hours: {activity['opening_hours']}")
            print(f"  |-- Visit: ~{activity['visit_duration_mins']} minutes")
            
            # Show website if available
            if activity.get('website'):
                print(f"  |-- Web: {activity['website']}")
            
            # GLOBAL FIX: Show lunch break for long visits (4+ hours)
            if activity.get('needs_lunch_break', False):
                print("  |-- Lunch Break (~60 minutes) - included in visit time")
            
            # Show lunch break between activities if crossing noon
            if not lunch_printed and start_dt.hour >= 12 and not activity['is_last']:
                lunch_printed = True
            
            if activity['is_last']:
                print("  +-- End of day.")
            else:
                travel_time = activity['travel_to_next_mins']
                print(f"  |\n  +-- Travel: ~{travel_time} minutes to next stop.")
        print("-" * 70)

### --- Rankings Table Generator --- ###
def create_rankings_table(places: List[Place], include_clusters: bool = True) -> str:
    """
    Create a formatted table showing all places ranked by score.
    
    Args:
        places: List of Place objects
        include_clusters: Whether to include cluster_id column
    
    Returns:
        Formatted table string
    """
    # Filter out airports and sort by rank_score
    ranked_places = sorted(
        [p for p in places if 'airport' not in p.get('types', []) and p.get('userRatingCount', 0) >= Config.MIN_REVIEW_COUNT],
        key=lambda p: p.get('rank_score', 0),
        reverse=True
    )
    
    if not ranked_places:
        return "No places to display."
    
    # Build table header
    header = f"{'Rank':<5} {'Place Name':<40} {'Score':<8} {'Rating':<7} {'Reviews':<10} {'Distance':<9}"
    if include_clusters:
        header += f" {'Cluster':<8}"
    header += f" {'Types':<30}"
    
    separator = "=" * len(header)
    
    rows = [separator, header, separator]
    
    # Build rows
    for i, place in enumerate(ranked_places[:50], 1):  # Limit to top 50
        name = place.get('displayName', {}).get('text', 'Unknown')[:38]
        score = f"{place.get('rank_score', 0):.4f}"
        rating = f"{place.get('rating', 0):.1f}"
        reviews = f"{place.get('userRatingCount', 0):,}"
        distance = f"{place.get('distance_to_query', 0):.1f} km"
        
        # Get primary type
        types = place.get('types', [])
        primary_type = types[0] if types else 'unknown'
        if 'tourist_attraction' in types and len(types) > 1:
            primary_type = types[1] if types[1] != 'point_of_interest' else types[0]
        primary_type = primary_type.replace('_', ' ')[:28]
        
        row = f"{i:<5} {name:<40} {score:<8} {rating:<7} {reviews:<10} {distance:<9}"
        
        if include_clusters:
            cluster = place.get('cluster_id', -1)
            cluster_str = f"{cluster}" if cluster != -1 else "N/A"
            row += f" {cluster_str:<8}"
        
        row += f" {primary_type:<30}"
        rows.append(row)
    
    rows.append(separator)
    return "\n".join(rows)

### --- Other Top Places Finder --- ###
def get_other_top_places(all_places: List[Place], itinerary_plan: List[Dict], nested_map: Dict[str, List[str]]) -> List[Place]:
    """
    Get remaining places from top 10 that aren't in the itinerary.
    Only returns places from the top 10 ranked attractions.
    
    Args:
        all_places: All available places
        itinerary_plan: The generated itinerary
        nested_map: Map of parent_id -> [child_ids] for nested attractions
    
    Returns:
        List of top 10 places not in itinerary (2-5 places typically)
    """
    # Extract place IDs from itinerary (including nested children)
    used_place_ids = set()
    for day in itinerary_plan:
        for activity in day.get('activities', []):
            place_obj = activity.get('place_obj', {})
            if place_obj.get('id'):
                used_place_ids.add(place_obj['id'])
                # Also mark nested children as "used"
                if place_obj['id'] in nested_map:
                    used_place_ids.update(nested_map[place_obj['id']])
    
    # Get top 10 places by rank_score
    top_10_places = sorted(
        [p for p in all_places 
         if 'airport' not in p.get('types', []) 
         and p.get('userRatingCount', 0) >= Config.MIN_REVIEW_COUNT
         and p.get('distance_to_query', 0) <= CITY_RADIUS_KM],  # Only city attractions
        key=lambda p: p.get('rank_score', 0),
        reverse=True
    )[:10]
    
    # Filter out places already in itinerary
    available_places = [p for p in top_10_places if p['id'] not in used_place_ids]
    
    return available_places

### --- Print Other Top Places (Simplified) --- ###
def print_other_top_places(other_places: List[Place]):
    """Print simplified list of other top places (name, rating, and review count)."""
    if not other_places:
        return
    
    print(f"\n{'='*70}")
    print("   OTHER TOP PLACES YOU MAY VISIT")
    print(f"{'='*70}\n")
    
    for i, place in enumerate(other_places, 1):
        name = place.get('displayName', {}).get('text', 'Unknown')
        rating = place.get('rating', 0)
        reviews = place.get('userRatingCount', 0)
        print(f"{i:2}. {name:<45} [{rating:.1f}/5.0] ({reviews:,} reviews)")
    
    print()

### --- Print Special Time Suggestions --- ###
def print_special_time_suggestions(special_places: Dict[str, List[Place]]):
    """Print early morning and late night place suggestions."""
    if special_places.get('early_morning'):
        print(f"\n{'='*70}")
        print("   EARLY MORNING SUGGESTIONS (Sunrise & More)")
        print(f"{'='*70}\n")
        for i, place in enumerate(special_places['early_morning'], 1):
            name = place.get('displayName', {}).get('text', 'Unknown')
            rating = place.get('rating', 0)
            types = place.get('types', [])
            primary_type = types[0].replace('_', ' ').title() if types else 'Attraction'
            print(f"{i}. {name}")
            print(f"   [{rating:.1f}/5.0] | {primary_type}")
            if website := place.get('websiteUri'):
                print(f"   Web: {website}")
            print()
    
    if special_places.get('late_night'):
        print(f"{'='*70}")
        print("   LATE NIGHT SUGGESTIONS (Sunset & Night Views)")
        print(f"{'='*70}\n")
        for i, place in enumerate(special_places['late_night'], 1):
            name = place.get('displayName', {}).get('text', 'Unknown')
            rating = place.get('rating', 0)
            types = place.get('types', [])
            primary_type = types[0].replace('_', ' ').title() if types else 'Attraction'
            print(f"{i}. {name}")
            print(f"   [{rating:.1f}/5.0] | {primary_type}")
            if website := place.get('websiteUri'):
                print(f"   Web: {website}")
            print()

### --- Save Trip as JSON --- ###
def save_trip_json(city_name: str, trip_data: Dict) -> str:
    """Save trip plan as JSON file in trip_database folder."""
    normalized_name = normalize_city_name(city_name, for_filename=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{normalized_name}_{timestamp}.json"
    filepath = Config.TRIP_DATABASE_DIR / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trip_data, f, indent=2, ensure_ascii=False)
        return str(filename)
    except Exception as e:
        logging.error(f"Could not save trip JSON: {e}")
        return None

# =============================================================================
# --- MAIN EXECUTION ---
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("  Welcome to AI Trip Planner")
    print("="*70)
    try:
        while True:
            city_input = input("\nEnter a city name (or 'quit' to exit): ")
            if city_input.lower() in ['quit', 'exit']: break
            if not city_input: continue
            
            normalized_name_fs = normalize_city_name(city_input, for_filename=True)
            hub_attractions_file = Config.HUB_ATTRACTIONS_DIR / f"{normalized_name_fs}.json"
            
            # Check if data exists, if not, fetch it
            if not hub_attractions_file.exists():
                print(f"\n{'='*70}")
                print(f"No local data for '{city_input.title()}'.")
                print("Running data engine to fetch attractions...")
                print(f"{'='*70}\n")
                
                try:
                    # Run main_engine.py to fetch data
                    result = subprocess.run(
                        [sys.executable, "main_engine.py", city_input], 
                        check=True, 
                        capture_output=True, 
                        text=True,
                        cwd=Path(__file__).parent  # Ensure correct working directory
                    )
                    
                    print(f"✓ Data for '{city_input.title()}' fetched successfully!")
                    
                    # Verify the file was created
                    if not hub_attractions_file.exists():
                        logging.error(f"Data engine completed but file not found: {hub_attractions_file}")
                        print(f"\n[WARNING] Error: Data file was not created. Please try again.")
                        continue
                        
                except subprocess.CalledProcessError as e:
                    logging.error(f"Data engine failed for '{city_input}'. Error:\n{e.stderr}")
                    print(f"\n[ERROR] Error fetching data for '{city_input}':")
                    print(f"{e.stderr[:500]}")  # Show first 500 chars of error
                    print("\nPlease check:")
                    print("  1. Your internet connection")
                    print("  2. Google API key is configured")
                    print("  3. City name spelling is correct")
                    continue
                    
                except FileNotFoundError:
                    logging.error("Could not find 'main_engine.py'. Make sure it's in the same directory.")
                    print("\n[ERROR] Error: main_engine.py not found in current directory.")
                    continue
            
            # Get user input for trip parameters
            num_days = int(input("\nHow many days is your trip? (e.g., 3): "))
            pacing = input("Choose pacing [R]elaxed, [M]oderate, [P]acked: ").upper()
            while pacing not in PACING_OPTIONS:
                pacing = input("Invalid choice. Please enter R, M, or P: ").upper()
            
            exclude_input = input("Types to EXCLUDE (comma-separated, optional): ")
            require_input = input("Types to REQUIRE (comma-separated, optional): ")
            require_places_input = input("Names of places to REQUIRE (comma-separated, optional): ")
            
            exclude_types = sorted([t.strip().lower() for t in exclude_input.split(',') if t.strip()])
            require_types = sorted([t.strip().lower() for t in require_input.split(',') if t.strip()])
            require_names = [normalize_city_name(name) for name in require_places_input.split(',') if name.strip()]

            print("\n" + "="*70)
            print("Analyzing attractions and building your personalized itinerary...")
            print("="*70)
            
            # Load places data
            with open(hub_attractions_file, 'r', encoding='utf-8') as f:
                all_places_data = json.load(f)
            
            # Get city coordinates
            city_center_coords = geocode_city_locally(city_input)
            if not city_center_coords:
                logging.error(f"Could not get coordinates for '{city_input}'.")
                print(f"\n[WARNING] Error: Could not find coordinates for '{city_input}'.")
                continue
            
            # Find nearest airport
            nearest_airport = find_nearest_airport(all_places_data, city_center_coords)
            if nearest_airport:
                airport_name = nearest_airport.get('displayName', {}).get('text', 'Unknown Airport')
                airport_distance = nearest_airport.get('distance_to_query', 0)
                print(f"\nNearest Airport: {airport_name} (~{airport_distance:.1f} km from city center)")
            
            # Perform clustering and nested detection for "other places" feature
            cluster_assignments = simple_clustering(all_places_data, eps_km=3.0, min_samples=2)
            nested_map = detect_nested_attractions(all_places_data)
            for place in all_places_data:
                place['cluster_id'] = cluster_assignments.get(place['id'], -1)
            
            # Generate itineraries
            plan1_title = f"{city_input.title()} Explorer"
            plan1_itinerary = create_final_itinerary(
                copy.deepcopy(all_places_data), 
                num_days, 
                pacing, 
                city_center_coords, 
                city_input, 
                exclude_types, 
                require_types, 
                force_city_only=True, 
                require_names=require_names
            )
            print_itinerary({"itinerary": plan1_itinerary}, plan1_title)
            
            # Show "Other Top Places" from top 10 (excluding itinerary places)
            if plan1_itinerary:
                other_places = get_other_top_places(all_places_data, plan1_itinerary, nested_map)
                print_other_top_places(other_places)

            # Generate day trip option if applicable
            far_places_exist = any(DAY_TRIP_MIN_KM <= p.get('distance_to_query', 0) <= DAY_TRIP_MAX_KM for p in all_places_data)
            plan2_itinerary = []
            if num_days >= 3 and far_places_exist:
                plan2_title = f"{city_input.title()} & Beyond (with Day Trip)"
                plan2_itinerary = create_final_itinerary(
                    copy.deepcopy(all_places_data), 
                    num_days, 
                    pacing, 
                    city_center_coords, 
                    city_input, 
                    exclude_types, 
                    require_types, 
                    force_city_only=False, 
                    require_names=require_names
                )
                print_itinerary({"itinerary": plan2_itinerary}, plan2_title)
                
                # Show other places for plan 2 as well
                if plan2_itinerary:
                    other_places_2 = get_other_top_places(all_places_data, plan2_itinerary, nested_map)
                    if other_places_2:
                        print_other_top_places(other_places_2)
            
            # Find and suggest special time places (sunrise/sunset/night views)
            special_places = find_special_time_places(all_places_data)
            print_special_time_suggestions(special_places)
            
            # Save trip as JSON
            trip_json_data = {
                "city": city_input.title(),
                "generated_at": datetime.now().isoformat(),
                "trip_parameters": {
                    "days": num_days,
                    "pacing": PACING_OPTIONS[pacing]["name"],
                    "exclude_types": exclude_types,
                    "require_types": require_types,
                    "require_names": require_names
                },
                "nearest_airport": {
                    "name": nearest_airport.get('displayName', {}).get('text') if nearest_airport else None,
                    "distance_km": nearest_airport.get('distance_to_query') if nearest_airport else None
                },
                "itineraries": {
                    "city_focused": plan1_itinerary,
                    "with_day_trip": plan2_itinerary if plan2_itinerary else None
                },
                "other_top_places": [
                    {
                        "name": p.get('displayName', {}).get('text'),
                        "rating": p.get('rating'),
                        "reviews": p.get('userRatingCount'),
                        "website": p.get('websiteUri')
                    }
                    for p in (other_places if plan1_itinerary else [])
                ],
                "special_time_suggestions": {
                    "early_morning": [
                        {
                            "name": p.get('displayName', {}).get('text'),
                            "rating": p.get('rating'),
                            "types": p.get('types', []),
                            "website": p.get('websiteUri')
                        }
                        for p in special_places.get('early_morning', [])
                    ],
                    "late_night": [
                        {
                            "name": p.get('displayName', {}).get('text'),
                            "rating": p.get('rating'),
                            "types": p.get('types', []),
                            "website": p.get('websiteUri')
                        }
                        for p in special_places.get('late_night', [])
                    ]
                }
            }
            
            saved_filename = save_trip_json(city_input, trip_json_data)
            if saved_filename:
                print(f"\n{'='*70}")
                print(f"[SUCCESS] Trip plan saved: {saved_filename}")
                print(f"{'='*70}")

    except (ValueError, TypeError) as e:
        logging.error(f"Invalid input. Please enter numbers where expected. Error: {e}")
        print(f"\n[ERROR] Input Error: {e}")
        print("Please enter valid numbers for days and make sure other inputs are formatted correctly.")
    except KeyboardInterrupt:
        print("\n\nThanks for using AI Trip Planner! Goodbye!")
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\n[ERROR] Unexpected Error: {e}")
        print("Please check the logs for details.")