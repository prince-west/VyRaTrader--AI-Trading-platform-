"""add market data tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create data_sources table
    op.create_table('data_sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('docs_url', sa.String(), nullable=True),
        sa.Column('auth_type', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_sources_id'), 'data_sources', ['id'], unique=False)
    op.create_index(op.f('ix_data_sources_name'), 'data_sources', ['name'], unique=False)
    op.create_unique_constraint('uq_data_sources_name', 'data_sources', ['name'])

    # Create price_ticks table
    op.create_table('price_ticks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('market', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('quote_volume', sa.Float(), nullable=True),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('extra', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_ticks_id'), 'price_ticks', ['id'], unique=False)
    op.create_index(op.f('ix_price_ticks_source_id'), 'price_ticks', ['source_id'], unique=False)
    op.create_index(op.f('ix_price_ticks_symbol'), 'price_ticks', ['symbol'], unique=False)
    op.create_unique_constraint('uq_price_ticks_source_symbol_ts', 'price_ticks', ['source_id', 'symbol', 'ts'])

    # Create orderbook_snapshots table
    op.create_table('orderbook_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('market', sa.String(), nullable=False),
        sa.Column('bids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('asks', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('depth', sa.Integer(), nullable=True),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('extra', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orderbook_snapshots_id'), 'orderbook_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_orderbook_snapshots_source_id'), 'orderbook_snapshots', ['source_id'], unique=False)
    op.create_index(op.f('ix_orderbook_snapshots_symbol'), 'orderbook_snapshots', ['symbol'], unique=False)

    # Create onchain_metrics table
    op.create_table('onchain_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('network', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('extra', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onchain_metrics_id'), 'onchain_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_onchain_metrics_network'), 'onchain_metrics', ['network'], unique=False)
    op.create_index(op.f('ix_onchain_metrics_metric_name'), 'onchain_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_onchain_metrics_source_id'), 'onchain_metrics', ['source_id'], unique=False)

    # Create news_items table
    op.create_table('news_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('tickers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('categories', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sentiment', sa.Float(), nullable=True),
        sa.Column('extra', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_items_id'), 'news_items', ['id'], unique=False)
    op.create_index(op.f('ix_news_items_source_id'), 'news_items', ['source_id'], unique=False)
    op.create_unique_constraint('uq_news_items_source_url', 'news_items', ['source_id', 'url'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('news_items')
    op.drop_table('onchain_metrics')
    op.drop_table('orderbook_snapshots')
    op.drop_table('price_ticks')
    op.drop_table('data_sources')
