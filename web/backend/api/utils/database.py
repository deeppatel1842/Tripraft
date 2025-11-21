"""
Database connection and query utilities
Provides thread-safe database connections with proper error handling.
"""
import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and queries"""
    
    def __init__(self, db_path: Path):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        logger.info(f"Database initialized: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Ensures proper connection cleanup
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dicts
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries with query results
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute a SELECT query and return single result
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Dictionary with query result or None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def execute_count(self, query: str, params: tuple = ()) -> int:
        """
        Execute a COUNT query and return the count
        
        Args:
            query: SQL query string (should include COUNT)
            params: Query parameters
            
        Returns:
            Count result
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection successful
        """
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get table schema information
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def get_tables(self) -> List[str]:
        """
        Get list of all tables in database
        
        Returns:
            List of table names
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        results = self.execute_query(query)
        return [row['name'] for row in results]


# Singleton instance
_db_manager = None


def init_database(db_path: Path) -> DatabaseManager:
    """
    Initialize database manager singleton
    
    Args:
        db_path: Path to database file
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager


def get_db() -> DatabaseManager:
    """
    Get database manager instance
    
    Returns:
        DatabaseManager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager
