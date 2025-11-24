from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool


from alembic import context
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Helper to use settings.DATABASE_URL and convert async drivers to sync for alembic
def get_alembic_url():
    try:
        from app.core.config import settings as app_settings
        url = app_settings.DATABASE_URL
        # Convert async drivers to sync for Alembic
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "+psycopg2")
        elif "+aiosqlite" in url:
            # Remove aiosqlite and use regular sqlite
            url = url.replace("+aiosqlite", "")
        return url
    except Exception:
        return None


# Import SQLModel metadata
from app.db.models import metadata as target_metadata


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Update the database URL if available
alembic_url = get_alembic_url()
if alembic_url:
    config.set_main_option("sqlalchemy.url", alembic_url)


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
