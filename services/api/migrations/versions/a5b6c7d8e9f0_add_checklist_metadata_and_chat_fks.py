# Purpose: Persist checklist metadata and protect chat message references. Revision ID: a5b6c7d8e9f0.
"""Persist checklist metadata and protect chat message references.

Revision ID: a5b6c7d8e9f0
Revises: f2a3b4c5d6e7
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _require_no_orphans(table: str, column: str) -> None:
    """Fail safely instead of silently deleting historic referential data."""
    count = op.get_bind().execute(sa.text(
        f'SELECT COUNT(*) FROM {table} AS child '
        f'LEFT JOIN gp_chat_messages AS parent ON parent.id = child.{column} '
        f'WHERE parent.id IS NULL'
    )).scalar_one()
    if count:
        raise RuntimeError(
            f'Cannot add {table}.{column} foreign key: {count} orphaned rows exist. '
            'Repair or archive those records explicitly, then re-run the migration.'
        )


def upgrade() -> None:
    """Add persisted checklist fields and cascade-safe chat foreign keys."""
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('gp_checklist_items')}
    def has_fk(table, column, parent):
        return any(
            fk['constrained_columns'] == [column] and fk['referred_table'] == parent
            for fk in inspector.get_foreign_keys(table)
        )
    with op.batch_alter_table('gp_checklist_items') as batch_op:
        if 'category' not in columns:
            batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=True))
        if 'priority' not in columns:
            batch_op.add_column(sa.Column('priority', sa.String(length=10), nullable=False, server_default='medium'))
        if 'due_date' not in columns:
            batch_op.add_column(sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
        if 'assigned_to_id' not in columns:
            batch_op.add_column(sa.Column('assigned_to_id', sa.Uuid(), nullable=True))
        if not has_fk('gp_checklist_items', 'assigned_to_id', 'users'):
            batch_op.create_foreign_key(
                'fk_gp_checklist_items_assigned_to_user', 'users', ['assigned_to_id'], ['id'],
                ondelete='SET NULL',
            )

    _require_no_orphans('gp_chat_summaries', 'from_message_id')
    _require_no_orphans('gp_chat_summaries', 'to_message_id')
    _require_no_orphans('gp_message_reads', 'last_read_message_id')

    with op.batch_alter_table('gp_chat_summaries') as batch_op:
        if not has_fk('gp_chat_summaries', 'from_message_id', 'gp_chat_messages'):
            batch_op.create_foreign_key(
                'fk_gp_chat_summaries_from_message', 'gp_chat_messages',
                ['from_message_id'], ['id'], ondelete='CASCADE',
            )
        if not has_fk('gp_chat_summaries', 'to_message_id', 'gp_chat_messages'):
            batch_op.create_foreign_key(
                'fk_gp_chat_summaries_to_message', 'gp_chat_messages',
                ['to_message_id'], ['id'], ondelete='CASCADE',
            )
    with op.batch_alter_table('gp_message_reads') as batch_op:
        if not has_fk('gp_message_reads', 'last_read_message_id', 'gp_chat_messages'):
            batch_op.create_foreign_key(
                'fk_gp_message_reads_last_read_message', 'gp_chat_messages',
                ['last_read_message_id'], ['id'], ondelete='CASCADE',
            )


def downgrade() -> None:
    """Remove the P3 metadata and referential protections."""
    with op.batch_alter_table('gp_message_reads') as batch_op:
        batch_op.drop_constraint('fk_gp_message_reads_last_read_message', type_='foreignkey')
    with op.batch_alter_table('gp_chat_summaries') as batch_op:
        batch_op.drop_constraint('fk_gp_chat_summaries_to_message', type_='foreignkey')
        batch_op.drop_constraint('fk_gp_chat_summaries_from_message', type_='foreignkey')
    with op.batch_alter_table('gp_checklist_items') as batch_op:
        batch_op.drop_constraint('fk_gp_checklist_items_assigned_to_user', type_='foreignkey')
        batch_op.drop_column('assigned_to_id')
        batch_op.drop_column('due_date')
        batch_op.drop_column('priority')
        batch_op.drop_column('category')
