"""add_chat_tables

Revision ID: c4d5e6f7a8b9
Revises: e80825488cb5
Create Date: 2026-03-21 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'e80825488cb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres():
    return op.get_bind().dialect.name == 'postgresql'


def upgrade() -> None:
    json_type = sa.dialects.postgresql.JSONB() if _is_postgres() else sa.JSON()

    op.create_table(
        'gp_chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('sender_type', sa.String(length=10), nullable=False, server_default='user'),
        sa.Column('type', sa.String(length=30), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', json_type, nullable=True),
        sa.Column('parent_message_id', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['gp_chat_messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    if _is_postgres():
        op.create_index(
            'idx_chat_messages_group_id',
            'gp_chat_messages',
            ['group_id', sa.text('id DESC')],
            postgresql_where=sa.text('NOT is_deleted'),
        )
        op.create_index(
            'idx_chat_messages_sender',
            'gp_chat_messages',
            ['sender_id'],
            postgresql_where=sa.text('sender_id IS NOT NULL'),
        )
    else:
        op.create_index('idx_chat_messages_group_id', 'gp_chat_messages', ['group_id', 'id'])
        op.create_index('idx_chat_messages_sender', 'gp_chat_messages', ['sender_id'])

    op.create_table(
        'gp_chat_summaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('from_message_id', sa.Integer(), nullable=False),
        sa.Column('to_message_id', sa.Integer(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('topic_tags', json_type, nullable=True),
        sa.Column('metadata', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chat_summaries_group', 'gp_chat_summaries', ['group_id', 'created_at'])

    op.create_table(
        'gp_message_reads',
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('last_read_message_id', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('group_id', 'user_id'),
    )
    op.create_index('idx_message_reads_user', 'gp_message_reads', ['user_id'])


def downgrade() -> None:
    op.drop_table('gp_message_reads')
    op.drop_table('gp_chat_summaries')
    op.drop_table('gp_chat_messages')
