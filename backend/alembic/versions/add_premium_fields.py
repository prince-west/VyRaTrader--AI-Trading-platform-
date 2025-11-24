"""add premium fields to users

Revision ID: add_premium_fields
Revises: aa053d676dcc
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_premium_fields'
down_revision = 'aa053d676dcc'  # Previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if users table exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'users' not in tables:
        # Table doesn't exist - app will create it with SQLModel
        # Columns will be created automatically when table is created
        return
    
    # Check if columns already exist
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add is_premium field if it doesn't exist
    if 'is_premium' not in columns:
        op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=True, server_default='false'))
    
    # Add premium_expires_at field if it doesn't exist
    if 'premium_expires_at' not in columns:
        op.add_column('users', sa.Column('premium_expires_at', sa.DateTime(timezone=True), nullable=True))
    
    # Check existing indexes
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    
    # Create index on is_premium for faster queries (if it doesn't exist)
    if 'ix_users_is_premium' not in indexes:
        op.create_index('ix_users_is_premium', 'users', ['is_premium'])
    
    # Create index on premium_expires_at for expiration queries (if it doesn't exist)
    if 'ix_users_premium_expires_at' not in indexes:
        op.create_index('ix_users_premium_expires_at', 'users', ['premium_expires_at'])
    
    # Set default value for existing users (SQLite-compatible)
    # Only if is_premium column exists and has NULL values
    try:
        op.execute("UPDATE users SET is_premium = 0 WHERE is_premium IS NULL")
    except Exception:
        pass  # Ignore if column type doesn't support this


def downgrade() -> None:
    op.drop_index('ix_users_premium_expires_at', table_name='users')
    op.drop_index('ix_users_is_premium', table_name='users')
    op.drop_column('users', 'premium_expires_at')
    op.drop_column('users', 'is_premium')

