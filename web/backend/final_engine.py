# # # # # import os
# # # # # import re
# # # # # import json
# # # # # import math
# # # # # import time
# # # # # import logging
# # # # # import threading
# # # # # import unicodedata
# # # # # import concurrent.futures
# # # # # import sqlite3
# # # # # import hashlib
# # # # # import random
# # # # # from dataclasses import dataclass, field
# # # # # from collections import deque
# # # # # from pathlib import Path
# # # # # from typing import Any, Dict, List, Optional, Tuple, TypedDict

# # # # # import requests
# # # # # from dotenv import load_dotenv

# # # # # try:
# # # # #     from scipy.spatial import KDTree
# # # # #     HAS_SCIPY = True
# # # # # except ImportError:
# # # # #     HAS_SCIPY = False

# # # # # # =============================================================================
# # # # # # INITIALIZATION
# # # # # # =============================================================================
# # # # # logging.basicConfig(
# # # # #     level=logging.INFO,
# # # # #     format='%(asctime)s - %(levelname)s - %(message)s'
# # # # # )

# # # # # # =============================================================================
# # # # # # TYPE DEFINITIONS
# # # # # # =============================================================================
# # # # # class Location(TypedDict):
# # # # #     latitude: float
# # # # #     longitude: float

# # # # # class DisplayName(TypedDict):
# # # # #     text: str
# # # # #     languageCode: str

# # # # # class Place(TypedDict, total=False):
# # # # #     id: str
# # # # #     location: Location
# # # # #     displayName: DisplayName
# # # # #     types: List[str]
# # # # #     rating: float
# # # # #     userRatingCount: int
# # # # #     thumbnailUrl: str
# # # # #     popularityScore: float
# # # # #     distance_to_query: float
# # # # #     formattedAddress: str
# # # # #     photos: List[Dict]
# # # # #     rank_score: float # CHANGED

# # # # # # =============================================================================
# # # # # # CONFIGURATION
# # # # # # =============================================================================
# # # # # class Config:
# # # # #     load_dotenv()
# # # # #     API_KEY = os.environ.get("GOOGLE_API_KEY")

# # # # #     # Storage
# # # # #     DB_DIR = Path("./adaptive_database")
# # # # #     GEOCODE_DIR = Path("./geocode_database")
# # # # #     CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
# # # # #     HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
# # # # #     TILE_DIR = DB_DIR / "tiles"
# # # # #     GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
# # # # #     PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
# # # # #     TTL_30D = 2_592_000

# # # # #     # Places API
# # # # #     MAX_NEARBY_RADIUS_M = 50_000
# # # # #     MAX_WORKERS = 16
# # # # #     PLACES_CALL_BUDGET: Optional[int] = 7
# # # # #     PAGINATE: bool = True
# # # # #     MAX_RETRIES = 3
# # # # #     TYPE_CITY = ("locality",)
# # # # #     TYPE_ATTRACTION = ("tourist_attraction",)
# # # # #     MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
# # # # #     MASK_ATTRACTION = "places.id,places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.photos"

# # # # #     # Quadtree
# # # # #     DEFAULT_SEARCH_RADIUS_KM = 120
# # # # #     QT_MAX_DEPTH = 4
# # # # #     QT_SPLIT_THRESHOLD = 40
# # # # #     QT_MIN_EDGE_KM = 25.0
# # # # #     TWO_PHASE_NODE: bool = True
    
# # # # #     # Subview (for cache hits)
# # # # #     SUBVIEW_RADIUS_KM = 50
# # # # #     SUBVIEW_MIN_TARGET = 20

# # # # #     # --- Search tuning ---
# # # # #     ADAPTIVE_RADIUS = True
# # # # #     ADAPTIVE_HIGH_THRESHOLD = 10
# # # # #     ADAPTIVE_LOW_THRESHOLD = 1
# # # # #     ADAPTIVE_SHRINK_FACTOR = 0.7
# # # # #     ADAPTIVE_EXPAND_FACTOR = 1.2

# # # # #     # Budget-aware planner
# # # # #     LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

# # # # #     # Reranking
# # # # #     RERANK_MODE = "hybrid"
# # # # #     RATING_PRIOR_M = 5000
# # # # #     WILSON_Z = 1.96
# # # # #     DISTANCE_DECAY_KM = 50.0
# # # # #     COUNT_WEIGHT = 0.25
# # # # #     BAYES_WEIGHT = 0.35
# # # # #     WILSON_WEIGHT = 0.25
# # # # #     DIST_WEIGHT = 0.15
# # # # #     TOP_N = 20
# # # # #     FILTER_NON_LATIN_NAMES = True

# # # # # # --- Ensure Dirs ---
# # # # # for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
# # # # #     path.mkdir(exist_ok=True)

# # # # # # =============================================================================
# # # # # # API CALL TRACKING & CORE CLASSES
# # # # # # =============================================================================
# # # # # class APITracker:
# # # # #     def __init__(self):
# # # # #         self.lock = threading.Lock()
# # # # #         self.calls = {"geocode": 0, "places": 0}
# # # # #         self.cache_hits = 0
# # # # #         self.start_time = time.time()
# # # # #     def count_call(self, api_type: str):
# # # # #         with self.lock:
# # # # #             self.calls[api_type] = self.calls.get(api_type, 0) + 1
# # # # #     def get_calls(self, api_type: str) -> int:
# # # # #         with self.lock:
# # # # #             return self.calls.get(api_type, 0)
# # # # #     def count_cache_hit(self):
# # # # #         with self.lock:
# # # # #             self.cache_hits += 1
# # # # #     def summary(self) -> Dict[str, Any]:
# # # # #         with self.lock:
# # # # #             return {
# # # # #                 "total_api_calls": sum(self.calls.values()),
# # # # #                 "breakdown": dict(self.calls),
# # # # #                 "cache_hits": self.cache_hits,
# # # # #                 "total_time_seconds": round(time.time() - self.start_time, 2),
# # # # #             }
# # # # # tracker = APITracker()

# # # # # class GeocodeCache:
# # # # #     _db_path = Config.GEOCODE_DB_FILE
# # # # #     @classmethod
# # # # #     def _init_db(cls):
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             conn.execute("PRAGMA journal_mode=WAL;")
# # # # #             conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
# # # # #     @classmethod
# # # # #     def load(cls):
# # # # #         cls._init_db()
# # # # #     @classmethod
# # # # #     def get(cls, city_key: str) -> Optional[Dict[str, float]]:
# # # # #         cls._init_db()
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
# # # # #         return {"latitude": row[0], "longitude": row[1]} if row else None
# # # # #     @classmethod
# # # # #     def save(cls, city_key: str, location: Dict[str, float]):
# # # # #         cls._init_db()
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             conn.execute("""
# # # # #                 INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)
# # # # #                 ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp
# # # # #             """, (city_key, location["latitude"], location["longitude"], time.time()))

# # # # # class PlaceIdCache:
# # # # #     _db_path = Config.PLACE_ID_DB_FILE
# # # # #     @classmethod
# # # # #     def _init_db(cls):
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             conn.execute("PRAGMA journal_mode=WAL;")
# # # # #             conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
# # # # #             conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
# # # # #     @classmethod
# # # # #     def load(cls):
# # # # #         cls._init_db()
# # # # #     @classmethod
# # # # #     def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
# # # # #         cls._init_db()
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
# # # # #         return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
# # # # #     @classmethod
# # # # #     def save_many(cls, places: List[Place], hub_name: str):
# # # # #         cls._init_db()
# # # # #         records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
# # # # #         if not records: return
# # # # #         with sqlite3.connect(cls._db_path) as conn:
# # # # #             conn.executemany("""
# # # # #                 INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?)
# # # # #                 ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp
# # # # #             """, records)

# # # # # class DiskCache:
# # # # #     _tile_mem_cache: Dict[str, List[Place]] = {}
# # # # #     _mem_lock = threading.Lock()
# # # # #     @staticmethod
# # # # #     def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> str:
# # # # #         key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}"
# # # # #         return hashlib.sha1(key_string.encode()).hexdigest()
# # # # #     @staticmethod
# # # # #     def _tile_path(key: str) -> Path:
# # # # #         return Config.TILE_DIR / f"{key}.json"
# # # # #     @classmethod
# # # # #     def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> Optional[List[Place]]:
# # # # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # # # #         path = cls._tile_path(key)
# # # # #         with cls._mem_lock:
# # # # #             if key in cls._tile_mem_cache:
# # # # #                 tracker.count_cache_hit()
# # # # #                 return cls._tile_mem_cache[key]
# # # # #         if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
# # # # #             try:
# # # # #                 with open(path, "r", encoding="utf-8") as f:
# # # # #                     data = json.load(f)
# # # # #                 with cls._mem_lock:
# # # # #                     cls._tile_mem_cache[key] = data
# # # # #                 tracker.count_cache_hit()
# # # # #                 return data
# # # # #             except (json.JSONDecodeError, IOError):
# # # # #                 return None
# # # # #         return None
# # # # #     @classmethod
# # # # #     def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place]):
# # # # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # # # #         path = cls._tile_path(key)
# # # # #         try:
# # # # #             with open(path, "w", encoding="utf-8") as f:
# # # # #                 json.dump(places, f, ensure_ascii=False)
# # # # #         except IOError as e:
# # # # #             logging.warning(f"Failed to save tile {path}: {e}")
# # # # #         with cls._mem_lock:
# # # # #             cls._tile_mem_cache[key] = places

# # # # # # =============================================================================
# # # # # # UTILITIES & API HELPERS
# # # # # # =============================================================================
# # # # # def is_primarily_latin(text: str, threshold: float = 0.9) -> bool:
# # # # #     if not text:
# # # # #         return False
# # # # #     latin_chars, total_alnum = 0, 0
# # # # #     for char in text:
# # # # #         if char.isalnum():
# # # # #             total_alnum += 1
# # # # #             if 'a' <= char.lower() <= 'z' or '0' <= char <= '9':
# # # # #                 latin_chars += 1
# # # # #     if total_alnum == 0:
# # # # #         return True
# # # # #     return (latin_chars / total_alnum) >= threshold

# # # # # def normalize_city_name(s: str) -> str:
# # # # #     if not s:
# # # # #         return ""
# # # # #     s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
# # # # #     s = s.lower().strip()
# # # # #     s = re.sub(r"[^\w\s-]", "", s)
# # # # #     s = re.sub(r"\s+", " ", s)
# # # # #     return s.strip()

# # # # # def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
# # # # #     R = 6371.0
# # # # #     dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
# # # # #     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
# # # # #     return 2 * R * math.asin(math.sqrt(a))

# # # # # def km_to_deg_lat(km: float) -> float:
# # # # #     return km / 111.0

# # # # # def km_to_deg_lon(km: float, at_lat: float) -> float:
# # # # #     return km / (111.320 * math.cos(math.radians(at_lat)) + 1e-12)

# # # # # def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
# # # # #     url = "https://places.googleapis.com/v1/places:searchNearby"
# # # # #     for attempt in range(Config.MAX_RETRIES):
# # # # #         try:
# # # # #             resp = requests.post(url, json=payload, headers=headers, timeout=30)
# # # # #             if 500 <= resp.status_code < 600 or resp.status_code == 429:
# # # # #                 logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
# # # # #                 time.sleep((2 ** attempt) + random.random())
# # # # #                 continue
# # # # #             if resp.status_code != 200:
# # # # #                 logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
# # # # #             resp.raise_for_status()
# # # # #             return resp.json()
# # # # #         except requests.exceptions.RequestException as e:
# # # # #             logging.error(f"API request failed after {attempt + 1} attempts: {e}")
# # # # #             break
# # # # #     return None

# # # # # def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str) -> List[Place]:
# # # # #     if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # # #         return []
# # # # #     cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask)
# # # # #     if cached is not None:
# # # # #         return cached

# # # # #     headers = { "Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask }
# # # # #     payload = {
# # # # #         "includedTypes": list(included_types),
# # # # #         "maxResultCount": 20,
# # # # #         "languageCode": "en",
# # # # #         "locationRestriction": {
# # # # #             "circle": {
# # # # #                 "center": {"latitude": lat, "longitude": lon},
# # # # #                 "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))
# # # # #             }
# # # # #         }
# # # # #     }

# # # # #     all_places: List[Place] = []
# # # # #     next_page_token = None
# # # # #     while True:
# # # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # # #             logging.warning("Places API budget exhausted during pagination.")
# # # # #             break
# # # # #         if next_page_token:
# # # # #             payload["pageToken"] = next_page_token
# # # # #             time.sleep(0.5 + random.random() * 0.5)

# # # # #         tracker.count_call("places")
# # # # #         data = _post_with_retry(payload, headers)
# # # # #         if not data or not data.get("places"):
# # # # #             break

# # # # #         current_places = data.get("places", [])
# # # # #         for p in current_places:
# # # # #             if p.get("photos") and len(p["photos"]) > 0:
# # # # #                 p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
# # # # #                 del p["photos"]
# # # # #         all_places.extend(current_places)
# # # # #         next_page_token = data.get("nextPageToken")
# # # # #         if not Config.PAGINATE or not next_page_token:
# # # # #             break

# # # # #     DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places)
# # # # #     return all_places

# # # # # def geocode_city(city_name: str) -> Dict[str, Any]:
# # # # #     normalized_name = normalize_city_name(city_name)
# # # # #     cached = GeocodeCache.get(normalized_name)
# # # # #     if cached:
# # # # #         tracker.count_cache_hit()
# # # # #         return cached
# # # # #     if not Config.API_KEY:
# # # # #         return {"error": "Google API key is not configured."}
# # # # #     tracker.count_call("geocode")
# # # # #     url = "https://maps.googleapis.com/maps/api/geocode/json"
# # # # #     try:
# # # # #         resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
# # # # #         resp.raise_for_status()
# # # # #         data = resp.json()
# # # # #         if data.get("status") == "OK":
# # # # #             loc = data["results"][0]["geometry"]["location"]
# # # # #             result = {"latitude": loc["lat"], "longitude": loc["lng"]}
# # # # #             GeocodeCache.save(normalized_name, result)
# # # # #             return result
# # # # #         return {"error": f"Geocoding API status: {data.get('status')}"}
# # # # #     except requests.exceptions.RequestException as e:
# # # # #         return {"error": f"Geocoding request failed: {e}"}

# # # # # # =============================================================================
# # # # # # QUADTREE ADAPTIVE SEARCH
# # # # # # =============================================================================
# # # # # @dataclass
# # # # # class Quadrant:
# # # # #     min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
# # # # #     @property
# # # # #     def center(self) -> Tuple[float, float]:
# # # # #         return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
# # # # #     @property
# # # # #     def edge_km(self) -> float:
# # # # #         return abs(self.max_lat - self.min_lat) * 111.0
# # # # #     @property
# # # # #     def inscribed_radius_m(self) -> int:
# # # # #         return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
# # # # #     def subdivide(self) -> List["Quadrant"]:
# # # # #         mid_lat, mid_lon = self.center; d = self.depth + 1
# # # # #         return [
# # # # #             Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d),
# # # # #             Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
# # # # #             Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d),
# # # # #             Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)
# # # # #         ]

# # # # # def get_budget_limit_for_depth(depth: int) -> int:
# # # # #     if Config.PLACES_CALL_BUDGET is None:
# # # # #         return float('inf')
    
# # # # #     total_budget = Config.PLACES_CALL_BUDGET
# # # # #     weights = Config.LEVEL_BUDGET_WEIGHTS
    
# # # # #     # Calculate the weight for the current depth and all previous depths
# # # # #     cumulative_weight = 0.0
# # # # #     for d in range(depth + 1):
# # # # #         cumulative_weight += weights.get(d, 0)

# # # # #     # If the depth is beyond what's defined, use the remainder of the budget
# # # # #     if depth not in weights and depth > max(weights.keys()):
# # # # #         remainder = max(0, 1.0 - sum(weights.values()))
# # # # #         # Apply only the remainder for this level, not cumulatively
# # # # #         # To get a cumulative value, we add the sum of all defined weights
# # # # #         cumulative_weight = sum(weights.values()) + remainder

# # # # #     # Ensure the final cumulative weight doesn't exceed 1.0
# # # # #     final_cumulative_weight = min(1.0, cumulative_weight)

# # # # #     return max(1, int(total_budget * final_cumulative_weight))


# # # # # def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# # # # #     q = deque([Quadrant(center_lat - km_to_deg_lat(search_radius_km), center_lon - km_to_deg_lon(search_radius_km, center_lat), center_lat + km_to_deg_lat(search_radius_km), center_lon + km_to_deg_lon(search_radius_km, center_lat), 0)])
# # # # #     cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()

# # # # #     def process_quadrant(quad: Quadrant):
# # # # #         budget_limit = get_budget_limit_for_depth(quad.depth)
# # # # #         if tracker.get_calls("places") >= budget_limit:
# # # # #             if quad.depth < 2:
# # # # #                 logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
# # # # #             return None, None
        
# # # # #         can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
# # # # #         lat, lon = quad.center
        
# # # # #         base_radius_m = quad.inscribed_radius_m
# # # # #         node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY)
        
# # # # #         for c in node_cities:
# # # # #             if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
# # # # #                 GeocodeCache.save(normalize_city_name(name), loc)
        
# # # # #         attraction_radius_m = base_radius_m
# # # # #         if Config.ADAPTIVE_RADIUS:
# # # # #             if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD:
# # # # #                 attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
# # # # #             elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD:
# # # # #                 attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        
# # # # #         node_attrs: List[Place] = []
# # # # #         if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
# # # # #             node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION)
        
# # # # #         with lock:
# # # # #             for p in node_cities:
# # # # #                 if p_id := p.get("id"): cities[p_id] = p
# # # # #             for p in node_attrs:
# # # # #                 if p_id := p.get("id"): attractions[p_id] = p
        
# # # # #         if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD:
# # # # #             return quad.subdivide(), quad.depth
# # # # #         return None, quad.depth

# # # # #     while q:
# # # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # # #             break
# # # # #         current_depth = q[0].depth
# # # # #         level_size = len(q)
# # # # #         logging.info(f"Processing level {current_depth} with {level_size} quadrants...")
        
# # # # #         quadrants_to_process = [q.popleft() for _ in range(level_size)]
# # # # #         with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
# # # # #             future_to_quad = {executor.submit(process_quadrant, quad): quad for quad in quadrants_to_process}
# # # # #             for future in concurrent.futures.as_completed(future_to_quad):
# # # # #                 try:
# # # # #                     if (result := future.result()) and (children := result[0]):
# # # # #                         q.extend(children)
# # # # #                 except Exception as e:
# # # # #                     logging.error(f"A quadrant processing task failed: {e}")
# # # # #     return list(cities.values()), list(attractions.values())

# # # # # # =============================================================================
# # # # # # HUB CACHE & RANKING
# # # # # # =============================================================================
# # # # # @dataclass
# # # # # class HubEntry:
# # # # #     hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)

# # # # # def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
# # # # #     if not places: return {"latitude": 0, "longitude": 0}, 0
# # # # #     lats = [p['location']['latitude'] for p in places if 'location' in p]
# # # # #     lngs = [p['location']['longitude'] for p in places if 'location' in p]
# # # # #     if not lats: return {"latitude": 0, "longitude": 0}, 0
# # # # #     centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
# # # # #     max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
# # # # #     return centroid, max_dist * 1.05

# # # # # class CentralHubCache:
# # # # #     _hubs: Dict[str, HubEntry] = {}
# # # # #     @classmethod
# # # # #     def load(cls):
# # # # #         if not Config.CENTRAL_HUB_FILE.exists(): return
# # # # #         try:
# # # # #             with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f:
# # # # #                 cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
# # # # #             logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
# # # # #         except Exception as e:
# # # # #             logging.error(f"Could not load central hub cache: {e}")
# # # # #     @classmethod
# # # # #     def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
# # # # #         for hub in cls._hubs.values():
# # # # #             if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km:
# # # # #                 return hub
# # # # #         return None
# # # # #     @classmethod
# # # # #     def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
# # # # #         path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
# # # # #         if not path.exists(): return None
# # # # #         try:
# # # # #             with open(path, "r", encoding="utf-8") as f:
# # # # #                 return json.load(f)
# # # # #         except Exception as e:
# # # # #             logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
# # # # #             return None
# # # # #     @classmethod
# # # # #     def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
# # # # #         cls._hubs[hub_entry.hub_name] = hub_entry
# # # # #         for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
# # # # #             temp_path = path.with_suffix(f"{path.suffix}.tmp")
# # # # #             try:
# # # # #                 with open(temp_path, "w", encoding="utf-8") as f:
# # # # #                     json.dump(data, f, ensure_ascii=False)
# # # # #                 os.replace(temp_path, path)
# # # # #             except IOError as e:
# # # # #                 logging.error(f"Could not save hub file {path}: {e}")

# # # # # def _safe_get_rating(p: Dict) -> Optional[float]:
# # # # #     try: return float(p.get("rating")) if p.get("rating") is not None else None
# # # # #     except (ValueError, TypeError): return None
# # # # # def _safe_get_count(p: Dict) -> int:
# # # # #     try: return int(p.get("userRatingCount", 0) or 0)
# # # # #     except (ValueError, TypeError): return 0
# # # # # def _global_mean_rating(places: List[Dict]) -> float:
# # # # #     vals = [_safe_get_rating(p) for p in places if _safe_get_rating(p) is not None]
# # # # #     return (sum(vals) / len(vals)) if vals else 3.5
# # # # # def _bayes_score(R: float, v: int, C: float, m: int) -> float:
# # # # #     return (v * R + m * C) / (v + m) if (v + m) > 0 else C
# # # # # def _wilson_lower_bound(p: float, n: int, z: float) -> float:
# # # # #     if n <= 0: return 0.0
# # # # #     denom = 1 + z*z/n
# # # # #     center = p + z*z/(2*n)
# # # # #     margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
# # # # #     return max(0.0, (center - margin) / denom)

# # # # # def rerank_places(places: List[Place], top_n: int = Config.TOP_N) -> List[Place]:
# # # # #     if not places: return []
# # # # #     mode, m, z, decay_km = Config.RERANK_MODE, Config.RATING_PRIOR_M, Config.WILSON_Z, Config.DISTANCE_DECAY_KM
# # # # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# # # # #     C = _global_mean_rating(places)
# # # # #     max_v = max([_safe_get_count(p) for p in places] + [1])
# # # # #     scored = []
# # # # #     for p in places:
# # # # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# # # # #         if R is None: continue
# # # # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # # # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # # # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # # # #         count_factor = math.log1p(v) / math.log1p(max_v)

# # # # #         if mode == "bayes": final_score = bayes_n
# # # # #         elif mode == "wilson": final_score = wilson
# # # # #         else: final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # # # #         p["rank_score"] = final_score # CHANGED
# # # # #         scored.append(p)

# # # # #     scored.sort(key=lambda x: (-x.get("rank_score", 0.0), x.get("distance_to_query", float("inf")), -_safe_get_count(x), -(_safe_get_rating(x) or 0.0))) # CHANGED
# # # # #     return scored[:top_n]

# # # # # def group_attractions_by_nearest_city(attractions: List[Place], cities: List[Place]) -> Dict[str, List[Place]]:
# # # # #     grouped: Dict[str, List[Place]] = {}
# # # # #     if not cities or not attractions: return grouped
# # # # #     cities_with_loc = [c for c in cities if 'location' in c]
# # # # #     if not cities_with_loc: return grouped
# # # # #     if HAS_SCIPY:
# # # # #         city_coords = [[c['location']['latitude'], c['location']['longitude']] for c in cities_with_loc]
# # # # #         tree = KDTree(city_coords)
# # # # #         for att in attractions:
# # # # #             if 'location' in att:
# # # # #                 _, idx = tree.query([att['location']['latitude'], att['location']['longitude']])
# # # # #                 name = cities_with_loc[idx].get("displayName", {}).get("text", "Unknown City")
# # # # #                 grouped.setdefault(name, []).append(att)
# # # # #     else:
# # # # #         for att in attractions:
# # # # #             if 'location' not in att: continue
# # # # #             best_d, best_c_name = float("inf"), "Unknown City"
# # # # #             for c in cities_with_loc:
# # # # #                 d = haversine_km(att['location']['latitude'], att['location']['longitude'], c['location']['latitude'], c['location']['longitude'])
# # # # #                 if d < best_d:
# # # # #                     best_d, best_c_name = d, c.get("displayName", {}).get("text", "Unknown City")
# # # # #             grouped.setdefault(best_c_name, []).append(att)
# # # # #     return grouped

# # # # # def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
# # # # #     """
# # # # #     Calculates and adds the rank_score to each place in a list.
# # # # #     This function modifies the list in-place and returns it.
# # # # #     """
# # # # #     if not places: 
# # # # #         return []
    
# # # # #     # Get parameters needed for scoring
# # # # #     m, z = Config.RATING_PRIOR_M, Config.WILSON_Z
# # # # #     decay_km = Config.DISTANCE_DECAY_KM
# # # # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
    
# # # # #     C = _global_mean_rating(places)
# # # # #     max_v = max([_safe_get_count(p) for p in places] + [1])

# # # # #     for p in places:
# # # # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
        
# # # # #         # Skip if there's no rating to score
# # # # #         if R is None: 
# # # # #             p["rank_score"] = 0.0 # CHANGED
# # # # #             continue

# # # # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # # # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # # # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # # # #         count_factor = math.log1p(v) / math.log1p(max_v)

# # # # #         final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # # # #         p["rank_score"] = final_score # CHANGED
        
# # # # #     return places

# # # # # # =============================================================================
# # # # # # MAIN FLOW & HELPERS
# # # # # # =============================================================================
# # # # # def enrich_subview_attractions(center_lat: float, center_lon: float, radius_km: float) -> List[Place]:
# # # # #     results: Dict[str, Place] = {}
# # # # #     pts = [(center_lat, center_lon, int(min(radius_km * 1000, Config.MAX_NEARBY_RADIUS_M)))]
# # # # #     for lat, lon, radius_m in pts:
# # # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
# # # # #         for p in places_nearby(lat, lon, radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION):
# # # # #             if pid := p.get("id"): results[pid] = p
# # # # #     return list(results.values())

# # # # # def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# # # # #     logging.info("Performing full adaptive search (this may take a moment)...")
# # # # #     city_list, all_attractions = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km)
    
# # # # #     if all_attractions:
# # # # #         # --- NEW LOGIC STARTS HERE ---
        
# # # # #         # 1. First, add the 'distance_to_query' key to each attraction
# # # # #         logging.info("Calculating distance for all new attractions...")
# # # # #         for att in all_attractions:
# # # # #             if loc := att.get('location'):
# # # # #                 att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))

# # # # #         # 2. Now, add the 'rank_score' to each attraction
# # # # #         logging.info("Calculating and adding rank scores before caching...")
# # # # #         all_attractions = add_rank_scores_to_places(all_attractions)

# # # # #         # --- NEW LOGIC ENDS HERE ---

# # # # #         hub_name = normalize_city_name(user_query_city)
# # # # #         PlaceIdCache.save_many(all_attractions, hub_name)
# # # # #         PlaceIdCache.save_many(city_list, hub_name)
        
# # # # #         centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
# # # # #         new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
        
# # # # #         # 3. Save the hub with attractions that NOW INCLUDE the score
# # # # #         CentralHubCache.save_hub(new_hub, all_attractions)
# # # # #         logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
        
# # # # #     return city_list, all_attractions

# # # # # def main(user_query_city: str, search_radius_km: Optional[float] = None):
# # # # #     if search_radius_km is None:
# # # # #         search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
        
# # # # #     logging.info(f"\n===== Searching for '{user_query_city}' =====")
# # # # #     GeocodeCache.load(); CentralHubCache.load()
# # # # #     center = geocode_city(user_query_city)
# # # # #     if "error" in center:
# # # # #         logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
# # # # #         return

# # # # #     matching_hub = CentralHubCache.find_matching_hub(center['latitude'], center['longitude'])
# # # # #     city_list, all_attractions = [], []

# # # # #     if matching_hub:
# # # # #         logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
# # # # #         tracker.count_cache_hit()
# # # # #         city_list = matching_hub.cities
# # # # #         all_attractions = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # # # #         normalized_query_name = normalize_city_name(user_query_city)
# # # # #         if normalized_query_name != matching_hub.hub_name:
# # # # #             radius_km = Config.SUBVIEW_RADIUS_KM
# # # # #             all_attractions = [att for att in all_attractions if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # # # #             logging.info(f"Filtered {len(all_attractions)} attractions within {radius_km} km of {user_query_city}.")
# # # # #             if len(all_attractions) < Config.SUBVIEW_MIN_TARGET:
# # # # #                 logging.info(f"No/low results for {user_query_city} in hub; enriching subview...")
# # # # #                 newly_found = enrich_subview_attractions(center["latitude"], center["longitude"], radius_km)
# # # # #                 if newly_found:
# # # # #                     PlaceIdCache.save_many(newly_found, matching_hub.hub_name)
# # # # #                     hub_all = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # # # #                     merged_by_id = {p["id"]: p for p in hub_all if p.get("id")}
# # # # #                     for p in newly_found:
# # # # #                         if pid := p.get("id"): merged_by_id[pid] = p
# # # # #                     merged = list(merged_by_id.values())
# # # # #                     CentralHubCache.save_hub(matching_hub, merged)
# # # # #                     all_attractions = [att for att in merged if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # # # #                     logging.info(f"Subview enrichment added {len(newly_found)}; now {len(all_attractions)} within {radius_km} km.")
# # # # #     else:
# # # # #         logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
# # # # #         city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km)

# # # # #     if not all_attractions:
# # # # #         logging.warning("No attractions found.")
# # # # #         return

# # # # #     for att in all_attractions:
# # # # #         if loc := att.get('location'):
# # # # #             att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    
# # # # #     city_list_for_grouping = city_list
# # # # #     if matching_hub and normalize_city_name(user_query_city) != matching_hub.hub_name:
# # # # #          city_list_for_grouping = [c for c in city_list if normalize_city_name(c.get("displayName",{}).get("text","")) == normalize_city_name(user_query_city)]
# # # # #          if not city_list_for_grouping:
# # # # #              city_list_for_grouping = [{"displayName": {"text": user_query_city}, "location": center}]

# # # # #     logging.info(f"\nFound {len(all_attractions)} total attractions.")
# # # # #     grouped = group_attractions_by_nearest_city(all_attractions, city_list_for_grouping)
    
# # # # #     print("\n--- Generating Curated Lists ---")
# # # # #     shown = set()
# # # # #     for cname in sorted(grouped.keys(), key=lambda n: normalize_city_name(n) != normalize_city_name(user_query_city)):
# # # # #         ranked = rerank_places(grouped[cname])
# # # # #         unique_top = [p for p in ranked if (name := p.get("displayName", {}).get("text")) and name not in shown and (is_primarily_latin(name) if Config.FILTER_NON_LATIN_NAMES else True)]
# # # # #         if not unique_top:
# # # # #             continue
# # # # #         print(f"\n--- 🏆 Top {len(unique_top)} Attractions in or near {cname} ---")
# # # # #         for i, p in enumerate(unique_top, 1):
# # # # #             name, rating, cnt, score = p.get("displayName", {}).get("text", "<unknown>"), p.get("rating", "N/A"), _safe_get_count(p), p.get("rank_score", 0) # CHANGED
# # # # #             shown.add(name)
# # # # #             dist = p.get('distance_to_query', -1)
# # # # #             print(f"{i}. {name:<40} | Rating: {rating} ({cnt:,} reviews) | Score: {score:.3f} | Dist: {dist:.1f} km")
# # # # #             # print(f"{i}. {name:<40} | Rating: {rating} ({cnt:,} reviews) | Score: {score:.3f}")

# # # # # # =============================================================================
# # # # # # RUNNER
# # # # # # =============================================================================
# # # # # if __name__ == "__main__":
# # # # #     if not Config.API_KEY:
# # # # #         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

# # # # #     try:
# # # # #         # High budget for initial "build" runs
# # # # #         main("seattle")
        
# # # # #         print("\n" + "#"*60 + "\n")
        
# # # # #         # Low budget for "query" runs that should hit the cache
# # # # #         main("Pattaya")
# # # # #     except Exception as e:
# # # # #         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
    
# # # # #     s = tracker.summary()
# # # # #     print("\n" + "="*50 + "\n" + " "*17 + "SESSION SUMMARY" + "\n" + "="*50)
# # # # #     print(f"Total Time Taken: {s['total_time_seconds']} seconds")
# # # # #     print(f"Total API Calls:  {s['total_api_calls']}")
# # # # #     print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
# # # # #     print(f"  - Places:       {s['breakdown'].get('places', 0)}")
# # # # #     print(f"Cache Hits:       {s['cache_hits']}")
# # # # #     print("="*50)


# # # # import os
# # # # import re
# # # # import json
# # # # import math
# # # # import time
# # # # import logging
# # # # import threading
# # # # import unicodedata
# # # # import concurrent.futures
# # # # import sqlite3
# # # # import hashlib
# # # # import random
# # # # from dataclasses import dataclass, field
# # # # from collections import deque
# # # # from pathlib import Path
# # # # from typing import Any, Dict, List, Optional, Tuple, TypedDict
# # # # from difflib import SequenceMatcher

# # # # import requests
# # # # from dotenv import load_dotenv

# # # # try:
# # # #     from scipy.spatial import KDTree
# # # #     HAS_SCIPY = True
# # # # except ImportError:
# # # #     HAS_SCIPY = False

# # # # try:
# # # #     import matplotlib.pyplot as plt
# # # #     import matplotlib.patches as patches
# # # #     HAS_MATPLOTLIB = True
# # # # except ImportError:
# # # #     HAS_MATPLOTLIB = False

# # # # # =============================================================================
# # # # # INITIALIZATION
# # # # # =============================================================================
# # # # logging.basicConfig(
# # # #     level=logging.INFO,
# # # #     format='%(asctime)s - %(levelname)s - %(message)s'
# # # # )

# # # # # =============================================================================
# # # # # TYPE DEFINITIONS
# # # # # =============================================================================
# # # # class Location(TypedDict):
# # # #     latitude: float
# # # #     longitude: float

# # # # class DisplayName(TypedDict):
# # # #     text: str
# # # #     languageCode: str

# # # # class Place(TypedDict, total=False):
# # # #     id: str
# # # #     location: Location
# # # #     displayName: DisplayName
# # # #     types: List[str]
# # # #     rating: float
# # # #     userRatingCount: int
# # # #     thumbnailUrl: str
# # # #     popularityScore: float
# # # #     distance_to_query: float
# # # #     formattedAddress: str
# # # #     photos: List[Dict]
# # # #     rank_score: float

# # # # # =============================================================================
# # # # # CONFIGURATION
# # # # # =============================================================================
# # # # class Config:
# # # #     load_dotenv()
# # # #     API_KEY = os.environ.get("GOOGLE_API_KEY")

# # # #     # Storage
# # # #     DB_DIR = Path("./adaptive_database")
# # # #     GEOCODE_DIR = Path("./geocode_database")
# # # #     CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
# # # #     HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
# # # #     TILE_DIR = DB_DIR / "tiles"
# # # #     GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
# # # #     PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
# # # #     TTL_30D = 2_592_000

# # # #     # Places API
# # # #     MAX_NEARBY_RADIUS_M = 50_000
# # # #     MAX_WORKERS = 16
# # # #     PLACES_CALL_BUDGET: Optional[int] = 7
# # # #     PAGINATE: bool = True
# # # #     MAX_RETRIES = 3
# # # #     TYPE_CITY = ("locality",)
# # # #     TYPE_ATTRACTION = ("tourist_attraction",)
# # # #     MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
# # # #     MASK_ATTRACTION = "places.id,places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.photos"

# # # #     # Quadtree
# # # #     DEFAULT_SEARCH_RADIUS_KM = 120
# # # #     QT_MAX_DEPTH = 4
# # # #     QT_SPLIT_THRESHOLD = 40
# # # #     QT_MIN_EDGE_KM = 25.0
# # # #     TWO_PHASE_NODE: bool = True
    
# # # #     # Subview (for cache hits)
# # # #     SUBVIEW_RADIUS_KM = 50
# # # #     SUBVIEW_MIN_TARGET = 20

# # # #     # --- Search tuning ---
# # # #     ADAPTIVE_RADIUS = True
# # # #     ADAPTIVE_HIGH_THRESHOLD = 10
# # # #     ADAPTIVE_LOW_THRESHOLD = 1
# # # #     ADAPTIVE_SHRINK_FACTOR = 0.7
# # # #     ADAPTIVE_EXPAND_FACTOR = 1.2

# # # #     # Budget-aware planner
# # # #     LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

# # # #     # Reranking
# # # #     RERANK_MODE = "hybrid"
# # # #     MIN_REVIEW_COUNT = 1000
# # # #     RATING_PRIOR_M = 5000
# # # #     WILSON_Z = 1.96
# # # #     DISTANCE_DECAY_KM = 50.0
# # # #     COUNT_WEIGHT = 0.25
# # # #     BAYES_WEIGHT = 0.35
# # # #     WILSON_WEIGHT = 0.25
# # # #     DIST_WEIGHT = 0.15
# # # #     TOP_N = 20
# # # #     FILTER_NON_LATIN_NAMES = True

# # # # # --- Ensure Dirs ---
# # # # for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
# # # #     path.mkdir(exist_ok=True)

# # # # # =============================================================================
# # # # # API CALL TRACKING & CORE CLASSES
# # # # # =============================================================================
# # # # class APITracker:
# # # #     def __init__(self):
# # # #         self.lock = threading.Lock()
# # # #         self.calls = {"geocode": 0, "places": 0}
# # # #         self.cache_hits = 0
# # # #         self.start_time = time.time()
# # # #     def count_call(self, api_type: str):
# # # #         with self.lock:
# # # #             self.calls[api_type] = self.calls.get(api_type, 0) + 1
# # # #     def get_calls(self, api_type: str) -> int:
# # # #         with self.lock:
# # # #             return self.calls.get(api_type, 0)
# # # #     def count_cache_hit(self):
# # # #         with self.lock:
# # # #             self.cache_hits += 1
# # # #     def summary(self) -> Dict[str, Any]:
# # # #         with self.lock:
# # # #             return {
# # # #                 "total_api_calls": sum(self.calls.values()),
# # # #                 "breakdown": dict(self.calls),
# # # #                 "cache_hits": self.cache_hits,
# # # #                 "total_time_seconds": round(time.time() - self.start_time, 2),
# # # #             }
# # # # tracker = APITracker()

# # # # class GeocodeCache:
# # # #     _db_path = Config.GEOCODE_DB_FILE
# # # #     @classmethod
# # # #     def _init_db(cls):
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             conn.execute("PRAGMA journal_mode=WAL;")
# # # #             conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
# # # #     @classmethod
# # # #     def load(cls):
# # # #         cls._init_db()
# # # #     @classmethod
# # # #     def get(cls, city_key: str) -> Optional[Dict[str, float]]:
# # # #         cls._init_db()
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
# # # #         return {"latitude": row[0], "longitude": row[1]} if row else None
# # # #     @classmethod
# # # #     def save(cls, city_key: str, location: Dict[str, float]):
# # # #         cls._init_db()
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             conn.execute("""
# # # #                 INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)
# # # #                 ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp
# # # #             """, (city_key, location["latitude"], location["longitude"], time.time()))

# # # # class PlaceIdCache:
# # # #     _db_path = Config.PLACE_ID_DB_FILE
# # # #     @classmethod
# # # #     def _init_db(cls):
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             conn.execute("PRAGMA journal_mode=WAL;")
# # # #             conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
# # # #             conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
# # # #     @classmethod
# # # #     def load(cls):
# # # #         cls._init_db()
# # # #     @classmethod
# # # #     def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
# # # #         cls._init_db()
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
# # # #         return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
# # # #     @classmethod
# # # #     def save_many(cls, places: List[Place], hub_name: str):
# # # #         cls._init_db()
# # # #         records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
# # # #         if not records: return
# # # #         with sqlite3.connect(cls._db_path) as conn:
# # # #             conn.executemany("""
# # # #                 INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?)
# # # #                 ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp
# # # #             """, records)

# # # # class DiskCache:
# # # #     _tile_mem_cache: Dict[str, List[Place]] = {}
# # # #     _mem_lock = threading.Lock()
# # # #     @staticmethod
# # # #     def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> str:
# # # #         key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}"
# # # #         return hashlib.sha1(key_string.encode()).hexdigest()
# # # #     @staticmethod
# # # #     def _tile_path(key: str) -> Path:
# # # #         return Config.TILE_DIR / f"{key}.json"
# # # #     @classmethod
# # # #     def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> Optional[List[Place]]:
# # # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # # #         path = cls._tile_path(key)
# # # #         with cls._mem_lock:
# # # #             if key in cls._tile_mem_cache:
# # # #                 tracker.count_cache_hit()
# # # #                 return cls._tile_mem_cache[key]
# # # #         if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
# # # #             try:
# # # #                 with open(path, "r", encoding="utf-8") as f:
# # # #                     data = json.load(f)
# # # #                 with cls._mem_lock:
# # # #                     cls._tile_mem_cache[key] = data
# # # #                 tracker.count_cache_hit()
# # # #                 return data
# # # #             except (json.JSONDecodeError, IOError):
# # # #                 return None
# # # #         return None
# # # #     @classmethod
# # # #     def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place]):
# # # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # # #         path = cls._tile_path(key)
# # # #         try:
# # # #             with open(path, "w", encoding="utf-8") as f:
# # # #                 json.dump(places, f, ensure_ascii=False)
# # # #         except IOError as e:
# # # #             logging.warning(f"Failed to save tile {path}: {e}")
# # # #         with cls._mem_lock:
# # # #             cls._tile_mem_cache[key] = places

# # # # # =============================================================================
# # # # # UTILITIES & API HELPERS
# # # # # =============================================================================
# # # # def is_primarily_latin(text: str, threshold: float = 0.9) -> bool:
# # # #     if not text:
# # # #         return False
# # # #     latin_chars, total_alnum = 0, 0
# # # #     for char in text:
# # # #         if char.isalnum():
# # # #             total_alnum += 1
# # # #             if 'a' <= char.lower() <= 'z' or '0' <= char <= '9':
# # # #                 latin_chars += 1
# # # #     if total_alnum == 0:
# # # #         return True
# # # #     return (latin_chars / total_alnum) >= threshold

# # # # def normalize_city_name(s: str) -> str:
# # # #     if not s:
# # # #         return ""
# # # #     s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
# # # #     s = s.lower().strip()
# # # #     s = re.sub(r"[^\w\s-]", "", s)
# # # #     s = re.sub(r"\s+", " ", s)
# # # #     return s.strip()

# # # # def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
# # # #     R = 6371.0
# # # #     dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
# # # #     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
# # # #     return 2 * R * math.asin(math.sqrt(a))

# # # # def km_to_deg_lat(km: float) -> float:
# # # #     return km / 111.0

# # # # def km_to_deg_lon(km: float, at_lat: float) -> float:
# # # #     return km / (111.320 * math.cos(math.radians(at_lat)) + 1e-12)

# # # # def get_simple_name(text: str) -> str:
# # # #     """Normalizes a name for comparison by removing generic terms."""
# # # #     if not text: return ""
# # # #     text = text.lower()
# # # #     text = text.replace('mt.', 'mount').replace('mt ', 'mount ')
# # # #     generic_terms = ['park', 'center', 'museum', 'garden', 'lookout', 'trail', 'trailhead']
# # # #     for term in generic_terms:
# # # #         text = text.replace(term, '')
# # # #     return re.sub(r'\s+', ' ', text).strip()

# # # # def get_category_from_place(place: Place) -> str:
# # # #     """Assigns a place to a predefined category based on its type and name."""
# # # #     types = place.get('types', [])
# # # #     name = place.get('displayName', {}).get('text', '').lower()
    
# # # #     # --- New, more specific categories at the top ---
# # # #     if 'beach' in types:
# # # #         return "Beaches & Waterfront"
    
# # # #     if 'historical_landmark' in types or 'historical_place' in types:
# # # #         return "Historical Sites"

# # # #     # --- Existing categories ---
# # # #     if 'zoo' in types or 'aquarium' in types: 
# # # #         return "Zoos & Aquariums"
        
# # # #     if 'museum' in types or 'art_gallery' in types: 
# # # #         return "Museums & Culture"
    
# # # #     if 'hike' in name or 'trail' in name or 'falls' in name or 'lookout' in name:
# # # #         return "Parks & Hiking"
        
# # # #     if 'park' in types or 'national_park' in types:
# # # #         if 'stadium' not in types:
# # # #             return "Parks & Hiking"
            
# # # #     if 'stadium' in types: 
# # # #         return "Venues & Stadiums"
        
# # # #     if 'tourist_attraction' in types: 
# # # #         return "Landmarks & Points of Interest"
    
# # # #     return "Other Attractions"

# # # # def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
# # # #     url = "https://places.googleapis.com/v1/places:searchNearby"
# # # #     for attempt in range(Config.MAX_RETRIES):
# # # #         try:
# # # #             resp = requests.post(url, json=payload, headers=headers, timeout=30)
# # # #             if 500 <= resp.status_code < 600 or resp.status_code == 429:
# # # #                 logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
# # # #                 time.sleep((2 ** attempt) + random.random())
# # # #                 continue
# # # #             if resp.status_code != 200:
# # # #                 logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
# # # #             resp.raise_for_status()
# # # #             return resp.json()
# # # #         except requests.exceptions.RequestException as e:
# # # #             logging.error(f"API request failed after {attempt + 1} attempts: {e}")
# # # #             break
# # # #     return None

# # # # def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str) -> List[Place]:
# # # #     if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # #         return []
# # # #     cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask)
# # # #     if cached is not None:
# # # #         return cached

# # # #     headers = { "Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask }
# # # #     payload = {
# # # #         "includedTypes": list(included_types),
# # # #         "maxResultCount": 20,
# # # #         "languageCode": "en",
# # # #         "locationRestriction": {
# # # #             "circle": {
# # # #                 "center": {"latitude": lat, "longitude": lon},
# # # #                 "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))
# # # #             }
# # # #         }
# # # #     }

# # # #     all_places: List[Place] = []
# # # #     next_page_token = None
# # # #     while True:
# # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # #             logging.warning("Places API budget exhausted during pagination.")
# # # #             break
# # # #         if next_page_token:
# # # #             payload["pageToken"] = next_page_token
# # # #             time.sleep(0.5 + random.random() * 0.5)

# # # #         tracker.count_call("places")
# # # #         data = _post_with_retry(payload, headers)
# # # #         if not data or not data.get("places"):
# # # #             break

# # # #         current_places = data.get("places", [])
# # # #         for p in current_places:
# # # #             if p.get("photos") and len(p["photos"]) > 0:
# # # #                 p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
# # # #                 del p["photos"]
# # # #         all_places.extend(current_places)
# # # #         next_page_token = data.get("nextPageToken")
# # # #         if not Config.PAGINATE or not next_page_token:
# # # #             break

# # # #     DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places)
# # # #     return all_places

# # # # def geocode_city(city_name: str) -> Dict[str, Any]:
# # # #     normalized_name = normalize_city_name(city_name)
# # # #     cached = GeocodeCache.get(normalized_name)
# # # #     if cached:
# # # #         tracker.count_cache_hit()
# # # #         return cached
# # # #     if not Config.API_KEY:
# # # #         return {"error": "Google API key is not configured."}
# # # #     tracker.count_call("geocode")
# # # #     url = "https://maps.googleapis.com/maps/api/geocode/json"
# # # #     try:
# # # #         resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
# # # #         resp.raise_for_status()
# # # #         data = resp.json()
# # # #         if data.get("status") == "OK":
# # # #             loc = data["results"][0]["geometry"]["location"]
# # # #             result = {"latitude": loc["lat"], "longitude": loc["lng"]}
# # # #             GeocodeCache.save(normalized_name, result)
# # # #             return result
# # # #         return {"error": f"Geocoding API status: {data.get('status')}"}
# # # #     except requests.exceptions.RequestException as e:
# # # #         return {"error": f"Geocoding request failed: {e}"}

# # # # def visualize_quadtree(quads: List[Dict], center: Dict, search_radius_km: float, filename="quadtree_visualization.png"):
# # # #     """
# # # #     Generates a visualization of the quadtree search grid.
# # # #     """
# # # #     if not HAS_MATPLOTLIB:
# # # #         logging.warning("Matplotlib not found. Skipping visualization.")
# # # #         return

# # # #     fig, ax = plt.subplots(figsize=(12, 12))
# # # #     ax.set_aspect('equal', adjustable='box')

# # # #     depth_colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6']
# # # #     all_lats = [center['latitude']]
# # # #     all_lons = [center['longitude']]
# # # #     max_density = max([q['cities'] + q['attractions'] for q in quads] + [1])

# # # #     for q in quads:
# # # #         min_lat, min_lon, max_lat, max_lon = q['bounds']
# # # #         depth = q['depth']
# # # #         density = q['cities'] + q['attractions']
# # # #         all_lats.extend([min_lat, max_lat])
# # # #         all_lons.extend([min_lon, max_lon])
# # # #         width = max_lon - min_lon
# # # #         height = max_lat - min_lat
# # # #         alpha = 0.1 + 0.6 * (density / max_density)
        
# # # #         rect = patches.Rectangle(
# # # #             (min_lon, min_lat), width, height,
# # # #             linewidth=1.5,
# # # #             edgecolor=depth_colors[depth % len(depth_colors)],
# # # #             facecolor=depth_colors[depth % len(depth_colors)],
# # # #             alpha=alpha
# # # #         )
# # # #         ax.add_patch(rect)
        
# # # #         if density > 0:
# # # #             ax.text(min_lon + width/2, min_lat + height/2, f"C:{q['cities']}\nA:{q['attractions']}",
# # # #                     ha='center', va='center', fontsize=8, color='black')

# # # #     ax.plot(center['longitude'], center['latitude'], 'ro', markersize=8, label='Query Center')
# # # #     lat_margin = (max(all_lats) - min(all_lats)) * 0.1
# # # #     lon_margin = (max(all_lons) - min(all_lons)) * 0.1
# # # #     ax.set_xlim(min(all_lons) - lon_margin, max(all_lons) + lon_margin)
# # # #     ax.set_ylim(min(all_lats) - lat_margin, max(all_lats) + lat_margin)
# # # #     ax.set_xlabel("Longitude")
# # # #     ax.set_ylabel("Latitude")
# # # #     ax.set_title(f"Quadtree Distribution for search radius {search_radius_km} km")
# # # #     ax.legend()
# # # #     ax.grid(True)
    
# # # #     plt.savefig(filename)
# # # #     plt.close(fig)
# # # #     logging.info(f"Quadtree visualization saved to {filename}")

# # # # def visualize_final_tree(categorized_data: Dict[str, List[Dict[str, Any]]], city_name: str, filename="final_tree_visualization.png"):
# # # #     """
# # # #     Generates a tree visualization of the final categorized and grouped attractions.
# # # #     """
# # # #     if not HAS_MATPLOTLIB:
# # # #         logging.warning("Matplotlib not found. Skipping final tree visualization.")
# # # #         return
        
# # # #     fig, ax = plt.subplots(figsize=(20, 30))
# # # #     ax.axis('off')
    
# # # #     total_items = 1 
# # # #     for category, items in categorized_data.items():
# # # #         total_items += 1 
# # # #         for item in items:
# # # #             total_items += 1 
# # # #             total_items += len(item['children'])

# # # #     y_step = 1.0 / (total_items + 2)
# # # #     y_pos = 0.98

# # # #     ax.text(0.0, y_pos, f"Attractions for {city_name.title()}", fontsize=20, fontweight='bold', ha='left')
# # # #     y_pos -= y_step * 2

# # # #     for category in sorted(categorized_data.keys()):
# # # #         cat_y = y_pos
# # # #         ax.text(0.1, y_pos, category, fontsize=16, fontweight='bold', color='#4363d8', ha='left')
# # # #         y_pos -= y_step

# # # #         for item in categorized_data[category]:
# # # #             parent = item['parent']
# # # #             parent_name = parent.get("displayName", {}).get("text", "<unknown>")
            
# # # #             parent_y = y_pos
# # # #             ax.plot([0.1, 0.2], [cat_y, parent_y], 'k-', lw=0.5)
# # # #             ax.text(0.22, y_pos, f"• {parent_name}", fontsize=12, ha='left', va='center')
# # # #             y_pos -= y_step
            
# # # #             for child in item['children']:
# # # #                 child_name = child.get("displayName", {}).get("text", "<unknown>")
# # # #                 ax.plot([0.2, 0.3], [parent_y, y_pos], 'k-', lw=0.5, color='gray')
# # # #                 ax.text(0.32, y_pos, f"- {child_name}", fontsize=10, ha='left', va='center', color='dimgray')
# # # #                 y_pos -= y_step
        
# # # #         y_pos -= y_step 
    
# # # #     ax.set_ylim(0, 1)
# # # #     ax.set_xlim(0, 1)
# # # #     plt.title("Attraction Hierarchy", fontsize=24, pad=20)
# # # #     plt.tight_layout()
# # # #     plt.savefig(filename, bbox_inches='tight')
# # # #     plt.close(fig)
# # # #     logging.info(f"Final tree visualization saved to {filename}")

# # # # # =============================================================================
# # # # # QUADTREE ADAPTIVE SEARCH
# # # # # =============================================================================
# # # # @dataclass
# # # # class Quadrant:
# # # #     min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
# # # #     @property
# # # #     def center(self) -> Tuple[float, float]:
# # # #         return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
# # # #     @property
# # # #     def edge_km(self) -> float:
# # # #         return abs(self.max_lat - self.min_lat) * 111.0
# # # #     @property
# # # #     def inscribed_radius_m(self) -> int:
# # # #         return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
# # # #     def subdivide(self) -> List["Quadrant"]:
# # # #         mid_lat, mid_lon = self.center; d = self.depth + 1
# # # #         return [
# # # #             Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d),
# # # #             Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
# # # #             Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d),
# # # #             Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)
# # # #         ]

# # # # def get_budget_limit_for_depth(depth: int) -> int:
# # # #     if Config.PLACES_CALL_BUDGET is None:
# # # #         return float('inf')
    
# # # #     total_budget = Config.PLACES_CALL_BUDGET
# # # #     weights = Config.LEVEL_BUDGET_WEIGHTS
    
# # # #     cumulative_weight = 0.0
# # # #     for d in range(depth + 1):
# # # #         cumulative_weight += weights.get(d, 0)

# # # #     if depth not in weights and depth > max(weights.keys()):
# # # #         remainder = max(0, 1.0 - sum(weights.values()))
# # # #         cumulative_weight = sum(weights.values()) + remainder

# # # #     final_cumulative_weight = min(1.0, cumulative_weight)

# # # #     return max(1, int(total_budget * final_cumulative_weight))


