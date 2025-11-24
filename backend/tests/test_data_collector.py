"""
Unit tests for data collector module.
Tests all collectors with mocked HTTPX responses and database inserts.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

import httpx
import pytest_asyncio
from sqlmodel import Session

from backend.app.services.data_collector import (
    collect_binance_tickers,
    collect_coingecko_markets,
    collect_cryptocompare_prices,
    collect_newsapi,
    collect_fred,
    collect_alpha_vantage_quotes,
    collect_exchangerate_api,
    collect_commodities_api,
    collect_api_ninjas_commodities,
    collect_gnews,
    collect_mediastack,
    collect_crypto_batch,
    collect_news_batch,
    collect_macro_batch,
    _ensure_data_source,
    _get_api_key
)
from backend.app.db.models import PriceTick, NewsItem, OnchainMetric, DataSource
from backend.app.db.session import get_session


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.exec = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client."""
    with patch('backend.app.services.data_collector._client') as mock_client:
        client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client
        yield client


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    with patch('backend.app.services.data_collector.settings') as mock_settings:
        mock_settings.NEWSAPI_KEY = "test_newsapi_key"
        mock_settings.FRED_API_KEY = "test_fred_key"
        mock_settings.ALPHAVANTAGE_API_KEY = "test_alpha_key"
        mock_settings.EXCHANGERATE_API_KEY = "test_exchange_key"
        mock_settings.COMMODITIES_API_KEY = "test_commodities_key"
        mock_settings.API_NINJAS_KEY = "test_ninjas_key"
        mock_settings.GNEWS_API_KEY = "test_gnews_key"
        mock_settings.MEDIASTACK_API_KEY = "test_mediastack_key"
        yield mock_settings


