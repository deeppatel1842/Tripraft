#!/usr/bin/env python3
"""
fill_coords_addresses.py

Helper script to locate missing coordinates (lat/lng) and address fields in a JSON places database
and fill them using one of three methods:
  - city-center fallbacks (safe, offline)
  - CSV mapping file (user-provided exact lat/lng/address)
  - optional Nominatim geocoding (online, rate-limited; disabled unless --geocode)

Usage examples:
  python fill_coords_addresses.py --input web/backend/world_database/USA/arizona.json --dry-run
  python fill_coords_addresses.py --input web/backend/world_database/USA/arizona.json --csv mappings.csv --write
  python fill_coords_addresses.py --input web/backend/world_database/USA/arizona.json --geocode --write

Contract (simple):
  - Input: path to JSON file containing structure {"cities": [{"city":..., "places": [...]}, ...]}
  - Output: prints a summary and (if --write) saves the updated JSON to the same file or an output path
  - Error modes: file not found, JSON decode error, network errors during geocoding (reported, skipped)

Notes:
  - The script will NOT call the network unless --geocode is passed.
  - Nominatim usage warns user and sleeps 1s between requests to be polite.
  - CSV mapping format: header with name_english or name_native (one of them), lat,lng,address (address optional).

"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

try:
    import requests
except Exception:
    requests = None  # only needed if --geocode is used

DEFAULT_CITY_CENTERS = {
    "Phoenix": {"lat": 33.448376, "lng": -112.074036},
    "Sedona": {"lat": 34.869740, "lng": -111.760990},
    "Grand Canyon Village": {"lat": 36.054444, "lng": -112.140111},
    "Grand Canyon Village (South Rim)": {"lat": 36.054444, "lng": -112.140111}
}


def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, path: str) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def find_missing_places(data: dict) -> List[Tuple[str, dict]]:
    missing = []
    cities = data.get('cities', [])
    for city_obj in cities:
        city_name = city_obj.get('city', '')
        for place in city_obj.get('places', []):
            coords = place.get('coordinates', {})
            lat = coords.get('lat')
            lng = coords.get('lng')
            address = place.get('address')
            if lat is None or lng is None or (address is None or (isinstance(address, str) and address.strip()=='')):
                missing.append((city_name, place))
    return missing


def apply_city_center_fallback(city_name: str, place: dict) -> bool:
    # return True if modified
    modified = False
    coords = place.setdefault('coordinates', {})
    if coords.get('lat') is None or coords.get('lng') is None:
        center = DEFAULT_CITY_CENTERS.get(city_name)
        if center:
            coords['lat'] = coords.get('lat') or center['lat']
            coords['lng'] = coords.get('lng') or center['lng']
            modified = True
    if not place.get('address'):
        # craft a minimal address using place name and city
        place['address'] = f"{place.get('name_english') or place.get('name_native')}, {city_name}, United States of America"
        modified = True
    return modified


def parse_csv_mappings(csv_path: str) -> Dict[str, Dict[str, str]]:
    mappings: Dict[str, Dict[str, str]] = {}
    import csv
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row.get('name_english') or row.get('name_native') or '').strip()
            if not key:
                continue
            mappings[key] = {
                'lat': row.get('lat') or '',
                'lng': row.get('lng') or '',
                'address': row.get('address') or ''
            }
    return mappings


def apply_csv_mappings(place: dict, mappings: Dict[str, Dict[str, str]]) -> bool:
    name = place.get('name_english') or place.get('name_native')
    if not name:
        return False
    m = mappings.get(name)
    if not m:
        return False
    modified = False
    coords = place.setdefault('coordinates', {})
    if coords.get('lat') is None or coords.get('lng') is None:
        try:
            if m.get('lat'):
                coords['lat'] = float(m['lat'])
                modified = True
            if m.get('lng'):
                coords['lng'] = float(m['lng'])
                modified = True
        except ValueError:
            pass
    if m.get('address') and (not place.get('address') or place.get('address').strip()==""):
        place['address'] = m['address']
        modified = True
    return modified


def nominatim_geocode(query: str, email: Optional[str]=None) -> Optional[Tuple[float, float, str]]:
    if requests is None:
        raise RuntimeError('requests package is required for geocoding')
    base = 'https://nominatim.openstreetmap.org/search'
    params = {'q': query, 'format': 'json', 'limit': 1}
    if email:
        params['email'] = email
    headers = {'User-Agent': 'tripraft-fill-script/1.0 (+https://example.com)'}
    resp = requests.get(base, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    top = data[0]
    lat = float(top['lat'])
    lon = float(top['lon'])
    display_name = top.get('display_name', '')
    return lat, lon, display_name


def fill_missing(data: dict, use_city_center: bool=True, csv_map: Optional[Dict[str, Dict[str, str]]]=None,
                 do_geocode: bool=False, geocode_email: Optional[str]=None, dry_run: bool=True,
                 output_path: Optional[str]=None) -> dict:
    cities = data.get('cities', [])
    stats = {'total_places':0, 'filled':0, 'skipped':0, 'errors':0}
    for city_obj in cities:
        city_name = city_obj.get('city', '')
        for place in city_obj.get('places', []):
            stats['total_places'] += 1
            try:
                coords = place.setdefault('coordinates', {})
                needs_coords = coords.get('lat') is None or coords.get('lng') is None
                needs_address = not place.get('address') or (isinstance(place.get('address'), str) and place.get('address').strip()=='')
                if not (needs_coords or needs_address):
                    stats['skipped'] += 1
                    continue
                modified = False
                # CSV mapping first (explicit overrides)
                if csv_map:
                    if apply_csv_mappings(place, csv_map):
                        modified = True
                # Geocode next if requested and still needs coords
                if do_geocode and (place.get('coordinates', {}).get('lat') is None or place.get('coordinates', {}).get('lng') is None):
                    name = place.get('name_english') or place.get('name_native')
                    query = f"{name}, {city_name}, USA"
                    try:
                        res = nominatim_geocode(query, email=geocode_email)
                        if res:
                            lat, lng, display_name = res
                            place['coordinates']['lat'] = lat
                            place['coordinates']['lng'] = lng
                            if not place.get('address'):
                                place['address'] = display_name
                            modified = True
                        else:
                            # no result
                            pass
                    except Exception as e:
                        print(f"Geocode error for '{query}': {e}", file=sys.stderr)
                        stats['errors'] += 1
                    time.sleep(1.0)  # be polite
                # City center fallback
                if use_city_center and (place.get('coordinates', {}).get('lat') is None or place.get('coordinates', {}).get('lng') is None or not place.get('address')):
                    if apply_city_center_fallback(city_name, place):
                        modified = True
                if modified:
                    stats['filled'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                print(f"Error processing place {place.get('name_english') or place.get('name_native')}: {e}", file=sys.stderr)
                stats['errors'] += 1
    # write back if asked
    if not dry_run:
        out = output_path or args.input
        save_json(data, out)
    print(json.dumps({'summary': stats}, indent=2))
    return data


def discover_json_files(root_dir: str) -> List[str]:
    """Recursively find all .json files under root_dir."""
    json_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith('.json'):
                json_files.append(os.path.join(dirpath, fname))
    return json_files


def process_single_file(file_path: str, csv_map: Optional[Dict[str, Dict[str, str]]]=None,
                        use_city_center: bool=True, do_geocode: bool=False,
                        geocode_email: Optional[str]=None, write: bool=False) -> dict:
    """Process a single JSON file and return stats."""
    try:
        data = load_json(file_path)
    except Exception as e:
        print(f"Failed to load JSON {file_path}: {e}", file=sys.stderr)
        return {'file': file_path, 'status': 'error', 'error': str(e)}
    
    missing = find_missing_places(data)
    if not missing:
        return {'file': file_path, 'status': 'skipped', 'reason': 'no missing data'}
    
    updated = fill_missing(data, use_city_center=use_city_center, csv_map=csv_map,
                          do_geocode=do_geocode, geocode_email=geocode_email,
                          dry_run=not write, output_path=None)
    
    if write:
        save_json(data, file_path)
    
    return {'file': file_path, 'status': 'processed', 'missing_count': len(missing)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fill missing coordinates and addresses in places JSON files')
    parser.add_argument('--input', '-i', help='Path to input JSON file OR directory to scan recursively')
    parser.add_argument('--output', '-o', help='Optional output path (only valid when --input is a single file)')
    parser.add_argument('--csv', help='CSV file with explicit mappings (columns: name_english|name_native, lat, lng, address)')
    parser.add_argument('--no-city-center', dest='city_center', action='store_false', help='Disable city-center fallback')
    parser.add_argument('--geocode', action='store_true', help='Enable Nominatim geocoding (requires internet and requests package)')
    parser.add_argument('--geocode-email', help='Optional email to pass to Nominatim for identification')
    parser.add_argument('--write', action='store_true', help='Write changes back to file (by default script is dry-run)')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Do not write changes; default')
    parser.add_argument('--database-dir', default='web/backend/world_database', help='Root directory for database JSON files (default: web/backend/world_database)')
    parser.set_defaults(dry_run=True)

    # allow shorthand: --write implies not dry-run
    known_args, unknown = parser.parse_known_args()
    # Make args globally available for save step
    args = known_args

    csv_map = None
    if args.csv:
        if not os.path.isfile(args.csv):
            print(f"CSV mapping file not found: {args.csv}", file=sys.stderr)
            sys.exit(4)
        csv_map = parse_csv_mappings(args.csv)

    if args.geocode and requests is None:
        print("requests package not available. Install via pip install requests to use --geocode", file=sys.stderr)
        sys.exit(6)

    # Determine input mode: single file or directory scan
    input_files = []
    if args.input:
        if os.path.isfile(args.input):
            input_files = [args.input]
        elif os.path.isdir(args.input):
            input_files = discover_json_files(args.input)
            print(f"Discovered {len(input_files)} JSON files in {args.input}")
        else:
            print(f"Input path not found: {args.input}", file=sys.stderr)
            sys.exit(2)
    else:
        # Default: scan database_dir
        if os.path.isdir(args.database_dir):
            input_files = discover_json_files(args.database_dir)
            print(f"Discovered {len(input_files)} JSON files in {args.database_dir}")
        else:
            print(f"Database directory not found: {args.database_dir}", file=sys.stderr)
            sys.exit(2)

    if not input_files:
        print("No JSON files to process.", file=sys.stderr)
        sys.exit(5)

    # Process files
    results = []
    for file_path in input_files:
        print(f"\nProcessing: {file_path}")
        try:
            data = load_json(file_path)
        except Exception as e:
            print(f"Failed to load JSON: {e}", file=sys.stderr)
            results.append({'file': file_path, 'status': 'error', 'error': str(e)})
            continue

        missing = find_missing_places(data)
        print(f"Found {len(missing)} places that may need filling. (dry-run={args.dry_run})")

        updated = fill_missing(data, use_city_center=args.city_center, csv_map=csv_map, do_geocode=args.geocode,
                               geocode_email=args.geocode_email, dry_run=not args.write,
                               output_path=args.output if args.input and os.path.isfile(args.input) else None)

        if args.write:
            out_path = args.output if (args.input and os.path.isfile(args.input) and args.output) else file_path
            save_json(data, out_path)
            print(f"Changes written to {out_path}")
            results.append({'file': file_path, 'status': 'written', 'missing_count': len(missing)})
        else:
            results.append({'file': file_path, 'status': 'dry-run', 'missing_count': len(missing)})

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(json.dumps({'results': results}, indent=2))
    if not args.write:
        print("\nDry-run complete. No files were modified. Re-run with --write to persist changes.")
