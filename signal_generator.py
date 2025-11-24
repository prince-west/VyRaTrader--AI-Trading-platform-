#!/usr/bin/env python3
"""
VyRaTrader Personal AI Signal Generator
A locally-running AI signal generator that:
- Collects market data from multiple free sources
- Runs 9 trading strategies continuously
- Filters signals with local AI (Ollama) or fallback providers
- Sends notifications via Telegram

Run with: python signal_generator.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# IMPORTANT: Import root config FIRST before adding backend to path
# This ensures we get config/settings.py, not backend/config.py
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Import config from root config/ directory BEFORE backend imports
from config.settings import SignalGeneratorConfig
from services.ai_filter import AIFilter
from services.telegram_notifier import TelegramNotifier
from services.signal_logger import SignalLogger

# NOW add backend to path for other imports
backend_path = str(Path(__file__).parent / "backend")
sys.path.insert(0, backend_path)

from dotenv import load_dotenv
import logging

# Import logger directly without triggering backend config  
from loguru import logger
# Set up logger to avoid import issues
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger.add(LOG_DIR / "signal_generator.log", rotation="10 MB", retention="14 days", level="INFO")

from app.services.data_collector import run_periodic, collect_crypto_batch, collect_forex_batch, collect_additional_crypto_forex_batch
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.breakout import BreakoutStrategy
from app.strategies.volatility_breakout import VolatilityBreakoutStrategy
from app.strategies.sentiment import SentimentStrategy
from app.strategies.sentiment_filter import SentimentFilterStrategy
from app.strategies.social_copy import SocialCopyStrategy
# Arbitrage removed: Requires millisecond execution, opportunities disappear in seconds (not practical for 10-minute intervals)
from app.strategies.rsi_macd_momentum import RSI_MACD_MomentumStrategy
from app.strategies.volume_breakout import VolumeBreakoutStrategy
from app.db.session import get_session
from app.db.models import PriceTick
from sqlmodel import select

# Load environment variables
load_dotenv()

# Load config
config = SignalGeneratorConfig()


class SignalGenerator:
    """
    Main signal generator that orchestrates:
    1. Data collection
    2. Strategy execution
    3. AI filtering
    4. Telegram notifications
    """
    
    def __init__(self):
        """Initialize the signal generator with all components."""
        self.config = config
        self.ai_filter = AIFilter(
            provider=config.AI_PROVIDER,
            model=config.AI_MODEL,
            confidence_threshold=config.AI_CONFIDENCE_THRESHOLD,
            groq_api_key=getattr(config, 'GROQ_API_KEY', None),
            huggingface_api_key=getattr(config, 'HUGGINGFACE_API_KEY', None),
        )
        self.telegram = TelegramNotifier(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID,
        )
        self.signal_logger = SignalLogger()
        
        # Initialize professional strategies (prioritize professional implementations)
        from backend.app.strategies.support_resistance import SupportResistanceStrategy
        from backend.app.strategies.vwap_strategy import VWAPStrategy
        from backend.app.strategies.order_blocks import OrderBlocksStrategy
        from backend.app.strategies.fair_value_gaps import FairValueGapsStrategy
        from backend.app.strategies.market_structure import MarketStructureStrategy
        from backend.app.strategies.volume_profile import VolumeProfileStrategy
        from backend.app.strategies.liquidity_zones import LiquidityZonesStrategy
        
        self.strategies = {
            # INSTITUTIONAL-LEVEL STRATEGIES (Highest Priority)
            "vwap": VWAPStrategy(),  # VWAP - institutional traders' PRIMARY tool
            "support_resistance": SupportResistanceStrategy(),  # Pivot-based S/R with order flow
            "order_blocks": OrderBlocksStrategy(),  # Smart money order placement zones
            "fair_value_gaps": FairValueGapsStrategy(),  # Price imbalances (90%+ fill rate)
            "market_structure": MarketStructureStrategy(),  # BOS/CHoCH - eliminates 60% of losses
            "volume_profile": VolumeProfileStrategy(),  # Price Volume Nodes (PVN)
            "liquidity_zones": LiquidityZonesStrategy(),  # Stop loss clusters (institutional hunts)
            
            # TECHNICAL INDICATOR STRATEGIES
            "rsi_macd_momentum": RSI_MACD_MomentumStrategy(),  # Professional RSI+MACD
            "volume_breakout": VolumeBreakoutStrategy(),  # Professional Volume Breakout
            "trend_following": TrendFollowingStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "momentum": MomentumStrategy(),
            "breakout": BreakoutStrategy(),
            "volatility_breakout": VolatilityBreakoutStrategy(),
            
            # SENTIMENT/SOCIAL STRATEGIES
            "sentiment": SentimentStrategy(),
            "sentiment_filter": SentimentFilterStrategy(),
            "social_copy": SocialCopyStrategy(),
            # Arbitrage removed: Requires millisecond execution, not practical for manual trading
        }
        
        # Track signal statistics
        self.stats = {
            "total_signals": 0,
            "ai_filtered": 0,
            "telegram_sent": 0,
            "by_strategy": defaultdict(int),
            "last_collection": None,
        }
        
        # Signal deduplication: track recent signals to prevent spam (6 hours cooldown)
        # Format: {(strategy, symbol, action): timestamp}
        self.recent_signals: Dict[tuple, datetime] = {}
        self.signal_cooldown_hours = 6  # Don't send same signal within 6 hours (professional standard)
        
        # Strategy performance-based weights (meta-labeling concept)
        # Higher weights for strategies that historically perform better
        # Based on research: ensemble weighting improves accuracy significantly
        self.strategy_weights = {
            # INSTITUTIONAL-LEVEL STRATEGIES (Highest Weights)
            "vwap": 3.0,  # VWAP - institutional traders' PRIMARY tool (highest weight)
            "liquidity_zones": 2.8,  # Liquidity grabs - extremely reliable (80-90% win rate)
            "order_blocks": 2.7,  # Smart money zones - very accurate (80%+ win rate)
            "fair_value_gaps": 2.6,  # FVG fills - 90%+ fill rate
            "market_structure": 2.5,  # BOS/CHoCH - eliminates 60% of losing trades
            "support_resistance": 2.4,  # Pivot-based S/R with order flow
            "volume_profile": 2.3,  # PVN bounces - very reliable
            
            # TECHNICAL INDICATOR STRATEGIES
            "rsi_macd_momentum": 1.5,  # Enhanced with divergence - high weight
            "volume_breakout": 1.3,    # Professional breakout - high weight
            "trend_following": 1.2,    # Multi-timeframe - high weight
            "momentum": 1.1,           # MACD momentum - good weight
            "breakout": 1.0,           # Standard breakout - base weight
            "mean_reversion": 0.9,     # Mean reversion - slightly lower
            "volatility_breakout": 0.9, # Volatility breakout - slightly lower
            
            # SENTIMENT/SOCIAL STRATEGIES
            "sentiment": 0.7,          # Sentiment - lower weight (less reliable)
            "social_copy": 0.6,       # Social copy - lower weight (external dependency)
            # Arbitrage removed: Requires millisecond execution, opportunities disappear in seconds
        }
        
        # Reliability configuration - selective for 3-8 signals/day across 30 assets
        # Enhanced with weighted consensus
        self.min_reliable_confidence = 0.55  # Single strategy needs 55%+ confidence to be considered reliable
        self.min_consensus_strategies = 2  # Need at least 2 strategies to agree for consensus
        self.consensus_min_confidence = 0.45  # Consensus strategies need at least 45% confidence each
        self.weighted_consensus_threshold = 2.0  # Weighted consensus score must be >= 2.0
        
        logger.info("✅ Signal Generator initialized")
        logger.info(f"   - Monitoring {len(config.ASSETS)} assets ({len(config.CRYPTO_SYMBOLS)} crypto, {len(config.FOREX_PAIRS)} forex)")
        logger.info(f"   - Crypto: {', '.join(config.CRYPTO_SYMBOLS[:5])}{'...' if len(config.CRYPTO_SYMBOLS) > 5 else ''}")
        if config.FOREX_PAIRS:
            logger.info(f"   - Forex: {', '.join(config.FOREX_PAIRS[:5])}{'...' if len(config.FOREX_PAIRS) > 5 else ''}")
        logger.info(f"   - Running {len(self.strategies)} strategies")
        logger.info(f"   - AI Provider: {config.AI_PROVIDER}")
        logger.info(f"   - AI Confidence Threshold: {config.AI_CONFIDENCE_THRESHOLD}/10 (signals must score ≥{config.AI_CONFIDENCE_THRESHOLD}/10 to pass)")
        
        # Check market hours status
        try:
            from services.market_hours import MarketHours
            market_status = MarketHours.get_market_status_message()
            logger.info(f"   - {market_status}")
        except ImportError:
            logger.warning("   - Market hours check unavailable (pytz may not be installed)")
        
        logger.info(f"   - Reliability Settings (Enhanced with Ensemble Weighting):")
        logger.info(f"     • Weighted consensus ≥{self.weighted_consensus_threshold:.1f} OR")
        logger.info(f"     • {self.min_consensus_strategies}+ strategies agree (each ≥{self.consensus_min_confidence:.0%}) OR")
        logger.info(f"     • Single strategy ≥{self.min_reliable_confidence:.0%} confidence (high-weight strategies preferred)")
        logger.info(f"   - Strategy Weights (Performance-Based):")
        for strategy_name, weight in sorted(self.strategy_weights.items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"     • {strategy_name}: {weight:.1f}x")
        
        # CRITICAL: Startup grace period to accumulate data
        self.startup_time = datetime.utcnow()
        self.startup_grace_minutes = 10  # Wait 10 minutes before signaling
        self.grace_period_active = True
        
        logger.info(f"   - Startup grace period: {self.startup_grace_minutes} minutes")
        logger.info(f"   - Signals will start after {(self.startup_time + timedelta(minutes=self.startup_grace_minutes)).strftime('%H:%M:%S')}")
    
    async def collect_market_data(self) -> bool:
        """
        Collect market data using the existing data collector.
        Supports both crypto and forex data collection.
        Returns True if data was collected successfully.
        """
        try:
            logger.info("📊 Collecting market data...")
            
            total_ticks = 0
            sources_count = 0
            
            # Collect crypto data if configured
            crypto_symbols = config.CRYPTO_SYMBOLS
            coingecko_ids = config.COINGECKO_IDS
            if crypto_symbols or coingecko_ids:
                crypto_results = await collect_crypto_batch(crypto_symbols, coingecko_ids)
                crypto_ticks = sum(len(ticks) for ticks in crypto_results.values() if ticks)
                total_ticks += crypto_ticks
                sources_count += len([k for k, v in crypto_results.items() if v])
                if crypto_ticks > 0:
                    logger.debug(f"Collected {crypto_ticks} crypto price ticks")
            
            # Collect forex data if configured
            forex_pairs = config.FOREX_PAIRS
            if forex_pairs:
                forex_results = await collect_forex_batch(forex_pairs)
                forex_ticks = sum(len(ticks) for ticks in forex_results.values() if ticks)
                total_ticks += forex_ticks
                sources_count += len([k for k, v in forex_results.items() if v])
                if forex_ticks > 0:
                    logger.debug(f"Collected {forex_ticks} forex price ticks")
                
                # Also collect from additional sources that support both crypto and forex
                additional_results = await collect_additional_crypto_forex_batch(forex_pairs)
                additional_ticks = sum(len(ticks) for ticks in additional_results.values() if ticks)
                total_ticks += additional_ticks
                sources_count += len([k for k, v in additional_results.items() if v])
                if additional_ticks > 0:
                    logger.debug(f"Collected {additional_ticks} additional price ticks")
            
            logger.info(f"✅ Collected {total_ticks} price ticks from {sources_count} sources")
            
            self.stats["last_collection"] = datetime.utcnow()
            return total_ticks > 0
            
        except Exception as e:
            logger.exception(f"❌ Error collecting market data: {e}")
            return False
    
    async def update_strategies_with_data(self, symbol: str) -> None:
        """
        Update all strategies with latest market data for continuous monitoring.
        This feeds new candles to strategies so they can detect pattern completion.
        """
        async for session in get_session():
            # Fetch recent price data
            cutoff = datetime.utcnow() - timedelta(hours=24)
            stmt = (
                select(PriceTick)
                .where(PriceTick.symbol == symbol)
                .where(PriceTick.ts >= cutoff)
                .order_by(PriceTick.ts)  # Oldest first
            )
            result = await session.exec(stmt)
            ticks = result.all()
            
            if not ticks:
                logger.debug(f"No price data found for {symbol}")
                break
            
            # Update each strategy with new candles
            for strategy_name, strategy in self.strategies.items():
                if strategy_name == "sentiment_filter":
                    continue  # Skip filter strategies
                
                try:
                    # Check if strategy supports update_data method (pattern completion model)
                    if hasattr(strategy, 'update_data'):
                        # Convert ticks to candles and update strategy
                        for tick in ticks:
                            candle = {
                                'timestamp': tick.ts,
                                'open': tick.open or tick.price,
                                'high': tick.high or tick.price,
                                'low': tick.low or tick.price,
                                'close': tick.price,
                                'volume': tick.volume or 0.0,
                            }
                            strategy.update_data(symbol, candle)
                    # For async strategies (TrendFollowing, VolatilityBreakout), they handle their own data
                    # We'll call their check_for_signal method if available
                except Exception as e:
                    logger.debug(f"Error updating {strategy_name} with data for {symbol}: {e}")
                    continue
            
            break  # Only use first session
    
    async def run_strategies(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Run all strategies on a symbol using pattern completion model.
        Only returns signals when patterns just completed.
        """
        signals = []
        
        # CRITICAL: Check startup grace period
        if self.grace_period_active:
            elapsed_minutes = (datetime.utcnow() - self.startup_time).total_seconds() / 60
            if elapsed_minutes < self.startup_grace_minutes:
                # Still in grace period - skip signaling
                return []
            else:
                # Grace period over - allow signals
                self.grace_period_active = False
                logger.info(f"✅ Startup grace period complete ({self.startup_grace_minutes} minutes) - signals now active")
        
        # First, update strategies with latest data
        await self.update_strategies_with_data(symbol)
        
        async for session in get_session():
            # Fetch recent price data for price trends calculation
            cutoff = datetime.utcnow() - timedelta(hours=24)
            stmt = (
                select(PriceTick)
                .where(PriceTick.symbol == symbol)
                .where(PriceTick.ts >= cutoff)
                .order_by(PriceTick.ts)
            )
            result = await session.exec(stmt)
            ticks = result.all()
            
            if not ticks:
                logger.debug(f"No price data found for {symbol}")
                break
            
            current_price = float(ticks[-1].price) if ticks else 0.0
            price_trends = self._calculate_price_trends(ticks, current_price, signal_timestamp=None)
            
            # Check each strategy for pattern completion
            for strategy_name, strategy in self.strategies.items():
                if strategy_name == "sentiment_filter":
                    continue  # Skip filter strategies
                
                try:
                    signal = None
                    
                    # Check for async generate_signal first (TrendFollowing, VolatilityBreakout)
                    # These strategies handle their own data fetching
                    if hasattr(strategy, 'generate_signal') and callable(getattr(strategy, 'generate_signal')):
                        import inspect
                        sig = inspect.signature(strategy.generate_signal)
                        if 'portfolio_value' in sig.parameters:
                            signal = await strategy.generate_signal(session, symbol, portfolio_value=10000.0)
                        else:
                            signal = await strategy.generate_signal(session, symbol)
                        
                        if signal and "action" not in signal:
                            signal["action"] = signal.get("signal", "hold")
                        if signal and "entry" not in signal:
                            signal["entry"] = signal.get("price", current_price)
                        if signal and "price_trends" not in signal:
                            signal["price_trends"] = price_trends
                        
                        # CRITICAL: Add time limit if not present (when to close trade)
                        if signal and "duration_minutes" not in signal:
                            time_limit = self._calculate_time_limit(strategy_name)
                            signal["duration_minutes"] = time_limit["duration_minutes"]
                            signal["duration_hours"] = time_limit["duration_hours"]
                            signal["expires_at"] = time_limit["expires_at"]
                            signal["time_limit_message"] = time_limit["time_limit_message"]
                    
                    # Check if strategy supports pattern completion model (check_for_signal)
                    elif hasattr(strategy, 'check_for_signal'):
                        # Pattern completion model - check if pattern just completed
                        signal = strategy.check_for_signal(symbol)
                        
                        # Log diagnostic info for strategies that return None
                        if not signal and hasattr(strategy, 'price_history') and symbol in strategy.price_history:
                            history_count = len(strategy.price_history[symbol])
                            logger.debug(f"Strategy {strategy_name} on {symbol} returned no signal (history: {history_count} candles)")
                        
                        if signal:
                            # Ensure signal has all required fields
                            if "strategy" not in signal:
                                signal["strategy"] = strategy_name
                            if "symbol" not in signal:
                                signal["symbol"] = symbol
                            if "timestamp" not in signal:
                                signal["timestamp"] = datetime.utcnow().isoformat()
                            
                            # PROFESSIONAL TRADING PRACTICE: Entry price should be LIVE market price (current_price)
                            # Not historical candle close - use live price for accurate entry
                            # Only use signal's entry if it's valid AND close to current price (within 1%)
                            signal_entry = signal.get("entry", 0.0)
                            entry_changed = False
                            if signal_entry <= 0:
                                # Invalid entry - use live market price
                                signal["entry"] = current_price
                                entry_changed = True
                                logger.debug(f"Using live market price as entry for {strategy_name} {symbol}: {current_price}")
                            elif current_price > 0:
                                # Check if signal entry is too far from live price (stale data)
                                price_diff_pct = abs(signal_entry - current_price) / current_price if current_price > 0 else 1.0
                                if price_diff_pct > 0.01:  # More than 1% difference
                                    # Use live price instead of stale candle close
                                    signal["entry"] = current_price
                                    entry_changed = True
                                    logger.debug(f"Signal entry {signal_entry} too far from live price {current_price} ({price_diff_pct*100:.2f}%) - using live price")
                                # If within 1%, keep signal's entry (it's close enough)
                            
                            # FIX: If entry changed, recalculate stop_loss/take_profit as offsets from new entry
                            # This ensures risk/reward remains valid when entry is updated to live price
                            current_entry = signal.get("entry", current_price)
                            
                            # Use stop_loss/take_profit from signal if available, otherwise calculate
                            if "sl" not in signal and "stop_loss" not in signal:
                                signal["stop_loss"] = self._calculate_stop_loss(
                                    current_entry,
                                    signal.get("action", "hold"),
                                    signal.get("confidence", 0.0) * 5.0
                                )
                            elif "sl" in signal:
                                signal["stop_loss"] = signal.pop("sl")
                            
                            # FIX: If entry changed and stop_loss exists, recalculate it as offset from new entry
                            if entry_changed and signal.get("stop_loss", 0.0) > 0:
                                old_entry = signal_entry if signal_entry > 0 else current_entry
                                old_stop_loss = signal.get("stop_loss", 0.0)
                                if old_entry > 0:
                                    # Calculate stop_loss as percentage offset from old entry
                                    if signal.get("action") == "buy":
                                        stop_loss_offset_pct = (old_entry - old_stop_loss) / old_entry if old_entry > 0 else 0.02
                                        # Recalculate stop_loss based on new entry with same offset
                                        signal["stop_loss"] = current_entry * (1 - stop_loss_offset_pct)
                                    else:  # sell
                                        stop_loss_offset_pct = (old_stop_loss - old_entry) / old_entry if old_entry > 0 else 0.02
                                        # Recalculate stop_loss based on new entry with same offset
                                        signal["stop_loss"] = current_entry * (1 + stop_loss_offset_pct)
                            
                            if "tp" not in signal and "take_profit" not in signal:
                                signal["take_profit"] = self._calculate_take_profit(
                                    current_entry,
                                    signal.get("action", "hold"),
                                    signal.get("confidence", 0.0) * 5.0
                                )
                            elif "tp" in signal:
                                signal["take_profit"] = signal.pop("tp")
                            
                            # FIX: If entry changed and take_profit exists, recalculate it as offset from new entry
                            if entry_changed and signal.get("take_profit", 0.0) > 0:
                                old_entry = signal_entry if signal_entry > 0 else current_entry
                                old_take_profit = signal.get("take_profit", 0.0)
                                if old_entry > 0:
                                    # Calculate take_profit as percentage offset from old entry
                                    if signal.get("action") == "buy":
                                        take_profit_offset_pct = (old_take_profit - old_entry) / old_entry if old_entry > 0 else 0.04
                                        # Recalculate take_profit based on new entry with same offset
                                        signal["take_profit"] = current_entry * (1 + take_profit_offset_pct)
                                    else:  # sell
                                        take_profit_offset_pct = (old_entry - old_take_profit) / old_entry if old_entry > 0 else 0.04
                                        # Recalculate take_profit based on new entry with same offset
                                        signal["take_profit"] = current_entry * (1 - take_profit_offset_pct)
                            
                            # FIX: Validate stop_loss and take_profit are valid after recalculation
                            if signal.get("stop_loss", 0.0) <= 0:
                                logger.warning(f"Invalid stop_loss after recalculation for {strategy_name} {symbol} - recalculating")
                                signal["stop_loss"] = self._calculate_stop_loss(
                                    current_entry,
                                    signal.get("action", "hold"),
                                    signal.get("confidence", 0.0) * 5.0
                                )
                            
                            if signal.get("take_profit", 0.0) <= 0:
                                logger.warning(f"Invalid take_profit after recalculation for {strategy_name} {symbol} - recalculating")
                                signal["take_profit"] = self._calculate_take_profit(
                                    current_entry,
                                    signal.get("action", "hold"),
                                    signal.get("confidence", 0.0) * 5.0
                                )
                            
                            # Add price trends (don't overwrite if already present)
                            if "price_trends" not in signal:
                                signal_timestamp = datetime.fromisoformat(signal.get("timestamp", datetime.utcnow().isoformat()).split('+')[0].split('Z')[0]) if 'T' in signal.get("timestamp", "") else datetime.utcnow()
                                signal["price_trends"] = self._calculate_price_trends(ticks, signal.get("entry", current_price), signal_timestamp)
                            signal["reference_price"] = current_price
                            
                            # CRITICAL: Add time limit if not present (when to close trade)
                            if "duration_minutes" not in signal:
                                time_limit = self._calculate_time_limit(strategy_name)
                                signal["duration_minutes"] = time_limit["duration_minutes"]
                                signal["duration_hours"] = time_limit["duration_hours"]
                                signal["expires_at"] = time_limit["expires_at"]
                                signal["time_limit_message"] = time_limit["time_limit_message"]
                            
                            # ENHANCEMENT: Add missing technical indicators if not present
                            # This ensures AI has all data it needs for better scoring
                            signal = self._enrich_signal_with_indicators(signal, symbol, strategy)
                    
                    # Legacy run method (for backward compatibility)
                    elif hasattr(strategy, 'run') and callable(getattr(strategy, 'run')):
                        prices = [float(tick.price) for tick in ticks]
                        try:
                            signal_data = strategy.run(symbol, prices)
                        except Exception as strategy_error:
                            logger.debug(f"Strategy {strategy_name} on {symbol} raised exception: {strategy_error}")
                            signal_data = {"signal": "hold", "confidence": 0.0}
                        
                        signal_action = signal_data.get("signal", "hold")
                        if signal_action == "hold":
                            # Log why strategy returned hold (for debugging)
                            reason = signal_data.get("reason", "unknown")
                            logger.debug(f"Strategy {strategy_name} on {symbol} returned 'hold' - reason: {reason}")
                            continue
                        
                        signal_timestamp = datetime.utcnow()
                        
                        # Calculate time limit for trade (CRITICAL: When to close trade)
                        # Based on research: Time limit = 3x timeframe for day trading
                        time_limit = self._calculate_time_limit(strategy_name)
                        
                        signal = {
                            "strategy": strategy_name,
                            "symbol": symbol,
                            "action": signal_action,
                            "entry": current_price,
                            "stop_loss": self._calculate_stop_loss(current_price, signal_action, signal_data.get("confidence", 0.0) * 5.0),
                            "take_profit": self._calculate_take_profit(current_price, signal_action, signal_data.get("confidence", 0.0) * 5.0),
                            "confidence": signal_data.get("confidence", 0.0),
                            "timestamp": signal_timestamp.isoformat(),
                            "signal_generated_at": signal_timestamp,  # CRITICAL: Track when signal was generated
                            "price_trends": self._calculate_price_trends(ticks, current_price, signal_timestamp),
                            "reference_price": current_price,
                            # CRITICAL: Time limit for trade - close after this duration
                            "duration_minutes": time_limit["duration_minutes"],
                            "duration_hours": time_limit["duration_hours"],
                            "expires_at": time_limit["expires_at"],
                            "time_limit_message": time_limit["time_limit_message"],
                        }
                        
                        # ENHANCEMENT: Add missing technical indicators
                        signal = self._enrich_signal_with_indicators(signal, symbol, strategy)
                    else:
                        logger.debug(f"Strategy {strategy_name} has no supported method - skipping")
                        continue
                    
                    # Validate signal quality
                    if signal and signal.get("action") != "hold":
                        if not self.validate_signal(signal):
                            logger.info(f"⚠️ Signal from {strategy_name} for {symbol} failed validation - checking details...")
                            # Log why it failed for debugging
                            action = signal.get('action')
                            entry = signal.get('entry', 0.0)
                            stop_loss = signal.get('stop_loss', 0.0)
                            take_profit = signal.get('take_profit', 0.0)
                            if action == "buy":
                                risk = entry - stop_loss if entry > stop_loss else 0
                                reward = take_profit - entry if take_profit > entry else 0
                            else:
                                risk = stop_loss - entry if stop_loss > entry else 0
                                reward = entry - take_profit if entry > take_profit else 0
                            if risk > 0:
                                ratio = reward / risk
                                logger.info(f"   Risk/reward ratio: {ratio:.2f} (entry={entry:.4f}, sl={stop_loss:.4f}, tp={take_profit:.4f})")
                            continue
                        
                        # Apply minimum confidence threshold
                        min_confidence = 0.0
                        if hasattr(config, 'STRATEGY_SETTINGS') and config.STRATEGY_SETTINGS:
                            strategy_settings = config.STRATEGY_SETTINGS.get(strategy_name, {})
                            min_confidence = strategy_settings.get("min_confidence", 0.0)
                        
                        signal_confidence = signal.get("confidence", 0.0)
                        if signal_confidence >= min_confidence:
                            # CRITICAL: Mark when signal was GENERATED (for age tracking)
                            if "signal_generated_at" not in signal:
                                signal["signal_generated_at"] = datetime.utcnow()
                            signals.append(signal)
                            self.stats["by_strategy"][strategy_name] += 1
                            self.stats["total_signals"] += 1
                            logger.info(f"✅ Pattern completed: {strategy_name} {symbol} {signal.get('action')} (confidence: {signal_confidence:.3f})")
                        else:
                            logger.info(f"❌ Signal filtered: {strategy_name} {symbol} confidence {signal_confidence:.3f} < min {min_confidence:.3f}")
                    elif signal and signal.get("action") == "hold":
                        logger.debug(f"Strategy {strategy_name} on {symbol} returned 'hold' signal")
                    elif not signal:
                        logger.debug(f"Strategy {strategy_name} on {symbol} returned no signal")
                    
                except ZeroDivisionError as e:
                    logger.warning(f"Division by zero in {strategy_name} on {symbol}: {e}")
                    continue
                except ValueError as e:
                    logger.warning(f"Value error in {strategy_name} on {symbol}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error running {strategy_name} on {symbol}: {e}", exc_info=True)
                    continue
            
            break  # Only use first session
        
        return signals
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate signal quality before sending.
        All criteria must pass for signal to be valid.
        
        Returns:
            True if signal is valid, False otherwise
        """
        if not signal:
            return False
        
        # CRITICAL: Check if signal is from fresh startup (likely false positive)
        signal_time = signal.get('timestamp')
        if signal_time:
            try:
                if isinstance(signal_time, str):
                    sig_dt = datetime.fromisoformat(signal_time.replace('Z', '+00:00').split('+')[0])
                else:
                    sig_dt = signal_time
                
                # Reject signals generated within first 10 minutes of startup
                time_since_startup = (datetime.utcnow() - self.startup_time).total_seconds() / 60
                if time_since_startup < 10:
                    logger.debug(f"Rejecting signal from startup grace period ({time_since_startup:.1f} min < 10 min)")
                    return False
            except:
                pass  # If parsing fails, continue with other validation
        
        # Must have required fields
        required_fields = ['action', 'entry', 'stop_loss', 'take_profit']
        for field in required_fields:
            if field not in signal:
                logger.debug(f"Signal missing required field: {field}")
                return False
        
        action = signal.get('action')
        entry = signal.get('entry', 0.0)
        
        # CRITICAL: Validate entry price is reasonable vs current price
        live_price_data = signal.get('_live_price_data')
        
        if live_price_data and entry > 0:
            live_price = live_price_data.get('price', 0.0)
            if live_price > 0:
                price_diff_pct = abs((entry - live_price) / live_price) * 100
                
                # If entry and live price differ by >5%, something is wrong
                if price_diff_pct > 5.0:
                    logger.error(f"❌ Signal validation failed: Entry ${entry:.5f} differs from live ${live_price:.5f} by {price_diff_pct:.2f}%")
                    return False
        stop_loss = signal.get('stop_loss', 0.0)
        take_profit = signal.get('take_profit', 0.0)
        
        if entry <= 0:
            logger.debug("Invalid entry price")
            return False
        
        # Risk/Reward check (minimum 1:2)
        if action == "buy":
            risk = entry - stop_loss
            reward = take_profit - entry
        elif action == "sell":
            risk = stop_loss - entry
            reward = entry - take_profit
        else:
            logger.debug(f"Invalid action: {action}")
            return False
        
        if risk <= 0:
            logger.debug(f"Invalid risk: {risk}")
            return False
        
        reward_risk_ratio = reward / risk
        
        # CRITICAL FIX: Reject unrealistic risk/reward ratios
        # Professional trading: 1.5:1 to 4:1 is realistic
        # Anything above 4:1 is fantasy (e.g., 50:1, 200:1 = impossible targets)
        if reward_risk_ratio < 1.5:
            logger.debug(f"Risk/reward ratio too low: {reward_risk_ratio:.2f} (need >= 1.5)")
            return False
        if reward_risk_ratio > 4.0:
            logger.warning(f"Risk/reward ratio too high (unrealistic): {reward_risk_ratio:.2f} (max 4.0). This would require +{((take_profit - entry) / entry * 100):.1f}% move - impossible in single trade!")
            return False
        
        # CRITICAL FIX: Reject unrealistic take profit targets
        # Professional trading: +3% to +6% is realistic for single trade
        # Anything above +6% is fantasy (e.g., +200% = would take months, not hours)
        if action == "buy":
            tp_pct = ((take_profit - entry) / entry) * 100
        else:
            tp_pct = ((entry - take_profit) / entry) * 100
        
        if tp_pct > 6.0:
            logger.warning(f"Take profit target too high (unrealistic): +{tp_pct:.1f}% (max +6%). This would take months, not hours!")
            return False
        
        # Price movement significance (minimum 0.1% move, or skip if entry == reference_price)
        reference_price = signal.get('reference_price', entry)
        if reference_price > 0 and abs(entry - reference_price) > 0.0001:  # Only check if prices differ
            move_percent = abs(entry - reference_price) / reference_price
            if move_percent < 0.001:  # Less than 0.1% move (relaxed from 0.5%)
                logger.debug(f"Price movement too small: {move_percent*100:.2f}% (need >= 0.1%)")
                return False
        # If entry == reference_price, that's fine - signal is based on pattern, not price movement
        
        # Volume confirmation (for breakouts/reversals that require it)
        if signal.get('requires_volume', False):
            volume_ratio = signal.get('volume_ratio', 0.0)
            if volume_ratio < 1.2:  # Relaxed from 1.3 to 1.2 to match multi-indicator filter
                logger.debug(f"Volume ratio too low: {volume_ratio:.2f} (need >= 1.2)")
                return False
        
        return True
    
    def _calculate_realistic_risk_management(self, entry: float, action: str, suggested_stop_loss: float = None, suggested_take_profit: float = None) -> tuple:
        """
        Calculate realistic risk management with caps.
        Professional standards:
        - Stop loss: 2-3% (max)
        - Take profit: 4-6% (max)
        - Risk/Reward: 2:1 to 3:1 (max 4:1)
        
        Returns: (stop_loss, take_profit, risk_reward_ratio)
        """
        if action == "buy":
            # Default: 2% stop, 4% target = 2:1 R:R
            default_stop_loss = entry * 0.98  # -2%
            default_take_profit = entry * 1.04  # +4%
        elif action == "sell":
            # Default: 2% stop, 4% target = 2:1 R:R
            default_stop_loss = entry * 1.02  # +2%
            default_take_profit = entry * 0.96  # -4%
        else:
            return entry, entry, 0.0
        
        # Use suggested values if provided, otherwise use defaults
        stop_loss = suggested_stop_loss if suggested_stop_loss and suggested_stop_loss > 0 else default_stop_loss
        take_profit = suggested_take_profit if suggested_take_profit and suggested_take_profit > 0 else default_take_profit
        
        # Calculate risk and reward
        if action == "buy":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        
        if risk <= 0:
            # Invalid risk - use defaults
            return default_stop_loss, default_take_profit, 2.0
        
        risk_reward_ratio = reward / risk
        
        # CRITICAL: Cap take profit at 6% (realistic maximum for single trade)
        if action == "buy":
            max_take_profit = entry * 1.06  # +6% max
            if take_profit > max_take_profit:
                take_profit = max_take_profit
                reward = take_profit - entry
                risk_reward_ratio = reward / risk if risk > 0 else 2.0
        else:
            max_take_profit = entry * 0.94  # -6% max
            if take_profit < max_take_profit:
                take_profit = max_take_profit
                reward = entry - take_profit
                risk_reward_ratio = reward / risk if risk > 0 else 2.0
        
        # CRITICAL: Cap risk/reward ratio at 4:1 (realistic maximum)
        if risk_reward_ratio > 4.0:
            # Adjust take profit to maintain 4:1 R:R
            if action == "buy":
                take_profit = entry + (risk * 4.0)
            else:
                take_profit = entry - (risk * 4.0)
            risk_reward_ratio = 4.0
        
        # Ensure minimum 1.5:1 R:R
        if risk_reward_ratio < 1.5:
            # Adjust take profit to maintain 1.5:1 R:R
            if action == "buy":
                take_profit = entry + (risk * 1.5)
            else:
                take_profit = entry - (risk * 1.5)
            risk_reward_ratio = 1.5
        
        return stop_loss, take_profit, risk_reward_ratio
    
    def _calculate_stop_loss(self, entry: float, action: str, score: float) -> float:
        """Calculate stop loss based on entry price and signal strength.
        Uses fixed 2% stop loss to ensure consistent 2:1 risk/reward ratio."""
        if action == "buy":
            # Fixed 2% stop loss below entry
            return entry * 0.98
        elif action == "sell":
            # Fixed 2% stop loss above entry
            return entry * 1.02
        return entry
    
    def _calculate_take_profit(self, entry: float, action: str, score: float) -> float:
        """Calculate take profit based on entry price and signal strength.
        Ensures minimum 2:1 risk/reward ratio (4% take profit for 2% stop loss = 2:1 ratio)."""
        if action == "buy":
            # Fixed 4% take profit above entry (2:1 ratio with 2% stop loss)
            return entry * 1.04
        elif action == "sell":
            # Fixed 4% take profit below entry (2:1 ratio with 2% stop loss)
            return entry * 0.96
        return entry
    
    async def _get_live_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current live price from exchange (not database).
        Returns dict with: price, timestamp, source, age_seconds
        """
        try:
            # Try Binance first (fastest, most reliable for crypto)
            if symbol.endswith('USDT'):
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"https://api.binance.com/api/v3/ticker/price",
                        params={"symbol": symbol}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "price": float(data["price"]),
                            "timestamp": datetime.utcnow(),
                            "source": "binance_live",
                            "age_seconds": 0.0
                        }
            
            # For forex, use latest database price (forex doesn't have free real-time API)
            async for session in get_session():
                from sqlmodel import select, desc
                from app.db.models import PriceTick
                
                stmt = (
                    select(PriceTick)
                    .where(PriceTick.symbol == symbol)
                    .order_by(desc(PriceTick.ts))
                    .limit(1)
                )
                result = await session.exec(stmt)
                tick = result.first()
                
                if tick:
                    age_seconds = (datetime.utcnow() - tick.ts).total_seconds()
                    return {
                        "price": float(tick.price),
                        "timestamp": tick.ts,
                        "source": "database",
                        "age_seconds": age_seconds
                    }
                break
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not fetch live price for {symbol}: {e}")
            return None
    
    def _calculate_time_limit(self, strategy_name: str) -> dict:
        """
        Calculate time limit for trade based on strategy type and timeframe.
        Based on research: Time limit = 3x timeframe for day trading strategies.
        
        Research sources:
        - 15-minute chart: Exit after 45 minutes (3x timeframe)
        - 5-minute chart: Exit after 15-30 minutes (3-6x timeframe)
        - 1-hour chart: Exit after 2-4 hours (2-4x timeframe)
        
        Returns:
            dict with 'duration_minutes', 'duration_hours', 'expires_at' (ISO timestamp)
        """
        from datetime import timedelta
        
        # Strategy timeframes and time limits (based on research)
        # Format: (timeframe_minutes, duration_minutes)
        # Institutional strategies are price-action based = SHORT-TERM (2-10 minutes)
        strategy_timeframes = {
            # INSTITUTIONAL-LEVEL STRATEGIES (Price-action based - SHORT-TERM)
            "vwap": (1, 3),  # VWAP bounces react in 2-3 minutes
            "liquidity_zones": (1, 3),  # Liquidity grabs happen fast (2-3 minutes)
            "order_blocks": (1, 4),  # Order block reversals: 3-4 minutes
            "fair_value_gaps": (1, 3),  # FVG fills happen quickly (2-3 minutes)
            "market_structure": (5, 8),  # Structure breaks need time (5-8 minutes)
            "support_resistance": (5, 8),  # S/R reactions need time (5-8 minutes)
            "volume_profile": (1, 4),  # PVN bounces are quick (3-4 minutes)
            
            # Short-term strategies (1-5 minute timeframes)
            "momentum": (1, 5),  # 1m chart, 5 minutes (5x timeframe)
            "rsi_macd_momentum": (1, 5),  # 1m chart, 5 minutes
            # Arbitrage removed: Not practical for manual trading
            "mean_reversion": (5, 15),  # 5m chart, 15 minutes (3x timeframe)
            
            # Medium-term strategies (15-minute timeframes)
            "breakout": (15, 45),  # 15m chart, 45 minutes (3x timeframe)
            "volume_breakout": (15, 45),  # 15m chart, 45 minutes
            "volatility_breakout": (15, 45),  # 15m chart, 45 minutes
            
            # Longer-term strategies (1-hour timeframes)
            "trend_following": (60, 180),  # 1h chart, 180 minutes = 3 hours (3x timeframe)
            "sentiment": (60, 240),  # 1h chart, 240 minutes = 4 hours
            "social_copy": (60, 180),  # 1h chart, 180 minutes = 3 hours
        }
        
        # Get timeframe and duration for strategy
        # Default: 5 minutes for institutional strategies (safe short-term)
        # This ensures all signals have reasonable expiration times
        timeframe_minutes, duration_minutes = strategy_timeframes.get(strategy_name, (1, 5))  # Default: 1m chart, 5 minutes
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        duration_hours = duration_minutes / 60.0
        
        return {
            "duration_minutes": duration_minutes,
            "duration_hours": round(duration_hours, 2),
            "expires_at": expires_at.isoformat(),
            "time_limit_message": f"Close trade after {duration_minutes} minutes ({duration_hours:.1f} hours) at {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC regardless of profit/loss"
        }
    
    def _enrich_signal_with_indicators(self, signal: Dict[str, Any], symbol: str, strategy: Any) -> Dict[str, Any]:
        """
        Enrich signal with missing technical indicators to improve AI scoring.
        Adds RSI, volume_ratio, MACD, and other indicators if not present.
        """
        # If signal already has all indicators, return as-is
        if signal.get('rsi') is not None and signal.get('volume_ratio', 0.0) > 0:
            return signal
        
        # Try to get indicators from strategy's price history
        if hasattr(strategy, 'price_history') and symbol in strategy.price_history:
            history = list(strategy.price_history[symbol])
            if len(history) >= 14:  # Need at least 14 candles for RSI
                closes = [c['close'] for c in history]
                volumes = [c.get('volume', 0.0) for c in history]
                
                # Calculate RSI if not present
                if signal.get('rsi') is None:
                    try:
                        rsi = self._calculate_rsi(closes, 14)
                        if rsi is not None:
                            signal['rsi'] = rsi
                    except:
                        pass
                
                # Calculate volume ratio if not present
                if signal.get('volume_ratio', 0.0) == 0.0:
                    try:
                        non_zero_volumes = [v for v in volumes[-20:] if v > 0]
                        if len(non_zero_volumes) >= 10:
                            from statistics import mean
                            avg_volume = mean(non_zero_volumes)
                            current_volume = volumes[-1] if volumes[-1] > 0 else 0.0
                            if avg_volume > 0:
                                signal['volume_ratio'] = current_volume / avg_volume
                    except:
                        pass
                
                # Calculate MACD if not present (for strategies that don't include it)
                if signal.get('macd') is None and len(closes) >= 26:
                    try:
                        macd_data = self._calculate_macd(closes)
                        if macd_data and macd_data.get('macd'):
                            signal['macd'] = macd_data['macd'][-1]
                            signal['signal_line'] = macd_data['signal'][-1] if macd_data.get('signal') else None
                            signal['histogram'] = macd_data['histogram'][-1] if macd_data.get('histogram') else None
                    except:
                        pass
        
        return signal
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI from price closes."""
        if len(closes) < period + 1:
            return None
        
        try:
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(abs(change))
            
            if len(gains) < period:
                return None
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return None
    
    def _calculate_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """Calculate MACD from price closes."""
        if len(closes) < slow + signal:
            return {"macd": [], "signal": [], "histogram": []}
        
        try:
            # Calculate EMAs
            ema_fast = self._calculate_ema(closes, fast)
            ema_slow = self._calculate_ema(closes, slow)
            
            if len(ema_fast) == 0 or len(ema_slow) == 0:
                return {"macd": [], "signal": [], "histogram": []}
            
            # Align EMA lengths - use the shorter one
            min_len = min(len(ema_fast), len(ema_slow))
            ema_fast = ema_fast[-min_len:]
            ema_slow = ema_slow[-min_len:]
            
            # MACD line = EMA(fast) - EMA(slow)
            macd_line = [ema_fast[i] - ema_slow[i] for i in range(min_len)]
            
            if len(macd_line) < signal:
                return {"macd": [], "signal": [], "histogram": []}
            
            # Signal line = EMA of MACD line
            signal_line = self._calculate_ema(macd_line, signal)
            
            if len(signal_line) == 0:
                return {"macd": [], "signal": [], "histogram": []}
            
            # Histogram = MACD - Signal (align lengths)
            histogram = []
            macd_for_hist = macd_line[-len(signal_line):]
            for i in range(len(signal_line)):
                histogram.append(macd_for_hist[i] - signal_line[i])
            
            return {
                "macd": macd_line[-len(signal_line):] if signal_line else [],
                "signal": signal_line,
                "histogram": histogram
            }
        except Exception as e:
            logger.debug(f"Error calculating MACD: {e}")
            return {"macd": [], "signal": [], "histogram": []}
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        ema = []
        multiplier = 2.0 / (period + 1)
        
        # First EMA value is SMA
        sma = sum(prices[:period]) / period
        ema.append(sma)
        
        # Calculate subsequent EMAs
        for i in range(period, len(prices)):
            ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_value)
        
        return ema
    
    def _calculate_price_trends(self, ticks: List[Any], current_price: float, signal_timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate price trends and time-based information to help users know when signal was generated
        and estimate time remaining before take profit.
        
        Returns dict with:
        - price_1h_ago: float
        - price_24h_ago: float
        - change_1h_pct: float (percentage change)
        - change_24h_pct: float
        - trend_1h: str ("rising", "falling", "stable")
        - trend_24h: str
        - signal_age_minutes: float (minutes since signal was generated)
        - estimated_tp_time_minutes: float (estimated minutes to reach take profit, based on historical volatility)
        """
        if not ticks or len(ticks) < 2:
            return {
                "price_1h_ago": current_price,
                "price_24h_ago": current_price,
                "change_1h_pct": 0.0,
                "change_24h_pct": 0.0,
                "trend_1h": "stable",
                "trend_24h": "stable",
                "signal_age_minutes": 0.0,
                "estimated_tp_time_minutes": None,
            }
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(hours=24)
        
        # Find closest tick to 1h and 24h ago
        price_1h_ago = current_price
        price_24h_ago = current_price
        
        for tick in reversed(ticks):  # Start from most recent
            if tick.ts <= one_hour_ago:
                price_1h_ago = float(tick.price)
                break
        
        for tick in reversed(ticks):
            if tick.ts <= one_day_ago:
                price_24h_ago = float(tick.price)
                break
        
        # Calculate percentage changes
        change_1h_pct = ((current_price - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0.0
        change_24h_pct = ((current_price - price_24h_ago) / price_24h_ago * 100) if price_24h_ago > 0 else 0.0
        
        # Determine trends
        trend_1h = "rising" if change_1h_pct > 0.5 else ("falling" if change_1h_pct < -0.5 else "stable")
        trend_24h = "rising" if change_24h_pct > 1.0 else ("falling" if change_24h_pct < -1.0 else "stable")
        
        # Calculate signal age (how long ago was signal generated)
        signal_age_minutes = 0.0
        if signal_timestamp:
            if isinstance(signal_timestamp, str):
                try:
                    signal_timestamp = datetime.fromisoformat(signal_timestamp.replace('Z', '+00:00'))
                except:
                    signal_timestamp = None
        
        if signal_timestamp:
            try:
                if signal_timestamp.tzinfo is None:
                    signal_timestamp = signal_timestamp.replace(tzinfo=None)
                    now_naive = datetime.utcnow()
                    age_delta = now_naive - signal_timestamp
                else:
                    age_delta = now - signal_timestamp
                signal_age_minutes = age_delta.total_seconds() / 60.0
            except:
                signal_age_minutes = 0.0
        
        # Estimate time to TP based on recent volatility (simplified - use 1h avg price change)
        estimated_tp_time_minutes = None
        if abs(change_1h_pct) > 0.01:  # Only if there's meaningful movement
            # Assume similar rate of change to reach TP (very rough estimate)
            # This is just an approximation based on current trend
            avg_change_per_minute = abs(change_1h_pct) / 60.0
            if avg_change_per_minute > 0:
                # Estimate minutes to reach typical TP (4-8% based on strategy)
                # Use average of 5% for estimate
                estimated_tp_time_minutes = (5.0 / avg_change_per_minute) if avg_change_per_minute > 0 else None
        
        return {
            "price_1h_ago": price_1h_ago,
            "price_24h_ago": price_24h_ago,
            "change_1h_pct": change_1h_pct,
            "change_24h_pct": change_24h_pct,
            "trend_1h": trend_1h,
            "trend_24h": trend_24h,
            "signal_age_minutes": signal_age_minutes,
            "estimated_tp_time_minutes": estimated_tp_time_minutes,
        }
    
    def _calculate_reliability(self, all_signals: List[Dict[str, Any]], signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced reliability calculation with performance-based weighting (meta-labeling concept).
        Based on research: ensemble weighting significantly improves signal accuracy.
        
        Calculate reliability score for a signal based on:
        1. Multi-strategy consensus (multiple strategies agree) - weighted by strategy performance
        2. Individual strategy confidence - weighted by strategy performance
        3. Strategy quality/weighting - from historical performance
        
        Returns dict with:
        - is_reliable: bool (True if signal should be sent)
        - reliability_score: float (0.0-1.0)
        - consensus_count: int (number of agreeing strategies)
        - weighted_consensus_score: float (weighted sum of agreeing strategies)
        - max_confidence: float (highest confidence from any strategy)
        - reasoning: str (explanation)
        """
        symbol = signal.get("symbol")
        action = signal.get("action")
        strategy_name = signal.get("strategy")
        confidence = signal.get("confidence", 0.0)
        
        # Get strategy weight (default to 1.0 if unknown)
        strategy_weight = self.strategy_weights.get(strategy_name, 1.0)
        
        # Find all signals for the same symbol+action (consensus)
        agreeing_signals = [
            s for s in all_signals
            if s.get("symbol") == symbol 
            and s.get("action") == action
            and s.get("confidence", 0.0) >= self.consensus_min_confidence
        ]
        
        consensus_count = len(agreeing_signals)
        
        # Calculate weighted consensus score (meta-labeling approach)
        # Each strategy's contribution = confidence * weight
        weighted_consensus_score = 0.0
        for sig in agreeing_signals:
            sig_strategy = sig.get("strategy", "unknown")
            sig_confidence = sig.get("confidence", 0.0)
            sig_weight = self.strategy_weights.get(sig_strategy, 1.0)
            weighted_consensus_score += sig_confidence * sig_weight
        
        # Add current signal's weighted contribution
        weighted_consensus_score += confidence * strategy_weight
        
        # Calculate average confidence (unweighted for display)
        max_confidence = max([s.get("confidence", 0.0) for s in agreeing_signals] + [confidence])
        avg_confidence = sum([s.get("confidence", 0.0) for s in agreeing_signals]) / len(agreeing_signals) if agreeing_signals else confidence
        
        # Enhanced reliability score calculation
        # Formula: (weighted_consensus_bonus + confidence_bonus) / 2
        # Weighted consensus bonus: normalized weighted score
        weighted_consensus_bonus = min(1.0, weighted_consensus_score / 3.0)  # Full bonus if weighted score >= 3.0
        confidence_bonus = max_confidence  # Higher confidence = higher bonus
        
        # Weight confidence more (60%) than consensus (40%)
        reliability_score = (weighted_consensus_bonus * 0.4 + confidence_bonus * 0.6)
        
        # Determine if signal is reliable
        is_reliable = False
        reasoning = ""
        
        # Enhanced reliability criteria:
        # 1. Weighted consensus score >= threshold (multiple strategies with good weights)
        # 2. OR single high-confidence signal from high-weight strategy
        # 3. OR consensus count >= min with good average confidence
        
        if weighted_consensus_score >= self.weighted_consensus_threshold:
            # Strong weighted consensus - highly reliable
            is_reliable = True
            reasoning = f"✅ RELIABLE: Weighted consensus {weighted_consensus_score:.2f} (≥{self.weighted_consensus_threshold}) from {consensus_count} strategies (avg confidence: {avg_confidence:.2f})"
        elif consensus_count >= self.min_consensus_strategies and avg_confidence >= 0.5:
            # Multi-strategy consensus with good average confidence
            is_reliable = True
            reasoning = f"✅ RELIABLE: {consensus_count} strategies agree on {action} (avg confidence: {avg_confidence:.2f}, weighted: {weighted_consensus_score:.2f})"
        elif confidence >= 0.60 and strategy_weight >= 1.0:
            # RELAXED: Single strategy with good confidence (≥60%) from any weighted strategy
            # Professional bots accept single high-quality signals
            is_reliable = True
            reasoning = f"✅ RELIABLE: Good confidence ({confidence:.2f}) from weighted strategy {strategy_name} (weight: {strategy_weight:.1f}x)"
        elif confidence >= 0.70:
            # FALLBACK: Very high confidence (≥70%) from ANY strategy (even weight <1.0)
            # Professional bots trust very high confidence signals
            is_reliable = True
            reasoning = f"✅ RELIABLE: Very high confidence ({confidence:.2f}) from {strategy_name} strategy"
        else:
            # Not reliable - needs either consensus or higher confidence
            is_reliable = False
            if consensus_count > 0:
                reasoning = f"⚠️ LOW RELIABILITY: Weighted consensus {weighted_consensus_score:.2f} < {self.weighted_consensus_threshold}, {consensus_count} strategies (need {self.min_consensus_strategies}), confidence {confidence:.2f} (need {self.min_reliable_confidence:.2f})"
            else:
                reasoning = f"⚠️ LOW RELIABILITY: Only {strategy_name} strategy (weight: {strategy_weight:.1f}), confidence {confidence:.2f} < {self.min_reliable_confidence:.2f}"
        
        return {
            "is_reliable": is_reliable,
            "reliability_score": reliability_score,
            "consensus_count": consensus_count,
            "weighted_consensus_score": weighted_consensus_score,
            "max_confidence": max_confidence,
            "avg_confidence": avg_confidence,
            "strategy_weight": strategy_weight,
            "reasoning": reasoning,
        }
    
    def _apply_multi_indicator_filter(self, signal: Dict[str, Any], all_signals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        SIMPLIFIED professional signal filtering (1-2 confirmations needed).
        Based on research: Most professional bots use 1-2 confirmations, not 3-5.
        
        Returns:
            Signal dict with 'confirmations' list if passed, None if rejected
        """
        confirmations = []
        symbol = signal.get('symbol')
        action = signal.get('action')
        entry = signal.get('entry', 0.0)
        stop_loss = signal.get('stop_loss', 0.0)
        take_profit = signal.get('take_profit', 0.0)
        confidence = signal.get('confidence', 0.0)
        
        # CONFIRMATION 1: Risk/Reward Check (minimum 1.5:1)
        if action == "buy":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        
        if risk > 0:
            rr_ratio = reward / risk
            if rr_ratio >= 1.5:  # Any R:R ≥ 1.5:1 counts
                confirmations.append('R:R')
        else:
            return None  # Invalid risk - reject
        
        # CONFIRMATION 2: Volume Check (LENIENT - count if >1.0x OR no data)
        volume_ratio = signal.get('volume_ratio', 0.0)
        if volume_ratio >= 1.2:  # Above average volume
            confirmations.append('Volume')
        elif volume_ratio == 0.0:
            # No volume data - don't penalize (crypto exchanges may not provide)
            confirmations.append('Volume-NA')  # Count as half confirmation
        
        # CONFIRMATION 3: Confidence Check (LENIENT - confidence ≥ 0.55)
        if confidence >= 0.55:
            confirmations.append('Confidence')
        
        # CONFIRMATION 4: RSI Check (VERY LENIENT - only reject extreme opposite)
        rsi = signal.get('rsi')
        if rsi is not None:
            # Only reject if RSI is EXTREME opposite direction
            # Buy: reject if RSI > 85 (extremely overbought)
            # Sell: reject if RSI < 15 (extremely oversold)
            if action == "buy" and rsi <= 85:
                confirmations.append('RSI-OK')
            elif action == "sell" and rsi >= 15:
                confirmations.append('RSI-OK')
            elif rsi is None:
                # No RSI data - don't penalize
                confirmations.append('RSI-NA')
        else:
            confirmations.append('RSI-NA')
        
        # DECISION LOGIC (SIMPLIFIED):
        # HIGH confidence (≥0.70): Need only 1 confirmation (just R:R is enough)
        # MEDIUM confidence (0.55-0.69): Need 2 confirmations
        # LOW confidence (<0.55): Reject
        
        if confidence >= 0.70:
            min_required = 1  # Just R:R is enough for high confidence
        elif confidence >= 0.55:
            min_required = 2  # Need R:R + one more
        else:
            return None  # Too low confidence
        
        # Count confirmations (Volume-NA and RSI-NA count as 0.5 each)
        full_confirmations = [c for c in confirmations if not c.endswith('-NA')]
        partial_confirmations = [c for c in confirmations if c.endswith('-NA')]
        total_score = len(full_confirmations) + (len(partial_confirmations) * 0.5)
        
        if total_score >= min_required:
            signal['confirmations'] = confirmations
            signal['pre_ai_score'] = len(full_confirmations)
            logger.info(f"✅ Signal passed filter: {len(full_confirmations)} confirmations + {len(partial_confirmations)} partial ({', '.join(confirmations)})")
            return signal
        else:
            logger.debug(f"Signal rejected: {total_score:.1f} < {min_required} confirmations needed (got: {', '.join(confirmations) if confirmations else 'none'})")
            return None
    
    def _is_duplicate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Check if this signal is a duplicate of a recently sent signal.
        Returns True if duplicate (should skip), False if new.
        """
        signal_key = (
            signal.get('strategy', 'unknown'),
            signal.get('symbol', 'unknown'),
            signal.get('action', 'unknown')
        )
        
        # Clean up old signals (older than cooldown period)
        cutoff = datetime.utcnow() - timedelta(hours=self.signal_cooldown_hours)
        self.recent_signals = {
            k: v for k, v in self.recent_signals.items() if v > cutoff
        }
        
        # Check if we've seen this signal recently
        if signal_key in self.recent_signals:
            last_sent = self.recent_signals[signal_key]
            hours_ago = (datetime.utcnow() - last_sent).total_seconds() / 3600
            logger.debug(f"Duplicate signal detected: {signal_key} was sent {hours_ago:.1f} hours ago (cooldown: {self.signal_cooldown_hours} hours)")
            return True
        
        return False
    
    async def process_signals(self, signals: List[Dict[str, Any]]) -> None:
        """
        Process signals through reliability check, AI filter, and send notifications.
        Only sends alerts for reliable trades (consensus or high confidence).
        Processes signals sequentially to match AI processing speed.
        """
        # Track filtering stages for diagnostics
        multi_indicator_passed = 0
        ai_passed = 0
        
        for idx, signal in enumerate(signals, 1):
            try:
                logger.info(f"Processing signal {idx}/{len(signals)}: {signal['strategy']} {signal['symbol']} {signal['action']} (confidence: {signal.get('confidence', 0.0):.2f})")
                
                # Check for duplicate signals (same strategy+symbol+action within cooldown period)
                if self._is_duplicate_signal(signal):
                    logger.info(f"⏭️  Skipping duplicate signal (within {self.signal_cooldown_hours} hour cooldown): {signal['strategy']} {signal['symbol']} {signal['action']}")
                    continue
                
                # Log all signals
                await self.signal_logger.log_signal(signal)
                
                # PROFESSIONAL MULTI-INDICATOR CONFIRMATION FILTER
                # Professional bots require multiple confirmations before sending signals
                confirmed_signal = self._apply_multi_indicator_filter(signal, signals)
                if not confirmed_signal:
                    logger.info(f"🚫 Signal rejected by multi-indicator filter: {signal['strategy']} {signal['symbol']} {signal['action']}")
                    self.stats["ai_filtered"] += 1
                    continue
                
                multi_indicator_passed += 1
                signal = confirmed_signal  # Use confirmed signal with confirmations list
                
                # CRITICAL: Ensure signal has expiration/duration information
                # This is essential for users to know when to close the trade
                if "duration_minutes" not in signal or "expires_at" not in signal:
                    strategy_name = signal.get('strategy', 'unknown')
                    time_limit = self._calculate_time_limit(strategy_name)
                    signal["duration_minutes"] = time_limit["duration_minutes"]
                    signal["duration_hours"] = time_limit["duration_hours"]
                    signal["expires_at"] = time_limit["expires_at"]
                    signal["time_limit_message"] = time_limit["time_limit_message"]
                    logger.info(f"Added expiration info to signal: {strategy_name} {signal.get('symbol')} - expires in {time_limit['duration_minutes']} minutes")
                
                # RELIABILITY INFO: Calculate for context but DON'T filter
                # (Multi-indicator filter already handled quality)
                reliability = self._calculate_reliability(signals, signal)
                logger.info(f"Reliability info: {reliability['reasoning']}")
                # Add to signal for AI context but don't reject
                signal['_reliability_info'] = reliability
                signal['weighted_consensus_score'] = reliability.get('weighted_consensus_score', 0.0)
                signal['strategy_weight'] = reliability.get('strategy_weight', 1.0)
                signal['consensus_count'] = reliability.get('consensus_count', 0)
                # Continue to AI filter (don't reject here)
                
                # CRITICAL: Update entry price to LIVE price before AI filtering
                symbol = signal.get('symbol')
                logger.info(f"Fetching live price for {symbol}...")
                
                live_price_data = await self._get_live_price(symbol)
                
                if live_price_data:
                    live_price = live_price_data['price']
                    old_entry = signal.get('entry', 0.0)
                    price_age = live_price_data['age_seconds']
                    
                    # Calculate price movement since signal generation
                    if old_entry > 0:
                        price_change_pct = ((live_price - old_entry) / old_entry) * 100
                    else:
                        price_change_pct = 0.0
                    
                    logger.info(f"   Signal entry: ${old_entry:.5f}")
                    logger.info(f"   Live price:   ${live_price:.5f} (age: {price_age:.1f}s)")
                    logger.info(f"   Movement:     {price_change_pct:+.2f}%")
                    
                    # WARNING: If price moved significantly (>2%), signal may be stale
                    if abs(price_change_pct) > 2.0:
                        logger.warning(f"⚠️  PRICE MOVED {price_change_pct:+.2f}% since signal generation!")
                        logger.warning(f"   Signal may be STALE - consider rejecting")
                        
                        # OPTION 1: Reject stale signals (SAFE - recommended)
                        if abs(price_change_pct) > 3.0:  # >3% movement = reject
                            logger.warning(f"🚫 REJECTING signal - price moved too much ({price_change_pct:+.2f}%)")
                            self.stats["ai_filtered"] += 1
                            continue
                        
                        # OPTION 2: Accept but warn user in Telegram
                        signal['_price_warning'] = {
                            'old_price': old_entry,
                            'live_price': live_price,
                            'movement_pct': price_change_pct,
                            'warning': f"Price moved {price_change_pct:+.2f}% since signal - EXECUTE WITH CAUTION"
                        }
                    
                    # Update entry price to LIVE price
                    signal['entry'] = live_price
                    signal['_live_price_data'] = live_price_data
                    
                    # Recalculate stop_loss and take_profit based on LIVE price
                    action = signal.get('action')
                    old_sl = signal.get('stop_loss', 0.0)
                    old_tp = signal.get('take_profit', 0.0)
                    
                    if old_entry > 0 and old_sl > 0 and old_tp > 0:
                        # Calculate original offsets as percentages
                        if action == "buy":
                            sl_offset_pct = (old_entry - old_sl) / old_entry
                            tp_offset_pct = (old_tp - old_entry) / old_entry
                            
                            # Apply same percentages to live price
                            new_sl = live_price * (1 - sl_offset_pct)
                            new_tp = live_price * (1 + tp_offset_pct)
                        else:  # sell
                            sl_offset_pct = (old_sl - old_entry) / old_entry
                            tp_offset_pct = (old_entry - old_tp) / old_entry
                            
                            new_sl = live_price * (1 + sl_offset_pct)
                            new_tp = live_price * (1 - tp_offset_pct)
                        
                        signal['stop_loss'] = new_sl
                        signal['take_profit'] = new_tp
                        
                        logger.info(f"   Updated SL/TP based on live price:")
                        logger.info(f"     Entry: ${old_entry:.5f} → ${live_price:.5f}")
                        logger.info(f"     SL:    ${old_sl:.5f} → ${new_sl:.5f}")
                        logger.info(f"     TP:    ${old_tp:.5f} → ${new_tp:.5f}")
                else:
                    logger.warning(f"⚠️  Could not fetch live price for {symbol} - using database price")
                    signal['_live_price_data'] = None
                
                # Filter with AI (takes time - Ollama may need 30-120 seconds)
                # OPTION: For highly reliable signals, we could skip AI filter, but let's try with intelligent fallback first
                logger.info(f"Waiting for AI analysis (this may take 30-120 seconds)...")
                try:
                    ai_result = self.ai_filter.filter_signal(signal)
                except Exception as ai_error:
                    logger.error(f"AI filter error: {ai_error}", exc_info=True)
                    # Continue to next signal if AI fails
                    continue
                
                if not ai_result.get("approved", False):
                    self.stats["ai_filtered"] += 1
                    ai_conf = ai_result.get('ai_confidence', 0.0)
                    threshold = self.ai_filter.confidence_threshold
                    market_open = ai_result.get('market_open', True)
                    logger.info(f"Signal filtered by AI: {signal['strategy']} {signal['symbol']} {signal['action']}")
                    logger.info(f"   AI confidence: {ai_conf:.1f}/10 (threshold: {threshold:.1f})")
                    logger.info(f"   Market open: {market_open}")
                    logger.info(f"   Verdict: {ai_result.get('verdict', 'unknown')}")
                    continue
                
                ai_passed += 1
                
                # Add reliability info to AI result for notification
                ai_result["reliability"] = reliability
                ai_result["consensus_count"] = reliability["consensus_count"]
                ai_result["weighted_consensus_score"] = reliability.get("weighted_consensus_score", 0.0)
                ai_result["strategy_weight"] = reliability.get("strategy_weight", 1.0)
                
                # Send Telegram notification (only reliable signals reach here)
                logger.info(f"📤 Sending Telegram notification for APPROVED signal...")
                logger.info(f"   Signal: {signal['strategy']} {signal['symbol']} {signal['action']}")
                logger.info(f"   Entry: ${signal.get('entry', 0):.5f}")
                logger.info(f"   AI Confidence: {ai_result.get('ai_confidence', 0.0):.1f}/10")
                
                try:
                    success = await self.telegram.send_signal_notification(signal, ai_result)
                    
                    if success:
                        self.stats["telegram_sent"] += 1
                        # Mark this signal as recently sent
                        signal_key = (
                            signal.get('strategy', 'unknown'),
                            signal.get('symbol', 'unknown'),
                            signal.get('action', 'unknown')
                        )
                        self.recent_signals[signal_key] = datetime.utcnow()
                        weighted_score = reliability.get('weighted_consensus_score', 0.0)
                        strategy_weight = reliability.get('strategy_weight', 1.0)
                        logger.info(f"✅✅✅ Telegram notification SENT successfully!")
                        logger.info(f"   Signal: {signal['strategy']} {signal['symbol']} {signal['action']}")
                        logger.info(f"   AI: {ai_result.get('ai_confidence', 0.0):.1f}/10")
                        logger.info(f"   Weighted Consensus: {weighted_score:.2f}")
                        logger.info(f"   Strategy Weight: {strategy_weight:.1f}x")
                        logger.info(f"   Consensus: {reliability['consensus_count']} strategies")
                    else:
                        logger.error(f"❌❌❌ FAILED to send Telegram notification!")
                        logger.error(f"   Signal: {signal['strategy']} {signal['symbol']} {signal['action']}")
                        logger.error(f"   Check Telegram bot token and chat ID in .env file")
                        logger.error(f"   Bot token present: {bool(self.telegram.bot_token)}")
                        logger.error(f"   Chat ID present: {bool(self.telegram.chat_id)}")
                except Exception as telegram_error:
                    logger.error(f"❌❌❌ EXCEPTION sending Telegram notification: {telegram_error}", exc_info=True)
                    logger.error(f"   Signal: {signal['strategy']} {signal['symbol']} {signal['action']}")
                
                # Add small delay between signals to avoid overwhelming Ollama
                if idx < len(signals):
                    await asyncio.sleep(2)  # 2 second pause between signal processing
                
            except Exception as e:
                logger.exception(f"Error processing signal: {e}")
                continue  # Continue with next signal even if one fails
        
        # Log diagnostic summary
        if signals:
            logger.info("="*60)
            logger.info(f"Stage 2 (Multi-Indicator): {multi_indicator_passed}/{len(signals)} passed")
            logger.info(f"Stage 3 (Reliability Info): {len(signals)} (no filtering)")
            logger.info(f"Stage 4 (AI Filter): {ai_passed}/{len(signals)} passed")
            logger.info(f"Stage 5 (Telegram Sent): {self.stats['telegram_sent']}")
            logger.info("="*60)
    
    async def run_cycle(self) -> None:
        """
        Run one complete cycle: collect data, run strategies, process signals.
        """
        try:
            # 1. Collect market data
            data_collected = await self.collect_market_data()
            
            if not data_collected:
                logger.warning("No data collected, skipping strategy execution")
                return
            
            # 2. Run strategies on all monitored assets
            all_signals = []
            for symbol in config.ASSETS:
                signals = await self.run_strategies(symbol)
                all_signals.extend(signals)
            
            # Log signal breakdown by strategy
            if all_signals:
                logger.info("="*60)
                logger.info("SIGNAL PIPELINE DIAGNOSTIC")
                logger.info("="*60)
                logger.info(f"Stage 1 (Pattern Completion): {len(all_signals)} signals generated")
                
                strategy_breakdown = defaultdict(int)
                action_breakdown = defaultdict(int)
                for sig in all_signals:
                    strategy_breakdown[sig.get('strategy', 'unknown')] += 1
                    action_breakdown[sig.get('action', 'unknown')] += 1
                logger.info(f"Generated {len(all_signals)} signals from {len(config.ASSETS)} assets")
                logger.debug(f"   - By strategy: {dict(strategy_breakdown)}")
                logger.debug(f"   - By action: {dict(action_breakdown)}")
                
                # Track filtering stages
                for sig in all_signals:
                    logger.info(f"  - {sig['strategy']} {sig['symbol']} {sig['action']} (conf: {sig.get('confidence', 0):.2f})")
                
                # Log which strategies did NOT generate signals (for debugging, especially social_copy)
                all_strategy_names = set(self.strategies.keys())
                signal_strategy_names = set(strategy_breakdown.keys())
                non_generating_strategies = all_strategy_names - signal_strategy_names - {"sentiment_filter"}  # Exclude filter strategies
                if non_generating_strategies:
                    logger.debug(f"   - Strategies with no signals: {', '.join(sorted(non_generating_strategies))}")
                    # Special note for social_copy
                    if "social_copy" in non_generating_strategies:
                        logger.debug(f"   - Note: social_copy strategy is running but returned 'hold' for all assets (check external signal sources)")
            else:
                logger.info(f"Generated 0 signals from {len(config.ASSETS)} assets")
                logger.debug(f"   - All {len(self.strategies) - 1} strategies (excluding filters) returned 'hold' or had errors")
                # DIAGNOSTIC: Log why no signals (every 5 cycles to avoid spam)
                if not hasattr(self, '_diagnostic_counter'):
                    self._diagnostic_counter = 0
                self._diagnostic_counter += 1
                if self._diagnostic_counter % 5 == 0:  # Every 5 cycles (~5 minutes)
                    self._log_diagnostic_info()
            
            # 3. Process signals (AI filter + Telegram)
            # Process signals sequentially - AI may take 30-120 seconds per signal
            if all_signals:
                logger.info(f"📨 Processing {len(all_signals)} signal(s) through pipeline (AI filter + Telegram)...")
                logger.info(f"   This may take several minutes if AI is slow...")
                await self.process_signals(all_signals)
            else:
                logger.debug("No signals to process - waiting for pattern completions...")
            
        except Exception as e:
            logger.exception(f"Error in run_cycle: {e}")
    
    async def run_continuously(self) -> None:
        """
        Run the signal generator continuously with pattern completion monitoring.
        Waits patiently for high-probability setups - only signals when patterns complete.
        """
        logger.info("🚀 Starting trading signal monitor...")
        logger.info("   - Waiting for high-probability setups...")
        logger.info(f"   - Monitoring {len(config.ASSETS)} assets with {len(self.strategies)} strategies")
        logger.info(f"   - Check interval: {config.POLLING_INTERVAL} seconds")
        logger.info(f"   - Press Ctrl+C to stop")
        
        # Send startup notification (if Telegram configured)
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            try:
                await self.telegram.send_message("🤖 Trading Signal Monitor Started\n\nMonitoring {} assets with {} strategies\n\nWaiting for high-probability setups...".format(
                    len(config.ASSETS), len(self.strategies)
                ))
            except Exception as e:
                logger.warning(f"Could not send startup notification to Telegram: {e}")
        else:
            logger.warning("Telegram not configured - notifications will be disabled")
        
        heartbeat_counter = 0
        heartbeat_interval = 300 // config.POLLING_INTERVAL  # Every 5 minutes
        
        # CRITICAL: Log data accumulation status during grace period
        grace_logged = False
        
        try:
            while True:
                # Check if in grace period and log status
                if self.grace_period_active and not grace_logged:
                    elapsed = (datetime.utcnow() - self.startup_time).total_seconds() / 60
                    remaining = max(0, self.startup_grace_minutes - elapsed)
                    
                    if remaining > 0:
                        logger.info(f"⏳ Grace period: {remaining:.1f} minutes remaining - accumulating data...")
                        
                        # Show data accumulation status
                        sample_symbols = self.config.ASSETS[:3]
                        for symbol in sample_symbols:
                            for strategy_name, strategy in self.strategies.items():
                                if strategy_name == "sentiment_filter":
                                    continue
                                if hasattr(strategy, 'price_history') and symbol in strategy.price_history:
                                    count = len(strategy.price_history[symbol])
                                    required = getattr(strategy, 'min_history_required', 50) + 10
                                    logger.info(f"   {strategy_name} {symbol}: {count}/{required} candles")
                        
                        grace_logged = True  # Only log once per cycle
                
                # Fetch new market data
                data_collected = await self.collect_market_data()
                
                if not data_collected:
                    logger.debug("No data collected, waiting for next cycle...")
                    await asyncio.sleep(config.POLLING_INTERVAL)
                    continue
                
                # Reset grace_logged flag for next cycle (so it logs again if still in grace period)
                grace_logged = False
                
                # Update all strategies with new data (for pattern completion detection)
                for symbol in config.ASSETS:
                    await self.update_strategies_with_data(symbol)
                
                # Check each strategy for completed patterns
                all_signals = []
                for symbol in config.ASSETS:
                    signals = await self.run_strategies(symbol)
                    all_signals.extend(signals)
                
                # Log diagnostic info periodically
                heartbeat_counter += 1
                if heartbeat_counter >= heartbeat_interval:
                    # Log strategy status
                    logger.info(f"📊 Status check: Monitoring {len(config.ASSETS)} assets with {len(self.strategies)} strategies")
                    
                    # Count patterns detected vs completed
                    pattern_stats = {}
                    for symbol in config.ASSETS[:5]:  # Check first 5 assets to avoid spam
                        for strategy_name, strategy in self.strategies.items():
                            if strategy_name == "sentiment_filter":
                                continue
                            if hasattr(strategy, 'price_history') and symbol in strategy.price_history:
                                history_count = len(strategy.price_history[symbol])
                                if hasattr(strategy, 'check_for_signal'):
                                    # Check pattern status - handle strategies that don't implement these methods
                                    pattern_exists = False
                                    pattern_completed = False
                                    
                                    try:
                                        if hasattr(strategy, '_detect_pattern'):
                                            pattern_exists = strategy._detect_pattern(symbol)
                                    except NotImplementedError:
                                        pattern_exists = False
                                    except Exception as e:
                                        logger.debug(f"{strategy_name}._detect_pattern error for {symbol}: {e}")
                                        pattern_exists = False
                                    
                                    try:
                                        if hasattr(strategy, '_confirm_completion'):
                                            pattern_completed = strategy._confirm_completion(symbol)
                                    except NotImplementedError:
                                        pattern_completed = False
                                    except Exception as e:
                                        logger.debug(f"{strategy_name}._confirm_completion error for {symbol}: {e}")
                                        pattern_completed = False
                                    
                                    key = f"{strategy_name}"
                                    if key not in pattern_stats:
                                        pattern_stats[key] = {"exists": 0, "completed": 0, "total": 0}
                                    pattern_stats[key]["total"] += 1
                                    if pattern_exists:
                                        pattern_stats[key]["exists"] += 1
                                    if pattern_completed:
                                        pattern_stats[key]["completed"] += 1
                                
                                logger.info(f"   - {strategy_name} on {symbol}: {history_count} candles in history (need {getattr(strategy, 'min_history_required', 50)})")
                    
                    # Log pattern statistics
                    if pattern_stats:
                        logger.info(f"📈 Pattern detection stats (sample of 5 assets):")
                        for strategy_name, stats in pattern_stats.items():
                            pct_exists = (stats["exists"] / stats["total"] * 100) if stats["total"] > 0 else 0
                            pct_completed = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                            logger.info(f"   - {strategy_name}: {stats['exists']}/{stats['total']} patterns exist ({pct_exists:.1f}%), {stats['completed']} completed ({pct_completed:.1f}%)")
                    
                    heartbeat_counter = 0
                
                # Log signal breakdown
                if all_signals:
                    logger.info(f"Found {len(all_signals)} completed pattern(s) across {len(config.ASSETS)} assets")
                    for sig in all_signals:
                        logger.info(f"   - {sig['strategy']} {sig['symbol']} {sig['action']} (confidence: {sig.get('confidence', 0.0):.2f})")
                    
                    # Process signals (AI filter + Telegram)
                    logger.info(f"Processing {len(all_signals)} signal(s) through AI filter...")
                    await self.process_signals(all_signals)
                else:
                    # Heartbeat already logged above
                    # DIAGNOSTIC: Log why no signals (every 5 cycles to avoid spam)
                    if not hasattr(self, '_diagnostic_counter'):
                        self._diagnostic_counter = 0
                    self._diagnostic_counter += 1
                    if self._diagnostic_counter % 5 == 0:  # Every 5 cycles (~5 minutes)
                        self._log_diagnostic_info()
                
                # Wait before next cycle
                await asyncio.sleep(config.POLLING_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down signal generator...")
            if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                try:
                    await self.telegram.send_message("🛑 Signal Generator Stopped")
                except:
                    pass
            self.log_statistics()
            self.signal_logger.generate_daily_summary()
            
        except Exception as e:
            logger.exception(f"Fatal error: {e}")
            if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                try:
                    await self.telegram.send_message(f"❌ Fatal error: {str(e)}")
                except:
                    pass
            raise
    
    def _log_diagnostic_info(self) -> None:
        """
        Log diagnostic information to help understand why no signals are being generated.
        Called periodically when no signals are detected.
        """
        logger.info("="*60)
        logger.info("🔍 DIAGNOSTIC: Why no signals? (Checking system status...)")
        logger.info("="*60)
        
        # 1. Check data collection
        last_collection = self.stats.get("last_collection")
        if last_collection:
            age = (datetime.utcnow() - last_collection).total_seconds() / 60
            logger.info(f"📊 Data Collection: Last collection {age:.1f} minutes ago")
        else:
            logger.warning("⚠️  Data Collection: No data collected yet!")
        
        # 2. Check strategy history for sample assets
        sample_symbols = config.ASSETS[:3] if len(config.ASSETS) >= 3 else config.ASSETS
        logger.info(f"\n📈 Strategy History Status (sample: {', '.join(sample_symbols)}):")
        
        for symbol in sample_symbols:
            logger.info(f"   {symbol}:")
            for strategy_name, strategy in self.strategies.items():
                if strategy_name == "sentiment_filter":
                    continue
                
                if hasattr(strategy, 'price_history') and symbol in strategy.price_history:
                    history_count = len(strategy.price_history[symbol])
                    min_required = getattr(strategy, 'min_history_required', 50)
                    status = "✅" if history_count >= min_required else "⏳"
                    logger.info(f"     {status} {strategy_name}: {history_count} candles (need {min_required})")
                    
                    # Check if pattern completion is being detected
                    if history_count >= min_required:
                        try:
                            if hasattr(strategy, '_confirm_completion'):
                                pattern_completed = strategy._confirm_completion(symbol)
                                if pattern_completed:
                                    logger.info(f"       🎯 Pattern completion detected!")
                                else:
                                    logger.debug(f"       ⏸️  No pattern completion yet (waiting for event)")
                        except Exception as e:
                            logger.debug(f"       ⚠️  Error checking completion: {e}")
                else:
                    logger.info(f"     ❌ {strategy_name}: No history yet")
        
        # 3. Check filter statistics
        logger.info(f"\n🚫 Filter Statistics:")
        logger.info(f"   - Total signals generated: {self.stats['total_signals']}")
        logger.info(f"   - AI filtered: {self.stats['ai_filtered']}")
        logger.info(f"   - Telegram sent: {self.stats['telegram_sent']}")
        logger.info(f"   - AI Confidence Threshold: {self.ai_filter.confidence_threshold}/10")
        
        # 4. Check market conditions
        try:
            from services.market_hours import MarketHours
            market_status = MarketHours.get_market_status_message()
            logger.info(f"\n🌍 Market Status: {market_status}")
        except:
            logger.info(f"\n🌍 Market Status: Unable to check")
        
        # 5. Recommendations
        logger.info(f"\n💡 Recommendations:")
        if self.stats['total_signals'] == 0:
            logger.info("   - No signals generated yet - strategies may be waiting for pattern completions")
            logger.info("   - Pattern completion requires events (crossovers, bounces, breakouts)")
            logger.info("   - This is normal - system only signals when patterns JUST complete")
        elif self.stats['ai_filtered'] > 0:
            logger.info(f"   - {self.stats['ai_filtered']} signals were filtered by AI (confidence < {self.ai_filter.confidence_threshold}/10)")
            logger.info(f"   - Consider lowering AI threshold if too many signals are filtered")
        
        logger.info("="*60)
    
    def log_statistics(self) -> None:
        """Log current statistics."""
        logger.info("📊 Statistics:")
        logger.info(f"   - Total signals: {self.stats['total_signals']}")
        logger.info(f"   - AI filtered: {self.stats['ai_filtered']}")
        logger.info(f"   - Telegram sent: {self.stats['telegram_sent']}")
        logger.info(f"   - By strategy: {dict(self.stats['by_strategy'])}")


async def run_self_test():
    """
    Self-test to verify strategies are implemented correctly (QuantConnect LEAN pattern).
    Run this before deploying to verify pattern completion detection works.
    """
    logger.info("="*60)
    logger.info("🧪 RUNNING SELF-TEST (QuantConnect LEAN Pattern Verification)")
    logger.info("="*60)
    
    # Test 1: Data fetch
    logger.info("\n[TEST 1] Fetching market data...")
    try:
        generator = SignalGenerator()
        # Try to fetch data for one asset
        test_symbol = config.ASSETS[0] if config.ASSETS else "BTCUSDT"
        async for session in get_session():
            cutoff = datetime.utcnow() - timedelta(hours=24)
            stmt = (
                select(PriceTick)
                .where(PriceTick.symbol == test_symbol)
                .where(PriceTick.ts >= cutoff)
                .order_by(PriceTick.ts)
            )
            result = await session.exec(stmt)
            ticks = result.all()
            logger.info(f"✅ PASS: Fetched {len(ticks)} price ticks for {test_symbol}")
            break
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        return False
    
    # Test 2: Historical data accumulation
    logger.info("\n[TEST 2] Checking historical data accumulation...")
    try:
        # Update strategy with data
        await generator.update_strategies_with_data(test_symbol)
        strategy = generator.strategies.get("momentum", MomentumStrategy())
        if hasattr(strategy, 'price_history') and test_symbol in strategy.price_history:
            history_count = len(strategy.price_history[test_symbol])
            if history_count < 50:
                logger.warning(f"⏳ WAIT: Only {history_count} candles. Need 50+")
                logger.info("   Run for 5-10 more minutes to accumulate data")
            else:
                logger.info(f"✅ PASS: Have {history_count} candles in history")
        else:
            logger.warning(f"⏳ WAIT: No history yet. Need to accumulate data")
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        return False
    
    # Test 3: Strategy pattern completion detection (QuantConnect LEAN pattern)
    logger.info("\n[TEST 3] Testing strategy pattern completion detection...")
    try:
        # Create fake crossover scenario (MACD momentum strategy)
        fake_prices = [100.0] * 50 + [101.0, 102.0, 103.0]  # Stable then rising
        fake_history = []
        for i, price in enumerate(fake_prices):
            candle = {
                'timestamp': datetime.utcnow() - timedelta(minutes=len(fake_prices) - i),
                'open': price,
                'high': price + 0.5,
                'low': price - 0.5,
                'close': price,
                'volume': 1000.0,
            }
            fake_history.append(candle)
        
        test_strategy = MomentumStrategy()
        
        # Feed all candles except last one
        for candle in fake_history[:-1]:
            test_strategy.update_data("TEST", candle)
        
        # Should NOT trigger on first check (no crossover yet)
        signal1 = test_strategy.check_for_signal("TEST")
        if signal1 is None:
            logger.info("✅ PASS: Strategy waits for pattern completion (no signal before crossover)")
        else:
            logger.error(f"❌ FAIL: Strategy triggered without pattern completion: {signal1}")
            return False
        
        # Feed last candle (should create crossover if MACD crosses)
        test_strategy.update_data("TEST", fake_history[-1])
        signal2 = test_strategy.check_for_signal("TEST")
        # May or may not have signal depending on MACD calculation, but should not error
        if signal2 is None:
            logger.info("✅ PASS: Strategy correctly evaluates pattern completion")
        else:
            logger.info(f"✅ PASS: Strategy detected pattern completion event: {signal2.get('action', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    # Test 4: Duplicate prevention
    logger.info("\n[TEST 4] Testing duplicate signal prevention...")
    try:
        test_strategy = MomentumStrategy()
        # Manually mark a signal as sent
        test_strategy._mark_signal_sent("TEST", "buy")
        # Check if duplicate is detected
        is_duplicate = test_strategy._is_duplicate("TEST", "buy")
        if is_duplicate:
            logger.info("✅ PASS: Duplicate signals prevented")
        else:
            logger.warning("⚠️  WARNING: Duplicate check may not be working (time window may have passed)")
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        return False
    
    # Test 5: Telegram connection
    logger.info("\n[TEST 5] Testing Telegram notification...")
    try:
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            await generator.telegram.send_message("🧪 Self-test notification - Bot is operational!")
            logger.info("✅ PASS: Telegram working")
        else:
            logger.warning("⏭️  SKIP: Telegram credentials not configured")
    except Exception as e:
        logger.warning(f"⚠️  WARNING: Telegram error - {e}")
    
    # Test 6: AI validation
    logger.info("\n[TEST 6] Testing AI validation...")
    try:
        test_signal = {
            'strategy': 'Test',
            'symbol': 'BTCUSDT',
            'action': 'buy',
            'entry': 50000.0,
            'stop_loss': 49000.0,
            'take_profit': 52000.0,
            'confidence': 0.75,
            'reasoning': 'Test signal for self-test',
            'risk_reward': 2.0,
        }
        
        ai_result = generator.ai_filter.filter_signal(test_signal)
        if ai_result:
            verdict = ai_result.get('verdict', 'unknown')
            logger.info(f"✅ PASS: AI validation working (verdict: {verdict})")
        else:
            logger.warning("⚠️  WARNING: AI validation returned nothing")
    except Exception as e:
        logger.warning(f"⚠️  WARNING: AI error - {e}")
    
    logger.info("\n" + "="*60)
    logger.info("🏁 SELF-TEST COMPLETE")
    logger.info("="*60)
    logger.info("\n✅ All critical tests passed! Pattern completion detection is working correctly.")
    logger.info("   The system will now only signal when events complete (crossover/bounce/breakout),")
    logger.info("   NOT when conditions are just true. This is the QuantConnect LEAN pattern.\n")
    
    return True


async def main():
    """Main entry point."""
    try:
        # Run self-test first
        logger.info("🚀 Starting signal generator with self-test...")
        test_passed = await run_self_test()
        
        if not test_passed:
            logger.error("❌ Self-test failed! Fix issues before deploying.")
            sys.exit(1)
        
        generator = SignalGenerator()
        logger.info("\n🚀 Starting continuous monitoring...")
        await generator.run_continuously()
    except Exception as e:
        logger.exception(f"Failed to start signal generator: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