# # # # def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float) -> Tuple[List[Place], List[Place], List[Dict]]:
# # # #     q = deque([Quadrant(center_lat - km_to_deg_lat(search_radius_km), center_lon - km_to_deg_lon(search_radius_km, center_lat), center_lat + km_to_deg_lat(search_radius_km), center_lon + km_to_deg_lon(search_radius_km, center_lat), 0)])
# # # #     cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()
# # # #     visual_quads: List[Dict] = []

# # # #     def process_quadrant(quad: Quadrant):
# # # #         budget_limit = get_budget_limit_for_depth(quad.depth)
# # # #         if tracker.get_calls("places") >= budget_limit:
# # # #             if quad.depth < 2:
# # # #                 logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
# # # #             return None, None
        
# # # #         can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
# # # #         lat, lon = quad.center
        
# # # #         base_radius_m = quad.inscribed_radius_m
# # # #         node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY)
        
# # # #         for c in node_cities:
# # # #             if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
# # # #                 GeocodeCache.save(normalize_city_name(name), loc)
        
# # # #         attraction_radius_m = base_radius_m
# # # #         if Config.ADAPTIVE_RADIUS:
# # # #             if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD:
# # # #                 attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
# # # #             elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD:
# # # #                 attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        
# # # #         node_attrs: List[Place] = []
# # # #         if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
# # # #             node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION)
        
# # # #         with lock:
# # # #             visual_quads.append({
# # # #                 'bounds': (quad.min_lat, quad.min_lon, quad.max_lat, quad.max_lon),
# # # #                 'depth': quad.depth,
# # # #                 'cities': len(node_cities),
# # # #                 'attractions': len(node_attrs)
# # # #             })
# # # #             for p in node_cities:
# # # #                 if p_id := p.get("id"): cities[p_id] = p
# # # #             for p in node_attrs:
# # # #                 if p_id := p.get("id"): attractions[p_id] = p
        
# # # #         if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD:
# # # #             return quad.subdivide(), quad.depth
# # # #         return None, quad.depth

# # # #     while q:
# # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # # #             break
# # # #         current_depth = q[0].depth
# # # #         level_size = len(q)
# # # #         logging.info(f"Processing level {current_depth} with {level_size} quadrants...")
        
# # # #         quadrants_to_process = [q.popleft() for _ in range(level_size)]
# # # #         with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
# # # #             future_to_quad = {executor.submit(process_quadrant, quad): quad for quad in quadrants_to_process}
# # # #             for future in concurrent.futures.as_completed(future_to_quad):
# # # #                 try:
# # # #                     if (result := future.result()) and (children := result[0]):
# # # #                         q.extend(children)
# # # #                 except Exception as e:
# # # #                     logging.error(f"A quadrant processing task failed: {e}")
# # # #     return list(cities.values()), list(attractions.values()), visual_quads

# # # # # =============================================================================
# # # # # HUB CACHE & RANKING
# # # # # =============================================================================
# # # # @dataclass
# # # # class HubEntry:
# # # #     hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)

# # # # def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
# # # #     if not places: return {"latitude": 0, "longitude": 0}, 0
# # # #     lats = [p['location']['latitude'] for p in places if 'location' in p]
# # # #     lngs = [p['location']['longitude'] for p in places if 'location' in p]
# # # #     if not lats: return {"latitude": 0, "longitude": 0}, 0
# # # #     centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
# # # #     max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
# # # #     return centroid, max_dist * 1.05

# # # # class CentralHubCache:
# # # #     _hubs: Dict[str, HubEntry] = {}
# # # #     @classmethod
# # # #     def load(cls):
# # # #         if not Config.CENTRAL_HUB_FILE.exists(): return
# # # #         try:
# # # #             with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f:
# # # #                 cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
# # # #             logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
# # # #         except Exception as e:
# # # #             logging.error(f"Could not load central hub cache: {e}")
# # # #     @classmethod
# # # #     def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
# # # #         for hub in cls._hubs.values():
# # # #             if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km:
# # # #                 return hub
# # # #         return None
# # # #     @classmethod
# # # #     def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
# # # #         path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
# # # #         if not path.exists(): return None
# # # #         try:
# # # #             with open(path, "r", encoding="utf-8") as f:
# # # #                 return json.load(f)
# # # #         except Exception as e:
# # # #             logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
# # # #             return None
# # # #     @classmethod
# # # #     def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
# # # #         cls._hubs[hub_entry.hub_name] = hub_entry
# # # #         for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
# # # #             temp_path = path.with_suffix(f"{path.suffix}.tmp")
# # # #             try:
# # # #                 with open(temp_path, "w", encoding="utf-8") as f:
# # # #                     json.dump(data, f, ensure_ascii=False, indent=4)
# # # #                 os.replace(temp_path, path)
# # # #             except IOError as e:
# # # #                 logging.error(f"Could not save hub file {path}: {e}")

# # # # def _safe_get_rating(p: Dict) -> Optional[float]:
# # # #     try: return float(p.get("rating")) if p.get("rating") is not None else None
# # # #     except (ValueError, TypeError): return None
# # # # def _safe_get_count(p: Dict) -> int:
# # # #     try: return int(p.get("userRatingCount", 0) or 0)
# # # #     except (ValueError, TypeError): return 0
# # # # def _global_mean_rating(places: List[Dict]) -> float:
# # # #     vals = [_safe_get_rating(p) for p in places if _safe_get_rating(p) is not None]
# # # #     return (sum(vals) / len(vals)) if vals else 3.5
# # # # def _bayes_score(R: float, v: int, C: float, m: int) -> float:
# # # #     return (v * R + m * C) / (v + m) if (v + m) > 0 else C
# # # # def _wilson_lower_bound(p: float, n: int, z: float) -> float:
# # # #     if n <= 0: return 0.0
# # # #     denom = 1 + z*z/n
# # # #     center = p + z*z/(2*n)
# # # #     margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
# # # #     return max(0.0, (center - margin) / denom)

# # # # def rerank_places(places: List[Place], top_n: int = Config.TOP_N) -> List[Place]:
# # # #     if not places: return []
# # # #     mode, m, z, decay_km = Config.RERANK_MODE, Config.RATING_PRIOR_M, Config.WILSON_Z, Config.DISTANCE_DECAY_KM
# # # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# # # #     C = _global_mean_rating(places)
# # # #     max_v = max([_safe_get_count(p) for p in places] + [1])
# # # #     scored = []
# # # #     for p in places:
# # # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# # # #         if R is None: continue
# # # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # # #         count_factor = math.log1p(v) / math.log1p(max_v)

# # # #         if mode == "bayes": final_score = bayes_n
# # # #         elif mode == "wilson": final_score = wilson
# # # #         else: final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # # #         p["rank_score"] = final_score
# # # #         scored.append(p)

# # # #     scored.sort(key=lambda x: (-x.get("rank_score", 0.0), x.get("distance_to_query", float("inf")), -_safe_get_count(x), -(_safe_get_rating(x) or 0.0)))
# # # #     return scored[:top_n]

# # # # def group_attractions_by_nearest_city(attractions: List[Place], cities: List[Place]) -> Dict[str, List[Place]]:
# # # #     grouped: Dict[str, List[Place]] = {}
# # # #     if not cities or not attractions: return grouped
# # # #     cities_with_loc = [c for c in cities if 'location' in c]
# # # #     if not cities_with_loc: return grouped
# # # #     if HAS_SCIPY:
# # # #         city_coords = [[c['location']['latitude'], c['location']['longitude']] for c in cities_with_loc]
# # # #         tree = KDTree(city_coords)
# # # #         for att in attractions:
# # # #             if 'location' in att:
# # # #                 _, idx = tree.query([att['location']['latitude'], att['location']['longitude']])
# # # #                 name = cities_with_loc[idx].get("displayName", {}).get("text", "Unknown City")
# # # #                 grouped.setdefault(name, []).append(att)
# # # #     else:
# # # #         for att in attractions:
# # # #             if 'location' not in att: continue
# # # #             best_d, best_c_name = float("inf"), "Unknown City"
# # # #             for c in cities_with_loc:
# # # #                 d = haversine_km(att['location']['latitude'], att['location']['longitude'], c['location']['latitude'], c['location']['longitude'])
# # # #                 if d < best_d:
# # # #                     best_d, best_c_name = d, c.get("displayName", {}).get("text", "Unknown City")
# # # #             grouped.setdefault(best_c_name, []).append(att)
# # # #     return grouped

# # # # def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
# # # #     if not places: return []
# # # #     m, z = Config.RATING_PRIOR_M, Config.WILSON_Z
# # # #     decay_km = Config.DISTANCE_DECAY_KM
# # # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# # # #     C = _global_mean_rating(places)
# # # #     max_v = max([_safe_get_count(p) for p in places] + [1])
# # # #     for p in places:
# # # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# # # #         if R is None: 
# # # #             p["rank_score"] = 0.0
# # # #             continue
# # # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # # #         count_factor = math.log1p(v) / math.log1p(max_v)
# # # #         final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # # #         p["rank_score"] = final_score
# # # #     return places

# # # # def structure_and_categorize_places(places: List[Place]) -> Dict[str, List[Dict[str, Any]]]:
# # # #     """
# # # #     Deduplicates, groups, and categorizes a list of places.
# # # #     This new version ensures a place can only be a child or a parent, not both,
# # # #     and uses a more robust method for grouping.
# # # #     """
# # # #     if not places: return {}
# # # #     places = [p for p in places if _safe_get_count(p) >= Config.MIN_REVIEW_COUNT]

# # # #     places.sort(key=lambda p: _safe_get_count(p), reverse=True)
    
# # # #     # --- Step 1: Deduplication ---
# # # #     unique_places_map: Dict[str, Place] = {}
# # # #     processed_for_dupes = set()
# # # #     for i in range(len(places)):
# # # #         p1 = places[i]
# # # #         p1_id = p1.get('id')
# # # #         if p1_id in processed_for_dupes: continue
        
# # # #         # This is now the primary entry, add it to the map
# # # #         unique_places_map[p1_id] = p1
# # # #         processed_for_dupes.add(p1_id)

# # # #         for j in range(i + 1, len(places)):
# # # #             p2 = places[j]
# # # #             p2_id = p2.get('id')
# # # #             if p2_id in processed_for_dupes: continue
            
# # # #             name1 = get_simple_name(p1.get('displayName', {}).get('text', ''))
# # # #             name2 = get_simple_name(p2.get('displayName', {}).get('text', ''))
# # # #             ratio = SequenceMatcher(None, name1, name2).ratio()
# # # #             dist = haversine_km(p1['location']['latitude'], p1['location']['longitude'], p2['location']['latitude'], p2['location']['longitude'])
            
# # # #             if ratio > 0.8 and dist < 0.5:
# # # #                 logging.info(f"Merging duplicate: '{p2['displayName']['text']}' into '{p1['displayName']['text']}'")
# # # #                 processed_for_dupes.add(p2_id)
    
# # # #     unique_places = list(unique_places_map.values())

# # # #     # --- Step 2: Hierarchical Grouping (Parent-Child) ---
# # # #     parent_keywords = {
# # # #         'national park': 50.0,
# # # #         'state park': 30.0,
# # # #         'seattle center': 1.0,
# # # #         'campus': 2.0,
# # # #         'center': 1.5,
# # # #     }
    
# # # #     potential_parents = []
# # # #     for p in unique_places:
# # # #         p_name = p.get('displayName', {}).get('text', '').lower()
# # # #         for keyword, radius in parent_keywords.items():
# # # #             if keyword in p_name:
# # # #                 potential_parents.append((p, radius))
# # # #                 break
    
# # # #     potential_parents.sort(key=lambda item: item[1], reverse=True)

# # # #     structured_list: List[Dict[str, Any]] = []
# # # #     assigned_place_ids = set()

# # # #     for parent, radius_km in potential_parents:
# # # #         if parent.get('id') in assigned_place_ids: continue
        
# # # #         parent_data = {"parent": parent, "children": []}
        
# # # #         for child in unique_places:
# # # #             child_id = child.get('id')
# # # #             if child_id == parent.get('id') or child_id in assigned_place_ids: continue

# # # #             dist = haversine_km(parent['location']['latitude'], parent['location']['longitude'], child['location']['latitude'], child['location']['longitude'])
            
# # # #             if dist < radius_km:
# # # #                 parent_data["children"].append(child)
# # # #                 assigned_place_ids.add(child_id)
        
# # # #         structured_list.append(parent_data)
# # # #         assigned_place_ids.add(parent.get('id'))

# # # #     for place in unique_places:
# # # #         if place.get('id') not in assigned_place_ids:
# # # #             structured_list.append({"parent": place, "children": []})

# # # #     # --- Step 3: Categorization ---
# # # #     final_categorized: Dict[str, List[Dict[str, Any]]] = {}
# # # #     for item in structured_list:
# # # #         category = get_category_from_place(item['parent'])
# # # #         if category not in final_categorized: final_categorized[category] = []
# # # #         final_categorized[category].append(item)
# # # #         item['children'].sort(key=lambda p: p.get('rank_score', 0), reverse=True)

# # # #     for category in final_categorized:
# # # #         final_categorized[category].sort(key=lambda item: item['parent'].get('rank_score', 0), reverse=True)

# # # #     return final_categorized

# # # # # =============================================================================
# # # # # MAIN FLOW & HELPERS
# # # # # =============================================================================
# # # # def enrich_subview_attractions(center_lat: float, center_lon: float, radius_km: float) -> List[Place]:
# # # #     results: Dict[str, Place] = {}
# # # #     pts = [(center_lat, center_lon, int(min(radius_km * 1000, Config.MAX_NEARBY_RADIUS_M)))]
# # # #     for lat, lon, radius_m in pts:
# # # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
# # # #         for p in places_nearby(lat, lon, radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION):
# # # #             if pid := p.get("id"): results[pid] = p
# # # #     return list(results.values())

# # # # def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# # # #     logging.info("Performing full adaptive search (this may take a moment)...")
# # # #     city_list, all_attractions, visual_quads = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km)
    
# # # #     if visual_quads:
# # # #         visualize_quadtree(visual_quads, center, search_radius_km)

# # # #     if all_attractions:
# # # #         logging.info("Calculating distance for all new attractions...")
# # # #         for att in all_attractions:
# # # #             if loc := att.get('location'):
# # # #                 att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
# # # #         logging.info("Calculating and adding rank scores before caching...")
# # # #         all_attractions = add_rank_scores_to_places(all_attractions)
# # # #         hub_name = normalize_city_name(user_query_city)
# # # #         PlaceIdCache.save_many(all_attractions, hub_name)
# # # #         PlaceIdCache.save_many(city_list, hub_name)
# # # #         centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
# # # #         new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
# # # #         CentralHubCache.save_hub(new_hub, all_attractions)
# # # #         logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
# # # #     return city_list, all_attractions

# # # # def main(user_query_city: str, search_radius_km: Optional[float] = None):
# # # #     if search_radius_km is None: search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
# # # #     logging.info(f"\n===== Searching for '{user_query_city}' =====")
# # # #     GeocodeCache.load(); CentralHubCache.load()
# # # #     center = geocode_city(user_query_city)
# # # #     if "error" in center:
# # # #         logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
# # # #         return

# # # #     matching_hub = CentralHubCache.find_matching_hub(center['latitude'], center['longitude'])
# # # #     city_list, all_attractions = [], []
# # # #     if matching_hub:
# # # #         logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
# # # #         tracker.count_cache_hit()
# # # #         city_list = matching_hub.cities
# # # #         all_attractions = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # # #         normalized_query_name = normalize_city_name(user_query_city)
# # # #         if normalized_query_name != matching_hub.hub_name:
# # # #             radius_km = Config.SUBVIEW_RADIUS_KM
# # # #             all_attractions = [att for att in all_attractions if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # # #             logging.info(f"Filtered {len(all_attractions)} attractions within {radius_km} km of {user_query_city}.")
# # # #             if len(all_attractions) < Config.SUBVIEW_MIN_TARGET:
# # # #                 logging.info(f"No/low results for {user_query_city} in hub; enriching subview...")
# # # #                 newly_found = enrich_subview_attractions(center["latitude"], center["longitude"], radius_km)
# # # #                 if newly_found:
# # # #                     PlaceIdCache.save_many(newly_found, matching_hub.hub_name)
# # # #                     hub_all = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # # #                     merged_by_id = {p["id"]: p for p in hub_all if p.get("id")}
# # # #                     for p in newly_found:
# # # #                         if pid := p.get("id"): merged_by_id[pid] = p
# # # #                     merged = list(merged_by_id.values())
# # # #                     CentralHubCache.save_hub(matching_hub, merged)
# # # #                     all_attractions = [att for att in merged if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # # #                     logging.info(f"Subview enrichment added {len(newly_found)}; now {len(all_attractions)} within {radius_km} km.")
# # # #     else:
# # # #         logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
# # # #         city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km)

# # # #     if not all_attractions:
# # # #         logging.warning("No attractions found.")
# # # #         return

# # # #     for att in all_attractions:
# # # #         if loc := att.get('location'):
# # # #             att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    
# # # #     logging.info(f"\nFound {len(all_attractions)} total attractions. Now structuring and categorizing...")
# # # #     categorized_results = structure_and_categorize_places(all_attractions)

# # # #     visualize_final_tree(categorized_results, user_query_city)

# # # #     print("\n" + "="*50)
# # # #     print(f" ✨ Curated Attractions for {user_query_city} ✨")
# # # #     print("="*50)

# # # #     # Dynamically iterate over sorted category keys
# # # #     for category in sorted(categorized_results.keys()):
# # # #         items = categorized_results[category]
# # # #         print(f"\n--- 🏛️ {category} ---")
        
# # # #         for item in items:
# # # #             parent = item['parent']
# # # #             children = item['children']
# # # #             p_name = parent.get("displayName", {}).get("text", "<unknown>")
# # # #             p_rating = parent.get("rating", "N/A")
# # # #             p_cnt = _safe_get_count(parent)
# # # #             p_dist = parent.get('distance_to_query', -1)
            
# # # #             print(f"\n📍 {p_name} (Rating: {p_rating}, {p_cnt:,} reviews) - {p_dist:.1f} km away")

# # # #             if children:
# # # #                 print("   Includes:")
# # # #                 for child in children[:5]: # Limit to top 5 children
# # # #                     c_name = child.get("displayName", {}).get("text", "<unknown>")
# # # #                     c_rating = child.get("rating", "N/A")
# # # #                     c_cnt = _safe_get_count(child)
# # # #                     print(f"   - {c_name} (Rating: {c_rating}, {c_cnt:,} reviews)")

# # # # # =============================================================================
# # # # # RUNNER
# # # # # =============================================================================
# # # # if __name__ == "__main__":
# # # #     if not Config.API_KEY:
# # # #         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

# # # #     try:
# # # #         main("seattle")
# # # #         print("\n" + "#"*60 + "\n")
# # # #         main("bangkok")
# # # #     except Exception as e:
# # # #         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
    
# # # #     s = tracker.summary()
# # # #     print("\n" + "="*50 + "\n" + " "*17 + "SESSION SUMMARY" + "\n" + "="*50)
# # # #     print(f"Total Time Taken: {s['total_time_seconds']} seconds")
# # # #     print(f"Total API Calls:  {s['total_api_calls']}")
# # # #     print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
# # # #     print(f"  - Places:       {s['breakdown'].get('places', 0)}")
# # # #     print(f"Cache Hits:       {s['cache_hits']}")
# # # #     print("="*50)


# # # import os
# # # import re
# # # import json
# # # import math
# # # import time
# # # import logging
# # # import threading
# # # import unicodedata
# # # import concurrent.futures
# # # import sqlite3
# # # import hashlib
# # # import random
# # # from dataclasses import dataclass, field
# # # from collections import deque
# # # from pathlib import Path
# # # from typing import Any, Dict, List, Optional, Tuple, TypedDict
# # # from difflib import SequenceMatcher

# # # import requests
# # # from dotenv import load_dotenv

# # # try:
# # #     from scipy.spatial import KDTree
# # #     HAS_SCIPY = True
# # # except ImportError:
# # #     HAS_SCIPY = False

# # # # =============================================================================
# # # # INITIALIZATION
# # # # =============================================================================
# # # logging.basicConfig(
# # #     level=logging.INFO,
# # #     format='%(asctime)s - %(levelname)s - %(message)s'
# # # )

# # # # =============================================================================
# # # # TYPE DEFINITIONS
# # # # =============================================================================
# # # class Location(TypedDict):
# # #     latitude: float
# # #     longitude: float

# # # class DisplayName(TypedDict):
# # #     text: str
# # #     languageCode: str

# # # class Place(TypedDict, total=False):
# # #     id: str
# # #     location: Location
# # #     displayName: DisplayName
# # #     types: List[str]
# # #     rating: float
# # #     userRatingCount: int
# # #     thumbnailUrl: str
# # #     popularityScore: float
# # #     distance_to_query: float
# # #     formattedAddress: str
# # #     photos: List[Dict]
# # #     rank_score: float

# # # # =============================================================================
# # # # CONFIGURATION
# # # # =============================================================================
# # # class Config:
# # #     load_dotenv()
# # #     API_KEY = os.environ.get("GOOGLE_API_KEY")

# # #     # Storage
# # #     DB_DIR = Path("./adaptive_database")
# # #     GEOCODE_DIR = Path("./geocode_database")
# # #     CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
# # #     HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
# # #     TILE_DIR = DB_DIR / "tiles"
# # #     GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
# # #     PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
# # #     TTL_30D = 2_592_000

# # #     # Places API
# # #     MAX_NEARBY_RADIUS_M = 50_000
# # #     MAX_WORKERS = 16
# # #     PLACES_CALL_BUDGET: Optional[int] = 7 # Increased budget for more comprehensive search
# # #     PAGINATE: bool = True
# # #     MAX_RETRIES = 3
# # #     TYPE_CITY = ("locality",)
# # #     TYPE_ATTRACTION = ("tourist_attraction",)
# # #     MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
# # #     MASK_ATTRACTION = "places.id,places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.photos"

# # #     # Quadtree
# # #     DEFAULT_SEARCH_RADIUS_KM = 120
# # #     QT_MAX_DEPTH = 4
# # #     QT_SPLIT_THRESHOLD = 40
# # #     QT_MIN_EDGE_KM = 25.0
# # #     TWO_PHASE_NODE: bool = True
    
# # #     # Subview (for cache hits)
# # #     SUBVIEW_RADIUS_KM = 50
# # #     SUBVIEW_MIN_TARGET = 20

# # #     # --- Search tuning ---
# # #     ADAPTIVE_RADIUS = True
# # #     ADAPTIVE_HIGH_THRESHOLD = 10
# # #     ADAPTIVE_LOW_THRESHOLD = 1
# # #     ADAPTIVE_SHRINK_FACTOR = 0.7
# # #     ADAPTIVE_EXPAND_FACTOR = 1.2

# # #     # Budget-aware planner
# # #     LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

# # #     # Reranking
# # #     RERANK_MODE = "hybrid"
# # #     MIN_REVIEW_COUNT = 1000
# # #     RATING_PRIOR_M = 5000
# # #     WILSON_Z = 1.96
# # #     DISTANCE_DECAY_KM = 50.0
# # #     COUNT_WEIGHT = 0.25
# # #     BAYES_WEIGHT = 0.35
# # #     WILSON_WEIGHT = 0.25
# # #     DIST_WEIGHT = 0.15
# # #     TOP_N = 20
# # #     FILTER_NON_LATIN_NAMES = False

# # # # --- Ensure Dirs ---
# # # for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
# # #     path.mkdir(exist_ok=True)

# # # # =============================================================================
# # # # API CALL TRACKING & CORE CLASSES
# # # # =============================================================================
# # # class APITracker:
# # #     def __init__(self):
# # #         self.lock = threading.Lock()
# # #         self.calls = {"geocode": 0, "places": 0}
# # #         self.cache_hits = 0
# # #         self.start_time = time.time()
# # #     def count_call(self, api_type: str):
# # #         with self.lock:
# # #             self.calls[api_type] = self.calls.get(api_type, 0) + 1
# # #     def get_calls(self, api_type: str) -> int:
# # #         with self.lock:
# # #             return self.calls.get(api_type, 0)
# # #     def count_cache_hit(self):
# # #         with self.lock:
# # #             self.cache_hits += 1
# # #     def summary(self) -> Dict[str, Any]:
# # #         with self.lock:
# # #             return {
# # #                 "total_api_calls": sum(self.calls.values()),
# # #                 "breakdown": dict(self.calls),
# # #                 "cache_hits": self.cache_hits,
# # #                 "total_time_seconds": round(time.time() - self.start_time, 2),
# # #             }
# # # tracker = APITracker()

# # # class GeocodeCache:
# # #     _db_path = Config.GEOCODE_DB_FILE
# # #     @classmethod
# # #     def _init_db(cls):
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             conn.execute("PRAGMA journal_mode=WAL;")
# # #             conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
# # #     @classmethod
# # #     def load(cls):
# # #         cls._init_db()
# # #     @classmethod
# # #     def get(cls, city_key: str) -> Optional[Dict[str, float]]:
# # #         cls._init_db()
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
# # #         return {"latitude": row[0], "longitude": row[1]} if row else None
# # #     @classmethod
# # #     def save(cls, city_key: str, location: Dict[str, float]):
# # #         cls._init_db()
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             conn.execute("""
# # #                 INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)
# # #                 ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp
# # #             """, (city_key, location["latitude"], location["longitude"], time.time()))

# # # class PlaceIdCache:
# # #     _db_path = Config.PLACE_ID_DB_FILE
# # #     @classmethod
# # #     def _init_db(cls):
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             conn.execute("PRAGMA journal_mode=WAL;")
# # #             conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
# # #             conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
# # #     @classmethod
# # #     def load(cls):
# # #         cls._init_db()
# # #     @classmethod
# # #     def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
# # #         cls._init_db()
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
# # #         return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
# # #     @classmethod
# # #     def save_many(cls, places: List[Place], hub_name: str):
# # #         cls._init_db()
# # #         records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
# # #         if not records: return
# # #         with sqlite3.connect(cls._db_path) as conn:
# # #             conn.executemany("""
# # #                 INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?)
# # #                 ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp
# # #             """, records)

# # # class DiskCache:
# # #     _tile_mem_cache: Dict[str, List[Place]] = {}
# # #     _mem_lock = threading.Lock()
# # #     @staticmethod
# # #     def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> str:
# # #         key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}"
# # #         return hashlib.sha1(key_string.encode()).hexdigest()
# # #     @staticmethod
# # #     def _tile_path(key: str) -> Path:
# # #         return Config.TILE_DIR / f"{key}.json"
# # #     @classmethod
# # #     def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> Optional[List[Place]]:
# # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # #         path = cls._tile_path(key)
# # #         with cls._mem_lock:
# # #             if key in cls._tile_mem_cache:
# # #                 tracker.count_cache_hit()
# # #                 return cls._tile_mem_cache[key]
# # #         if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
# # #             try:
# # #                 with open(path, "r", encoding="utf-8") as f:
# # #                     data = json.load(f)
# # #                 with cls._mem_lock:
# # #                     cls._tile_mem_cache[key] = data
# # #                 tracker.count_cache_hit()
# # #                 return data
# # #             except (json.JSONDecodeError, IOError):
# # #                 return None
# # #         return None
# # #     @classmethod
# # #     def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place]):
# # #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# # #         path = cls._tile_path(key)
# # #         try:
# # #             with open(path, "w", encoding="utf-8") as f:
# # #                 json.dump(places, f, ensure_ascii=False)
# # #         except IOError as e:
# # #             logging.warning(f"Failed to save tile {path}: {e}")
# # #         with cls._mem_lock:
# # #             cls._tile_mem_cache[key] = places

