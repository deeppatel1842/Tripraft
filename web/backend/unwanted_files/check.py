import os
import json
import shutil

# CONFIGURATION
SOURCE_FOLDER = 'countries'
PASS_FOLDER = 'passed_countries'
FAIL_FOLDER = 'failed_countries'

def validate_json_content(data):
    """
    Returns True if the JSON has valid content (cities and places).
    Returns False if it is empty or missing data.
    """
    try:
        # 1. Check for 'cities' list
        if "cities" not in data or not isinstance(data["cities"], list):
            return False
        
        # 2. Check if there are any cities at all
        if len(data["cities"]) == 0:
            return False

        # 3. Check if there is at least ONE place in the whole file
        total_places = 0
        for city in data["cities"]:
            if "places" in city and isinstance(city["places"], list):
                total_places += len(city["places"])
        
        if total_places == 0:
            return False

        return True

    except Exception:
        return False

def organize_files():
    # Create destination folders if they don't exist
    if not os.path.exists(PASS_FOLDER):
        os.makedirs(PASS_FOLDER)
    if not os.path.exists(FAIL_FOLDER):
        os.makedirs(FAIL_FOLDER)

    moved_pass = 0
    moved_fail = 0

    print(f"Scanning '{SOURCE_FOLDER}' and organizing files...")
    print("-" * 30)

    for dirpath, _, filenames in os.walk(SOURCE_FOLDER):
        for filename in filenames:
            if filename.lower().endswith('.json'):
                source_path = os.path.join(dirpath, filename)
                
                # Get the relative folder path (e.g., "argentina" or "usa")
                # This helps us keep the structure in the new folders
                relative_folder = os.path.relpath(dirpath, SOURCE_FOLDER)
                
                # Determine validity
                is_valid = False
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        is_valid = validate_json_content(data)
                except Exception as e:
                    print(f"❌ Corrupt file: {filename} ({e})")
                    is_valid = False

                # define destination root based on validity
                target_root = PASS_FOLDER if is_valid else FAIL_FOLDER
                
                # Create the country subfolder in the target (e.g., passed_json/usa)
                target_dir = os.path.join(target_root, relative_folder)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                target_path = os.path.join(target_dir, filename)

                # Move the file
                shutil.move(source_path, target_path)

                if is_valid:
                    moved_pass += 1
                else:
                    moved_fail += 1
                    print(f"Moved to FAILED: {os.path.join(relative_folder, filename)}")

    print("-" * 30)
    print("Organization Complete.")
    print(f"✅ Moved to '{PASS_FOLDER}': {moved_pass} files")
    print(f"⚠️  Moved to '{FAIL_FOLDER}': {moved_fail} files")
    
    # Optional cleanup: remove empty country folders in the source directory
    # try:
    #     os.rmdir(SOURCE_FOLDER)
    # except:
    #     pass

if __name__ == "__main__":
    if os.path.exists(SOURCE_FOLDER):
        organize_files()
    else:
        print(f"Error: Folder '{SOURCE_FOLDER}' not found.")