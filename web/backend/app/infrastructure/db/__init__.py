"""
Database Infrastructure Package

- connection.py  — SQLAlchemy engine for tripraft.db (users, expenses, groups)
- base.py        — Shared declarative Base
- travel_db.py   — sqlite3 manager for travel_data_complete.db (read-only)
"""
from .base import Base
from .connection import (DATABASE_URL, TRAVEL_DATA_TABLES, TRAVEL_DATA_URL,
                         RoutingSession, RoutingSessionLocal, SessionLocal, db,
                         engine, get_db, get_db_session, init_db, reset_db,
                         travel_engine)

__all__ = [
    'Base',
    'DATABASE_URL',
    'TRAVEL_DATA_URL',
    'TRAVEL_DATA_TABLES',
    'SessionLocal',
    'RoutingSession',
    'RoutingSessionLocal',
    'db',
    'engine',
    'travel_engine',
    'get_db',
    'get_db_session',
    'init_db',
    'reset_db',
]

# Optional: Travel database (may not exist in all environments)
try:
    from .travel_db import TravelDatabase, travel_db
    __all__.extend(['TravelDatabase', 'travel_db'])
except (ImportError, FileNotFoundError):
    pass
