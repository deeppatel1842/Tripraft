"""
Ingestion Audit Log Migration
==============================
Creates the ``ingestion_log`` table in travel_data_complete.db so every
write operation (insert/update/delete) from the ingestion pipeline is
recorded for audit purposes.

Run:  python web/backend/scripts/add_ingestion_log.py
"""

import sqlite3
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent.parent / "database" / "travel_data_complete.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT    NOT NULL CHECK(entity_type IN ('place','country','state','city','photo','tag','opening_hours')),
    entity_id       INTEGER,
    action          TEXT    NOT NULL CHECK(action IN ('insert','update','delete')),
    source          TEXT    NOT NULL CHECK(source IN ('api','cli','bulk')),
    data_hash       TEXT,
    errors          TEXT,
    ingested_by     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_ingestion_log_entity ON ingestion_log(entity_type, entity_id);",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_log_created ON ingestion_log(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_log_action ON ingestion_log(action);",
]


def run_migration():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print(f"Database: {DB_PATH}")
    print(f"Size:     {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB\n")

    steps = [
        ("Create ingestion_log table", lambda c: c.execute(CREATE_TABLE_SQL)),
        ("Create indexes", lambda c: [c.execute(s) for s in CREATE_INDEXES_SQL]),
    ]

    for name, fn in steps:
        print(f"  [{name}] ... ", end="", flush=True)
        start = time.time()
        try:
            fn(cursor)
            conn.commit()
            ms = (time.time() - start) * 1000
            print(f"OK ({ms:.0f}ms)")
        except Exception as e:
            conn.rollback()
            print(f"FAILED: {e}")
            conn.close()
            sys.exit(1)

    # Verify
    cursor.execute("SELECT COUNT(*) FROM ingestion_log")
    count = cursor.fetchone()[0]
    print(f"\n  ingestion_log rows: {count}")
    print("Migration complete.")
    conn.close()


if __name__ == "__main__":
    run_migration()
