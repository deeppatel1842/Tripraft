# Purpose: Place Search Database Module Thread-safe database connection pool for the travel database.
"""
Place Search Database Module

Thread-safe database connection pool for the travel database.
Used by PlaceSearchService and location API routes.
Delegates connection creation to TravelDatabase (infrastructure layer).
"""

import logging
import queue
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Config

DATABASE_PATH = Config.TRAVEL_DATABASE_PATH

logger = logging.getLogger(__name__)

# Pool configuration
_POOL_SIZE = 5
_POOL_TIMEOUT = 10  # seconds to wait for a connection


class DatabaseConnection:
    """Thread-safe database connection pool for place search."""

    def __init__(self, db_path: Optional[Path] = None, pool_size: int = _POOL_SIZE):
        self.db_path = db_path or DATABASE_PATH
        self._validate_database()
        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        self._pool_size = pool_size
        self._created = 0
        self._lock = threading.Lock()
        self._wal_enabled = False
        self._enable_wal()

    def _validate_database(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def _enable_wal(self) -> None:
        """Enable WAL journal mode once on startup."""
        try:
            from app.core.db.travel_db import TravelDatabase
            db = TravelDatabase(self.db_path)
            with db.get_connection() as conn:
                mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                self._wal_enabled = mode.lower() == 'wal'
                if self._wal_enabled:
                    logger.info("SQLite WAL mode enabled: %s", self.db_path.name)
        except Exception as e:
            logger.warning("Could not enable WAL mode: %s", e)

    def _create_connection(self):
        """Create a new SQLite connection via TravelDatabase factory."""
        from app.core.db.travel_db import TravelDatabase
        db = TravelDatabase(self.db_path)
        # Open a raw connection through TravelDatabase's path (validated)
        conn = db._raw_connection(read_only=True)
        return conn

    @contextmanager
    def get_connection(self):
        """Borrow a connection from the pool, return it when done."""
        conn = None
        try:
            # Try to get an existing connection from the pool
            try:
                conn = self._pool.get_nowait()
            except queue.Empty:
                # Pool empty — create new if under limit, else wait
                with self._lock:
                    if self._created < self._pool_size:
                        conn = self._create_connection()
                        self._created += 1
                if conn is None:
                    conn = self._pool.get(timeout=_POOL_TIMEOUT)
            yield conn
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            # Discard broken connection
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._created -= 1
                conn = None
            raise
        finally:
            if conn is not None:
                try:
                    self._pool.put_nowait(conn)
                except queue.Full:
                    conn.close()
                    with self._lock:
                        self._created -= 1

    def execute_query(
        self,
        query: str,
        params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return all rows as dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_single(
        self,
        query: str,
        params: tuple = ()
    ) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first row or None."""
        results = self.execute_query(query, params)
        return results[0] if results else None

    def execute_count(self, query: str, params: tuple = ()) -> int:
        """Execute a COUNT query and return the integer result."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]

    def close_all(self) -> None:
        """Close all pooled connections (call on shutdown)."""
        closed = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                closed += 1
            except queue.Empty:
                break
        with self._lock:
            self._created = 0
        if closed:
            logger.info("Closed %d pooled connections", closed)


# Singleton database instance
_db_instance: Optional[DatabaseConnection] = None
_instance_lock = threading.Lock()


def get_database() -> DatabaseConnection:
    """Get thread-safe database connection singleton."""
    global _db_instance
    if _db_instance is None:
        with _instance_lock:
            if _db_instance is None:
                _db_instance = DatabaseConnection()
    return _db_instance
