"""
Trading Strategies Module
Exports all strategy classes for easy importing.
"""

# INSTITUTIONAL-LEVEL STRATEGIES (Highest Priority)
from backend.app.strategies.vwap_strategy import VWAPStrategy
from backend.app.strategies.support_resistance import SupportResistanceStrategy
from backend.app.strategies.order_blocks import OrderBlocksStrategy
from backend.app.strategies.fair_value_gaps import FairValueGapsStrategy
from backend.app.strategies.market_structure import MarketStructureStrategy
from backend.app.strategies.volume_profile import VolumeProfileStrategy
from backend.app.strategies.liquidity_zones import LiquidityZonesStrategy

# TECHNICAL INDICATOR STRATEGIES
from backend.app.strategies.rsi_macd_momentum import RSI_MACD_MomentumStrategy
from backend.app.strategies.volume_breakout import VolumeBreakoutStrategy
from backend.app.strategies.trend_following import TrendFollowingStrategy
from backend.app.strategies.mean_reversion import MeanReversionStrategy
from backend.app.strategies.momentum import MomentumStrategy
from backend.app.strategies.breakout import BreakoutStrategy
from backend.app.strategies.volatility_breakout import VolatilityBreakoutStrategy

# SENTIMENT/SOCIAL STRATEGIES
from backend.app.strategies.sentiment import SentimentStrategy
from backend.app.strategies.sentiment_filter import SentimentFilterStrategy
from backend.app.strategies.social_copy import SocialCopyStrategy
from backend.app.strategies.arbitrage import ArbitrageStrategy

# Base class
from backend.app.strategies.base import StrategyBase

__all__ = [
    # Institutional-level
    "VWAPStrategy",
    "SupportResistanceStrategy",
    "OrderBlocksStrategy",
    "FairValueGapsStrategy",
    "MarketStructureStrategy",
    "VolumeProfileStrategy",
    "LiquidityZonesStrategy",
    # Technical indicators
    "RSI_MACD_MomentumStrategy",
    "VolumeBreakoutStrategy",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "BreakoutStrategy",
    "VolatilityBreakoutStrategy",
    # Sentiment/Social
    "SentimentStrategy",
    "SentimentFilterStrategy",
    "SocialCopyStrategy",
    "ArbitrageStrategy",
    # Base
    "StrategyBase",
]
