"""
Database Migration Script: Embed Top Places in Location Documents

This script updates the Firestore database schema to include embedded place data
in country, state, and city documents. This eliminates the need for multiple
queries and reduces Firebase reads from 1000+ to 1-2 per search.

Schema Changes:
1. Cities: Add top_places[] (20 places)
2. States: Add top_places[] (20 places)
3. Countries: Add states[] with embedded top_places (5 per state)

Usage:
    python migrate_embed_places.py

Requirements:
    - FIREBASE_CREDENTIALS environment variable must be set
    - Firebase Admin SDK must be installed
    - Sufficient permissions to update Firestore documents
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Check if already initialized
        try:
            app = firebase_admin.get_app()
            logger.info("Firebase already initialized")
        except ValueError:
            # Initialize Firebase
            cred_path = os.getenv('FIREBASE_CREDENTIALS')
            if not cred_path:
                raise ValueError("FIREBASE_CREDENTIALS environment variable not set")
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized with credentials from {cred_path}")
        
        db = firestore.client()
        return db
    
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise

def embed_places_in_cities(db, dry_run=False):
    """
    Embed top 20 places in each city document
    
    Changes:
        cities/{city_id}:
            + top_places: [place1, place2, ..., place20]
            + last_updated: timestamp
    """
    logger.info("\n" + "=" * 80)
    logger.info("📍 PHASE 1: Embedding places in cities")
    logger.info("=" * 80)
    
    cities_ref = db.collection('cities')
    cities_docs = list(cities_ref.stream())
    
    logger.info(f"Found {len(cities_docs)} cities to process")
    
    updated_count = 0
    skipped_count = 0
    
    for city_doc in cities_docs:
        city_id = city_doc.id
        city_data = city_doc.to_dict()
        city_name = city_data.get('name')
        
        if not city_name:
            logger.warning(f"  ⚠️  Skipping city {city_id} (no name)")
            skipped_count += 1
            continue
        
        try:
            # Get top 20 places for this city
            places_query = db.collection('places') \
                .where('city_name', '==', city_name) \
                .order_by('rank_score', direction=firestore.Query.DESCENDING) \
                .limit(20)
            
            places_docs = list(places_query.stream())
            top_places = [doc.to_dict() for doc in places_docs]
            
            if not dry_run:
                # Update city document
                cities_ref.document(city_id).update({
                    'top_places': top_places,
                    'place_count': len(top_places),
                    'last_updated': datetime.now()
                })
            
            logger.info(f"  ✅ {city_name}: Embedded {len(top_places)} places")
            updated_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {city_name}: {e}")
            skipped_count += 1
    
    logger.info(f"\n✅ Phase 1 complete: {updated_count} cities updated, {skipped_count} skipped")
    return updated_count, skipped_count

def embed_places_in_states(db, dry_run=False):
    """
    Embed top 20 places in each state document
    
    Changes:
        states/{state_id}:
            + top_places: [place1, place2, ..., place20]
            + last_updated: timestamp
    """
    logger.info("\n" + "=" * 80)
    logger.info("🗺️  PHASE 2: Embedding places in states")
    logger.info("=" * 80)
    
    states_ref = db.collection('states')
    states_docs = list(states_ref.stream())
    
    logger.info(f"Found {len(states_docs)} states to process")
    
    updated_count = 0
    skipped_count = 0
    
    for state_doc in states_docs:
        state_id = state_doc.id
        state_data = state_doc.to_dict()
        state_name = state_data.get('name')
        
        if not state_name:
            logger.warning(f"  ⚠️  Skipping state {state_id} (no name)")
            skipped_count += 1
            continue
        
        try:
            # Get top 20 places for this state
            places_query = db.collection('places') \
                .where('state_name', '==', state_name) \
                .order_by('rank_score', direction=firestore.Query.DESCENDING) \
                .limit(20)
            
            places_docs = list(places_query.stream())
            top_places = [doc.to_dict() for doc in places_docs]
            
            if not dry_run:
                # Update state document
                states_ref.document(state_id).update({
                    'top_places': top_places,
                    'place_count': len(top_places),
                    'last_updated': datetime.now()
                })
            
            logger.info(f"  ✅ {state_name}: Embedded {len(top_places)} places")
            updated_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {state_name}: {e}")
            skipped_count += 1
    
    logger.info(f"\n✅ Phase 2 complete: {updated_count} states updated, {skipped_count} skipped")
    return updated_count, skipped_count

def embed_states_in_countries(db, dry_run=False):
    """
    Embed states with their top 5 places in each country document
    
    Changes:
        countries/{country_id}:
            + states: [
                {
                    state_id: "maharashtra",
                    state_name: "Maharashtra",
                    place_count: 100,
                    top_places: [place1, place2, ..., place5]
                },
                ...
            ]
            + last_updated: timestamp
    """
    logger.info("\n" + "=" * 80)
    logger.info("🌍 PHASE 3: Embedding states in countries")
    logger.info("=" * 80)
    
    countries_ref = db.collection('countries')
    countries_docs = list(countries_ref.stream())
    
    logger.info(f"Found {len(countries_docs)} countries to process")
    
    updated_count = 0
    skipped_count = 0
    
    for country_doc in countries_docs:
        country_id = country_doc.id
        country_data = country_doc.to_dict()
        country_name = country_data.get('name')
        
        if not country_name:
            logger.warning(f"  ⚠️  Skipping country {country_id} (no name)")
            skipped_count += 1
            continue
        
        try:
            # Get all states in this country
            states_query = db.collection('states') \
                .where('country', '==', country_name)
            
            states_docs = list(states_query.stream())
            
            states_with_places = []
            
            for state_doc in states_docs:
                state_data = state_doc.to_dict()
                state_name = state_data.get('name')
                
                if not state_name:
                    continue
                
                # Get top 5 places for this state
                places_query = db.collection('places') \
                    .where('state_name', '==', state_name) \
                    .order_by('rank_score', direction=firestore.Query.DESCENDING) \
                    .limit(5)
                
                places_docs = list(places_query.stream())
                top_places = [doc.to_dict() for doc in places_docs]
                
                states_with_places.append({
                    'state_id': state_doc.id,
                    'state_name': state_name,
                    'place_count': state_data.get('place_count', 0),
                    'top_places': top_places
                })
            
            if not dry_run:
                # Update country document
                countries_ref.document(country_id).update({
                    'states': states_with_places,
                    'state_count': len(states_with_places),
                    'last_updated': datetime.now()
                })
            
            logger.info(f"  ✅ {country_name}: Embedded {len(states_with_places)} states")
            updated_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {country_name}: {e}")
            skipped_count += 1
    
    logger.info(f"\n✅ Phase 3 complete: {updated_count} countries updated, {skipped_count} skipped")
    return updated_count, skipped_count

def main():
    """Run migration"""
    logger.info("=" * 80)
    logger.info("🚀 DATABASE MIGRATION: Embed Places in Location Documents")
    logger.info("=" * 80)
    logger.info("\nThis will reduce Firebase reads from 1000+ to 1-2 per search")
    logger.info("Estimated time: 10-30 minutes (depending on database size)")
    
    # Ask for confirmation
    response = input("\nDo you want to proceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        logger.info("❌ Migration cancelled by user")
        return
    
    # Ask for dry run
    dry_run = False
    response = input("\nRun in DRY RUN mode (no changes)? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        dry_run = True
        logger.info("🔍 Running in DRY RUN mode (no changes will be made)")
    
    try:
        # Initialize Firebase
        db = init_firebase()
        
        # Run migrations
        start_time = datetime.now()
        
        cities_updated, cities_skipped = embed_places_in_cities(db, dry_run)
        states_updated, states_skipped = embed_places_in_states(db, dry_run)
        countries_updated, countries_skipped = embed_states_in_countries(db, dry_run)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Cities updated: {cities_updated} (skipped: {cities_skipped})")
        logger.info(f"✅ States updated: {states_updated} (skipped: {states_skipped})")
        logger.info(f"✅ Countries updated: {countries_updated} (skipped: {countries_skipped})")
        logger.info(f"\n⏱️  Total time: {duration:.1f} seconds")
        
        if dry_run:
            logger.info("\n🔍 DRY RUN complete - no changes were made")
            logger.info("   Run again without DRY RUN mode to apply changes")
        else:
            logger.info("\n🎉 MIGRATION COMPLETE!")
            logger.info("   Database schema updated successfully")
            logger.info("   Firebase reads reduced from 1000+ to 1-2 per search")
    
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        raise

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Migration failed: {e}")
        sys.exit(1)
