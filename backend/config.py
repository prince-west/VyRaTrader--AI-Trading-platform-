# backend/config.py
"""
Application settings for VyRaTrader.
Uses pydantic-settings (Pydantic v2) to load environment variables from .env.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Required
    SECRET_KEY: str = Field(..., description="JWT / session secret")
    DATABASE_URL: str = Field(..., description="SQLAlchemy/asyncpg database URL")

    # Optional, with sensible defaults
    PROJECT_NAME: str = "VyRaTrader"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Environment flags
    ENV: str = "development"   # development | staging | production
    DEBUG: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Payment / webhook secrets
    SANDBOX_WEBHOOK_SECRET: str | None = None

    # Broker flags
    BINANCE_TESTNET: bool = False
    OANDA_ENVIRONMENT: str = "practice"

    # Fees & trading rules (defaults can be adjusted)
    DEPOSIT_FEE_PERCENT: float = 2.0
    WITHDRAWAL_FEE_PERCENT: float = 5.0
    MIN_DEPOSIT: float = 500.0


class Config:
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    case_sensitive = False

# ✅ Ensure pydantic loads the .env file in backend/
Settings.model_config = SettingsConfigDict(
    env_file=os.path.join(os.path.dirname(__file__), ".env"),
    case_sensitive=False,
)

# single settings instance for import
settings = Settings()
