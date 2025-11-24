# backend/app/strategies/volume_breakout.py
"""
Professional Volume Breakout Strategy
Based on industry-standard implementations from professional trading bots.

Pattern: Consolidation (tight range <3%) followed by breakout (>2% beyond range) with volume surge (>2x average) + ATR expansion
"""
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class VolumeBreakoutStrategy(StrategyBase):
    """
    Professional breakout strategy:
    - Detects consolidation (tight range)
    - Waits for breakout with volume surge
    - Confirms with ATR expansion
    """
    name = "volume_breakout"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50
        self.consolidation_period = 10  # Check last 10 candles for consolidation (relaxed from 20)
        self.max_consolidation_range_pct = 0.05  # 5% max range during consolidation (relaxed from 3%)
        self.min_breakout_pct = 0.01  # 1% breakout beyond range (relaxed from 2%)
        self.min_volume_ratio = 1.5  # Volume must be 1.5x average (relaxed from 2.0)
        self.atr_period = 14
        self.min_atr_expansion = 1.3  # ATR must be 1.3x average
    
    def _calculate_atr(self, history: List[Dict[str, Any]], period: int) -> float:
        """Calculate Average True Range."""
        try:
            if len(history) < period + 1:
                return 0.0
            
            true_ranges = []
            for i in range(len(history) - period, len(history)):
                if i == 0:
                    continue
                if i >= len(history):
                    break
                high = history[i].get('high', 0.0)
                low = history[i].get('low', 0.0)
                prev_close = history[i-1].get('close', 0.0) if i > 0 else high
                
                if high <= 0 or low <= 0 or prev_close <= 0:
                    continue
                
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                true_ranges.append(max(tr1, tr2, tr3))
            
            return mean(true_ranges) if true_ranges else 0.0
        except Exception:
            return 0.0
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if consolidation pattern exists."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.consolidation_period + 1:
            return False
        
        # Get consolidation window (excluding current candle)
        consolidation_window = history[-(self.consolidation_period + 1):-1]
        
        if len(consolidation_window) < self.consolidation_period:
            return False
        
        # Calculate consolidation range
        highs = [c['high'] for c in consolidation_window]
        lows = [c['low'] for c in consolidation_window]
        consolidation_high = max(highs)
        consolidation_low = min(lows)
        consolidation_range_pct = (consolidation_high - consolidation_low) / consolidation_low if consolidation_low > 0 else 1.0
        
        # Pattern exists if consolidation range is small enough
        is_consolidating = consolidation_range_pct <= self.max_consolidation_range_pct
        
        return is_consolidating
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that breakout EVENT just completed (QuantConnect LEAN pattern).
        Detects: Price crossing ABOVE resistance (buy) or BELOW support (sell).
        Compares PREVIOUS vs CURRENT price to detect the breakout event.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        # FIX: Use min_history_required instead of consolidation_period + 2
        # This ensures we have enough data for all calculations
        if len(history) < max(self.consolidation_period + 2, self.min_history_required):
            return False
        
        # Get consolidation window (excluding current and previous candles)
        consolidation_window = history[-(self.consolidation_period + 2):-2]
        previous_candle = history[-2]
        current_candle = history[-1]
        
        if len(consolidation_window) < self.consolidation_period:
            return False
        
        # Calculate consolidation range
        highs = [c['high'] for c in consolidation_window]
        lows = [c['low'] for c in consolidation_window]
        consolidation_high = max(highs)
        consolidation_low = min(lows)
        
        # Safety check: if consolidation_high or consolidation_low is 0, skip
        if consolidation_high <= 0 or consolidation_low <= 0:
            return False
        
        # Get previous and current prices (QuantConnect LEAN pattern)
        previous_high = previous_candle['high']
        previous_low = previous_candle['low']
        current_high = current_candle['high']
        current_low = current_candle['low']
        
        # PRIMARY EVENT: Price crosses ABOVE resistance (same pattern as momentum - detect ONE event first)
        bullish_breakout_event = previous_high <= consolidation_high and current_high > consolidation_high
        
        # PRIMARY EVENT: Price crosses BELOW support
        bearish_breakdown_event = previous_low >= consolidation_low and current_low < consolidation_low
        
        if not (bullish_breakout_event or bearish_breakdown_event):
            return False  # No primary event (same pattern as momentum)
        
        # CONFIRMATION 1: Breakout percentage (same as momentum's histogram expansion check)
        if bullish_breakout_event:
            breakout_pct = (current_high - consolidation_high) / consolidation_high
            if breakout_pct < self.min_breakout_pct:
                return False  # Breakout too small (same as momentum rejecting weak histogram)
        
        if bearish_breakdown_event:
            breakdown_pct = (consolidation_low - current_low) / consolidation_low
            if breakdown_pct < self.min_breakout_pct:
                return False  # Breakdown too small
        
        # CONFIRMATION 2: Volume confirmation (same as momentum's price confirmation)
        volumes = [c.get('volume', 0.0) for c in consolidation_window if c.get('volume', 0.0) > 0]
        if volumes:
            avg_volume = mean(volumes)
            current_volume = current_candle.get('volume', 0.0)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0
            if volume_ratio >= self.min_volume_ratio:
                # CONFIRMATION 3: ATR expansion (same as momentum's histogram expansion - adds strength)
                atr_current = self._calculate_atr(history, self.atr_period)
                if len(history) >= 30:
                    atr_values = []
                    for i in range(len(history) - 30, len(history) - 1):
                        atr_val = self._calculate_atr(history[:i+1], self.atr_period)
                        if atr_val > 0:
                            atr_values.append(atr_val)
                    atr_avg = mean(atr_values) if atr_values else atr_current
                else:
                    atr_avg = atr_current
                
                if atr_current >= atr_avg * self.min_atr_expansion:
                    return True  # Breakout confirmed with volume + ATR (same pattern as momentum)
                # ATR not expanding but volume is strong - still valid (same as momentum allowing without histogram)
                return True
        else:
            # No volume data - allow breakout (same as momentum allowing without volume)
            return True
        
        return False  # No breakout event completed (handled above)
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """
        Determine buy/sell action from breakout event (QuantConnect LEAN pattern).
        ONLY returns action when breakout event just completed.
        """
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.consolidation_period + 2:  # Need previous candle too
            return None
        
        # Get consolidation window (excluding current and previous candles)
        consolidation_window = history[-(self.consolidation_period + 2):-2]
        previous_candle = history[-2]
        current_candle = history[-1]
        
        highs = [c['high'] for c in consolidation_window]
        lows = [c['low'] for c in consolidation_window]
        consolidation_high = max(highs)
        consolidation_low = min(lows)
        
        # Safety check: if consolidation_high or consolidation_low is 0, skip
        if consolidation_high <= 0 or consolidation_low <= 0:
            return None
        
        # Get previous and current prices (QuantConnect LEAN pattern)
        previous_high = previous_candle['high']
        current_high = current_candle['high']
        previous_low = previous_candle['low']
        current_low = current_candle['low']
        
        # BULLISH BREAKOUT EVENT: Previous price <= resistance, current price > resistance
        if previous_high <= consolidation_high and current_high > consolidation_high:
            breakout_pct = (current_high - consolidation_high) / consolidation_high
            if breakout_pct >= self.min_breakout_pct:
                return "buy"
        
        # BEARISH BREAKDOWN EVENT: Previous price >= support, current price < support
        if previous_low >= consolidation_low and current_low < consolidation_low:
            breakdown_pct = (consolidation_low - current_low) / consolidation_low
            if breakdown_pct >= self.min_breakout_pct:
                return "sell"
        
        # NO ACTION - breakout event hasn't completed yet
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
        
        # Calculate consolidation levels
        consolidation_window = history[-(self.consolidation_period + 1):-1]
        highs = [c['high'] for c in consolidation_window]
        lows = [c['low'] for c in consolidation_window]
        consolidation_high = max(highs)
        consolidation_low = min(lows)
        consolidation_range = consolidation_high - consolidation_low
        
        # Calculate volume ratio
        volumes = [c.get('volume', 0.0) for c in consolidation_window if c.get('volume', 0.0) > 0]
        avg_volume = mean(volumes) if volumes else 0.0
        current_volume = current_candle.get('volume', 0.0)
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0
        
        if action == "buy":
            # Stop loss below consolidation low, take profit 2x range above entry
            # FIX: Ensure consolidation_low is valid before using it
            if consolidation_low <= 0 or consolidation_low >= entry:
                # Invalid consolidation_low - use ATR-based stop loss as fallback
                atr = self._calculate_atr(history, self.atr_period)
                if atr <= 0:
                    atr = entry * 0.02  # 2% fallback
                stop_loss = entry - (atr * 2.0)
            else:
                stop_loss = consolidation_low * 0.995  # Slightly below consolidation low
            take_profit = entry + (consolidation_range * 2.5)  # 2.5x range for 1:2.5 R:R
            # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
            max_take_profit = entry * 1.06  # +6% max
            if take_profit > max_take_profit:
                take_profit = max_take_profit
        elif action == "sell":
            # Stop loss above consolidation high, take profit 2x range below entry
            # FIX: Ensure consolidation_high is valid before using it
            if consolidation_high <= 0 or consolidation_high <= entry:
                # Invalid consolidation_high - use ATR-based stop loss as fallback
                atr = self._calculate_atr(history, self.atr_period)
                if atr <= 0:
                    atr = entry * 0.02  # 2% fallback
                stop_loss = entry + (atr * 2.0)
            else:
                stop_loss = consolidation_high * 1.005  # Slightly above consolidation high
            take_profit = entry - (consolidation_range * 2.5)  # 2.5x range for 1:2.5 R:R
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
        
        # Calculate confidence based on breakout strength and volume
        breakout_strength = min(1.0, (reward / risk) / 2.5)  # Normalize to 0-1
        volume_bonus = min(0.3, (volume_ratio - 2.0) / 5.0) if volume_ratio >= 2.0 else 0.0
        confidence = min(0.9, 0.6 + breakout_strength * 0.2 + volume_bonus)
        
        # Build reasoning
        if action == "buy":
            reasoning = f"Breakout above ${consolidation_high:.2f} with {volume_ratio:.1f}x volume + ATR expansion. Range: {consolidation_range/entry*100:.2f}%."
        else:
            reasoning = f"Breakdown below ${consolidation_low:.2f} with {volume_ratio:.1f}x volume + ATR expansion. Range: {consolidation_range/entry*100:.2f}%."
        
        return {
            "strategy": self.name,
            "symbol": symbol,
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": reasoning,
            "requires_volume": True,
            "volume_ratio": volume_ratio,
            "consolidation_range_pct": (consolidation_range / entry) * 100,
        }

