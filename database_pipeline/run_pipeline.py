#!/usr/bin/env python3
"""
run_pipeline.py

Master pipeline runner that orchestrates the full data processing workflow:
  1. Fill missing coordinates and addresses (fill_coords_addresses.py)
  2. Calculate ranking scores (database_pipeline/ranking_engine.py)
  3. Fetch and attach photos (database_pipeline/photo_engine.py)

Usage:
  python run_pipeline.py --database-dir web/backend/world_database --write
  python run_pipeline.py --dry-run  # preview changes without writing

Features:
  - Auto-discovers all JSON files recursively in the database directory
  - Runs each stage in sequence for all discovered files
  - Reports summary statistics after each stage
  - Supports dry-run mode for safe previewing
  - Logs errors and continues processing remaining files

Requirements:
  - Python 3.7+
  - requests package (optional, for geocoding and photo fetching)
  - All pipeline scripts must be in their expected locations
"""

import argparse
import json
import os
import subprocess
import sys
from typing import List, Dict


def discover_json_files(root_dir: str) -> List[str]:
    """Recursively find all .json files under root_dir."""
    json_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith('.json'):
                json_files.append(os.path.join(dirpath, fname))
    return json_files


def run_stage(stage_name: str, script_path: str, args: List[str], json_files: List[str],
              write: bool = False) -> Dict:
    """
    Run a pipeline stage script for all JSON files.
    Returns: {'stage': name, 'status': 'success'|'error', 'processed': count, 'errors': [...]}
    """
    print(f"\n{'='*70}")
    print(f"STAGE: {stage_name}")
    print(f"{'='*70}\n")
    
    if not os.path.isfile(script_path):
        return {'stage': stage_name, 'status': 'error', 'error': f'Script not found: {script_path}'}
    
    errors = []
    processed = 0
    
    # Build base command
    base_cmd = [sys.executable, script_path] + args
    if write:
        base_cmd.append('--write')
    
    # For fill_coords_addresses, we can pass the directory once
    if 'fill_coords_addresses' in script_path:
        cmd = base_cmd + ['--database-dir', os.path.dirname(json_files[0]) if json_files else '.']
        print(f"Running: {' '.join(cmd)}\n")
        try:
            result = subprocess.run(cmd, capture_output=False, text=True, check=False)
            if result.returncode == 0:
                processed = len(json_files)
            else:
                errors.append({'file': 'batch', 'error': f'exit code {result.returncode}'})
        except Exception as e:
            errors.append({'file': 'batch', 'error': str(e)})
    else:
        # For ranking and photo engines, process each file individually
        for json_file in json_files:
            cmd = base_cmd + [json_file]
            print(f"Running: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    processed += 1
                    print(f"✓ {json_file}")
                else:
                    errors.append({'file': json_file, 'error': f'exit code {result.returncode}', 'stderr': result.stderr})
                    print(f"✗ {json_file}: {result.stderr[:200]}")
            except Exception as e:
                errors.append({'file': json_file, 'error': str(e)})
                print(f"✗ {json_file}: {e}")
    
    status = 'success' if not errors else ('partial' if processed > 0 else 'error')
    return {'stage': stage_name, 'status': status, 'processed': processed, 'total': len(json_files), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description='Run the complete data processing pipeline')
    parser.add_argument('--database-dir', default='web/backend/world_database',
                       help='Root directory containing JSON database files (default: web/backend/world_database)')
    parser.add_argument('--write', action='store_true',
                       help='Write changes to files (default is dry-run)')
    parser.add_argument('--skip-fill', action='store_true',
                       help='Skip coordinate/address filling stage')
    parser.add_argument('--skip-ranking', action='store_true',
                       help='Skip ranking calculation stage')
    parser.add_argument('--skip-photos', action='store_true',
                       help='Skip photo fetching stage')
    parser.add_argument('--geocode', action='store_true',
                       help='Enable Nominatim geocoding in fill stage (requires internet)')
    parser.add_argument('--csv', help='CSV mapping file for coordinate filling stage')
    args = parser.parse_args()
    
    # Validate database directory
    if not os.path.isdir(args.database_dir):
        print(f"Error: Database directory not found: {args.database_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Discover JSON files
    print(f"Scanning {args.database_dir} for JSON files...")
    json_files = discover_json_files(args.database_dir)
    
    if not json_files:
        print(f"No JSON files found in {args.database_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files:\n")
    for f in json_files[:10]:  # show first 10
        print(f"  - {f}")
    if len(json_files) > 10:
        print(f"  ... and {len(json_files) - 10} more")
    
    # Define pipeline stages
    stages = []
    
    # Stage 1: Fill coordinates and addresses
    if not args.skip_fill:
        fill_script = os.path.join('web', 'backend', 'scripts', 'fill_coords_addresses.py')
        fill_args = []
        if args.geocode:
            fill_args.append('--geocode')
        if args.csv:
            fill_args.extend(['--csv', args.csv])
        stages.append({
            'name': 'Fill Coordinates & Addresses',
            'script': fill_script,
            'args': fill_args
        })
    
    # Stage 2: Calculate ranking scores
    if not args.skip_ranking:
        ranking_script = os.path.join('database_pipeline', 'ranking_engine.py')
        stages.append({
            'name': 'Calculate Ranking Scores',
            'script': ranking_script,
            'args': []
        })
    
    # Stage 3: Fetch photos
    if not args.skip_photos:
        photo_script = os.path.join('database_pipeline', 'photo_engine.py')
        stages.append({
            'name': 'Fetch Photos',
            'script': photo_script,
            'args': []
        })
    
    # Execute pipeline
    results = []
    for stage in stages:
        result = run_stage(stage['name'], stage['script'], stage['args'], json_files, write=args.write)
        results.append(result)
        
        # Stop on critical errors
        if result['status'] == 'error' and result['processed'] == 0:
            print(f"\n⚠ Critical error in stage '{stage['name']}'. Stopping pipeline.", file=sys.stderr)
            break
    
    # Print final summary
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}\n")
    
    for result in results:
        status_icon = {'success': '✓', 'partial': '⚠', 'error': '✗'}.get(result['status'], '?')
        print(f"{status_icon} {result['stage']}: {result.get('processed', 0)}/{result.get('total', 0)} files")
        if result.get('errors'):
            print(f"  Errors: {len(result['errors'])}")
            for err in result['errors'][:3]:  # show first 3 errors
                print(f"    - {err.get('file', 'unknown')}: {err.get('error', 'unknown error')[:80]}")
            if len(result['errors']) > 3:
                print(f"    ... and {len(result['errors']) - 3} more errors")
    
    print(f"\n{'='*70}")
    if args.write:
        print("Pipeline complete. Changes written to database files.")
    else:
        print("Dry-run complete. No files modified. Re-run with --write to apply changes.")
    print(f"{'='*70}\n")
    
    # Save detailed results
    results_file = 'pipeline_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'files': json_files}, f, indent=2)
    print(f"Detailed results saved to: {results_file}")


if __name__ == '__main__':
    main()
