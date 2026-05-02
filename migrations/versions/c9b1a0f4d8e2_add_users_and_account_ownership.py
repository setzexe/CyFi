"""add users and account ownership

Revision ID: c9b1a0f4d8e2
Revises: 8f2ce7e2fafd
Create Date: 2026-05-01 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c9b1a0f4d8e2'
down_revision = '8f2ce7e2fafd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_accounts_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_accounts_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.create_unique_constraint('uq_accounts_user_id_name', ['user_id', 'name'])

    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_account_history_events_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_account_history_events_user_id_users', 'users', ['user_id'], ['id'])


def downgrade():
    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.drop_constraint('fk_account_history_events_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_account_history_events_user_id'))
        batch_op.drop_column('user_id')

    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_accounts_user_id_name', type_='unique')
        batch_op.drop_constraint('fk_accounts_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_accounts_user_id'))
        batch_op.drop_column('user_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))

    op.drop_table('users')
