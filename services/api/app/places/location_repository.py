# Purpose: Location Database Utilities Thin wrapper around the shared DatabaseConnection pool from repository.py.
"""
Location Database Utilities

Thin wrapper around the shared DatabaseConnection pool from repository.py.
Maintains backward-compatible init_database / get_db API used by locations.py and factory.py.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.places.repository import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Location DB manager backed by shared connection pool."""

    def __init__(self, db_path: Path):
        self._conn = DatabaseConnection(db_path)
        logger.info("Location database initialized: %s", db_path.name)

    def get_connection(self):
        return self._conn.get_connection()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        return self._conn.execute_query(query, params)

    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        return self._conn.execute_single(query, params)

    def execute_count(self, query: str, params: tuple = ()) -> int:
        return self._conn.execute_count(query, params)

    def test_connection(self) -> bool:
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error("Database connection test failed: %s", e)
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        return self.execute_query(f"PRAGMA table_info({table_name})")

    def get_tables(self) -> List[str]:
        results = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row['name'] for row in results]


# Singleton instance
_db_manager = None


def init_database(db_path: Path) -> DatabaseManager:
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager


def get_db() -> DatabaseManager:
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager
