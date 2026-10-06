# Purpose: Travel Data Database — travel_data_complete.db Connection manager for the travel reference database.
"""
Travel Data Database — travel_data_complete.db
================================================
Connection manager for the travel reference database.

Provides:
  - Read-only helpers: execute_query, execute_one, execute_count
  - Write helpers: insert_one, insert_many, update_one, delete_one
  - Audit logging for every write via ingestion_log table

All modules now import `travel_db` from here.
"""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Resolve database path — travel DB lives in web/database/, not services/api/data/
from app.core.config import Config
DATA_DIR = Config.DATABASE_DIR

# Allowlisted tables and columns for write operations (SQL injection prevention)
_ALLOWED_TABLES: frozenset = frozenset({
    'countries', 'states', 'cities', 'places', 'photos',
    'tags', 'place_tags', 'opening_hours', 'restaurants',
    'ingestion_log',
})

_ALLOWED_COLUMNS: frozenset = frozenset({
    # Common
    'id', 'created_at', 'updated_at',
    # Countries
    'country_name', 'country_code', 'latitude', 'longitude',
    # States
    'state_name', 'country_id',
    # Cities
    'city_name', 'state_id',
    # Places
    'place_name', 'name_english', 'city_id', 'address',
    'official_website', 'ai_summary', 'suggested_duration',
    'best_time_to_visit', 'place_tip', 'advanced_booking',
    'sunrise_view', 'sunset_view', 'sunrise_time', 'sunset_time',
    'cost', 'rating_tourist_priority', 'rating_traveler_experience',
    'rank_score',
    # Photos
    'place_id', 'thumbnail_url', 'photo_url', 'attribution',
    # Tags / place_tags
    'tag_name', 'tag_id',
    # Opening hours
    'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday', 'notes',
    # Restaurants
    'restaurant_name',
    # Ingestion log
    'entity_type', 'entity_id', 'action', 'source',
    'data_hash', 'errors', 'ingested_by',
})


def _validate_identifier(value: str, allowed: frozenset, kind: str) -> str:
    """Validate a SQL identifier against an allowlist. Raises ValueError on mismatch."""
    if value not in allowed:
        raise ValueError(f"Disallowed {kind}: {value!r}")
    return value


class TravelDatabase:
    """
    Connection manager for travel_data_complete.db.

    Thread-safe: each call opens and closes its own connection.
    Row factory set to sqlite3.Row so results can be accessed by column name.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (DATA_DIR / 'travel_data_complete.db')
        self._validated = False

    def _validate(self):
        """Validate DB file exists (lazy, once)."""
        if self._validated:
            return
        if not self.db_path.exists():
            raise FileNotFoundError(f"Travel database not found: {self.db_path}")
        self._validated = True

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _raw_connection(self, read_only: bool = False) -> sqlite3.Connection:
        """
        Create and return a raw SQLite connection.
        Caller is responsible for closing it.
        Used by the connection pool in repository.py.
        """
        self._validate()
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        if read_only:
            conn.execute("PRAGMA query_only = ON")
        return conn

    @contextmanager
    def get_connection(self):
        """
        Context manager for read-only database connections.

        Yields:
            sqlite3.Connection with Row factory enabled.
        """
        self._validate()
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error("Travel DB error: %s", e)
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_connection_rw(self):
        """
        Context manager for read-write connections with WAL mode + foreign keys.

        Auto-commits on success, rolls back on exception.
        """
        self._validate()
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error("Travel DB write error: %s", e)
            raise
        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single result or None."""
        results = self.execute_query(query, params)
        return results[0] if results else None

    def execute_count(self, query: str, params: tuple = ()) -> int:
        """Execute a COUNT query and return the integer result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _data_hash(data: Dict[str, Any]) -> str:
        """Deterministic SHA-256 of a dict for audit deduplication."""
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _audit(
        self,
        cursor: sqlite3.Cursor,
        entity_type: str,
        entity_id: Optional[int],
        action: str,
        source: str,
        data: Dict[str, Any],
        errors: Optional[str] = None,
        ingested_by: Optional[str] = None,
    ):
        """Insert a row into ingestion_log within the same transaction."""
        cursor.execute(
            """INSERT INTO ingestion_log
               (entity_type, entity_id, action, source, data_hash, errors, ingested_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_type,
                entity_id,
                action,
                source,
                self._data_hash(data),
                errors,
                ingested_by,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            ),
        )

    def insert_one(
        self,
        table: str,
        data: Dict[str, Any],
        *,
        source: str = "api",
        ingested_by: Optional[str] = None,
    ) -> int:
        """
        Insert a single row and return the new rowid.

        Also records an audit log entry.
        """
        _validate_identifier(table, _ALLOWED_TABLES, "table")
        for col in data:
            _validate_identifier(col, _ALLOWED_COLUMNS, "column")

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        with self.get_connection_rw() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(data.values()))
            row_id = cur.lastrowid
            self._audit(cur, table, row_id, "insert", source, data, ingested_by=ingested_by)
            return row_id

    def insert_many(
        self,
        table: str,
        rows: List[Dict[str, Any]],
        *,
        source: str = "bulk",
        ingested_by: Optional[str] = None,
    ) -> List[int]:
        """
        Insert multiple rows in a single transaction. Returns list of rowids.
        """
        if not rows:
            return []

        _validate_identifier(table, _ALLOWED_TABLES, "table")
        for col in rows[0]:
            _validate_identifier(col, _ALLOWED_COLUMNS, "column")

        cols = ", ".join(rows[0].keys())
        placeholders = ", ".join(["?"] * len(rows[0]))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        ids: List[int] = []
        with self.get_connection_rw() as conn:
            cur = conn.cursor()
            for row_data in rows:
                cur.execute(sql, tuple(row_data.values()))
                rid = cur.lastrowid
                ids.append(rid)
                self._audit(cur, table, rid, "insert", source, row_data, ingested_by=ingested_by)
            return ids

    def update_one(
        self,
        table: str,
        row_id: int,
        data: Dict[str, Any],
        *,
        source: str = "api",
        ingested_by: Optional[str] = None,
    ) -> bool:
        """
        Update a single row by id. Returns True if a row was actually changed.
        """
        if not data:
            return False

        _validate_identifier(table, _ALLOWED_TABLES, "table")
        for col in data:
            _validate_identifier(col, _ALLOWED_COLUMNS, "column")

        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        with self.get_connection_rw() as conn:
            cur = conn.cursor()
            cur.execute(sql, (*data.values(), row_id))
            changed = cur.rowcount > 0
            if changed:
                self._audit(cur, table, row_id, "update", source, data, ingested_by=ingested_by)
            return changed

    def delete_one(
        self,
        table: str,
        row_id: int,
        *,
        source: str = "api",
        ingested_by: Optional[str] = None,
    ) -> bool:
        """
        Delete a single row by id. Returns True if a row was actually deleted.
        """
        _validate_identifier(table, _ALLOWED_TABLES, "table")

        sql = f"DELETE FROM {table} WHERE id = ?"

        with self.get_connection_rw() as conn:
            cur = conn.cursor()
            cur.execute(sql, (row_id,))
            deleted = cur.rowcount > 0
            if deleted:
                self._audit(cur, table, row_id, "delete", source, {"id": row_id}, ingested_by=ingested_by)
            return deleted

    def rebuild_fts(self):
        """Rebuild the FTS5 index after bulk writes."""
        with self.get_connection_rw() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
            logger.info("FTS5 index rebuilt")
travel_db = TravelDatabase()
