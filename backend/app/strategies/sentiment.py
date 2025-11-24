# backend/app/strategies/sentiment.py
from typing import List, Dict, Any, Optional
from backend.app.strategies.base import StrategyBase


class SentimentStrategy(StrategyBase):
    """
    Sentiment strategy that uses news/social sentiment.
    This strategy relies on external news data, so it uses the legacy run() method.
    """
    name = "sentiment"

    def __init__(self):
        super().__init__()  # Initialize StrategyBase
        self.POS = {"buy", "bull", "surge", "rally", "long", "bullish", "up"}
        self.NEG = {"sell", "bear", "dump", "crash", "short", "bearish", "down"}

    def _detect_pattern(self, symbol: str) -> bool:
        """Sentiment strategy doesn't use pattern completion - uses external news."""
        return False  # Always use legacy run() method

    def _confirm_completion(self, symbol: str) -> bool:
        """Sentiment strategy doesn't use pattern completion."""
        return False

    def _get_action_from_pattern(self, symbol: str) -> Optional[str]:
        """Sentiment strategy doesn't use pattern completion."""
        return None

    def _build_signal(self, symbol: str, action: str) -> Optional[Dict[str, Any]]:
        """Sentiment strategy doesn't use pattern completion."""
        return None

    def score_text(self, text: str) -> float:
        if not text:
            return 0.0
        t = text.lower()
        score = 0
        for p in self.POS:
            if p in t:
                score += 1
        for n in self.NEG:
            if n in t:
                score -= 1
        return float(score)

    def run(self, symbol: str, prices: List[float], **extra) -> Dict[str, Any]:
        """
        Expects extra.get('recent_news') -> List[str] (bodies)
        Returns a sentiment-based signal: strong positive sentiment -> buy, strong negative -> sell
        """
        news = extra.get("recent_news") or []
        if not news:
            return {"signal": "hold", "score": 0.0, "confidence": 0.0}

        total = 0.0
        for n in news:
            total += self.score_text(n)
        avg = total / max(1, len(news))
        confidence = min(1.0, abs(avg) / 3.0)
        score = min(5.0, abs(avg))

        # FIX: Relaxed thresholds (professional standard: 0.5-0.8 for sentiment signals)
        # This makes sentiment strategy more responsive while maintaining quality
        if avg > 0.5:  # Relaxed from 0.8
            return {"signal": "buy", "score": float(score), "confidence": float(confidence)}
        elif avg < -0.5:  # Relaxed from -0.8
            return {"signal": "sell", "score": float(score), "confidence": float(confidence)}
        else:
            return {"signal": "hold", "score": 0.0, "confidence": 0.0}
