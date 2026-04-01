"""
Data Ingestion CLI
===================
Command-line tool for importing travel data from CSV/JSON files
into travel_data_complete.db.

Usage:
  python scripts/ingest_data.py --file places.csv --type place
  python scripts/ingest_data.py --file places.json --type place --dry-run
  python scripts/ingest_data.py --file countries.json --type country
  python scripts/ingest_data.py --file places.csv --type place --skip-geo-check
"""

import argparse
import sys
import time
from pathlib import Path

# Make sure we can import from app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.data_ingestion_service import data_ingestion_service


def main():
    parser = argparse.ArgumentParser(
        description="Import travel data from CSV/JSON into travel_data_complete.db"
    )
    parser.add_argument(
        "--file", "-f", required=True, type=Path,
        help="Path to CSV or JSON file to import"
    )
    parser.add_argument(
        "--type", "-t", default="place",
        choices=["place", "country", "state", "city", "photo", "tag", "opening_hours"],
        help="Entity type to import (default: place)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate only — do not insert any data"
    )
    parser.add_argument(
        "--skip-geo-check", action="store_true",
        help="Skip geo-distance warnings between places and their cities"
    )
    parser.add_argument(
        "--user", "-u", default="cli",
        help="Username for audit log (default: cli)"
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    content = args.file.read_text(encoding="utf-8")
    suffix = args.file.suffix.lower()

    print(f"File:   {args.file}")
    print(f"Type:   {args.type}")
    print(f"Mode:   {'dry-run' if args.dry_run else 'import'}")
    print()

    start = time.time()

    if args.dry_run:
        # Dry-run only works for places currently
        import csv
        import json
        from io import StringIO
        if suffix == ".csv":
            reader = csv.DictReader(StringIO(content))
            rows = [data_ingestion_service._coerce_csv_row(r) for r in reader]
        elif suffix == ".json":
            data = json.loads(content)
            rows = data if isinstance(data, list) else data.get("places", data.get("items", []))
        else:
            print("ERROR: Only .csv and .json files are supported")
            sys.exit(1)

        result = data_ingestion_service.validate_only(rows, skip_geo_check=args.skip_geo_check)
        elapsed = time.time() - start

        print(f"Validated {result.total} rows in {elapsed:.2f}s")
        print(f"  Valid:    {result.valid}")
        print(f"  Errors:   {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")

        if result.errors:
            print("\nErrors:")
            for e in result.errors[:20]:
                print(f"  Row {e.row}: {e.message}")
            if len(result.errors) > 20:
                print(f"  ... and {len(result.errors) - 20} more")

        if result.warnings:
            print("\nGeo-distance warnings:")
            for w in result.warnings[:10]:
                print(f"  Row {w.row}: {w.place_name} is {w.distance_km}km from {w.city_name}")
            if len(result.warnings) > 10:
                print(f"  ... and {len(result.warnings) - 10} more")

        sys.exit(0 if result.ok else 1)

    # Actual import
    if suffix == ".csv":
        result = data_ingestion_service.import_from_csv(
            content, args.type, source="cli", ingested_by=args.user
        )
    elif suffix == ".json":
        result = data_ingestion_service.import_from_json(
            content, args.type, source="cli", ingested_by=args.user
        )
    else:
        print("ERROR: Only .csv and .json files are supported")
        sys.exit(1)

    elapsed = time.time() - start

    print(f"Completed in {elapsed:.2f}s")
    print(f"  Inserted: {result.inserted}")
    print(f"  Skipped:  {result.skipped}")
    print(f"  Errors:   {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.errors:
        print("\nErrors:")
        for e in result.errors[:20]:
            print(f"  Row {e.row}: {e.message}")
        if len(result.errors) > 20:
            print(f"  ... and {len(result.errors) - 20} more")

    if result.warnings:
        print("\nGeo-distance warnings:")
        for w in result.warnings[:10]:
            print(f"  Row {w.row}: {w.place_name} is {w.distance_km}km from {w.city_name}")

    sys.exit(0 if not result.errors else 1)


if __name__ == "__main__":
    main()
