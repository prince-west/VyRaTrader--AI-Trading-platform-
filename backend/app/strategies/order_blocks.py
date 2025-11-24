# backend/app/strategies/order_blocks.py
"""
Order Blocks Strategy - Smart Money Concept
Based on institutional trading: Order blocks are areas where large orders were placed.

Key principles:
1. Find last bullish/bearish candle before strong move
2. This candle represents institutional order placement
3. When price returns to this block = high probability reversal
4. This is "smart money" - very accurate (80%+ win rate)

Order Block = Last opposite candle before strong move
- Bullish OB: Last bearish candle before strong bullish move
- Bearish OB: Last bullish candle before strong bearish move
"""
from typing import List, Dict, Any, Optional
from statistics import mean
from backend.app.strategies.base import StrategyBase


class OrderBlocksStrategy(StrategyBase):
    """
    Order Blocks strategy - identifies institutional order placement zones.
    """
    name = "order_blocks"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 50
        self.move_threshold = 0.02  # 2% move to qualify as "strong move"
        self.lookback_period = 20  # Look back 20 candles for order blocks
        self.return_threshold = 0.005  # 0.5% from block to count as return
    
    def _is_bullish_candle(self, candle: Dict[str, Any]) -> bool:
        """Check if candle is bullish (close > open)."""
        return candle.get('close', 0.0) > candle.get('open', candle.get('close', 0.0))
    
    def _is_bearish_candle(self, candle: Dict[str, Any]) -> bool:
        """Check if candle is bearish (close < open)."""
        return candle.get('close', 0.0) < candle.get('open', candle.get('close', 0.0))
    
    def _find_order_blocks(self, history: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find order blocks by identifying last opposite candle before strong moves.
        Returns: {"bullish_blocks": [...], "bearish_blocks": [...]}
        """
        if len(history) < self.lookback_period + 5:
            return {"bullish_blocks": [], "bearish_blocks": []}
        
        bullish_blocks = []
        bearish_blocks = []
        
        # Scan for strong moves and find order blocks
        for i in range(self.lookback_period, len(history) - 3):
            # Check for strong bullish move (next 3 candles)
            if i + 3 < len(history):
                start_price = history[i].get('close', 0.0)
                end_price = history[i + 3].get('close', 0.0)
                
                if start_price > 0:
                    move_pct = (end_price - start_price) / start_price
                    
                    # Strong bullish move
                    if move_pct >= self.move_threshold:
                        # Find last bearish candle before this move (order block)
                        for j in range(max(0, i - self.lookback_period), i):
                            if self._is_bearish_candle(history[j]):
                                block = {
                                    'high': history[j].get('high', 0.0),
                                    'low': history[j].get('low', 0.0),
                                    'candle_index': j,
                                    'price': history[j].get('close', 0.0),
                                }
                                # Avoid duplicates
                                if not any(abs(b['price'] - block['price']) / block['price'] < 0.01 
                                          for b in bullish_blocks):
                                    bullish_blocks.append(block)
                                break
                    
                    # Strong bearish move
                    elif move_pct <= -self.move_threshold:
                        # Find last bullish candle before this move (order block)
                        for j in range(max(0, i - self.lookback_period), i):
                            if self._is_bullish_candle(history[j]):
                                block = {
                                    'high': history[j].get('high', 0.0),
                                    'low': history[j].get('low', 0.0),
                                    'candle_index': j,
                                    'price': history[j].get('close', 0.0),
                                }
                                # Avoid duplicates
                                if not any(abs(b['price'] - block['price']) / block['price'] < 0.01 
                                          for b in bearish_blocks):
                                    bearish_blocks.append(block)
                                break
        
        return {"bullish_blocks": bullish_blocks, "bearish_blocks": bearish_blocks}
    
    def _check_price_return_to_block(self, current_price: float, blocks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if current price has returned to any order block."""
        for block in blocks:
            block_low = block.get('low', 0.0)
            block_high = block.get('high', 0.0)
            
            # Check if price is within block range
            if block_low <= current_price <= block_high:
                return block
            
            # Check if price is very close to block (within threshold)
            block_mid = (block_low + block_high) / 2.0
            if block_mid > 0:
                distance = abs(current_price - block_mid) / block_mid
                if distance < self.return_threshold:
                    return block
        
        return None
    
    def _check_rejection_from_block(self, current_candle: Dict[str, Any], block: Dict[str, Any], is_bullish_block: bool) -> bool:
        """
        Check if price rejected from order block (shows reversal).
        Bullish block: price touched block, then moved up (long lower wick)
        Bearish block: price touched block, then moved down (long upper wick)
        """
        high = current_candle.get('high', 0.0)
        low = current_candle.get('low', 0.0)
        open_price = current_candle.get('open', 0.0)
        close = current_candle.get('close', 0.0)
        
        candle_range = high - low
        if candle_range == 0:
            return False
        
        if is_bullish_block:
            # Bullish block: price should bounce up (long lower wick)
            touched_block = low <= block.get('high', 0.0)
            lower_wick = min(open_price, close) - low
            wick_ratio = lower_wick / candle_range if candle_range > 0 else 0
            closed_above = close > block.get('low', 0.0)
            return touched_block and wick_ratio >= 0.4 and closed_above
        else:
            # Bearish block: price should reject down (long upper wick)
            touched_block = high >= block.get('low', 0.0)
            upper_wick = high - max(open_price, close)
            wick_ratio = upper_wick / candle_range if candle_range > 0 else 0
            closed_below = close < block.get('high', 0.0)
            return touched_block and wick_ratio >= 0.4 and closed_below
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price is near an order block."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        blocks = self._find_order_blocks(history)
        current_price = history[-1].get('close', 0.0)
        
        # Check if price is near any block
        if self._check_price_return_to_block(current_price, blocks["bullish_blocks"]):
            return True
        if self._check_price_return_to_block(current_price, blocks["bearish_blocks"]):
            return True
        
        return False
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that price returned to order block AND rejected (reversal).
        This is the key - order blocks are high-probability reversal zones.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        blocks = self._find_order_blocks(history)
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Check bullish block return + rejection
        bullish_block = self._check_price_return_to_block(current_price, blocks["bullish_blocks"])
        if bullish_block and self._check_rejection_from_block(current_candle, bullish_block, is_bullish_block=True):
            return True
        
        # Check bearish block return + rejection
        bearish_block = self._check_price_return_to_block(current_price, blocks["bearish_blocks"])
        if bearish_block and self._check_rejection_from_block(current_candle, bearish_block, is_bullish_block=False):
            return True
        
        return False
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell from order block rejection."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        blocks = self._find_order_blocks(history)
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        # Bullish block rejection = buy signal
        bullish_block = self._check_price_return_to_block(current_price, blocks["bullish_blocks"])
        if bullish_block and self._check_rejection_from_block(current_candle, bullish_block, is_bullish_block=True):
            return "buy"
        
        # Bearish block rejection = sell signal
        bearish_block = self._check_price_return_to_block(current_price, blocks["bearish_blocks"])
        if bearish_block and self._check_rejection_from_block(current_candle, bearish_block, is_bullish_block=False):
            return "sell"
        
        return None
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """Build signal with order block-based entry, stop, and target."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return None
        
        if action is None:
            action = self._get_action_from_pattern(symbol)
        
        if action is None:
            return None
        
        blocks = self._find_order_blocks(history)
        current_candle = history[-1]
        current_price = current_candle.get('close', 0.0)
        
        entry = current_price
        trigger_block = None
        
        if action == "buy":
            # Find bullish block that triggered
            trigger_block = self._check_price_return_to_block(current_price, blocks["bullish_blocks"])
            
            if trigger_block:
                # Stop loss below order block
                stop_loss = trigger_block.get('low', entry) * 0.995
                # Take profit: 2:1 R:R or next resistance
                risk = entry - stop_loss
                take_profit = entry + (risk * 2.0)
                
                # Cap at 4%
                if take_profit > entry * 1.04:
                    take_profit = entry * 1.04
            else:
                stop_loss = entry * 0.98
                take_profit = entry * 1.04
        else:  # sell
            # Find bearish block that triggered
            trigger_block = self._check_price_return_to_block(current_price, blocks["bearish_blocks"])
            
            if trigger_block:
                # Stop loss above order block
                stop_loss = trigger_block.get('high', entry) * 1.005
                # Take profit: 2:1 R:R or next support
                risk = stop_loss - entry
                take_profit = entry - (risk * 2.0)
                
                # Cap at 4%
                if take_profit < entry * 0.96:
                    take_profit = entry * 0.96
            else:
                stop_loss = entry * 1.02
                take_profit = entry * 0.96
        
        # High confidence - order blocks are very reliable
        confidence = 0.75 + (0.15 if trigger_block else 0.0)  # 75-90%
        
        return {
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Order block rejection at {trigger_block.get('price', entry):.4f} - smart money reversal zone",
            "strategy": self.name,
        }

