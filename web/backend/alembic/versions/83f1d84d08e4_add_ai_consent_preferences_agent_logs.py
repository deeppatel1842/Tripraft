"""add_ai_consent_preferences_agent_logs

Revision ID: 83f1d84d08e4
Revises: 74866d910457
Create Date: 2026-03-30 13:29:14.488445

Phase 31 — AI Guide Agent (@scout)
Creates tables for consent management, preference profiles, and agent audit logs.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '83f1d84d08e4'
down_revision: Union[str, Sequence[str], None] = '74866d910457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI consent, preference profiles, and agent logs tables."""

    # -- ai_consent --
    op.create_table(
        'ai_consent',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('consent_type', sa.String(30), nullable=False, server_default='chat_history_read'),
        sa.Column('granted', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('consent_version', sa.String(10), nullable=False, server_default='1.0'),
        sa.Column('jurisdiction', sa.String(10), nullable=False, server_default='GDPR'),
        sa.Column('notice_shown_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('group_id', 'user_id', 'consent_type', name='uq_ai_consent_group_user_type'),
    )
    op.create_index('idx_ai_consent_group', 'ai_consent', ['group_id'])
    op.create_index('idx_ai_consent_user', 'ai_consent', ['user_id'])

    # -- ai_preference_profiles --
    op.create_table(
        'ai_preference_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('preference_key', sa.String(50), nullable=False),
        sa.Column('preference_value', sa.String(200), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('group_id', 'user_id', 'preference_key', name='uq_ai_prefs_group_user_key'),
    )
    op.create_index('idx_ai_prefs_group', 'ai_preference_profiles', ['group_id'])
    op.create_index('idx_ai_prefs_user', 'ai_preference_profiles', ['user_id'])

    # -- ai_agent_logs --
    op.create_table(
        'ai_agent_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('agent', sa.String(10), nullable=False),
        sa.Column('intent', sa.String(30), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_summary', sa.String(500), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_agent_logs_group', 'ai_agent_logs', ['group_id', 'created_at'])
    op.create_index('idx_agent_logs_agent', 'ai_agent_logs', ['agent', 'created_at'])


def downgrade() -> None:
    """Drop AI agent tables."""
    op.drop_table('ai_agent_logs')
    op.drop_table('ai_preference_profiles')
    op.drop_table('ai_consent')
