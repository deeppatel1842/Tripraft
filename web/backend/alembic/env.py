"""
Alembic Environment Configuration
===================================
Connects Alembic to the app's SQLAlchemy metadata and database URL.
Supports both online (live DB) and offline (SQL script) modes.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure the backend package is importable (web/backend/ on sys.path)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.ai.models import AIConsent  # noqa: E402, F401
from app.domain.ai.models import AIAgentLog, AIPreferenceProfile
from app.domain.expenses.models import Expense  # noqa: E402, F401
from app.domain.expenses.models import (ExpenseHistory, ExpenseSplit, Group,
                                        GroupBalance, GroupMember, Invitation,
                                        Settlement)
from app.domain.group_planner.models import ChecklistItem  # noqa: E402, F401
from app.domain.group_planner.models import (GroupActivity, ItineraryDocument,
                                             Notification, Place, PlaceVote,
                                             Poll, PollVote, TravelGroup,
                                             TripInvitation, TripMember)
from app.domain.users.models import (AuditLog, User,  # noqa: E402, F401
                                     UserSession)
# ---------------------------------------------------------------------------
# Import ALL models so Base.metadata contains every table
# ---------------------------------------------------------------------------
from app.infrastructure.db.base import Base  # noqa: E402

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at the app's metadata (all tables registered above)
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override sqlalchemy.url from env var if set (production deploys)
# ---------------------------------------------------------------------------
database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live database connection."""
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
