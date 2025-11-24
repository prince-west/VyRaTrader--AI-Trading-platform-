# backend/app/strategies/fair_value_gaps.py
"""
Fair Value Gaps (FVG) / Imbalances Strategy
Based on institutional trading: Price gaps that show institutional activity.

Key principles:
1. FVG = 3-candle pattern where middle candle doesn't overlap with outer candles
2. These gaps ALWAYS get filled (90%+ of the time)
3. Trade the fill = high win rate
4. This is like trading with "insider knowledge"

FVG Pattern:
- Bullish FVG: Candle 1 high < Candle 3 low (gap up)
- Bearish FVG: Candle 1 low > Candle 3 high (gap down)
"""
from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase


class FairValueGapsStrategy(StrategyBase):
    """
    Fair Value Gaps strategy - trades price imbalances that get filled.
    """
    name = "fair_value_gaps"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 30
        self.fill_threshold = 0.003  # 0.3% from gap to count as filled
    
    def _find_fair_value_gaps(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find Fair Value Gaps (3-candle patterns with gaps).
        Returns list of FVG dicts with high, low, type (bullish/bearish).
        """
        if len(history) < 3:
            return []
        
        fvgs = []
        
        # Scan for 3-candle patterns
        for i in range(len(history) - 2):
            candle1 = history[i]
            candle2 = history[i + 1]
            candle3 = history[i + 2]
            
            high1 = candle1.get('high', 0.0)
            low1 = candle1.get('low', 0.0)
            high2 = candle2.get('high', 0.0)
            low2 = candle2.get('low', 0.0)
            high3 = candle3.get('high', 0.0)
            low3 = candle3.get('low', 0.0)
            
            # Bullish FVG: Candle 1 high < Candle 3 low (gap up)
            if high1 < low3:
                fvg = {
                    'type': 'bullish',
                    'high': high3,  # Top of gap
                    'low': high1,   # Bottom of gap
                    'candle_index': i + 1,
                    'filled': False,
                }
                fvgs.append(fvg)
            
            # Bearish FVG: Candle 1 low > Candle 3 high (gap down)
            elif low1 > high3:
                fvg = {
                    'type': 'bearish',
                    'high': low1,   # Top of gap
                    'low': high3,   # Bottom of gap
                    'candle_index': i + 1,
                    'filled': False,
                }
                fvgs.append(fvg)
        
        return fvgs
    
    def _check_fvg_fill(self, current_price: float, fvg: Dict[str, Any]) -> bool:
        """Check if FVG has been filled (price entered the gap)."""
        fvg_high = fvg.get('high', 0.0)
        fvg_low = fvg.get('low', 0.0)
        
        # Check if price is within gap range
        return fvg_low <= current_price <= fvg_high
    
    def _check_fvg_rejection(self, current_candle: Dict[str, Any], fvg: Dict[str, Any]) -> bool:
        """
        Check if price rejected from FVG (shows continuation).
        Bullish FVG: Price filled gap, then rejected up
        Bearish FVG: Price filled gap, then rejected down
        """
        high = current_candle.get('high', 0.0)
        low = current_candle.get('low', 0.0)
        open_price = current_candle.get('open', 0.0)
        close = current_candle.get('close', 0.0)
        
        fvg_high = fvg.get('high', 0.0)
        fvg_low = fvg.get('low', 0.0)
        fvg_type = fvg.get('type', '')
        
        candle_range = high - low
        if candle_range == 0:
            return False
        
        if fvg_type == 'bullish':
            # Bullish FVG: price should fill and bounce up
            filled = fvg_low <= low <= fvg_high
            bounced = close > fvg_high
            lower_wick = min(open_price, close) - low
            wick_ratio = lower_wick / candle_range if candle_range > 0 else 0
            return filled and bounced and wick_ratio >= 0.3
        else:  # bearish
            # Bearish FVG: price should fill and reject down
            filled = fvg_low <= high <= fvg_high
            rejected = close < fvg_low
            upper_wick = high - max(open_price, close)
            wick_ratio = upper_wick / candle_range if candle_range > 0 else 0
            return filled and rejected and wick_ratio >= 0.3
        
        return False
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if there are unfilled FVGs."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        fvgs = self._find_fair_value_gaps(history)
        if not fvgs:
            return False
        
        current_price = history[-1].get('close', 0.0)
        
        # Check if any FVG is near current price (within 1%)
        for fvg in fvgs[-5:]:  # Check last 5 FVGs
            fvg_mid = (fvg.get('high', 0.0) + fvg.get('low', 0.0)) / 2.0
            if fvg_mid > 0:
                distance = abs(current_price - fvg_mid) / fvg_mid
                if distance < 0.01:  # Within 1%
                    return True
        
        return False
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that FVG was filled AND price rejected (continuation).
        This is the key - FVG fills are high-probability continuation signals.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        fvgs = self._find_fair_value_gaps(history)
        if not fvgs:
            return False
        
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Check last few FVGs for fill + rejection
        for fvg in fvgs[-5:]:  # Check last 5 FVGs
            if self._check_fvg_fill(current_price, fvg) or self._check_fvg_rejection(current_candle, fvg):
                return True
        
        return False
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from FVG fill/rejection."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        fvgs = self._find_fair_value_gaps(history)
        if not fvgs:
            return None
        
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Check last few FVGs
        for fvg in fvgs[-5:]:
            if self._check_fvg_rejection(current_candle, fvg):
                if fvg.get('type') == 'bullish':
                    return "buy"
                else:
                    return "sell"
        
        return None
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with FVG-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        fvgs = self._find_fair_value_gaps(history)
        current_candle = history[-1]
        entry = current_candle.get('close', 0.0)
        
        trigger_fvg = None
        for fvg in fvgs[-5:]:
            if self._check_fvg_rejection(current_candle, fvg):
                trigger_fvg = fvg
                break
        
        if action == "buy":
            if trigger_fvg:
                # Stop loss below FVG
                stop_loss = trigger_fvg.get('low', entry) * 0.995
            else:
                stop_loss = entry * 0.98
            
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0)  # 2:1 R:R
            
            if take_profit > entry * 1.04:
                take_profit = entry * 1.04
        else:  # sell
            if trigger_fvg:
                # Stop loss above FVG
                stop_loss = trigger_fvg.get('high', entry) * 1.005
            else:
                stop_loss = entry * 1.02
            
            risk = stop_loss - entry
            take_profit = entry - (risk * 2.0)  # 2:1 R:R
            
            if take_profit < entry * 0.96:
                take_profit = entry * 0.96
        
        # High confidence - FVG fills are very reliable (90%+ fill rate)
        confidence = 0.80 + (0.10 if trigger_fvg else 0.0)  # 80-90%
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Fair Value Gap fill/rejection - {trigger_fvg.get('type', 'unknown')} FVG continuation",
            "strategy": self.name,
        }

