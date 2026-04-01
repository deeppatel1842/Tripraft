"""add_missing_composite_indexes

Revision ID: 60621bfec6f2
Revises: 75118e6ab634
Create Date: 2026-03-19 15:28:24.348817

Adds indexes identified in the Phase 1 audit:
- Session expiry for cleanup queries
- Settlement chronological ordering
- Expense history for audit trail queries
- gp_places geo for map-based proximity queries
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '60621bfec6f2'
down_revision: Union[str, Sequence[str], None] = '75118e6ab634'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes for query performance."""
    # Use raw SQL with IF NOT EXISTS for idempotent index creation
    # (safe to re-run if migration was partially applied)
    conn = op.get_bind()

    # Session cleanup: DELETE FROM user_sessions WHERE expires_at < NOW()
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_sessions_expires '
        'ON user_sessions (expires_at)'
    ))

    # Settlement history: WHERE group_id = ? ORDER BY settlement_date DESC
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_settlements_group_date '
        'ON settlements (group_id, settlement_date)'
    ))

    # Audit trail: WHERE expense_id = ? ORDER BY created_at DESC
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_expense_history_expense '
        'ON expense_history (expense_id, created_at)'
    ))

    # User audit trail: WHERE changed_by = ? ORDER BY created_at DESC
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_expense_history_user '
        'ON expense_history (changed_by, created_at)'
    ))

    # Map proximity: ORDER BY latitude, longitude
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_gp_places_geo '
        'ON gp_places (latitude, longitude)'
    ))

    # Recent expenses by payer: WHERE paid_by = ? ORDER BY created_at DESC
    conn.execute(sa.text(
        'CREATE INDEX IF NOT EXISTS idx_expenses_paid_by_date '
        'ON expenses (paid_by, created_at)'
    ))


def downgrade() -> None:
    """Remove composite indexes."""
    with op.batch_alter_table('expenses') as batch_op:
        batch_op.drop_index('idx_expenses_paid_by_date')

    with op.batch_alter_table('gp_places') as batch_op:
        batch_op.drop_index('idx_gp_places_geo')

    with op.batch_alter_table('expense_history') as batch_op:
        batch_op.drop_index('idx_expense_history_user')
        batch_op.drop_index('idx_expense_history_expense')

    with op.batch_alter_table('settlements') as batch_op:
        batch_op.drop_index('idx_settlements_group_date')

    with op.batch_alter_table('user_sessions') as batch_op:
        batch_op.drop_index('idx_sessions_expires')
