"""standardize text field lengths

Revision ID: 6a4f5d7b9c21
Revises: d4f7a2c9b1e0
Create Date: 2026-05-02 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '6a4f5d7b9c21'
down_revision = 'd4f7a2c9b1e0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(length=80), type_=sa.String(length=50), nullable=False)

    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.alter_column('account_name', existing_type=sa.String(length=80), type_=sa.String(length=50), nullable=False)

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column(
            'transaction_name',
            existing_type=sa.String(length=120),
            type_=sa.String(length=50),
            existing_server_default='Transaction',
            nullable=False,
        )
        batch_op.alter_column('category', existing_type=sa.String(length=60), type_=sa.String(length=25), nullable=False)

    with op.batch_alter_table('recurring_bills', schema=None) as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(length=120), type_=sa.String(length=50), nullable=False)
        batch_op.alter_column('category', existing_type=sa.String(length=60), type_=sa.String(length=25), nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('username', existing_type=sa.String(length=80), type_=sa.String(length=30), nullable=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('username', existing_type=sa.String(length=30), type_=sa.String(length=80), nullable=False)

    with op.batch_alter_table('recurring_bills', schema=None) as batch_op:
        batch_op.alter_column('category', existing_type=sa.String(length=25), type_=sa.String(length=60), nullable=False)
        batch_op.alter_column('name', existing_type=sa.String(length=50), type_=sa.String(length=120), nullable=False)

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column('category', existing_type=sa.String(length=25), type_=sa.String(length=60), nullable=False)
        batch_op.alter_column(
            'transaction_name',
            existing_type=sa.String(length=50),
            type_=sa.String(length=120),
            existing_server_default='Transaction',
            nullable=False,
        )

    with op.batch_alter_table('account_history_events', schema=None) as batch_op:
        batch_op.alter_column('account_name', existing_type=sa.String(length=50), type_=sa.String(length=80), nullable=False)

    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(length=50), type_=sa.String(length=80), nullable=False)
