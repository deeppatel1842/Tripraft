#!/usr/bin/env python3
"""
Places Engine - Full Automation Pipeline

Executes the complete data preparation workflow:
1. Apply ranking scores to all places
2. Add Wikimedia photos (where missing)
3. Normalize JSON attributes to PLACE_SCHEMA
4. Prepare dataset for upload
5. Upload to Firebase Firestore

Usage:
    python -m places_engine.pipeline.run_full_pipeline [options]

Options:
    --source PATH       Source data directory (default: dataset/a)
    --skip-photos       Skip photo enrichment step
    --skip-upload       Skip Firebase upload step
    --dry-run          Simulate without writing files
    --verbose          Show detailed progress
"""

import argparse
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: RANKING SCORE CALCULATION
# ============================================================

RANK_WEIGHTS = {
    "tourist_priority": 0.45,
    "traveler_experience": 0.25,
    "cost": 0.05,
    "duration": 0.10,
    "tags": 0.15,
}

TAG_BOOSTS = {
    "Landmark": 0.10, "Viewpoint": 0.07, "Nature": 0.07,
    "Museum": 0.07, "Art": 0.07, "Culture": 0.06,
    "Historic": 0.06, "Architecture": 0.05,
    "Beach": 0.05, "Mountain": 0.05, "Park": 0.05,
    "Shopping": 0.04, "Food": 0.04, "Market": 0.04,
    "Lake": 0.03, "Trail": 0.03, "Nightlife": 0.03,
    "Garden": 0.05, "Photography": 0.04, "Hike": 0.05,
    "Outdoors": 0.04, "Entertainment": 0.04, "Adventure": 0.05,
    "Wildlife": 0.05, "Religious": 0.04, "Palace": 0.06,
    "Temple": 0.05, "Castle": 0.06, "Festival": 0.04,
    "Island": 0.05, "Waterfall": 0.06, "Cave": 0.05,
    "Volcano": 0.06, "Desert": 0.05, "Forest": 0.05,
}


def clamp01(x: float) -> float:
    """Clamp value between 0 and 1."""
    return max(0.0, min(1.0, x))


def normalize_rating(v: Optional[float]) -> float:
    """Normalize rating to 0-1 scale."""
    if v is None:
        return 0.8
    return clamp01(v / 5.0)


def cost_score(cost: Optional[str]) -> float:
    """Calculate cost score."""
    if not cost:
        return 0.8
    cost = cost.lower()
    if "free" in cost:
        return 1.0
    if "paid" in cost or "ticket" in cost:
        return 0.7
    if "varies" in cost:
        return 0.65
    return 0.8


def parse_duration_minutes(text: Optional[str]) -> float:
    """Parse duration text to minutes."""
    if not text:
        return 120
    text = text.lower().strip()
    h_m = re.findall(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|h)", text)
    m_m = re.findall(r"(\d+(?:\.\d+)?)\s*(?:minute|min|m)", text)
    if len(h_m) == 2:
        return (float(h_m[0]) + float(h_m[1])) / 2 * 60
    if len(h_m) == 1:
        return float(h_m[0]) * 60
    if len(m_m) == 2:
        return (float(m_m[0]) + float(m_m[1])) / 2
    if len(m_m) == 1:
        return float(m_m[0])
    return 120


def duration_score(duration_text: Optional[str]) -> float:
    """Calculate duration score (ideal: 2-3 hours)."""
    mins = parse_duration_minutes(duration_text)
    mu, sigma = 150, 120
    z = (mins - mu) / sigma
    score = math.exp(-0.5 * z ** 2)
    return clamp01(0.5 * score + 0.25)


def tag_boost(tags: Optional[List[str]]) -> float:
    """Calculate tag boost score."""
    if not tags:
        return 0.0
    total = sum(TAG_BOOSTS.get(tag, 0.0) for tag in tags)
    return clamp01(total)


