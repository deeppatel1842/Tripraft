"""
SQLAlchemy Connection Manager
==============================
SINGLE SOURCE OF TRUTH for the ORM database connection.

Supports both SQLite (dev) and PostgreSQL (production).
Configured via DATABASE_URL environment variable.

Architecture:
  - engine          → Primary DB (tripraft.db / PostgreSQL primary)
  - travel_engine   → Travel data read replica (travel_data_complete.db / PostgreSQL replica)
  - RoutingSession  → Routes read queries to the appropriate engine
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from flask import Flask
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URLs — defaults to SQLite for local dev, override for PostgreSQL
# ---------------------------------------------------------------------------
_DEFAULT_SQLITE_DIR = Path(__file__).parent.parent.parent.parent.parent / 'database'
_DEFAULT_SQLITE_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f'sqlite:///{_DEFAULT_SQLITE_DIR}/tripraft.db'
)

TRAVEL_DATA_URL = os.getenv(
    'TRAVEL_DATA_URL',
    f'sqlite:///{_DEFAULT_SQLITE_DIR}/travel_data_complete.db'
)

_SQL_ECHO = os.getenv('SQL_ECHO', 'false').lower() == 'true'
_IS_SQLITE = DATABASE_URL.startswith('sqlite')

# ---------------------------------------------------------------------------
# Tables that live on the travel data replica
# ---------------------------------------------------------------------------
TRAVEL_DATA_TABLES: frozenset = frozenset({
    'countries', 'states', 'cities', 'places',
    'place_photos', 'place_tags', 'opening_hours',
    'ingestion_log', 'places_fts',
})


# ---------------------------------------------------------------------------
# Primary Engine — SQLite for local dev, PostgreSQL for production
# ---------------------------------------------------------------------------
def _create_sqlite_engine(url: str, pool_size_hint: int = 0):
    """Create a SQLite engine with WAL mode and foreign keys."""
    eng = create_engine(
        url,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=_SQL_ECHO,
    )

    @event.listens_for(eng, 'connect')
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.close()

    return eng


def _create_pg_engine(url: str, pool_size: int = 20, max_overflow: int = 10):
    """Create a PostgreSQL engine with production-grade pool settings."""
    return create_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '1800')),
        pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
        pool_pre_ping=True,
        echo=_SQL_ECHO,
    )


if _IS_SQLITE:
    engine = _create_sqlite_engine(DATABASE_URL)
else:
    engine = _create_pg_engine(
        DATABASE_URL,
        pool_size=int(os.getenv('DB_POOL_SIZE', '20')),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
    )


# ---------------------------------------------------------------------------
# Travel Data Read Replica Engine
# ---------------------------------------------------------------------------
if TRAVEL_DATA_URL.startswith('sqlite'):
    travel_engine = _create_sqlite_engine(TRAVEL_DATA_URL)
else:
    travel_engine = _create_pg_engine(
        TRAVEL_DATA_URL,
        pool_size=int(os.getenv('TRAVEL_POOL_SIZE', '10')),
        max_overflow=int(os.getenv('TRAVEL_MAX_OVERFLOW', '5')),
    )

logger.info(
    'Engines created — primary: %s, travel: %s',
    'SQLite' if _IS_SQLITE else 'PostgreSQL',
    'SQLite' if TRAVEL_DATA_URL.startswith('sqlite') else 'PostgreSQL',
)


# ---------------------------------------------------------------------------
# Routing Session — directs reads to the correct engine
# ---------------------------------------------------------------------------
class RoutingSession(Session):
    """
    Routes queries to the appropriate engine based on the target table.

    - Flush / write operations → primary engine (always)
    - Reads on TRAVEL_DATA_TABLES → travel_engine (read replica)
    - All other reads → primary engine
    """

    def get_bind(self, mapper=None, clause=None, **kw):
        if self._flushing or self.info.get('is_write'):
            return engine

        if mapper is not None:
            table_name = getattr(mapper.persist_selectable, 'name', None)
            if table_name in TRAVEL_DATA_TABLES:
                return travel_engine

        return engine


# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Routing session factory — use when travel data has ORM models
RoutingSessionLocal = sessionmaker(
    class_=RoutingSession,
    autocommit=False,
    autoflush=False,
)

# Thread-safe scoped session (primary)
db = scoped_session(SessionLocal)


def _import_all_models():
    """Import all ORM models so Base.metadata knows about their tables."""
    from importlib import import_module
    import_module('app.domain.users.models')
    import_module('app.domain.expenses.models')
    import_module('app.domain.group_planner.models')
    import_module('app.domain.ai.models')


def init_db(app: Optional[Flask] = None) -> None:
    """
    Initialize database — create tables if they don't exist.

    For production PostgreSQL, Alembic manages schema evolution.
    create_all() is a safe no-op when tables already exist.
    """
    _import_all_models()
    Base.metadata.create_all(bind=engine)

    db_label = 'PostgreSQL' if not _IS_SQLITE else 'SQLite'
    logger.info('TripRaft database initialized (%s)', db_label)

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
