"""
Social Copy Trading Strategy
Aggregates trading signals from external platforms (TradingView, Reddit, Twitter)
without requiring user accounts. Uses public data and sentiment analysis.
"""

from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase
from backend.app.services.external_signals import get_external_aggregator


class SocialCopyStrategy(StrategyBase):
    """
    Social copy trading strategy that aggregates signals from external platforms.
    No user accounts required - uses public TradingView, Reddit, and Twitter data.
    This strategy uses external signals, so it uses the legacy run() method.
    """
    
    name = "social_copy"
    
    def __init__(self):
        super().__init__()  # Initialize StrategyBase
        self.aggregator = get_external_aggregator()
    
    def _detect_pattern(self, symbol: str) -> bool:
        """Social copy strategy doesn't use pattern completion - uses external signals."""
        return False  # Always use legacy run() method
    
    def _confirm_completion(self, symbol: str) -> bool:
        """Social copy strategy doesn't use pattern completion."""
        return False
    
    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Social copy strategy doesn't use pattern completion."""
        return None
    
    def _build_signal(self, symbol: str, action: str) -> Optional[Dict[str, Any]]:
        """Social copy strategy doesn't use pattern completion."""
        return None
    
    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """
        Run social copy strategy by aggregating external platform signals.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            prices: Price history (used for context but not primary signal)
            **extra: Additional context
        
        Returns:
            Dict with keys: signal, score, confidence
        """
        try:
            # FIX: Check if aggregator is available
            if not self.aggregator:
                return {
                    "signal": "hold",
                    "score": 0.0,
                    "confidence": 0.0,
                    "reason": "aggregator_not_initialized"
                }
            
            # Get aggregated external signals
            external_signal = self.aggregator.aggregate_external_signals(symbol)
            
            if not external_signal or external_signal.get("signal") == "hold":
                return {
                    "signal": "hold",
                    "score": 0.0,
                    "confidence": 0.0,
                    "reason": external_signal.get("reason", "no_external_signals") if external_signal else "no_external_signals"
                }
            
            # Map to our format
            signal = external_signal.get("signal", "hold")
            score = external_signal.get("score", 0.0)
            confidence = external_signal.get("confidence", 0.0)
            
            # FIX: Only return non-hold signals if confidence is meaningful
            if signal == "hold" or confidence < 0.3:
                return {
                    "signal": "hold",
                    "score": 0.0,
                    "confidence": 0.0,
                    "reason": "low_confidence_external_signals"
                }
            
            # Reason includes sources
            sources = external_signal.get("sources", [])
            reason = f"external_signals_from_{','.join(sources) if sources else 'unknown'}"
            
            return {
                "signal": signal,
                "score": float(score),
                "confidence": float(confidence),
                "reason": reason,
                "details": external_signal.get("details", {})
            }
            
        except Exception as e:
            # Fail gracefully - return hold if external services are down
            # FIX: Log error for debugging but don't break the system
            from backend.app.core.logger import logger
            logger.debug(f"Social copy strategy error for {symbol}: {str(e)}")
            return {
                "signal": "hold",
                "score": 0.0,
                "confidence": 0.0,
                "reason": f"external_service_error: {str(e)}"
            }