def compute_rank_score(place: Dict) -> float:
    """Calculate overall rank score for a place."""
    rt = normalize_rating(place.get("rating_tourist_priority", 4))
    re = normalize_rating(place.get("rating_traveler_experience", 4))
    c = cost_score(place.get("cost", ""))
    d = duration_score(place.get("suggested_duration", ""))
    t = tag_boost(place.get("tags", []))

    rank = (
        RANK_WEIGHTS["tourist_priority"] * rt +
        RANK_WEIGHTS["traveler_experience"] * re +
        RANK_WEIGHTS["cost"] * c +
        RANK_WEIGHTS["duration"] * d +
        RANK_WEIGHTS["tags"] * t
    )
    return round(clamp01(rank), 4)


# ============================================================
# STEP 2: PHOTO ENRICHMENT (Wikimedia Commons)
# ============================================================

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def get_wikimedia_photo(
    name: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    thumb_width: int = 800
) -> Optional[Dict]:
    """Fetch photo from Wikimedia Commons."""
    if not REQUESTS_AVAILABLE:
        return None
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "TripRaftBot/2.0 (tripraft@example.com)"
    })
    
    wiki_api = "https://en.wikipedia.org/w/api.php"
    commons_api = "https://commons.wikimedia.org/w/api.php"
    
    try:
        # Search Wikipedia
        pageid = None
        
        # Try geosearch first
        if lat and lng:
            params = {
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{lat}|{lng}",
                "gsradius": 1500,
                "gslimit": 5,
                "format": "json"
            }
            resp = session.get(wiki_api, params=params, timeout=10)
            hits = resp.json().get("query", {}).get("geosearch", [])
            if hits:
                # Find best match by name
                norm_name = re.sub(r"[^a-z0-9]+", "", name.lower())
                best = None
                best_score = -1
                for h in hits:
                    cand = re.sub(r"[^a-z0-9]+", "", h.get("title", "").lower())
                    score = sum(1 for c1, c2 in zip(norm_name, cand) if c1 == c2)
                    if score > best_score:
                        best = h
                        best_score = score
                if best:
                    pageid = best.get("pageid")
        
        # Fall back to text search
        if not pageid:
            query = name
            if city and country:
                query = f"{name} {city} {country}"
            elif city:
                query = f"{name} {city}"
            
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json"
            }
            resp = session.get(wiki_api, params=params, timeout=10)
            hits = resp.json().get("query", {}).get("search", [])
            if hits:
                pageid = hits[0].get("pageid")
        
        if not pageid:
            return None
        
        # Get page image
        params = {
            "action": "query",
            "prop": "pageimages|pageprops",
            "ppprop": "page_image",
            "piprop": "original",
            "pageids": pageid,
            "format": "json"
        }
        resp = session.get(wiki_api, params=params, timeout=10)
        pages = resp.json().get("query", {}).get("pages", {})
        page = pages.get(str(pageid), {})
        
        page_image = (page.get("pageprops") or {}).get("page_image")
        if not page_image:
            return None
        
        filename = f"File:{page_image}" if not page_image.startswith("File:") else page_image
        
        # Get Commons info
        params = {
            "action": "query",
            "prop": "imageinfo",
            "titles": filename,
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": thumb_width,
            "format": "json"
        }
        resp = session.get(commons_api, params=params, timeout=10)
        pages = resp.json().get("query", {}).get("pages", {})
        
        if not pages:
            return None
        
        page = next(iter(pages.values()))
        infos = page.get("imageinfo", [])
        if not infos:
            return None
        
        info = infos[0]
        meta = info.get("extmetadata", {}) or {}
        
        def get_meta(k):
            return (meta.get(k, {}) or {}).get("value")
        
        def strip_html(s):
            if not s:
                return s
            return re.sub(r"<[^>]+>", "", s).strip()
        
        return {
            "source_file": filename,
            "thumbnail": {
                "url": info.get("thumburl") or info.get("url"),
                "width": info.get("thumbwidth") or info.get("width"),
                "height": info.get("thumbheight") or info.get("height"),
                "attribution": {
                    "title": strip_html(get_meta("ObjectName")) or filename.replace("File:", ""),
                    "author": strip_html(get_meta("Artist")),
                    "license": get_meta("LicenseShortName"),
                    "license_url": get_meta("LicenseUrl"),
                    "source_url": f"https://commons.wikimedia.org/wiki/{filename.replace(' ', '_')}"
                }
            }
        }
    except Exception as e:
        logger.debug(f"Photo fetch failed for {name}: {e}")
        return None


# ============================================================
# STEP 3: NORMALIZE JSON ATTRIBUTES
# ============================================================

# Standard attribute schema
PLACE_SCHEMA = {
    "id": str,
    "name": str,
    "name_english": str,
    "description": str,
    "tags": list,
    "category": str,
    "latitude": float,
    "longitude": float,
    "city": str,
    "state": str,
    "country": str,
    "cost": str,
    "suggested_duration": str,
    "best_time_to_visit": str,
    "photos": dict,
    "rank_score": float,
    "search_text": str,
    "created_at": str,
    "updated_at": str,
}

# Invalid photo patterns
INVALID_PHOTO_PATTERNS = [
    r"commons-logo",
    r"flag_of_",
    r"coat_of_arms",
    r"ambox_",
    r"airplane_silhouette",
    r"question_book",
    r"wiki-",
    r"edit-clear",
    r"symbol_",
    r"icon_",
    r"pictogram",
    r"\.svg$",
    r"no_image",
    r"placeholder",
    r"default_",
    r"missing_",
]


def is_valid_photo_url(url: Optional[str]) -> bool:
    """Check if photo URL is valid (not a placeholder)."""
    if not url:
        return False
    url_lower = url.lower()
    for pattern in INVALID_PHOTO_PATTERNS:
        if re.search(pattern, url_lower):
            return False
    return True


