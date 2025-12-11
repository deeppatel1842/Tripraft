import os
import json

# CONFIGURATION
# Make sure this matches your actual folder name
ROOT_FOLDER = 'passed_countries'

# ==========================================
# 1. THE SCORING ALGORITHM (STRICTER VERSION)
# ==========================================
def calculate_rank_score(place):
    """
    Calculates a ranking score (0.0 - 1.0) with strict differentiation.
    
    New Logic:
    - Base Score: Derived from Priority (50%) + Experience (30%).
    - Content Bonus: Only applied if specific 'Tier 1' keywords are found.
    - Penalties: Applies slight decay for generic descriptions.
    """
    
    # --- 1. BASE SCORES (Max 0.80) ---
    # We cap the base rating contribution so that 5/5 ratings alone 
    # only get you to 0.80. The rest must be earned via 'Significance'.
    
    p_score = place.get('rating_tourist_priority', 0) / 5.0
    e_score = place.get('rating_traveler_experience', 0) / 5.0
    
    # Priority is weighted heavily, but we multiply by 0.8 to leave room for the bonus
    base_score = (p_score * 0.50) + (e_score * 0.30) 
    
    # --- 2. SIGNIFICANCE BONUS (Max 0.20) ---
    # This is where we separate "Great" from "Legendary"
    summary = place.get('ai_summary', '').lower()
    tags = [t.lower() for t in place.get('tags', [])]
    
    # Tier 1 Words: Global Icons (Huge Boost)
    # These imply people fly to this country just to see this.
    tier_1_keywords = [
        'unesco', 'world heritage', 'iconic', 'most visited', 
        'famous', 'landmark', 'symbol', 'signature', 'world-class',
        'tallest', 'largest', 'highest', 'ancient', 'wonder'
    ]
    
    # Tier 2 Words: Major Regional Attractions (Moderate Boost)
    tier_2_keywords = [
        'popular', 'historic', 'must-see', 'scenic', 'panoramic', 
        'spectacular', 'breathtaking', 'unique', 'top rated'
    ]
    
    bonus = 0.0
    
    # Check for Tier 1 matches (limit 2)
    t1_count = sum(1 for k in tier_1_keywords if k in summary)
    bonus += min(t1_count * 0.08, 0.16)  # Max 0.16 boost
    
    # Check for Tier 2 matches (limit 2)
    t2_count = sum(1 for k in tier_2_keywords if k in summary)
    bonus += min(t2_count * 0.02, 0.04)  # Max 0.04 boost

    # --- 3. TAG CONTEXT BONUS (Tie-Breaker, Max 0.05) ---
    # Boost if it has 'National Park' or 'Museum' tags (usually higher value than 'Park')
    high_value_tags = ['national park', 'museum', 'historic', 'viewpoint']
    if any(tag in tags for tag in high_value_tags):
        bonus += 0.02

    # --- 4. CALCULATE FINAL ---
    final_score = base_score + bonus
    
    # Cap at 0.99 (Reserve 1.0 for theoretical perfection)
    return round(min(final_score, 0.9900), 4)

# ==========================================
# 2. THE UPDATE LOGIC
# ==========================================
def update_rankings(root_directory):
    total_files = 0
    updated_places = 0
    files_modified = 0

    print(f"Starting STRICT RANKING UPDATE on: {root_directory}...")
    print("-" * 30)

    if not os.path.exists(root_directory):
        print(f"❌ Error: Folder '{root_directory}' not found.")
        return

    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if filename.lower().endswith('.json'):
                file_path = os.path.join(dirpath, filename)
                total_files += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    modified_this_file = False

                    # Helper to process a list of places
                    def process_place_list(places_list):
                        count = 0
                        for place in places_list:
                            new_score = calculate_rank_score(place)
                            # Only update if the score actually changes significantly
                            if place.get("rank_score") != new_score:
                                place["rank_score"] = new_score
                                count += 1
                        return count

                    # Update Cities
                    if "cities" in data and isinstance(data["cities"], list):
                        for city in data["cities"]:
                            if "places" in city and isinstance(city["places"], list):
                                count = process_place_list(city["places"])
                                if count > 0:
                                    modified_this_file = True
                                    updated_places += count
                    
                    # Update Regions
                    if "nearby_regions" in data and isinstance(data["nearby_regions"], list):
                        for region in data["nearby_regions"]:
                            if "places" in region and isinstance(region["places"], list):
                                count = process_place_list(region["places"])
                                if count > 0:
                                    modified_this_file = True
                                    updated_places += count

                    # Save File
                    if modified_this_file:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        files_modified += 1
                        print(f"Updated: {filename}")

                except Exception as e:
                    print(f"Error reading {filename}: {e}")

    print("-" * 30)
    print("UPDATE COMPLETE")
    print(f"Total files scanned: {total_files}")
    print(f"Files modified: {files_modified}")
    print(f"Total places rescored: {updated_places}")

if __name__ == "__main__":
    update_rankings(ROOT_FOLDER)