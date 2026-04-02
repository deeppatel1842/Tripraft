"""
FTS5 Index Migration Script

Adds full-text search capabilities to travel_data_complete.db:
1. Creates FTS5 virtual table for place/city/state/country name searching
2. Adds composite indexes for ranked queries
3. Enables WAL mode for concurrent read performance

Run: python web/backend/scripts/add_fts_index.py
"""

import sqlite3
import sys
import time
from pathlib import Path

# Resolve database path
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent.parent / 'database' / 'travel_data_complete.db'


def run_migration():
    """Execute the FTS5 migration."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print(f"Database: {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    print()

    steps = [
        ("Enable WAL mode", _enable_wal),
        ("Create FTS5 virtual table", _create_fts5_table),
        ("Populate FTS5 index", _populate_fts5),
        ("Create composite indexes", _create_composite_indexes),
        ("Verify FTS5 index", _verify_fts5),
    ]

    for step_name, step_fn in steps:
        print(f"  [{step_name}] ... ", end="", flush=True)
        start = time.time()
        try:
            step_fn(cursor)
            conn.commit()
            elapsed = (time.time() - start) * 1000
            print(f"OK ({elapsed:.0f}ms)")
        except Exception as e:
            conn.rollback()
            print(f"FAILED: {e}")
            conn.close()
            sys.exit(1)

    conn.close()
    print("\nMigration complete.")


def _enable_wal(cursor):
    """Enable WAL journal mode for concurrent reads."""
    cursor.execute("PRAGMA journal_mode=WAL")
    result = cursor.fetchone()[0]
    if result.lower() != 'wal':
        raise RuntimeError(f"Expected WAL mode, got: {result}")


def _create_fts5_table(cursor):
    """Create FTS5 virtual table for full-text search across place hierarchy."""
    # Drop if exists (idempotent)
    cursor.execute("DROP TABLE IF EXISTS places_fts")

    # Create contentless FTS5 table for search across the place hierarchy
    # Contentless (content='') means FTS5 stores only the index, not the original text
    # This saves space since data lives in the source tables
    cursor.execute("""
        CREATE VIRTUAL TABLE places_fts USING fts5(
            place_name,
            name_english,
            city_name,
            state_name,
            country_name,
            content='',
            tokenize='unicode61 remove_diacritics 2'
        )
    """)


def _populate_fts5(cursor):
    """Populate FTS5 index from joined place data."""
    cursor.execute("""
        INSERT INTO places_fts(rowid, place_name, name_english, city_name, state_name, country_name)
        SELECT
            p.id,
            p.place_name,
            COALESCE(p.name_english, ''),
            ci.city_name,
            s.state_name,
            c.country_name
        FROM places p
        JOIN cities ci ON p.city_id = ci.id
        JOIN states s ON ci.state_id = s.id
        JOIN countries c ON s.country_id = c.id
    """)

    # Verify row count matches
    cursor.execute("SELECT COUNT(*) FROM places")
    places_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM places_fts")
    fts_count = cursor.fetchone()[0]

    if places_count != fts_count:
        raise RuntimeError(
            f"FTS5 count mismatch: {fts_count} indexed vs {places_count} places"
        )


def _create_composite_indexes(cursor):
    """Create composite indexes for common query patterns."""
    indexes = [
        # Places ranked within a city
        ("idx_places_city_rank", "CREATE INDEX IF NOT EXISTS idx_places_city_rank ON places(city_id, rank_score DESC)"),
        # Places ranked within a state (via cities)
        ("idx_cities_state_id", "CREATE INDEX IF NOT EXISTS idx_cities_state_id ON cities(state_id)"),
        # Places by cost for filtering
        ("idx_places_cost", "CREATE INDEX IF NOT EXISTS idx_places_cost ON places(cost)"),
        # Places by rating for filtering
        ("idx_places_rating", "CREATE INDEX IF NOT EXISTS idx_places_rating ON places(rating_tourist_priority)"),
        # Country name lookup (case-insensitive via collation)
        ("idx_countries_name_lower", "CREATE INDEX IF NOT EXISTS idx_countries_name_lower ON countries(country_name COLLATE NOCASE)"),
        # State name lookup
        ("idx_states_name_lower", "CREATE INDEX IF NOT EXISTS idx_states_name_lower ON states(state_name COLLATE NOCASE)"),
        # City name lookup
        ("idx_cities_name_lower", "CREATE INDEX IF NOT EXISTS idx_cities_name_lower ON cities(city_name COLLATE NOCASE)"),
        # Place name lookup
        ("idx_places_name_lower", "CREATE INDEX IF NOT EXISTS idx_places_name_lower ON places(place_name COLLATE NOCASE)"),
        # Tags join index
        ("idx_place_tags_place", "CREATE INDEX IF NOT EXISTS idx_place_tags_place ON place_tags(place_id)"),
        ("idx_place_tags_tag", "CREATE INDEX IF NOT EXISTS idx_place_tags_tag ON place_tags(tag_id)"),
    ]

    for idx_name, sql in indexes:
        cursor.execute(sql)


def _verify_fts5(cursor):
    """Verify FTS5 index works correctly."""
    # Test a basic MATCH query
    cursor.execute("""
        SELECT rowid, place_name FROM places_fts 
        WHERE places_fts MATCH 'taj' 
        LIMIT 5
    """)
    results = cursor.fetchall()
    if not results:
        # Try a broader query to ensure something exists
        cursor.execute("SELECT COUNT(*) FROM places_fts")
        count = cursor.fetchone()[0]
        if count == 0:
            raise RuntimeError("FTS5 index is empty")

    # Test EXPLAIN QUERY PLAN to confirm FTS usage
    cursor.execute("""
        EXPLAIN QUERY PLAN 
        SELECT rowid FROM places_fts WHERE places_fts MATCH 'paris'
    """)
    plan = cursor.fetchall()
    plan_text = str(plan)
    if 'VIRTUAL TABLE' not in plan_text.upper() and 'SCAN' not in plan_text.upper():
        print(f"\n  WARNING: Query plan may not use FTS5: {plan_text}")


if __name__ == '__main__':
    print("=== FTS5 Index Migration ===\n")
    run_migration()
