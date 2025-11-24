"""
SQLModel models for VyRaTrader.
- Core application models (preserving existing field names/types used in the repo)
- Market data models (data sources, price ticks, orderbooks, on-chain metrics, news)
- Exposes `metadata = SQLModel.metadata` for Alembic migrations
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from sqlmodel import SQLModel, Field, Column, JSON

from sqlalchemy import Column as SAColumn, DateTime, UniqueConstraint, JSON as SAJSON, Integer, String, Boolean, Text
from sqlalchemy.sql import func



# -----------------------------
# Utilities
# -----------------------------

def gen_uuid() -> str:
    import uuid

    return str(uuid.uuid4())


# -----------------------------
# Core application models
# -----------------------------


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    total_value: float = Field(default=0.0)
    cash_balance: float = Field(default=0.0)
    positions_value: float = Field(default=0.0)
    total_pnl: float = Field(default=0.0)
    snapshot_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    accepted_terms: bool = Field(default=False)
    # Premium subscription fields
    is_premium: bool = Field(default=False, index=True)
    premium_expires_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    currency: str = Field(default="GHS", nullable=False)
    available_balance: float = Field(default=0.0)
    ledger_balance: float = Field(default=0.0)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )



class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: Optional[str] = Field(foreign_key="users.id", index=True)
    account_id: Optional[str] = Field(foreign_key="accounts.id", index=True)
    type: str = Field(nullable=False)  # deposit/withdrawal/fee/trade
    amount: float = Field(nullable=False)
    currency: str = Field(default="GHS")
    status: str = Field(default="pending")  # pending/completed/failed
    fee_percent: Optional[float] = None
    fee_amount: Optional[float] = None
    external_reference: Optional[str] = Field(index=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )



class Trade(SQLModel, table=True):
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    symbol: str = Field(nullable=False, index=True)
    side: str = Field(nullable=False)  # buy/sell
    quantity: float = Field(nullable=False)
    entry_price: float = Field(nullable=False)
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = Field(default="open")  # open, closed, cancelled
    profit_loss: Optional[float] = None
    strategy: Optional[str] = None
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"
    __table_args__ = {'extend_existing': True}

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    name: str = Field(nullable=False)
    config: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    performance: Optional[Dict] = Field(default=None, sa_column=Column(JSON))


class AILog(SQLModel, table=True):
    __tablename__ = "ai_logs"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: Optional[str] = Field(foreign_key="users.id", index=True)
    message: str = Field(default="", sa_column=Column(Text, nullable=False))
    response: str = Field(default="", sa_column=Column(Text, nullable=False))
    context: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    model: Optional[str] = None
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True)
    )



class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    title: str = Field(nullable=False)
    message: str = Field(nullable=False)
    type: str = Field(default="info")  # info, warning, error, success
    read: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True)
    )



class AppWallet(SQLModel, table=True):
    __tablename__ = "app_wallets"
    __table_args__ = {'extend_existing': True}

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    currency: str = Field(nullable=False, unique=True, index=True)
    ledger_balance: float = Field(default=0.0)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )



# -----------------------------
# Market data models
# -----------------------------


class DataSource(SQLModel, table=True):
    """
    Registry of external data sources (crypto, forex, news).
    - Crypto: Binance, CoinGecko, CryptoCompare, Messari, Blockchair, BitcoinAverage, Etherscan,
              Alpha Vantage, Twelve Data, Finnhub, Polygon.io, Tiingo (also provide forex)
      Docs: https://binance-docs.github.io/apidocs/ , https://www.coingecko.com/en/api/documentation ,
            https://min-api.cryptocompare.com/documentation , https://messari.io/api ,
            https://blockchair.com/api , https://apiv2.bitcoinaverage.com/ , https://etherscan.io/apis
    - Forex: ExchangeRate-API, Currencylayer, FreeForexAPI, Open Exchange Rates, API Ninjas,
             Alpha Vantage, Twelve Data, Finnhub, Polygon.io, Tiingo (also provide crypto)
      Docs: https://www.exchangerate-api.com/docs/overview , https://currencylayer.com/documentation ,
            https://www.freeforexapi.com/ , https://docs.openexchangerates.org/ , https://api-ninjas.com/
    - News: NewsAPI.ai, GNews, MediaStack
      Docs: https://newsapi.ai/ , https://gnews.io/docs/ , https://mediastack.com/documentation
    - Note: FMP and EODHD collectors removed (they don't provide crypto/forex data)
    """

    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("name", name="uq_data_sources_name"),
        {'extend_existing': True},
    )

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    name: str = Field(nullable=False, index=True)
    category: str = Field(nullable=False, description="crypto|forex|news")
    base_url: Optional[str] = None
    docs_url: Optional[str] = None
    auth_type: Optional[str] = Field(default="none", description="none|api_key|oauth")
    is_active: bool = Field(default=True)
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
)

    updated_at: datetime = Field(
    sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
)



class PriceTick(SQLModel, table=True):
    """
    Single instrument price snapshot.
    """
    __tablename__ = "price_ticks"
    __table_args__ = (
        UniqueConstraint("source_id", "symbol", "ts", name="uq_price_ticks_source_symbol_ts"),
        {'extend_existing': True},
    )

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    source_id: Optional[str] = Field(default=None, foreign_key="data_sources.id", index=True)
    symbol: str = Field(index=True)
    market: str = Field(default="crypto", description="crypto|forex")
    price: float = Field(default=0.0)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    quote_volume: Optional[float] = None
    ts: datetime = Field(default_factory=datetime.utcnow, description="market timestamp")
    received_at: datetime = Field(default_factory=datetime.utcnow)
    extra: Optional[Dict] = Field(default=None, sa_column=Column(JSON))


class OrderbookSnapshot(SQLModel, table=True):
    """
    Aggregated orderbook snapshot. Bids/asks are stored as arrays [[price, size], ...].
    """

    __tablename__ = "orderbook_snapshots"
    __table_args__ = {'extend_existing': True}

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    source_id: Optional[str] = Field(default=None, foreign_key="data_sources.id", index=True)
    symbol: str = Field(index=True)
    market: str = Field(default="crypto")
    bids: Optional[List] = Field(default=None, sa_column=Column(JSON))
    asks: Optional[List] = Field(default=None, sa_column=Column(JSON))
    depth: Optional[int] = Field(default=None, description="number of levels captured")
    ts: datetime = Field(default_factory=datetime.utcnow)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    extra: Optional[Dict] = Field(default=None, sa_column=Column(JSON))


class OnchainMetric(SQLModel, table=True):
    """
    On-chain metric snapshot (e.g., active addresses, transactions per day).
    """

    __tablename__ = "onchain_metrics"
    __table_args__ = {'extend_existing': True}

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    network: str = Field(index=True, description="e.g., bitcoin, ethereum")
    metric_name: str = Field(index=True)
    value: float = Field(nullable=False)
    unit: Optional[str] = None

    ts: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    source_id: Optional[str] = Field(default=None, foreign_key="data_sources.id", index=True)
    extra: Optional[Dict] = Field(default=None, sa_column=Column(JSON))


class NewsItem(SQLModel, table=True):
    """
    News item normalized across sources.
    """

    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("source_id", "url", name="uq_news_items_source_url"),
        {'extend_existing': True},
    )

    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    source_id: Optional[str] = Field(default=None, foreign_key="data_sources.id", index=True)
    title: str = Field(nullable=False)
    summary: Optional[str] = None
    url: str = Field(nullable=False)
    language: Optional[str] = Field(default="en")
    published_at: Optional[datetime] = Field(default=None)
    tickers: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    categories: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    sentiment: Optional[float] = Field(default=None, description="-1.0..1.0 if available")
    extra: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
)



class Signals(SQLModel, table=True):
    """
    Trading signals generated by strategies.
    """

    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("strategy", "symbol", "timestamp", name="uq_signals_strategy_symbol_timestamp"),
        {'extend_existing': True},
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    strategy: str = Field(nullable=False, index=True)
    symbol: str = Field(nullable=False, index=True)
    action: str = Field(nullable=False)  # buy, sell, hold
    entry: float = Field(nullable=False)
    sl: float = Field(nullable=False)  # stop loss
    tp: float = Field(nullable=False)  # take profit
    confidence: float = Field(default=0.5)
    source_meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    processed: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}
    
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(nullable=False, unique=True, index=True)
    expires_at: datetime = Field(nullable=False)
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APICache(SQLModel, table=True):
    """
    Cache for API responses to reduce API request consumption.
    Stores temporary cached data from APIs that can be reused across users.
    """
    __tablename__ = "api_cache"
    __table_args__ = (
        UniqueConstraint("api_name", "cache_key", name="uq_api_cache_key"),
        {'extend_existing': True},
    )
    
    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    api_name: str = Field(nullable=False, index=True)
    cache_key: str = Field(nullable=False, index=True)
    data: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    request_count: int = Field(default=1, description="number of times this cache was used")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(nullable=False)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class APICallLog(SQLModel, table=True):
    """
    Log of API calls for monitoring and retraining Prince AI.
    Helps track what data Prince uses and how successful predictions are.
    """
    __tablename__ = "api_call_logs"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    api_name: str = Field(nullable=False, index=True)
    endpoint: Optional[str] = None
    category: str = Field(nullable=False, index=True, description="crypto|stock|forex|etc")
    query: Optional[str] = None
    response_time_ms: Optional[float] = None
    success: bool = Field(default=True)
    user_id: Optional[str] = None
    cached: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)


class PrinceSignalAlert(SQLModel, table=True):
    """
    Alert notifications when Prince AI finds reliable signals for users who are offline.
    """
    __tablename__ = "prince_signal_alerts"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    signal_id: Optional[str] = Field(default=None, foreign_key="signals.id")
    symbol: str = Field(nullable=False, index=True)
    market: str = Field(nullable=False, index=True)
    action: str = Field(nullable=False, description="buy|sell|hold")
    confidence: float = Field(default=0.0)
    expected_profit_pct: Optional[float] = None
    risk_level: str = Field(default="medium")
    prince_message: Optional[str] = None
    notified: bool = Field(default=False)
    notification_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: datetime = Field(nullable=False, index=True)


class StrategyPerformance(SQLModel, table=True):
    """
    Track performance of each strategy for continuous improvement.
    Helps Prince AI learn which strategies work best in different market conditions.
    """
    __tablename__ = "strategy_performance"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[str] = Field(default_factory=gen_uuid, primary_key=True, index=True)
    strategy_name: str = Field(nullable=False, index=True)
    market_condition: str = Field(nullable=False, index=True)
    symbol: Optional[str] = None
    win_rate: float = Field(default=0.0)
    avg_profit: float = Field(default=0.0)
    avg_loss: float = Field(default=0.0)
    total_trades: int = Field(default=0)
    total_pnl: float = Field(default=0.0)
    sharpe_ratio: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime = Field(default_factory=datetime.utcnow)
    period_end: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------
# Alembic integration
# -----------------------------

metadata = SQLModel.metadata
