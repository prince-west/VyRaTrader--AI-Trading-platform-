import sys, os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

# make backend importable
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.core.config import settings
# import your SQLModel/SQLAlchemy Base
from backend.app.db.models import metadata
# Use the metadata from our models module
target_metadata = metadata

def get_sync_url(async_url: str) -> str:
    if async_url.startswith("postgresql+asyncpg://"):
        return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if async_url.startswith("postgresql://"):
        return async_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return async_url

DATABASE_URL = get_sync_url(settings.DATABASE_URL)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_online():
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
