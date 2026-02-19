"""
Place Search Database Module

Handles database connections and operations.
Uses SQLite for data storage.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Config

DATABASE_PATH = Config.TRAVEL_DATABASE_PATH

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager for place search"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or DATABASE_PATH
        self._validate_database()
    
    def _validate_database(self) -> None:
        """Validate that database file exists"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(
        self, 
        query: str, 
        params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
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
        """
        Execute a query and return single result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single result row as dictionary or None
        """
        results = self.execute_query(query, params)
        return results[0] if results else None


# Singleton database instance
_db_instance: Optional[DatabaseConnection] = None


def get_database() -> DatabaseConnection:
    """
    Get database connection singleton.
    
    Returns:
        DatabaseConnection instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
    return _db_instance
