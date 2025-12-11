# import os
# import json
# import requests
# import concurrent.futures
# from tqdm import tqdm
# from difflib import SequenceMatcher
# import threading

# # CONFIGURATION
# INPUT_FOLDER = 'passed_countries' 
# USER_AGENT = "TravelApp_Strict/2.0 (contact@example.com)"

# # Images with these words in the filename will be rejected
# BANNED_KEYWORDS = ["flag", "map", "location", "coat of arms", "coa", "logo", "symbol", "stub", "silhoutte", "admin", "region"]
# BANNED_EXTENSIONS = [".svg", ".png", ".gif"]

# # Global counters
# stats_lock = threading.Lock()
# GLOBAL_STATS = {
#     "total_places": 0,
#     "places_with_image": 0,
#     "places_empty": 0
# }

# def similarity(a, b):
#     return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# def is_valid_image(filename):
#     fname_lower = filename.lower()
#     if any(fname_lower.endswith(ext) for ext in BANNED_EXTENSIONS):
#         return False
#     if any(keyword in fname_lower for keyword in BANNED_KEYWORDS):
#         return False
#     return True

# def get_wiki_image_data(place_name, city_name, country_name):
#     session = requests.Session()
#     base_url = "https://en.wikipedia.org/w/api.php"

#     queries = [f"{place_name} {city_name}", place_name]

#     for query in queries:
#         search_params = {
#             "action": "query", "format": "json", "list": "search",
#             "srsearch": query, "srlimit": 3
#         }

#         try:
#             search_resp = session.get(base_url, params=search_params, headers={"User-Agent": USER_AGENT}, timeout=5)
#             search_data = search_resp.json()
            
#             if not search_data.get("query", {}).get("search"):
#                 continue

#             best_page = None
#             for result in search_data["query"]["search"]:
#                 title = result["title"]
                
#                 # REJECT generic pages
#                 if title.lower() in [country_name.lower(), city_name.lower()]:
#                     continue

#                 # STRICT MATCHING
#                 title_sim = similarity(place_name, title)
#                 query_sim = similarity(query, title)
                
#                 if title_sim > 0.4 or query_sim > 0.4 or place_name.lower() in title.lower():
#                     best_page = title
#                     break
            
#             if not best_page:
#                 continue

#             # Fetch Image
#             img_params = {
#                 "action": "query", "format": "json", "prop": "pageimages|pageterms",
#                 "titles": best_page, "piprop": "thumbnail|name|original", "pithumbsize": 800
#             }

#             img_resp = session.get(base_url, params=img_params, headers={"User-Agent": USER_AGENT}, timeout=5)
#             img_data = img_resp.json()
            
#             pages = img_data.get("query", {}).get("pages", {})
#             for _, page in pages.items():
#                 if "pageimage" in page:
#                     file_name = "File:" + page["pageimage"]
                    
#                     if not is_valid_image(file_name):
#                         continue

#                     return get_commons_attribution(file_name, page.get("thumbnail", {}).get("source"), 800, 600)

#         except Exception:
#             continue
    
#     return {}

# def get_commons_attribution(filename, url, width, height):
#     commons_url = "https://commons.wikimedia.org/w/api.php"
#     params = {
#         "action": "query", "format": "json", "prop": "imageinfo",
#         "titles": filename, "iiprop": "extmetadata|user|url"
#     }
#     try:
#         resp = requests.get(commons_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=5)
#         data = resp.json()
#         pages = data.get("query", {}).get("pages", {})
        
#         for _, page in pages.items():
#             if "imageinfo" in page:
#                 info = page["imageinfo"][0]
#                 meta = info.get("extmetadata", {})
                
#                 return {
#                     "wikimedia_commons": {
#                         "source_file": filename,
#                         "thumbnail": {
#                             "url": url, "width": width, "height": height,
#                             "attribution": {
#                                 "title": meta.get("ObjectName", {}).get("value", filename.replace("File:", "")),
#                                 "author": meta.get("Artist", {}).get("value", info.get("user", "Unknown")),
#                                 "license": meta.get("LicenseShortName", {}).get("value", "Public domain"),
#                                 "license_url": meta.get("LicenseUrl", {}).get("value", None),
#                                 "source_url": info.get("descriptionurl", ""),
#                                 "credit": "Wikimedia Commons", 
#                                 "usage_terms": meta.get("UsageTerms", {}).get("value", "Public domain"),
#                                 "description": meta.get("ImageDescription", {}).get("value", "")
#                             }
#                         }
#                     }
#                 }
#     except:
#         pass
#     return {}

# def process_single_file(file_path):
#     local_found = 0
#     local_total = 0
#     updated_file = False

#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
        
#         country = data.get("country", "")
        
#         if "cities" in data:
#             for city in data["cities"]:
#                 city_name = city.get("city", "")
#                 if "places" in city:
#                     for place in city["places"]:
#                         local_total += 1
                        
#                         # Only fetch if photos are currently EMPTY (optional optimization)
#                         # Remove 'if place.get("photos") == {}:' if you want to FORCE overwrite everything
#                         if place.get("photos") == {}: 
#                             new_photo = get_wiki_image_data(place.get("name"), city_name, country)
                            
#                             if new_photo:
#                                 place["photos"] = new_photo
#                                 local_found += 1
#                                 updated_file = True
#                             else:
#                                 # Keep empty if not found
#                                 place["photos"] = {}
#                         elif place.get("photos"):
#                              # If it already has a photo, count it as found
#                              local_found += 1

#         if updated_file:
#             with open(file_path, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, indent=2, ensure_ascii=False)
        
#         with stats_lock:
#             GLOBAL_STATS["total_places"] += local_total
#             GLOBAL_STATS["places_with_image"] += local_found
#             GLOBAL_STATS["places_empty"] += (local_total - local_found)

#         # PRINT UPDATE: Use tqdm.write so it doesn't break the progress bar
#         filename = os.path.basename(file_path)
#         folder = os.path.basename(os.path.dirname(file_path))
#         tqdm.write(f"Completed: {folder}/{filename} -> Found {local_found}/{local_total} photos")

#     except Exception as e:
#         tqdm.write(f"Error {file_path}: {e}")

# def main():
#     if not os.path.exists(INPUT_FOLDER):
#         print(f"Error: Folder '{INPUT_FOLDER}' not found.")
#         return

#     all_files = []
#     for dirpath, _, filenames in os.walk(INPUT_FOLDER):
#         for filename in filenames:
#             if filename.lower().endswith('.json'):
#                 all_files.append(os.path.join(dirpath, filename))

#     print(f"Refining photos for {len(all_files)} files... (Strict Mode)")
#     print("-" * 40)

#     # 5 Workers for parallel processing
#     with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#         list(tqdm(executor.map(process_single_file, all_files), total=len(all_files), unit="file"))

#     print("-" * 40)
#     print("PROCESS COMPLETE")
#     print(f"Total Places Scanned:      {GLOBAL_STATS['total_places']}")
#     print(f"✅ Original Images Found:   {GLOBAL_STATS['places_with_image']}")
#     print(f"⚠️ No Valid Image Found:    {GLOBAL_STATS['places_empty']}")
    
#     if GLOBAL_STATS['total_places'] > 0:
#         success_rate = (GLOBAL_STATS['places_with_image'] / GLOBAL_STATS['total_places']) * 100
#         print(f"Success Rate:              {success_rate:.2f}%")

# if __name__ == "__main__":
#     main()


import os
import json
import requests
import concurrent.futures
from tqdm import tqdm
from difflib import SequenceMatcher
import threading
import re

# CONFIGURATION
INPUT_FOLDER = 'passed_countries' 
USER_AGENT = "TravelApp_Deep/3.0 (contact@example.com)"