# # # # =============================================================================
# # # # UTILITIES & API HELPERS
# # # # =============================================================================
# # # def is_primarily_latin(text: str, threshold: float = 0.9) -> bool:
# # #     if not text:
# # #         return False
# # #     latin_chars, total_alnum = 0, 0
# # #     for char in text:
# # #         if char.isalnum():
# # #             total_alnum += 1
# # #             if 'a' <= char.lower() <= 'z' or '0' <= char <= '9':
# # #                 latin_chars += 1
# # #     if total_alnum == 0:
# # #         return True
# # #     return (latin_chars / total_alnum) >= threshold

# # # def normalize_city_name(s: str) -> str:
# # #     if not s:
# # #         return ""
# # #     s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
# # #     s = s.lower().strip()
# # #     s = re.sub(r"[^\w\s-]", "", s)
# # #     s = re.sub(r"\s+", " ", s)
# # #     return s.strip()

# # # def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
# # #     R = 6371.0
# # #     dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
# # #     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
# # #     return 2 * R * math.asin(math.sqrt(a))

# # # def km_to_deg_lat(km: float) -> float:
# # #     return km / 111.0

# # # def km_to_deg_lon(km: float, at_lat: float) -> float:
# # #     return km / (111.320 * math.cos(math.radians(at_lat)) + 1e-12)

# # # def get_simple_name(text: str) -> str:
# # #     """Normalizes a name for comparison by removing generic terms."""
# # #     if not text: return ""
# # #     text = text.lower()
# # #     text = text.replace('mt.', 'mount').replace('mt ', 'mount ')
# # #     generic_terms = ['park', 'center', 'museum', 'garden', 'lookout', 'trail', 'trailhead']
# # #     for term in generic_terms:
# # #         text = text.replace(term, '')
# # #     return re.sub(r'\s+', ' ', text).strip()

# # # def get_category_from_place(place: Place) -> str:
# # #     """Assigns a place to a predefined category based on its type and name."""
# # #     types = place.get('types', [])
# # #     name = place.get('displayName', {}).get('text', '').lower()
    
# # #     if 'beach' in types:
# # #         return "Beaches & Waterfront"
# # #     if 'historical_landmark' in types or 'historical_place' in types:
# # #         return "Historical Sites"
# # #     if 'buddhist_temple' in types or 'hindu_temple' in types or 'mosque' in types or 'church' in types:
# # #         return "Temples & Religious Sites"
# # #     if 'market' in types:
# # #         return "Shopping & Markets"
# # #     if 'zoo' in types or 'aquarium' in types: 
# # #         return "Zoos & Aquariums"
# # #     if 'museum' in types or 'art_gallery' in types: 
# # #         return "Museums & Culture"
# # #     if 'hike' in name or 'trail' in name or 'falls' in name or 'lookout' in name:
# # #         return "Parks & Hiking"
# # #     if 'park' in types or 'national_park' in types:
# # #         if 'stadium' not in types:
# # #             return "Parks & Hiking"
# # #     if 'stadium' in types: 
# # #         return "Venues & Stadiums"
# # #     if 'tourist_attraction' in types: 
# # #         return "Landmarks & Points of Interest"
    
# # #     return "Other Attractions"

# # # def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
# # #     url = "https://places.googleapis.com/v1/places:searchNearby"
# # #     for attempt in range(Config.MAX_RETRIES):
# # #         try:
# # #             resp = requests.post(url, json=payload, headers=headers, timeout=30)
# # #             if 500 <= resp.status_code < 600 or resp.status_code == 429:
# # #                 logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
# # #                 time.sleep((2 ** attempt) + random.random())
# # #                 continue
# # #             if resp.status_code != 200:
# # #                 logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
# # #             resp.raise_for_status()
# # #             return resp.json()
# # #         except requests.exceptions.RequestException as e:
# # #             logging.error(f"API request failed after {attempt + 1} attempts: {e}")
# # #             break
# # #     return None

# # # def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str) -> List[Place]:
# # #     if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # #         return []
# # #     cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask)
# # #     if cached is not None:
# # #         return cached

# # #     headers = { "Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask }
# # #     payload = {
# # #         "includedTypes": list(included_types),
# # #         "maxResultCount": 20,
# # #         "languageCode": "en",
# # #         "locationRestriction": {
# # #             "circle": {
# # #                 "center": {"latitude": lat, "longitude": lon},
# # #                 "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))
# # #             }
# # #         }
# # #     }

# # #     all_places: List[Place] = []
# # #     next_page_token = None
# # #     while True:
# # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # #             logging.warning("Places API budget exhausted during pagination.")
# # #             break
# # #         if next_page_token:
# # #             payload["pageToken"] = next_page_token
# # #             time.sleep(0.5 + random.random() * 0.5)

# # #         tracker.count_call("places")
# # #         data = _post_with_retry(payload, headers)
# # #         if not data or not data.get("places"):
# # #             break

# # #         current_places = data.get("places", [])
# # #         for p in current_places:
# # #             if p.get("photos") and len(p["photos"]) > 0:
# # #                 p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
# # #                 del p["photos"]
# # #         all_places.extend(current_places)
# # #         next_page_token = data.get("nextPageToken")
# # #         if not Config.PAGINATE or not next_page_token:
# # #             break

# # #     DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places)
# # #     return all_places

# # # def geocode_city(city_name: str) -> Dict[str, Any]:
# # #     normalized_name = normalize_city_name(city_name)
# # #     cached = GeocodeCache.get(normalized_name)
# # #     if cached:
# # #         tracker.count_cache_hit()
# # #         return cached
# # #     if not Config.API_KEY:
# # #         return {"error": "Google API key is not configured."}
# # #     tracker.count_call("geocode")
# # #     url = "https://maps.googleapis.com/maps/api/geocode/json"
# # #     try:
# # #         resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
# # #         resp.raise_for_status()
# # #         data = resp.json()
# # #         if data.get("status") == "OK":
# # #             loc = data["results"][0]["geometry"]["location"]
# # #             result = {"latitude": loc["lat"], "longitude": loc["lng"]}
# # #             GeocodeCache.save(normalized_name, result)
# # #             return result
# # #         return {"error": f"Geocoding API status: {data.get('status')}"}
# # #     except requests.exceptions.RequestException as e:
# # #         return {"error": f"Geocoding request failed: {e}"}

# # # # =============================================================================
# # # # QUADTREE ADAPTIVE SEARCH
# # # # =============================================================================
# # # @dataclass
# # # class Quadrant:
# # #     min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
# # #     @property
# # #     def center(self) -> Tuple[float, float]:
# # #         return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
# # #     @property
# # #     def edge_km(self) -> float:
# # #         return abs(self.max_lat - self.min_lat) * 111.0
# # #     @property
# # #     def inscribed_radius_m(self) -> int:
# # #         return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
# # #     def subdivide(self) -> List["Quadrant"]:
# # #         mid_lat, mid_lon = self.center; d = self.depth + 1
# # #         return [
# # #             Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d),
# # #             Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
# # #             Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d),
# # #             Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)
# # #         ]

# # # def get_budget_limit_for_depth(depth: int) -> int:
# # #     if Config.PLACES_CALL_BUDGET is None:
# # #         return float('inf')
    
# # #     total_budget = Config.PLACES_CALL_BUDGET
# # #     weights = Config.LEVEL_BUDGET_WEIGHTS
    
# # #     cumulative_weight = 0.0
# # #     for d in range(depth + 1):
# # #         cumulative_weight += weights.get(d, 0)

# # #     if depth not in weights and depth > max(weights.keys()):
# # #         remainder = max(0, 1.0 - sum(weights.values()))
# # #         cumulative_weight = sum(weights.values()) + remainder

# # #     final_cumulative_weight = min(1.0, cumulative_weight)

# # #     return max(1, int(total_budget * final_cumulative_weight))


# # # def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# # #     q = deque([Quadrant(center_lat - km_to_deg_lat(search_radius_km), center_lon - km_to_deg_lon(search_radius_km, center_lat), center_lat + km_to_deg_lat(search_radius_km), center_lon + km_to_deg_lon(search_radius_km, center_lat), 0)])
# # #     cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()
    
# # #     def process_quadrant(quad: Quadrant):
# # #         budget_limit = get_budget_limit_for_depth(quad.depth)
# # #         if tracker.get_calls("places") >= budget_limit:
# # #             if quad.depth < 2:
# # #                 logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
# # #             return None, None
        
# # #         can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
# # #         lat, lon = quad.center
        
# # #         base_radius_m = quad.inscribed_radius_m
# # #         node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY)
        
# # #         for c in node_cities:
# # #             if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
# # #                 GeocodeCache.save(normalize_city_name(name), loc)
        
# # #         attraction_radius_m = base_radius_m
# # #         if Config.ADAPTIVE_RADIUS:
# # #             if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD:
# # #                 attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
# # #             elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD:
# # #                 attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        
# # #         node_attrs: List[Place] = []
# # #         if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
# # #             node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION)
        
# # #         with lock:
# # #             for p in node_cities:
# # #                 if p_id := p.get("id"): cities[p_id] = p
# # #             for p in node_attrs:
# # #                 if p_id := p.get("id"): attractions[p_id] = p
        
# # #         if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD:
# # #             return quad.subdivide(), quad.depth
# # #         return None, quad.depth

# # #     while q:
# # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# # #             break
# # #         current_depth = q[0].depth
# # #         level_size = len(q)
# # #         logging.info(f"Processing level {current_depth} with {level_size} quadrants...")
        
# # #         quadrants_to_process = [q.popleft() for _ in range(level_size)]
# # #         with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
# # #             future_to_quad = {executor.submit(process_quadrant, quad): quad for quad in quadrants_to_process}
# # #             for future in concurrent.futures.as_completed(future_to_quad):
# # #                 try:
# # #                     if (result := future.result()) and (children := result[0]):
# # #                         q.extend(children)
# # #                 except Exception as e:
# # #                     logging.error(f"A quadrant processing task failed: {e}")
# # #     return list(cities.values()), list(attractions.values())

# # # # =============================================================================
# # # # HUB CACHE & RANKING
# # # # =============================================================================
# # # @dataclass
# # # class HubEntry:
# # #     hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)

# # # def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
# # #     if not places: return {"latitude": 0, "longitude": 0}, 0
# # #     lats = [p['location']['latitude'] for p in places if 'location' in p]
# # #     lngs = [p['location']['longitude'] for p in places if 'location' in p]
# # #     if not lats: return {"latitude": 0, "longitude": 0}, 0
# # #     centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
# # #     max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
# # #     return centroid, max_dist * 1.05

# # # class CentralHubCache:
# # #     _hubs: Dict[str, HubEntry] = {}
# # #     @classmethod
# # #     def load(cls):
# # #         if not Config.CENTRAL_HUB_FILE.exists(): return
# # #         try:
# # #             with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f:
# # #                 cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
# # #             logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
# # #         except Exception as e:
# # #             logging.error(f"Could not load central hub cache: {e}")
# # #     @classmethod
# # #     def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
# # #         for hub in cls._hubs.values():
# # #             if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km:
# # #                 return hub
# # #         return None
# # #     @classmethod
# # #     def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
# # #         path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
# # #         if not path.exists(): return None
# # #         try:
# # #             with open(path, "r", encoding="utf-8") as f:
# # #                 return json.load(f)
# # #         except Exception as e:
# # #             logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
# # #             return None
# # #     @classmethod
# # #     def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
# # #         cls._hubs[hub_entry.hub_name] = hub_entry
# # #         for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
# # #             temp_path = path.with_suffix(f"{path.suffix}.tmp")
# # #             try:
# # #                 with open(temp_path, "w", encoding="utf-8") as f:
# # #                     json.dump(data, f, ensure_ascii=False, indent=4)
# # #                 os.replace(temp_path, path)
# # #             except IOError as e:
# # #                 logging.error(f"Could not save hub file {path}: {e}")

# # # def _safe_get_rating(p: Dict) -> Optional[float]:
# # #     try: return float(p.get("rating")) if p.get("rating") is not None else None
# # #     except (ValueError, TypeError): return None
# # # def _safe_get_count(p: Dict) -> int:
# # #     try: return int(p.get("userRatingCount", 0) or 0)
# # #     except (ValueError, TypeError): return 0
# # # def _global_mean_rating(places: List[Dict]) -> float:
# # #     vals = [_safe_get_rating(p) for p in places if _safe_get_rating(p) is not None]
# # #     return (sum(vals) / len(vals)) if vals else 3.5
# # # def _bayes_score(R: float, v: int, C: float, m: int) -> float:
# # #     return (v * R + m * C) / (v + m) if (v + m) > 0 else C
# # # def _wilson_lower_bound(p: float, n: int, z: float) -> float:
# # #     if n <= 0: return 0.0
# # #     denom = 1 + z*z/n
# # #     center = p + z*z/(2*n)
# # #     margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
# # #     return max(0.0, (center - margin) / denom)

# # # def rerank_places(places: List[Place], top_n: int = Config.TOP_N) -> List[Place]:
# # #     if not places: return []
# # #     mode, m, z, decay_km = Config.RERANK_MODE, Config.RATING_PRIOR_M, Config.WILSON_Z, Config.DISTANCE_DECAY_KM
# # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# # #     C = _global_mean_rating(places)
# # #     max_v = max([_safe_get_count(p) for p in places] + [1])
# # #     scored = []
# # #     for p in places:
# # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# # #         if R is None: continue
# # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # #         count_factor = math.log1p(v) / math.log1p(max_v)

# # #         if mode == "bayes": final_score = bayes_n
# # #         elif mode == "wilson": final_score = wilson
# # #         else: final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # #         p["rank_score"] = final_score
# # #         scored.append(p)

# # #     scored.sort(key=lambda x: (-x.get("rank_score", 0.0), x.get("distance_to_query", float("inf")), -_safe_get_count(x), -(_safe_get_rating(x) or 0.0)))
# # #     return scored[:top_n]

# # # def group_attractions_by_nearest_city(attractions: List[Place], cities: List[Place]) -> Dict[str, List[Place]]:
# # #     grouped: Dict[str, List[Place]] = {}
# # #     if not cities or not attractions: return grouped
# # #     cities_with_loc = [c for c in cities if 'location' in c]
# # #     if not cities_with_loc: return grouped
# # #     if HAS_SCIPY:
# # #         city_coords = [[c['location']['latitude'], c['location']['longitude']] for c in cities_with_loc]
# # #         tree = KDTree(city_coords)
# # #         for att in attractions:
# # #             if 'location' in att:
# # #                 _, idx = tree.query([att['location']['latitude'], att['location']['longitude']])
# # #                 name = cities_with_loc[idx].get("displayName", {}).get("text", "Unknown City")
# # #                 grouped.setdefault(name, []).append(att)
# # #     else:
# # #         for att in attractions:
# # #             if 'location' not in att: continue
# # #             best_d, best_c_name = float("inf"), "Unknown City"
# # #             for c in cities_with_loc:
# # #                 d = haversine_km(att['location']['latitude'], att['location']['longitude'], c['location']['latitude'], c['location']['longitude'])
# # #                 if d < best_d:
# # #                     best_d, best_c_name = d, c.get("displayName", {}).get("text", "Unknown City")
# # #             grouped.setdefault(best_c_name, []).append(att)
# # #     return grouped

# # # def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
# # #     if not places: return []
# # #     m, z = Config.RATING_PRIOR_M, Config.WILSON_Z
# # #     decay_km = Config.DISTANCE_DECAY_KM
# # #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# # #     C = _global_mean_rating(places)
# # #     max_v = max([_safe_get_count(p) for p in places] + [1])
# # #     for p in places:
# # #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# # #         if R is None: 
# # #             p["rank_score"] = 0.0
# # #             continue
# # #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# # #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# # #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# # #         count_factor = math.log1p(v) / math.log1p(max_v)
# # #         final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# # #         p["rank_score"] = final_score
# # #     return places

# # # def structure_and_categorize_places(places: List[Place]) -> Dict[str, List[Dict[str, Any]]]:
# # #     """
# # #     Deduplicates, groups, and categorizes a list of places, creating a tree structure.
# # #     Every place gets its own card, even if it's also a child.
# # #     """
# # #     if not places: return {}
    
# # #     # --- Step 1: Filter and Deduplicate ---
# # #     places = [p for p in places if _safe_get_count(p) >= Config.MIN_REVIEW_COUNT]
# # #     places.sort(key=lambda p: _safe_get_count(p), reverse=True)
    
# # #     unique_places_map: Dict[str, Place] = {}
# # #     processed_for_dupes = set()
# # #     for i in range(len(places)):
# # #         p1 = places[i]
# # #         p1_id = p1.get('id')
# # #         if p1_id in processed_for_dupes: continue
        
# # #         unique_places_map[p1_id] = p1
# # #         processed_for_dupes.add(p1_id)

# # #         for j in range(i + 1, len(places)):
# # #             p2 = places[j]
# # #             p2_id = p2.get('id')
# # #             if p2_id in processed_for_dupes: continue
            
# # #             name1 = get_simple_name(p1.get('displayName', {}).get('text', ''))
# # #             name2 = get_simple_name(p2.get('displayName', {}).get('text', ''))
# # #             ratio = SequenceMatcher(None, name1, name2).ratio()
# # #              # Ensure locations exist before calculating distance
# # #             if 'location' not in p1 or 'location' not in p2: continue
# # #             dist = haversine_km(p1['location']['latitude'], p1['location']['longitude'], p2['location']['latitude'], p2['location']['longitude'])
            
# # #             if ratio > 0.8 and dist < 0.5:
# # #                 logging.info(f"Merging duplicate: '{p2['displayName']['text']}' into '{p1['displayName']['text']}'")
# # #                 processed_for_dupes.add(p2_id)
    
# # #     unique_places = list(unique_places_map.values())

# # #     # --- Step 2: Hierarchical Grouping (Parent-Child) ---
# # #     parent_keywords = {
# # #         'national park': 50.0, 'state park': 30.0, 'seattle center': 1.0, 
# # #         'campus': 2.0, 'center': 1.5,
# # #     }
    
# # #     structured_list: List[Dict[str, Any]] = [{"parent": p, "children": []} for p in unique_places]
    
# # #     for item in structured_list:
# # #         parent = item['parent']
# # #         p_name = parent.get('displayName', {}).get('text', '').lower()
        
# # #         for keyword, radius_km in parent_keywords.items():
# # #             if keyword in p_name:
# # #                 for other_item in structured_list:
# # #                     child = other_item['parent']
# # #                     if parent['id'] == child['id']: continue

# # #                     dist = haversine_km(parent['location']['latitude'], parent['location']['longitude'], child['location']['latitude'], child['location']['longitude'])
                    
# # #                     if dist < radius_km:
# # #                         item['children'].append(child)
                
# # #                 item['children'].sort(key=lambda p: p.get('rank_score', 0), reverse=True)
# # #                 break 

# # #     # --- Step 3: Categorization ---
# # #     final_categorized: Dict[str, List[Dict[str, Any]]] = {}
# # #     for item in structured_list:
# # #         category = get_category_from_place(item['parent'])
# # #         if category not in final_categorized: final_categorized[category] = []
# # #         final_categorized[category].append(item)

# # #     for category in final_categorized:
# # #         final_categorized[category].sort(key=lambda i: i['parent'].get('rank_score', 0), reverse=True)

# # #     return final_categorized

# # # def generate_html_report(categorized_data: Dict[str, List[Dict[str, Any]]], city_name: str, filename="attractions_report.html"):
# # #     """
# # #     Generates a beautiful HTML report with a grid layout.
# # #     MODIFIED: This version will not display the "Includes:" section.
# # #     """
    
# # #     html_content = f"""
# # #     <!DOCTYPE html>
# # #     <html lang="en">
# # #     <head>
# # #         <meta charset="UTF-8">
# # #         <meta name="viewport" content="width=device-width, initial-scale=1.0">
# # #         <title>Attractions in {city_name.title()}</title>
# # #         <style>
# # #             body {{
# # #                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
# # #                 margin: 0;
# # #                 background-color: #f7f8fc;
# # #                 color: #333;
# # #             }}
# # #             .container {{
# # #                 max-width: 1200px;
# # #                 margin: 20px auto;
# # #                 padding: 20px;
# # #             }}
# # #             h1 {{
# # #                 color: #1a1a1a;
# # #                 text-align: center;
# # #                 border-bottom: 2px solid #eee;
# # #                 padding-bottom: 20px;
# # #                 margin-bottom: 30px;
# # #             }}
# # #             h2 {{
# # #                 color: #0056b3;
# # #                 border-bottom: 1px solid #ddd;
# # #                 padding-bottom: 8px;
# # #                 margin-top: 40px;
# # #             }}
# # #             .category-grid {{
# # #                 display: grid;
# # #                 grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
# # #                 gap: 25px;
# # #             }}
# # #             .attraction-card {{
# # #                 background-color: #fff;
# # #                 border-radius: 12px;
# # #                 box-shadow: 0 4px 12px rgba(0,0,0,0.08);
# # #                 transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
# # #                 overflow: hidden;
# # #                 display: flex;
# # #                 flex-direction: column;
# # #             }}
# # #             .attraction-card:hover {{
# # #                 transform: translateY(-5px);
# # #                 box-shadow: 0 8px 20px rgba(0,0,0,0.12);
# # #             }}
# # #             .card-image img {{
# # #                 width: 100%;
# # #                 height: 200px;
# # #                 object-fit: cover;
# # #             }}
# # #             .card-content {{
# # #                 padding: 20px;
# # #                 display: flex;
# # #                 flex-direction: column;
# # #                 flex-grow: 1;
# # #             }}
# # #             .card-content h3 {{
# # #                 margin: 0 0 10px 0;
# # #                 font-size: 1.25em;
# # #                 color: #222;
# # #             }}
# # #             .card-content p {{
# # #                 margin: 0 0 15px 0;
# # #                 color: #666;
# # #                 font-size: 0.95em;
# # #                 line-height: 1.5;
# # #             }}
# # #             .score-badge {{
# # #                 color: #fff;
# # #                 padding: 6px 12px;
# # #                 border-radius: 20px;
# # #                 font-weight: bold;
# # #                 font-size: 0.9em;
# # #                 margin-top: auto;
# # #                 align-self: flex-start;
# # #             }}
# # #             .expert-choice {{ background-color: #28a745; }}
# # #             .regular-score {{ background-color: #007bff; }}
# # #         </style>
# # #     </head>
# # #     <body>
# # #         <div class="container">
# # #             <h1>Curated Attractions for {city_name.title()}</h1>
# # #     """

# # #     for category in sorted(categorized_data.keys()):
# # #         html_content += f"<h2>{category}</h2><div class='category-grid'>"
# # #         for item in categorized_data[category]:
# # #             parent = item['parent']
# # #             p_name = parent.get("displayName", {}).get("text", "Unknown")
# # #             p_rating = parent.get("rating", "N/A")
# # #             p_cnt = _safe_get_count(parent)
# # #             p_score = parent.get("rank_score", 0.0)
# # #             expert_score = int(p_score * 100)
# # #             p_thumb = parent.get("thumbnailUrl", "https://placehold.co/400x300/eee/333?text=No+Image")
            
# # #             score_badge_html = ""
# # #             if p_score > 0.85:
# # #                 score_badge_html = "<div class='score-badge expert-choice'>🏆 Top Expert Choice</div>"
# # #             else:
# # #                 score_badge_html = f"<div class='score-badge regular-score'>Expert Score: {expert_score}%</div>"

# # #             html_content += f"""
# # #             <div class="attraction-card">
# # #                 <div class="card-image">
# # #                     <img src="{p_thumb}" alt="{p_name}">
# # #                 </div>
# # #                 <div class="card-content">
# # #                     <h3>{p_name}</h3>
# # #                     <p>Rating: {p_rating} ★ ({p_cnt:,} reviews)</p>
# # #                     {score_badge_html}
# # #                 </div>
# # #             </div>
# # #             """
# # #             # NOTE: The block for rendering children has been removed to keep the UI flat.
# # #         html_content += "</div>" # Close category-grid

# # #     html_content += """
# # #         </div>
# # #     </body>
# # #     </html>
# # #     """
# # #     try:
# # #         with open(filename, "w", encoding="utf-8") as f:
# # #             f.write(html_content)
# # #         logging.info(f"HTML report saved to {filename}")
# # #     except IOError as e:
# # #         logging.error(f"Could not save HTML report: {e}")

# # # # =============================================================================
# # # # MAIN FLOW & HELPERS
# # # # =============================================================================
# # # def enrich_subview_attractions(center_lat: float, center_lon: float, radius_km: float) -> List[Place]:
# # #     results: Dict[str, Place] = {}
# # #     pts = [(center_lat, center_lon, int(min(radius_km * 1000, Config.MAX_NEARBY_RADIUS_M)))]
# # #     for lat, lon, radius_m in pts:
# # #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
# # #         for p in places_nearby(lat, lon, radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION):
# # #             if pid := p.get("id"): results[pid] = p
# # #     return list(results.values())

# # # def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# # #     logging.info("Performing full adaptive search (this may take a moment)...")
# # #     city_list, all_attractions = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km)
    
# # #     if all_attractions:
# # #         logging.info("Calculating distance for all new attractions...")
# # #         for att in all_attractions:
# # #             if loc := att.get('location'):
# # #                 att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
# # #         logging.info("Calculating and adding rank scores before caching...")
# # #         all_attractions = add_rank_scores_to_places(all_attractions)
# # #         hub_name = normalize_city_name(user_query_city)
# # #         PlaceIdCache.save_many(all_attractions, hub_name)
# # #         PlaceIdCache.save_many(city_list, hub_name)
# # #         centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
# # #         new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
# # #         CentralHubCache.save_hub(new_hub, all_attractions)
# # #         logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
# # #     return city_list, all_attractions

# # # def main(user_query_city: str, search_radius_km: Optional[float] = None):
# # #     if search_radius_km is None: search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
# # #     logging.info(f"\n===== Searching for '{user_query_city}' =====")
    
# # #     global tracker
# # #     tracker = APITracker()

# # #     GeocodeCache.load(); CentralHubCache.load()
# # #     center = geocode_city(user_query_city)
# # #     if "error" in center:
# # #         logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
# # #         return

# # #     matching_hub = CentralHubCache.find_matching_hub(center['latitude'], center['longitude'])
# # #     city_list, all_attractions = [], []
# # #     if matching_hub:
# # #         logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
# # #         tracker.count_cache_hit()
# # #         city_list = matching_hub.cities
# # #         all_attractions = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # #         normalized_query_name = normalize_city_name(user_query_city)
# # #         if normalized_query_name != matching_hub.hub_name:
# # #             radius_km = Config.SUBVIEW_RADIUS_KM
# # #             all_attractions = [att for att in all_attractions if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # #             logging.info(f"Filtered {len(all_attractions)} attractions within {radius_km} km of {user_query_city}.")
# # #             if len(all_attractions) < Config.SUBVIEW_MIN_TARGET:
# # #                 logging.info(f"No/low results for {user_query_city} in hub; enriching subview...")
# # #                 newly_found = enrich_subview_attractions(center["latitude"], center["longitude"], radius_km)
# # #                 if newly_found:
# # #                     PlaceIdCache.save_many(newly_found, matching_hub.hub_name)
# # #                     hub_all = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# # #                     merged_by_id = {p["id"]: p for p in hub_all if p.get("id")}
# # #                     for p in newly_found:
# # #                         if pid := p.get("id"): merged_by_id[pid] = p
# # #                     merged = list(merged_by_id.values())
# # #                     CentralHubCache.save_hub(matching_hub, merged)
# # #                     all_attractions = [att for att in merged if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# # #                     logging.info(f"Subview enrichment added {len(newly_found)}; now {len(all_attractions)} within {radius_km} km.")
# # #     else:
# # #         logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
# # #         city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km)

