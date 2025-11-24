"""
Sentiment filter strategy using news analysis and lexicon-based scoring.
- Analyzes NewsItem entries from all news sources
- Simple lexicon/emoji-based sentiment scoring
- Provides filter functions to modify strategy confidence or block trades
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable

import numpy as np
from sqlmodel import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.strategies.base import StrategyBase
from backend.app.core.logger import logger
from backend.app.db.models import NewsItem


class SentimentFilterStrategy(StrategyBase):
    name = "sentiment_filter"

    """News sentiment analysis and trading filter."""
    
    def __init__(
        self,
        lookback_hours: int = 24,
        min_news_count: int = 3,
        sentiment_threshold: float = 0.3,
        confidence_modifier: float = 0.2,
    ):
        self.lookback_hours = lookback_hours
        self.min_news_count = min_news_count
        self.sentiment_threshold = sentiment_threshold
        self.confidence_modifier = confidence_modifier
        self.name = "sentiment_filter"
        
        # Simple sentiment lexicons
        self.positive_words = {
            'bullish', 'bull', 'rise', 'rising', 'up', 'upward', 'gain', 'gains', 'profit', 'profits',
            'growth', 'growing', 'strong', 'strength', 'positive', 'optimistic', 'optimism', 'buy',
            'buying', 'purchase', 'invest', 'investment', 'rally', 'surge', 'breakout', 'breakthrough',
            'success', 'successful', 'win', 'winning', 'victory', 'triumph', 'excellent', 'great',
            'good', 'better', 'best', 'improve', 'improvement', 'recovery', 'recover', 'rebound',
            'momentum', 'trending', 'hot', 'popular', 'demand', 'demanding', 'interest', 'interested',
            'confidence', 'confident', 'trust', 'trusted', 'stable', 'stability', 'secure', 'security'
        }
        
        self.negative_words = {
            'bearish', 'bear', 'fall', 'falling', 'down', 'downward', 'loss', 'losses', 'decline',
            'declining', 'weak', 'weakness', 'negative', 'pessimistic', 'pessimism', 'sell', 'selling',
            'dump', 'dumping', 'crash', 'crashed', 'collapse', 'collapsed', 'failure', 'failed',
            'lose', 'losing', 'defeat', 'defeated', 'terrible', 'awful', 'bad', 'worse', 'worst',
            'deteriorate', 'deterioration', 'recession', 'depression', 'crisis', 'panic', 'fear',
            'worried', 'concern', 'concerned', 'risk', 'risky', 'danger', 'dangerous', 'volatile',
            'volatility', 'uncertain', 'uncertainty', 'doubt', 'doubtful', 'skeptical', 'skepticism',
            'bubble', 'overvalued', 'undervalued', 'correction', 'pullback', 'retreat', 'withdrawal'
        }
        
        # Emoji sentiment mapping
        self.positive_emojis = {
            '🚀', '📈', '💰', '💎', '🔥', '⭐', '✨', '🎉', '👍', '💪', '🏆', '✅', '🌟', '💯'
        }
        
        self.negative_emojis = {
            '📉', '💸', '😱', '😰', '😢', '😭', '💔', '❌', '⚠️', '🚨', '💀', '🔥', '💥'
        }
    
    async def get_recent_news(
        self, 
        session: AsyncSession, 
        symbol: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[NewsItem]:
        """Fetch recent news items for sentiment analysis."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
        
        # Build query conditions
        conditions = [NewsItem.created_at >= cutoff_time]
        
        if symbol:
            # Look for symbol in title, summary, or tickers
            symbol_conditions = [
                NewsItem.title.contains(symbol),
                NewsItem.summary.contains(symbol),
            ]
            conditions.append(and_(*symbol_conditions))
        
        if query:
            query_conditions = [
                NewsItem.title.contains(query),
                NewsItem.summary.contains(query),
            ]
            conditions.append(and_(*query_conditions))
        
        stmt = select(NewsItem).where(and_(*conditions)).order_by(desc(NewsItem.created_at))
        
        result = await session.exec(stmt)
        news_items = result.all()
        
        return news_items
    
    def extract_text_content(self, news_item: NewsItem) -> str:
        """Extract text content from news item for analysis."""
        content_parts = []
        
        if news_item.title:
            content_parts.append(news_item.title.lower())
        
        if news_item.summary:
            content_parts.append(news_item.summary.lower())
        
        return ' '.join(content_parts)
    
    def calculate_lexicon_score(self, text: str) -> float:
        """Calculate sentiment score using lexicon-based approach."""
        if not text:
            return 0.0
        
        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        if not words:
            return 0.0
        
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Calculate score
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0
        
        score = (positive_count - negative_count) / total_sentiment_words
        return max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
    
    def calculate_emoji_score(self, text: str) -> float:
        """Calculate sentiment score based on emojis."""
        if not text:
            return 0.0
        
        positive_emoji_count = sum(1 for emoji in self.positive_emojis if emoji in text)
        negative_emoji_count = sum(1 for emoji in self.negative_emojis if emoji in text)
        
        total_emojis = positive_emoji_count + negative_emoji_count
        if total_emojis == 0:
            return 0.0
        
        score = (positive_emoji_count - negative_emoji_count) / total_emojis
        return max(-1.0, min(1.0, score))
    
    def calculate_news_sentiment(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """Calculate overall sentiment from a list of news items."""
        if not news_items:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "news_count": 0,
                "breakdown": {}
            }
        
        lexicon_scores = []
        emoji_scores = []
        
        for item in news_items:
            text = self.extract_text_content(item)
            lexicon_score = self.calculate_lexicon_score(text)
            emoji_score = self.calculate_emoji_score(text)
            
            lexicon_scores.append(lexicon_score)
            emoji_scores.append(emoji_score)
        
        # Calculate weighted average (lexicon has higher weight)
        avg_lexicon = np.mean(lexicon_scores) if lexicon_scores else 0.0
        avg_emoji = np.mean(emoji_scores) if emoji_scores else 0.0
        
        # Combined score (70% lexicon, 30% emoji)
        combined_score = (avg_lexicon * 0.7) + (avg_emoji * 0.3)
        
        # Confidence based on number of news items and score consistency
        score_std = np.std(lexicon_scores) if len(lexicon_scores) > 1 else 0.0
        consistency = 1.0 - min(1.0, score_std)  # Lower std = higher consistency
        news_count_factor = min(1.0, len(news_items) / self.min_news_count)
        confidence = consistency * news_count_factor
        
        return {
            "sentiment_score": float(combined_score),
            "confidence": float(confidence),
            "news_count": len(news_items),
            "breakdown": {
                "lexicon_score": float(avg_lexicon),
                "emoji_score": float(avg_emoji),
                "score_std": float(score_std),
                "consistency": float(consistency)
            }
        }
    
    async def analyze_sentiment(
        self, 
        session: AsyncSession, 
        symbol: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment for a given symbol or query."""
        try:
            # Get recent news
            news_items = await self.get_recent_news(session, symbol, query)
            
            if len(news_items) < self.min_news_count:
                return {
                    "strategy": self.name,
                    "symbol": symbol,
                    "query": query,
                    "sentiment_score": 0.0,
                    "confidence": 0.0,
                    "news_count": len(news_items),
                    "recommendation": "insufficient_data",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Calculate sentiment
            sentiment_result = self.calculate_news_sentiment(news_items)
            
            # Determine recommendation
            score = sentiment_result["sentiment_score"]
            confidence = sentiment_result["confidence"]
            
            if confidence < 0.5:
                recommendation = "low_confidence"
            elif score > self.sentiment_threshold:
                recommendation = "positive"
            elif score < -self.sentiment_threshold:
                recommendation = "negative"
            else:
                recommendation = "neutral"
            
            return {
                "strategy": self.name,
                "symbol": symbol,
                "query": query,
                "sentiment_score": sentiment_result["sentiment_score"],
                "confidence": sentiment_result["confidence"],
                "news_count": sentiment_result["news_count"],
                "recommendation": recommendation,
                "timestamp": datetime.utcnow().isoformat(),
                "breakdown": sentiment_result["breakdown"]
            }
            
        except Exception as exc:
            logger.exception(f"Error analyzing sentiment for {symbol}: {exc}")
            return {
                "strategy": self.name,
                "symbol": symbol,
                "query": query,
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "news_count": 0,
                "recommendation": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc)
            }
    
    def create_confidence_filter(self, sentiment_analysis: Dict[str, Any]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Create a filter function that modifies strategy confidence based on sentiment."""
        def filter_function(strategy_signal: Dict[str, Any]) -> Dict[str, Any]:
            """Filter function that modifies strategy signals based on sentiment."""
            if sentiment_analysis["recommendation"] == "insufficient_data":
                # No modification if insufficient data
                return strategy_signal
            
            sentiment_score = sentiment_analysis["sentiment_score"]
            sentiment_confidence = sentiment_analysis["confidence"]
            
            # Only apply filter if sentiment confidence is reasonable
            if sentiment_confidence < 0.3:
                return strategy_signal
            
            original_confidence = strategy_signal.get("confidence", 0.0)
            action = strategy_signal.get("action", "hold")
            
            # Apply sentiment filter
            if action == "buy":
                if sentiment_score > 0:
                    # Positive sentiment supports buy signal
                    confidence_modifier = self.confidence_modifier * sentiment_score
                    new_confidence = min(0.95, original_confidence + confidence_modifier)
                else:
                    # Negative sentiment reduces buy confidence
                    confidence_modifier = self.confidence_modifier * abs(sentiment_score)
                    new_confidence = max(0.05, original_confidence - confidence_modifier)
            
            elif action == "sell":
                if sentiment_score < 0:
                    # Negative sentiment supports sell signal
                    confidence_modifier = self.confidence_modifier * abs(sentiment_score)
                    new_confidence = min(0.95, original_confidence + confidence_modifier)
                else:
                    # Positive sentiment reduces sell confidence
                    confidence_modifier = self.confidence_modifier * sentiment_score
                    new_confidence = max(0.05, original_confidence - confidence_modifier)
            
            else:
                # Hold signal - no modification
                new_confidence = original_confidence
            
            # Update the signal
            filtered_signal = strategy_signal.copy()
            filtered_signal["confidence"] = new_confidence
            filtered_signal["sentiment_filter"] = {
                "original_confidence": original_confidence,
                "sentiment_score": sentiment_score,
                "sentiment_confidence": sentiment_confidence,
                "confidence_change": new_confidence - original_confidence
            }
            
            return filtered_signal
        
        return filter_function
    
    def create_trade_blocker(self, sentiment_analysis: Dict[str, Any]) -> Callable[[Dict[str, Any]], bool]:
        """Create a function that blocks trades based on extreme sentiment."""
        def should_block_trade(strategy_signal: Dict[str, Any]) -> bool:
            """Determine if a trade should be blocked based on sentiment."""
            if sentiment_analysis["recommendation"] in ["insufficient_data", "error"]:
                return False
            
            sentiment_score = sentiment_analysis["sentiment_score"]
            sentiment_confidence = sentiment_analysis["confidence"]
            action = strategy_signal.get("action", "hold")
            
            # Only block if sentiment confidence is high
            if sentiment_confidence < 0.7:
                return False
            
            # Block trades that go against strong sentiment
            if action == "buy" and sentiment_score < -0.6:
                return True  # Block buy on very negative sentiment
            
            if action == "sell" and sentiment_score > 0.6:
                return True  # Block sell on very positive sentiment
            
            return False
        
        return should_block_trade


# Convenience functions for external use
async def analyze_sentiment(
    session: AsyncSession,
    symbol: Optional[str] = None,
    query: Optional[str] = None,
    **filter_kwargs
) -> Dict[str, Any]:
    """Analyze sentiment for a symbol or query."""
    filter_strategy = SentimentFilterStrategy(**filter_kwargs)
    return await filter_strategy.analyze_sentiment(session, symbol, query)


def create_sentiment_filter(
    sentiment_analysis: Dict[str, Any],
    **filter_kwargs
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Create a sentiment-based confidence filter."""
    filter_strategy = SentimentFilterStrategy(**filter_kwargs)
    return filter_strategy.create_confidence_filter(sentiment_analysis)


def create_sentiment_blocker(
    sentiment_analysis: Dict[str, Any],
    **filter_kwargs
) -> Callable[[Dict[str, Any]], bool]:
    """Create a sentiment-based trade blocker."""
    filter_strategy = SentimentFilterStrategy(**filter_kwargs)
    return filter_strategy.create_trade_blocker(sentiment_analysis)
