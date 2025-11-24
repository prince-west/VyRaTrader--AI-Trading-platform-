"""
Strategy runner service for VyRaTrader.
- Runs enabled strategies periodically or on-demand
- Stores signals in database with deduplication
- Ensures idempotency and prevents duplicate signals
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

from sqlmodel import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import Strategy, Signals, PriceTick
from backend.app.db.session import get_session

# Import strategy modules
from backend.app.strategies.trend_following import generate_trend_signal
from backend.app.strategies.volatility_breakout import generate_breakout_signal
from backend.app.strategies.sentiment_filter import analyze_sentiment, create_sentiment_filter


class StrategyRunner:
    """Runs trading strategies and manages signal generation."""
    
    def __init__(self, deduplication_window_minutes: int = 15):
        self.deduplication_window_minutes = deduplication_window_minutes
        self.strategy_functions = {
            "trend_following": generate_trend_signal,
            "volatility_breakout": generate_breakout_signal,
            # Add more strategies as they're implemented
        }
    
    async def get_enabled_strategies(self, session: AsyncSession) -> List[Strategy]:
        """Get all enabled strategies from database."""
        stmt = select(Strategy).where(Strategy.is_active == True)
        result = await session.exec(stmt)
        return result.all()
    
    async def get_symbols_to_analyze(self, session: AsyncSession) -> List[str]:
        """Get symbols to analyze from recent price data."""
        # Get symbols from recent price ticks
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        stmt = select(PriceTick.symbol).where(
            PriceTick.ts >= cutoff_time
        ).distinct()
        
        result = await session.exec(stmt)
        symbols = [row[0] for row in result.all()]
        
        # Fallback to configured symbols if no recent data
        if not symbols:
            symbols = getattr(settings, "CRYPTO_SYMBOLS", ["BTCUSDT", "ETHUSDT"])
        
        return symbols[:10]  # Limit to prevent overload
    
    async def check_duplicate_signal(
        self, 
        session: AsyncSession, 
        strategy: str, 
        symbol: str, 
        action: str
    ) -> bool:
        """Check if a similar signal already exists within the deduplication window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.deduplication_window_minutes)
        
        stmt = select(Signals).where(
            and_(
                Signals.strategy == strategy,
                Signals.symbol == symbol,
                Signals.action == action,
                Signals.timestamp >= cutoff_time
            )
        )
        
        result = await session.exec(stmt)
        existing_signal = result.first()
        
        return existing_signal is not None
    
    async def store_signal(
        self, 
        session: AsyncSession, 
        signal_data: Dict[str, Any]
    ) -> Optional[Signals]:
        """Store a signal in the database with deduplication."""
        try:
            strategy = signal_data.get("strategy", "unknown")
            symbol = signal_data.get("symbol", "")
            action = signal_data.get("action", "hold")
            
            # Skip hold signals
            if action == "hold":
                return None
            
            # Check for duplicates
            is_duplicate = await self.check_duplicate_signal(session, strategy, symbol, action)
            if is_duplicate:
                logger.debug(f"Duplicate signal skipped: {strategy} {symbol} {action}")
                return None
            
            # Create signal record
            signal = Signals(
                strategy=strategy,
                symbol=symbol,
                action=action,
                entry=signal_data.get("entry", 0.0),
                sl=signal_data.get("sl", 0.0),
                tp=signal_data.get("tp", 0.0),
                confidence=signal_data.get("confidence", 0.0),
                source_meta=signal_data.get("source_meta", {}),
                timestamp=datetime.utcnow(),
                processed=False,
                expires_at=datetime.utcnow() + timedelta(hours=24)  # Signals expire after 24h
            )
            
            session.add(signal)
            await session.commit()
            await session.refresh(signal)
            
            logger.info(f"Stored signal: {strategy} {symbol} {action} (confidence: {signal.confidence:.2f})")
            return signal
            
        except Exception as exc:
            logger.exception(f"Error storing signal: {exc}")
            await session.rollback()
            return None
    
    async def run_strategy(
        self, 
        session: AsyncSession, 
        strategy: Strategy, 
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Run a single strategy on a symbol."""
        try:
            strategy_name = strategy.name
            
            # Get strategy function
            if strategy_name not in self.strategy_functions:
                logger.warning(f"Strategy function not found: {strategy_name}")
                return None
            
            strategy_func = self.strategy_functions[strategy_name]
            
            # Run strategy with default parameters
            if strategy_name == "trend_following":
                signal = await strategy_func(session, symbol)
            elif strategy_name == "volatility_breakout":
                signal = await strategy_func(session, symbol, portfolio_value=10000.0)
            else:
                signal = await strategy_func(session, symbol)
            
            # Add strategy metadata
            if signal and signal.get("action") != "hold":
                signal["source_meta"] = {
                    "strategy_config": strategy.config or {},
                    "strategy_performance": strategy.performance or {},
                    "generated_by": "strategy_runner"
                }
            
            return signal
            
        except Exception as exc:
            logger.exception(f"Error running strategy {strategy.name} on {symbol}: {exc}")
            return None
    
    async def run_all_strategies(
        self, 
        session: AsyncSession,
        symbols: Optional[List[str]] = None
    ) -> List[Signals]:
        """Run all enabled strategies on specified symbols."""
        if symbols is None:
            symbols = await self.get_symbols_to_analyze(session)
        
        # Get enabled strategies
        strategies = await self.get_enabled_strategies(session)
        
        if not strategies:
            logger.warning("No enabled strategies found")
            return []
        
        logger.info(f"Running {len(strategies)} strategies on {len(symbols)} symbols")
        
        stored_signals = []
        
        # Run strategies concurrently
        tasks = []
        for strategy in strategies:
            for symbol in symbols:
                task = self.run_strategy(session, strategy, symbol)
                tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and store signals
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Strategy execution error: {result}")
                continue
            
            if result and result.get("action") != "hold":
                stored_signal = await self.store_signal(session, result)
                if stored_signal:
                    stored_signals.append(stored_signal)
        
        logger.info(f"Generated {len(stored_signals)} new signals")
        return stored_signals
    
    async def run_strategies_for_symbol(
        self, 
        session: AsyncSession, 
        symbol: str
    ) -> List[Signals]:
        """Run all strategies for a specific symbol."""
        return await self.run_all_strategies(session, [symbol])
    
    async def cleanup_expired_signals(self, session: AsyncSession) -> int:
        """Clean up expired signals."""
        try:
            expired_cutoff = datetime.utcnow()
            
            # Count expired signals
            stmt = select(Signals).where(
                and_(
                    Signals.expires_at <= expired_cutoff,
                    Signals.processed == False
                )
            )
            result = await session.exec(stmt)
            expired_signals = result.all()
            
            # Delete expired signals
            for signal in expired_signals:
                await session.delete(signal)
            
            await session.commit()
            
            logger.info(f"Cleaned up {len(expired_signals)} expired signals")
            return len(expired_signals)
            
        except Exception as exc:
            logger.exception(f"Error cleaning up expired signals: {exc}")
            await session.rollback()
            return 0
    
    async def get_latest_signals(
        self, 
        session: AsyncSession,
        limit: int = 50,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Signals]:
        """Get latest signals with optional filtering."""
        conditions = []
        
        if strategy:
            conditions.append(Signals.strategy == strategy)
        
        if symbol:
            conditions.append(Signals.symbol == symbol)
        
        stmt = select(Signals).where(and_(*conditions) if conditions else True).order_by(
            desc(Signals.timestamp)
        ).limit(limit)
        
        result = await session.exec(stmt)
        return result.all()


# Global strategy runner instance
_strategy_runner: Optional[StrategyRunner] = None


def get_strategy_runner() -> StrategyRunner:
    """Get or create the global strategy runner instance."""
    global _strategy_runner
    if _strategy_runner is None:
        _strategy_runner = StrategyRunner()
    return _strategy_runner


# Convenience functions for external use
async def run_strategies(symbols: Optional[List[str]] = None) -> List[Signals]:
    """Run all strategies and return generated signals."""
    runner = get_strategy_runner()
    async for session in get_session():
        return await runner.run_all_strategies(session, symbols)


async def run_strategies_for_symbol(symbol: str) -> List[Signals]:
    """Run all strategies for a specific symbol."""
    runner = get_strategy_runner()
    async for session in get_session():
        return await runner.run_strategies_for_symbol(session, symbol)


async def get_latest_signals(
    limit: int = 50,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None
) -> List[Signals]:
    """Get latest signals with optional filtering."""
    runner = get_strategy_runner()
    async for session in get_session():
        return await runner.get_latest_signals(session, limit, strategy, symbol)


async def cleanup_expired_signals() -> int:
    """Clean up expired signals."""
    runner = get_strategy_runner()
    async for session in get_session():
        return await runner.cleanup_expired_signals(session)