# Images/Files to reject
BANNED_KEYWORDS = ["flag", "map", "location", "coat of arms", "coa", "logo", "symbol", "stub", "silhoutte", "admin", "region", "currency"]
BANNED_EXTENSIONS = [".svg", ".png", ".gif"]

# Words to strip if strict search fails
GENERIC_SUFFIXES = [" hike", " tour", " walk", " experience", " trip", " visit", " excursion", " scenic drive", " viewpoint"]

# Global stats
stats_lock = threading.Lock()
GLOBAL_STATS = {
    "total_places": 0,
    "places_with_image": 0,
    "places_empty": 0
}

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_valid_image(filename):
    fname_lower = filename.lower()
    if any(fname_lower.endswith(ext) for ext in BANNED_EXTENSIONS):
        return False
    if any(keyword in fname_lower for keyword in BANNED_KEYWORDS):
        return False
    return True

def clean_place_name(name):
    # Remove text in parentheses: "Bariloche (Patagonia)" -> "Bariloche"
    return re.sub(r'\([^)]*\)', '', name).strip()

def generate_search_queries(place_name, city_name, country_name):
    """Generates a list of search queries from specific to broad."""
    clean_name = clean_place_name(place_name)
    
    queries = []
    
    # 1. Exact Place + City
    queries.append(f"{clean_name} {city_name}")
    
    # 2. Exact Place + Country
    queries.append(f"{clean_name} {country_name}")
    
    # 3. Just Place Name
    queries.append(clean_name)

    # 4. Keyword Stripped Version (e.g. "Refugio Frey Hike" -> "Refugio Frey")
    for suffix in GENERIC_SUFFIXES:
        if suffix.lower() in clean_name.lower():
            stripped = re.sub(suffix, '', clean_name, flags=re.IGNORECASE).strip()
            queries.append(f"{stripped} {city_name}")
            queries.append(stripped)
            break 
            
    return list(dict.fromkeys(queries)) # Remove duplicates

def get_wiki_image_deep(place_name, city_name, country_name):
    session = requests.Session()
    base_url = "https://en.wikipedia.org/w/api.php"

    queries = generate_search_queries(place_name, city_name, country_name)

    for query in queries:
        search_params = {
            "action": "query", "format": "json", "list": "search",
            "srsearch": query, "srlimit": 3
        }

        try:
            search_resp = session.get(base_url, params=search_params, headers={"User-Agent": USER_AGENT}, timeout=5)
            search_data = search_resp.json()
            
            if not search_data.get("query", {}).get("search"):
                continue

            best_page = None
            for result in search_data["query"]["search"]:
                title = result["title"]
                
                # REJECT generic pages (Country or City main pages)
                # This prevents "Chocolate Shop" -> returning "Argentina"
                if title.lower() in [country_name.lower(), city_name.lower(), "tourism", "travel"]:
                    continue

                # MATCHING LOGIC
                # We are more lenient here because we are trying deeper variations
                title_sim = similarity(place_name, title)
                query_sim = similarity(query, title)
                
                # If match is decent OR the cleaned place name is inside the title
                if title_sim > 0.35 or query_sim > 0.35 or clean_place_name(place_name).lower() in title.lower():
                    best_page = title
                    break
            
            if not best_page:
                continue

            # Fetch Image for Page
            img_params = {
                "action": "query", "format": "json", "prop": "pageimages|pageterms",
                "titles": best_page, "piprop": "thumbnail|name|original", "pithumbsize": 800
            }

            img_resp = session.get(base_url, params=img_params, headers={"User-Agent": USER_AGENT}, timeout=5)
            img_data = img_resp.json()
            
            pages = img_data.get("query", {}).get("pages", {})
            for _, page in pages.items():
                if "pageimage" in page:
                    file_name = "File:" + page["pageimage"]
                    
                    if not is_valid_image(file_name):
                        continue

                    # Found a valid image!
                    return get_commons_attribution(file_name, page.get("thumbnail", {}).get("source"), 800, 600)

        except Exception:
            continue
    
    return {}

