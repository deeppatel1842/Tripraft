# Purpose: json_to_jsonb_postgresql PostgreSQL-only migration: converts JSON columns to JSONB for indexing,.
"""json_to_jsonb_postgresql

PostgreSQL-only migration: converts JSON columns to JSONB for indexing,
partial updates, and containment queries.

Affected columns:
  - gp_polls.options
  - expense_history.changes_json
  - expense_history.before_snapshot
  - expense_history.after_snapshot
  - gp_group_activities.details
  - gp_notifications.data

Also creates GIN indexes on the JSONB columns for fast containment queries.

On SQLite this migration is a no-op.

Revision ID: 119b418945ce
Revises: e336ee48cb0f
Create Date: 2026-03-19 15:37:19.787625
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision: str = '119b418945ce'
down_revision: Union[str, Sequence[str], None] = 'e336ee48cb0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql(conn: Connection) -> bool:
    return conn.dialect.name == 'postgresql'


# (table, column) pairs to convert from JSON -> JSONB
_COLUMNS = [
    ('gp_polls',            'options'),
    ('expense_history',     'changes_json'),
    ('expense_history',     'before_snapshot'),
    ('expense_history',     'after_snapshot'),
    ('gp_group_activities', 'details'),
    ('gp_notifications',    'data'),
]

# GIN indexes for containment queries (@>, ?)
_GIN_INDEXES = [
    ('idx_gin_polls_options',         'gp_polls',            'options'),
    ('idx_gin_exp_history_changes',   'expense_history',     'changes_json'),
    ('idx_gin_gp_activities_details', 'gp_group_activities', 'details'),
    ('idx_gin_gp_notifications_data', 'gp_notifications',    'data'),
]


def upgrade() -> None:
    """Retired: the fresh baseline owns the portable JSON column types."""
    # Do not cast current JSON columns with legacy assumptions. A dedicated,
    # reviewed migration is required before changing storage types again.
    return

    conn = op.get_bind()
    if not _is_postgresql(conn):
        return

    # Convert columns to JSONB
    for table, column in _COLUMNS:
        conn.execute(text(
            f'ALTER TABLE {table} ALTER COLUMN {column} '
            f'TYPE JSONB USING {column}::jsonb'
        ))

    # Create GIN indexes
    for idx_name, table, column in _GIN_INDEXES:
        conn.execute(text(
            f'CREATE INDEX IF NOT EXISTS {idx_name} '
            f'ON {table} USING gin({column})'
        ))


def downgrade() -> None:
    """Retired alongside the legacy JSONB conversion."""
    return

    conn = op.get_bind()
    if not _is_postgresql(conn):
        return

    # Drop GIN indexes
    for idx_name, _, _ in reversed(_GIN_INDEXES):
        conn.execute(text(f'DROP INDEX IF EXISTS {idx_name}'))

    # Revert JSONB -> JSON
    for table, column in reversed(_COLUMNS):
        conn.execute(text(
            f'ALTER TABLE {table} ALTER COLUMN {column} '
            f'TYPE JSON USING {column}::json'
        ))