# # #     if not all_attractions:
# # #         logging.warning("No attractions found.")
# # #         return

# # #     for att in all_attractions:
# # #         if loc := att.get('location'):
# # #             att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    
# # #     all_attractions = add_rank_scores_to_places(all_attractions)
    
# # #     logging.info(f"\nFound {len(all_attractions)} total attractions. Now structuring and categorizing...")
# # #     categorized_results = structure_and_categorize_places(all_attractions)

# # #     # --- Generate Outputs ---
# # #     generate_html_report(categorized_results, user_query_city)
# # #     try:
# # #         with open("attractions_output.json", "w", encoding="utf-8") as f:
# # #             json.dump(categorized_results, f, ensure_ascii=False, indent=4)
# # #         logging.info("JSON output saved to attractions_output.json")
# # #     except IOError as e:
# # #         logging.error(f"Could not save JSON output: {e}")

# # #     print("\n" + "="*50)
# # #     print(f" ✨ Curated Attractions for {user_query_city} ✨")
# # #     print("="*50)

# # #     # Dynamically iterate over sorted category keys
# # #     for category in sorted(categorized_results.keys()):
# # #         items = categorized_results[category]
# # #         print(f"\n--- 🏛️ {category} ---")
        
# # #         for item in items:
# # #             parent = item['parent']
# # #             p_name = parent.get("displayName", {}).get("text", "<unknown>")
# # #             p_rating = parent.get("rating", "N/A")
# # #             p_cnt = _safe_get_count(parent)
# # #             p_dist = parent.get('distance_to_query', -1)
            
# # #             # MODIFIED: Print each item directly without an "Includes" section.
# # #             print(f"\n📍 {p_name} (Rating: {p_rating}, {p_cnt:,} reviews) - {p_dist:.1f} km away")
    
# # #     s = tracker.summary()
# # #     print("\n" + "="*50 + "\n" + f"SESSION SUMMARY for {user_query_city.title()}" + "\n" + "="*50)
# # #     print(f"Total Time Taken: {s['total_time_seconds']} seconds")
# # #     print(f"Total API Calls:  {s['total_api_calls']}")
# # #     print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
# # #     print(f"  - Places:       {s['breakdown'].get('places', 0)}")
# # #     print(f"Cache Hits:       {s['cache_hits']}")
# # #     print("="*50)


# # # # =============================================================================
# # # # RUNNER
# # # # =============================================================================
# # # if __name__ == "__main__":
# # #     if not Config.API_KEY:
# # #         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

# # #     try:
# # #         while True:
# # #             city = input("\nEnter a city name to search for (or 'quit' to exit): ")
# # #             if city.lower() in ['quit', 'exit']:
# # #                 break
# # #             if city:
# # #                 main(city)
# # #             else:
# # #                 print("Please enter a valid city name.")
# # #     except Exception as e:
# # #         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)


# # import os
# # import re
# # import json
# # import math
# # import time
# # import logging
# # import threading
# # import unicodedata
# # import concurrent.futures
# # import sqlite3
# # import hashlib
# # import random
# # from dataclasses import dataclass, field
# # from collections import deque
# # from pathlib import Path
# # from typing import Any, Dict, List, Optional, Tuple, TypedDict
# # from difflib import SequenceMatcher

# # import requests
# # from dotenv import load_dotenv

# # try:
# #     from scipy.spatial import KDTree
# #     HAS_SCIPY = True
# # except ImportError:
# #     HAS_SCIPY = False

# # # =============================================================================
# # # INITIALIZATION
# # # =============================================================================
# # logging.basicConfig(
# #     level=logging.INFO,
# #     format='%(asctime)s - %(levelname)s - %(message)s'
# # )

# # # =============================================================================
# # # TYPE DEFINITIONS
# # # =============================================================================
# # class Location(TypedDict):
# #     latitude: float
# #     longitude: float

# # class DisplayName(TypedDict):
# #     text: str
# #     languageCode: str

# # class Place(TypedDict, total=False):
# #     id: str
# #     location: Location
# #     displayName: DisplayName
# #     types: List[str]
# #     rating: float
# #     userRatingCount: int
# #     thumbnailUrl: str
# #     popularityScore: float
# #     distance_to_query: float
# #     formattedAddress: str
# #     photos: List[Dict]
# #     rank_score: float

# # # =============================================================================
# # # CONFIGURATION
# # # =============================================================================
# # class Config:
# #     load_dotenv()
# #     API_KEY = os.environ.get("GOOGLE_API_KEY")

# #     # Storage
# #     DB_DIR = Path("./adaptive_database_5")
# #     GEOCODE_DIR = Path("./geocode_database")
# #     CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
# #     HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
# #     TILE_DIR = DB_DIR / "tiles"
# #     GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
# #     PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
# #     TTL_30D = 2_592_000

# #     # Places API
# #     MAX_NEARBY_RADIUS_M = 50_000
# #     MAX_WORKERS = 16
# #     PLACES_CALL_BUDGET: Optional[int] = 7 # Increased budget for more comprehensive search
# #     PAGINATE: bool = True
# #     MAX_RETRIES = 3
# #     TYPE_CITY = ("locality",)
# #     TYPE_ATTRACTION = ("tourist_attraction",)
# #     MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
# #     # In your Config class, update MASK_ATTRACTION
# #     MASK_ATTRACTION = "places.id,places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.photos,places.editorialSummary,places.openingHours"

# #     # Quadtree
# #     DEFAULT_SEARCH_RADIUS_KM = 120
# #     QT_MAX_DEPTH = 4
# #     QT_SPLIT_THRESHOLD = 40
# #     QT_MIN_EDGE_KM = 25.0
# #     TWO_PHASE_NODE: bool = True
    
# #     # Subview (for cache hits)
# #     SUBVIEW_RADIUS_KM = 50
# #     SUBVIEW_MIN_TARGET = 20

# #     # --- Search tuning ---
# #     ADAPTIVE_RADIUS = True
# #     ADAPTIVE_HIGH_THRESHOLD = 10
# #     ADAPTIVE_LOW_THRESHOLD = 1
# #     ADAPTIVE_SHRINK_FACTOR = 0.7
# #     ADAPTIVE_EXPAND_FACTOR = 1.2

# #     # Budget-aware planner
# #     LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

# #     # Reranking
# #     RERANK_MODE = "hybrid"
# #     MIN_REVIEW_COUNT = 1000
# #     RATING_PRIOR_M = 5000
# #     WILSON_Z = 1.96
# #     DISTANCE_DECAY_KM = 50.0
# #     COUNT_WEIGHT = 0.25
# #     BAYES_WEIGHT = 0.35
# #     WILSON_WEIGHT = 0.25
# #     DIST_WEIGHT = 0.15
# #     TOP_N = 20
# #     FILTER_NON_LATIN_NAMES = False

# # # --- Ensure Dirs ---
# # for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
# #     path.mkdir(exist_ok=True)

# # # =============================================================================
# # # API CALL TRACKING & CORE CLASSES
# # # =============================================================================
# # class APITracker:
# #     def __init__(self):
# #         self.lock = threading.Lock()
# #         self.calls = {"geocode": 0, "places": 0}
# #         self.cache_hits = 0
# #         self.start_time = time.time()
# #     def count_call(self, api_type: str):
# #         with self.lock:
# #             self.calls[api_type] = self.calls.get(api_type, 0) + 1
# #     def get_calls(self, api_type: str) -> int:
# #         with self.lock:
# #             return self.calls.get(api_type, 0)
# #     def count_cache_hit(self):
# #         with self.lock:
# #             self.cache_hits += 1
# #     def summary(self) -> Dict[str, Any]:
# #         with self.lock:
# #             return {
# #                 "total_api_calls": sum(self.calls.values()),
# #                 "breakdown": dict(self.calls),
# #                 "cache_hits": self.cache_hits,
# #                 "total_time_seconds": round(time.time() - self.start_time, 2),
# #             }
# # tracker = APITracker()

# # class GeocodeCache:
# #     _db_path = Config.GEOCODE_DB_FILE
# #     @classmethod
# #     def _init_db(cls):
# #         with sqlite3.connect(cls._db_path) as conn:
# #             conn.execute("PRAGMA journal_mode=WAL;")
# #             conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
# #     @classmethod
# #     def load(cls):
# #         cls._init_db()
# #     @classmethod
# #     def get(cls, city_key: str) -> Optional[Dict[str, float]]:
# #         cls._init_db()
# #         with sqlite3.connect(cls._db_path) as conn:
# #             row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
# #         return {"latitude": row[0], "longitude": row[1]} if row else None
# #     @classmethod
# #     def save(cls, city_key: str, location: Dict[str, float]):
# #         cls._init_db()
# #         with sqlite3.connect(cls._db_path) as conn:
# #             conn.execute("""
# #                 INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)
# #                 ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp
# #             """, (city_key, location["latitude"], location["longitude"], time.time()))

# # class PlaceIdCache:
# #     _db_path = Config.PLACE_ID_DB_FILE
# #     @classmethod
# #     def _init_db(cls):
# #         with sqlite3.connect(cls._db_path) as conn:
# #             conn.execute("PRAGMA journal_mode=WAL;")
# #             conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
# #             conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
# #     @classmethod
# #     def load(cls):
# #         cls._init_db()
# #     @classmethod
# #     def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
# #         cls._init_db()
# #         with sqlite3.connect(cls._db_path) as conn:
# #             row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
# #         return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
# #     @classmethod
# #     def save_many(cls, places: List[Place], hub_name: str):
# #         cls._init_db()
# #         records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
# #         if not records: return
# #         with sqlite3.connect(cls._db_path) as conn:
# #             conn.executemany("""
# #                 INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?)
# #                 ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp
# #             """, records)

# # class DiskCache:
# #     _tile_mem_cache: Dict[str, List[Place]] = {}
# #     _mem_lock = threading.Lock()
# #     @staticmethod
# #     def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> str:
# #         key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}"
# #         return hashlib.sha1(key_string.encode()).hexdigest()
# #     @staticmethod
# #     def _tile_path(key: str) -> Path:
# #         return Config.TILE_DIR / f"{key}.json"
# #     @classmethod
# #     def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> Optional[List[Place]]:
# #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# #         path = cls._tile_path(key)
# #         with cls._mem_lock:
# #             if key in cls._tile_mem_cache:
# #                 tracker.count_cache_hit()
# #                 return cls._tile_mem_cache[key]
# #         if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
# #             try:
# #                 with open(path, "r", encoding="utf-8") as f:
# #                     data = json.load(f)
# #                 with cls._mem_lock:
# #                     cls._tile_mem_cache[key] = data
# #                 tracker.count_cache_hit()
# #                 return data
# #             except (json.JSONDecodeError, IOError):
# #                 return None
# #         return None
# #     @classmethod
# #     def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place]):
# #         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
# #         path = cls._tile_path(key)
# #         try:
# #             with open(path, "w", encoding="utf-8") as f:
# #                 json.dump(places, f, ensure_ascii=False)
# #         except IOError as e:
# #             logging.warning(f"Failed to save tile {path}: {e}")
# #         with cls._mem_lock:
# #             cls._tile_mem_cache[key] = places

# # # =============================================================================
# # # UTILITIES & API HELPERS
# # # =============================================================================
# # def is_primarily_latin(text: str, threshold: float = 0.9) -> bool:
# #     if not text:
# #         return False
# #     latin_chars, total_alnum = 0, 0
# #     for char in text:
# #         if char.isalnum():
# #             total_alnum += 1
# #             if 'a' <= char.lower() <= 'z' or '0' <= char <= '9':
# #                 latin_chars += 1
# #     if total_alnum == 0:
# #         return True
# #     return (latin_chars / total_alnum) >= threshold

# # def normalize_city_name(s: str) -> str:
# #     if not s:
# #         return ""
# #     s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
# #     s = s.lower().strip()
# #     s = re.sub(r"[^\w\s-]", "", s)
# #     s = re.sub(r"\s+", " ", s)
# #     return s.strip()

# # def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
# #     R = 6371.0
# #     dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
# #     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
# #     return 2 * R * math.asin(math.sqrt(a))

# # def km_to_deg_lat(km: float) -> float:
# #     return km / 111.0

# # def km_to_deg_lon(km: float, at_lat: float) -> float:
# #     return km / (111.320 * math.cos(math.radians(at_lat)) + 1e-12)

# # def get_simple_name(text: str) -> str:
# #     """Normalizes a name for comparison by removing generic terms."""
# #     if not text: return ""
# #     text = text.lower()
# #     text = text.replace('mt.', 'mount').replace('mt ', 'mount ')
# #     generic_terms = ['park', 'center', 'museum', 'garden', 'lookout', 'trail', 'trailhead']
# #     for term in generic_terms:
# #         text = text.replace(term, '')
# #     return re.sub(r'\s+', ' ', text).strip()

# # def get_category_from_place(place: Place) -> str:
# #     """Assigns a place to a predefined category based on its type and name."""
# #     types = place.get('types', [])
# #     name = place.get('displayName', {}).get('text', '').lower()
    
# #     if 'beach' in types:
# #         return "Beaches & Waterfront"
# #     if 'historical_landmark' in types or 'historical_place' in types:
# #         return "Historical Sites"
# #     if 'buddhist_temple' in types or 'hindu_temple' in types or 'mosque' in types or 'church' in types:
# #         return "Temples & Religious Sites"
# #     if 'market' in types:
# #         return "Shopping & Markets"
# #     if 'zoo' in types or 'aquarium' in types: 
# #         return "Zoos & Aquariums"
# #     if 'museum' in types or 'art_gallery' in types: 
# #         return "Museums & Culture"
# #     if 'hike' in name or 'trail' in name or 'falls' in name or 'lookout' in name:
# #         return "Parks & Hiking"
# #     if 'park' in types or 'national_park' in types:
# #         if 'stadium' not in types:
# #             return "Parks & Hiking"
# #     if 'stadium' in types: 
# #         return "Venues & Stadiums"
# #     if 'tourist_attraction' in types: 
# #         return "Landmarks & Points of Interest"
    
# #     return "Other Attractions"

# # def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
# #     url = "https://places.googleapis.com/v1/places:searchNearby"
# #     for attempt in range(Config.MAX_RETRIES):
# #         try:
# #             resp = requests.post(url, json=payload, headers=headers, timeout=30)
# #             if 500 <= resp.status_code < 600 or resp.status_code == 429:
# #                 logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
# #                 time.sleep((2 ** attempt) + random.random())
# #                 continue
# #             if resp.status_code != 200:
# #                 logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
# #             resp.raise_for_status()
# #             return resp.json()
# #         except requests.exceptions.RequestException as e:
# #             logging.error(f"API request failed after {attempt + 1} attempts: {e}")
# #             break
# #     return None

# # def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str) -> List[Place]:
# #     if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# #         return []
# #     cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask)
# #     if cached is not None:
# #         return cached

# #     headers = { "Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask }
# #     payload = {
# #         "includedTypes": list(included_types),
# #         "maxResultCount": 20,
# #         "languageCode": "en",
# #         "locationRestriction": {
# #             "circle": {
# #                 "center": {"latitude": lat, "longitude": lon},
# #                 "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))
# #             }
# #         }
# #     }

# #     all_places: List[Place] = []
# #     next_page_token = None
# #     while True:
# #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# #             logging.warning("Places API budget exhausted during pagination.")
# #             break
# #         if next_page_token:
# #             payload["pageToken"] = next_page_token
# #             time.sleep(0.5 + random.random() * 0.5)

# #         tracker.count_call("places")
# #         data = _post_with_retry(payload, headers)
# #         if not data or not data.get("places"):
# #             break

# #         current_places = data.get("places", [])
# #         for p in current_places:
# #             if p.get("photos") and len(p["photos"]) > 0:
# #                 p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
# #                 del p["photos"]
# #         all_places.extend(current_places)
# #         next_page_token = data.get("nextPageToken")
# #         if not Config.PAGINATE or not next_page_token:
# #             break

# #     DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places)
# #     return all_places

# # def geocode_city(city_name: str) -> Dict[str, Any]:
# #     normalized_name = normalize_city_name(city_name)
# #     cached = GeocodeCache.get(normalized_name)
# #     if cached:
# #         tracker.count_cache_hit()
# #         return cached
# #     if not Config.API_KEY:
# #         return {"error": "Google API key is not configured."}
# #     tracker.count_call("geocode")
# #     url = "https://maps.googleapis.com/maps/api/geocode/json"
# #     try:
# #         resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
# #         resp.raise_for_status()
# #         data = resp.json()
# #         if data.get("status") == "OK":
# #             loc = data["results"][0]["geometry"]["location"]
# #             result = {"latitude": loc["lat"], "longitude": loc["lng"]}
# #             GeocodeCache.save(normalized_name, result)
# #             return result
# #         return {"error": f"Geocoding API status: {data.get('status')}"}
# #     except requests.exceptions.RequestException as e:
# #         return {"error": f"Geocoding request failed: {e}"}

# # # =============================================================================
# # # QUADTREE ADAPTIVE SEARCH
# # # =============================================================================
# # @dataclass
# # class Quadrant:
# #     min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
# #     @property
# #     def center(self) -> Tuple[float, float]:
# #         return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
# #     @property
# #     def edge_km(self) -> float:
# #         return abs(self.max_lat - self.min_lat) * 111.0
# #     @property
# #     def inscribed_radius_m(self) -> int:
# #         return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
# #     def subdivide(self) -> List["Quadrant"]:
# #         mid_lat, mid_lon = self.center; d = self.depth + 1
# #         return [
# #             Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d),
# #             Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
# #             Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d),
# #             Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)
# #         ]

# # def get_budget_limit_for_depth(depth: int) -> int:
# #     if Config.PLACES_CALL_BUDGET is None:
# #         return float('inf')
    
# #     total_budget = Config.PLACES_CALL_BUDGET
# #     weights = Config.LEVEL_BUDGET_WEIGHTS
    
# #     cumulative_weight = 0.0
# #     for d in range(depth + 1):
# #         cumulative_weight += weights.get(d, 0)

# #     if depth not in weights and depth > max(weights.keys()):
# #         remainder = max(0, 1.0 - sum(weights.values()))
# #         cumulative_weight = sum(weights.values()) + remainder

# #     final_cumulative_weight = min(1.0, cumulative_weight)

# #     return max(1, int(total_budget * final_cumulative_weight))


# # def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# #     q = deque([Quadrant(center_lat - km_to_deg_lat(search_radius_km), center_lon - km_to_deg_lon(search_radius_km, center_lat), center_lat + km_to_deg_lat(search_radius_km), center_lon + km_to_deg_lon(search_radius_km, center_lat), 0)])
# #     cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()
    
# #     def process_quadrant(quad: Quadrant):
# #         budget_limit = get_budget_limit_for_depth(quad.depth)
# #         if tracker.get_calls("places") >= budget_limit:
# #             if quad.depth < 2:
# #                 logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
# #             return None, None
        
# #         can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
# #         lat, lon = quad.center
        
# #         base_radius_m = quad.inscribed_radius_m
# #         node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY)
        
# #         for c in node_cities:
# #             if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
# #                 GeocodeCache.save(normalize_city_name(name), loc)
        
# #         attraction_radius_m = base_radius_m
# #         if Config.ADAPTIVE_RADIUS:
# #             if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD:
# #                 attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
# #             elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD:
# #                 attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        
# #         node_attrs: List[Place] = []
# #         if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
# #             node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION)
        
# #         with lock:
# #             for p in node_cities:
# #                 if p_id := p.get("id"): cities[p_id] = p
# #             for p in node_attrs:
# #                 if p_id := p.get("id"): attractions[p_id] = p
        
# #         if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD:
# #             return quad.subdivide(), quad.depth
# #         return None, quad.depth

# #     while q:
# #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
# #             break
# #         current_depth = q[0].depth
# #         level_size = len(q)
# #         logging.info(f"Processing level {current_depth} with {level_size} quadrants...")
        
# #         quadrants_to_process = [q.popleft() for _ in range(level_size)]
# #         with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
# #             future_to_quad = {executor.submit(process_quadrant, quad): quad for quad in quadrants_to_process}
# #             for future in concurrent.futures.as_completed(future_to_quad):
# #                 try:
# #                     if (result := future.result()) and (children := result[0]):
# #                         q.extend(children)
# #                 except Exception as e:
# #                     logging.error(f"A quadrant processing task failed: {e}")
# #     return list(cities.values()), list(attractions.values())

# # # =============================================================================
# # # HUB CACHE & RANKING
# # # =============================================================================
# # @dataclass
# # class HubEntry:
# #     hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)

# # def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
# #     if not places: return {"latitude": 0, "longitude": 0}, 0
# #     lats = [p['location']['latitude'] for p in places if 'location' in p]
# #     lngs = [p['location']['longitude'] for p in places if 'location' in p]
# #     if not lats: return {"latitude": 0, "longitude": 0}, 0
# #     centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
# #     max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
# #     return centroid, max_dist * 1.05

# # class CentralHubCache:
# #     _hubs: Dict[str, HubEntry] = {}
# #     @classmethod
# #     def load(cls):
# #         if not Config.CENTRAL_HUB_FILE.exists(): return
# #         try:
# #             with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f:
# #                 cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
# #             logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
# #         except Exception as e:
# #             logging.error(f"Could not load central hub cache: {e}")
# #     @classmethod
# #     def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
# #         for hub in cls._hubs.values():
# #             if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km:
# #                 return hub
# #         return None
# #     @classmethod
# #     def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
# #         path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
# #         if not path.exists(): return None
# #         try:
# #             with open(path, "r", encoding="utf-8") as f:
# #                 return json.load(f)
# #         except Exception as e:
# #             logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
# #             return None
# #     @classmethod
# #     def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
# #         cls._hubs[hub_entry.hub_name] = hub_entry
# #         for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
# #             temp_path = path.with_suffix(f"{path.suffix}.tmp")
# #             try:
# #                 with open(temp_path, "w", encoding="utf-8") as f:
# #                     json.dump(data, f, ensure_ascii=False, indent=4)
# #                 os.replace(temp_path, path)
# #             except IOError as e:
# #                 logging.error(f"Could not save hub file {path}: {e}")

# # def _safe_get_rating(p: Dict) -> Optional[float]:
# #     try: return float(p.get("rating")) if p.get("rating") is not None else None
# #     except (ValueError, TypeError): return None
# # def _safe_get_count(p: Dict) -> int:
# #     try: return int(p.get("userRatingCount", 0) or 0)
# #     except (ValueError, TypeError): return 0
# # def _global_mean_rating(places: List[Dict]) -> float:
# #     vals = [_safe_get_rating(p) for p in places if _safe_get_rating(p) is not None]
# #     return (sum(vals) / len(vals)) if vals else 3.5
# # def _bayes_score(R: float, v: int, C: float, m: int) -> float:
# #     return (v * R + m * C) / (v + m) if (v + m) > 0 else C
# # def _wilson_lower_bound(p: float, n: int, z: float) -> float:
# #     if n <= 0: return 0.0
# #     denom = 1 + z*z/n
# #     center = p + z*z/(2*n)
# #     margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
# #     return max(0.0, (center - margin) / denom)

# # def rerank_places(places: List[Place], top_n: int = Config.TOP_N) -> List[Place]:
# #     if not places: return []
# #     mode, m, z, decay_km = Config.RERANK_MODE, Config.RATING_PRIOR_M, Config.WILSON_Z, Config.DISTANCE_DECAY_KM
# #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# #     C = _global_mean_rating(places)
# #     max_v = max([_safe_get_count(p) for p in places] + [1])
# #     scored = []
# #     for p in places:
# #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# #         if R is None: continue
# #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# #         count_factor = math.log1p(v) / math.log1p(max_v)

# #         if mode == "bayes": final_score = bayes_n
# #         elif mode == "wilson": final_score = wilson
# #         else: final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# #         p["rank_score"] = final_score
# #         scored.append(p)

# #     scored.sort(key=lambda x: (-x.get("rank_score", 0.0), x.get("distance_to_query", float("inf")), -_safe_get_count(x), -(_safe_get_rating(x) or 0.0)))
# #     return scored[:top_n]

# # def group_attractions_by_nearest_city(attractions: List[Place], cities: List[Place]) -> Dict[str, List[Place]]:
# #     grouped: Dict[str, List[Place]] = {}
# #     if not cities or not attractions: return grouped
# #     cities_with_loc = [c for c in cities if 'location' in c]
# #     if not cities_with_loc: return grouped
# #     if HAS_SCIPY:
# #         city_coords = [[c['location']['latitude'], c['location']['longitude']] for c in cities_with_loc]
# #         tree = KDTree(city_coords)
# #         for att in attractions:
# #             if 'location' in att:
# #                 _, idx = tree.query([att['location']['latitude'], att['location']['longitude']])
# #                 name = cities_with_loc[idx].get("displayName", {}).get("text", "Unknown City")
# #                 grouped.setdefault(name, []).append(att)
# #     else:
# #         for att in attractions:
# #             if 'location' not in att: continue
# #             best_d, best_c_name = float("inf"), "Unknown City"
# #             for c in cities_with_loc:
# #                 d = haversine_km(att['location']['latitude'], att['location']['longitude'], c['location']['latitude'], c['location']['longitude'])
# #                 if d < best_d:
# #                     best_d, best_c_name = d, c.get("displayName", {}).get("text", "Unknown City")
# #             grouped.setdefault(best_c_name, []).append(att)
# #     return grouped

# # def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
# #     if not places: return []
# #     m, z = Config.RATING_PRIOR_M, Config.WILSON_Z
# #     decay_km = Config.DISTANCE_DECAY_KM
# #     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
# #     C = _global_mean_rating(places)
# #     max_v = max([_safe_get_count(p) for p in places] + [1])
# #     for p in places:
# #         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
# #         if R is None: 
# #             p["rank_score"] = 0.0
# #             continue
# #         bayes_n = _bayes_score(R, v, C, m) / 5.0
# #         wilson = _wilson_lower_bound(R / 5.0, v, z)
# #         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
# #         count_factor = math.log1p(v) / math.log1p(max_v)
# #         final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
# #         p["rank_score"] = final_score
# #     return places

# # def structure_and_categorize_places(places: List[Place]) -> Dict[str, List[Dict[str, Any]]]:
# #     """
# #     Deduplicates, groups, and categorizes a list of places, creating a tree structure.
# #     Every place gets its own card, even if it's also a child.
# #     """
# #     if not places: return {}
    
# #     # --- Step 1: Filter and Deduplicate ---
# #     places = [p for p in places if _safe_get_count(p) >= Config.MIN_REVIEW_COUNT]
# #     places.sort(key=lambda p: _safe_get_count(p), reverse=True)
    
# #     unique_places_map: Dict[str, Place] = {}
# #     processed_for_dupes = set()
# #     for i in range(len(places)):
# #         p1 = places[i]
# #         p1_id = p1.get('id')
# #         if p1_id in processed_for_dupes: continue
        
# #         unique_places_map[p1_id] = p1
# #         processed_for_dupes.add(p1_id)

# #         for j in range(i + 1, len(places)):
# #             p2 = places[j]
# #             p2_id = p2.get('id')
# #             if p2_id in processed_for_dupes: continue
            
# #             name1 = get_simple_name(p1.get('displayName', {}).get('text', ''))
# #             name2 = get_simple_name(p2.get('displayName', {}).get('text', ''))
# #             ratio = SequenceMatcher(None, name1, name2).ratio()
# #              # Ensure locations exist before calculating distance
# #             if 'location' not in p1 or 'location' not in p2: continue
# #             dist = haversine_km(p1['location']['latitude'], p1['location']['longitude'], p2['location']['latitude'], p2['location']['longitude'])
            
