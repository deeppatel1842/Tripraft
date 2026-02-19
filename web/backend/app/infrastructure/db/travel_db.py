"""
Travel Data Database — travel_data_complete.db
================================================
SINGLE connection manager for the read-only travel reference database.

Replaces 4 separate sqlite3 connection patterns that existed in:
  - api/utils/database.py
  - place_search/database.py
  - api/routes/trip_planner.py (inline)
  - Group_planner/services/places_service.py (inline)

All modules now import `travel_db` from here.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Resolve database path
DATA_DIR = Path(__file__).parent.parent.parent.parent / 'data'


class TravelDatabase:
    """
    Single connection manager for travel_data_complete.db (read-only).

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

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

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


# ---------------------------------------------------------------------------
# Singleton — import this everywhere
# ---------------------------------------------------------------------------
travel_db = TravelDatabase()
