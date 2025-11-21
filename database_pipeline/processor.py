#!/usr/bin/env python3
"""
TripRaft Database Processing Pipeline
======================================
Automated pipeline that processes raw JSON files through:
1. Ranking calculation
2. Photo enhancement
3. Data validation
4. Final database generation

Usage:
    python processor.py --input california.json
    python processor.py --input-dir ./raw_data
    python processor.py --watch  # Auto-process new files
"""

import json
import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import shutil

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent / "web" / "backend"))

# Import modules
from ranking_engine import RankingEngine
from photo_engine import PhotoEngine

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabasePipeline:
    """Automated database processing pipeline"""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.ranking_engine = RankingEngine()
        self.photo_engine = PhotoEngine()
        
        self.stats = {
            "files_processed": 0,
            "places_ranked": 0,
            "photos_added": 0,
            "errors": 0,
            "start_time": datetime.now(timezone.utc)
        }
    
    def process_file(self, input_file: Path) -> Tuple[bool, str]:
        """Process a single JSON file through the pipeline"""
        logger.info("=" * 70)
        logger.info(f"PROCESSING: {input_file.name}")
        logger.info("=" * 70)
        
        try:
            # Step 1: Load and validate
            logger.info("Step 1/5: Loading JSON file...")
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            original_structure = self._analyze_structure(data)
            logger.info(f"  ✓ Found {original_structure['total_places']} places in {original_structure['containers']} containers")
            
            # Step 2: Add ranking scores
            logger.info("\nStep 2/5: Calculating ranking scores...")
            ranked_count = self.ranking_engine.add_rankings(data)
            self.stats["places_ranked"] += ranked_count
            logger.info(f"  ✓ Ranked {ranked_count} places")
            
            # Step 3: Add photos
            logger.info("\nStep 3/5: Fetching photos from Wikipedia/Commons...")
            photo_count = self.photo_engine.add_photos(data)
            self.stats["photos_added"] += photo_count
            logger.info(f"  ✓ Added photos to {photo_count} places")
            
            # Step 4: Add metadata
            logger.info("\nStep 4/5: Adding pipeline metadata...")
            self._add_metadata(data, input_file, ranked_count, photo_count)
            logger.info("  ✓ Metadata added")
            
            # Step 5: Save output
            logger.info("\nStep 5/5: Saving enriched database...")
            output_file = self.output_dir / input_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✓ Saved to: {output_file}")
            
            self.stats["files_processed"] += 1
            
            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("✅ PROCESSING COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Input:  {input_file}")
            logger.info(f"Output: {output_file}")
            logger.info(f"Places: {original_structure['total_places']}")
            logger.info(f"Ranked: {ranked_count}")
            logger.info(f"Photos: {photo_count}")
            logger.info("=" * 70 + "\n")
            
            return True, str(output_file)
            
        except Exception as e:
            logger.error(f"❌ ERROR processing {input_file.name}: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            return False, str(e)
    
    def _analyze_structure(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Analyze JSON structure"""
        total_places = 0
        containers = 0
        
        # Check for common structures
        if "cities" in data:
            for city in data["cities"]:
                if "places" in city:
                    total_places += len(city["places"])
                    containers += 1
        elif "regions" in data:
            for region in data["regions"]:
                if "places" in region:
                    total_places += len(region["places"])
                    containers += 1
        elif "places" in data:
            total_places = len(data["places"])
            containers = 1
        elif "top_places" in data:
            total_places = len(data["top_places"])
            containers = 1
        
        return {"total_places": total_places, "containers": containers}
    
    def _add_metadata(self, data: Dict[str, Any], source_file: Path, 
                      ranked: int, photos: int):
        """Add comprehensive pipeline metadata"""
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"].update({
            "pipeline_version": "1.0",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "source_file": source_file.name,
            "processing_steps": [
                "ranking_calculation",
                "photo_enhancement",
                "metadata_enrichment"
            ],
            "statistics": {
                "places_ranked": ranked,
                "photos_added": photos,
                "ranking_formula": "tourist_priority(45%) + experience(25%) + tags(15%) + duration(10%) + cost(5%)",
                "photo_sources": ["wikipedia", "wikimedia_commons"]
            },
            "data_quality": {
                "ranking_applied": True,
                "photos_enhanced": True,
                "sorted_by_rank": True
            }
        })
    
    def process_directory(self):
        """Process all JSON files in input directory"""
        json_files = list(self.input_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {self.input_dir}")
            return
        
        logger.info("=" * 70)
        logger.info("TRIPRAFT DATABASE PIPELINE")
        logger.info("=" * 70)
        logger.info(f"Input Directory:  {self.input_dir}")
        logger.info(f"Output Directory: {self.output_dir}")
        logger.info(f"Files to Process: {len(json_files)}")
        logger.info("=" * 70 + "\n")
        
        for i, json_file in enumerate(json_files, 1):
            logger.info(f"\n[{i}/{len(json_files)}] Starting: {json_file.name}")
            success, result = self.process_file(json_file)
            
            if success:
                # Archive processed file
                archive_dir = self.input_dir / "processed"
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(json_file), str(archive_dir / json_file.name))
                logger.info(f"✓ Moved to archive: {archive_dir / json_file.name}\n")
        
        self._print_final_summary()
    
    def watch_directory(self, interval: int = 10):
        """Watch input directory and auto-process new files"""
        logger.info("=" * 70)
        logger.info("PIPELINE WATCH MODE ENABLED")
        logger.info("=" * 70)
        logger.info(f"Watching: {self.input_dir}")
        logger.info(f"Output:   {self.output_dir}")
        logger.info(f"Interval: {interval} seconds")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70 + "\n")
        
        processed_files = set()
        
        try:
            while True:
                json_files = list(self.input_dir.glob("*.json"))
                new_files = [f for f in json_files if f not in processed_files]
                
                for json_file in new_files:
                    logger.info(f"🔔 New file detected: {json_file.name}")
                    success, result = self.process_file(json_file)
                    
                    if success:
                        processed_files.add(json_file)
                        # Archive
                        archive_dir = self.input_dir / "processed"
                        archive_dir.mkdir(exist_ok=True)
                        shutil.move(str(json_file), str(archive_dir / json_file.name))
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Watch mode stopped by user")
            self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final processing summary"""
        duration = datetime.now(timezone.utc) - self.stats["start_time"]
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Files Processed:  {self.stats['files_processed']}")
        logger.info(f"Places Ranked:    {self.stats['places_ranked']}")
        logger.info(f"Photos Added:     {self.stats['photos_added']}")
        logger.info(f"Errors:           {self.stats['errors']}")
        logger.info(f"Duration:         {duration.total_seconds():.1f} seconds")
        logger.info(f"Log File:         {log_file}")
        logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="TripRaft Database Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single file
  python processor.py --input california.json
  
  # Process all files in directory
  python processor.py --input-dir ./raw_data
  
  # Watch mode (auto-process new files)
  python processor.py --watch
  
  # Custom directories
  python processor.py --input-dir ./custom_input --output-dir ./custom_output
        """
    )
    
    parser.add_argument("--input", type=Path, help="Single JSON file to process")
    parser.add_argument("--input-dir", type=Path, help="Directory containing JSON files")
    parser.add_argument("--output-dir", type=Path, help="Output directory for processed files")
    parser.add_argument("--watch", action="store_true", help="Watch input directory for new files")
    parser.add_argument("--watch-interval", type=int, default=10, help="Watch interval in seconds (default: 10)")
    
    args = parser.parse_args()
    
    # Default directories
    default_input = Path(__file__).parent / "input"
    default_output = Path(__file__).parent / "output"
    
    input_dir = args.input_dir or default_input
    output_dir = args.output_dir or default_output
    
    # Create pipeline
    pipeline = DatabasePipeline(input_dir, output_dir)
    
    if args.input:
        # Process single file
        if not args.input.exists():
            logger.error(f"File not found: {args.input}")
            sys.exit(1)
        
        # Copy to input dir and process
        input_copy = input_dir / args.input.name
        shutil.copy(str(args.input), str(input_copy))
        success, result = pipeline.process_file(input_copy)
        
        if success:
            input_copy.unlink()  # Remove from input after processing
        
        sys.exit(0 if success else 1)
    
    elif args.watch:
        # Watch mode
        pipeline.watch_directory(args.watch_interval)
    
    else:
        # Process directory once
        pipeline.process_directory()


if __name__ == "__main__":
    main()
