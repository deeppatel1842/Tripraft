"""add_audit_log_table

Revision ID: e80825488cb5
Revises: a0a12823fc65
Create Date: 2026-03-19 15:48:41.526412

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e80825488cb5'
down_revision: Union[str, Sequence[str], None] = 'a0a12823fc65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('resource_type', sa.String(length=50), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=True),
    sa.Column('old_data', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('idx_audit_action', ['action', 'created_at'], unique=False)
        batch_op.create_index('idx_audit_resource', ['resource_type', 'resource_id'], unique=False)
        batch_op.create_index('idx_audit_user_time', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('idx_audit_user_time')
        batch_op.drop_index('idx_audit_resource')
        batch_op.drop_index('idx_audit_action')

    op.drop_table('audit_log')
