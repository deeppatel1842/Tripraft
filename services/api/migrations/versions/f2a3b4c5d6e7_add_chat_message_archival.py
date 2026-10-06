# Purpose: Add reversible archival support for group chat messages. Revision ID: f2a3b4c5d6e7.
"""Add reversible archival support for group chat messages.

Revision ID: f2a3b4c5d6e7
Revises: d4a1c3e8f9b0
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'd4a1c3e8f9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a persisted, reversible archive marker for chat retention."""
    if context.is_offline_mode():
        return
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('gp_chat_messages')}
    if 'is_archived' in columns:
        return
    with op.batch_alter_table('gp_chat_messages') as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_archived',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_index('idx_chat_messages_group_id', table_name='gp_chat_messages')
        op.create_index(
            'idx_chat_messages_group_id', 'gp_chat_messages', ['group_id', 'id'],
            postgresql_where=sa.text('NOT is_deleted AND NOT is_archived'),
        )


def downgrade() -> None:
    """Remove the archive marker when rolling the migration back."""
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_index('idx_chat_messages_group_id', table_name='gp_chat_messages')
        op.create_index(
            'idx_chat_messages_group_id', 'gp_chat_messages', ['group_id', 'id'],
            postgresql_where=sa.text('NOT is_deleted'),
        )
    with op.batch_alter_table('gp_chat_messages') as batch_op:
        batch_op.drop_column('is_archived')
