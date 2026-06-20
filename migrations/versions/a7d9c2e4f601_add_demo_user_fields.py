"""add demo user fields

Revision ID: a7d9c2e4f601
Revises: f95bcc39e9f7
Create Date: 2026-06-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7d9c2e4f601'
down_revision = 'f95bcc39e9f7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('demo_expires_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_demo_expires_at'), ['demo_expires_at'], unique=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_demo_expires_at'))
        batch_op.drop_index(batch_op.f('ix_users_is_demo'))
        batch_op.drop_column('demo_expires_at')
        batch_op.drop_column('is_demo')