# #             if ratio > 0.8 and dist < 0.5:
# #                 logging.info(f"Merging duplicate: '{p2['displayName']['text']}' into '{p1['displayName']['text']}'")
# #                 processed_for_dupes.add(p2_id)
    
# #     unique_places = list(unique_places_map.values())

# #     # --- Step 2: Hierarchical Grouping (Parent-Child) ---
# #     parent_keywords = {
# #         'national park': 50.0, 'state park': 30.0, 'seattle center': 1.0, 
# #         'campus': 2.0, 'center': 1.5,
# #     }
    
# #     structured_list: List[Dict[str, Any]] = [{"parent": p, "children": []} for p in unique_places]
    
# #     for item in structured_list:
# #         parent = item['parent']
# #         p_name = parent.get('displayName', {}).get('text', '').lower()
        
# #         for keyword, radius_km in parent_keywords.items():
# #             if keyword in p_name:
# #                 for other_item in structured_list:
# #                     child = other_item['parent']
# #                     if parent['id'] == child['id']: continue

# #                     dist = haversine_km(parent['location']['latitude'], parent['location']['longitude'], child['location']['latitude'], child['location']['longitude'])
                    
# #                     if dist < radius_km:
# #                         item['children'].append(child)
                
# #                 item['children'].sort(key=lambda p: p.get('rank_score', 0), reverse=True)
# #                 break 

# #     # --- Step 3: Categorization ---
# #     final_categorized: Dict[str, List[Dict[str, Any]]] = {}
# #     for item in structured_list:
# #         category = get_category_from_place(item['parent'])
# #         if category not in final_categorized: final_categorized[category] = []
# #         final_categorized[category].append(item)

# #     for category in final_categorized:
# #         final_categorized[category].sort(key=lambda i: i['parent'].get('rank_score', 0), reverse=True)

# #     return final_categorized

# # def generate_html_report(categorized_data: Dict[str, List[Dict[str, Any]]], city_name: str, filename="attractions_report.html"):
# #     """
# #     Generates a beautiful HTML report with a grid layout.
# #     MODIFIED: This version will not display the "Includes:" section.
# #     """
    
# #     html_content = f"""
# #     <!DOCTYPE html>
# #     <html lang="en">
# #     <head>
# #         <meta charset="UTF-8">
# #         <meta name="viewport" content="width=device-width, initial-scale=1.0">
# #         <title>Attractions in {city_name.title()}</title>
# #         <style>
# #             body {{
# #                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
# #                 margin: 0;
# #                 background-color: #f7f8fc;
# #                 color: #333;
# #             }}
# #             .container {{
# #                 max-width: 1200px;
# #                 margin: 20px auto;
# #                 padding: 20px;
# #             }}
# #             h1 {{
# #                 color: #1a1a1a;
# #                 text-align: center;
# #                 border-bottom: 2px solid #eee;
# #                 padding-bottom: 20px;
# #                 margin-bottom: 30px;
# #             }}
# #             h2 {{
# #                 color: #0056b3;
# #                 border-bottom: 1px solid #ddd;
# #                 padding-bottom: 8px;
# #                 margin-top: 40px;
# #             }}
# #             .category-grid {{
# #                 display: grid;
# #                 grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
# #                 gap: 25px;
# #             }}
# #             .attraction-card {{
# #                 background-color: #fff;
# #                 border-radius: 12px;
# #                 box-shadow: 0 4px 12px rgba(0,0,0,0.08);
# #                 transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
# #                 overflow: hidden;
# #                 display: flex;
# #                 flex-direction: column;
# #             }}
# #             .attraction-card:hover {{
# #                 transform: translateY(-5px);
# #                 box-shadow: 0 8px 20px rgba(0,0,0,0.12);
# #             }}
# #             .card-image img {{
# #                 width: 100%;
# #                 height: 200px;
# #                 object-fit: cover;
# #             }}
# #             .card-content {{
# #                 padding: 20px;
# #                 display: flex;
# #                 flex-direction: column;
# #                 flex-grow: 1;
# #             }}
# #             .card-content h3 {{
# #                 margin: 0 0 10px 0;
# #                 font-size: 1.25em;
# #                 color: #222;
# #             }}
# #             .card-content p {{
# #                 margin: 0 0 15px 0;
# #                 color: #666;
# #                 font-size: 0.95em;
# #                 line-height: 1.5;
# #             }}
# #             .score-badge {{
# #                 color: #fff;
# #                 padding: 6px 12px;
# #                 border-radius: 20px;
# #                 font-weight: bold;
# #                 font-size: 0.9em;
# #                 margin-top: auto;
# #                 align-self: flex-start;
# #             }}
# #             .expert-choice {{ background-color: #28a745; }}
# #             .regular-score {{ background-color: #007bff; }}
# #         </style>
# #     </head>
# #     <body>
# #         <div class="container">
# #             <h1>Curated Attractions for {city_name.title()}</h1>
# #     """

# #     for category in sorted(categorized_data.keys()):
# #         html_content += f"<h2>{category}</h2><div class='category-grid'>"
# #         for item in categorized_data[category]:
# #             parent = item['parent']
# #             p_name = parent.get("displayName", {}).get("text", "Unknown")
# #             p_rating = parent.get("rating", "N/A")
# #             p_cnt = _safe_get_count(parent)
# #             p_score = parent.get("rank_score", 0.0)
# #             expert_score = int(p_score * 100)
# #             p_thumb = parent.get("thumbnailUrl", "https://placehold.co/400x300/eee/333?text=No+Image")
            
# #             score_badge_html = ""
# #             if p_score > 0.85:
# #                 score_badge_html = "<div class='score-badge expert-choice'>🏆 Top Expert Choice</div>"
# #             else:
# #                 score_badge_html = f"<div class='score-badge regular-score'>Expert Score: {expert_score}%</div>"

# #             html_content += f"""
# #             <div class="attraction-card">
# #                 <div class="card-image">
# #                     <img src="{p_thumb}" alt="{p_name}">
# #                 </div>
# #                 <div class="card-content">
# #                     <h3>{p_name}</h3>
# #                     <p>Rating: {p_rating} ★ ({p_cnt:,} reviews)</p>
# #                     {score_badge_html}
# #                 </div>
# #             </div>
# #             """
# #             # NOTE: The block for rendering children has been removed to keep the UI flat.
# #         html_content += "</div>" # Close category-grid

# #     html_content += """
# #         </div>
# #     </body>
# #     </html>
# #     """
# #     try:
# #         with open(filename, "w", encoding="utf-8") as f:
# #             f.write(html_content)
# #         logging.info(f"HTML report saved to {filename}")
# #     except IOError as e:
# #         logging.error(f"Could not save HTML report: {e}")

# # # =============================================================================
# # # MAIN FLOW & HELPERS
# # # =============================================================================
# # def enrich_subview_attractions(center_lat: float, center_lon: float, radius_km: float) -> List[Place]:
# #     results: Dict[str, Place] = {}
# #     pts = [(center_lat, center_lon, int(min(radius_km * 1000, Config.MAX_NEARBY_RADIUS_M)))]
# #     for lat, lon, radius_m in pts:
# #         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
# #         for p in places_nearby(lat, lon, radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION):
# #             if pid := p.get("id"): results[pid] = p
# #     return list(results.values())

# # def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
# #     logging.info("Performing full adaptive search (this may take a moment)...")
# #     city_list, all_attractions = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km)
    
# #     if all_attractions:
# #         logging.info("Calculating distance for all new attractions...")
# #         for att in all_attractions:
# #             if loc := att.get('location'):
# #                 att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
# #         logging.info("Calculating and adding rank scores before caching...")
# #         all_attractions = add_rank_scores_to_places(all_attractions)
# #         hub_name = normalize_city_name(user_query_city)
# #         PlaceIdCache.save_many(all_attractions, hub_name)
# #         PlaceIdCache.save_many(city_list, hub_name)
# #         centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
# #         new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
# #         CentralHubCache.save_hub(new_hub, all_attractions)
# #         logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
# #     return city_list, all_attractions

# # def main(user_query_city: str, search_radius_km: Optional[float] = None):
# #     if search_radius_km is None: search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
# #     logging.info(f"\n===== Searching for '{user_query_city}' =====")
    
# #     global tracker
# #     tracker = APITracker()

# #     GeocodeCache.load(); CentralHubCache.load()
# #     center = geocode_city(user_query_city)
# #     if "error" in center:
# #         logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
# #         return

# #     matching_hub = CentralHubCache.find_matching_hub(center['latitude'], center['longitude'])
# #     city_list, all_attractions = [], []
# #     if matching_hub:
# #         logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
# #         tracker.count_cache_hit()
# #         city_list = matching_hub.cities
# #         all_attractions = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# #         normalized_query_name = normalize_city_name(user_query_city)
# #         if normalized_query_name != matching_hub.hub_name:
# #             radius_km = Config.SUBVIEW_RADIUS_KM
# #             all_attractions = [att for att in all_attractions if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# #             logging.info(f"Filtered {len(all_attractions)} attractions within {radius_km} km of {user_query_city}.")
# #             if len(all_attractions) < Config.SUBVIEW_MIN_TARGET:
# #                 logging.info(f"No/low results for {user_query_city} in hub; enriching subview...")
# #                 newly_found = enrich_subview_attractions(center["latitude"], center["longitude"], radius_km)
# #                 if newly_found:
# #                     PlaceIdCache.save_many(newly_found, matching_hub.hub_name)
# #                     hub_all = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
# #                     merged_by_id = {p["id"]: p for p in hub_all if p.get("id")}
# #                     for p in newly_found:
# #                         if pid := p.get("id"): merged_by_id[pid] = p
# #                     merged = list(merged_by_id.values())
# #                     CentralHubCache.save_hub(matching_hub, merged)
# #                     all_attractions = [att for att in merged if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
# #                     logging.info(f"Subview enrichment added {len(newly_found)}; now {len(all_attractions)} within {radius_km} km.")
# #     else:
# #         logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
# #         city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km)

# #     if not all_attractions:
# #         logging.warning("No attractions found.")
# #         return

# #     for att in all_attractions:
# #         if loc := att.get('location'):
# #             att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    
# #     all_attractions = add_rank_scores_to_places(all_attractions)
    
# #     logging.info(f"\nFound {len(all_attractions)} total attractions. Now structuring and categorizing...")
# #     categorized_results = structure_and_categorize_places(all_attractions)

# #     # --- Generate Outputs ---
# #     generate_html_report(categorized_results, user_query_city)
# #     try:
# #         with open("attractions_output.json", "w", encoding="utf-8") as f:
# #             json.dump(categorized_results, f, ensure_ascii=False, indent=4)
# #         logging.info("JSON output saved to attractions_output.json")
# #     except IOError as e:
# #         logging.error(f"Could not save JSON output: {e}")

# #     print("\n" + "="*50)
# #     print(f" ✨ Curated Attractions for {user_query_city} ✨")
# #     print("="*50)

# #     # Dynamically iterate over sorted category keys
# #     for category in sorted(categorized_results.keys()):
# #         items = categorized_results[category]
# #         print(f"\n--- 🏛️ {category} ---")
        
# #         for item in items:
# #             parent = item['parent']
# #             p_name = parent.get("displayName", {}).get("text", "<unknown>")
# #             p_rating = parent.get("rating", "N/A")
# #             p_cnt = _safe_get_count(parent)
# #             p_dist = parent.get('distance_to_query', -1)
            
# #             # MODIFIED: Print each item directly without an "Includes" section.
# #             print(f"\n📍 {p_name} (Rating: {p_rating}, {p_cnt:,} reviews) - {p_dist:.1f} km away")
    
# #     s = tracker.summary()
# #     print("\n" + "="*50 + "\n" + f"SESSION SUMMARY for {user_query_city.title()}" + "\n" + "="*50)
# #     print(f"Total Time Taken: {s['total_time_seconds']} seconds")
# #     print(f"Total API Calls:  {s['total_api_calls']}")
# #     print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
# #     print(f"  - Places:       {s['breakdown'].get('places', 0)}")
# #     print(f"Cache Hits:       {s['cache_hits']}")
# #     print("="*50)


# # # =============================================================================
# # # RUNNER
# # # =============================================================================
# # if __name__ == "__main__":
# #     if not Config.API_KEY:
# #         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

# #     try:
# #         while True:
# #             city = input("\nEnter a city name to search for (or 'quit' to exit): ")
# #             if city.lower() in ['quit', 'exit']:
# #                 break
# #             if city:
# #                 main(city)
# #             else:
# #                 print("Please enter a valid city name.")
# #     except Exception as e:
# #         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)



# import os
# import re
# import json
# import math
# import time
# import logging
# import threading
# import unicodedata
# import concurrent.futures
# import sqlite3
# import hashlib
# import random
# from dataclasses import dataclass, field
# from collections import deque
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Tuple, TypedDict
# from difflib import SequenceMatcher

# import requests
# from dotenv import load_dotenv

# try:
#     from scipy.spatial import KDTree
#     HAS_SCIPY = True
# except ImportError:
#     HAS_SCIPY = False

# # =============================================================================
# # INITIALIZATION
# # =============================================================================
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# # =============================================================================
# # TYPE DEFINITIONS
# # =============================================================================
# class Location(TypedDict):
#     latitude: float
#     longitude: float

# class DisplayName(TypedDict):
#     text: str
#     languageCode: str

# class Summary(TypedDict):
#     text: str
#     languageCode: str

# class Place(TypedDict, total=False):
#     # --- Base Fields ---
#     id: str
#     location: Location
#     displayName: DisplayName
#     types: List[str]
#     rating: float
#     userRatingCount: int
#     photos: List[Dict]
#     formattedAddress: str
#     # --- Enriched/Calculated Fields ---
#     thumbnailUrl: str
#     rank_score: float
#     distance_to_query: float
#     # --- Newly Added Rich Data Fields ---
#     paymentOptions: Dict[str, bool]
#     allowsDogs: bool
#     goodForChildren: bool
#     outdoorSeating: bool
#     servesCoffee: bool
#     # --- AI Summary Fields ---
#     generativeSummary: Summary
#     reviewSummary: Summary
#     neighborhoodSummary: Summary

# # =============================================================================
# # CONFIGURATION
# # =============================================================================
# class Config:
#     load_dotenv()
#     API_KEY = os.environ.get("GOOGLE_API_KEY")

#     # Storage
#     DB_DIR = Path("./adaptive_database_5")
#     GEOCODE_DIR = Path("./geocode_database")
#     CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
#     HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
#     TILE_DIR = DB_DIR / "tiles"
#     GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
#     PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
#     TTL_30D = 2_592_000

#     # Places API
#     MAX_NEARBY_RADIUS_M = 50_000
#     MAX_WORKERS = 16
#     PLACES_CALL_BUDGET: Optional[int] = 7
#     PAGINATE: bool = True
#     MAX_RETRIES = 3
#     TYPE_CITY = ("locality",)
#     TYPE_ATTRACTION = ("tourist_attraction",)
#     MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
#     MASK_ATTRACTION = (
#         "places.id,"
#         "places.displayName,"
#         "places.location,"
#         "places.types,"
#         "places.rating,"
#         "places.userRatingCount,"
#         "places.photos,"
#         "places.regularOpeningHours,"
#         "places.paymentOptions,"
#         "places.allowsDogs,"
#         "places.goodForChildren,"
#         "places.outdoorSeating,"
#         "places.servesCoffee,"
#         "places.generativeSummary,"
#         "places.reviewSummary,"
#         "places.neighborhoodSummary"
#     )


#     # Quadtree
#     DEFAULT_SEARCH_RADIUS_KM = 120
#     QT_MAX_DEPTH = 4
#     QT_SPLIT_THRESHOLD = 40
#     QT_MIN_EDGE_KM = 25.0
#     TWO_PHASE_NODE: bool = True
    
#     # Subview (for cache hits)
#     SUBVIEW_RADIUS_KM = 50
#     SUBVIEW_MIN_TARGET = 20

#     # --- Search tuning ---
#     ADAPTIVE_RADIUS = True
#     ADAPTIVE_HIGH_THRESHOLD = 10
#     ADAPTIVE_LOW_THRESHOLD = 1
#     ADAPTIVE_SHRINK_FACTOR = 0.7
#     ADAPTIVE_EXPAND_FACTOR = 1.2

#     # Budget-aware planner
#     LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

#     # Reranking
#     RERANK_MODE = "hybrid"
#     MIN_REVIEW_COUNT = 1000
#     RATING_PRIOR_M = 5000
#     WILSON_Z = 1.96
#     DISTANCE_DECAY_KM = 50.0
#     COUNT_WEIGHT = 0.25
#     BAYES_WEIGHT = 0.35
#     WILSON_WEIGHT = 0.25
#     DIST_WEIGHT = 0.15
#     TOP_N = 20
#     FILTER_NON_LATIN_NAMES = False

# # --- Ensure Dirs ---
# for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
#     path.mkdir(exist_ok=True)

# # =============================================================================
# # API CALL TRACKING & CORE CLASSES
# # =============================================================================
# class APITracker:
#     def __init__(self):
#         self.lock = threading.Lock()
#         self.calls = {"geocode": 0, "places": 0}
#         self.cache_hits = 0
#         self.start_time = time.time()
#     def count_call(self, api_type: str):
#         with self.lock:
#             self.calls[api_type] = self.calls.get(api_type, 0) + 1
#     def get_calls(self, api_type: str) -> int:
#         with self.lock:
#             return self.calls.get(api_type, 0)
#     def count_cache_hit(self):
#         with self.lock:
#             self.cache_hits += 1
#     def summary(self) -> Dict[str, Any]:
#         with self.lock:
#             return {
#                 "total_api_calls": sum(self.calls.values()),
#                 "breakdown": dict(self.calls),
#                 "cache_hits": self.cache_hits,
#                 "total_time_seconds": round(time.time() - self.start_time, 2),
#             }
# tracker = APITracker()

# class GeocodeCache:
#     _db_path = Config.GEOCODE_DB_FILE
#     @classmethod
#     def _init_db(cls):
#         with sqlite3.connect(cls._db_path) as conn:
#             conn.execute("PRAGMA journal_mode=WAL;")
#             conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
#     @classmethod
#     def load(cls):
#         cls._init_db()
#     @classmethod
#     def get(cls, city_key: str) -> Optional[Dict[str, float]]:
#         cls._init_db()
#         with sqlite3.connect(cls._db_path) as conn:
#             row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
#         return {"latitude": row[0], "longitude": row[1]} if row else None
#     @classmethod
#     def save(cls, city_key: str, location: Dict[str, float]):
#         cls._init_db()
#         with sqlite3.connect(cls._db_path) as conn:
#             conn.execute("""
#                 INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)
#                 ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp
#             """, (city_key, location["latitude"], location["longitude"], time.time()))

# class PlaceIdCache:
#     _db_path = Config.PLACE_ID_DB_FILE
#     @classmethod
#     def _init_db(cls):
#         with sqlite3.connect(cls._db_path) as conn:
#             conn.execute("PRAGMA journal_mode=WAL;")
#             conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
#             conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
#     @classmethod
#     def load(cls):
#         cls._init_db()
#     @classmethod
#     def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
#         cls._init_db()
#         with sqlite3.connect(cls._db_path) as conn:
#             row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
#         return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
#     @classmethod
#     def save_many(cls, places: List[Place], hub_name: str):
#         cls._init_db()
#         records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
#         if not records: return
#         with sqlite3.connect(cls._db_path) as conn:
#             conn.executemany("""
#                 INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?)
#                 ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp
#             """, records)

# class DiskCache:
#     _tile_mem_cache: Dict[str, List[Place]] = {}
#     _mem_lock = threading.Lock()
#     @staticmethod
#     def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> str:
#         key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}"
#         return hashlib.sha1(key_string.encode()).hexdigest()
#     @staticmethod
#     def _tile_path(key: str) -> Path:
#         return Config.TILE_DIR / f"{key}.json"
#     @classmethod
#     def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str) -> Optional[List[Place]]:
#         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
#         path = cls._tile_path(key)
#         with cls._mem_lock:
#             if key in cls._tile_mem_cache:
#                 tracker.count_cache_hit()
#                 return cls._tile_mem_cache[key]
#         if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
#             try:
#                 with open(path, "r", encoding="utf-8") as f:
#                     data = json.load(f)
#                 with cls._mem_lock:
#                     cls._tile_mem_cache[key] = data
#                 tracker.count_cache_hit()
#                 return data
#             except (json.JSONDecodeError, IOError):
#                 return None
#         return None
#     @classmethod
#     def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place]):
#         key = cls._tile_key(lat, lon, radius_m, types, field_mask)
#         path = cls._tile_path(key)
#         try:
#             with open(path, "w", encoding="utf-8") as f:
#                 json.dump(places, f, ensure_ascii=False)
#         except IOError as e:
#             logging.warning(f"Failed to save tile {path}: {e}")
#         with cls._mem_lock:
#             cls._tile_mem_cache[key] = places

# # =============================================================================
# # UTILITIES & API HELPERS
# # =============================================================================
# def is_primarily_latin(text: str, threshold: float = 0.9) -> bool:
#     if not text:
#         return False
#     latin_chars, total_alnum = 0, 0
#     for char in text:
#         if char.isalnum():
#             total_alnum += 1
#             if 'a' <= char.lower() <= 'z' or '0' <= char <= '9':
#                 latin_chars += 1
#     if total_alnum == 0:
#         return True
#     return (latin_chars / total_alnum) >= threshold

# def normalize_city_name(s: str) -> str:
#     if not s:
#         return ""
#     s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
#     s = s.lower().strip()
#     s = re.sub(r"[^\w\s-]", "", s)
#     s = re.sub(r"\s+", " ", s)
#     return s.strip()

# def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
#     R = 6371.0
#     dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
#     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
#     return 2 * R * math.asin(math.sqrt(a))

# def km_to_deg_lat(km: float) -> float:
#     return km / 111.0

# def km_to_deg_lon(km: float, at_lat: float) -> float:
#     return km / (111.320 * math.cos(math.radians(at_lat)) + 1e-12)

# def get_simple_name(text: str) -> str:
#     """Normalizes a name for comparison by removing generic terms."""
#     if not text: return ""
#     text = text.lower()
#     text = text.replace('mt.', 'mount').replace('mt ', 'mount ')
#     generic_terms = ['park', 'center', 'museum', 'garden', 'lookout', 'trail', 'trailhead']
#     for term in generic_terms:
#         text = text.replace(term, '')
#     return re.sub(r'\s+', ' ', text).strip()

# def get_category_from_place(place: Place) -> str:
#     """Assigns a place to a predefined category based on its type and name."""
#     types = place.get('types', [])
#     name = place.get('displayName', {}).get('text', '').lower()
    
#     if 'beach' in types:
#         return "Beaches & Waterfront"
#     if 'historical_landmark' in types or 'historical_place' in types:
#         return "Historical Sites"
#     if 'buddhist_temple' in types or 'hindu_temple' in types or 'mosque' in types or 'church' in types:
#         return "Temples & Religious Sites"
#     if 'market' in types:
#         return "Shopping & Markets"
#     if 'zoo' in types or 'aquarium' in types: 
#         return "Zoos & Aquariums"
#     if 'museum' in types or 'art_gallery' in types: 
#         return "Museums & Culture"
#     if 'hike' in name or 'trail' in name or 'falls' in name or 'lookout' in name:
#         return "Parks & Hiking"
#     if 'park' in types or 'national_park' in types:
#         if 'stadium' not in types:
#             return "Parks & Hiking"
#     if 'stadium' in types: 
#         return "Venues & Stadiums"
#     if 'tourist_attraction' in types: 
#         return "Landmarks & Points of Interest"
    
#     return "Other Attractions"

# def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
#     url = "https://places.googleapis.com/v1/places:searchNearby"
#     for attempt in range(Config.MAX_RETRIES):
#         try:
#             resp = requests.post(url, json=payload, headers=headers, timeout=30)
#             if 500 <= resp.status_code < 600 or resp.status_code == 429:
#                 logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
#                 time.sleep((2 ** attempt) + random.random())
#                 continue
#             if resp.status_code != 200:
#                 logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
#             resp.raise_for_status()
#             return resp.json()
#         except requests.exceptions.RequestException as e:
#             logging.error(f"API request failed after {attempt + 1} attempts: {e}")
#             break
#     return None

# def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str) -> List[Place]:
#     if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
#         return []
#     cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask)
#     if cached is not None:
#         return cached

#     headers = { "Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask }
#     payload = {
#         "includedTypes": list(included_types),
#         "maxResultCount": 20,
#         "languageCode": "en",
#         "locationRestriction": {
#             "circle": {
#                 "center": {"latitude": lat, "longitude": lon},
#                 "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))
#             }
#         }
#     }

#     all_places: List[Place] = []
#     next_page_token = None
#     while True:
#         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
#             logging.warning("Places API budget exhausted during pagination.")
#             break
#         if next_page_token:
#             payload["pageToken"] = next_page_token
#             time.sleep(0.5 + random.random() * 0.5)

#         tracker.count_call("places")
#         data = _post_with_retry(payload, headers)
#         if not data or not data.get("places"):
#             break

#         current_places = data.get("places", [])
#         for p in current_places:
#             if p.get("photos") and len(p["photos"]) > 0:
#                 p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
#                 del p["photos"]
#         all_places.extend(current_places)
#         next_page_token = data.get("nextPageToken")
#         if not Config.PAGINATE or not next_page_token:
#             break

#     DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places)
#     return all_places

# def geocode_city(city_name: str) -> Dict[str, Any]:
#     normalized_name = normalize_city_name(city_name)
#     cached = GeocodeCache.get(normalized_name)
#     if cached:
#         tracker.count_cache_hit()
#         return cached
#     if not Config.API_KEY:
#         return {"error": "Google API key is not configured."}
#     tracker.count_call("geocode")
#     url = "https://maps.googleapis.com/maps/api/geocode/json"
#     try:
#         resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
#         resp.raise_for_status()
#         data = resp.json()
#         if data.get("status") == "OK":
#             loc = data["results"][0]["geometry"]["location"]
#             result = {"latitude": loc["lat"], "longitude": loc["lng"]}
#             GeocodeCache.save(normalized_name, result)
#             return result
#         return {"error": f"Geocoding API status: {data.get('status')}"}
#     except requests.exceptions.RequestException as e:
#         return {"error": f"Geocoding request failed: {e}"}

# # =============================================================================
# # QUADTREE ADAPTIVE SEARCH
# # =============================================================================
# @dataclass
# class Quadrant:
#     min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
#     @property
#     def center(self) -> Tuple[float, float]:
#         return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
#     @property
#     def edge_km(self) -> float:
#         return abs(self.max_lat - self.min_lat) * 111.0
#     @property
#     def inscribed_radius_m(self) -> int:
#         return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
#     def subdivide(self) -> List["Quadrant"]:
#         mid_lat, mid_lon = self.center; d = self.depth + 1
#         return [
#             Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d),
#             Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
#             Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d),
#             Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)
#         ]

# def get_budget_limit_for_depth(depth: int) -> int:
#     if Config.PLACES_CALL_BUDGET is None:
#         return float('inf')
    
#     total_budget = Config.PLACES_CALL_BUDGET
#     weights = Config.LEVEL_BUDGET_WEIGHTS
    
#     cumulative_weight = 0.0
#     for d in range(depth + 1):
#         cumulative_weight += weights.get(d, 0)

#     if depth not in weights and depth > max(weights.keys()):
#         remainder = max(0, 1.0 - sum(weights.values()))
#         cumulative_weight = sum(weights.values()) + remainder

#     final_cumulative_weight = min(1.0, cumulative_weight)

#     return max(1, int(total_budget * final_cumulative_weight))


# def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
#     q = deque([Quadrant(center_lat - km_to_deg_lat(search_radius_km), center_lon - km_to_deg_lon(search_radius_km, center_lat), center_lat + km_to_deg_lat(search_radius_km), center_lon + km_to_deg_lon(search_radius_km, center_lat), 0)])
#     cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()
    
#     def process_quadrant(quad: Quadrant):
#         budget_limit = get_budget_limit_for_depth(quad.depth)
#         if tracker.get_calls("places") >= budget_limit:
#             if quad.depth < 2:
#                 logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
#             return None, None
        
#         can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
#         lat, lon = quad.center
        
#         base_radius_m = quad.inscribed_radius_m
#         node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY)
        
#         for c in node_cities:
#             if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
#                 GeocodeCache.save(normalize_city_name(name), loc)
        
#         attraction_radius_m = base_radius_m
#         if Config.ADAPTIVE_RADIUS:
#             if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD:
#                 attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
#             elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD:
#                 attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        
#         node_attrs: List[Place] = []
#         if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
#             node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION)
        
#         with lock:
#             for p in node_cities:
#                 if p_id := p.get("id"): cities[p_id] = p
#             for p in node_attrs:
#                 if p_id := p.get("id"): attractions[p_id] = p
        
#         if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD:
#             return quad.subdivide(), quad.depth
#         return None, quad.depth

#     while q:
#         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET:
#             break
#         current_depth = q[0].depth
#         level_size = len(q)
#         logging.info(f"Processing level {current_depth} with {level_size} quadrants...")
        
#         quadrants_to_process = [q.popleft() for _ in range(level_size)]
#         with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
#             future_to_quad = {executor.submit(process_quadrant, quad): quad for quad in quadrants_to_process}
#             for future in concurrent.futures.as_completed(future_to_quad):
#                 try:
#                     if (result := future.result()) and (children := result[0]):
#                         q.extend(children)
#                 except Exception as e:
#                     logging.error(f"A quadrant processing task failed: {e}")
#     return list(cities.values()), list(attractions.values())

# # =============================================================================
# # HUB CACHE & RANKING
# # =============================================================================
# @dataclass
# class HubEntry:
#     hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)

# def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
#     if not places: return {"latitude": 0, "longitude": 0}, 0
#     lats = [p['location']['latitude'] for p in places if 'location' in p]
#     lngs = [p['location']['longitude'] for p in places if 'location' in p]
#     if not lats: return {"latitude": 0, "longitude": 0}, 0
#     centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
#     max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
#     return centroid, max_dist * 1.05

# class CentralHubCache:
#     _hubs: Dict[str, HubEntry] = {}
#     @classmethod
#     def load(cls):
#         if not Config.CENTRAL_HUB_FILE.exists(): return
#         try:
#             with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f:
#                 cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
#             logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
#         except Exception as e:
#             logging.error(f"Could not load central hub cache: {e}")
#     @classmethod
#     def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
#         for hub in cls._hubs.values():
#             if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km:
#                 return hub
#         return None
#     @classmethod
#     def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
#         path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
#         if not path.exists(): return None
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception as e:
#             logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
#             return None
#     @classmethod
#     def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
#         cls._hubs[hub_entry.hub_name] = hub_entry
#         for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
#             temp_path = path.with_suffix(f"{path.suffix}.tmp")
#             try:
#                 with open(temp_path, "w", encoding="utf-8") as f:
#                     json.dump(data, f, ensure_ascii=False, indent=4)
#                 os.replace(temp_path, path)
#             except IOError as e:
#                 logging.error(f"Could not save hub file {path}: {e}")

# def _safe_get_rating(p: Dict) -> Optional[float]:
#     try: return float(p.get("rating")) if p.get("rating") is not None else None
#     except (ValueError, TypeError): return None
# def _safe_get_count(p: Dict) -> int:
#     try: return int(p.get("userRatingCount", 0) or 0)
#     except (ValueError, TypeError): return 0
# def _global_mean_rating(places: List[Dict]) -> float:
#     vals = [_safe_get_rating(p) for p in places if _safe_get_rating(p) is not None]
#     return (sum(vals) / len(vals)) if vals else 3.5
# def _bayes_score(R: float, v: int, C: float, m: int) -> float:
#     return (v * R + m * C) / (v + m) if (v + m) > 0 else C
# def _wilson_lower_bound(p: float, n: int, z: float) -> float:
#     if n <= 0: return 0.0
#     denom = 1 + z*z/n
#     center = p + z*z/(2*n)
#     margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
#     return max(0.0, (center - margin) / denom)

# def rerank_places(places: List[Place], top_n: int = Config.TOP_N) -> List[Place]:
#     if not places: return []
#     mode, m, z, decay_km = Config.RERANK_MODE, Config.RATING_PRIOR_M, Config.WILSON_Z, Config.DISTANCE_DECAY_KM
#     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
#     C = _global_mean_rating(places)
#     max_v = max([_safe_get_count(p) for p in places] + [1])
#     scored = []
#     for p in places:
#         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
#         if R is None: continue
#         bayes_n = _bayes_score(R, v, C, m) / 5.0
#         wilson = _wilson_lower_bound(R / 5.0, v, z)
#         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
#         count_factor = math.log1p(v) / math.log1p(max_v)

#         if mode == "bayes": final_score = bayes_n
#         elif mode == "wilson": final_score = wilson
#         else: final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
#         p["rank_score"] = final_score
#         scored.append(p)

#     scored.sort(key=lambda x: (-x.get("rank_score", 0.0), x.get("distance_to_query", float("inf")), -_safe_get_count(x), -(_safe_get_rating(x) or 0.0)))
#     return scored[:top_n]

# def group_attractions_by_nearest_city(attractions: List[Place], cities: List[Place]) -> Dict[str, List[Place]]:
#     grouped: Dict[str, List[Place]] = {}
#     if not cities or not attractions: return grouped
#     cities_with_loc = [c for c in cities if 'location' in c]
#     if not cities_with_loc: return grouped
#     if HAS_SCIPY:
#         city_coords = [[c['location']['latitude'], c['location']['longitude']] for c in cities_with_loc]
#         tree = KDTree(city_coords)
#         for att in attractions:
#             if 'location' in att:
#                 _, idx = tree.query([att['location']['latitude'], att['location']['longitude']])
#                 name = cities_with_loc[idx].get("displayName", {}).get("text", "Unknown City")
#                 grouped.setdefault(name, []).append(att)
#     else:
#         for att in attractions:
#             if 'location' not in att: continue
#             best_d, best_c_name = float("inf"), "Unknown City"
#             for c in cities_with_loc:
#                 d = haversine_km(att['location']['latitude'], att['location']['longitude'], c['location']['latitude'], c['location']['longitude'])
#                 if d < best_d:
#                     best_d, best_c_name = d, c.get("displayName", {}).get("text", "Unknown City")
#             grouped.setdefault(best_c_name, []).append(att)
#     return grouped

# def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
#     if not places: return []
#     m, z = Config.RATING_PRIOR_M, Config.WILSON_Z
#     decay_km = Config.DISTANCE_DECAY_KM
#     w_b, w_w, w_d, w_c = Config.BAYES_WEIGHT, Config.WILSON_WEIGHT, Config.DIST_WEIGHT, Config.COUNT_WEIGHT
#     C = _global_mean_rating(places)
#     max_v = max([_safe_get_count(p) for p in places] + [1])
#     for p in places:
#         R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
#         if R is None: 
#             p["rank_score"] = 0.0
#             continue
#         bayes_n = _bayes_score(R, v, C, m) / 5.0
#         wilson = _wilson_lower_bound(R / 5.0, v, z)
#         dist_factor = math.exp(-d / decay_km) if isinstance(d, (int, float)) and d >= 0 else 0.6
#         count_factor = math.log1p(v) / math.log1p(max_v)
#         final_score = w_b * bayes_n + w_w * wilson + w_d * dist_factor + w_c * count_factor
#         p["rank_score"] = final_score
#     return places

# def structure_and_categorize_places(places: List[Place]) -> Dict[str, List[Dict[str, Any]]]:
#     """
#     Deduplicates, groups, and categorizes a list of places, creating a tree structure.
#     Every place gets its own card, even if it's also a child.
#     """
#     if not places: return {}
    
#     # --- Step 1: Filter and Deduplicate ---
#     places = [p for p in places if _safe_get_count(p) >= Config.MIN_REVIEW_COUNT]
#     places.sort(key=lambda p: _safe_get_count(p), reverse=True)
    
#     unique_places_map: Dict[str, Place] = {}
#     processed_for_dupes = set()
#     for i in range(len(places)):
#         p1 = places[i]
#         p1_id = p1.get('id')
#         if p1_id in processed_for_dupes: continue
        
#         unique_places_map[p1_id] = p1
#         processed_for_dupes.add(p1_id)

#         for j in range(i + 1, len(places)):
#             p2 = places[j]
#             p2_id = p2.get('id')
#             if p2_id in processed_for_dupes: continue
            
#             name1 = get_simple_name(p1.get('displayName', {}).get('text', ''))
#             name2 = get_simple_name(p2.get('displayName', {}).get('text', ''))
#             ratio = SequenceMatcher(None, name1, name2).ratio()
#              # Ensure locations exist before calculating distance
#             if 'location' not in p1 or 'location' not in p2: continue
#             dist = haversine_km(p1['location']['latitude'], p1['location']['longitude'], p2['location']['latitude'], p2['location']['longitude'])
            
#             if ratio > 0.8 and dist < 0.5:
#                 logging.info(f"Merging duplicate: '{p2['displayName']['text']}' into '{p1['displayName']['text']}'")
#                 processed_for_dupes.add(p2_id)
    
#     unique_places = list(unique_places_map.values())

#     # --- Step 2: Hierarchical Grouping (Parent-Child) ---
#     parent_keywords = {
#         'national park': 50.0, 'state park': 30.0, 'seattle center': 1.0, 
#         'campus': 2.0, 'center': 1.5,
#     }
    
#     structured_list: List[Dict[str, Any]] = [{"parent": p, "children": []} for p in unique_places]
    
#     for item in structured_list:
#         parent = item['parent']
#         p_name = parent.get('displayName', {}).get('text', '').lower()
        
#         for keyword, radius_km in parent_keywords.items():
#             if keyword in p_name:
#                 for other_item in structured_list:
#                     child = other_item['parent']
#                     if parent['id'] == child['id']: continue

#                     dist = haversine_km(parent['location']['latitude'], parent['location']['longitude'], child['location']['latitude'], child['location']['longitude'])
                    
#                     if dist < radius_km:
#                         item['children'].append(child)
                
#                 item['children'].sort(key=lambda p: p.get('rank_score', 0), reverse=True)
#                 break 

#     # --- Step 3: Categorization ---
#     final_categorized: Dict[str, List[Dict[str, Any]]] = {}
#     for item in structured_list:
#         category = get_category_from_place(item['parent'])
#         if category not in final_categorized: final_categorized[category] = []
#         final_categorized[category].append(item)

#     for category in final_categorized:
#         final_categorized[category].sort(key=lambda i: i['parent'].get('rank_score', 0), reverse=True)

#     return final_categorized

# def generate_html_report(categorized_data: Dict[str, List[Dict[str, Any]]], city_name: str, filename="attractions_report.html"):
#     """
#     Generates a beautiful HTML report with a grid layout and new attribute icons.
#     """
    
#     html_content = f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <title>Attractions in {city_name.title()}</title>
#         <style>
#             body {{
#                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
#                 margin: 0;
#                 background-color: #f7f8fc;
#                 color: #333;
#             }}
#             .container {{
#                 max-width: 1200px;
#                 margin: 20px auto;
#                 padding: 20px;
#             }}
#             h1 {{
#                 color: #1a1a1a;
#                 text-align: center;
#                 border-bottom: 2px solid #eee;
#                 padding-bottom: 20px;
#                 margin-bottom: 30px;
#             }}
#             h2 {{
#                 color: #0056b3;
#                 border-bottom: 1px solid #ddd;
#                 padding-bottom: 8px;
#                 margin-top: 40px;
#             }}
#             .category-grid {{
#                 display: grid;
#                 grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
#                 gap: 25px;
#             }}
#             .attraction-card {{
#                 background-color: #fff;
#                 border-radius: 12px;
#                 box-shadow: 0 4px 12px rgba(0,0,0,0.08);
#                 transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
#                 overflow: hidden;
#                 display: flex;
#                 flex-direction: column;
#                 position: relative;
#             }}
#             .attraction-card:hover {{
#                 transform: translateY(-5px);
#                 box-shadow: 0 8px 20px rgba(0,0,0,0.12);
#             }}
#             .card-image img {{
#                 width: 100%;
#                 height: 200px;
#                 object-fit: cover;
#             }}
#             .card-content {{
#                 padding: 20px;
#                 padding-bottom: 50px;
#                 display: flex;
#                 flex-direction: column;
#                 flex-grow: 1;
#             }}
#             .card-content h3 {{
#                 margin: 0 0 10px 0;
#                 font-size: 1.25em;
#                 color: #222;
#             }}
#             .card-content p {{
#                 margin: 0 0 15px 0;
#                 color: #666;
#                 font-size: 0.95em;
#                 line-height: 1.5;
#             }}
#             .summary-text {{
#                 font-size: 0.9em;
#                 color: #555;
#                 border-left: 3px solid #007bff;
#                 padding-left: 10px;
#                 margin-top: 10px;
#                 margin-bottom: 15px;
#             }}
#             .score-badge {{
#                 color: #fff;
#                 padding: 6px 12px;
#                 border-radius: 20px;
#                 font-weight: bold;
#                 font-size: 0.9em;
#                 margin-top: auto;
#                 align-self: flex-start;
#             }}
#             .expert-choice {{ background-color: #28a745; }}
#             .regular-score {{ background-color: #007bff; }}
#             .card-footer-icons {{
#                 position: absolute;
#                 bottom: 15px;
#                 left: 20px;
#                 right: 20px;
#                 display: flex;
#                 gap: 12px;
#                 font-size: 1.2em;
#             }}
#             .icon-badge {{ color: #555; }}
#             .icon-badge.enabled {{ color: #007bff; }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <h1>Curated Attractions for {city_name.title()}</h1>
#     """

#     for category in sorted(categorized_data.keys()):
#         html_content += f"<h2>{category}</h2><div class='category-grid'>"
#         for item in categorized_data[category]:
#             parent = item['parent']
#             p_name = parent.get("displayName", {}).get("text", "Unknown")
#             p_rating = parent.get("rating", "N/A")
#             p_cnt = _safe_get_count(parent)
#             p_score = parent.get("rank_score", 0.0)
#             expert_score = int(p_score * 100)
#             p_thumb = parent.get("thumbnailUrl", "https://placehold.co/400x300/eee/333?text=No+Image")
            
#             score_badge_html = ""
#             if p_score > 0.85:
#                 score_badge_html = "<div class='score-badge expert-choice'>🏆 Top Expert Choice</div>"
#             else:
#                 score_badge_html = f"<div class='score-badge regular-score'>Expert Score: {expert_score}%</div>"
            
#             place_summary = parent.get("generativeSummary", {}).get("text")
#             review_summary = parent.get("reviewSummary", {}).get("text")
#             summary_html = ""
#             if place_summary:
#                 summary_html += f'<p class="summary-text"><b>Summary:</b> {place_summary}</p>'
#             elif review_summary:
#                 summary_html += f'<p class="summary-text"><b>From Reviews:</b> {review_summary}</p>'

#             icons_html = "<div class='card-footer-icons'>"
#             if parent.get('wheelchairAccessibleEntrance'): icons_html += "<span class='icon-badge enabled' title='Wheelchair Accessible'>♿</span>"
#             if parent.get('allowsDogs'): icons_html += "<span class='icon-badge enabled' title='Dogs Allowed'>🐶</span>"
#             if parent.get('goodForChildren'): icons_html += "<span class='icon-badge enabled' title='Good for Children'>👨‍👩‍👧‍👦</span>"
#             if parent.get('outdoorSeating'): icons_html += "<span class='icon-badge enabled' title='Outdoor Seating'>🌳</span>"
#             if parent.get('paymentOptions', {}).get('acceptsCreditCards'): icons_html += "<span class='icon-badge enabled' title='Accepts Credit Cards'>💳</span>"
#             icons_html += "</div>"

#             html_content += f"""
#             <div class="attraction-card">
#                 <div class="card-image"><img src="{p_thumb}" alt="{p_name}"></div>
#                 <div class="card-content">
#                     <h3>{p_name}</h3>
#                     <p>Rating: {p_rating} ★ ({p_cnt:,} reviews)</p>
#                     {summary_html}
#                     {score_badge_html}
#                 </div>
#                 {icons_html}
#             </div>
#             """
#         html_content += "</div>"

#     html_content += "</div></body></html>"
#     try:
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(html_content)
#         logging.info(f"HTML report saved to {filename}")
#     except IOError as e:
#         logging.error(f"Could not save HTML report: {e}")

# # =============================================================================
# # MAIN FLOW & HELPERS
# # =============================================================================
# def enrich_subview_attractions(center_lat: float, center_lon: float, radius_km: float) -> List[Place]:
#     results: Dict[str, Place] = {}
#     pts = [(center_lat, center_lon, int(min(radius_km * 1000, Config.MAX_NEARBY_RADIUS_M)))]
#     for lat, lon, radius_m in pts:
#         if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
#         for p in places_nearby(lat, lon, radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION):
#             if pid := p.get("id"): results[pid] = p
#     return list(results.values())

# def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float) -> Tuple[List[Place], List[Place]]:
#     logging.info("Performing full adaptive search (this may take a moment)...")
#     city_list, all_attractions = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km)
    
#     if all_attractions:
#         logging.info("Calculating distance for all new attractions...")
#         for att in all_attractions:
#             if loc := att.get('location'):
#                 att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
#         logging.info("Calculating and adding rank scores before caching...")
#         all_attractions = add_rank_scores_to_places(all_attractions)
#         hub_name = normalize_city_name(user_query_city)
#         PlaceIdCache.save_many(all_attractions, hub_name)
#         PlaceIdCache.save_many(city_list, hub_name)
#         centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
#         new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
#         CentralHubCache.save_hub(new_hub, all_attractions)
#         logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
#     return city_list, all_attractions

# def main(user_query_city: str, search_radius_km: Optional[float] = None):
#     if search_radius_km is None: search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
#     logging.info(f"\n===== Searching for '{user_query_city}' =====")
    
#     global tracker
#     tracker = APITracker()

#     GeocodeCache.load(); CentralHubCache.load()
#     center = geocode_city(user_query_city)
#     if "error" in center:
#         logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
#         return

#     matching_hub = CentralHubCache.find_matching_hub(center['latitude'], center['longitude'])
#     city_list, all_attractions = [], []
#     if matching_hub:
#         logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
#         tracker.count_cache_hit()
#         city_list = matching_hub.cities
#         all_attractions = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
#         normalized_query_name = normalize_city_name(user_query_city)
#         if normalized_query_name != matching_hub.hub_name:
#             radius_km = Config.SUBVIEW_RADIUS_KM
#             all_attractions = [att for att in all_attractions if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
#             logging.info(f"Filtered {len(all_attractions)} attractions within {radius_km} km of {user_query_city}.")
#             if len(all_attractions) < Config.SUBVIEW_MIN_TARGET:
#                 logging.info(f"No/low results for {user_query_city} in hub; enriching subview...")
#                 newly_found = enrich_subview_attractions(center["latitude"], center["longitude"], radius_km)
#                 if newly_found:
#                     PlaceIdCache.save_many(newly_found, matching_hub.hub_name)
#                     hub_all = CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
#                     merged_by_id = {p["id"]: p for p in hub_all if p.get("id")}
#                     for p in newly_found:
#                         if pid := p.get("id"): merged_by_id[pid] = p
#                     merged = list(merged_by_id.values())
#                     CentralHubCache.save_hub(matching_hub, merged)
#                     all_attractions = [att for att in merged if (loc := att.get("location")) and haversine_km(center["latitude"], center["longitude"], loc.get("latitude", 0.0), loc.get("longitude", 0.0)) <= radius_km]
#                     logging.info(f"Subview enrichment added {len(newly_found)}; now {len(all_attractions)} within {radius_km} km.")
#     else:
#         logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
#         city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km)

#     if not all_attractions:
#         logging.warning("No attractions found.")
#         return

#     for att in all_attractions:
#         if loc := att.get('location'):
#             att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    
#     all_attractions = add_rank_scores_to_places(all_attractions)
    
#     logging.info(f"\nFound {len(all_attractions)} total attractions. Now structuring and categorizing...")
#     categorized_results = structure_and_categorize_places(all_attractions)

#     # --- Generate Outputs ---
#     generate_html_report(categorized_results, user_query_city)
#     try:
#         with open("attractions_output.json", "w", encoding="utf-8") as f:
#             json.dump(categorized_results, f, ensure_ascii=False, indent=4)
#         logging.info("JSON output saved to attractions_output.json")
#     except IOError as e:
#         logging.error(f"Could not save JSON output: {e}")

#     print("\n" + "="*50)
#     print(f" ✨ Curated Attractions for {user_query_city} ✨")
#     print("="*50)

#     for category in sorted(categorized_results.keys()):
#         items = categorized_results[category]
#         print(f"\n--- 🏛️ {category} ---")
        
#         for item in items:
#             parent = item['parent']
#             p_name = parent.get("displayName", {}).get("text", "<unknown>")
#             p_rating = parent.get("rating", "N/A")
#             p_cnt = _safe_get_count(parent)
#             p_dist = parent.get('distance_to_query', -1)
            
#             print(f"\n📍 {p_name} (Rating: {p_rating}, {p_cnt:,} reviews) - {p_dist:.1f} km away")

#             info_parts = []
#             if parent.get('wheelchairAccessibleEntrance'): info_parts.append("♿ Accessible")
#             if parent.get('allowsDogs'): info_parts.append("🐶 Dogs Allowed")
#             if parent.get('goodForChildren'): info_parts.append("👨‍👩‍👧‍👦 Family Friendly")
#             if parent.get('outdoorSeating'): info_parts.append("🌳 Outdoor Seating")
#             if info_parts:
#                 print(f"   ✨ {' | '.join(info_parts)}")
            
#             summary = parent.get("generativeSummary", {}).get("text")
#             if summary:
#                 print(f"   📝 Summary: {summary}")

#     s = tracker.summary()
#     print("\n" + "="*50 + "\n" + f"SESSION SUMMARY for {user_query_city.title()}" + "\n" + "="*50)
#     print(f"Total Time Taken: {s['total_time_seconds']} seconds")
#     print(f"Total API Calls:  {s['total_api_calls']}")
#     print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
#     print(f"  - Places:       {s['breakdown'].get('places', 0)}")
#     print(f"Cache Hits:       {s['cache_hits']}")
#     print("="*50)


# # =============================================================================
# # RUNNER
# # =============================================================================
# if __name__ == "__main__":
#     if not Config.API_KEY:
#         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

#     try:
#         while True:
#             city = input("\nEnter a city name to search for (or 'quit' to exit): ")
#             if city.lower() in ['quit', 'exit']:
#                 break
#             if city:
#                 main(city)
#             else:
#                 print("Please enter a valid city name.")
#     except Exception as e:
#         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)

##########-------------------------------------------------------------------------

import os
import re
import json
import math
import time
import logging
import threading
import unicodedata
import concurrent.futures
import sqlite3
import hashlib
import random
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from difflib import SequenceMatcher
import sys
import requests
from dotenv import load_dotenv

try:
    from scipy.spatial import KDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# =============================================================================
# INITIALIZATION
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

class Summary(TypedDict):
    text: str
    languageCode: str

class Leg(TypedDict):
    duration: str
    distanceMeters: int

class RoutingSummary(TypedDict):
    legs: List[Leg]

class Place(TypedDict, total=False):
    id: str
    location: Location
    displayName: DisplayName
    types: List[str]
    rating: float
    userRatingCount: int
    photos: List[Dict]
    formattedAddress: str
    regularOpeningHours: Dict
    thumbnailUrl: str
    rank_score: float
    distance_to_query: float
    paymentOptions: Dict[str, bool]
    allowsDogs: bool
    goodForChildren: bool
    outdoorSeating: bool
    servesCoffee: bool
    priceLevel: str
    # MODIFIED: Added priceRange field
    priceRange: Dict
    websiteUri: str
    goodForGroups: bool
    generativeSummary: Summary
    reviewSummary: Summary
    areaSummary: Summary
    routingSummary: RoutingSummary

# =============================================================================
# CONFIGURATION
# =============================================================================
class Config:
    load_dotenv()
    API_KEY = os.environ.get("GOOGLE_API_KEY")

    # Storage - use absolute paths relative to backend directory
    BASE_DIR = Path(__file__).parent  # This file is directly in backend/
    DB_DIR = BASE_DIR / "database" / "adaptive_database"
    GEOCODE_DIR = BASE_DIR / "database" / "geocode_database"
    CENTRAL_HUB_FILE = DB_DIR / "central_hub.json"
    HUB_ATTRACTIONS_DIR = DB_DIR / "hubs"
    TILE_DIR = DB_DIR / "tiles"
    GEOCODE_DB_FILE = GEOCODE_DIR / "geocode_cache.sqlite"
    PLACE_ID_DB_FILE = GEOCODE_DIR / "place_id_cache.sqlite"
    TTL_30D = 2_592_000

    # Places API
    MAX_NEARBY_RADIUS_M = 50_000
    MAX_WORKERS = 16
    PLACES_CALL_BUDGET: Optional[int] = 7
    PAGINATE: bool = True
    MAX_RETRIES = 3
    TYPE_CITY = ("locality",)
    TYPE_ATTRACTION = ("tourist_attraction", "airport")
    MASK_CITY = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
    # MODIFIED: Added priceRange to the mask
    MASK_ATTRACTION = (
        "places.id,"
        "places.displayName,"
        "places.location,"
        "places.types,"
        "places.rating,"
        "places.userRatingCount,"
        "places.photos,"
        "places.regularOpeningHours,"
        "places.paymentOptions,"
        "places.allowsDogs,"
        "places.goodForChildren,"
        "places.outdoorSeating,"
        "places.servesCoffee,"
        "places.priceLevel,"
        "places.priceRange,"
        "places.websiteUri,"
        "places.goodForGroups,"
        "places.generativeSummary,"
        "places.reviewSummary,"
        "places.areaSummary,"
        "routingSummaries"
    )

    # Quadtree
    DEFAULT_SEARCH_RADIUS_KM = 120
    QT_MAX_DEPTH = 4
    QT_SPLIT_THRESHOLD = 40
    QT_MIN_EDGE_KM = 25.0
    TWO_PHASE_NODE: bool = True
    
    # Subview (for cache hits)
    SUBVIEW_RADIUS_KM = 50
    SUBVIEW_MIN_TARGET = 20

    # --- Search tuning ---
    ADAPTIVE_RADIUS = True
    ADAPTIVE_HIGH_THRESHOLD = 10
    ADAPTIVE_LOW_THRESHOLD = 1
    ADAPTIVE_SHRINK_FACTOR = 0.7
    ADAPTIVE_EXPAND_FACTOR = 1.2

    # Budget-aware planner
    LEVEL_BUDGET_WEIGHTS = {0: 0.5, 1: 0.3}

    # Reranking
    RERANK_MODE = "hybrid"
    MIN_REVIEW_COUNT = 1000
    RATING_PRIOR_M = 5000
    WILSON_Z = 1.96
    DISTANCE_DECAY_KM = 50.0
    COUNT_WEIGHT = 0.25
    BAYES_WEIGHT = 0.35
    WILSON_WEIGHT = 0.25
    DIST_WEIGHT = 0.15
    TOP_N = 20
    FILTER_NON_LATIN_NAMES = False

# --- Ensure Dirs ---
for path in [Config.DB_DIR, Config.GEOCODE_DIR, Config.TILE_DIR, Config.HUB_ATTRACTIONS_DIR]:
    path.mkdir(exist_ok=True)

# =============================================================================
# API CALL TRACKING & CORE CLASSES (UNCHANGED)
# =============================================================================
class APITracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.calls = {"geocode": 0, "places": 0}
        self.cache_hits = 0
        self.start_time = time.time()
    def count_call(self, api_type: str):
        with self.lock: self.calls[api_type] = self.calls.get(api_type, 0) + 1
    def get_calls(self, api_type: str) -> int:
        with self.lock: return self.calls.get(api_type, 0)
    def count_cache_hit(self):
        with self.lock: self.cache_hits += 1
    def summary(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "total_api_calls": sum(self.calls.values()), "breakdown": dict(self.calls),
                "cache_hits": self.cache_hits, "total_time_seconds": round(time.time() - self.start_time, 2),
            }
tracker = APITracker()

class GeocodeCache:
    _db_path = Config.GEOCODE_DB_FILE
    @classmethod
    def _init_db(cls):
        with sqlite3.connect(cls._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("CREATE TABLE IF NOT EXISTS geocodes (city_key TEXT PRIMARY KEY, latitude REAL, longitude REAL, timestamp REAL)")
    @classmethod
    def load(cls): cls._init_db()
    @classmethod
    def get(cls, city_key: str) -> Optional[Dict[str, float]]:
        cls._init_db()
        with sqlite3.connect(cls._db_path) as conn:
            row = conn.execute("SELECT latitude, longitude FROM geocodes WHERE city_key = ?", (city_key,)).fetchone()
        return {"latitude": row[0], "longitude": row[1]} if row else None
    @classmethod
    def save(cls, city_key: str, location: Dict[str, float]):
        cls._init_db()
        with sqlite3.connect(cls._db_path) as conn:
            conn.execute("INSERT INTO geocodes (city_key, latitude, longitude, timestamp) VALUES (?, ?, ?, ?) ON CONFLICT(city_key) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, timestamp = excluded.timestamp",
                         (city_key, location["latitude"], location["longitude"], time.time()))

class PlaceIdCache:
    _db_path = Config.PLACE_ID_DB_FILE
    @classmethod
    def _init_db(cls):
        with sqlite3.connect(cls._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("CREATE TABLE IF NOT EXISTS places (place_id TEXT PRIMARY KEY, latitude REAL, longitude REAL, hub_name TEXT, timestamp REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hub_name ON places(hub_name);")
    @classmethod
    def load(cls): cls._init_db()
    @classmethod
    def get(cls, place_id: str) -> Optional[Dict[str, Any]]:
        cls._init_db()
        with sqlite3.connect(cls._db_path) as conn:
            row = conn.execute("SELECT latitude, longitude, hub_name FROM places WHERE place_id = ?", (place_id,)).fetchone()
        return {"latitude": row[0], "longitude": row[1], "hub_name": row[2]} if row else None
    @classmethod
    def save_many(cls, places: List[Place], hub_name: str):
        cls._init_db()
        records = [(p["id"], p["location"]["latitude"], p["location"]["longitude"], hub_name, time.time()) for p in places if p.get("id") and isinstance(p.get("location"), dict)]
        if not records: return
        with sqlite3.connect(cls._db_path) as conn:
            conn.executemany("INSERT INTO places (place_id, latitude, longitude, hub_name, timestamp) VALUES (?, ?, ?, ?, ?) ON CONFLICT(place_id) DO UPDATE SET latitude = excluded.latitude, longitude = excluded.longitude, hub_name = excluded.hub_name, timestamp = excluded.timestamp", records)

class DiskCache:
    _tile_mem_cache: Dict[str, List[Place]] = {}
    _mem_lock = threading.Lock()
    @staticmethod
    def _tile_key(lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, travel_mode: str) -> str:
        key_string = f"tile_{round(lat, 3)}_{round(lon, 3)}_{radius_m}_{'_'.join(sorted(types))}_{field_mask}_{travel_mode}"
        return hashlib.sha1(key_string.encode()).hexdigest()
    @staticmethod
    def _tile_path(key: str) -> Path: return Config.TILE_DIR / f"{key}.json"
    @classmethod
    def get_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, travel_mode: str) -> Optional[List[Place]]:
        key = cls._tile_key(lat, lon, radius_m, types, field_mask, travel_mode)
        path = cls._tile_path(key)
        with cls._mem_lock:
            if key in cls._tile_mem_cache:
                tracker.count_cache_hit()
                return cls._tile_mem_cache[key]
        if path.exists() and (time.time() - path.stat().st_mtime) < Config.TTL_30D:
            try:
                with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                with cls._mem_lock: cls._tile_mem_cache[key] = data
                tracker.count_cache_hit()
                return data
            except (json.JSONDecodeError, IOError): return None
        return None
    @classmethod
    def save_tile(cls, lat: float, lon: float, radius_m: int, types: Tuple[str, ...], field_mask: str, places: List[Place], travel_mode: str):
        key = cls._tile_key(lat, lon, radius_m, types, field_mask, travel_mode)
        path = cls._tile_path(key)
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(places, f, ensure_ascii=False)
        except IOError as e: logging.warning(f"Failed to save tile {path}: {e}")
        with cls._mem_lock: cls._tile_mem_cache[key] = places

# =============================================================================
# UTILITIES & API HELPERS (UNCHANGED)
# =============================================================================
def normalize_city_name(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_category_from_place(place: Place) -> str:
    types = place.get('types', [])
    name = place.get('displayName', {}).get('text', '').lower()
    if 'airport' in types: return "Airports"
    if 'beach' in types: return "Beaches & Waterfront"
    if 'historical_landmark' in types or 'historical_place' in types: return "Historical Sites"
    if 'buddhist_temple' in types or 'hindu_temple' in types or 'mosque' in types or 'church' in types: return "Temples & Religious Sites"
    if 'market' in types: return "Shopping & Markets"
    if 'zoo' in types or 'aquarium' in types: return "Zoos & Aquariums"
    if 'museum' in types or 'art_gallery' in types: return "Museums & Culture"
    if 'hike' in name or 'trail' in name or 'falls' in name or 'lookout' in name: return "Parks & Hiking"
    if 'park' in types or 'national_park' in types:
        if 'stadium' not in types: return "Parks & Hiking"
    if 'stadium' in types: return "Venues & Stadiums"
    if 'tourist_attraction' in types: return "Landmarks & Points of Interest"
    return "Other Attractions"

def _post_with_retry(payload: Dict, headers: Dict) -> Optional[Dict]:
    url = "https://places.googleapis.com/v1/places:searchNearby"
    for attempt in range(Config.MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if 500 <= resp.status_code < 600 or resp.status_code == 429:
                logging.warning(f"API returned {resp.status_code}. Retrying... (Attempt {attempt + 1})")
                time.sleep((2 ** attempt) + random.random())
                continue
            if resp.status_code != 200:
                logging.error(f"API request failed with status {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed after {attempt + 1} attempts: {e}")
            break
    return None

def places_nearby(lat: float, lon: float, radius_m: int, included_types: Tuple[str, ...], field_mask: str, origin: Optional[Dict] = None, travel_mode: str = "DRIVE") -> List[Place]:
    if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: return []
    cached = DiskCache.get_tile(lat, lon, radius_m, included_types, field_mask, travel_mode)
    if cached is not None: return cached
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": Config.API_KEY, "X-Goog-FieldMask": field_mask}
    payload: Dict[str, Any] = {
        "includedTypes": list(included_types), "maxResultCount": 20, "languageCode": "en",
        "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": float(min(radius_m, Config.MAX_NEARBY_RADIUS_M))}}
    }
    if origin: payload["routingParameters"] = {"origin": origin, "travelMode": travel_mode}
    all_places: List[Place] = []
    next_page_token = None
    while True:
        if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
        if next_page_token:
            payload["pageToken"] = next_page_token
            time.sleep(0.5 + random.random() * 0.5)
        tracker.count_call("places")
        data = _post_with_retry(payload, headers)
        if data:
            current_places, routing_summaries = data.get("places", []), data.get("routingSummaries", [])
            for i, p in enumerate(current_places):
                if i < len(routing_summaries): p["routingSummary"] = routing_summaries[i]
                if p.get("photos") and len(p["photos"]) > 0:
                    p["thumbnailUrl"] = f"https://places.googleapis.com/v1/{p['photos'][0]['name']}/media?key={Config.API_KEY}&maxWidthPx=1000"
                    del p["photos"]
            all_places.extend(current_places)
            next_page_token = data.get("nextPageToken")
            if not Config.PAGINATE or not next_page_token: break
        else: break
    DiskCache.save_tile(lat, lon, radius_m, included_types, field_mask, all_places, travel_mode)
    return all_places

def geocode_city(city_name: str) -> Dict[str, Any]:
    normalized_name = normalize_city_name(city_name)
    cached = GeocodeCache.get(normalized_name)
    if cached:
        tracker.count_cache_hit()
        return cached
    if not Config.API_KEY: return {"error": "Google API key is not configured."}
    tracker.count_call("geocode")
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        resp = requests.get(url, params={"address": city_name, "key": Config.API_KEY}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            result = {"latitude": loc["lat"], "longitude": loc["lng"]}
            GeocodeCache.save(normalized_name, result)
            return result
        return {"error": f"Geocoding API status: {data.get('status')}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Geocoding request failed: {e}"}

# =============================================================================
# QUADTREE ADAPTIVE SEARCH & OTHER CORE LOGIC... (UNCHANGED)
# =============================================================================
@dataclass
class Quadrant:
    min_lat: float; min_lon: float; max_lat: float; max_lon: float; depth: int
    @property
    def center(self) -> Tuple[float, float]: return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)
    @property
    def edge_km(self) -> float: return abs(self.max_lat - self.min_lat) * 111.0
    @property
    def inscribed_radius_m(self) -> int: return int(min((self.max_lat - self.min_lat) * 111_000.0 / 2.0, Config.MAX_NEARBY_RADIUS_M))
    def subdivide(self) -> List["Quadrant"]:
        mid_lat, mid_lon = self.center; d = self.depth + 1
        return [Quadrant(self.min_lat, self.min_lon, mid_lat, mid_lon, d), Quadrant(self.min_lat, mid_lon, mid_lat, self.max_lon, d),
                Quadrant(mid_lat, self.min_lon, self.max_lat, mid_lon, d), Quadrant(mid_lat, mid_lon, self.max_lat, self.max_lon, d)]

def get_budget_limit_for_depth(depth: int) -> int:
    if Config.PLACES_CALL_BUDGET is None: return float('inf')
    total_budget, weights = Config.PLACES_CALL_BUDGET, Config.LEVEL_BUDGET_WEIGHTS
    cumulative_weight = sum(weights.get(d, 0) for d in range(depth + 1))
    if depth not in weights and depth > max(weights.keys()):
        cumulative_weight = sum(weights.values()) + max(0, 1.0 - sum(weights.values()))
    return max(1, int(total_budget * min(1.0, cumulative_weight)))

def adaptive_quadtree_crawl(center_lat: float, center_lon: float, search_radius_km: float, origin: Dict, travel_mode: str) -> Tuple[List[Place], List[Place]]:
    q = deque([Quadrant(center_lat - (search_radius_km/111.0), center_lon - (search_radius_km/(111.320*math.cos(math.radians(center_lat))+1e-12)),
                         center_lat + (search_radius_km/111.0), center_lon + (search_radius_km/(111.320*math.cos(math.radians(center_lat))+1e-12)), 0)])
    cities: Dict[str, Place] = {}; attractions: Dict[str, Place] = {}; lock = threading.Lock()
    def process_quadrant(quad: Quadrant, search_origin: Dict, mode: str):
        if tracker.get_calls("places") >= get_budget_limit_for_depth(quad.depth):
            if quad.depth < 2: logging.warning(f"Budget limit for depth {quad.depth} reached. Halting this level.")
            return None, None
        can_split = not (quad.depth >= Config.QT_MAX_DEPTH or quad.edge_km <= Config.QT_MIN_EDGE_KM)
        lat, lon = quad.center
        base_radius_m = quad.inscribed_radius_m
        node_cities = places_nearby(lat, lon, base_radius_m, Config.TYPE_CITY, Config.MASK_CITY, search_origin, mode)
        for c in node_cities:
            if (name_obj := c.get("displayName")) and (name := name_obj.get("text")) and isinstance(loc := c.get("location"), dict):
                GeocodeCache.save(normalize_city_name(name), loc)
        attraction_radius_m = base_radius_m
        if Config.ADAPTIVE_RADIUS:
            if len(node_cities) >= Config.ADAPTIVE_HIGH_THRESHOLD: attraction_radius_m = int(base_radius_m * Config.ADAPTIVE_SHRINK_FACTOR)
            elif len(node_cities) <= Config.ADAPTIVE_LOW_THRESHOLD: attraction_radius_m = int(min(Config.MAX_NEARBY_RADIUS_M, base_radius_m * Config.ADAPTIVE_EXPAND_FACTOR))
        node_attrs: List[Place] = []
        if (len(node_cities) > 0) or (not can_split) or (not Config.TWO_PHASE_NODE):
            node_attrs = places_nearby(lat, lon, attraction_radius_m, Config.TYPE_ATTRACTION, Config.MASK_ATTRACTION, search_origin, mode)
        with lock:
            for p in node_cities:
                if p_id := p.get("id"): cities[p_id] = p
            for p in node_attrs:
                if p_id := p.get("id"): attractions[p_id] = p
        if can_split and (len(node_cities) + len(node_attrs)) >= Config.QT_SPLIT_THRESHOLD: return quad.subdivide(), quad.depth
        return None, quad.depth
    while q:
        if Config.PLACES_CALL_BUDGET is not None and tracker.get_calls("places") >= Config.PLACES_CALL_BUDGET: break
        logging.info(f"Processing level {q[0].depth} with {len(q)} quadrants...")
        quadrants_to_process = [q.popleft() for _ in range(len(q))]
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_to_quad = {executor.submit(process_quadrant, quad, origin, travel_mode): quad for quad in quadrants_to_process}
            for future in concurrent.futures.as_completed(future_to_quad):
                try:
                    if (result := future.result()) and (children := result[0]): q.extend(children)
                except Exception as e: logging.error(f"A quadrant processing task failed: {e}")
    return list(cities.values()), list(attractions.values())

@dataclass
class HubEntry:
    hub_name: str; centroid: Dict[str, float]; bounding_radius_km: float; cities: List[Place] = field(default_factory=list)
def calculate_centroid_and_radius(places: List[Place]) -> Tuple[Dict[str, float], float]:
    if not places: return {"latitude": 0, "longitude": 0}, 0
    lats = [p['location']['latitude'] for p in places if 'location' in p]
    lngs = [p['location']['longitude'] for p in places if 'location' in p]
    if not lats: return {"latitude": 0, "longitude": 0}, 0
    centroid = {"latitude": sum(lats) / len(lats), "longitude": sum(lngs) / len(lngs)}
    max_dist = max((haversine_km(centroid['latitude'], centroid['longitude'], p_lat, p_lng) for p_lat, p_lng in zip(lats, lngs)), default=0)
    return centroid, max_dist * 1.05
class CentralHubCache:
    _hubs: Dict[str, HubEntry] = {}
    @classmethod
    def load(cls):
        if not Config.CENTRAL_HUB_FILE.exists(): return
        try:
            with open(Config.CENTRAL_HUB_FILE, "r", encoding="utf-8") as f: cls._hubs = {name: HubEntry(**entry) for name, entry in json.load(f).items()}
            logging.info(f"Loaded {len(cls._hubs)} hubs from central cache.")
        except Exception as e: logging.error(f"Could not load central hub cache: {e}")
    @classmethod
    def find_matching_hub(cls, lat: float, lng: float) -> Optional[HubEntry]:
        for hub in cls._hubs.values():
            if haversine_km(lat, lng, hub.centroid['latitude'], hub.centroid['longitude']) <= hub.bounding_radius_km: return hub
        return None
    @classmethod
    def get_hub_attractions(cls, hub_name: str) -> Optional[List[Place]]:
        path = Config.HUB_ATTRACTIONS_DIR / f"{hub_name}.json"
        if not path.exists(): return None
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception as e:
            logging.error(f"Error reading hub attractions for '{hub_name}': {e}")
            return None
    @classmethod
    def save_hub(cls, hub_entry: HubEntry, attractions: List[Place]):
        cls._hubs[hub_entry.hub_name] = hub_entry
        for path, data in [(Config.CENTRAL_HUB_FILE, {n: h.__dict__ for n, h in cls._hubs.items()}), (Config.HUB_ATTRACTIONS_DIR / f"{hub_entry.hub_name}.json", attractions)]:
            temp_path = path.with_suffix(f"{path.suffix}.tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
                os.replace(temp_path, path)
            except IOError as e: logging.error(f"Could not save hub file {path}: {e}")
def _safe_get_rating(p: Dict) -> Optional[float]:
    try: return float(p.get("rating")) if p.get("rating") is not None else None
    except (ValueError, TypeError): return None
def _safe_get_count(p: Dict) -> int:
    try: return int(p.get("userRatingCount", 0) or 0)
    except (ValueError, TypeError): return 0
def add_rank_scores_to_places(places: List[Place]) -> List[Place]:
    if not places: return []
    C = sum(r for p in places if (r := _safe_get_rating(p)) is not None) / len(places) if places else 3.5
    max_v = max([_safe_get_count(p) for p in places] + [1])
    for p in places:
        R, v, d = _safe_get_rating(p), _safe_get_count(p), p.get("distance_to_query")
        if R is None: p["rank_score"] = 0.0; continue
        bayes_n = (v * R + Config.RATING_PRIOR_M * C) / (v + Config.RATING_PRIOR_M) / 5.0 if (v + Config.RATING_PRIOR_M) > 0 else C/5.0
        p_eff, n, z = R / 5.0, v, Config.WILSON_Z
        wilson = ((p_eff + z*z/(2*n) - z * math.sqrt((p_eff*(1-p_eff) + z*z/(4*n))/n))/(1 + z*z/n)) if n > 0 else 0.0
        dist_factor = math.exp(-(d or 0) / Config.DISTANCE_DECAY_KM)
        count_factor = math.log1p(v) / math.log1p(max_v)
        p["rank_score"] = (Config.BAYES_WEIGHT * bayes_n + Config.WILSON_WEIGHT * wilson + 
                         Config.DIST_WEIGHT * dist_factor + Config.COUNT_WEIGHT * count_factor)
    return places
def structure_and_categorize_places(places: List[Place]) -> Dict[str, List[Dict[str, Any]]]:
    if not places: return {}
    places = [p for p in places if _safe_get_count(p) >= Config.MIN_REVIEW_COUNT or 'airport' in p.get('types', [])]
    places.sort(key=lambda p: _safe_get_count(p), reverse=True)
    unique_places_map: Dict[str, Place] = {}
    processed_for_dupes = set()
    for i, p1 in enumerate(places):
        if (p1_id := p1.get('id')) and p1_id not in processed_for_dupes:
            unique_places_map[p1_id] = p1
            processed_for_dupes.add(p1_id)
            for j in range(i + 1, len(places)):
                p2 = places[j]
                if (p2_id := p2.get('id')) and p2_id not in processed_for_dupes:
                    if 'location' not in p1 or 'location' not in p2: continue
                    dist = haversine_km(p1['location']['latitude'], p1['location']['longitude'], p2['location']['latitude'], p2['location']['longitude'])
                    name1, name2 = p1.get('displayName', {}).get('text', ''), p2.get('displayName', {}).get('text', '')
                    if SequenceMatcher(None, name1, name2).ratio() > 0.8 and dist < 0.5:
                        processed_for_dupes.add(p2_id)
    unique_places = list(unique_places_map.values())
    parent_keywords = {'national park': 50.0, 'state park': 30.0, 'seattle center': 1.0, 'campus': 2.0, 'center': 1.5}
    structured_list: List[Dict[str, Any]] = [{"parent": p, "children": []} for p in unique_places]
    for item in structured_list:
        parent = item['parent']
        p_name = parent.get('displayName', {}).get('text', '').lower()
        for keyword, radius_km in parent_keywords.items():
            if keyword in p_name:
                for other_item in structured_list:
                    child = other_item['parent']
                    if parent['id'] == child['id'] or 'location' not in parent or 'location' not in child: continue
                    if haversine_km(parent['location']['latitude'], parent['location']['longitude'], child['location']['latitude'], child['location']['longitude']) < radius_km:
                        item['children'].append(child)
                item['children'].sort(key=lambda p: p.get('rank_score', 0), reverse=True)
                break
    final_categorized: Dict[str, List[Dict[str, Any]]] = {}
    for item in structured_list:
        category = get_category_from_place(item['parent'])
        final_categorized.setdefault(category, []).append(item)
    for category in final_categorized:
        final_categorized[category].sort(key=lambda i: i['parent'].get('rank_score', 0), reverse=True)
    return final_categorized

# =============================================================================
# MAIN FLOW & HELPERS
# =============================================================================
def perform_full_crawl(user_query_city: str, center: Dict, search_radius_km: float, travel_mode: str) -> Tuple[List[Place], List[Place]]:
    logging.info("Performing full adaptive search (this may take a moment)...")
    city_list, all_attractions = adaptive_quadtree_crawl(center["latitude"], center["longitude"], search_radius_km, origin=center, travel_mode=travel_mode)
    if all_attractions:
        logging.info("Calculating distance for all new attractions...")
        for att in all_attractions:
            if loc := att.get('location'):
                att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
        logging.info("Calculating and adding rank scores before caching...")
        all_attractions = add_rank_scores_to_places(all_attractions)
        hub_name = normalize_city_name(user_query_city)
        PlaceIdCache.save_many(all_attractions, hub_name)
        PlaceIdCache.save_many(city_list, hub_name)
        centroid, radius = calculate_centroid_and_radius(all_attractions + city_list)
        new_hub = HubEntry(hub_name=hub_name, centroid=centroid, bounding_radius_km=radius, cities=city_list)
        CentralHubCache.save_hub(new_hub, all_attractions)
        logging.info(f"Created and cached new hub '{hub_name}' with {len(all_attractions)} scored attractions.")
    return city_list, all_attractions

def main(user_query_city: str, search_radius_km: Optional[float] = None, travel_mode: str = "DRIVE"):
    if search_radius_km is None: search_radius_km = Config.DEFAULT_SEARCH_RADIUS_KM
    logging.info(f"\n===== Searching for '{user_query_city}' with travel mode '{travel_mode}' =====")
    
    global tracker
    tracker = APITracker()
    GeocodeCache.load(); CentralHubCache.load()
    center = geocode_city(user_query_city)
    if "error" in center:
        logging.critical(f"Could not geocode '{user_query_city}'. {center['error']}")
        return

    city_list, all_attractions = [], []
    if matching_hub := CentralHubCache.find_matching_hub(center['latitude'], center['longitude']):
        logging.info(f"CACHE HIT (L1): Query falls within the '{matching_hub.hub_name}' hub.")
        tracker.count_cache_hit()
        city_list, all_attractions = matching_hub.cities, CentralHubCache.get_hub_attractions(matching_hub.hub_name) or []
    else:
        logging.info("CACHE MISS (L1): Query is outside all known hub boundaries.")
        city_list, all_attractions = perform_full_crawl(user_query_city, center, search_radius_km, travel_mode)

    if not all_attractions:
        logging.warning("No attractions found.")
        return

    for att in all_attractions:
        if loc := att.get('location'):
            att['distance_to_query'] = haversine_km(center['latitude'], center['longitude'], loc.get('latitude', 0.0), loc.get('longitude', 0.0))
    all_attractions = add_rank_scores_to_places(all_attractions)
    
    logging.info(f"\nFound {len(all_attractions)} total attractions. Now structuring and categorizing...")
    categorized_results = structure_and_categorize_places(all_attractions)

    # try:
    #     with open("attractions_output.json", "w", encoding="utf-8") as f:
    #         json.dump(categorized_results, f, ensure_ascii=False, indent=4)
    #     logging.info("JSON output saved to attractions_output.json")
    # except IOError as e:
    #     logging.error(f"Could not save JSON output: {e}")

    print("\n" + "="*50 + f"\n ✨ Curated Attractions for {user_query_city} ✨\n" + "="*50)
    for category in sorted(categorized_results.keys()):
        items = categorized_results[category]
        print(f"\n--- 🏛️ {category} ---")
        for item in items:
            parent = item['parent']
            p_name = parent.get("displayName", {}).get("text", "<unknown>")
            p_rating = parent.get("rating", "N/A")
            p_cnt = _safe_get_count(parent)
            p_dist = parent.get('distance_to_query', -1)
            
            travel_time_str = ""
            if (rs := parent.get("routingSummary")) and rs.get("legs"):
                duration_min = int(rs["legs"][0].get("duration", "0s").replace('s', '')) // 60
                if duration_min > 0: travel_time_str = f" (~{duration_min} min {travel_mode.lower()})"
            print(f"\n📍 {p_name} (Rating: {p_rating}, {p_cnt:,} reviews) - {p_dist:.1f} km away{travel_time_str}")

            info_parts = []
            if price := parent.get('priceLevel'):
                info_parts.append(f"Price: {price.replace('PRICE_LEVEL_', '').title()}")
            if parent.get('goodForGroups'):
                info_parts.append("🧑‍🤝‍🧑 Good for Groups")
            
            if website := parent.get('websiteUri'):
                print(f"   🌐 Website: {website}")
            if info_parts:
                print(f"   ✨ {' | '.join(info_parts)}")
            
            if summary := parent.get("generativeSummary", {}).get("text"):
                print(f"   📝 Summary: {summary}")

    s = tracker.summary()
    print("\n" + "="*50 + f"\nSESSION SUMMARY for {user_query_city.title()}\n" + "="*50)
    print(f"Total Time Taken: {s['total_time_seconds']} seconds")
    print(f"Total API Calls:  {s['total_api_calls']}")
    print(f"  - Geocoding:    {s['breakdown'].get('geocode', 0)}")
    print(f"  - Places:       {s['breakdown'].get('places', 0)}")
    print(f"Cache Hits:       {s['cache_hits']}")
    print("="*50)

# =============================================================================
# RUNNER
# =============================================================================
# if __name__ == "__main__":
#     if not Config.API_KEY:
#         raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

#     try:
#         while True:
#             city = input("\nEnter a city name to search for (or 'quit' to exit): ")
#             if city.lower() in ['quit', 'exit']:
#                 break
#             if not city:
#                 print("Please enter a valid city name.")
#                 continue
            
#             main(city, travel_mode="DRIVE")

#     except Exception as e:
#         logging.critical(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    if not Config.API_KEY:
        raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env file. Please check your setup.")

    # Allows running from command line like: python final_engine.py "san diego"
    if len(sys.argv) > 1:
        city_to_run = sys.argv[1]
        print(f"Engine started for city: {city_to_run}")
        main(city_to_run)
    else:
        # Keep the interactive mode for testing the engine directly
        try:
            while True:
                city = input("\nEnter a city name to search for (or 'quit' to exit): ")
                if city.lower() in ['quit', 'exit']:
                    break
                if city:
                    main(city)
                else:
                    print("Please enter a valid city name.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred: {e}", exc_info=True)