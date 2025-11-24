# backend/app/strategies/mean_reversion.py
"""
Enhanced Mean Reversion Strategy with Adaptive Thresholds
Based on research-proven techniques for better signal accuracy.
"""
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean, stdev
from backend.app.strategies.base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    """
    Enhanced mean reversion strategy with adaptive thresholds.
    Detects extreme oversold/overbought conditions followed by reversal beginnings.
    
    Pattern: RSI extreme (adaptive) + price makes higher low/lower high + RSI starts rising/falling
    """
    name = "mean_reversion"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 40  # Need more for volatility calculation
        self.rsi_period = 14
        self.extreme_oversold_base = 30  # Base threshold, adjusted by volatility
        self.extreme_overbought_base = 70
        self.reversal_confirmation_period = 3  # Need 3 candles to confirm reversal
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        if len(closes) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]
        
        # Use recent period
        recent_gains = gains[-period:]
        recent_losses = losses[-period:]
        
        avg_gain = mean(recent_gains) if recent_gains else 0.0
        avg_loss = mean(recent_losses) if recent_losses else 0.0
        
        if avg_loss == 0:
            return 100.0  # All gains, no losses
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_volatility(self, closes: List[float], period: int = 20) -> float:
        """Calculate price volatility (standard deviation of returns)."""
        if len(closes) < period + 1:
            return 0.0
        
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:  # Avoid division by zero
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
        
        recent_returns = returns[-period:] if len(returns) >= period else returns
        
        if len(recent_returns) < 2:
            return 0.0
        
        try:
            return stdev(recent_returns) if recent_returns else 0.0
        except:
            return 0.0
    
    def _get_adaptive_thresholds(self, closes: List[float]) -> Tuple[float, float]:
        """
        Get adaptive RSI thresholds based on market volatility.
        Higher volatility = wider thresholds (more extreme required).
        """
        volatility = self._calculate_volatility(closes)
        
        # Normalize volatility (typical range 0.001-0.05 for most assets)
        normalized_vol = min(1.0, volatility * 100)  # Scale to 0-1
        
        # Adjust thresholds: high volatility = more extreme required
        oversold = self.extreme_oversold_base - (normalized_vol * 5)  # 30 -> 25 in high vol
        overbought = self.extreme_overbought_base + (normalized_vol * 5)  # 70 -> 75 in high vol
        
        # Clamp to reasonable bounds
        oversold = max(20, min(35, oversold))
        overbought = min(80, max(65, overbought))
        
        return oversold, overbought
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if extreme condition exists."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        # Calculate RSI
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        
        # Get adaptive thresholds
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # Pattern exists if RSI is in extreme territory (using adaptive thresholds)
        is_extreme = current_rsi <= oversold or current_rsi >= overbought
        
        # Log diagnostic info occasionally
        import random
        if random.random() < 0.02:  # 2% of checks
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"MeanReversion {symbol}: RSI={current_rsi:.1f} (oversold<{oversold:.1f}, overbought>{overbought:.1f}), is_extreme={is_extreme}")
        
        return is_extreme
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that RSI BOUNCE event just completed (QuantConnect LEAN pattern).
        Follows momentum strategy pattern: detect ONE simple state transition, then confirm.
        Detects: RSI crossing UP from oversold (buy) or DOWN from overbought (sell).
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return False
        
        # Calculate RSI for CURRENT and PREVIOUS (QuantConnect LEAN pattern - same as momentum)
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        previous_rsi = self._calculate_rsi(closes[:-1], self.rsi_period)
        
        # Get adaptive thresholds
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # PRIMARY EVENT: RSI crosses UP through oversold level (same pattern as momentum crossover)
        # Allow 2-candle lookback for more realistic pattern detection
        if len(closes) >= self.min_history_required + 3:
            prev_prev_rsi = self._calculate_rsi(closes[:-2], self.rsi_period)
            
            # Oversold bounce: RSI was below threshold, now at/above
            oversold_bounce = (
                (prev_prev_rsi < oversold and current_rsi >= oversold) or
                (previous_rsi < oversold and current_rsi >= oversold)
            ) and current_rsi >= oversold  # Must still be at/above
            
            # Overbought rejection: RSI was above threshold, now at/below
            overbought_rejection = (
                (prev_prev_rsi > overbought and current_rsi <= overbought) or
                (previous_rsi > overbought and current_rsi <= overbought)
            ) and current_rsi <= overbought  # Must still be at/below
        else:
            # Fallback to current check if not enough history
            oversold_bounce = previous_rsi < oversold and current_rsi >= oversold
            overbought_rejection = previous_rsi > overbought and current_rsi <= overbought
        
        if not (oversold_bounce or overbought_rejection):
            return False  # No primary event (same pattern as momentum)
        
        # CONFIRMATION: Price should move in same direction as RSI bounce (same as momentum price confirmation)
        prev_close = closes[-2]
        current_close = closes[-1]
        
        if oversold_bounce:
            # RSI bouncing up - price should also be rising
            price_confirms = current_close > prev_close
        else:  # overbought_rejection
            # RSI rejecting down - price should also be falling
            price_confirms = current_close < prev_close
        
        return price_confirms
    
    def _get_diagnostic_info(self, symbol: str) -> str:
        """Get diagnostic information about why pattern didn't complete."""
        if symbol not in self.price_history:
            return "No price history"
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return f"Insufficient history: {len(history)} < {self.min_history_required + 2}"
        
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        previous_rsi = self._calculate_rsi(closes[:-1], self.rsi_period)
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        return f"RSI: prev={previous_rsi:.1f}, curr={current_rsi:.1f}, oversold<{oversold:.1f}, overbought>{overbought:.1f}"
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """
        Determine buy/sell action from RSI bounce event (QuantConnect LEAN pattern).
        ONLY returns action when bounce event just completed.
        """
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return None
        
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        previous_rsi = self._calculate_rsi(closes[:-1], self.rsi_period)
        
        # Get adaptive thresholds
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # OVERSOLD BOUNCE: RSI crosses UP through oversold = BUY (QuantConnect LEAN pattern)
        if previous_rsi < oversold and current_rsi >= oversold:
            return "buy"
        
        # OVERBOUGHT REJECTION: RSI crosses DOWN through overbought = SELL (QuantConnect LEAN pattern)
        if previous_rsi > overbought and current_rsi <= overbought:
            return "sell"
        
        # NO ACTION - bounce event hasn't completed yet
        return None
    
    def _build_signal(self, symbol: str, action: str) -> Optional[Dict[str, Any]]:
        """Build signal with entry, stop loss, take profit."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < 1:
            return None
        
        current_candle = history[-1]
        entry = current_candle['close']
        
        # Calculate mean and standard deviation for stop loss/take profit
        closes = [c['close'] for c in history[-20:]]  # Use 20-period mean
        mu = mean(closes)
        try:
            sigma = stdev(closes) if len(closes) > 1 else 0.0
        except:
            sigma = 0.0
        
        if sigma <= 0:
            sigma = entry * 0.02  # Default 2% if no volatility
        
        if action == "buy":
            # Stop loss below recent low, take profit at mean + 1.5 sigma
            # FIX: Filter out invalid lows (0.0 or negative) before calculating min
            recent_lows = [c.get('low', 0.0) for c in history[-10:] if c.get('low', 0.0) > 0]
            if not recent_lows:
                # No valid lows - use sigma-based stop loss as fallback
                stop_loss = entry - (sigma * 2.0)  # 2x sigma below entry
            else:
                stop_loss = min(recent_lows) * 0.995  # Slightly below recent low
                # Ensure stop_loss is below entry and valid
                if stop_loss >= entry or stop_loss <= 0:
                    stop_loss = entry - (sigma * 2.0)  # Fallback to sigma-based
            take_profit = mu + (sigma * 1.5)  # Target mean reversion
            # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
            max_take_profit = entry * 1.06  # +6% max
            if take_profit > max_take_profit:
                take_profit = max_take_profit
        elif action == "sell":
            # Stop loss above recent high, take profit at mean - 1.5 sigma
            # FIX: Filter out invalid highs (0.0 or negative) before calculating max
            recent_highs = [c.get('high', 0.0) for c in history[-10:] if c.get('high', 0.0) > 0]
            if not recent_highs:
                # No valid highs - use sigma-based stop loss as fallback
                stop_loss = entry + (sigma * 2.0)  # 2x sigma above entry
            else:
                stop_loss = max(recent_highs) * 1.005  # Slightly above recent high
                # Ensure stop_loss is above entry and valid
                if stop_loss <= entry or stop_loss <= 0:
                    stop_loss = entry + (sigma * 2.0)  # Fallback to sigma-based
            take_profit = mu - (sigma * 1.5)  # Target mean reversion
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
        
        # Calculate confidence based on RSI extreme and reversal strength
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        
        # Get adaptive thresholds for confidence calculation
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # More extreme RSI = higher confidence (using adaptive thresholds)
        if action == "buy":
            if oversold > 0:
                rsi_extreme = max(0.0, (oversold - current_rsi) / oversold)  # 0-1 scale
            else:
                rsi_extreme = 0.0
        else:
            denominator = 100 - overbought
            if denominator > 0:
                rsi_extreme = max(0.0, (current_rsi - overbought) / denominator)  # 0-1 scale
            else:
                rsi_extreme = 0.0
        
        rsi_confidence = min(0.5, rsi_extreme * 0.5)
        reversal_confidence = min(0.4, (reward / risk) / 5.0)  # Bonus for good R:R
        confidence = min(0.85, 0.5 + rsi_confidence + reversal_confidence)
        
        return {
            "strategy": self.name,
            "symbol": symbol,
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Mean reversion from extreme RSI {current_rsi:.1f} (threshold: {oversold:.1f}/{overbought:.1f}). Reversal beginning confirmed. Target: mean reversion to {mu:.4f}.",
            "requires_volume": False,
            "rsi": current_rsi,
            "rsi_oversold_threshold": oversold,
            "rsi_overbought_threshold": overbought,
            "volatility": self._calculate_volatility(closes),
        }
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """Legacy run method for backward compatibility."""
        return super().run(symbol, prices, **extra)
