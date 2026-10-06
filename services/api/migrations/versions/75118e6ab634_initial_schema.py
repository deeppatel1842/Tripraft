# Purpose: Frozen UUID-native application schema (2026-10-02). Revision ID: 75118e6ab634.
"""Frozen UUID-native application schema (2026-10-02).

Revision ID: 75118e6ab634
Revises:

This revision is independent of application models. Future schema changes
belong in new revisions; never regenerate this snapshot after deployment.
"""
from alembic import op
import sqlalchemy as sa

revision = '75118e6ab634'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ai_agent_logs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('agent', sa.String(length=10), nullable=False),
    sa.Column('intent', sa.String(length=30), nullable=False),
    sa.Column('query_text', sa.Text(), nullable=False),
    sa.Column('response_summary', sa.String(length=500), nullable=True),
    sa.Column('tokens_used', sa.Integer(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('cache_hit', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_logs_agent', 'ai_agent_logs', ['agent', 'created_at'], unique=False)
    op.create_index('idx_agent_logs_group', 'ai_agent_logs', ['group_id', 'created_at'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=100), nullable=True),
    sa.Column('photo_url', sa.Text(), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('default_currency', sa.String(length=3), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('email_verified', sa.Boolean(), nullable=True),
    sa.Column('email_verified_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('audit_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('resource_type', sa.String(length=50), nullable=False),
    sa.Column('resource_id', sa.Uuid(), nullable=True),
    sa.Column('old_data', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_action', 'audit_log', ['action', 'created_at'], unique=False)
    op.create_index('idx_audit_resource', 'audit_log', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_audit_user_time', 'audit_log', ['user_id', 'created_at'], unique=False)
    op.create_table('groups',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('group_code', sa.String(length=20), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('image_url', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_code')
    )
    op.create_table('travel_groups',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('destination', sa.String(length=255), nullable=True),
    sa.Column('destination_lat', sa.Float(), nullable=True),
    sa.Column('destination_lng', sa.Float(), nullable=True),
    sa.Column('destination_type', sa.String(length=20), nullable=True),
    sa.Column('destination_id', sa.String(length=50), nullable=True),
    sa.Column('group_code', sa.String(length=20), nullable=True),
    sa.Column('group_image', sa.Text(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('estimated_budget', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('budget_currency', sa.String(length=3), nullable=True),
    sa.Column('expense_group_id', sa.Uuid(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_travel_groups_created_by', 'travel_groups', ['created_by', 'is_active'], unique=False)
    op.create_index(op.f('ix_travel_groups_group_code'), 'travel_groups', ['group_code'], unique=True)
    op.create_table('user_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('refresh_token', sa.String(length=500), nullable=False),
    sa.Column('device_info', sa.Text(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_used', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_expires', 'user_sessions', ['expires_at'], unique=False)
    op.create_index('idx_user_sessions_token', 'user_sessions', ['refresh_token'], unique=False)
    op.create_index('idx_user_sessions_user', 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_refresh_token'), 'user_sessions', ['refresh_token'], unique=False)
    op.create_table('ai_consent',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('consent_type', sa.String(length=30), nullable=False),
    sa.Column('granted', sa.Boolean(), nullable=False),
    sa.Column('consent_version', sa.String(length=10), nullable=False),
    sa.Column('jurisdiction', sa.String(length=10), nullable=False),
    sa.Column('notice_shown_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=False),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'user_id', 'consent_type', name='uq_ai_consent_group_user_type')
    )
    op.create_index('idx_ai_consent_group', 'ai_consent', ['group_id'], unique=False, postgresql_where='granted = TRUE')
    op.create_index('idx_ai_consent_user', 'ai_consent', ['user_id'], unique=False)
    op.create_table('ai_preference_profiles',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('preference_key', sa.String(length=50), nullable=False),
    sa.Column('preference_value', sa.String(length=200), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'user_id', 'preference_key', name='uq_ai_prefs_group_user_key')
    )
    op.create_index('idx_ai_prefs_group', 'ai_preference_profiles', ['group_id'], unique=False)
    op.create_index('idx_ai_prefs_user', 'ai_preference_profiles', ['user_id'], unique=False)
    op.create_table('expenses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('paid_by', sa.Uuid(), nullable=False),
    sa.Column('split_type', sa.String(length=20), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('expense_date', sa.Date(), nullable=True),
    sa.Column('receipt_url', sa.Text(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['paid_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_expenses_group', 'expenses', ['group_id', 'is_deleted', 'expense_date'], unique=False)
    op.create_index('idx_expenses_paid_by', 'expenses', ['paid_by'], unique=False)
    op.create_index('idx_expenses_paid_by_date', 'expenses', ['paid_by', 'created_at'], unique=False)
    op.create_table('gp_chat_messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('sender_id', sa.Uuid(), nullable=True),
    sa.Column('sender_type', sa.String(length=10), nullable=False),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=True),
    sa.Column('parent_message_id', sa.Uuid(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('is_archived', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_message_id'], ['gp_chat_messages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_group_id', 'gp_chat_messages', ['group_id', 'id'], unique=False, postgresql_where='NOT is_deleted AND NOT is_archived')
    op.create_index('idx_chat_messages_sender', 'gp_chat_messages', ['sender_id'], unique=False, postgresql_where='sender_id IS NOT NULL')
    op.create_table('gp_checklist_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('item', sa.String(length=500), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=True),
    sa.Column('completed_by', sa.Uuid(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('priority', sa.String(length=10), server_default='medium', nullable=False),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('assigned_to_id', sa.Uuid(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], name='fk_gp_checklist_items_assigned_to_user', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['completed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_checklist_completed', 'gp_checklist_items', ['completed', 'group_id'], unique=False)
    op.create_index('idx_gp_checklist_group', 'gp_checklist_items', ['group_id', 'is_deleted'], unique=False)
    op.create_table('gp_group_activities',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=True),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_activities_group', 'gp_group_activities', ['group_id', 'created_at'], unique=False)
    op.create_table('gp_group_members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('joined_at', sa.DateTime(), nullable=True),
    sa.Column('removed_at', sa.DateTime(), nullable=True),
    sa.Column('removed_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['removed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'user_id', name='uq_gp_group_member')
    )
    op.create_index('idx_gp_group_members_group', 'gp_group_members', ['group_id', 'is_active'], unique=False)
    op.create_index('idx_gp_group_members_user', 'gp_group_members', ['user_id', 'is_active'], unique=False)
    op.create_table('gp_invitations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('invitee_email', sa.String(length=255), nullable=False),
    sa.Column('invitee_user_id', sa.Uuid(), nullable=True),
    sa.Column('invited_by', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('responded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['invitee_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'invitee_email', name='uq_gp_invitation')
    )
    op.create_index('idx_gp_invitations_email', 'gp_invitations', ['invitee_email', 'status'], unique=False)
    op.create_index('idx_gp_invitations_group', 'gp_invitations', ['group_id', 'status'], unique=False)
    op.create_table('gp_itinerary_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('last_edited_by', sa.Uuid(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['last_edited_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id')
    )
    op.create_table('gp_notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=True),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_notifications_user', 'gp_notifications', ['user_id', 'is_read', 'created_at'], unique=False)
    op.create_table('gp_places',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('visit_date', sa.Date(), nullable=True),
    sa.Column('suggested_time', sa.String(length=10), nullable=True),
    sa.Column('suggested_duration', sa.String(length=50), nullable=True),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('photo_url', sa.Text(), nullable=True),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('rating', sa.Float(), nullable=True),
    sa.Column('added_by', sa.Uuid(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['added_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_places_category', 'gp_places', ['category', 'group_id'], unique=False)
    op.create_index('idx_gp_places_geo', 'gp_places', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_gp_places_group', 'gp_places', ['group_id', 'is_deleted'], unique=False)
    op.create_index('idx_gp_places_visit_date', 'gp_places', ['visit_date', 'group_id'], unique=False)
    op.create_table('gp_polls',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('options', sa.JSON(), nullable=False),
    sa.Column('is_multiple_choice', sa.Boolean(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_polls_group', 'gp_polls', ['group_id', 'is_deleted'], unique=False)
    op.create_table('gp_vault_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.Uuid(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gp_vault_group', 'gp_vault_documents', ['group_id', 'is_deleted'], unique=False)
    op.create_table('group_balances',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'user_id', name='uq_group_balance')
    )
    op.create_index('idx_balances_group', 'group_balances', ['group_id'], unique=False)
    op.create_index('idx_balances_user', 'group_balances', ['user_id'], unique=False)
    op.create_table('group_members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('joined_at', sa.DateTime(), nullable=True),
    sa.Column('removed_at', sa.DateTime(), nullable=True),
    sa.Column('removed_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['removed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'user_id', name='uq_group_member')
    )
    op.create_index('idx_group_members_group', 'group_members', ['group_id', 'is_active'], unique=False)
    op.create_index('idx_group_members_user', 'group_members', ['user_id', 'is_active'], unique=False)
    op.create_table('invitations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('invitee_email', sa.String(length=255), nullable=False),
    sa.Column('invitee_user_id', sa.Uuid(), nullable=True),
    sa.Column('invited_by', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('responded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['invitee_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'invitee_email', name='uq_invitation')
    )
    op.create_index('idx_invitations_email', 'invitations', ['invitee_email', 'status'], unique=False)
    op.create_index('idx_invitations_group', 'invitations', ['group_id', 'status'], unique=False)
    op.create_table('settlements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('from_user_id', sa.Uuid(), nullable=False),
    sa.Column('to_user_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('method', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('proof_url', sa.Text(), nullable=True),
    sa.Column('recorded_by', sa.Uuid(), nullable=False),
    sa.Column('settlement_date', sa.Date(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_settlements_deleted_by_user'),
    sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_settlements_group', 'settlements', ['group_id', 'is_deleted'], unique=False)
    op.create_index('idx_settlements_group_date', 'settlements', ['group_id', 'settlement_date'], unique=False)
    op.create_index('idx_settlements_users', 'settlements', ['from_user_id', 'to_user_id'], unique=False)
    op.create_table('expense_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('expense_id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=20), nullable=False),
    sa.Column('changed_by', sa.Uuid(), nullable=False),
    sa.Column('changes_json', sa.JSON(), nullable=True),
    sa.Column('before_snapshot', sa.JSON(), nullable=True),
    sa.Column('after_snapshot', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_expense_history_expense', 'expense_history', ['expense_id', 'created_at'], unique=False)
    op.create_index('idx_expense_history_user', 'expense_history', ['changed_by', 'created_at'], unique=False)
    op.create_table('expense_splits',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('expense_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('shares', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('expense_id', 'user_id', name='uq_expense_split')
    )
    op.create_index('idx_expense_splits_user', 'expense_splits', ['user_id'], unique=False)
    op.create_table('gp_chat_summaries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('from_message_id', sa.Uuid(), nullable=False),
    sa.Column('to_message_id', sa.Uuid(), nullable=False),
    sa.Column('summary_text', sa.Text(), nullable=False),
    sa.Column('topic_tags', sa.JSON(), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['from_message_id'], ['gp_chat_messages.id'], name='fk_gp_chat_summaries_from_message', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_message_id'], ['gp_chat_messages.id'], name='fk_gp_chat_summaries_to_message', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_summaries_group', 'gp_chat_summaries', ['group_id', 'created_at'], unique=False)
    op.create_table('gp_message_reads',
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('last_read_message_id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['last_read_message_id'], ['gp_chat_messages.id'], name='fk_gp_message_reads_last_read_message', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('group_id', 'user_id')
    )
    op.create_index('idx_message_reads_user', 'gp_message_reads', ['user_id'], unique=False)
    op.create_table('gp_place_votes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('place_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['place_id'], ['gp_places.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('place_id', 'user_id', name='uq_gp_place_vote')
    )
    op.create_table('gp_poll_votes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('poll_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('option', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['poll_id'], ['gp_polls.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('poll_id', 'user_id', 'option', name='uq_gp_poll_vote')
    )
    op.create_index('idx_gp_poll_votes', 'gp_poll_votes', ['poll_id', 'user_id'], unique=False)


def downgrade():
    op.drop_table('gp_poll_votes')
    op.drop_table('gp_place_votes')
    op.drop_table('gp_message_reads')
    op.drop_table('gp_chat_summaries')
    op.drop_table('expense_splits')
    op.drop_table('expense_history')
    op.drop_table('settlements')
    op.drop_table('invitations')
    op.drop_table('group_members')
    op.drop_table('group_balances')
    op.drop_table('gp_vault_documents')
    op.drop_table('gp_polls')
    op.drop_table('gp_places')
    op.drop_table('gp_notifications')
    op.drop_table('gp_itinerary_documents')
    op.drop_table('gp_invitations')
    op.drop_table('gp_group_members')
    op.drop_table('gp_group_activities')
    op.drop_table('gp_checklist_items')
    op.drop_table('gp_chat_messages')
    op.drop_table('expenses')
    op.drop_table('ai_preference_profiles')
    op.drop_table('ai_consent')
    op.drop_table('user_sessions')
    op.drop_table('travel_groups')
    op.drop_table('groups')
    op.drop_table('audit_log')
    op.drop_table('users')
    op.drop_table('ai_agent_logs')
