# import os
# import json

# ROOT_FOLDER = 'passed_countries'

# def audit_files(root_directory):
#     files_with_zero_places = []
#     files_with_photos_remaining = []
#     malformed_files = []

#     print(f"Auditing files in: {root_directory}...")
#     print("-" * 30)

#     for dirpath, _, filenames in os.walk(root_directory):
#         for filename in filenames:
#             if filename.lower().endswith('.json'):
#                 file_path = os.path.join(dirpath, filename)
#                 relative_path = os.path.join(os.path.basename(dirpath), filename)
                
#                 try:
#                     with open(file_path, 'r', encoding='utf-8') as f:
#                         data = json.load(f)

#                     place_count = 0
#                     has_remaining_photos = False

#                     # Check structure
#                     if "cities" in data and isinstance(data["cities"], list):
#                         for city in data["cities"]:
#                             if "places" in city and isinstance(city["places"], list):
#                                 place_count += len(city["places"])
                                
#                                 # Sanity check: Did we miss any?
#                                 for place in city["places"]:
#                                     if "photos" in place and place["photos"]:
#                                         has_remaining_photos = True

#                     # categorize
#                     if place_count == 0:
#                         files_with_zero_places.append(relative_path)
                    
#                     if has_remaining_photos:
#                         files_with_photos_remaining.append(relative_path)

#                 except Exception as e:
#                     malformed_files.append(f"{relative_path} ({str(e)})")

#     # REPORT
#     print("\n" + "="*30)
#     print("AUDIT REPORT")
#     print("="*30)

#     if files_with_photos_remaining:
#         print(f"\n⚠️  WARNING: {len(files_with_photos_remaining)} files still have photos (Update Failed):")
#         for f in files_with_photos_remaining:
#             print(f" - {f}")
#     else:
#         print("\n✅ Verification Success: No files have remaining photos.")

#     if files_with_zero_places:
#         print(f"\nℹ️  The following {len(files_with_zero_places)} files have 0 places (likely why they were not modified):")
#         for f in files_with_zero_places:
#             print(f" - {f}")
#     else:
#         print("\nAll files contain at least one place.")

#     if malformed_files:
#         print(f"\n❌ The following files are broken/invalid:")
#         for f in malformed_files:
#             print(f" - {f}")

# if __name__ == "__main__":
#     audit_files(ROOT_FOLDER)


import os
import json

# CONFIGURATION
ROOT_FOLDER = 'passed_countries'

def clean_photos_and_gallery(root_directory):
    total_files = 0
    files_modified = 0
    places_cleaned = 0

    print(f"Starting DEEP CLEAN on: {root_directory}...")
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

                    if "cities" in data and isinstance(data["cities"], list):
                        for city in data["cities"]:
                            if "places" in city and isinstance(city["places"], list):
                                for place in city["places"]:
                                    
                                    # 1. REMOVE 'gallery' key if it exists as a sibling
                                    if "gallery" in place:
                                        del place["gallery"]
                                        modified_this_file = True

                                    # 2. FORCE RESET 'photos' to {} 
                                    # We check if it is NOT empty, or if it has keys like 'osm'/'wikimedia_commons'
                                    if "photos" in place:
                                        # If it's not already exactly {}, we wipe it.
                                        if place["photos"] != {}:
                                            place["photos"] = {}
                                            modified_this_file = True
                                            places_cleaned += 1

                    if modified_this_file:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        files_modified += 1
                        print(f"✅ Cleaned: {filename}")

                except Exception as e:
                    print(f"❌ Error reading {filename}: {e}")

    print("-" * 30)
    print("CLEANING COMPLETE")
    print(f"Total files scanned: {total_files}")
    print(f"Files modified: {files_modified}")
    print(f"Places wiped: {places_cleaned}")

if __name__ == "__main__":
    clean_photos_and_gallery(ROOT_FOLDER)