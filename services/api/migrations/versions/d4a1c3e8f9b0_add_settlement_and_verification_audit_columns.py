# Purpose: Persist settlement deletion and email-verification audit timestamps. Revision ID: d4a1c3e8f9b0.
"""Persist settlement deletion and email-verification audit timestamps.

Revision ID: d4a1c3e8f9b0
Revises: 83f1d84d08e4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op


revision: str = 'd4a1c3e8f9b0'
down_revision: Union[str, Sequence[str], None] = '83f1d84d08e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    """Return existing columns so this is safe with repaired fresh baselines."""
    return {column['name'] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if context.is_offline_mode():
        return
    settlement_columns = _columns('settlements')
    if 'deleted_at' not in settlement_columns or 'deleted_by' not in settlement_columns:
        # Batch mode keeps the migration portable to SQLite, whose ALTER TABLE
        # support cannot add a foreign-key constraint in place.
        with op.batch_alter_table('settlements') as batch_op:
            if 'deleted_at' not in settlement_columns:
                batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
            if 'deleted_by' not in settlement_columns:
                batch_op.add_column(
                    sa.Column('deleted_by', sa.Uuid(), nullable=True)
                )
                batch_op.create_foreign_key(
                    'fk_settlements_deleted_by_user', 'users', ['deleted_by'], ['id'],
                )

    if 'email_verified_at' not in _columns('users'):
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    settlement_columns = _columns('settlements')
    if 'deleted_at' in settlement_columns or 'deleted_by' in settlement_columns:
        with op.batch_alter_table('settlements') as batch_op:
            if 'deleted_by' in settlement_columns:
                batch_op.drop_column('deleted_by')
            if 'deleted_at' in settlement_columns:
                batch_op.drop_column('deleted_at')

    if 'email_verified_at' in _columns('users'):
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('email_verified_at')
