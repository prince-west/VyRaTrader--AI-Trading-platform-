# backend/app/strategies/base.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class StrategyBase:
    """
    Base class for trading strategies following pattern completion model.
    
    Strategies should:
    1. Track price history (200+ candles)
    2. Detect when patterns COMPLETE (not just exist)
    3. Only signal when pattern just completed
    4. Prevent duplicate signals (6 hour cooldown)
    """

    name: str = "base"
    
    def __init__(self):
        """Initialize strategy with price history tracking."""
        # Store price history (candles with OHLCV data)
        self.price_history: Dict[str, deque] = {}  # symbol -> deque of candles
        self.last_signal_time: Dict[tuple, datetime] = {}  # (strategy, symbol, action) -> timestamp
        self.min_signal_gap = 6 * 3600  # 6 hours between same signals (in seconds)
        self.min_history_required = 50  # Minimum candles needed before signaling
    
    def update_data(self, symbol: str, new_candle: Dict[str, Any]) -> None:
        """
        Called every time new market data arrives.
        
        Args:
            symbol: Asset symbol
            new_candle: Dict with keys: timestamp, open, high, low, close, volume
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=200)
        
        # Ensure candle has required fields
        candle = {
            'timestamp': new_candle.get('timestamp', datetime.utcnow()),
            'open': new_candle.get('open', new_candle.get('close', 0.0)),
            'high': new_candle.get('high', new_candle.get('close', 0.0)),
            'low': new_candle.get('low', new_candle.get('close', 0.0)),
            'close': new_candle.get('close', 0.0),
            'volume': new_candle.get('volume', 0.0),
        }
        
        self.price_history[symbol].append(candle)
    
    def _is_duplicate(self, symbol: str, action: str) -> bool:
        """
        Check if we've sent this signal recently.
        
        Args:
            symbol: Asset symbol
            action: buy/sell action
            
        Returns:
            True if duplicate (should skip), False if new
        """
        signal_key = (self.name, symbol, action)
        
        if signal_key not in self.last_signal_time:
            return False
        
        last_time = self.last_signal_time[signal_key]
        time_since = (datetime.utcnow() - last_time).total_seconds()
        
        if time_since < self.min_signal_gap:
            return True
        
        return False
    
    def _mark_signal_sent(self, symbol: str, action: str) -> None:
        """Mark that a signal was sent for this symbol/action."""
        signal_key = (self.name, symbol, action)
        self.last_signal_time[signal_key] = datetime.utcnow()
    
    def check_for_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Check if a tradeable pattern just completed.
        This is the main method that should be called continuously.
        
        Returns:
            Signal dict with entry, stop_loss, take_profit, reasoning, etc.
            OR None if no signal
        """
        # Check if we have enough history
        if symbol not in self.price_history:
            return None
        
        history = self.price_history[symbol]
        
        # CRITICAL: Enforce STRICT minimum history requirement
        # Add 10 candle buffer to ensure pattern has time to develop
        required_history = self.min_history_required + 10
        
        if len(history) < required_history:
            # Log occasionally for diagnosis (don't spam)
            import random
            if random.random() < 0.01:  # 1% of checks
                logger.debug(f"{self.name} on {symbol}: Only {len(history)}/{required_history} candles - waiting for more data")
            return None
        
        # QuantConnect LEAN pattern: ONLY signal when pattern JUST COMPLETED (event detection)
        # We don't check pattern_exists - we only care about completion events
        pattern_just_completed = self._confirm_completion(symbol)
        
        # Enhanced diagnostic logging (log periodically to diagnose why no signals)
        import random
        if random.random() < 0.10:  # Log 10% of checks for diagnosis (increased from 5%)
            logger.debug(f"🔍 {self.name} on {symbol}: pattern_just_completed={pattern_just_completed}, history={len(history)}")
            if not pattern_just_completed:
                # Try to get more diagnostic info from strategy
                try:
                    if hasattr(self, '_get_diagnostic_info'):
                        diag_info = self._get_diagnostic_info(symbol)
                        if diag_info:
                            logger.debug(f"   ℹ️ {self.name} diagnostic: {diag_info}")
                except:
                    pass
                logger.debug(f"   ℹ️ No pattern completion event - waiting for crossover/bounce/breakout")
        
        # Generate signal ONLY if pattern just completed (QuantConnect LEAN pattern)
        # This ensures we only signal when an EVENT happens (crossover, bounce, breakout)
        # NOT when a condition is just true
        if pattern_just_completed:
            # Check for duplicates
            action = self._get_action_from_pattern(symbol)
            if not action:
                # If action can't be determined, try to infer from pattern completion
                if pattern_just_completed:
                    logger.debug(f"{self.name} on {symbol}: Pattern completed but _get_action_from_pattern returned None - cannot determine action")
                    # Try to get action from completion logic
                    # For now, return None if we can't determine action
                    return None
                else:
                    logger.debug(f"{self.name} on {symbol}: Pattern exists but _get_action_from_pattern returned None")
                    return None
            
            if action and self._is_duplicate(symbol, action):
                logger.debug(f"{self.name} on {symbol}: Duplicate signal detected for {action}")
                return None  # Already sent recently
            
            # Build signal
            signal = self._build_signal(symbol, action)
            if not signal:
                logger.debug(f"{self.name} on {symbol}: Pattern {'completed' if pattern_just_completed else 'detected'} with action {action}, but _build_signal returned None (likely R:R validation failed)")
                return None
            
            if signal:
                logger.info(f"✅ {self.name} on {symbol}: Pattern completion event detected! Generating {action} signal")
                self._mark_signal_sent(symbol, action)
                return signal
        
        return None  # No tradeable setup right now
    
    def _detect_pattern(self, symbol: str) -> bool:
        """
        Detect if a tradeable pattern exists in the price history.
        Subclasses must implement this.
        
        Returns:
            True if pattern exists, False otherwise
        """
        raise NotImplementedError("Subclasses must implement _detect_pattern")
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that the pattern just completed (not just exists).
        This is what distinguishes professional analysis from guessing.
        Subclasses must implement this.
        
        Returns:
            True if pattern just completed, False otherwise
        """
        raise NotImplementedError("Subclasses must implement _confirm_completion")
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """
        Get the action (buy/sell) from the detected pattern.
        Subclasses must implement this.
        
        Returns:
            "buy", "sell", or None
        """
        raise NotImplementedError("Subclasses must implement _get_action_from_pattern")
    
    def _build_signal(self, symbol: str, action: str) -> Optional[Dict[str, Any]]:
        """
        Build a complete signal dict with entry, stop loss, take profit, reasoning.
        Subclasses must implement this.
        
        Returns:
            Signal dict or None if signal is invalid
        """
        raise NotImplementedError("Subclasses must implement _build_signal")
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """
        Legacy run method for backward compatibility.
        Converts price list to candles and checks for signals.
        
        Note: This is less ideal than continuous monitoring with update_data(),
        but kept for compatibility with existing code.
        """
        # Convert prices to candles (assume each price is a close price)
        candles = []
        for i, price in enumerate(prices):
            candle = {
                'timestamp': datetime.utcnow() - timedelta(minutes=len(prices) - i),
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': 0.0,
            }
            candles.append(candle)
        
        # Update with all candles
        for candle in candles:
            self.update_data(symbol, candle)
        
        # Check for signal
        signal = self.check_for_signal(symbol)
        
        if signal:
            return {
                "signal": signal.get("action", "hold"),
                "score": signal.get("confidence", 0.0) * 5.0,  # Convert 0-1 to 0-5
                "confidence": signal.get("confidence", 0.0),
                "reason": signal.get("reasoning", "pattern_completed"),
            }
        
        return {"signal": "hold", "score": 0.0, "confidence": 0.0, "reason": "no_pattern"}
