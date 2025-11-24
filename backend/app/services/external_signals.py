"""
External Signal Aggregator Service
Aggregates trading signals from external platforms (TradingView, Reddit, Twitter)
without requiring user accounts or API keys where possible.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

# Try importing optional dependencies
try:
    import praw  # Reddit API
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False

try:
    from tradingview_ta import TA_Handler
    TRADINGVIEW_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AVAILABLE = False


class ExternalSignalAggregator:
    """
    Aggregates trading signals from external platforms.
    No user accounts required - uses public data and APIs.
    """
    
    def __init__(self):
        self.reddit_client = None
        # Reddit PRAW requires client_id/client_secret for full access
        # For now, we'll skip Reddit if not configured (graceful degradation)
        # You can add Reddit API keys later if needed, but it's optional
    
    def get_tradingview_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get signals from TradingView by analyzing popular indicators.
        Uses public TradingView data without authentication.
        """
        signals = []
        
        if not TRADINGVIEW_AVAILABLE:
            return signals
        
        try:
            # Convert symbol format (BTCUSDT -> BTCUSDT for crypto)
            tv_symbol = symbol.replace("USDT", "").replace("USD", "")
            
            # Analyze using TradingView TA library (public data)
            handler = TA_Handler(
                symbol=tv_symbol,
                screener="crypto",  # or "forex", "stock"
                exchange="BINANCE",  # Default exchange
                interval="1h"
            )
            
            analysis = handler.get_analysis()
            
            if analysis:
                # Parse recommendation
                recommendation = analysis.summary.get("RECOMMENDATION", "NEUTRAL")
                
                # Map to our signal format
                signal_map = {
                    "STRONG_BUY": "buy",
                    "BUY": "buy",
                    "NEUTRAL": "hold",
                    "SELL": "sell",
                    "STRONG_SELL": "sell"
                }
                
                signal = signal_map.get(recommendation, "hold")
                score = analysis.summary.get("BUY", 0) - analysis.summary.get("SELL", 0)
                confidence = min(1.0, abs(score) / 10.0)
                
                signals.append({
                    "source": "tradingview",
                    "signal": signal,
                    "score": abs(score) if score != 0 else 0.0,
                    "confidence": confidence,
                    "timestamp": datetime.utcnow(),
                    "details": {
                        "recommendation": recommendation,
                        "buy_signals": analysis.summary.get("BUY", 0),
                        "sell_signals": analysis.summary.get("SELL", 0),
                        "oscillators": analysis.summary.get("BUY", 0),
                        "moving_averages": analysis.summary.get("SELL", 0)
                    }
                })
        except Exception as e:
            # Fail silently - external service might be down
            pass
        
        return signals
    
    def get_reddit_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Scrape Reddit for trading sentiment and signals.
        Uses web scraping or public Reddit API endpoints.
        Note: Reddit API requires authentication for full access.
        For now, returns empty - can be enhanced with web scraping or API keys.
        This is optional and doesn't break the strategy if unavailable.
        """
        # TODO: Implement Reddit scraping with web scraping or API keys
        # Can use public Reddit RSS feeds or web scraping as fallback
        return []
    
    def get_twitter_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X for crypto trading signals using public methods.
        Note: Twitter API requires auth, so we use RSS feeds or web scraping as fallback.
        """
        signals = []
        
        try:
            # Extract base symbol
            base_symbol = symbol.replace("USDT", "").replace("USD", "").upper()
            
            # Use Twitter RSS feeds (public, no auth)
            # Example: search.twitter.com RSS feeds (if available)
            # For now, return empty - can be enhanced with proper scraping
            
            # Alternative: Use public Twitter search without auth (limited)
            # This would require more sophisticated scraping
            
        except Exception:
            pass
        
        return signals
    
    def aggregate_external_signals(self, symbol: str) -> Dict[str, Any]:
        """
        Aggregate all external signals for a symbol.
        Returns weighted consensus signal.
        """
        all_signals = []
        
        # Collect signals from all sources
        all_signals.extend(self.get_tradingview_signals(symbol))
        all_signals.extend(self.get_reddit_signals(symbol))
        all_signals.extend(self.get_twitter_signals(symbol))
        
        if not all_signals:
            return {
                "signal": "hold",
                "score": 0.0,
                "confidence": 0.0,
                "sources": [],
                "reason": "no_external_signals_available"
            }
        
        # Weight signals by source reliability
        source_weights = {
            "tradingview": 1.0,  # Most reliable
            "reddit": 0.6,       # Less reliable
            "twitter": 0.4       # Least reliable
        }
        
        # Aggregate signals
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for sig in all_signals:
            source = sig.get("source", "unknown")
            weight = source_weights.get(source, 0.5) * sig.get("confidence", 0.5)
            
            if sig["signal"] == "buy":
                buy_score += sig["score"] * weight
            elif sig["signal"] == "sell":
                sell_score += sig["score"] * weight
            
            total_weight += weight
        
        # Calculate final signal
        if total_weight == 0:
            return {
                "signal": "hold",
                "score": 0.0,
                "confidence": 0.0,
                "sources": [],
                "reason": "insufficient_signal_weight"
            }
        
        net_score = (buy_score - sell_score) / max(1.0, total_weight)
        final_signal = "buy" if net_score > 0.3 else "sell" if net_score < -0.3 else "hold"
        final_confidence = min(1.0, abs(net_score) / 2.0)
        
        return {
            "signal": final_signal,
            "score": abs(net_score),
            "confidence": final_confidence,
            "sources": [s["source"] for s in all_signals],
            "details": {
                "total_signals": len(all_signals),
                "buy_score": buy_score,
                "sell_score": sell_score
            }
        }


# Global instance
_external_aggregator: Optional[ExternalSignalAggregator] = None


def get_external_aggregator() -> ExternalSignalAggregator:
    """Get or create global external signal aggregator."""
    global _external_aggregator
    if _external_aggregator is None:
        _external_aggregator = ExternalSignalAggregator()
    return _external_aggregator

