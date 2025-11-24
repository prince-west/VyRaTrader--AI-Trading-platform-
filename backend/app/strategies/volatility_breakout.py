"""
Volatility breakout strategy using ATR-based breakouts and volatility sizing.
- Uses recent highs/lows and ATR for breakout detection
- Pulls data from diverse sources via price_ticks
- Returns JSON-serializable signals with dynamic position sizing
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


class VolatilityBreakoutStrategy(StrategyBase):
    name = "volatility_breakout"
    """ATR-based breakout strategy with volatility-adjusted position sizing."""
    
    def __init__(
        self,
        lookback_period: int = 20,
        atr_period: int = 14,
        breakout_multiplier: float = 1.5,  # Relaxed from 2.0 (professional standard: 1.5-2.5x ATR)
        min_volume_ratio: float = 1.3,  # Relaxed from 1.5 (professional standard: 1.3-1.5x)
        max_risk_per_trade: float = 0.02,  # 2% of portfolio
    ):
        super().__init__()  # Initialize StrategyBase
        self.lookback_period = lookback_period
        self.atr_period = atr_period
        self.breakout_multiplier = breakout_multiplier
        self.min_volume_ratio = min_volume_ratio
        self.max_risk_per_trade = max_risk_per_trade
        self.name = "volatility_breakout"
    
    async def get_historical_data(
        self, 
        session: AsyncSession, 
        symbol: str, 
        hours_back: int = 48
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
        
        # Set timestamp as index and resample to 15-minute bars
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample to 15-minute bars for better breakout detection
        df_15m = df.resample('15min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return df_15m
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        return atr
    
    def calculate_volatility_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility and volume metrics."""
        if len(df) < self.lookback_period:
            return {"atr": 0.0, "volatility": 0.0, "volume_ratio": 0.0}
        
        # Calculate ATR
        atr = self.calculate_atr(df, self.atr_period)
        current_atr = atr.iloc[-1] if not atr.empty else 0.0
        
        # Calculate price volatility (standard deviation of returns)
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(window=self.lookback_period).std().iloc[-1] if len(returns) >= self.lookback_period else 0.0
        
        # Calculate volume ratio (current vs average)
        try:
            current_volume = df['volume'].iloc[-1] if not df['volume'].empty else 0.0
            avg_volume = df['volume'].rolling(window=self.lookback_period).mean().iloc[-1] if len(df) >= self.lookback_period else 0.0
            
            if pd.isna(avg_volume) or avg_volume <= 0:
                volume_ratio = 0.0
            else:
                volume_ratio = current_volume / avg_volume
        except Exception:
            volume_ratio = 0.0
        
        return {
            "atr": float(current_atr) if not pd.isna(current_atr) else 0.0,
            "volatility": float(volatility) if not pd.isna(volatility) else 0.0,
            "volume_ratio": float(volume_ratio) if not pd.isna(volume_ratio) else 0.0
        }
    
    def detect_breakout(self, df: pd.DataFrame, atr: float) -> Dict[str, Any]:
        """Detect breakout patterns using recent highs/lows and ATR."""
        if len(df) < self.lookback_period + 1:
            return {"signal": "hold", "breakout_type": None, "confidence": 0.0}
        
        # Get recent data
        recent_data = df.tail(self.lookback_period + 1)
        current_bar = recent_data.iloc[-1]
        previous_bars = recent_data.iloc[:-1]
        
        # Calculate recent highs and lows
        recent_high = previous_bars['high'].max()
        recent_low = previous_bars['low'].min()
        current_high = current_bar['high']
        current_low = current_bar['low']
        current_close = current_bar['close']
        
        # Calculate breakout levels
        resistance = recent_high + (atr * self.breakout_multiplier)
        support = recent_low - (atr * self.breakout_multiplier)
        
        # Detect breakout
        signal = "hold"
        breakout_type = None
        confidence = 0.0
        
        # Bullish breakout
        if current_high > resistance and current_close > recent_high:
            signal = "buy"
            breakout_type = "bullish"
            # Confidence based on how far above resistance
            confidence = min(0.9, (current_high - resistance) / (atr * 0.5))
        
        # Bearish breakout
        elif current_low < support and current_close < recent_low:
            signal = "sell"
            breakout_type = "bearish"
            # Confidence based on how far below support
            confidence = min(0.9, (support - current_low) / (atr * 0.5))
        
        return {
            "signal": signal,
            "breakout_type": breakout_type,
            "confidence": confidence,
            "resistance": float(resistance),
            "support": float(support),
            "recent_high": float(recent_high),
            "recent_low": float(recent_low),
            "current_price": float(current_close)
        }
    
    def calculate_position_size(
        self, 
        price: float, 
        atr: float, 
        portfolio_value: float = 10000.0
    ) -> Dict[str, float]:
        """Calculate position size based on volatility and risk management."""
        if atr <= 0 or price <= 0:
            return {"position_size": 0.0, "risk_amount": 0.0}
        
        # Risk amount based on portfolio value
        risk_amount = portfolio_value * self.max_risk_per_trade
        
        # Position size based on ATR (volatility-adjusted)
        # Higher ATR = smaller position size
        atr_percentage = atr / price
        position_size = risk_amount / (atr * 2)  # 2x ATR stop loss
        
        # Cap position size to reasonable limits
        max_position_value = portfolio_value * 0.1  # Max 10% of portfolio
        max_position_size = max_position_value / price
        
        position_size = min(position_size, max_position_size)
        
        return {
            "position_size": float(position_size),
            "risk_amount": float(risk_amount),
            "atr_percentage": float(atr_percentage)
        }
    
    async def generate_signal(
        self, 
        session: AsyncSession, 
        symbol: str,
        portfolio_value: float = 10000.0
    ) -> Dict[str, Any]:
        """Generate volatility breakout signal for the given symbol."""
        try:
            # Get historical data
            df = await self.get_historical_data(session, symbol, hours_back=48)
            
            # FIX: Relaxed minimum data requirement (professional standard: lookback + 2)
            if df.empty or len(df) < self.lookback_period + 2:
                return {
                    "strategy": self.name,
                    "symbol": symbol,
                    "action": "hold",
                    "entry": 0.0,
                    "sl": 0.0,
                    "tp": 0.0,
                    "confidence": 0.0,
                    "position_size": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "insufficient_data"
                }
            
            # Calculate volatility metrics
            vol_metrics = self.calculate_volatility_metrics(df)
            atr = vol_metrics["atr"]
            volume_ratio = vol_metrics["volume_ratio"]
            
            # Check volume requirement
            if volume_ratio < self.min_volume_ratio:
                return {
                    "strategy": self.name,
                    "symbol": symbol,
                    "action": "hold",
                    "entry": 0.0,
                    "sl": 0.0,
                    "tp": 0.0,
                    "confidence": 0.0,
                    "position_size": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "low_volume"
                }
            
            # Detect breakout
            breakout = self.detect_breakout(df, atr)
            
            if breakout["signal"] == "hold":
                return {
                    "strategy": self.name,
                    "symbol": symbol,
                    "action": "hold",
                    "entry": 0.0,
                    "sl": 0.0,
                    "tp": 0.0,
                    "confidence": 0.0,
                    "position_size": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "no_breakout"
                }
            
            # Calculate entry, stop loss, and take profit
            current_price = breakout["current_price"]
            
            if breakout["signal"] == "buy":
                entry = current_price
                sl = entry - (atr * 2)  # 2x ATR stop loss
                tp = entry + (atr * 3)  # 3x ATR take profit (1.5:1 risk/reward)
                # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
                max_take_profit = entry * 1.06  # +6% max
                if tp > max_take_profit:
                    tp = max_take_profit
            else:  # sell
                entry = current_price
                sl = entry + (atr * 2)  # 2x ATR stop loss
                tp = entry - (atr * 3)  # 3x ATR take profit
                # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
                max_take_profit = entry * 0.94  # -6% max
                if tp < max_take_profit:
                    tp = max_take_profit
            
            # Calculate position size
            position_info = self.calculate_position_size(entry, atr, portfolio_value)
            
            return {
                "strategy": self.name,
                "symbol": symbol,
                "action": breakout["signal"],
                "entry": float(entry),
                "sl": float(sl),
                "tp": float(tp),
                "confidence": float(breakout["confidence"]),
                "position_size": position_info["position_size"],
                "timestamp": datetime.utcnow().isoformat(),
                "breakout_info": {
                    "type": breakout["breakout_type"],
                    "resistance": breakout["resistance"],
                    "support": breakout["support"],
                    "recent_high": breakout["recent_high"],
                    "recent_low": breakout["recent_low"]
                },
                "volatility_metrics": vol_metrics,
                "position_info": position_info
            }
            
        except Exception as exc:
            logger.exception(f"Error generating volatility breakout signal for {symbol}: {exc}")
            return {
                "strategy": self.name,
                "symbol": symbol,
                "action": "hold",
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "confidence": 0.0,
                "position_size": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"error: {str(exc)}"
            }


# Convenience function for external use
async def generate_breakout_signal(
    session: AsyncSession, 
    symbol: str,
    portfolio_value: float = 10000.0,
    **strategy_kwargs
) -> Dict[str, Any]:
    """Generate volatility breakout signal for a symbol."""
    strategy = VolatilityBreakoutStrategy(**strategy_kwargs)
    return await strategy.generate_signal(session, symbol, portfolio_value)
