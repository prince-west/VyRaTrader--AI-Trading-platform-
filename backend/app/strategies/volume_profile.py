# backend/app/strategies/volume_profile.py
"""
Volume Profile Strategy - Price Volume Nodes (PVN)
Based on institutional trading: Where most trading happened = natural support/resistance.

Key principles:
1. Calculate volume at each price level
2. Identify Price Volume Nodes (PVN) - high volume areas
3. These become natural support/resistance
4. Trade bounces/rejections from PVN levels

Volume Profile:
- High volume nodes = strong support/resistance
- Low volume nodes = weak areas (price moves through quickly)
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from statistics import mean
from backend.app.strategies.base import StrategyBase


class VolumeProfileStrategy(StrategyBase):
    """
    Volume Profile strategy - trades bounces from Price Volume Nodes.
    """
    name = "volume_profile"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50
        self.profile_period = 50  # Calculate profile over last 50 candles
        self.node_threshold = 1.5  # Volume must be 1.5x average to be a node
        self.bounce_threshold = 0.005  # 0.5% from node to count as bounce
    
    def _calculate_volume_profile(self, history: List[Dict[str, Any]]) -> Dict[float, float]:
        """
        Calculate volume profile - volume at each price level.
        Returns: {price_level: total_volume}
        """
        if len(history) < self.profile_period:
            return {}
        
        # Use recent candles
        recent_history = history[-self.profile_period:]
        
        # Create price buckets (divide price range into 20 levels)
        prices = [c.get('close', 0.0) for c in recent_history if c.get('close', 0.0) > 0]
        if not prices:
            return {}
        
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            return {}
        
        # Create 20 price buckets
        num_buckets = 20
        bucket_size = price_range / num_buckets
        
        volume_profile = defaultdict(float)
        
        for candle in recent_history:
            high = candle.get('high', 0.0)
            low = candle.get('low', 0.0)
            volume = candle.get('volume', 0.0)
            
            if high == 0 or low == 0:
                continue
            
            # Distribute volume across price buckets this candle touched
            candle_range = high - low
            if candle_range == 0:
                # Single price - all volume to that bucket
                bucket = int((high - min_price) / bucket_size)
                bucket = max(0, min(num_buckets - 1, bucket))
                price_level = min_price + (bucket * bucket_size)
                volume_profile[price_level] += volume
            else:
                # Distribute volume proportionally across touched buckets
                touched_buckets = set()
                for price in [low, high, candle.get('open', 0.0), candle.get('close', 0.0)]:
                    if min_price <= price <= max_price:
                        bucket = int((price - min_price) / bucket_size)
                        bucket = max(0, min(num_buckets - 1, bucket))
                        touched_buckets.add(bucket)
                
                # Distribute volume equally among touched buckets
                if touched_buckets:
                    volume_per_bucket = volume / len(touched_buckets)
                    for bucket in touched_buckets:
                        price_level = min_price + (bucket * bucket_size)
                        volume_profile[price_level] += volume_per_bucket
        
        return dict(volume_profile)
    
    def _find_volume_nodes(self, volume_profile: Dict[float, float]) -> List[Dict[str, Any]]:
        """
        Find Price Volume Nodes (PVN) - high volume areas.
        Returns list of nodes with price and volume.
        """
        if not volume_profile:
            return []
        
        volumes = list(volume_profile.values())
        if not volumes:
            return []
        
        avg_volume = mean(volumes)
        threshold = avg_volume * self.node_threshold
        
        nodes = []
        for price, volume in volume_profile.items():
            if volume >= threshold:
                nodes.append({
                    "price": price,
                    "volume": volume,
                })
        
        # Sort by volume (highest first)
        nodes.sort(key=lambda x: x["volume"], reverse=True)
        
        return nodes[:5]  # Return top 5 nodes
    
    def _check_pvn_bounce(self, history: List[Dict[str, Any]], nodes: List[Dict[str, Any]]) -> Optional[str]:
        """
        Check if price bounced/rejected from a PVN.
        Returns: "buy" if bullish bounce, "sell" if bearish rejection, None otherwise.
        """
        if len(history) < 2 or not nodes:
            return None
        
        current_candle = history[-1]
        prev_candle = history[-2]
        
        current_close = current_candle.get('close', 0.0)
        current_low = current_candle.get('low', 0.0)
        current_high = current_candle.get('high', 0.0)
        prev_close = prev_candle.get('close', 0.0)
        
        # Check each node
        for node in nodes[:3]:  # Check top 3 nodes
            node_price = node["price"]
            
            # Check if price is near node
            distance = abs(current_close - node_price) / node_price if node_price > 0 else 1.0
            if distance > self.bounce_threshold:
                continue
            
            # Bullish bounce: price was below node, now above, with rejection wick
            was_below = prev_close < node_price
            now_above = current_close > node_price
            touched_node = current_low <= node_price * 1.01
            
            if was_below and now_above and touched_node:
                candle_range = current_high - current_low
                lower_wick = min(current_candle.get('open', current_close), current_close) - current_low
                if candle_range > 0 and lower_wick / candle_range >= 0.4:
                    return "buy"
            
            # Bearish rejection: price was above node, now below, with rejection wick
            was_above = prev_close > node_price
            now_below = current_close < node_price
            touched_node = current_high >= node_price * 0.99
            
            if was_above and now_below and touched_node:
                candle_range = current_high - current_low
                upper_wick = current_high - max(current_candle.get('open', current_close), current_close)
                if candle_range > 0 and upper_wick / candle_range >= 0.4:
                    return "sell"
        
        return None
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price is near a Volume Profile Node."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        volume_profile = self._calculate_volume_profile(history)
        nodes = self._find_volume_nodes(volume_profile)
        
        if not nodes:
            return False
        
        current_price = history[-1].get('close', 0.0)
        
        # Check if price is near any node
        for node in nodes[:3]:
            distance = abs(current_price - node["price"]) / node["price"] if node["price"] > 0 else 1.0
            if distance < self.bounce_threshold:
                return True
        
        return False
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that price bounced/rejected from PVN.
        This is the key - PVN bounces are high-probability signals.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        volume_profile = self._calculate_volume_profile(history)
        nodes = self._find_volume_nodes(volume_profile)
        
        if not nodes:
            return False
        
        bounce = self._check_pvn_bounce(history, nodes)
        return bounce is not None
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from PVN bounce/rejection."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        volume_profile = self._calculate_volume_profile(history)
        nodes = self._find_volume_nodes(volume_profile)
        
        if not nodes:
            return None
        
        return self._check_pvn_bounce(history, nodes)
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with PVN-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        volume_profile = self._calculate_volume_profile(history)
        nodes = self._find_volume_nodes(volume_profile)
        entry = history[-1].get('close', 0.0)
        
        trigger_node = None
        for node in nodes[:3]:
            distance = abs(entry - node["price"]) / node["price"] if node["price"] > 0 else 1.0
            if distance < self.bounce_threshold:
                trigger_node = node
                break
        
        if action == "buy":
            if trigger_node:
                stop_loss = trigger_node["price"] * 0.995
            else:
                stop_loss = entry * 0.98
            
            risk = entry - stop_loss
            take_profit = entry + (risk * 2.0)
            
            if take_profit > entry * 1.04:
                take_profit = entry * 1.04
        else:  # sell
            if trigger_node:
                stop_loss = trigger_node["price"] * 1.005
            else:
                stop_loss = entry * 1.02
            
            risk = stop_loss - entry
            take_profit = entry - (risk * 2.0)
            
            if take_profit < entry * 0.96:
                take_profit = entry * 0.96
        
        # High confidence - PVN bounces are very reliable
        node_strength = trigger_node["volume"] / mean([n["volume"] for n in nodes]) if trigger_node and nodes else 1.0
        confidence = 0.70 + (min(0.20, (node_strength - 1.0) * 0.1))  # 70-90%
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Volume Profile Node bounce/rejection at {trigger_node.get('price', entry):.4f} (volume: {trigger_node.get('volume', 0):.0f})",
            "strategy": self.name,
        }

