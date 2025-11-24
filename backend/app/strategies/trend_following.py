"""
Trend-following strategy using multi-timeframe EMA crossovers and ADX filter.
- Uses historical price data from price_ticks table
- Multi-timeframe analysis (5min, 15min, 1h)
- ADX filter for trend strength
- Returns JSON-serializable signals with entry/exit levels
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from sqlmodel import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logger import logger
from backend.app.db.models import PriceTick
from backend.app.strategies.base import StrategyBase


class TrendFollowingStrategy(StrategyBase):
    name = "trend_following"
    """Multi-timeframe EMA crossover strategy with ADX trend filter."""
    
    def __init__(
        self,
        fast_ema: int = 12,
        slow_ema: int = 26,
        adx_period: int = 14,
        adx_threshold: float = 20.0,  # Relaxed from 25.0 (professional standard: 20-25)
        min_confidence: float = 0.5,  # Relaxed from 0.6 (professional standard: 0.5-0.6)
    ):
        super().__init__()  # Initialize StrategyBase
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.min_confidence = min_confidence
        self.name = "trend_following"
    
    async def get_historical_data(
        self, 
        session: AsyncSession, 
        symbol: str, 
        hours_back: int = 24
    ) -> pd.DataFrame:
        """Fetch historical price data for the symbol."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        stmt = select(PriceTick).where(
            and_(
                PriceTick.symbol == symbol,
                PriceTick.ts >= cutoff_time
            )
        ).order_by(PriceTick.ts)
        
        result = await session.exec(stmt)
        ticks = result.all()
        
        if not ticks:
            logger.warning(f"No price data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for tick in ticks:
            data.append({
                'timestamp': tick.ts,
                'open': tick.open or tick.price,
                'high': tick.high or tick.price,
                'low': tick.low or tick.price,
                'close': tick.price,
                'volume': tick.volume or 0.0,
            })
        
        df = pd.DataFrame(data)
        if df.empty:
            return df
        
        # Set timestamp as index and resample to 5-minute bars
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample to 5-minute bars
        df_5m = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return df_5m
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low), 
                          np.maximum(high - high.shift(1), 0), 0)
        dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)), 
                           np.maximum(low.shift(1) - low, 0), 0)
        
        # Smooth the values
        tr_smooth = tr.rolling(window=period).mean()
        dm_plus_smooth = pd.Series(dm_plus).rolling(window=period).mean()
        dm_minus_smooth = pd.Series(dm_minus).rolling(window=period).mean()
        
        # Calculate Directional Indicators (with division by zero protection)
        di_plus = 100 * (dm_plus_smooth / tr_smooth.replace(0, 1))  # Replace 0 with 1 to avoid division by zero
        di_minus = 100 * (dm_minus_smooth / tr_smooth.replace(0, 1))
        
        # Calculate ADX (with division by zero protection)
        denominator = di_plus + di_minus
        dx = 100 * abs(di_plus - di_minus) / denominator.replace(0, 1)  # Replace 0 with 1 to avoid division by zero
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def analyze_timeframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze a single timeframe for EMA crossover signals."""
        try:
            if df.empty or len(df) < max(self.fast_ema, self.slow_ema, self.adx_period):
                return {"signal": "hold", "confidence": 0.0}
            
            # Calculate EMAs
            ema_fast = self.calculate_ema(df['close'], self.fast_ema)
            ema_slow = self.calculate_ema(df['close'], self.slow_ema)
            
            if ema_fast.empty or ema_slow.empty:
                return {"signal": "hold", "confidence": 0.0}
            
            # Calculate ADX
            adx = self.calculate_adx(df, self.adx_period)
            
            # Get latest values
            latest_fast = ema_fast.iloc[-1]
            latest_slow = ema_slow.iloc[-1]
            latest_adx = adx.iloc[-1] if not adx.empty else 0.0
            latest_price = df['close'].iloc[-1]
            
            # Check for crossover
            prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else latest_fast
            prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else latest_slow
            
            # Determine signal
            signal = "hold"
            confidence = 0.0
            
            if pd.isna(latest_adx) or latest_adx < self.adx_threshold:
                # Weak trend - no signal
                return {"signal": "hold", "confidence": 0.0}
            
            if prev_fast <= prev_slow and latest_fast > latest_slow:
                # Bullish crossover
                signal = "buy"
                confidence = min(0.9, latest_adx / 50.0) if latest_adx > 0 else 0.0  # Scale confidence with ADX
            elif prev_fast >= prev_slow and latest_fast < latest_slow:
                # Bearish crossover
                signal = "sell"
                confidence = min(0.9, latest_adx / 50.0) if latest_adx > 0 else 0.0
            
            return {
                "signal": signal,
                "confidence": confidence,
                "ema_fast": float(latest_fast),
                "ema_slow": float(latest_slow),
                "adx": float(latest_adx) if not pd.isna(latest_adx) else 0.0,
                "price": float(latest_price)
            }
        except Exception as e:
            logger.exception(f"Error in analyze_timeframe: {e}")
            return {"signal": "hold", "confidence": 0.0}
    
    async def generate_signal(
        self, 
        session: AsyncSession, 
        symbol: str
    ) -> Dict[str, Any]:
        """Generate trading signal for the given symbol."""
        try:
            # Get historical data
            df = await self.get_historical_data(session, symbol, hours_back=24)
            
            # FIX: Relaxed minimum data requirement (professional standard: 30-50 candles)
            if df.empty or len(df) < 30:
                return {
                    "strategy": self.name,
                    "symbol": symbol,
                    "action": "hold",
                    "entry": 0.0,
                    "sl": 0.0,
                    "tp": 0.0,
                    "confidence": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "insufficient_data"
                }
            
            # Analyze 5-minute timeframe
            tf_5m = self.analyze_timeframe(df)
            
            # Create 15-minute and 1-hour timeframes
            df_15m = df.resample('15min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            df_1h = df.resample('1h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Analyze higher timeframes
            tf_15m = self.analyze_timeframe(df_15m) if len(df_15m) >= 20 else {"signal": "hold", "confidence": 0.0}
            tf_1h = self.analyze_timeframe(df_1h) if len(df_1h) >= 20 else {"signal": "hold", "confidence": 0.0}
            
            # Multi-timeframe consensus
            signals = [tf_5m["signal"], tf_15m["signal"], tf_1h["signal"]]
            confidences = [tf_5m["confidence"], tf_15m["confidence"], tf_1h["confidence"]]
            
            # Weight higher timeframes more
            weights = [0.2, 0.3, 0.5]  # 5m, 15m, 1h
            weighted_confidence = sum(c * w for c, w in zip(confidences, weights))
            
            # Determine final signal
            # FIX: Professional systems allow 1 timeframe if strong enough (high ADX + high confidence)
            # This makes the strategy more responsive while maintaining quality
            buy_count = signals.count("buy")
            sell_count = signals.count("sell")
            
            # Get strongest timeframe signal for single-timeframe check
            strongest_tf = max([tf_5m, tf_15m, tf_1h], key=lambda x: x.get("confidence", 0.0))
            strongest_adx = strongest_tf.get("adx", 0.0)
            strongest_confidence = strongest_tf.get("confidence", 0.0)
            
            # Multi-timeframe consensus (preferred): 2+ timeframes agree
            if buy_count >= 2 and weighted_confidence >= self.min_confidence:
                action = "buy"
                entry = tf_5m.get("price", 0.0)
                # Set stop loss and take profit based on ATR
                atr = self.calculate_atr(df, 14)
                sl = entry * 0.98  # 2% stop loss
                tp = entry * 1.04  # 4% take profit
            elif sell_count >= 2 and weighted_confidence >= self.min_confidence:
                action = "sell"
                entry = tf_5m.get("price", 0.0)
                atr = self.calculate_atr(df, 14)
                sl = entry * 1.02  # 2% stop loss
                tp = entry * 0.96  # 4% take profit
            # Single timeframe with strong confirmation (professional fallback)
            elif buy_count >= 1 and strongest_adx >= 30.0 and strongest_confidence >= 0.7:
                # Strong trend (ADX >= 30) + high confidence (>= 0.7) = valid signal
                action = "buy"
                entry = strongest_tf.get("price", tf_5m.get("price", 0.0))
                atr = self.calculate_atr(df, 14)
                sl = entry * 0.98  # 2% stop loss
                tp = entry * 1.04  # 4% take profit
                weighted_confidence = strongest_confidence  # Use strongest confidence
            elif sell_count >= 1 and strongest_adx >= 30.0 and strongest_confidence >= 0.7:
                # Strong trend (ADX >= 30) + high confidence (>= 0.7) = valid signal
                action = "sell"
                entry = strongest_tf.get("price", tf_5m.get("price", 0.0))
                atr = self.calculate_atr(df, 14)
                sl = entry * 1.02  # 2% stop loss
                tp = entry * 0.96  # 4% take profit
                weighted_confidence = strongest_confidence  # Use strongest confidence
            else:
                action = "hold"
                entry = sl = tp = 0.0
                weighted_confidence = 0.0
            
            return {
                "strategy": self.name,
                "symbol": symbol,
                "action": action,
                "entry": float(entry),
                "sl": float(sl),
                "tp": float(tp),
                "confidence": float(weighted_confidence),
                "timestamp": datetime.utcnow().isoformat(),
                "timeframes": {
                    "5m": tf_5m,
                    "15m": tf_15m,
                    "1h": tf_1h
                }
            }
            
        except Exception as exc:
            logger.exception(f"Error generating trend-following signal for {symbol}: {exc}")
            return {
                "strategy": self.name,
                "symbol": symbol,
                "action": "hold",
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"error: {str(exc)}"
            }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean().iloc[-1]
        return float(atr) if not pd.isna(atr) else 0.0


# Convenience function for external use
async def generate_trend_signal(
    session: AsyncSession, 
    symbol: str,
    **strategy_kwargs
) -> Dict[str, Any]:
    """Generate trend-following signal for a symbol."""
    strategy = TrendFollowingStrategy(**strategy_kwargs)
    return await strategy.generate_signal(session, symbol)
