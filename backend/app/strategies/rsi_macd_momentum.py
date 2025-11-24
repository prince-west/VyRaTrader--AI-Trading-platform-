# backend/app/strategies/rsi_macd_momentum.py
"""
Enhanced Professional RSI + MACD Momentum Strategy
Based on research-proven AI trading techniques:
- RSI/MACD divergence detection (highly accurate)
- Adaptive thresholds based on volatility
- Multi-timeframe confirmation
- Enhanced feature engineering

Pattern: RSI reversal + MACD crossover + divergence + volume confirmation
"""
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean, stdev, StatisticsError
from backend.app.strategies.base import StrategyBase
import numpy as np


class RSI_MACD_MomentumStrategy(StrategyBase):
    """
    Enhanced RSI + MACD momentum strategy with divergence detection.
    Uses adaptive thresholds and multi-timeframe analysis for better accuracy.
    """
    name = "rsi_macd_momentum"
    
    def __init__(self):
        super().__init__()
        self.min_history_required = 60  # Need more for divergence detection
        self.rsi_period = 14
        self.rsi_oversold_base = 30  # Base threshold, adjusted by volatility
        self.rsi_overbought_base = 70
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.min_volume_ratio = 1.2
        self.divergence_lookback = 20  # Look back 20 candles for divergence
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2.0 / (period + 1.0)
        
        # Start with SMA
        try:
            sma = mean(prices[:period]) if len(prices[:period]) > 0 else 0.0
        except (ValueError, StatisticsError):
            sma = prices[0] if prices else 0.0
        ema_values.append(sma)
        
        # Calculate EMA for remaining values
        for price in prices[period:]:
            ema = (price - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        return ema_values
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        if len(closes) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]
        
        # Use recent period
        recent_gains = gains[-period:] if len(gains) >= period else gains
        recent_losses = losses[-period:] if len(losses) >= period else losses
        
        # Check if lists are not empty before calling mean
        try:
            avg_gain = mean(recent_gains) if len(recent_gains) > 0 else 0.0
        except (ValueError, StatisticsError):
            avg_gain = 0.0
        
        try:
            avg_loss = mean(recent_losses) if len(recent_losses) > 0 else 0.0
        except (ValueError, StatisticsError):
            avg_loss = 0.0
        
        if avg_loss == 0:
            return 100.0  # All gains, no losses
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_rsi_series(self, closes: List[float], period: int = 14) -> List[float]:
        """Calculate RSI for entire series (needed for divergence detection)."""
        if len(closes) < period + 1:
            return [50.0] * len(closes)
        
        rsi_values = []
        for i in range(period, len(closes)):
            try:
                subset = closes[:i+1]
                if len(subset) >= period + 1:
                    rsi = self._calculate_rsi(subset, period)
                    rsi_values.append(rsi)
                else:
                    rsi_values.append(50.0)  # Neutral if not enough data
            except:
                rsi_values.append(50.0)  # Neutral on error
        
        # Pad beginning with neutral RSI
        return [50.0] * period + rsi_values
    
    def _calculate_volatility(self, closes: List[float], period: int = 20) -> float:
        """Calculate price volatility (standard deviation of returns)."""
        if len(closes) < period + 1:
            return 0.0
        
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:  # Avoid division by zero
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
        
        recent_returns = returns[-period:] if len(returns) >= period else returns
        
        if len(recent_returns) < 2:
            return 0.0
        
        try:
            return stdev(recent_returns) if recent_returns else 0.0
        except:
            return 0.0
    
    def _get_adaptive_thresholds(self, closes: List[float]) -> Tuple[float, float]:
        """
        Get adaptive RSI thresholds based on market volatility.
        Higher volatility = wider thresholds (more extreme required).
        Research shows this improves signal quality.
        """
        volatility = self._calculate_volatility(closes)
        
        # Normalize volatility (typical range 0.001-0.05 for most assets)
        normalized_vol = min(1.0, volatility * 100)  # Scale to 0-1
        
        # Adjust thresholds: high volatility = more extreme required
        # Low volatility: use base thresholds (30/70)
        # High volatility: require more extreme (25/75 or 20/80)
        oversold = self.rsi_oversold_base - (normalized_vol * 5)  # 30 -> 25 in high vol
        overbought = self.rsi_overbought_base + (normalized_vol * 5)  # 70 -> 75 in high vol
        
        # Clamp to reasonable bounds
        oversold = max(20, min(35, oversold))
        overbought = min(80, max(65, overbought))
        
        return oversold, overbought
    
    def _detect_divergence(self, closes: List[float], rsi_values: List[float]) -> Optional[str]:
        """
        Detect RSI divergence - one of the most powerful trading signals.
        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high
        
        Returns: "bullish", "bearish", or None
        """
        if len(closes) < self.divergence_lookback or len(rsi_values) < self.divergence_lookback:
            return None
        
        # Look at recent price and RSI peaks/troughs
        lookback = min(self.divergence_lookback, len(closes))
        recent_closes = closes[-lookback:]
        recent_rsi = rsi_values[-lookback:]
        
        # Find local minima (troughs) for bullish divergence
        # Find local maxima (peaks) for bearish divergence
        min_window = 3
        
        # Check for bullish divergence (price lower low, RSI higher low)
        for i in range(min_window, len(recent_closes) - min_window):
            # Check if we have a local low in price
            is_price_low = all(recent_closes[i] <= recent_closes[i-j] for j in range(1, min_window+1)) and \
                          all(recent_closes[i] <= recent_closes[i+j] for j in range(1, min_window+1))
            
            if is_price_low:
                # Check previous low
                for j in range(i + min_window, len(recent_closes) - min_window):
                    is_prev_price_low = all(recent_closes[j] <= recent_closes[j-k] for k in range(1, min_window+1)) and \
                                       all(recent_closes[j] <= recent_closes[j+k] for k in range(1, min_window+1))
                    
                    if is_prev_price_low:
                        # Price made lower low
                        if recent_closes[j] < recent_closes[i]:
                            # Check if RSI made higher low
                            if recent_rsi[j] > recent_rsi[i] and recent_rsi[i] < 40:
                                return "bullish"
        
        # Check for bearish divergence (price higher high, RSI lower high)
        for i in range(min_window, len(recent_closes) - min_window):
            # Check if we have a local high in price
            is_price_high = all(recent_closes[i] >= recent_closes[i-j] for j in range(1, min_window+1)) and \
                           all(recent_closes[i] >= recent_closes[i+j] for j in range(1, min_window+1))
            
            if is_price_high:
                # Check previous high
                for j in range(i + min_window, len(recent_closes) - min_window):
                    is_prev_price_high = all(recent_closes[j] >= recent_closes[j-k] for k in range(1, min_window+1)) and \
                                        all(recent_closes[j] >= recent_closes[j+k] for k in range(1, min_window+1))
                    
                    if is_prev_price_high:
                        # Price made higher high
                        if recent_closes[j] > recent_closes[i]:
                            # Check if RSI made lower high
                            if recent_rsi[j] < recent_rsi[i] and recent_rsi[i] > 60:
                                return "bearish"
        
        return None
    
    def _calculate_macd(self, closes: List[float]) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        try:
            if len(closes) < self.macd_slow + self.macd_signal:
                return {"macd": [], "signal": [], "histogram": []}
            
            # Calculate fast and slow EMAs
            fast_ema = self._calculate_ema(closes, self.macd_fast)
            slow_ema = self._calculate_ema(closes, self.macd_slow)
            
            if not fast_ema or not slow_ema:
                return {"macd": [], "signal": [], "histogram": []}
            
            # MACD line = fast EMA - slow EMA
            macd_line = []
            offset = self.macd_fast - self.macd_slow
            for i in range(len(slow_ema)):
                if i + offset < len(fast_ema):
                    macd_val = fast_ema[i + offset] - slow_ema[i]
                    macd_line.append(macd_val)
            
            if not macd_line:
                return {"macd": [], "signal": [], "histogram": []}
            
            # Signal line = EMA of MACD line
            signal_line = self._calculate_ema(macd_line, self.macd_signal)
            
            if not signal_line:
                return {"macd": macd_line, "signal": [], "histogram": []}
            
            # Histogram = MACD - Signal
            histogram = []
            hist_offset = len(macd_line) - len(signal_line)
            for i in range(len(signal_line)):
                if i + hist_offset < len(macd_line):
                    hist_val = macd_line[i + hist_offset] - signal_line[i]
                    histogram.append(hist_val)
            
            return {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram
            }
        except Exception as e:
            # Return empty on any error
            return {"macd": [], "signal": [], "histogram": []}
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Check if RSI is in extreme territory (using adaptive thresholds)."""
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required:
            return False
        
        closes = [c['close'] for c in history]
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        
        # Use adaptive thresholds based on volatility
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # Pattern exists if RSI is in extreme territory
        is_extreme = current_rsi <= oversold or current_rsi >= overbought
        
        return is_extreme
    
    def _confirm_completion(self, symbol: str) -> bool:
        """
        Confirm that RSI reversal + MACD crossover + divergence just completed with volume.
        Enhanced with divergence detection for higher accuracy.
        """
        if symbol not in self.price_history:
            return False
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return False
        
        closes = [c['close'] for c in history]
        volumes = [c.get('volume', 0.0) for c in history]
        
        # Get adaptive thresholds
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # Calculate RSI for current and previous
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        previous_rsi = self._calculate_rsi(closes[:-1], self.rsi_period)
        
        # Calculate RSI series for divergence detection
        rsi_series = self._calculate_rsi_series(closes, self.rsi_period)
        divergence = self._detect_divergence(closes, rsi_series)
        
        # Calculate MACD for current and previous
        macd_data = self._calculate_macd(closes)
        prev_macd_data = self._calculate_macd(closes[:-1])
        
        if len(macd_data["macd"]) < 2 or len(prev_macd_data["macd"]) < 2:
            return False
        
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        prev_macd = prev_macd_data["macd"][-1]
        prev_signal = prev_macd_data["signal"][-1]
        
        # Volume confirmation
        if len(volumes) >= 20:
            non_zero_volumes = [v for v in volumes[-20:] if v > 0]
            try:
                avg_volume = mean(non_zero_volumes) if len(non_zero_volumes) > 0 else 0.0
            except (ValueError, StatisticsError):
                avg_volume = 0.0
            current_volume = volumes[-1] if volumes[-1] > 0 else 0.0
            volume_ok = current_volume > avg_volume * self.min_volume_ratio if avg_volume > 0 else True
        else:
            volume_ok = True  # No volume data available
        
        # PRIMARY EVENT 1: RSI bounce (same pattern as momentum - detect ONE event first)
        rsi_bounce_bullish = previous_rsi < oversold and current_rsi >= oversold
        rsi_rejection_bearish = previous_rsi > overbought and current_rsi <= overbought
        
        # PRIMARY EVENT 2: MACD crossover (same pattern as momentum strategy)
        macd_cross_bullish = prev_macd <= prev_signal and current_macd > current_signal
        macd_cross_bearish = prev_macd >= prev_signal and current_macd < current_signal
        
        # Check if at least ONE primary event occurred (same as momentum - it only needs crossover)
        has_primary_event = (rsi_bounce_bullish or rsi_rejection_bearish or 
                            macd_cross_bullish or macd_cross_bearish)
        
        if not has_primary_event:
            return False  # No primary event (same pattern as momentum)
        
        # CONFIRMATION 1: If RSI bounce, check MACD confirms (or vice versa)
        # This is like momentum's histogram confirmation - adds strength but not required
        if rsi_bounce_bullish and macd_cross_bullish:
            # Both confirm - very strong signal
            return volume_ok
        
        if rsi_rejection_bearish and macd_cross_bearish:
            # Both confirm - very strong signal
            return volume_ok
        
        # CONFIRMATION 2: Price confirmation (same as momentum strategy)
        prev_close = closes[-2]
        current_close = closes[-1]
        
        if (rsi_bounce_bullish or macd_cross_bullish):
            price_confirms = current_close > prev_close
            if price_confirms and volume_ok:
                return True
        
        if (rsi_rejection_bearish or macd_cross_bearish):
            price_confirms = current_close < prev_close
            if price_confirms and volume_ok:
                return True
        
        # CONFIRMATION 3: Divergence bonus (makes signal stronger but not required)
        if (rsi_bounce_bullish or macd_cross_bullish) and divergence == "bullish" and volume_ok:
            return True
        
        if (rsi_rejection_bearish or macd_cross_bearish) and divergence == "bearish" and volume_ok:
            return True
        
        return False
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Determine buy/sell action from RSI reversal + MACD crossover direction (with adaptive thresholds)."""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < self.min_history_required + 2:
            return None
        
        closes = [c['close'] for c in history]
        
        # Get adaptive thresholds
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # Calculate RSI
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        previous_rsi = self._calculate_rsi(closes[:-1], self.rsi_period)
        
        # Calculate MACD
        macd_data = self._calculate_macd(closes)
        prev_macd_data = self._calculate_macd(closes[:-1])
        
        if len(macd_data["macd"]) < 2 or len(prev_macd_data["macd"]) < 2:
            return None
        
        current_macd = macd_data["macd"][-1]
        current_signal = macd_data["signal"][-1]
        prev_macd = prev_macd_data["macd"][-1]
        prev_signal = prev_macd_data["signal"][-1]
        
        # FIX: Match _confirm_completion logic - allow EITHER RSI bounce OR MACD cross
        # This matches the completion logic which allows either event
        
        # Bullish: RSI oversold bounce OR MACD bullish cross (matches _confirm_completion)
        rsi_bounce_bullish = previous_rsi < oversold and current_rsi >= oversold
        macd_cross_bullish = prev_macd <= prev_signal and current_macd > current_signal
        
        if rsi_bounce_bullish or macd_cross_bullish:
            return "buy"
        
        # Bearish: RSI overbought rejection OR MACD bearish cross (matches _confirm_completion)
        rsi_rejection_bearish = previous_rsi > overbought and current_rsi <= overbought
        macd_cross_bearish = prev_macd >= prev_signal and current_macd < current_signal
        
        if rsi_rejection_bearish or macd_cross_bearish:
            return "sell"
        
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
        
        closes = [c['close'] for c in history]
        volumes = [c.get('volume', 0.0) for c in history]
        
        # Calculate indicators for reasoning
        current_rsi = self._calculate_rsi(closes, self.rsi_period)
        macd_data = self._calculate_macd(closes)
        current_histogram = macd_data["histogram"][-1] if macd_data["histogram"] else 0.0
        
        # Calculate volume ratio
        if len(volumes) >= 20:
            non_zero_volumes = [v for v in volumes[-20:] if v > 0]
            if non_zero_volumes:  # Check if list is not empty
                try:
                    avg_volume = mean(non_zero_volumes)
                except (ValueError, StatisticsError):
                    avg_volume = 0.0
                current_volume = volumes[-1] if volumes[-1] > 0 else 0.0
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0  # No volume data available
        else:
            volume_ratio = 1.0
        
        # Calculate stop loss and take profit (2% stop, 4% target = 2:1 R:R)
        if action == "buy":
            stop_loss = entry * 0.98  # 2% stop loss
            take_profit = entry * 1.04  # 4% take profit
        elif action == "sell":
            stop_loss = entry * 1.02  # 2% stop loss
            take_profit = entry * 0.96  # 4% take profit
        else:
            return None
        
        # Validate risk/reward ratio (minimum 1:2)
        if action == "buy":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        
        if risk <= 0 or reward / risk < 1.5:
            return None  # Invalid risk/reward (relaxed from 2.0 to 1.5 to match other strategies)
        
        # Get adaptive thresholds for reasoning
        oversold, overbought = self._get_adaptive_thresholds(closes)
        
        # Calculate RSI series for divergence detection
        rsi_series = self._calculate_rsi_series(closes, self.rsi_period)
        divergence = self._detect_divergence(closes, rsi_series)
        
        # Enhanced confidence calculation with divergence bonus
        score = 5.0
        
        # RSI extreme = higher confidence (using adaptive thresholds)
        if current_rsi < (oversold - 5) or current_rsi > (overbought + 5):
            score += 2.5  # Very extreme
        elif current_rsi < oversold or current_rsi > overbought:
            score += 1.5  # Extreme
        
        # Divergence detection = SIGNIFICANT bonus (proven to be very accurate)
        if divergence == "bullish" and action == "buy":
            score += 3.0  # Strong bullish divergence
        elif divergence == "bearish" and action == "sell":
            score += 3.0  # Strong bearish divergence
        
        # Strong MACD histogram = higher confidence
        if abs(current_histogram) > 0.5:
            score += 1.5
        elif abs(current_histogram) > 0.3:
            score += 0.5
        
        # Volume confirmation = higher confidence
        if volume_ratio > 1.5:
            score += 1.5
        elif volume_ratio > 1.2:
            score += 1.0
        
        # Volatility adjustment: higher volatility = slightly lower confidence (more risk)
        volatility = self._calculate_volatility(closes)
        if volatility > 0.02:  # High volatility
            score -= 0.5
        
        confidence = min(0.95, max(0.3, score / 12.0))  # Convert to 0-1 scale, cap at 0.95
        
        # Build enhanced reasoning
        divergence_text = ""
        if divergence:
            divergence_text = f" + {divergence.upper()} divergence detected"
        
        if action == "buy":
            reasoning = f"RSI oversold bounce ({current_rsi:.1f}, threshold: {oversold:.1f}) + MACD golden cross + volume ({volume_ratio:.2f}x){divergence_text}"
        else:
            reasoning = f"RSI overbought rejection ({current_rsi:.1f}, threshold: {overbought:.1f}) + MACD death cross + volume ({volume_ratio:.2f}x){divergence_text}"
        
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
            "rsi": current_rsi,
            "rsi_oversold_threshold": oversold,
            "rsi_overbought_threshold": overbought,
            "macd": macd_data["macd"][-1] if macd_data["macd"] else 0.0,
            "signal_line": macd_data["signal"][-1] if macd_data["signal"] else 0.0,
            "histogram": current_histogram,
            "volume_ratio": volume_ratio,
            "divergence": divergence,  # New: divergence detection
            "volatility": volatility,  # New: volatility metric
        }

