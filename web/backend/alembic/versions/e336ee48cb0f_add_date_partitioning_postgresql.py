"""add_date_partitioning_postgresql

PostgreSQL-only migration: converts expenses, expense_history, and
gp_group_activities to range-partitioned tables by month.

On SQLite this migration is a no-op (partitioning is not supported).

Revision ID: e336ee48cb0f
Revises: 60621bfec6f2
Create Date: 2026-03-19 15:35:39.555138
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision: str = 'e336ee48cb0f'
down_revision: Union[str, Sequence[str], None] = '60621bfec6f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql(conn: Connection) -> bool:
    return conn.dialect.name == 'postgresql'


# ---- Partition helpers ---------------------------------------------------

_PARTITION_SQL = """
-- 1. Rename original table
ALTER TABLE {table} RENAME TO {table}_old;

-- 2. Create partitioned table with same schema
CREATE TABLE {table} (LIKE {table}_old INCLUDING ALL)
    PARTITION BY RANGE ({partition_col});

-- 3. Create default partition (catches all rows outside defined ranges)
CREATE TABLE {table}_default PARTITION OF {table} DEFAULT;

-- 4. Create monthly partitions for 2026
{monthly_ddl}

-- 5. Copy data from old table
INSERT INTO {table} SELECT * FROM {table}_old;

-- 6. Drop old table
DROP TABLE {table}_old CASCADE;
"""

_UNPARTITION_SQL = """
-- Reverse: collapse partitioned table back to a regular table
CREATE TABLE {table}_flat (LIKE {table} INCLUDING ALL);
INSERT INTO {table}_flat SELECT * FROM {table};
DROP TABLE {table} CASCADE;
ALTER TABLE {table}_flat RENAME TO {table};
"""


def _monthly_partitions(table: str, col: str, year: int = 2026) -> str:
    """Generate CREATE TABLE ... PARTITION OF statements for each month."""
    lines = []
    for m in range(1, 13):
        start = f'{year}-{m:02d}-01'
        if m < 12:
            end = f'{year}-{m + 1:02d}-01'
        else:
            end = f'{year + 1}-01-01'
        name = f'{table}_{year}_{m:02d}'
        lines.append(
            f"CREATE TABLE {name} PARTITION OF {table} "
            f"FOR VALUES FROM ('{start}') TO ('{end}');"
        )
    return '\n'.join(lines)


# ---- Tables to partition -------------------------------------------------

_TABLES = [
    ('expenses',            'expense_date'),
    ('expense_history',     'created_at'),
    ('gp_group_activities', 'created_at'),
]


def upgrade() -> None:
    conn = op.get_bind()
    if not _is_postgresql(conn):
        # SQLite: partitioning not supported — skip silently
        return

    for table, col in _TABLES:
        monthly_ddl = _monthly_partitions(table, col)
        sql = _PARTITION_SQL.format(
            table=table,
            partition_col=col,
            monthly_ddl=monthly_ddl,
        )
        for statement in sql.split(';'):
            stmt = statement.strip()
            if stmt and not stmt.startswith('--'):
                conn.execute(text(stmt))


def downgrade() -> None:
    conn = op.get_bind()
    if not _is_postgresql(conn):
        return

    for table, _ in reversed(_TABLES):
        sql = _UNPARTITION_SQL.format(table=table)
        for statement in sql.split(';'):
            stmt = statement.strip()
            if stmt and not stmt.startswith('--'):
                conn.execute(text(stmt))
