# backend/app/strategies/vwap_strategy.py
"""
VWAP (Volume Weighted Average Price) Strategy
Institutional traders use VWAP as their PRIMARY reference - this is critical.

Key principles:
1. VWAP acts as dynamic support/resistance
2. Price above VWAP = bullish bias, below = bearish bias
3. Bounces/rejections from VWAP are high-probability signals
4. VWAP + volume confirmation = institutional-level accuracy

This is what makes signals "almost always true" - VWAP is where institutions trade.
"""
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class VWAPStrategy(StrategyBase):
    """
    VWAP-based strategy - institutional traders' primary tool.
    """
    name = "vwap"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50  # Need enough for VWAP calculation
        self.vwap_period = 20  # Standard VWAP period (can be session-based)
        self.bounce_threshold = 0.002  # 0.2% from VWAP to count as bounce
    
    def _calculate_vwap(self, history: List[Dict[str, Any]]) -> float:
        """
        Calculate VWAP (Volume Weighted Average Price).
        VWAP = Sum(Price * Volume) / Sum(Volume)
        """
        if not history:
            return 0.0
        
        # Use recent candles for VWAP (or session-based)
        recent_history = history[-self.vwap_period:] if len(history) >= self.vwap_period else history
        
        total_price_volume = 0.0
        total_volume = 0.0
        
        for candle in recent_history:
            # Typical price = (high + low + close) / 3
            typical_price = (
                candle.get('high', 0.0) + 
                candle.get('low', 0.0) + 
                candle.get('close', 0.0)
            ) / 3.0
            
            volume = candle.get('volume', 0.0)
            
            total_price_volume += typical_price * volume
            total_volume += volume
        
        if total_volume == 0:
            # Fallback to simple average if no volume
            closes = [c.get('close', 0.0) for c in recent_history]
            return mean(closes) if closes else 0.0
        
        return total_price_volume / total_volume
    
    def _check_vwap_bounce(self, history: List[Dict[str, Any]], vwap: float) -> Optional[str]:
        """
        Check if price bounced/rejected from VWAP.
        Returns "buy" if bullish bounce, "sell" if bearish rejection, None otherwise.
        """
        if len(history) < 2:
            return None
        
        current_candle = history[-1]
        prev_candle = history[-2]
        
        current_close = current_candle.get('close', 0.0)
        current_low = current_candle.get('low', 0.0)
        current_high = current_candle.get('high', 0.0)
        prev_close = prev_candle.get('close', 0.0)
        
        if vwap == 0:
            return None
        
        # Check for bullish bounce (price was below VWAP, now above)
        was_below = prev_close < vwap * (1 - self.bounce_threshold)
        now_above = current_close > vwap * (1 + self.bounce_threshold)
        touched_vwap = current_low <= vwap * (1 + self.bounce_threshold * 2)
        
        if was_below and now_above and touched_vwap:
            # Check for rejection wick (long lower wick = bounce)
            candle_range = current_high - current_low
            lower_wick = min(current_candle.get('open', current_close), current_close) - current_low
            if candle_range > 0 and lower_wick / candle_range >= 0.4:  # 40% wick = strong bounce
                return "buy"
        
        # Check for bearish rejection (price was above VWAP, now below)
        was_above = prev_close > vwap * (1 + self.bounce_threshold)
        now_below = current_close < vwap * (1 - self.bounce_threshold)
        touched_vwap = current_high >= vwap * (1 - self.bounce_threshold * 2)
        
        if was_above and now_below and touched_vwap:
            # Check for rejection wick (long upper wick = rejection)
            candle_range = current_high - current_low
            upper_wick = current_high - max(current_candle.get('open', current_close), current_close)
            if candle_range > 0 and upper_wick / candle_range >= 0.4:  # 40% wick = strong rejection
                return "sell"
        
        return None
    
    def _check_volume_confirmation(self, history: List[Dict[str, Any]]) -> bool:
        """Check if volume confirms the move (above average = strong signal)."""
        if len(history) < 20:
            return True  # No volume data
        
        volumes = [c.get('volume', 0.0) for c in history[-20:]]
        non_zero_volumes = [v for v in volumes if v > 0]
        
        if not non_zero_volumes:
            return True  # No volume data
        
        avg_volume = mean(non_zero_volumes)
        current_volume = volumes[-1] if volumes[-1] > 0 else 0.0
        
        return current_volume >= avg_volume * 1.2  # 20% above average
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price is near VWAP."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        vwap = self._calculate_vwap(history)
        if vwap == 0:
            return False
        
        current_price = history[-1].get('close', 0.0)
        
        # Pattern exists if price is near VWAP (within 1%)
        distance = abs(current_price - vwap) / vwap
        return distance < 0.01
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that price bounced/rejected from VWAP with volume.
        This is the key - VWAP bounces are highly reliable.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        vwap = self._calculate_vwap(history)
        if vwap == 0:
            return False
        
        # Check for bounce/rejection
        bounce = self._check_vwap_bounce(history, vwap)
        if not bounce:
            return False
        
        # Confirm with volume
        volume_ok = self._check_volume_confirmation(history)
        
        return volume_ok
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from VWAP bounce/rejection."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        vwap = self._calculate_vwap(history)
        if vwap == 0:
            return None
        
        return self._check_vwap_bounce(history, vwap)
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with VWAP-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        vwap = self._calculate_vwap(history)
        if vwap == 0:
            return None
        
        entry = history[-1].get('close', 0.0)
        
        if action == "buy":
            # Stop loss below VWAP (or recent low)
            recent_low = min([c.get('low', entry) for c in history[-10:]])
            stop_loss = min(recent_low * 0.998, vwap * 0.995)  # Below VWAP or recent low
            
            # Take profit at next resistance or 2:1 R:R
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0)  # 2:1 R:R
            
            # Cap at 4% max
            if take_profit > entry * 1.04:
                take_profit = entry * 1.04
        else:  # sell
            # Stop loss above VWAP (or recent high)
            recent_high = max([c.get('high', entry) for c in history[-10:]])
            stop_loss = max(recent_high * 1.002, vwap * 1.005)  # Above VWAP or recent high
            
            # Take profit at next support or 2:1 R:R
            risk = stop_loss - entry
            take_profit = entry - (risk * 2.0)  # 2:1 R:R
            
            # Cap at 4% max
            if take_profit < entry * 0.96:
                take_profit = entry * 0.96
        
        # Calculate confidence based on VWAP distance and volume
        vwap_distance = abs(entry - vwap) / vwap
        volume_ratio = history[-1].get('volume', 0.0) / mean([c.get('volume', 0.0) for c in history[-20:]]) if len(history) >= 20 else 1.0
        
        # Closer to VWAP + higher volume = higher confidence
        confidence = 0.65 + (0.25 if vwap_distance < 0.005 else 0.0) + (0.10 if volume_ratio > 1.5 else 0.0)
        confidence = min(0.90, confidence)  # Cap at 90%
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"VWAP bounce/rejection at {vwap:.4f} with volume confirmation",
            "strategy": self.name,
        }

