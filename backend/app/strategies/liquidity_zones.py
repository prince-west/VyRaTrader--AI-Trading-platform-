# backend/app/strategies/liquidity_zones.py
"""
Liquidity Zones Strategy - Stop Loss Clusters
Based on institutional trading: Institutions target areas where stop losses cluster.

Key principles:
1. Identify areas where stop losses cluster (above highs, below lows)
2. Institutions target these zones to trigger stops
3. Trade the liquidity grab = high win rate
4. This is "smart money" - they hunt retail stops

Liquidity Zones:
- Above recent highs = buy stop clusters (institutions sell to trigger)
- Below recent lows = sell stop clusters (institutions buy to trigger)
"""
from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase


class LiquidityZonesStrategy(StrategyBase):
    """
    Liquidity Zones strategy - trades institutional liquidity grabs.
    """
    name = "liquidity_zones"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50
        self.lookback_period = 20  # Look back 20 candles for highs/lows
        self.zone_threshold = 0.005  # 0.5% from zone to count as hit
    
    def _find_liquidity_zones(self, history: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Find liquidity zones (stop loss clusters).
        Returns: {"buy_stops": [...], "sell_stops": [...]}
        Buy stops = above recent highs (institutions sell to trigger)
        Sell stops = below recent lows (institutions buy to trigger)
        """
        if len(history) < self.lookback_period:
            return {"buy_stops": [], "sell_stops": []}
        
        recent_history = history[-self.lookback_period:]
        
        # Find recent highs (buy stop clusters above)
        highs = [c.get('high', 0.0) for c in recent_history if c.get('high', 0.0) > 0]
        if highs:
            max_high = max(highs)
            # Cluster highs within 0.5% of max (avoid division by zero)
            if max_high > 0:
                buy_stop_zones = [h for h in highs if abs(h - max_high) / max_high < 0.005]
            else:
                buy_stop_zones = []
        else:
            buy_stop_zones = []
        
        # Find recent lows (sell stop clusters below)
        lows = [c.get('low', 0.0) for c in recent_history if c.get('low', 0.0) > 0]
        if lows:
            min_low = min(lows)
            # Cluster lows within 0.5% of min (avoid division by zero)
            if min_low > 0:
                sell_stop_zones = [l for l in lows if abs(l - min_low) / min_low < 0.005]
            else:
                sell_stop_zones = []
        else:
            sell_stop_zones = []
        
        return {
            "buy_stops": list(set(buy_stop_zones)),  # Remove duplicates
            "sell_stops": list(set(sell_stop_zones)),
        }
    
    def _check_liquidity_grab(self, history: List[Dict[str, Any]], zones: Dict[str, List[float]]) -> Optional[str]:
        """
        Check if price grabbed liquidity (hit zone then reversed).
        Returns: "buy" if sell stop grab (bullish), "sell" if buy stop grab (bearish).
        """
        if len(history) < 3:
            return None
        
        current_candle = history[-1]
        prev_candle = history[-2]
        prev_prev_candle = history[-3]
        
        current_high = current_candle.get('high', 0.0)
        current_low = current_candle.get('low', 0.0)
        current_close = current_candle.get('close', 0.0)
        prev_close = prev_candle.get('close', 0.0)
        prev_prev_close = prev_prev_candle.get('close', 0.0)
        
        # Check buy stop grab (bearish): Price hit zone above highs, then reversed down
        for zone in zones["buy_stops"]:
            hit_zone = current_high >= zone * (1 - self.zone_threshold)
            reversed_down = current_close < prev_close and prev_close < prev_prev_close
            if hit_zone and reversed_down:
                return "sell"
        
        # Check sell stop grab (bullish): Price hit zone below lows, then reversed up
        for zone in zones["sell_stops"]:
            hit_zone = current_low <= zone * (1 + self.zone_threshold)
            reversed_up = current_close > prev_close and prev_close > prev_prev_close
            if hit_zone and reversed_up:
                return "buy"
        
        return None
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price is near a liquidity zone."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        zones = self._find_liquidity_zones(history)
        current_price = history[-1].get('close', 0.0)
        current_high = history[-1].get('high', 0.0)
        current_low = history[-1].get('low', 0.0)
        
        # Check if price is near any zone (avoid division by zero)
        for zone in zones["buy_stops"]:
            if zone > 0 and abs(current_high - zone) / zone < self.zone_threshold:
                return True
        
        for zone in zones["sell_stops"]:
            if zone > 0 and abs(current_low - zone) / zone < self.zone_threshold:
                return True
        
        return False
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that liquidity was grabbed (hit zone then reversed).
        This is the key - liquidity grabs are high-probability reversal signals.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        zones = self._find_liquidity_zones(history)
        grab = self._check_liquidity_grab(history, zones)
        
        return grab is not None
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from liquidity grab."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        zones = self._find_liquidity_zones(history)
        return self._check_liquidity_grab(history, zones)
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with liquidity zone-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        zones = self._find_liquidity_zones(history)
        entry = history[-1].get('close', 0.0)
        
        if action == "buy":
            # Sell stop grab: price hit lows, reversed up
            # Stop loss below the liquidity zone
            if zones["sell_stops"]:
                stop_loss = min(zones["sell_stops"]) * 0.995
            else:
                stop_loss = entry * 0.98
            
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0)  # 2:1 R:R
            
            if take_profit > entry * 1.04:
                take_profit = entry * 1.04
        else:  # sell
            # Buy stop grab: price hit highs, reversed down
            # Stop loss above the liquidity zone
            if zones["buy_stops"]:
                stop_loss = max(zones["buy_stops"]) * 1.005
            else:
                stop_loss = entry * 1.02
            
            risk = stop_loss - entry
            take_profit = entry - (risk * 2.0)  # 2:1 R:R
            
            if take_profit < entry * 0.96:
                take_profit = entry * 0.96
        
        # Very high confidence - liquidity grabs are extremely reliable
        confidence = 0.80 + (0.10 if (zones["buy_stops"] or zones["sell_stops"]) else 0.0)  # 80-90%
        
        zone_type = "sell stop grab" if action == "buy" else "buy stop grab"
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Liquidity grab - {zone_type} (institutional stop hunt)",
            "strategy": self.name,
        }

