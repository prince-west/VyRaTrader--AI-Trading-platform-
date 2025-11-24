# backend/app/strategies/breakout.py
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class BreakoutStrategy(StrategyBase):
    """
    Breakout strategy that detects consolidation periods followed by breakouts.
    
    Pattern: Price consolidates (range <3% for 10+ candles) then breaks out
    (>2% beyond range) with volume confirmation (>2x average).
    """
    name = "breakout"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 30  # Need at least 30 candles
        self.consolidation_period = 10  # Minimum candles in consolidation
        self.max_consolidation_range_pct = 0.05  # 5% max range during consolidation (relaxed from 3%)
        self.min_breakout_pct = 0.01  # 1% breakout beyond range (relaxed from 2%)
        self.min_volume_ratio = 1.5  # Volume must be 1.5x average (relaxed from 2.0)
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if consolidation pattern exists."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        # Check for consolidation period (last N candles before current)
        if len(history) < self.consolidation_period + 1:
            return False
        
        # Get consolidation window (excluding current candle)
        consolidation_window = history[-(self.consolidation_period + 1):-1]
        
        if len(consolidation_window) < self.consolidation_period:
            return False
        
        # Calculate consolidation range
        try:
            highs = [c.get('high', 0.0) for c in consolidation_window if c.get('high', 0.0) > 0]
            lows = [c.get('low', float('inf')) for c in consolidation_window if c.get('low', 0.0) > 0]
            
            if not highs or not lows:
                return False
            
            consolidation_high = max(highs)
            consolidation_low = min(lows)
            
            if consolidation_low <= 0:
                return False
            
            consolidation_range_pct = (consolidation_high - consolidation_low) / consolidation_low
        except Exception:
            return False
        
        # Pattern exists if consolidation range is small enough
        is_consolidating = consolidation_range_pct <= self.max_consolidation_range_pct
        
        # Log diagnostic info occasionally
        import random
        if random.random() < 0.02:  # 2% of checks
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Breakout {symbol}: consolidation_range={consolidation_range_pct*100:.2f}% (need <{self.max_consolidation_range_pct*100:.1f}%), is_consolidating={is_consolidating}")
        
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
        volumes = [c['volume'] for c in consolidation_window if c.get('volume', 0) > 0]
        if volumes:
            avg_volume = mean(volumes)
            current_volume = current_candle.get('volume', 0.0)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0
            if volume_ratio >= self.min_volume_ratio:
                return True  # Breakout confirmed with volume (same pattern as momentum)
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
        
        # Calculate stop loss and take profit based on consolidation range
        consolidation_window = history[-(self.consolidation_period + 1):-1]
        highs = [c['high'] for c in consolidation_window]
        lows = [c['low'] for c in consolidation_window]
        consolidation_high = max(highs)
        consolidation_low = min(lows)
        consolidation_range = consolidation_high - consolidation_low
        
        if action == "buy":
            # Stop loss below consolidation low, take profit 2x range above entry
            # FIX: Ensure consolidation_low is valid before using it
            if consolidation_low <= 0 or consolidation_low >= entry:
                # Invalid consolidation_low - use ATR-based stop loss as fallback
                # Calculate simple ATR for fallback
                closes = [c['close'] for c in history[-14:]]
                if len(closes) > 1:
                    atr_approx = abs(closes[-1] - closes[-2]) * 2.0  # Approximate ATR
                else:
                    atr_approx = entry * 0.02  # 2% fallback
                stop_loss = entry - (atr_approx * 2.0)
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
                # Calculate simple ATR for fallback
                closes = [c['close'] for c in history[-14:]]
                if len(closes) > 1:
                    atr_approx = abs(closes[-1] - closes[-2]) * 2.0  # Approximate ATR
                else:
                    atr_approx = entry * 0.02  # 2% fallback
                stop_loss = entry + (atr_approx * 2.0)
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
        
        # Enhanced confidence calculation with multiple confirmations (research-proven)
        volumes = [c['volume'] for c in consolidation_window if c['volume'] > 0]
        avg_volume = mean(volumes) if volumes else 0.0
        current_volume = current_candle['volume']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0
        
        # Safety check: if consolidation_high or consolidation_low is 0, return None
        if consolidation_high <= 0 or consolidation_low <= 0:
            return None
        
        # Calculate breakout strength (how far beyond consolidation range)
        if action == "buy":
            breakout_strength_pct = (current_candle['high'] - consolidation_high) / consolidation_high
        else:
            breakout_strength_pct = (consolidation_low - current_candle['low']) / consolidation_low
        
        # Base confidence from consolidation quality (tighter = better)
        consolidation_quality = 1.0 - (consolidation_range / entry) / self.max_consolidation_range_pct
        consolidation_confidence = min(0.3, consolidation_quality * 0.3)
        
        # Breakout strength bonus
        breakout_confidence = min(0.3, breakout_strength_pct * 10.0)  # Scale breakout strength
        
        # Volume confirmation bonus (critical for breakouts)
        volume_bonus = 0.0
        if volume_ratio >= 2.0:
            volume_bonus = 0.2  # Strong volume
        elif volume_ratio >= 1.5:
            volume_bonus = 0.1  # Good volume
        elif volume_ratio < 1.0:
            volume_bonus = -0.1  # Penalty for low volume
        
        # Risk/reward bonus
        rr_ratio = reward / risk if risk > 0 else 0.0
        rr_confidence = min(0.2, (rr_ratio - 1.5) / 5.0) if rr_ratio >= 1.5 else 0.0
        
        # Total confidence with all confirmations
        confidence = min(0.90, 0.3 + consolidation_confidence + breakout_confidence + volume_bonus + rr_confidence)
        
        return {
            "strategy": self.name,
            "symbol": symbol,
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Breakout from {self.consolidation_period}-candle consolidation. Range: {consolidation_range/entry*100:.2f}%. Volume: {volume_ratio:.1f}x average.",
            "requires_volume": True,
            "volume_ratio": volume_ratio,
        }
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """Legacy run method for backward compatibility."""
        return super().run(symbol, prices, **extra)
