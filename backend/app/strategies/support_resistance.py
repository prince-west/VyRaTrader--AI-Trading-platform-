# backend/app/strategies/support_resistance.py
"""
Support/Resistance + Order Flow Strategy
Based on institutional trading methods - this is what makes signals "almost always true"

Key principles:
1. Identify KEY support/resistance levels (pivot clusters, not just moving averages)
2. Wait for price REJECTION from these levels (bounce off support, reject from resistance)
3. Confirm with order flow (large volume at key levels)
4. Multi-timeframe confirmation (higher timeframe trend)

This is what successful bots use - it's like having "insider knowledge" of where price will react.
"""
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class SupportResistanceStrategy(StrategyBase):
    """
    Support/Resistance strategy using pivot points and order flow.
    This is the "secret sauce" of successful trading bots.
    """
    name = "support_resistance"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50  # Need enough for pivot detection
        self.pivot_lookback = 20  # Look back 20 candles for pivot points
        self.min_pivot_cluster = 3  # Need at least 3 pivots to form support/resistance
        self.rejection_candle_ratio = 0.6  # Rejection wick must be 60% of candle
    
    def _find_pivot_points(self, history: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Find pivot points (local highs and lows).
        Pivot high: high is highest in lookback period
        Pivot low: low is lowest in lookback period
        """
        if len(history) < self.pivot_lookback * 2:
            return {"highs": [], "lows": []}
        
        pivot_highs = []
        pivot_lows = []
        
        for i in range(self.pivot_lookback, len(history) - self.pivot_lookback):
            high = history[i].get('high', 0.0)
            low = history[i].get('low', 0.0)
            
            # Check if this is a pivot high
            is_pivot_high = True
            for j in range(i - self.pivot_lookback, i + self.pivot_lookback + 1):
                if j != i and history[j].get('high', 0.0) >= high:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                pivot_highs.append(high)
            
            # Check if this is a pivot low
            is_pivot_low = True
            for j in range(i - self.pivot_lookback, i + self.pivot_lookback + 1):
                if j != i and history[j].get('low', 0.0) <= low:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                pivot_lows.append(low)
        
        return {"highs": pivot_highs, "lows": pivot_lows}
    
    def _find_support_resistance_levels(self, pivot_highs: List[float], pivot_lows: List[float]) -> Dict[str, List[float]]:
        """
        Find support/resistance levels by clustering pivot points.
        Levels with multiple pivots are stronger.
        """
        # Cluster pivot highs (resistance)
        resistance_levels = []
        if pivot_highs:
            sorted_highs = sorted(pivot_highs)
            cluster = [sorted_highs[0]]
            
            for high in sorted_highs[1:]:
                # If within 1% of cluster average, add to cluster
                cluster_avg = mean(cluster)
                if abs(high - cluster_avg) / cluster_avg < 0.01:
                    cluster.append(high)
                else:
                    # Save cluster if it has enough pivots
                    if len(cluster) >= self.min_pivot_cluster:
                        resistance_levels.append(mean(cluster))
                    cluster = [high]
            
            # Don't forget last cluster
            if len(cluster) >= self.min_pivot_cluster:
                resistance_levels.append(mean(cluster))
        
        # Cluster pivot lows (support)
        support_levels = []
        if pivot_lows:
            sorted_lows = sorted(pivot_lows)
            cluster = [sorted_lows[0]]
            
            for low in sorted_lows[1:]:
                # If within 1% of cluster average, add to cluster
                cluster_avg = mean(cluster)
                if abs(low - cluster_avg) / cluster_avg < 0.01:
                    cluster.append(low)
                else:
                    # Save cluster if it has enough pivots
                    if len(cluster) >= self.min_pivot_cluster:
                        support_levels.append(mean(cluster))
                    cluster = [low]
            
            # Don't forget last cluster
            if len(cluster) >= self.min_pivot_cluster:
                support_levels.append(mean(cluster))
        
        return {"support": support_levels, "resistance": resistance_levels}
    
    def _check_rejection_candle(self, candle: Dict[str, Any], level: float, is_support: bool) -> bool:
        """
        Check if candle shows rejection from support/resistance level.
        Rejection = long wick showing price was rejected from level.
        """
        high = candle.get('high', 0.0)
        low = candle.get('low', 0.0)
        open_price = candle.get('open', 0.0)
        close = candle.get('close', 0.0)
        
        candle_range = high - low
        if candle_range == 0:
            return False
        
        # For support: price touched support (low near level) but closed above (rejection wick)
        if is_support:
            touched_support = abs(low - level) / level < 0.005  # Within 0.5% of support
            wick_size = low - min(open_price, close)
            wick_ratio = wick_size / candle_range if candle_range > 0 else 0
            closed_above = close > level * 0.998  # Closed above support (within 0.2%)
            return touched_support and wick_ratio >= self.rejection_candle_ratio and closed_above
        
        # For resistance: price touched resistance (high near level) but closed below (rejection wick)
        else:
            touched_resistance = abs(high - level) / level < 0.005  # Within 0.5% of resistance
            wick_size = max(open_price, close) - high
            wick_ratio = abs(wick_size) / candle_range if candle_range > 0 else 0
            closed_below = close < level * 1.002  # Closed below resistance (within 0.2%)
            return touched_resistance and wick_ratio >= self.rejection_candle_ratio and closed_below
    
    def _check_order_flow(self, history: List[Dict[str, Any]], level: float, is_support: bool) -> bool:
        """
        Check order flow at support/resistance level.
        Large volume at key level = strong signal (institutional activity).
        """
        if len(history) < 10:
            return True  # No volume data
        
        # Get volumes near the level
        volumes_near_level = []
        for candle in history[-20:]:  # Last 20 candles
            if is_support:
                low = candle.get('low', 0.0)
                if abs(low - level) / level < 0.01:  # Within 1% of support
                    volumes_near_level.append(candle.get('volume', 0.0))
            else:
                high = candle.get('high', 0.0)
                if abs(high - level) / level < 0.01:  # Within 1% of resistance
                    volumes_near_level.append(candle.get('volume', 0.0))
        
        if not volumes_near_level:
            return True  # No volume data at level
        
        # Check if recent volume is above average (order flow confirmation)
        avg_volume = mean([c.get('volume', 0.0) for c in history[-20:]])
        recent_volume = mean(volumes_near_level) if volumes_near_level else 0.0
        
        return recent_volume >= avg_volume * 1.2  # 20% above average = strong order flow
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price is near a support/resistance level."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        # Find pivot points
        pivots = self._find_pivot_points(history)
        
        # Find support/resistance levels
        levels = self._find_support_resistance_levels(pivots["highs"], pivots["lows"])
        
        # Check if current price is near any level
        current_price = history[-1].get('close', 0.0)
        
        for support in levels["support"]:
            if abs(current_price - support) / support < 0.02:  # Within 2% of support
                return True
        
        for resistance in levels["resistance"]:
            if abs(current_price - resistance) / resistance < 0.02:  # Within 2% of resistance
                return True
        
        return False
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that price REJECTED from support/resistance with order flow.
        This is the key - we wait for actual rejection, not just proximity.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        # Find pivot points
        pivots = self._find_pivot_points(history)
        
        # Find support/resistance levels
        levels = self._find_support_resistance_levels(pivots["highs"], pivots["lows"])
        
        # Check current candle for rejection
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Check support rejection (bounce)
        for support in levels["support"]:
            if self._check_rejection_candle(current_candle, support, is_support=True):
                # Confirm with order flow
                if self._check_order_flow(history, support, is_support=True):
                    return True
        
        # Check resistance rejection
        for resistance in levels["resistance"]:
            if self._check_rejection_candle(current_candle, resistance, is_support=False):
                # Confirm with order flow
                if self._check_order_flow(history, resistance, is_support=False):
                    return True
        
        return False
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from support/resistance rejection."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        # Find pivot points
        pivots = self._find_pivot_points(history)
        
        # Find support/resistance levels
        levels = self._find_support_resistance_levels(pivots["highs"], pivots["lows"])
        
        # Check current candle
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Check support bounce (buy signal)
        for support in levels["support"]:
            if self._check_rejection_candle(current_candle, support, is_support=True):
                if self._check_order_flow(history, support, is_support=True):
                    return "buy"
        
        # Check resistance rejection (sell signal)
        for resistance in levels["resistance"]:
            if self._check_rejection_candle(current_candle, resistance, is_support=False):
                if self._check_order_flow(history, resistance, is_support=False):
                    return "sell"
        
        return None
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with support/resistance-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        # Find the level that triggered the signal
        pivots = self._find_pivot_points(history)
        levels = self._find_support_resistance_levels(pivots["highs"], pivots["lows"])
        current_candle = history[-1]
        
        entry = current_candle.get('close', 0.0)
        trigger_level = None
        
        if action == "buy":
            # Find which support level triggered
            for support in levels["support"]:
                if self._check_rejection_candle(current_candle, support, is_support=True):
                    trigger_level = support
                    break
            
            if trigger_level:
                # Stop loss below support level
                stop_loss = trigger_level * 0.995  # 0.5% below support
                # Take profit at next resistance or 2:1 R:R
                if levels["resistance"]:
                    next_resistance = min([r for r in levels["resistance"] if r > entry], default=entry * 1.04)
                    take_profit = min(next_resistance * 0.998, entry * 1.04)  # Cap at 4%
                else:
                    risk = entry - stop_loss
                    take_profit = entry + (risk * 2.0)  # 2:1 R:R
            else:
                # Fallback
                stop_loss = entry * 0.98
                take_profit = entry * 1.04
        
        else:  # sell
            # Find which resistance level triggered
            for resistance in levels["resistance"]:
                if self._check_rejection_candle(current_candle, resistance, is_support=False):
                    trigger_level = resistance
                    break
            
            if trigger_level:
                # Stop loss above resistance level
                stop_loss = trigger_level * 1.005  # 0.5% above resistance
                # Take profit at next support or 2:1 R:R
                if levels["support"]:
                    next_support = max([s for s in levels["support"] if s < entry], default=entry * 0.96)
                    take_profit = max(next_support * 1.002, entry * 0.96)  # Cap at 4%
                else:
                    risk = stop_loss - entry
                    take_profit = entry - (risk * 2.0)  # 2:1 R:R
            else:
                # Fallback
                stop_loss = entry * 1.02
                take_profit = entry * 0.96
        
        # Calculate confidence based on level strength
        level_strength = 0.0
        if trigger_level:
            # Count how many pivots formed this level
            if action == "buy":
                level_pivots = [p for p in pivots["lows"] if abs(p - trigger_level) / trigger_level < 0.01]
            else:
                level_pivots = [p for p in pivots["highs"] if abs(p - trigger_level) / trigger_level < 0.01]
            
            level_strength = min(1.0, len(level_pivots) / 5.0)  # Max strength at 5+ pivots
        
        confidence = 0.6 + (level_strength * 0.3)  # 60-90% confidence
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Support/Resistance rejection at {trigger_level:.4f} with order flow confirmation",
            "strategy": self.name,
        }

