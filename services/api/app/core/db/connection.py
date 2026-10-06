# Purpose: SQLAlchemy Connection Manager SINGLE SOURCE OF TRUTH for the ORM database connection.
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
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Base
from app.core.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URLs — defaults to SQLite for local dev, override for PostgreSQL
# ---------------------------------------------------------------------------
DATABASE_URL = Config.DATABASE_URL
if DATABASE_URL.startswith('sqlite'):
    sqlite_file = make_url(DATABASE_URL).database
    if sqlite_file and sqlite_file != ':memory:':
        Path(sqlite_file).parent.mkdir(parents=True, exist_ok=True)

TRAVEL_DATA_URL = os.getenv(
    'TRAVEL_DATA_URL',
    Config.TRAVEL_DATA_URL
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
    # File databases need separate connections for concurrent transactions.
    # Sharing one connection via StaticPool lets threads share writer locks.
    pool_options = (
        {'poolclass': StaticPool}
        if make_url(url).database in (None, '', ':memory:') else {}
    )
    eng = create_engine(
        url,
        connect_args={'check_same_thread': False},
        **pool_options,
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
    import_module('app.auth.models')
    import_module('app.expenses.models')
    import_module('app.trips.models')
    import_module('app.scout.models')


def init_db(app: Optional[Flask] = None) -> None:
    """Verify a migrated schema; application startup never changes DDL."""
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config as AlembicConfig
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    _import_all_models()
    backend_root = Path(__file__).resolve().parents[3]
    migration_config = AlembicConfig(str(backend_root / 'alembic.ini'))
    migration_config.set_main_option('script_location', str(backend_root / 'migrations'))
    expected_heads = set(ScriptDirectory.from_config(migration_config).get_heads())
    with engine.connect() as connection:
        migration_context = MigrationContext.configure(connection, opts={
            'compare_type': True,
            'compare_server_default': True,
        })
        if set(migration_context.get_current_heads()) != expected_heads:
            raise RuntimeError(
                'Database migrations are not current. Run alembic upgrade head '
                'from services/api before starting the application.'
            )
        differences = compare_metadata(migration_context, Base.metadata)
        if differences:
            raise RuntimeError(
                'Database schema drift detected. Run alembic check and repair '
                'the schema with an explicit migration before starting the application.'
            )

    db_label = 'PostgreSQL' if not _IS_SQLITE else 'SQLite'
    logger.info('TripRaft database schema verified (%s)', db_label)

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