def get_commons_attribution(filename, url, width, height):
    commons_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "prop": "imageinfo",
        "titles": filename, "iiprop": "extmetadata|user|url"
    }
    try:
        resp = requests.get(commons_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=5)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        
        for _, page in pages.items():
            if "imageinfo" in page:
                info = page["imageinfo"][0]
                meta = info.get("extmetadata", {})
                
                return {
                    "wikimedia_commons": {
                        "source_file": filename,
                        "thumbnail": {
                            "url": url, "width": width, "height": height,
                            "attribution": {
                                "title": meta.get("ObjectName", {}).get("value", filename.replace("File:", "")),
                                "author": meta.get("Artist", {}).get("value", info.get("user", "Unknown")),
                                "license": meta.get("LicenseShortName", {}).get("value", "Public domain"),
                                "license_url": meta.get("LicenseUrl", {}).get("value", None),
                                "source_url": info.get("descriptionurl", ""),
                                "credit": "Wikimedia Commons", 
                                "usage_terms": meta.get("UsageTerms", {}).get("value", "Public domain"),
                                "description": meta.get("ImageDescription", {}).get("value", "")
                            }
                        }
                    }
                }
    except:
        pass
    return {}

def process_single_file(file_path):
    local_found = 0
    local_total = 0
    updated_file = False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        country = data.get("country", "")
        
        if "cities" in data:
            for city in data["cities"]:
                city_name = city.get("city", "")
                if "places" in city:
                    for place in city["places"]:
                        local_total += 1
                        
                        # Optimization: Skip if already has a valid wikimedia photo
                        # Remove this check if you want to force re-check everything
                        if place.get("photos") and "wikimedia_commons" in place.get("photos", {}):
                            local_found += 1
                            continue 

                        # Run Deep Search
                        new_photo = get_wiki_image_deep(place.get("name"), city_name, country)
                        
                        if new_photo:
                            place["photos"] = new_photo
                            local_found += 1
                            updated_file = True
                        else:
                            place["photos"] = {} # Keep empty if not found
                            updated_file = True

        if updated_file:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        with stats_lock:
            GLOBAL_STATS["total_places"] += local_total
            GLOBAL_STATS["places_with_image"] += local_found
            GLOBAL_STATS["places_empty"] += (local_total - local_found)

        filename = os.path.basename(file_path)
        folder = os.path.basename(os.path.dirname(file_path))
        tqdm.write(f"Updated: {folder}/{filename} -> Found {local_found}/{local_total}")

    except Exception as e:
        tqdm.write(f"Error {file_path}: {e}")

def main():
    if not os.path.exists(INPUT_FOLDER):
        print(f"Error: Folder '{INPUT_FOLDER}' not found.")
        return

    all_files = []
    for dirpath, _, filenames in os.walk(INPUT_FOLDER):
        for filename in filenames:
            if filename.lower().endswith('.json'):
                all_files.append(os.path.join(dirpath, filename))

    print(f"Deep Searching photos for {len(all_files)} files...")
    print("-" * 40)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(process_single_file, all_files), total=len(all_files), unit="file"))

    print("-" * 40)
    print("DEEP SEARCH COMPLETE")
    print(f"Total Places:              {GLOBAL_STATS['total_places']}")
    print(f"✅ Images Found:            {GLOBAL_STATS['places_with_image']}")
    print(f"⚠️ Still Missing Images:    {GLOBAL_STATS['places_empty']}")
    
    if GLOBAL_STATS['total_places'] > 0:
        success_rate = (GLOBAL_STATS['places_with_image'] / GLOBAL_STATS['total_places']) * 100
        print(f"Coverage:                  {success_rate:.2f}%")

if __name__ == "__main__":
    main()