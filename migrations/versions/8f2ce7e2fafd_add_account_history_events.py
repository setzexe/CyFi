"""add account history events

Revision ID: 8f2ce7e2fafd
Revises: 115b82820802
Create Date: 2026-04-15 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f2ce7e2fafd'
down_revision = '115b82820802'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'account_history_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('account_name', sa.String(length=80), nullable=False),
        sa.Column('account_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_account_history_events_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_account_history_events_created_at'))

    op.drop_table('account_history_events')
