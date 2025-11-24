# backend/app/strategies/momentum.py
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class MomentumStrategy(StrategyBase):
    """
    Momentum strategy that detects momentum SHIFTS, not just current momentum.
    
    Pattern: MACD crosses signal line + histogram expanding + price confirms direction
    """
    name = "momentum"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50  # Need enough for MACD calculation
        self.fast_period = 12
        self.slow_period = 26
        self.signal_period = 9
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2.0 / (period + 1.0)
        
        # Start with SMA
        sma = mean(prices[:period])
        ema_values.append(sma)
        
        # Calculate EMA for remaining values
        for price in prices[period:]:
            ema = (price - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        return ema_values
    
    def _calculate_macd(self, closes: List[float]) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(closes) < self.slow_period + self.signal_period:
            return {"macd": [], "signal": [], "histogram": []}
        
        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)
        
        # MACD line = fast EMA - slow EMA
        macd_line = []
        for i in range(len(slow_ema)):
            macd_val = fast_ema[i + (self.fast_period - self.slow_period)] - slow_ema[i]
            macd_line.append(macd_val)
        
        # Signal line = EMA of MACD line
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Histogram = MACD - Signal
        histogram = []
        for i in range(len(signal_line)):
            hist_val = macd_line[i + (len(macd_line) - len(signal_line))] - signal_line[i]
            histogram.append(hist_val)
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if MACD pattern exists."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        closes = [c['close'] for c in history]
        macd_data = self._calculate_macd(closes)
        
        if len(macd_data["macd"]) < 2 or len(macd_data["signal"]) < 2:
            return False
        
        # Pattern exists if MACD and signal line are close (potential crossover)
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        
        # Check if they're close enough for a crossover (more lenient - 15% instead of 5%)
        diff_pct = abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 1.0
        is_close = diff_pct < 0.15  # Within 15% of each other (relaxed from 5%)
        
        # Log diagnostic info occasionally
        import random
        if random.random() < 0.02:  # 2% of checks
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Momentum {symbol}: MACD={current_macd:.4f}, Signal={current_signal:.4f}, diff={diff_pct*100:.2f}% (need <5%), is_close={is_close}")
        
        return is_close
    
    def _confirm_completion(self, symbol: str) -> bool:
        """Confirm that MACD crossover just completed with histogram expansion."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return False
        
        closes = [c['close'] for c in history]
        macd_data = self._calculate_macd(closes)
        
        if len(macd_data["macd"]) < 3 or len(macd_data["signal"]) < 3 or len(macd_data["histogram"]) < 2:
            return False
        
        # Check for crossover: MACD crosses above/below signal line
        # Allow 2-candle lookback for more realistic pattern detection
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        
        # Check if crossover happened in last 2 candles (more realistic)
        if len(macd_data["macd"]) >= 3:
            prev_prev_macd = macd_data["macd"][-3]
            prev_prev_signal = macd_data["signal"][-3]
            prev_macd = macd_data["macd"][-2]
            prev_signal = macd_data["signal"][-2]
            
            # Bullish: crossed up in last 2 candles AND currently above
            bullish_cross = (
                (prev_prev_macd <= prev_prev_signal and current_macd > current_signal) or
                (prev_macd <= prev_signal and current_macd > current_signal)
            ) and current_macd > current_signal  # Must still be above
            
            # Bearish: crossed down in last 2 candles AND currently below
            bearish_cross = (
                (prev_prev_macd >= prev_prev_signal and current_macd < current_signal) or
                (prev_macd >= prev_signal and current_macd < current_signal)
            ) and current_macd < current_signal  # Must still be below
        else:
            # Fallback to current check if not enough history
            prev_macd = macd_data["macd"][-2]
            prev_signal = macd_data["signal"][-2]
            bullish_cross = prev_macd <= prev_signal and current_macd > current_signal
            bearish_cross = prev_macd >= prev_signal and current_macd < current_signal
        
        if not (bullish_cross or bearish_cross):
            return False  # No crossover
        
        # Check histogram expansion (momentum confirmation)
        if len(macd_data["histogram"]) < 2:
            return False
        
        prev_hist = macd_data["histogram"][-2]
        current_hist = macd_data["histogram"][-1]
        
        # Histogram should be expanding (increasing in absolute value)
        if bullish_cross:
            # Histogram should be increasing (becoming more positive)
            histogram_expanding = current_hist > prev_hist and current_hist > 0
        else:  # bearish_cross
            # Histogram should be decreasing (becoming more negative)
            histogram_expanding = current_hist < prev_hist and current_hist < 0
        
        if not histogram_expanding:
            return False  # No momentum confirmation
        
        # Price confirmation: price should move in same direction as crossover
        prev_close = closes[-2]
        current_close = closes[-1]
        
        if bullish_cross:
            price_confirms = current_close > prev_close
        else:
            price_confirms = current_close < prev_close
        
        return price_confirms
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """
        Determine buy/sell action from MACD crossover event (QuantConnect LEAN pattern).
        ONLY returns action when crossover event just completed.
        """
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return None
        
        closes = [c['close'] for c in history]
        macd_data = self._calculate_macd(closes)
        
        if len(macd_data["macd"]) < 2 or len(macd_data["signal"]) < 2:
            return None
        
        prev_macd = macd_data["macd"][-2]
        prev_signal = macd_data["signal"][-2]
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        
        # BULLISH CROSSOVER EVENT: MACD crosses ABOVE signal (QuantConnect LEAN pattern)
        if prev_macd <= prev_signal and current_macd > current_signal:
            return "buy"
        
        # BEARISH CROSSOVER EVENT: MACD crosses BELOW signal (QuantConnect LEAN pattern)
        if prev_macd >= prev_signal and current_macd < current_signal:
            return "sell"
        
        # NO ACTION - crossover event hasn't completed yet
        return None
    
    def _build_signal(self, symbol: str, action: str) -> Optional[Dict[str, Any]]:
        """
        Build signal with entry, stop loss, take profit.
        
        PROFESSIONAL TRADING PRACTICE:
        - Entry price will be set to LIVE market price by SignalGenerator (not candle close)
        - We calculate stop_loss/take_profit based on candle data for risk management
        - This ensures entry is always current market price, not stale historical data
        """
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < 1:
            return None
        
        current_candle = history[-1]
        # Use close price for calculations, but SignalGenerator will use live price for actual entry
        # This is standard practice - strategies calculate levels, but entry uses live market price
        reference_price = current_candle.get('close', 0.0)
        
        # If close is invalid, try high/low average for calculations
        if reference_price <= 0:
            high = current_candle.get('high', 0.0)
            low = current_candle.get('low', 0.0)
            if high > 0 and low > 0:
                reference_price = (high + low) / 2.0
            elif high > 0:
                reference_price = high
            elif low > 0:
                reference_price = low
            else:
                # No valid price data - cannot build signal
                return None
        
        # Use reference_price for stop_loss/take_profit calculations
        # Entry will be set to live market price by SignalGenerator
        entry = reference_price  # Temporary - will be replaced with live price
        
        # Calculate ATR for stop loss
        closes = [c['close'] for c in history[-14:]]
        highs = [c['high'] for c in history[-14:]]
        lows = [c['low'] for c in history[-14:]]
        
        # Simple ATR calculation
        true_ranges = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        atr = mean(true_ranges) if true_ranges else entry * 0.02
        
        if action == "buy":
            # Stop loss below recent low, take profit 2.5x ATR above entry
            # FIX: Filter out invalid lows (0.0 or negative) before calculating min
            recent_lows = [c.get('low', 0.0) for c in history[-10:] if c.get('low', 0.0) > 0]
            if not recent_lows:
                # No valid lows - use ATR-based stop loss as fallback
                stop_loss = entry - (atr * 2.0)  # 2x ATR below entry
            else:
                stop_loss = min(recent_lows) * 0.995
                # Ensure stop_loss is below entry and valid
                if stop_loss >= entry or stop_loss <= 0:
                    stop_loss = entry - (atr * 2.0)  # Fallback to ATR-based
            take_profit = entry + (atr * 2.5)
            # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
            max_take_profit = entry * 1.06  # +6% max
            if take_profit > max_take_profit:
                take_profit = max_take_profit
        elif action == "sell":
            # Stop loss above recent high, take profit 2.5x ATR below entry
            # FIX: Filter out invalid highs (0.0 or negative) before calculating max
            recent_highs = [c.get('high', 0.0) for c in history[-10:] if c.get('high', 0.0) > 0]
            if not recent_highs:
                # No valid highs - use ATR-based stop loss as fallback
                stop_loss = entry + (atr * 2.0)  # 2x ATR above entry
            else:
                stop_loss = max(recent_highs) * 1.005
                # Ensure stop_loss is above entry and valid
                if stop_loss <= entry or stop_loss <= 0:
                    stop_loss = entry + (atr * 2.0)  # Fallback to ATR-based
            take_profit = entry - (atr * 2.5)
            # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
            max_take_profit = entry * 0.94  # -6% max
            if take_profit < max_take_profit:
                take_profit = max_take_profit
        else:
            return None
        
        # Validate risk/reward ratio (minimum 1.5:1, maximum 4:1)
        if action == "buy":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        
        if risk <= 0:
            return None  # Invalid risk
        
        risk_reward_ratio = reward / risk
        
        # CRITICAL FIX: Reject unrealistic risk/reward ratios (>4:1)
        if risk_reward_ratio < 1.5:
            return None  # Invalid risk/reward (too low)
        if risk_reward_ratio > 4.0:
            # Cap R:R at 4:1 by adjusting take profit
            if action == "buy":
                take_profit = entry + (risk * 4.0)
            else:
                take_profit = entry - (risk * 4.0)
            risk_reward_ratio = 4.0
        
        # Enhanced confidence calculation with multiple confirmations
        closes = [c['close'] for c in history]
        macd_data = self._calculate_macd(closes)
        
        if len(macd_data["histogram"]) < 1:
            return None
        
        current_hist = abs(macd_data["histogram"][-1])
        prev_hist = abs(macd_data["histogram"][-2]) if len(macd_data["histogram"]) >= 2 else current_hist
        
        # Enhanced confidence calculation (research-proven approach)
        # Base confidence from histogram strength
        hist_strength = current_hist / entry if entry > 0 else 0.0
        hist_confidence = min(0.4, hist_strength * 100)  # Normalize to 0-0.4
        
        # Histogram expansion bonus (momentum confirmation)
        hist_expanding = current_hist > prev_hist
        expansion_bonus = 0.15 if hist_expanding else 0.0
        
        # Risk/reward bonus
        rr_ratio = reward / risk if risk > 0 else 0.0
        rr_confidence = min(0.3, (rr_ratio - 1.5) / 5.0) if rr_ratio >= 1.5 else 0.0
        
        # MACD crossover strength (how far MACD is from signal line)
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        macd_separation = abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 0.0
        macd_bonus = min(0.15, macd_separation * 2.0)  # Bonus for strong separation
        
        # Total confidence with all confirmations
        confidence = min(0.90, 0.4 + hist_confidence + expansion_bonus + rr_confidence + macd_bonus)
        
        return {
            "strategy": self.name,
            "symbol": symbol,
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"MACD momentum shift: {action.upper()} crossover confirmed with histogram expansion. MACD: {macd_data['macd'][-1]:.4f}, Signal: {macd_data['signal'][-1]:.4f}.",
            "requires_volume": False,
            "macd": macd_data["macd"][-1],
            "signal_line": macd_data["signal"][-1],
            "histogram": macd_data["histogram"][-1],
        }
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """Legacy run method for backward compatibility."""
        return super().run(symbol, prices, **extra)
