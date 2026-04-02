"""materialized_views_postgresql

PostgreSQL-only migration: creates two materialized views for
high-traffic read paths.

1. mv_group_balances — pre-computed net balance per (group_id, user_id).
   Replaces on-the-fly SUM queries in the expense settlement engine.
   Refreshable concurrently via: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_group_balances;

2. mv_place_rankings — pre-computed rank score + full-text search vector
   for the places search engine (travel data).
   Refreshable daily via: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_place_rankings;

On SQLite this migration is a no-op.

Revision ID: a0a12823fc65
Revises: 119b418945ce
Create Date: 2026-03-19 15:40:15.742069
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision: str = 'a0a12823fc65'
down_revision: Union[str, Sequence[str], None] = '119b418945ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql(conn: Connection) -> bool:
    return conn.dialect.name == 'postgresql'


# --------------------------------------------------------------------------
# mv_group_balances
# --------------------------------------------------------------------------
_MV_GROUP_BALANCES = """
CREATE MATERIALIZED VIEW mv_group_balances AS
SELECT
    gm.group_id,
    gm.user_id,
    COALESCE(paid.total_paid, 0)
      - COALESCE(owed.total_owed, 0)
      + COALESCE(received.total_received, 0)
      - COALESCE(sent.total_sent, 0) AS net_balance
FROM group_members gm
LEFT JOIN (
    SELECT group_id, paid_by AS user_id, SUM(amount) AS total_paid
    FROM expenses
    WHERE is_deleted = false
    GROUP BY group_id, paid_by
) paid ON gm.group_id = paid.group_id AND gm.user_id = paid.user_id
LEFT JOIN (
    SELECT e.group_id, es.user_id, SUM(es.amount) AS total_owed
    FROM expense_splits es
    JOIN expenses e ON es.expense_id = e.id
    WHERE e.is_deleted = false
    GROUP BY e.group_id, es.user_id
) owed ON gm.group_id = owed.group_id AND gm.user_id = owed.user_id
LEFT JOIN (
    SELECT group_id, to_user_id AS user_id, SUM(amount) AS total_received
    FROM settlements
    GROUP BY group_id, to_user_id
) received ON gm.group_id = received.group_id AND gm.user_id = received.user_id
LEFT JOIN (
    SELECT group_id, from_user_id AS user_id, SUM(amount) AS total_sent
    FROM settlements
    GROUP BY group_id, from_user_id
) sent ON gm.group_id = sent.group_id AND gm.user_id = sent.user_id
WHERE gm.is_active = true
WITH NO DATA
"""

_MV_GROUP_BALANCES_IDX = """
CREATE UNIQUE INDEX idx_mv_balances_pk
    ON mv_group_balances (group_id, user_id)
"""


# --------------------------------------------------------------------------
# mv_place_rankings
# --------------------------------------------------------------------------
_MV_PLACE_RANKINGS = """
CREATE MATERIALIZED VIEW mv_place_rankings AS
SELECT
    p.id,
    p.name,
    p.category,
    p.rating,
    p.latitude,
    p.longitude,
    c.name  AS city_name,
    s.name  AS state_name,
    co.name AS country_name,
    (COALESCE(p.rating, 0) * 2
     + COALESCE(p.user_ratings_total, 0) * 0.01) AS rank_score,
    to_tsvector(
        'english',
        p.name || ' '
        || COALESCE(p.category, '') || ' '
        || COALESCE(c.name, '') || ' '
        || COALESCE(s.name, '')
    ) AS fts_vector
FROM places p
JOIN cities c    ON p.city_id = c.id
JOIN states s    ON c.state_id = s.id
JOIN countries co ON s.country_id = co.id
WITH NO DATA
"""

_MV_PLACE_RANKINGS_INDEXES = [
    'CREATE INDEX idx_mv_rankings_fts   ON mv_place_rankings USING gin(fts_vector)',
    'CREATE INDEX idx_mv_rankings_score ON mv_place_rankings (rank_score DESC)',
    'CREATE INDEX idx_mv_rankings_geo   ON mv_place_rankings (latitude, longitude)',
]


def upgrade() -> None:
    conn = op.get_bind()
    if not _is_postgresql(conn):
        return

    # 1. Group balances
    conn.execute(text(_MV_GROUP_BALANCES))
    conn.execute(text(_MV_GROUP_BALANCES_IDX))

    # 2. Place rankings (only if travel data tables exist in same DB)
    result = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'places'"
        ")"
    ))
    places_exist = result.scalar()

    if places_exist:
        conn.execute(text(_MV_PLACE_RANKINGS))
        for idx_sql in _MV_PLACE_RANKINGS_INDEXES:
            conn.execute(text(idx_sql))


def downgrade() -> None:
    conn = op.get_bind()
    if not _is_postgresql(conn):
        return

    conn.execute(text('DROP MATERIALIZED VIEW IF EXISTS mv_place_rankings CASCADE'))
    conn.execute(text('DROP MATERIALIZED VIEW IF EXISTS mv_group_balances CASCADE'))
