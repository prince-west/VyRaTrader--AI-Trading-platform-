# backend/app/strategies/arbitrage.py
from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase


class ArbitrageStrategy(StrategyBase):
    """
    Arbitrage strategy that finds profitable price differences between exchanges.
    
    Pattern: Price difference >1% between exchanges + execution feasible (accounts for fees + slippage)
    """
    name = "arbitrage"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 5  # Need minimal history
        self.min_profit_pct = 0.005  # Minimum 0.5% profit after fees (professional standard: 0.5-1%)
        self.fee_pct = 0.001  # Assume 0.1% fee per trade (0.2% total round trip)
        self.slippage_pct = 0.0005  # Assume 0.05% slippage
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if price difference exists between exchanges."""
        # This strategy relies on external exchange data, not just price history
        # Pattern detection happens in _confirm_completion
        return True  # Always check (we'll filter in completion)
    
    def _confirm_completion(self, symbol: str) -> bool:
        """Confirm that profitable arbitrage opportunity exists."""
        # This strategy needs external exchange data
        # We'll check in _build_signal since we need extra data
        return True  # Defer to _build_signal for validation
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell action from arbitrage opportunity."""
        # This will be determined in _build_signal with external data
        return None  # Will be set in _build_signal
    
    def _build_signal(self, symbol: str, action: Optional[str] = None, **extra) -> Optional[Dict[str, Any]]:
        """
        Build signal with entry, stop loss, take profit.
        Requires 'other_exchanges' in extra dict.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if symbol not in self.price_history:
            logger.debug(f"Arbitrage {symbol}: No price history")
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < 1:
            logger.debug(f"Arbitrage {symbol}: Insufficient history ({len(history)} candles)")
            return None
        
        local_price = history[-1]['close']
        
        # Get external exchange prices
        extern = extra.get("other_exchanges") if extra else None
        if not extern:
            logger.debug(f"Arbitrage {symbol}: No external exchange data")
            return None  # No external data
        
        # Compute average external price
        ext_vals = [v for v in extern.values() if isinstance(v, (int, float)) and v > 0]
        if not ext_vals:
            return None
        
        ext_avg = sum(ext_vals) / len(ext_vals)
        if ext_avg <= 0:
            return None
        
        # Calculate price difference
        diff_pct = (local_price - ext_avg) / ext_avg
        
        # Account for fees and slippage
        total_cost_pct = (self.fee_pct * 2) + (self.slippage_pct * 2)  # Round trip
        
        # Net profit after costs
        if diff_pct > 0:
            # Local price higher: sell locally, buy externally
            net_profit = diff_pct - total_cost_pct
            if net_profit < self.min_profit_pct:
                logger.debug(f"Arbitrage {symbol}: Not profitable (diff={diff_pct*100:.2f}%, costs={total_cost_pct*100:.2f}%, net={net_profit*100:.2f}% < min={self.min_profit_pct*100:.2f}%)")
                return None  # Not profitable after costs
            action = "sell"
            entry = local_price
            # Take profit: external price (where we'd buy back)
            take_profit = ext_avg * (1 + self.fee_pct)  # External price + fee
            # Stop loss: if local price RISES too much, arbitrage disappears (for SELL, stop_loss must be ABOVE entry)
            stop_loss = local_price * (1 + net_profit * 0.5)  # Half the profit as buffer above entry
        elif diff_pct < 0:
            # Local price lower: buy locally, sell externally
            net_profit = abs(diff_pct) - total_cost_pct
            if net_profit < self.min_profit_pct:
                logger.debug(f"Arbitrage {symbol}: Not profitable (diff={abs(diff_pct)*100:.2f}%, costs={total_cost_pct*100:.2f}%, net={net_profit*100:.2f}% < min={self.min_profit_pct*100:.2f}%)")
                return None  # Not profitable after costs
            action = "buy"
            entry = local_price
            # Take profit: external price (where we'd sell)
            take_profit = ext_avg * (1 - self.fee_pct)  # External price - fee
            # Stop loss: if local price DROPS too much, arbitrage disappears (for BUY, stop_loss must be BELOW entry)
            stop_loss = local_price * (1 - net_profit * 0.5)  # Half the profit as buffer below entry
        else:
            return None  # No difference
        
        # CRITICAL FIX: Cap take profit at 6% (realistic maximum for single trade)
        if action == "buy":
            max_take_profit = entry * 1.06  # +6% max
            if take_profit > max_take_profit:
                take_profit = max_take_profit
        else:  # sell
            max_take_profit = entry * 0.94  # -6% max
            if take_profit < max_take_profit:
                take_profit = max_take_profit
        
        # Validate risk/reward ratio (minimum 1.5:1, maximum 4:1)
        if action == "buy":
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
        else:  # sell
            risk = abs(stop_loss - entry)
            reward = abs(entry - take_profit)
        
        if risk <= 0:
            return None  # Invalid risk (zero or negative)
        
        risk_reward_ratio = reward / risk
        
        # CRITICAL FIX: Reject unrealistic risk/reward ratios
        if risk_reward_ratio < 1.5:
            logger.debug(f"Arbitrage {symbol}: Risk/reward too low (R:R={risk_reward_ratio:.2f} < 1.5, risk={risk:.4f}, reward={reward:.4f})")
            return None  # Invalid risk/reward (less than 1:1.5)
        if risk_reward_ratio > 4.0:
            # Cap R:R at 4:1 by adjusting take profit
            if action == "buy":
                take_profit = entry + (risk * 4.0)
            else:
                take_profit = entry - (risk * 4.0)
            risk_reward_ratio = 4.0
        
        # Calculate confidence based on profit margin
        profit_margin = net_profit / self.min_profit_pct  # How much above minimum
        confidence = min(0.9, 0.6 + (profit_margin - 1.0) * 0.3)  # 0.6-0.9 range
        
        return {
            "strategy": self.name,
            "symbol": symbol,
            "action": action,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasoning": f"Arbitrage opportunity: {action.upper()} locally at {entry:.4f}, external avg: {ext_avg:.4f}. Net profit: {net_profit*100:.2f}% after fees.",
            "requires_volume": False,
            "external_price": ext_avg,
            "net_profit_pct": net_profit,
        }
    
    def check_for_signal(self, symbol: str, **extra) -> Optional[Dict[str, Any]]:
        """
        Override to pass extra data (external exchange prices) to _build_signal.
        """
        if symbol not in self.price_history:
            return None
        
        history = self.price_history[symbol]
        if len(history) < self.min_history_required:
            return None
        
        # Check for duplicates first
        # We'll determine action in _build_signal, so check both
        if self._is_duplicate(symbol, "buy") and self._is_duplicate(symbol, "sell"):
            return None
        
        # Build signal with external data
        signal = self._build_signal(symbol, action=None, **extra)
        
        if signal:
            action = signal.get("action")
            if action:
                if self._is_duplicate(symbol, action):
                    return None  # Already sent recently
                self._mark_signal_sent(symbol, action)
                return signal
        
        return None
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """Legacy run method for backward compatibility."""
        # Convert prices to candles
        from datetime import datetime, timedelta
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
        
        for candle in candles:
            self.update_data(symbol, candle)
        
        # Check for signal with external data
        signal = self.check_for_signal(symbol, **extra)
        
        if signal:
            return {
                "signal": signal.get("action", "hold"),
                "score": signal.get("confidence", 0.0) * 5.0,
                "confidence": signal.get("confidence", 0.0),
                "reason": signal.get("reasoning", "arbitrage_opportunity"),
            }
        
        return {"signal": "hold", "score": 0.0, "confidence": 0.0, "reason": "no_arbitrage"}
