"""conditionally add premium columns to users (SQLite-safe)

Revision ID: add_premium_columns_sqlite
Revises: add_premium_fields
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_premium_columns_sqlite'
down_revision = 'add_premium_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    cols = {c['name'] for c in inspector.get_columns('users')}

    # Add is_premium column if it doesn't exist
    if 'is_premium' not in cols:
        try:
            op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=True, server_default='0'))
            debugPrint = print  # Simple debug
            debugPrint(f'✅ Added is_premium column to users table')
        except Exception as e:
            print(f'⚠️ Failed to add is_premium: {e}')
    
    # Refresh column list after adding
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('users')}
    
    # Add premium_expires_at column if it doesn't exist
    if 'premium_expires_at' not in cols:
        try:
            op.add_column('users', sa.Column('premium_expires_at', sa.DateTime(timezone=True), nullable=True))
            print(f'✅ Added premium_expires_at column to users table')
        except Exception as e:
            print(f'⚠️ Failed to add premium_expires_at: {e}')

    # Create indexes if columns exist
    cols = {c['name'] for c in inspector.get_columns('users')}
    idx_names = {i['name'] for i in inspector.get_indexes('users')}
    
    if 'is_premium' in cols and 'ix_users_is_premium' not in idx_names:
        try:
            op.create_index('ix_users_is_premium', 'users', ['is_premium'])
            print(f'✅ Created index ix_users_is_premium')
        except Exception as e:
            print(f'⚠️ Failed to create index: {e}')
            
    if 'premium_expires_at' in cols and 'ix_users_premium_expires_at' not in idx_names:
        try:
            op.create_index('ix_users_premium_expires_at', 'users', ['premium_expires_at'])
            print(f'✅ Created index ix_users_premium_expires_at')
        except Exception as e:
            print(f'⚠️ Failed to create index: {e}')


def downgrade() -> None:
    # Safe to drop indexes/columns if exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'users' in inspector.get_table_names():
        # Drop indexes if present
        try:
            op.drop_index('ix_users_premium_expires_at', table_name='users')
        except Exception:
            pass
        try:
            op.drop_index('ix_users_is_premium', table_name='users')
        except Exception:
            pass
        # Drop columns (SQLite can't drop easily; skip in downgrade)
        # Intentionally left no-op for SQLite compatibility
        pass