class TestBinanceCollector:
    """Test Binance ticker collector."""
    
    @pytest.mark.asyncio
    async def test_collect_binance_tickers_success(self, mock_httpx_client, mock_session):
        """Test successful Binance ticker collection."""
        # Mock HTTPX response
        mock_response = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000.00",
            "openPrice": "49000.00",
            "highPrice": "51000.00",
            "lowPrice": "48500.00",
            "volume": "1000.5",
            "quoteVolume": "50000000.0",
            "bidPrice": "49999.00",
            "askPrice": "50001.00"
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        # Mock database operations
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_binance_tickers(["BTCUSDT"])
                
                assert len(result) == 1
                tick = result[0]
                assert tick.symbol == "BTCUSDT"
                assert tick.price == 50000.0
                assert tick.open == 49000.0
                assert tick.high == 51000.0
                assert tick.low == 48500.0
                assert tick.volume == 1000.5
                assert tick.quote_volume == 50000000.0
                assert tick.market == "crypto"
                
                # Verify database operations
                mock_session.add.assert_called()
                mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_collect_binance_tickers_empty_symbols(self):
        """Test Binance collector with empty symbols list."""
        result = await collect_binance_tickers([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_collect_binance_tickers_http_error(self, mock_httpx_client):
        """Test Binance collector with HTTP error."""
        mock_httpx_client.request.side_effect = httpx.HTTPError("Connection error")
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source'):
                result = await collect_binance_tickers(["BTCUSDT"])
                assert result == []


class TestCoinGeckoCollector:
    """Test CoinGecko markets collector."""
    
    @pytest.mark.asyncio
    async def test_collect_coingecko_markets_success(self, mock_httpx_client, mock_session):
        """Test successful CoinGecko markets collection."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "current_price": 50000.0,
                "total_volume": 1000000.0,
                "market_cap": 1000000000.0
            }
        ]
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_coingecko_markets(["bitcoin"])
                
                assert len(result) == 1
                tick = result[0]
                assert tick.symbol == "BTC"
                assert tick.price == 50000.0
                assert tick.volume == 1000000.0
                assert tick.market == "crypto"
                
                mock_session.add.assert_called()
                mock_session.commit.assert_called()


class TestCryptoCompareCollector:
    """Test CryptoCompare collector."""
    
    @pytest.mark.asyncio
    async def test_collect_cryptocompare_prices_success(self, mock_httpx_client, mock_session):
        """Test successful CryptoCompare price collection."""
        mock_response = {
            "RAW": {
                "BTC": {
                    "USD": {
                        "PRICE": 50000.0,
                        "OPEN24HOUR": 49000.0,
                        "HIGH24HOUR": 51000.0,
                        "LOW24HOUR": 48500.0,
                        "TOTALVOLUME24H": 1000.0,
                        "MKTCAP": 1000000000.0
                    }
                }
            }
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_cryptocompare_prices(["BTC"])
                
                assert len(result) == 1
                tick = result[0]
                assert tick.symbol == "BTC"
                assert tick.price == 50000.0
                assert tick.open == 49000.0
                assert tick.high == 51000.0
                assert tick.low == 48500.0
                assert tick.volume == 1000.0
                assert tick.market == "crypto"


class TestNewsCollectors:
    """Test news collectors."""
    
    @pytest.mark.asyncio
    async def test_collect_newsapi_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful NewsAPI collection."""
        mock_response = {
            "articles": [
                {
                    "title": "Bitcoin Price Surges",
                    "description": "Bitcoin reaches new highs",
                    "url": "https://example.com/news1",
                    "publishedAt": "2024-01-01T12:00:00Z",
                    "source": {"name": "Test News"}
                }
            ]
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_newsapi("bitcoin")
                
                assert len(result) == 1
                news = result[0]
                assert news.title == "Bitcoin Price Surges"
                assert news.summary == "Bitcoin reaches new highs"
                assert news.url == "https://example.com/news1"
                assert news.language == "en"
                
                mock_session.add.assert_called()
                mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_collect_newsapi_missing_key(self, mock_httpx_client):
        """Test NewsAPI collector with missing API key."""
        with patch('backend.app.services.data_collector._get_api_key') as mock_get_key:
            mock_get_key.return_value = None
            
            result = await collect_newsapi("bitcoin")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_collect_gnews_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful GNews collection."""
        mock_response = {
            "articles": [
                {
                    "title": "Market Analysis",
                    "description": "Detailed market analysis",
                    "url": "https://example.com/gnews1",
                    "language": "en"
                }
            ]
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_gnews("markets")
                
                assert len(result) == 1
                news = result[0]
                assert news.title == "Market Analysis"
                assert news.summary == "Detailed market analysis"
                assert news.url == "https://example.com/gnews1"


class TestStockCollectors:
    """Test stock market collectors."""
    
    @pytest.mark.asyncio
    async def test_collect_alpha_vantage_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful Alpha Vantage collection."""
        mock_response = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.00",
                "03. high": "155.00",
                "04. low": "145.00"
            }
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_alpha_vantage_quotes(["AAPL"])
                
                assert len(result) == 1
                tick = result[0]
                assert tick.symbol == "AAPL"
                assert tick.price == 150.0
                assert tick.market == "stock"


class TestForexCollectors:
    """Test forex collectors."""
    
    @pytest.mark.asyncio
    async def test_collect_exchangerate_api_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful ExchangeRate-API collection."""
        mock_response = {
            "conversion_rates": {
                "EUR": 0.85,
                "GBP": 0.73,
                "JPY": 110.0
            }
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_exchangerate_api("USD")
                
                assert len(result) == 3
                assert all(tick.market == "forex" for tick in result)
                assert any(tick.symbol == "USDEUR" and tick.price == 0.85 for tick in result)
                assert any(tick.symbol == "USDGBP" and tick.price == 0.73 for tick in result)
                assert any(tick.symbol == "USDJPY" and tick.price == 110.0 for tick in result)


class TestCommoditiesCollectors:
    """Test commodities collectors."""
    
    @pytest.mark.asyncio
    async def test_collect_commodities_api_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful Commodities-API collection."""
        mock_response = {
            "data": {
                "rates": {
                    "XAU": 2000.0,
                    "XAG": 25.0
                }
            }
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_commodities_api(["XAU", "XAG"])
                
                assert len(result) == 2
                assert all(tick.market == "commodity" for tick in result)
                assert any(tick.symbol == "XAU" and tick.price == 2000.0 for tick in result)
                assert any(tick.symbol == "XAG" and tick.price == 25.0 for tick in result)


class TestMacroCollectors:
    """Test macroeconomic collectors."""
    
    @pytest.mark.asyncio
    async def test_collect_fred_success(self, mock_httpx_client, mock_session, mock_settings):
        """Test successful FRED collection."""
        mock_response = {
            "observations": [
                {"date": "2024-01-01", "value": "5.0"},
                {"date": "2024-01-02", "value": "5.1"}
            ]
        }
        mock_httpx_client.request.return_value.json.return_value = mock_response
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            with patch('backend.app.services.data_collector._ensure_data_source') as mock_ensure_ds:
                mock_ensure_ds.return_value = "test_source_id"
                
                result = await collect_fred(["DGS10"])
                
                assert len(result) == 1
                metric = result[0]
                assert metric.network == "macro"
                assert metric.metric_name == "fred_DGS10"
                assert metric.value == 5.1  # Latest value
                assert metric.unit is None


class TestBatchCollectors:
    """Test batch collection functions."""
    
    @pytest.mark.asyncio
    async def test_collect_crypto_batch(self, mock_httpx_client, mock_session):
        """Test crypto batch collection."""
        with patch('backend.app.services.data_collector.collect_binance_tickers') as mock_binance:
            with patch('backend.app.services.data_collector.collect_coingecko_markets') as mock_coingecko:
                with patch('backend.app.services.data_collector.collect_cryptocompare_prices') as mock_cc:
                    mock_binance.return_value = [MagicMock(symbol="BTCUSDT")]
                    mock_coingecko.return_value = [MagicMock(symbol="BTC")]
                    mock_cc.return_value = [MagicMock(symbol="BTC")]
                    
                    result = await collect_crypto_batch(["BTCUSDT"], ["bitcoin"])
                    
                    assert "binance" in result
                    assert "coingecko" in result
                    assert "cryptocompare" in result
                    assert len(result["binance"]) == 1
                    assert len(result["coingecko"]) == 1
                    assert len(result["cryptocompare"]) == 1
    
    @pytest.mark.asyncio
    async def test_collect_news_batch(self, mock_httpx_client, mock_session, mock_settings):
        """Test news batch collection."""
        with patch('backend.app.services.data_collector.collect_newsapi') as mock_newsapi:
            with patch('backend.app.services.data_collector.collect_gnews') as mock_gnews:
                with patch('backend.app.services.data_collector.collect_mediastack') as mock_mediastack:
                    mock_newsapi.return_value = [MagicMock(title="News 1")]
                    mock_gnews.return_value = [MagicMock(title="News 2")]
                    mock_mediastack.return_value = [MagicMock(title="News 3")]
                    
                    result = await collect_news_batch("markets")
                    
                    assert "newsapi" in result
                    assert "gnews" in result
                    assert "mediastack" in result
                    assert len(result["newsapi"]) == 1
                    assert len(result["gnews"]) == 1
                    assert len(result["mediastack"]) == 1


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_ensure_data_source_new(self, mock_session):
        """Test creating new data source."""
        mock_session.exec.return_value.first.return_value = None
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            result = await _ensure_data_source("test_source", "crypto", "https://test.com", "https://docs.test.com")
            
            assert result is not None
            mock_session.add.assert_called()
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_ensure_data_source_existing(self, mock_session):
        """Test using existing data source."""
        existing_source = MagicMock()
        existing_source.id = "existing_id"
        mock_session.exec.return_value.first.return_value = existing_source
        
        with patch('backend.app.services.data_collector.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            result = await _ensure_data_source("test_source", "crypto", "https://test.com", "https://docs.test.com")
            
            assert result == "existing_id"
            mock_session.add.assert_not_called()
    
    def test_get_api_key(self, mock_settings):
        """Test API key retrieval."""
        with patch('backend.app.services.data_collector.settings') as mock_settings:
            mock_settings.TEST_KEY = "test_value"
            
            result = _get_api_key("TEST_KEY")
            assert result == "test_value"
            
            result = _get_api_key("NONEXISTENT_KEY")
            assert result is None


@pytest.mark.integration
class TestDataCollectorIntegration:
    """Integration tests for data collectors."""
    
    @pytest.mark.asyncio
    async def test_collector_error_handling(self):
        """Test that collectors handle errors gracefully."""
        with patch('backend.app.services.data_collector._client') as mock_client:
            mock_client.return_value.__aenter__.side_effect = Exception("Connection failed")
            
            # All collectors should return empty lists on error
            result = await collect_binance_tickers(["BTCUSDT"])
            assert result == []
            
            result = await collect_coingecko_markets(["bitcoin"])
            assert result == []
            
            result = await collect_newsapi("test")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_collector_timeout_handling(self):
        """Test that collectors handle timeouts gracefully."""
        with patch('backend.app.services.data_collector._client') as mock_client:
            mock_client.return_value.__aenter__.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await collect_binance_tickers(["BTCUSDT"])
            assert result == []
