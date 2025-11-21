#!/usr/bin/env python3
"""
Photo Enhancement Engine for TripRaft Database Pipeline
========================================================
Fetches and adds photos from:
- Wikipedia (primary photo)
- Wikimedia Commons (gallery)
"""

import re
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)


class PhotoEngine:
    """Photo enhancement engine"""
    
    USER_AGENT = "TripRaft/1.0 (contact@tripraft.com)"
    WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    COMMONS_API = "https://commons.wikimedia.org/w/api.php"
    PAUSE_BETWEEN_REQUESTS = 1.0
    
    def __init__(self):
        self.photos_added = 0
        self.api_calls = 0
    
    @staticmethod
    def clean_place_name(place_name: str) -> str:
        """Clean place name for better search results"""
        cleaned = re.sub(r'\([^)]*\)', '', place_name)
        cleaned = cleaned.replace('&', 'and').strip()
        return cleaned
    
    def get_wikipedia_photo(self, place_name: str) -> Optional[Dict[str, Any]]:
        """Get primary photo from Wikipedia"""
        try:
            search_term = self.clean_place_name(place_name)
            wiki_url = f"{self.WIKIPEDIA_API}{quote(search_term)}"
            headers = {"User-Agent": self.USER_AGENT}
            
            response = requests.get(wiki_url, headers=headers, timeout=10)
            self.api_calls += 1
            
            if response.status_code == 200:
                data = response.json()
                
                if "thumbnail" in data:
                    thumb_url = data["thumbnail"]["source"]
                    # Get higher resolution
                    large_url = thumb_url.replace("/thumb/", "/").split("/")
                    if len(large_url) > 1:
                        large_url = "/".join(large_url[:-1])
                    else:
                        large_url = thumb_url
                    
                    return {
                        "url": large_url,
                        "source": "wikipedia",
                        "title": data.get("title", place_name),
                        "description": data.get("description", ""),
                        "license": "Various (Wikipedia/Wikimedia)",
                        "attribution": f"Image from Wikipedia article: {data.get('title', place_name)}"
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Wikipedia photo error for {place_name}: {str(e)}")
            return None
    
    def get_wikimedia_commons_photos(self, place_name: str, 
                                     max_photos: int = 3) -> List[Dict[str, Any]]:
        """Get additional photos from Wikimedia Commons"""
        photos = []
        try:
            search_term = self.clean_place_name(place_name)
            
            # Search for images
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": f'"{search_term}" filetype:bitmap',
                "srlimit": max_photos * 2,
                "srnamespace": 6
            }
            headers = {"User-Agent": self.USER_AGENT}
            
            response = requests.get(self.COMMONS_API, params=params, 
                                   headers=headers, timeout=15)
            self.api_calls += 1
            
            if response.status_code == 200:
                data = response.json()
                search_results = data.get("query", {}).get("search", [])
                
                if search_results:
                    pageids = [str(item["pageid"]) for item in search_results[:max_photos]]
                    
                    # Get image details
                    info_params = {
                        "action": "query",
                        "format": "json",
                        "pageids": "|".join(pageids),
                        "prop": "imageinfo",
                        "iiprop": "url|user|extmetadata|size",
                        "iiurlwidth": 800
                    }
                    
                    info_response = requests.get(self.COMMONS_API, params=info_params,
                                                headers=headers, timeout=15)
                    self.api_calls += 1
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        pages = info_data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if "imageinfo" in page and page["imageinfo"]:
                                img_info = page["imageinfo"][0]
                                
                                photos.append({
                                    "url": img_info.get("thumburl", img_info.get("url", "")),
                                    "source": "wikimedia_commons",
                                    "title": page.get("title", "").replace("File:", ""),
                                    "width": img_info.get("thumbwidth", img_info.get("width")),
                                    "height": img_info.get("thumbheight", img_info.get("height")),
                                    "license": "Creative Commons (Various)",
                                    "attribution": f"Wikimedia Commons - {img_info.get('user', 'Unknown')}"
                                })
                                
                                if len(photos) >= max_photos:
                                    break
            
            return photos
            
        except Exception as e:
            logger.debug(f"Commons photos error for {place_name}: {str(e)}")
            return []
    
    def enhance_place_photos(self, place: Dict[str, Any]) -> bool:
        """Add photos to a single place"""
        place_name = place.get("name_english") or place.get("name_native") or place.get("name", "")
        
        if not place_name:
            return False
        
        # Skip if photos already exist
        if place.get("photos") and place["photos"].get("primary"):
            logger.debug(f"  Skipping {place_name} (photos exist)")
            return False
        
        logger.debug(f"  Fetching photos for: {place_name}")
        
        photos_data = {"primary": None, "gallery": []}
        
        # Get primary photo from Wikipedia
        wiki_photo = self.get_wikipedia_photo(place_name)
        if wiki_photo:
            photos_data["primary"] = wiki_photo
        
        time.sleep(self.PAUSE_BETWEEN_REQUESTS)
        
        # Get gallery from Commons
        commons_photos = self.get_wikimedia_commons_photos(place_name, max_photos=2)
        if commons_photos:
            photos_data["gallery"] = commons_photos
        
        time.sleep(self.PAUSE_BETWEEN_REQUESTS)
        
        # Fallback placeholder if no photos found
        if not photos_data["primary"] and not photos_data["gallery"]:
            photos_data["primary"] = {
                "url": f"https://via.placeholder.com/800x600/4A90E2/FFFFFF?text={quote(place_name)}",
                "source": "placeholder",
                "title": place_name,
                "description": f"Placeholder image for {place_name}",
                "license": "Placeholder",
                "attribution": "Generated placeholder"
            }
        
        place["photos"] = photos_data
        return True
    
    def find_all_places(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all place objects in data structure"""
        places = []
        
        # Common structures
        if "cities" in data:
            for city in data["cities"]:
                if "places" in city:
                    places.extend(city["places"])
        elif "regions" in data:
            for region in data["regions"]:
                if "places" in region:
                    places.extend(region["places"])
        elif "places" in data:
            places.extend(data["places"])
        elif "top_places" in data:
            places.extend(data["top_places"])
        
        return places
    
    def add_photos(self, data: Dict[str, Any]) -> int:
        """Add photos to all places in data structure"""
        places = self.find_all_places(data)
        
        if not places:
            logger.warning("  No places found in data structure")
            return 0
        
        added_count = 0
        total = len(places)
        
        logger.info(f"  Photo engine: Processing {total} places...")
        
        for i, place in enumerate(places, 1):
            try:
                if self.enhance_place_photos(place):
                    added_count += 1
                
                # Progress update every 10 places
                if i % 10 == 0:
                    logger.info(f"    Progress: {i}/{total} places ({(i/total)*100:.0f}%)")
                    
            except Exception as e:
                logger.error(f"  Error adding photos to place: {str(e)}")
        
        self.photos_added = added_count
        logger.info(f"  Photo engine: Added photos to {added_count}/{total} places")
        logger.info(f"  API calls made: {self.api_calls}")
        
        return added_count


# Standalone test
if __name__ == "__main__":
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_place = {
        "name_english": "Golden Gate Bridge",
        "name_native": "Golden Gate Bridge"
    }
    
    engine = PhotoEngine()
    success = engine.enhance_place_photos(test_place)
    
    print(f"\nSuccess: {success}")
    print(f"Result: {json.dumps(test_place, indent=2)}")
