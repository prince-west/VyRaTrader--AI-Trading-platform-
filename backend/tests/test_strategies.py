"""
Unit tests for trading strategies.
Tests strategy modules with test database fixtures and sample inputs.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from backend.app.strategies.trend_following import TrendFollowingStrategy, generate_trend_signal
from backend.app.strategies.volatility_breakout import VolatilityBreakoutStrategy, generate_breakout_signal
from backend.app.strategies.sentiment_filter import SentimentFilter, analyze_sentiment
from backend.app.db.models import PriceTick, NewsItem, DataSource
from backend.app.db.session import get_session


@pytest.fixture
def mock_session():
    """Mock database session for strategy tests."""
    session = AsyncMock()
    session.exec = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5T')
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)  # Random walk around 50000
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices - 50,
        'high': prices + 100,
        'low': prices - 100,
        'close': prices,
        'volume': np.random.uniform(100, 1000, 100)
    }).set_index('timestamp')


@pytest.fixture
def sample_news_data():
    """Sample news data for testing."""
    return [
        NewsItem(
            id="1",
            title="Bitcoin Price Surges to New Highs",
            summary="Bitcoin reaches $50,000 as institutional adoption increases",
            url="https://example.com/news1",
            language="en",
            published_at=datetime.now(timezone.utc),
            tickers=["BTC"],
            categories=["crypto"],
            sentiment=0.8,
            created_at=datetime.now(timezone.utc)
        ),
        NewsItem(
            id="2",
            title="Market Volatility Concerns",
            summary="Analysts warn of increased market volatility ahead",
            url="https://example.com/news2",
            language="en",
            published_at=datetime.now(timezone.utc),
            tickers=["BTC", "ETH"],
            categories=["markets"],
            sentiment=-0.3,
            created_at=datetime.now(timezone.utc)
        )
    ]


class TestTrendFollowingStrategy:
    """Test trend-following strategy."""
    
    @pytest.mark.asyncio
    async def test_trend_following_initialization(self):
        """Test strategy initialization."""
        strategy = TrendFollowingStrategy()
        assert strategy.fast_ema == 12
        assert strategy.slow_ema == 26
        assert strategy.adx_period == 14
        assert strategy.adx_threshold == 25.0
        assert strategy.min_confidence == 0.6
        assert strategy.name == "trend_following"
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, mock_session):
        """Test historical data retrieval."""
        # Mock price ticks
        mock_ticks = [
            PriceTick(
                id="1",
                symbol="BTCUSDT",
                price=50000.0,
                open=49000.0,
                high=51000.0,
                low=48500.0,
                volume=1000.0,
                ts=datetime.now(timezone.utc)
            ),
            PriceTick(
                id="2",
                symbol="BTCUSDT",
                price=50100.0,
                open=50000.0,
                high=50200.0,
                low=49900.0,
                volume=1100.0,
                ts=datetime.now(timezone.utc) + timedelta(minutes=5)
            )
        ]
        
        mock_session.exec.return_value.all.return_value = mock_ticks
        
        strategy = TrendFollowingStrategy()
        df = await strategy.get_historical_data(mock_session, "BTCUSDT", hours_back=1)
        
        assert not df.empty
        assert len(df) == 2
        assert df.index.name == 'timestamp'
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    def test_calculate_ema(self, sample_price_data):
        """Test EMA calculation."""
        strategy = TrendFollowingStrategy()
        ema = strategy.calculate_ema(sample_price_data['close'], 12)
        
        assert len(ema) == len(sample_price_data)
        assert not ema.isna().all()
        assert ema.iloc[-1] is not None
    
    def test_calculate_adx(self, sample_price_data):
        """Test ADX calculation."""
        strategy = TrendFollowingStrategy()
        adx = strategy.calculate_adx(sample_price_data, 14)
        
        assert len(adx) == len(sample_price_data)
        # ADX should be positive when calculated
        assert adx.iloc[-1] >= 0
    
    def test_analyze_timeframe_bullish_crossover(self):
        """Test timeframe analysis with bullish EMA crossover."""
        # Create data with bullish crossover
        dates = pd.date_range(start='2024-01-01', periods=50, freq='5T')
        prices = np.linspace(49000, 51000, 50)  # Upward trend
        
        df = pd.DataFrame({
            'open': prices - 50,
            'high': prices + 100,
            'low': prices - 100,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 50)
        }, index=dates)
        
        strategy = TrendFollowingStrategy(fast_ema=5, slow_ema=10, adx_threshold=20.0)
        result = strategy.analyze_timeframe(df)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['buy', 'sell', 'hold']
        assert 0.0 <= result['confidence'] <= 1.0
    
    def test_analyze_timeframe_insufficient_data(self):
        """Test timeframe analysis with insufficient data."""
        # Create data with insufficient points
        dates = pd.date_range(start='2024-01-01', periods=10, freq='5T')
        prices = np.linspace(49000, 51000, 10)
        
        df = pd.DataFrame({
            'open': prices - 50,
            'high': prices + 100,
            'low': prices - 100,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 10)
        }, index=dates)
        
        strategy = TrendFollowingStrategy()
        result = strategy.analyze_timeframe(df)
        
        assert result['signal'] == 'hold'
        assert result['confidence'] == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_signal_success(self, mock_session, sample_price_data):
        """Test successful signal generation."""
        # Mock historical data retrieval
        with patch.object(TrendFollowingStrategy, 'get_historical_data', return_value=sample_price_data):
            strategy = TrendFollowingStrategy()
            signal = await strategy.generate_signal(mock_session, "BTCUSDT")
            
            assert 'strategy' in signal
            assert 'symbol' in signal
            assert 'action' in signal
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            assert 'confidence' in signal
            assert 'timestamp' in signal
            
            assert signal['strategy'] == 'trend_following'
            assert signal['symbol'] == 'BTCUSDT'
            assert signal['action'] in ['buy', 'sell', 'hold']
            assert isinstance(signal['entry'], (int, float))
            assert isinstance(signal['sl'], (int, float))
            assert isinstance(signal['tp'], (int, float))
            assert 0.0 <= signal['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_signal_insufficient_data(self, mock_session):
        """Test signal generation with insufficient data."""
        with patch.object(TrendFollowingStrategy, 'get_historical_data', return_value=pd.DataFrame()):
            strategy = TrendFollowingStrategy()
            signal = await strategy.generate_signal(mock_session, "BTCUSDT")
            
            assert signal['action'] == 'hold'
            assert signal['confidence'] == 0.0
            assert signal['reason'] == 'insufficient_data'
    
    @pytest.mark.asyncio
    async def test_generate_trend_signal_convenience(self, mock_session):
        """Test convenience function for trend signal generation."""
        with patch.object(TrendFollowingStrategy, 'generate_signal') as mock_generate:
            mock_generate.return_value = {
                'strategy': 'trend_following',
                'symbol': 'BTCUSDT',
                'action': 'buy',
                'entry': 50000.0,
                'sl': 49000.0,
                'tp': 52000.0,
                'confidence': 0.8,
                'timestamp': datetime.now().isoformat()
            }
            
            signal = await generate_trend_signal(mock_session, "BTCUSDT")
            
            assert signal['strategy'] == 'trend_following'
            assert signal['action'] == 'buy'
            mock_generate.assert_called_once()


class TestVolatilityBreakoutStrategy:
    """Test volatility breakout strategy."""
    
    @pytest.mark.asyncio
    async def test_volatility_breakout_initialization(self):
        """Test strategy initialization."""
        strategy = VolatilityBreakoutStrategy()
        assert strategy.lookback_period == 20
        assert strategy.atr_period == 14
        assert strategy.breakout_multiplier == 2.0
        assert strategy.min_volume_ratio == 1.5
        assert strategy.max_risk_per_trade == 0.02
        assert strategy.name == "volatility_breakout"
    
    def test_calculate_atr(self, sample_price_data):
        """Test ATR calculation."""
        strategy = VolatilityBreakoutStrategy()
        atr = strategy.calculate_atr(sample_price_data, 14)
        
        assert isinstance(atr, float)
        assert atr >= 0
    
    def test_calculate_volatility_metrics(self, sample_price_data):
        """Test volatility metrics calculation."""
        strategy = VolatilityBreakoutStrategy()
        metrics = strategy.calculate_volatility_metrics(sample_price_data)
        
        assert 'atr' in metrics
        assert 'volatility' in metrics
        assert 'volume_ratio' in metrics
        assert isinstance(metrics['atr'], float)
        assert isinstance(metrics['volatility'], float)
        assert isinstance(metrics['volume_ratio'], float)
    
    def test_detect_breakout_bullish(self):
        """Test bullish breakout detection."""
        # Create data with bullish breakout
        dates = pd.date_range(start='2024-01-01', periods=25, freq='15T')
        prices = np.concatenate([
            np.linspace(49000, 49500, 20),  # Consolidation
            [50000, 50200, 50500, 50800, 51000]  # Breakout
        ])
        
        df = pd.DataFrame({
            'open': prices - 50,
            'high': prices + 100,
            'low': prices - 100,
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 25)
        }, index=dates)
        
        strategy = VolatilityBreakoutStrategy()
        atr = strategy.calculate_atr(df, 14)
        result = strategy.detect_breakout(df, atr)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['buy', 'sell', 'hold']
        assert 0.0 <= result['confidence'] <= 1.0
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        strategy = VolatilityBreakoutStrategy()
        
        # Test normal case
        pos_size = strategy.calculate_position_size(10000.0, 0.02, 0.01, 1.0)
        assert pos_size > 0
        assert pos_size <= 1000.0  # Max 10% of account
        
        # Test edge cases
        pos_size = strategy.calculate_position_size(0.0, 0.02, 0.01, 1.0)
        assert pos_size == 0.0
        
        pos_size = strategy.calculate_position_size(10000.0, 0.0, 0.01, 1.0)
        assert pos_size == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_signal_success(self, mock_session, sample_price_data):
        """Test successful signal generation."""
        with patch.object(VolatilityBreakoutStrategy, 'get_historical_data', return_value=sample_price_data):
            strategy = VolatilityBreakoutStrategy()
            signal = await strategy.generate_signal(mock_session, "BTCUSDT", 10000.0)
            
            assert 'strategy' in signal
            assert 'symbol' in signal
            assert 'action' in signal
            assert 'entry' in signal
            assert 'sl' in signal
            assert 'tp' in signal
            assert 'confidence' in signal
            assert 'position_size' in signal
            assert 'timestamp' in signal
            
            assert signal['strategy'] == 'volatility_breakout'
            assert signal['symbol'] == 'BTCUSDT'
            assert signal['action'] in ['buy', 'sell', 'hold']
            assert isinstance(signal['position_size'], (int, float))
    
    @pytest.mark.asyncio
    async def test_generate_breakout_signal_convenience(self, mock_session):
        """Test convenience function for breakout signal generation."""
        with patch.object(VolatilityBreakoutStrategy, 'generate_signal') as mock_generate:
            mock_generate.return_value = {
                'strategy': 'volatility_breakout',
                'symbol': 'BTCUSDT',
                'action': 'buy',
                'entry': 50000.0,
                'sl': 49000.0,
                'tp': 52000.0,
                'confidence': 0.7,
                'position_size': 1000.0,
                'timestamp': datetime.now().isoformat()
            }
            
            signal = await generate_breakout_signal(mock_session, "BTCUSDT", 10000.0)
            
            assert signal['strategy'] == 'volatility_breakout'
            assert signal['action'] == 'buy'
            mock_generate.assert_called_once()


class TestSentimentFilter:
    """Test sentiment filter strategy."""
    
    @pytest.mark.asyncio
    async def test_sentiment_filter_initialization(self):
        """Test strategy initialization."""
        filter_strategy = SentimentFilter()
        assert filter_strategy.lookback_hours == 24
        assert filter_strategy.min_news_count == 3
        assert filter_strategy.sentiment_threshold == 0.3
        assert filter_strategy.confidence_modifier == 0.2
        assert filter_strategy.name == "sentiment_filter"
    
    def test_extract_text_content(self, sample_news_data):
        """Test text content extraction."""
        filter_strategy = SentimentFilter()
        text = filter_strategy.extract_text_content(sample_news_data[0])
        
        assert "bitcoin price surges" in text.lower()
        assert "bitcoin reaches" in text.lower()
    
    def test_calculate_lexicon_score_positive(self):
        """Test positive sentiment lexicon scoring."""
        filter_strategy = SentimentFilter()
        text = "bitcoin price surges to new highs with strong bullish momentum"
        score = filter_strategy.calculate_lexicon_score(text)
        
        assert score > 0
        assert -1.0 <= score <= 1.0
    
    def test_calculate_lexicon_score_negative(self):
        """Test negative sentiment lexicon scoring."""
        filter_strategy = SentimentFilter()
        text = "market crash causes panic selling and bearish sentiment"
        score = filter_strategy.calculate_lexicon_score(text)
        
        assert score < 0
        assert -1.0 <= score <= 1.0
    
    def test_calculate_lexicon_score_neutral(self):
        """Test neutral sentiment lexicon scoring."""
        filter_strategy = SentimentFilter()
        text = "the market opened today and closed at the same level"
        score = filter_strategy.calculate_lexicon_score(text)
        
        assert score == 0.0
    
    def test_calculate_emoji_score_positive(self):
        """Test positive emoji scoring."""
        filter_strategy = SentimentFilter()
        text = "bitcoin is going to the moon 🚀📈💰"
        score = filter_strategy.calculate_emoji_score(text)
        
        assert score > 0
        assert -1.0 <= score <= 1.0
    
    def test_calculate_emoji_score_negative(self):
        """Test negative emoji scoring."""
        filter_strategy = SentimentFilter()
        text = "market is crashing 📉💸😱"
        score = filter_strategy.calculate_emoji_score(text)
        
        assert score < 0
        assert -1.0 <= score <= 1.0
    
    def test_calculate_news_sentiment(self, sample_news_data):
        """Test news sentiment calculation."""
        filter_strategy = SentimentFilter()
        result = filter_strategy.calculate_news_sentiment(sample_news_data)
        
        assert 'sentiment_score' in result
        assert 'confidence' in result
        assert 'news_count' in result
        assert 'breakdown' in result
        
        assert -1.0 <= result['sentiment_score'] <= 1.0
        assert 0.0 <= result['confidence'] <= 1.0
        assert result['news_count'] == 2
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_success(self, mock_session, sample_news_data):
        """Test successful sentiment analysis."""
        mock_session.exec.return_value.all.return_value = sample_news_data
        
        with patch('backend.app.strategies.sentiment_filter.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            result = await analyze_sentiment(mock_session, "BTC", "bitcoin")
            
            assert 'strategy' in result
            assert 'symbol' in result
            assert 'sentiment_score' in result
            assert 'confidence' in result
            assert 'recommendation' in result
            assert 'timestamp' in result
            
            assert result['strategy'] == 'sentiment_filter'
            assert result['symbol'] == 'BTC'
            assert -1.0 <= result['sentiment_score'] <= 1.0
            assert 0.0 <= result['confidence'] <= 1.0
            assert result['recommendation'] in ['positive', 'negative', 'neutral', 'insufficient_data']
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_insufficient_data(self, mock_session):
        """Test sentiment analysis with insufficient news data."""
        mock_session.exec.return_value.all.return_value = []
        
        with patch('backend.app.strategies.sentiment_filter.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            result = await analyze_sentiment(mock_session, "BTC", "bitcoin")
            
            assert result['recommendation'] == 'insufficient_data'
            assert result['news_count'] == 0
    
    def test_create_confidence_filter(self, sample_news_data):
        """Test confidence filter creation."""
        filter_strategy = SentimentFilter()
        
        # Mock sentiment analysis result
        sentiment_analysis = {
            'sentiment_score': 0.5,
            'confidence': 0.8,
            'recommendation': 'positive'
        }
        
        filter_func = filter_strategy.create_confidence_filter(sentiment_analysis)
        
        # Test with buy signal
        buy_signal = {
            'strategy': 'test',
            'action': 'buy',
            'confidence': 0.6
        }
        
        filtered_signal = filter_func(buy_signal)
        
        assert 'sentiment_filter' in filtered_signal
        assert filtered_signal['confidence'] > buy_signal['confidence']  # Should increase confidence
    
    def test_create_trade_blocker(self, sample_news_data):
        """Test trade blocker creation."""
        filter_strategy = SentimentFilter()
        
        # Mock sentiment analysis result with very negative sentiment
        sentiment_analysis = {
            'sentiment_score': -0.8,
            'confidence': 0.9,
            'recommendation': 'negative'
        }
        
        blocker_func = filter_strategy.create_trade_blocker(sentiment_analysis)
        
        # Test with buy signal (should be blocked)
        buy_signal = {
            'strategy': 'test',
            'action': 'buy',
            'confidence': 0.6
        }
        
        should_block = blocker_func(buy_signal)
        assert should_block == True
        
        # Test with sell signal (should not be blocked)
        sell_signal = {
            'strategy': 'test',
            'action': 'sell',
            'confidence': 0.6
        }
        
        should_block = blocker_func(sell_signal)
        assert should_block == False


@pytest.mark.integration
class TestStrategyIntegration:
    """Integration tests for strategies."""
    
    @pytest.mark.asyncio
    async def test_strategy_error_handling(self, mock_session):
        """Test that strategies handle errors gracefully."""
        # Mock database error
        mock_session.exec.side_effect = Exception("Database error")
        
        # All strategies should return hold signals on error
        trend_strategy = TrendFollowingStrategy()
        signal = await trend_strategy.generate_signal(mock_session, "BTCUSDT")
        assert signal['action'] == 'hold'
        assert 'error' in signal['reason']
        
        breakout_strategy = VolatilityBreakoutStrategy()
        signal = await breakout_strategy.generate_signal(mock_session, "BTCUSDT", 10000.0)
        assert signal['action'] == 'hold'
        assert 'error' in signal['reason']
    
    @pytest.mark.asyncio
    async def test_strategy_signal_format_consistency(self, mock_session, sample_price_data):
        """Test that all strategies return consistent signal formats."""
        with patch.object(TrendFollowingStrategy, 'get_historical_data', return_value=sample_price_data):
            with patch.object(VolatilityBreakoutStrategy, 'get_historical_data', return_value=sample_price_data):
                
                # Test trend following
                trend_strategy = TrendFollowingStrategy()
                trend_signal = await trend_strategy.generate_signal(mock_session, "BTCUSDT")
                
                # Test volatility breakout
                breakout_strategy = VolatilityBreakoutStrategy()
                breakout_signal = await breakout_strategy.generate_signal(mock_session, "BTCUSDT", 10000.0)
                
                # Both signals should have the same required fields
                required_fields = ['strategy', 'symbol', 'action', 'entry', 'sl', 'tp', 'confidence', 'timestamp']
                
                for field in required_fields:
                    assert field in trend_signal
                    assert field in breakout_signal
                
                # Actions should be valid
                assert trend_signal['action'] in ['buy', 'sell', 'hold']
                assert breakout_signal['action'] in ['buy', 'sell', 'hold']
                
                # Confidences should be in valid range
                assert 0.0 <= trend_signal['confidence'] <= 1.0
                assert 0.0 <= breakout_signal['confidence'] <= 1.0
