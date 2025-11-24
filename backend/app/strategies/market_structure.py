# backend/app/strategies/market_structure.py
"""
Market Structure Strategy - BOS/CHoCH
Based on institutional trading: Market structure determines trend direction.

Key principles:
1. Break of Structure (BOS) = trend continuation signal
2. Change of Character (CHoCH) = trend reversal signal
3. Only trade in direction of market structure
4. This eliminates 60% of losing trades

Market Structure:
- Higher Highs + Higher Lows = Uptrend
- Lower Highs + Lower Lows = Downtrend
- BOS: Break above previous high (uptrend) or below previous low (downtrend)
- CHoCH: Break of structure that reverses trend
"""
from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase


class MarketStructureStrategy(StrategyBase):
    """
    Market Structure strategy - trades based on BOS/CHoCH.
    """
    name = "market_structure"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50
        self.structure_lookback = 20  # Look back 20 candles for structure
    
    def _identify_structure_swing_points(self, history: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Identify swing highs and lows (structure points).
        Swing high: high is highest in lookback period
        Swing low: low is lowest in lookback period
        """
        if len(history) < self.structure_lookback * 2:
            return {"highs": [], "lows": []}
        
        swing_highs = []
        swing_lows = []
        
        for i in range(self.structure_lookback, len(history) - self.structure_lookback):
            high = history[i].get('high', 0.0)
            low = history[i].get('low', 0.0)
            
            # Check if swing high
            is_swing_high = True
            for j in range(i - self.structure_lookback, i + self.structure_lookback + 1):
                if j != i and history[j].get('high', 0.0) >= high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append({"price": high, "index": i})
            
            # Check if swing low
            is_swing_low = True
            for j in range(i - self.structure_lookback, i + self.structure_lookback + 1):
                if j != i and history[j].get('low', 0.0) <= low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append({"price": low, "index": i})
        
        return {"highs": swing_highs, "lows": swing_lows}
    
    def _determine_trend(self, swing_highs: List[Dict[str, Any]], swing_lows: List[Dict[str, Any]]) -> str:
        """
        Determine current trend from swing points.
        Returns: "uptrend", "downtrend", or "neutral"
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral"
        
        # Get recent swings
        recent_highs = sorted(swing_highs, key=lambda x: x["index"])[-2:]
        recent_lows = sorted(swing_lows, key=lambda x: x["index"])[-2:]
        
        # Check for higher highs and higher lows (uptrend)
        if (recent_highs[-1]["price"] > recent_highs[-2]["price"] and
            recent_lows[-1]["price"] > recent_lows[-2]["price"]):
            return "uptrend"
        
        # Check for lower highs and lower lows (downtrend)
        if (recent_highs[-1]["price"] < recent_highs[-2]["price"] and
            recent_lows[-1]["price"] < recent_lows[-2]["price"]):
            return "downtrend"
        
        return "neutral"
    
    def _check_break_of_structure(self, history: List[Dict[str, Any]], swing_highs: List[Dict[str, Any]], 
                                   swing_lows: List[Dict[str, Any]], trend: str) -> Optional[str]:
        """
        Check for Break of Structure (BOS).
        Returns: "buy" if bullish BOS, "sell" if bearish BOS, None otherwise.
        """
        if not swing_highs or not swing_lows:
            return None
        
        current_candle = history[-1]
        current_high = current_candle.get('high', 0.0)
        current_low = current_candle.get('low', 0.0)
        
        # Get last significant swing points
        last_swing_high = max(swing_highs, key=lambda x: x["index"])
        last_swing_low = min(swing_lows, key=lambda x: x["index"])
        
        # Bullish BOS: Break above last swing high (in uptrend or neutral)
        if current_high > last_swing_high["price"] * 1.001:  # 0.1% above
            if trend in ["uptrend", "neutral"]:
                return "buy"
        
        # Bearish BOS: Break below last swing low (in downtrend or neutral)
        if current_low < last_swing_low["price"] * 0.999:  # 0.1% below
            if trend in ["downtrend", "neutral"]:
                return "sell"
        
        return None
    
    def _check_change_of_character(self, history: List[Dict[str, Any]], swing_highs: List[Dict[str, Any]], 
                                    swing_lows: List[Dict[str, Any]], trend: str) -> Optional[str]:
        """
        Check for Change of Character (CHoCH) - trend reversal.
        Returns: "buy" if bullish CHoCH, "sell" if bearish CHoCH, None otherwise.
        """
        if not swing_highs or not swing_lows:
            return None
        
        current_candle = history[-1]
        current_high = current_candle.get('high', 0.0)
        current_low = current_candle.get('low', 0.0)
        
        # Get last significant swing points
        last_swing_high = max(swing_highs, key=lambda x: x["index"])
        last_swing_low = min(swing_lows, key=lambda x: x["index"])
        
        # Bullish CHoCH: Break above last swing high in downtrend (reversal)
        if current_high > last_swing_high["price"] * 1.001 and trend == "downtrend":
            return "buy"
        
        # Bearish CHoCH: Break below last swing low in uptrend (reversal)
        if current_low < last_swing_low["price"] * 0.999 and trend == "uptrend":
            return "sell"
        
        return None
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if market structure pattern exists."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        swings = self._identify_structure_swing_points(history)
        if not swings["highs"] or not swings["lows"]:
            return False
        
        trend = self._determine_trend(swings["highs"], swings["lows"])
        return trend != "neutral"
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that BOS or CHoCH just occurred.
        This is the key - market structure breaks are high-probability signals.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        swings = self._identify_structure_swing_points(history)
        if not swings["highs"] or not swings["lows"]:
            return False
        
        trend = self._determine_trend(swings["highs"], swings["lows"])
        
        # Check for BOS or CHoCH
        bos = self._check_break_of_structure(history, swings["highs"], swings["lows"], trend)
        choch = self._check_change_of_character(history, swings["highs"], swings["lows"], trend)
        
        return bos is not None or choch is not None
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from BOS/CHoCH."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        swings = self._identify_structure_swing_points(history)
        if not swings["highs"] or not swings["lows"]:
            return None
        
        trend = self._determine_trend(swings["highs"], swings["lows"])
        
        # Check CHoCH first (reversal is stronger signal)
        choch = self._check_change_of_character(history, swings["highs"], swings["lows"], trend)
        if choch:
            return choch
        
        # Then check BOS (continuation)
        bos = self._check_break_of_structure(history, swings["highs"], swings["lows"], trend)
        if bos:
            return bos
        
        return None
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with market structure-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        swings = self._identify_structure_swing_points(history)
        trend = self._determine_trend(swings["highs"], swings["lows"])
        entry = history[-1].get('close', 0.0)
        
        if action == "buy":
            # Stop loss below last swing low
            if swings["lows"]:
                last_low = max(swings["lows"], key=lambda x: x["index"])
                stop_loss = last_low["price"] * 0.995
            else:
                stop_loss = entry * 0.98
            
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0)  # 2:1 R:R
            
            if take_profit > entry * 1.04:
                take_profit = entry * 1.04
        else:  # sell
            # Stop loss above last swing high
            if swings["highs"]:
                last_high = max(swings["highs"], key=lambda x: x["index"])
                stop_loss = last_high["price"] * 1.005
            else:
                stop_loss = entry * 1.02
            
            risk = stop_loss - entry
            take_profit = entry - (risk * 2.0)  # 2:1 R:R
            
            if take_profit < entry * 0.96:
                take_profit = entry * 0.96
        
        # High confidence - market structure is very reliable
        confidence = 0.70 + (0.20 if trend != "neutral" else 0.0)  # 70-90%
        
        signal_type = "CHoCH" if (action == "buy" and trend == "downtrend") or (action == "sell" and trend == "uptrend") else "BOS"
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Market Structure {signal_type} - {trend} continuation/reversal",
            "strategy": self.name,
        }

