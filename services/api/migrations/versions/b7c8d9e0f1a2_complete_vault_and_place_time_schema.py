# Purpose: Complete vault/time coverage and validate UUID-native existing databases. Revision ID: b7c8d9e0f1a2.
"""Complete vault/time coverage and validate UUID-native existing databases.

Revision ID: b7c8d9e0f1a2
Revises: a5b6c7d8e9f0
"""
from alembic import context, op
import sqlalchemy as sa

from app.core.db.migration_checks import assert_uuid_storage

revision = 'b7c8d9e0f1a2'
down_revision = 'a5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade():
    # Offline fresh-install SQL has these objects in the frozen baseline.
    if context.is_offline_mode():
        return
    connection = op.get_bind()
    assert_uuid_storage(connection)
    inspector = sa.inspect(connection)
    if 'gp_vault_documents' not in inspector.get_table_names():
        op.create_table(
            'gp_vault_documents',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('group_id', sa.Uuid(), nullable=False),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('original_filename', sa.String(255), nullable=False),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('uploaded_by', sa.Uuid(), nullable=False),
            sa.Column('is_deleted', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['group_id'], ['travel_groups.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('idx_gp_vault_group', 'gp_vault_documents', ['group_id', 'is_deleted'])
    columns = {column['name'] for column in inspector.get_columns('gp_places')}
    if 'suggested_time' not in columns:
        op.add_column('gp_places', sa.Column('suggested_time', sa.String(10), nullable=True))


def downgrade():
    """Retain vault data: these objects also belong to the frozen baseline."""
