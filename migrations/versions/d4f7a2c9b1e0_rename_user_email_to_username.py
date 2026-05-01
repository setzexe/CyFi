"""rename user email to username

Revision ID: d4f7a2c9b1e0
Revises: c9b1a0f4d8e2
Create Date: 2026-05-01 11:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f7a2c9b1e0'
down_revision = 'c9b1a0f4d8e2'
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    has_email = _has_column('users', 'email')
    has_username = _has_column('users', 'username')

    if has_email and not has_username:
        if _has_index('users', 'ix_users_email'):
            op.drop_index('ix_users_email', table_name='users')

        if bind.dialect.name == 'sqlite':
            op.execute('ALTER TABLE users RENAME COLUMN email TO username')
            if not _has_index('users', 'ix_users_username'):
                op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
        else:
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.alter_column(
                    'email',
                    new_column_name='username',
                    existing_type=sa.String(length=255),
                    existing_nullable=False,
                )
                batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)


def downgrade():
    bind = op.get_bind()
    has_email = _has_column('users', 'email')
    has_username = _has_column('users', 'username')

    if has_username and not has_email:
        if _has_index('users', 'ix_users_username'):
            op.drop_index('ix_users_username', table_name='users')

        if bind.dialect.name == 'sqlite':
            op.execute('ALTER TABLE users RENAME COLUMN username TO email')
            if not _has_index('users', 'ix_users_email'):
                op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        else:
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.alter_column(
                    'username',
                    new_column_name='email',
                    existing_type=sa.String(length=80),
                    existing_nullable=False,
                )
                batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
