"""
Database Infrastructure Package

- connection.py  — SQLAlchemy engine for tripraft.db (users, expenses, groups)
- base.py        — Shared declarative Base
- travel_db.py   — sqlite3 manager for travel_data_complete.db (read-only)
"""
from .base import Base
from .connection import (DATABASE_URL, SessionLocal, db, engine, get_db,
                         get_db_session, init_db, reset_db)

__all__ = [
    'Base',
    'DATABASE_URL',
    'SessionLocal',
    'db',
    'engine',
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