def normalize_string(s: Any) -> str:
    """Clean and normalize a string."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return " ".join(s.split()).strip()


def generate_place_id(name: str, city: str, country: str, lat: float = None, lng: float = None) -> str:
    """Generate unique short numeric ID for a place.
    
    Format: P{8-digit-hash}
    Uses hash of name+city+country+coords for uniqueness.
    """
    import hashlib
    
    # Create unique string from place attributes
    unique_str = f"{name}|{city}|{country}|{lat or 0}|{lng or 0}".lower()
    
    # Generate hash and take first 8 chars of hex
    hash_val = hashlib.md5(unique_str.encode()).hexdigest()[:8]
    
    return f"P{hash_val.upper()}"


def generate_city_id(city: str, country: str) -> str:
    """Generate unique short ID for a city.
    
    Format: C{6-digit-hash}
    """
    import hashlib
    
    unique_str = f"{city}|{country}".lower()
    hash_val = hashlib.md5(unique_str.encode()).hexdigest()[:6]
    
    return f"C{hash_val.upper()}"


def generate_country_id(country: str) -> str:
    """Generate unique short ID for a country.
    
    Format: CO{4-digit-hash}
    """
    import hashlib
    
    unique_str = country.lower()
    hash_val = hashlib.md5(unique_str.encode()).hexdigest()[:4]
    
    return f"CO{hash_val.upper()}"


def generate_search_text(place: Dict) -> str:
    """Generate searchable text from place data."""
    parts = [
        place.get("name", ""),
        place.get("name_english", ""),
        place.get("city", ""),
        place.get("state", ""),
        place.get("country", ""),
        place.get("category", ""),
        place.get("description", "")[:200] if place.get("description") else "",
    ]
    tags = place.get("tags", [])
    if tags:
        parts.extend(tags)
    
    text = " ".join(filter(None, parts))
    return normalize_string(text).lower()


def normalize_place(place: Dict, city: str, state: str, country: str) -> Dict:
    """Normalize place data - PRESERVE ALL ORIGINAL DATA."""
    # Start with a copy of ALL original data
    normalized = dict(place)
    
    # Extract coordinates (handle both formats)
    coords = place.get("coordinates", {}) or {}
    lat = coords.get("lat") or coords.get("latitude")
    lng = coords.get("lng") or coords.get("longitude")
    
    # Generate unique short ID
    name = normalize_string(place.get("name", ""))
    normalized["id"] = generate_place_id(name, city, country, lat, lng)
    
    # Also store the readable slug for reference
    slug = f"{name}_{city}_{country}".lower()
    normalized["slug"] = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")[:100]
    
    # Ensure required fields exist
    normalized["name"] = name
    normalized["name_english"] = normalize_string(place.get("name_english", name))
    normalized["name_native"] = place.get("name_native", "")
    
    # Location fields
    normalized["latitude"] = float(lat) if lat is not None else None
    normalized["longitude"] = float(lng) if lng is not None else None
    normalized["coordinates"] = {"latitude": lat, "longitude": lng} if lat and lng else None
    normalized["city"] = normalize_string(city)
    normalized["state"] = normalize_string(state)
    normalized["country"] = normalize_string(country)
    normalized["address"] = place.get("address", "")
    
    # Content fields - preserve all
    normalized["ai_summary"] = place.get("ai_summary", "")
    normalized["description"] = normalize_string(place.get("description", place.get("ai_summary", "")))
    normalized["place_tip"] = place.get("place_tip", "")
    normalized["tags"] = place.get("tags", []) or []
    normalized["category"] = normalize_string(place.get("category", ""))
    
    # Time/cost fields
    normalized["cost"] = normalize_string(place.get("cost", ""))
    normalized["suggested_duration"] = normalize_string(place.get("suggested_duration", ""))
    normalized["best_time_to_visit"] = normalize_string(place.get("best_time_to_visit", ""))
    normalized["opening_hours"] = place.get("opening_hours", {})
    normalized["advanced_booking"] = place.get("advanced_booking", "")
    
    # Rating fields
    normalized["rating_tourist_priority"] = place.get("rating_tourist_priority")
    normalized["rating_traveler_experience"] = place.get("rating_traveler_experience")
    normalized["rank_score"] = place.get("rank_score", 0.5)
    
    # View fields
    normalized["sunrise_view"] = place.get("sunrise_view", False)
    normalized["sunset_view"] = place.get("sunset_view", False)
    normalized["sunrise_time"] = place.get("sunrise_time")
    normalized["sunset_time"] = place.get("sunset_time")
    
    # External links
    normalized["official_website"] = place.get("official_website", "")
    normalized["nearest_airport"] = place.get("nearest_airport", "")
    
    # Photos - validate and clean
    photos = place.get("photos", {})
    if isinstance(photos, dict):
        cleaned_photos = {}
        # Keep wikimedia_commons if valid
        wc = photos.get("wikimedia_commons", {})
        if wc and isinstance(wc, dict):
            thumb_url = (wc.get("thumbnail") or {}).get("url")
            if is_valid_photo_url(thumb_url):
                cleaned_photos["wikimedia_commons"] = wc
        # Keep osm and wikipedia arrays
        if photos.get("osm"):
            cleaned_photos["osm"] = photos["osm"]
        if photos.get("wikipedia"):
            cleaned_photos["wikipedia"] = photos["wikipedia"]
        normalized["photos"] = cleaned_photos
    else:
        normalized["photos"] = {}
    
    # Add search text for querying
    normalized["search_text"] = generate_search_text(normalized)
    
    # Add timestamps
    now = datetime.utcnow().isoformat() + "Z"
    normalized["created_at"] = place.get("created_at", now)
    normalized["updated_at"] = now
    
    return normalized


# ============================================================
# MAIN PIPELINE
# ============================================================

class FullPipeline:
    """Complete data preparation pipeline."""
    
    def __init__(
        self,
        source_path: str,
        fallback_path: str = None,
        output_path: str = None,
        skip_photos: bool = False,
        dry_run: bool = False,
        verbose: bool = False
    ):
        self.source_path = Path(source_path)
        self.fallback_path = Path(fallback_path) if fallback_path else None
        self.output_path = Path(output_path) if output_path else self.source_path.parent / "prepared_data"
        self.skip_photos = skip_photos
        self.dry_run = dry_run
        self.verbose = verbose
        
        self.stats = {
            "files_processed": 0,
            "places_total": 0,
            "ranks_applied": 0,
            "photos_added": 0,
            "places_normalized": 0,
            "fallback_used": 0,
            "errors": [],
        }
    
    def find_json_files(self) -> List[Path]:
        """Find all JSON files in source directory."""
        files = []
        for item in self.source_path.rglob("*.json"):
            if item.is_file() and not item.name.startswith("."):
                files.append(item)
        return sorted(files)
    
    def find_fallback_file(self, filepath: Path) -> Optional[Path]:
        """Find matching fallback file for empty/missing source file."""
        if not self.fallback_path:
            return None
        
        # Get relative path from source
        try:
            rel_path = filepath.relative_to(self.source_path)
        except ValueError:
            return None
        
        # Try exact match in fallback
        fallback_file = self.fallback_path / rel_path
        if fallback_file.exists():
            return fallback_file
        
        # Try case-insensitive match (folder names may differ)
        country_folder = filepath.parent.name.lower()
        filename = filepath.name.lower()
        
        for folder in self.fallback_path.iterdir():
            if folder.is_dir() and folder.name.lower() == country_folder:
                for f in folder.iterdir():
                    if f.name.lower() == filename:
                        return f
        
        return None
    
    def is_file_empty(self, data: Dict) -> bool:
        """Check if file has no places data."""
        for city_data in data.get("cities", []):
            if city_data.get("places", []):
                return False
        return True
    
    def process_file(self, filepath: Path) -> Tuple[List[Dict], Dict, bool]:
        """Process a single JSON file. Returns (places, stats, used_fallback)."""
        places = []
        file_stats = {"places": 0, "ranks": 0, "photos": 0}
        used_fallback = False
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if file is empty and try fallback
            if self.is_file_empty(data) and self.fallback_path:
                fallback_file = self.find_fallback_file(filepath)
                if fallback_file:
                    logger.info(f"  -> Using fallback: {fallback_file.name}")
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    used_fallback = True
            
            country = data.get("country", filepath.parent.name)
            state = data.get("state", filepath.stem)
            
            for city_data in data.get("cities", []):
                city_name = city_data.get("city", "")
                nearest_airport = city_data.get("nearest_airport", "")
                
                for place in city_data.get("places", []):
                    file_stats["places"] += 1
                    
                    # Add nearest_airport from city to place
                    if nearest_airport:
                        place["nearest_airport"] = nearest_airport
                    
                    # Step 1: Apply rank score
                    if "rank_score" not in place or place.get("rank_score") is None:
                        place["rank_score"] = compute_rank_score(place)
                        file_stats["ranks"] += 1
                    
                    # Step 2: Add photo if missing
                    if not self.skip_photos:
                        photos = place.get("photos", {})
                        has_valid_photo = False
                        if isinstance(photos, dict):
                            wc = photos.get("wikimedia_commons", {})
                            if wc and isinstance(wc, dict):
                                thumb_url = (wc.get("thumbnail") or {}).get("url")
                                has_valid_photo = is_valid_photo_url(thumb_url)
                        
                        if not has_valid_photo:
                            coords = place.get("coordinates", {}) or {}
                            photo = get_wikimedia_photo(
                                name=place.get("name_english") or place.get("name", ""),
                                lat=coords.get("lat") or coords.get("latitude"),
                                lng=coords.get("lng") or coords.get("longitude"),
                                city=city_name,
                                country=country
                            )
                            if photo:
                                if "photos" not in place:
                                    place["photos"] = {}
                                place["photos"]["wikimedia_commons"] = photo
                                file_stats["photos"] += 1
                            
                            # Rate limit
                            time.sleep(0.3)
                    
                    # Step 3: Normalize (preserves ALL data)
                    normalized = normalize_place(place, city_name, state, country)
                    places.append(normalized)
            
            return places, file_stats, used_fallback
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            self.stats["errors"].append(str(filepath))
            return [], file_stats, False
    
    def run(self) -> Dict:
        """Execute the full pipeline."""
        logger.info("=" * 70)
        logger.info("PLACES ENGINE - FULL AUTOMATION PIPELINE")
        logger.info("=" * 70)
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No files will be written")
        
        logger.info(f"Source: {self.source_path}")
        if self.fallback_path:
            logger.info(f"Fallback: {self.fallback_path}")
        
        # Find all files
        json_files = self.find_json_files()
        logger.info(f"Found {len(json_files)} JSON files in {self.source_path}")
        
        if not json_files:
            logger.warning("No JSON files found!")
            return self.stats
        
        # Process each file
        all_places = []
        cities_data = {}
        countries_data = {}
        
        for i, filepath in enumerate(json_files, 1):
            rel_path = filepath.relative_to(self.source_path)
            logger.info(f"[{i}/{len(json_files)}] Processing {rel_path}")
            
            places, file_stats, used_fallback = self.process_file(filepath)
            
            self.stats["files_processed"] += 1
            self.stats["places_total"] += file_stats["places"]
            self.stats["ranks_applied"] += file_stats["ranks"]
            self.stats["photos_added"] += file_stats["photos"]
            self.stats["places_normalized"] += len(places)
            if used_fallback:
                self.stats["fallback_used"] += 1
            
            all_places.extend(places)
            
            # Build city/country indices
            for place in places:
                city = place.get("city", "")
                country = place.get("country", "")
                state = place.get("state", "")
                nearest_airport = place.get("nearest_airport", "")
                
                # City index - with unique short ID
                city_key = f"{city}_{country}".lower()
                if city_key not in cities_data:
                    cities_data[city_key] = {
                        "id": generate_city_id(city, country),
                        "slug": re.sub(r"[^a-z0-9]+", "_", city_key).strip("_"),
                        "city": city,
                        "state": state,
                        "country": country,
                        "nearest_airport": nearest_airport,
                        "place_count": 0,
                    }
                elif nearest_airport and not cities_data[city_key].get("nearest_airport"):
                    # Update if we find nearest_airport later
                    cities_data[city_key]["nearest_airport"] = nearest_airport
                cities_data[city_key]["place_count"] += 1
                
                # Country index - with unique short ID
                if country not in countries_data:
                    countries_data[country] = {
                        "id": generate_country_id(country),
                        "slug": re.sub(r"[^a-z0-9]+", "_", country.lower()).strip("_"),
                        "country": country,
                        "city_count": 0,
                        "place_count": 0,
                    }
                countries_data[country]["place_count"] += 1
            
            if self.verbose:
                fb = " (fallback)" if used_fallback else ""
                logger.info(f"  -> {file_stats['places']} places, {file_stats['ranks']} ranks, {file_stats['photos']} photos{fb}")
        
        # Count unique cities per country
        for city_data in cities_data.values():
            country = city_data["country"]
            if country in countries_data:
                countries_data[country]["city_count"] += 1
        
        # Save prepared data
        if not self.dry_run:
            self.output_path.mkdir(parents=True, exist_ok=True)
            
            # Save places
            places_file = self.output_path / "places.json"
            with open(places_file, "w", encoding="utf-8") as f:
                json.dump(all_places, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(all_places)} places to {places_file}")
            
            # Save cities
            cities_file = self.output_path / "cities.json"
            with open(cities_file, "w", encoding="utf-8") as f:
                json.dump(list(cities_data.values()), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(cities_data)} cities to {cities_file}")
            
            # Save countries
            countries_file = self.output_path / "countries.json"
            with open(countries_file, "w", encoding="utf-8") as f:
                json.dump(list(countries_data.values()), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(countries_data)} countries to {countries_file}")
            
            # Save ID mappings for reference
            mappings = {
                "places": {p["id"]: {"name": p.get("name"), "slug": p.get("slug"), "city": p.get("city"), "country": p.get("country")} for p in all_places},
                "cities": {c["id"]: {"city": c.get("city"), "slug": c.get("slug"), "country": c.get("country")} for c in cities_data.values()},
                "countries": {c["id"]: {"country": c.get("country"), "slug": c.get("slug")} for c in countries_data.values()},
            }
            mappings_file = self.output_path / "id_mappings.json"
            with open(mappings_file, "w", encoding="utf-8") as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved ID mappings to {mappings_file}")
            
            # Save stats
            stats_file = self.output_path / "stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "pipeline_stats": self.stats,
                    "summary": {
                        "total_places": len(all_places),
                        "total_cities": len(cities_data),
                        "total_countries": len(countries_data),
                    }
                }, f, ensure_ascii=False, indent=2)
        
        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Fallback files used: {self.stats['fallback_used']}")
        logger.info(f"Total places: {self.stats['places_total']}")
        logger.info(f"Rank scores applied: {self.stats['ranks_applied']}")
        logger.info(f"Photos added: {self.stats['photos_added']}")
        logger.info(f"Places normalized: {self.stats['places_normalized']}")
        logger.info(f"Cities: {len(cities_data)}")
        logger.info(f"Countries: {len(countries_data)}")
        
        if self.stats["errors"]:
            logger.warning(f"Errors: {len(self.stats['errors'])} files")
        
        logger.info(f"\nOutput: {self.output_path}")
        
        return self.stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Places Engine - Full Automation Pipeline"
    )
    parser.add_argument(
        "--source",
        default="dataset/countries",
        help="Primary source data directory (default: dataset/countries)"
    )
    parser.add_argument(
        "--fallback",
        default="dataset/a",
        help="Fallback source for empty files (default: dataset/a)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: places_engine/pipeline/prepared_data)"
    )
    parser.add_argument(
        "--skip-photos",
        action="store_true",
        help="Skip photo enrichment step"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip Firebase upload step"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without writing files"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    backend_dir = Path(__file__).parent.parent.parent
    source_path = backend_dir / args.source
    fallback_path = backend_dir / args.fallback if args.fallback else None
    output_path = Path(args.output) if args.output else backend_dir / "places_engine" / "pipeline" / "prepared_data"
    
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_path}")
        sys.exit(1)
    
    if fallback_path and not fallback_path.exists():
        logger.warning(f"Fallback directory not found: {fallback_path}")
        fallback_path = None
    
    # Run pipeline
    pipeline = FullPipeline(
        source_path=str(source_path),
        output_path=str(output_path),
        fallback_path=str(fallback_path) if fallback_path else None,
        skip_photos=args.skip_photos,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    stats = pipeline.run()
    
    # Upload to Firebase if not skipped
    if not args.skip_upload and not args.dry_run:
        logger.info("")
        logger.info("=" * 70)
        logger.info("UPLOADING TO FIREBASE")
        logger.info("=" * 70)
        
        try:
            from places_engine.pipeline.upload_to_firestore import FirestoreUploader
            
            uploader = FirestoreUploader(prepared_data_path=str(output_path))
            upload_results = uploader.run(dry_run=False)
            
            logger.info("")
            logger.info("UPLOAD COMPLETE")
            logger.info(f"Places uploaded: {upload_results.get('places_uploaded', 0)}")
            logger.info(f"Cities uploaded: {upload_results.get('cities_uploaded', 0)}")
            logger.info(f"Countries uploaded: {upload_results.get('countries_uploaded', 0)}")
            
        except ImportError as e:
            logger.error(f"Firebase upload failed: {e}")
            logger.info("Run manually: python -m places_engine.pipeline.upload_to_firestore")
        except Exception as e:
            logger.error(f"Firebase upload error: {e}")
    
    logger.info("")
    logger.info("Done!")


if __name__ == "__main__":
    main()
