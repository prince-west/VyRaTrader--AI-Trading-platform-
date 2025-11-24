"""
Application configuration using Pydantic BaseSettings.
Centralized settings loader for the VyRaTrader backend.
"""

from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List, Optional
from functools import lru_cache
import os


class AppConfig(BaseSettings):
    # Environment
    ENV: str = "development"
    DEBUG: bool = True

    # Core app info
    PROJECT_NAME: str = "VyRaTrader"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Database - Using SQLite for development, PostgreSQL for production
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vyra_trader.db")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Secrets - MUST be set via environment variables in production
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
    SANDBOX_WEBHOOK_SECRET: str = os.getenv("SANDBOX_WEBHOOK_SECRET", "CHANGE_THIS_IN_PRODUCTION")

    # AI
    OPENAI_API_KEY: Optional[str] = None

    # Broker flags
    BINANCE_TESTNET: bool = True
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    OANDA_ENVIRONMENT: str = "practice"
    OANDA_API_KEY: Optional[str] = None

    # Frontend origins allowed for CORS
    CORS_ORIGINS: Optional[List[AnyHttpUrl]] = None

    # Trading rules / fees
    MIN_DEPOSIT: float = 500.0
    DEPOSIT_FEE_PERCENT: float = 2.0
    WITHDRAWAL_FEE_PERCENT: float = 5.0

    # Data collection
    COLLECTION_INTERVAL: int = 30
    CRYPTO_SYMBOLS: List[str] = ["BTCUSDT", "ETHUSDT"]
    COINGECKO_IDS: List[str] = ["bitcoin", "ethereum"]
    FOREX_PAIRS: List[str] = ["EURUSD", "USDJPY"]
    NEWS_QUERY: str = "markets"
    FRED_SERIES: List[str] = ["DGS10"]

    # API Keys (all optional - collectors will skip if missing)
    # Crypto APIs (Core)
    COINMARKETCAP_API_KEY: Optional[str] = None
    CRYPTOCOMPARE_API_KEY: Optional[str] = None
    MESSARI_API_KEY: Optional[str] = None
    ETHERSCAN_API_KEY: Optional[str] = None
    BSCSCAN_API_KEY: Optional[str] = None
    POLYGONSCAN_API_KEY: Optional[str] = None
    
    # Additional crypto/forex APIs (Alpha Vantage, Twelve Data, Finnhub, Polygon, Tiingo provide crypto/forex)
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    TWELVE_DATA_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    TIINGO_API_KEY: Optional[str] = None
    
    # Forex APIs (Core)
    EXCHANGERATE_API_KEY: Optional[str] = None
    OPEN_EXCHANGE_RATES_API_KEY: Optional[str] = None
    API_NINJAS_KEY: Optional[str] = None  # Also provides forex data
    
    # News APIs (Core)
    NEWSAPI_KEY: Optional[str] = None
    GNEWS_API_KEY: Optional[str] = None
    MARKETAUX_API_KEY: Optional[str] = None
    
    # Macro APIs (Core)
    FRED_API_KEY: Optional[str] = None
    WORLD_BANK_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # prevents crash if .env has extra keys


# ✅ Cache settings instance (so it’s only loaded once)
@lru_cache()
def get_settings() -> AppConfig:
    return AppConfig()


# ✅ Export for global import (used in main.py and others)
settings: AppConfig = get_settings()
