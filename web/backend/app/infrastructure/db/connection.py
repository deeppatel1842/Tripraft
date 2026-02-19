"""
SQLAlchemy Connection Manager
==============================
SINGLE SOURCE OF TRUTH for the ORM database connection.

Physical target: database/tripraft.db
Used by: users, expenses, group planner (all ORM models)
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from flask import Flask
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Base

logger = logging.getLogger(__name__)

# Database configuration — points to web/database/
DATABASE_DIR = Path(__file__).parent.parent.parent.parent.parent / 'database'
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f'sqlite:///{DATABASE_DIR}/tripraft.db'
)

# Create engine based on database type
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=os.getenv('SQL_ECHO', 'false').lower() == 'true'
    )

    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        """Enable foreign keys for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=os.getenv('SQL_ECHO', 'false').lower() == 'true'
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe scoped session
db = scoped_session(SessionLocal)


def _import_all_models():
    """Import all ORM models so Base.metadata knows about their tables."""
    from importlib import import_module
    import_module('app.domain.users.models')
    import_module('app.domain.expenses.models')
    import_module('app.domain.group_planner.models')


def init_db(app: Flask = None) -> None:
    """
    Initialize database — create tables if they don't exist.
    
    Imports all domain models first so their table metadata is
    registered with Base before calling create_all.
    """
    _import_all_models()
    Base.metadata.create_all(bind=engine)
    logger.info('Database initialized: %s', DATABASE_URL.split('///')[-1])

    if app:
        @app.teardown_appcontext
        def shutdown_session(_exception=None):
            db.remove()


def get_db_session() -> Session:
    """Get a new database session (caller must close)."""
    return SessionLocal()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db() as session:
            user = session.query(User).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db() -> None:
    """Reset database — DROP AND RECREATE ALL TABLES (testing only)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.warning('Database reset — all data deleted!')
    logger.warning("Database reset — all data deleted!")
