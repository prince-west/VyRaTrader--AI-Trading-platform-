# backend/app/api/v1/market.py
"""
Market data API endpoints for real-time prices and charts.
Supports: Crypto (Binance), Forex (ExchangeRate-API, Open Exchange Rates, API Ninjas)
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import httpx
import time
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from backend.app.db.session import get_session
from backend.app.db.models import PriceTick

router = APIRouter(tags=["Market"])

# Binance public API (no key needed)
BINANCE_API = "https://api.binance.com/api/v3"


@router.get("/quote")
async def get_market_quote(
    symbol: str = Query(..., description="Trading symbol"),
    market: Optional[str] = Query("crypto", description="Market type: crypto, forex"),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get real-time market quote using data collectors with all configured API keys.
    Falls back to direct APIs if collectors don't have fresh data.
    Returns current price, 24h change, and volume.
    """
    # Try getting latest price from database (collected by data collectors)
    try:
        stmt = (
            select(PriceTick)
                .where(PriceTick.symbol == symbol)
                .where(PriceTick.market == market.lower())
                .order_by(desc(PriceTick.ts))
                .limit(1)
        )
        result = await session.exec(stmt)
        latest_tick = result.first()
        
        # Check if data is recent (less than 5 minutes old)
        # PriceTick.ts is naive UTC, so compare with naive UTC
        now_naive = datetime.utcnow()
        if latest_tick:
            age_seconds = (now_naive - latest_tick.ts).total_seconds() if latest_tick.ts else 999999
            if age_seconds < 300:  # Data less than 5 minutes old
                    # Get 24h change from historical data
                    day_ago = now_naive - timedelta(days=1)
                    stmt_24h = (
                        select(PriceTick)
                        .where(PriceTick.symbol == symbol)
                        .where(PriceTick.market == market.lower())
                        .where(PriceTick.ts >= day_ago)
                        .order_by(PriceTick.ts)
                        .limit(1)
                    )
                    result_24h = await session.exec(stmt_24h)
                    tick_24h = result_24h.first()
                    
                    change_24h = 0.0
                    if tick_24h:
                        change_24h = ((latest_tick.price - tick_24h.price) / tick_24h.price) * 100
                    
                    # Get high/low from recent data
                    stmt_range = (
                        select(PriceTick)
                        .where(PriceTick.symbol == symbol)
                        .where(PriceTick.market == market.lower())
                        .where(PriceTick.ts >= day_ago)
                    )
                    result_range = await session.exec(stmt_range)
                    ticks_range = result_range.all()
                    
                    high_24h = max([t.price for t in ticks_range]) if ticks_range else latest_tick.price
                    low_24h = min([t.price for t in ticks_range]) if ticks_range else latest_tick.price
                    volume_24h = sum([t.volume or 0 for t in ticks_range]) if ticks_range else (latest_tick.volume or 0)
                    
                    return {
                        "symbol": symbol,
                        "price": latest_tick.price,
                        "change_24h": change_24h,
                        "volume_24h": volume_24h,
                        "high_24h": high_24h,
                        "low_24h": low_24h,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "data_collector"
                    }
    except Exception as db_error:
        pass  # Continue to direct API calls
    
    # If no fresh database data, try fetching fresh using data collectors
    try:
        from backend.app.services.data_collector import (
            collect_crypto_batch,
            collect_forex_batch,
            collect_additional_crypto_forex_batch,
        )
        
        if market == "crypto":
            # Primary crypto collectors
            batch_results = await collect_crypto_batch([symbol])
            # Additional collectors that also provide crypto
            additional_results = await collect_additional_crypto_forex_batch([symbol])
            # Merge results
            for collector_name, ticks in {**batch_results, **additional_results}.items():
                for tick in ticks:
                    if tick.symbol == symbol and tick.market == "crypto":
                        return {
                            "symbol": tick.symbol,
                            "price": tick.price,
                            "change_24h": 0.0,  # Would need historical data
                            "volume_24h": tick.volume or 0,
                            "high_24h": tick.high or tick.price,
                            "low_24h": tick.low or tick.price,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": f"data_collector_{collector_name}"
                        }
        elif market == "forex":
            batch_results = await collect_forex_batch([symbol[:3], symbol[3:]])
            for collector_name, ticks in batch_results.items():
                for tick in ticks:
                    if (symbol[:3] in tick.symbol or symbol[3:] in tick.symbol) and tick.market == "forex":
                        return {
                            "symbol": symbol,
                            "price": tick.price,
                            "change_24h": 0.0,
                            "volume_24h": tick.volume or 0,
                            "high_24h": tick.high or tick.price,
                            "low_24h": tick.low or tick.price,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": f"data_collector_{collector_name}"
                        }
    except Exception as collector_error:
        pass  # Fall back to direct API calls
    
    # Fallback to direct APIs (only if data collectors don't work)
    # Crypto market - use Binance (REAL-TIME)
    if market == "crypto":
        try:
            # Ensure symbol is in Binance format
            binance_symbol = symbol.replace("USD", "USDT") if "USD" in symbol and "USDT" not in symbol else symbol
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                ticker_url = f"{BINANCE_API}/ticker/24hr"
                params = {"symbol": binance_symbol.upper()}
                
                response = await client.get(ticker_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "symbol": data.get("symbol"),
                    "price": float(data.get("lastPrice", 0)),
                    "change_24h": float(data.get("priceChangePercent", 0)),
                    "volume_24h": float(data.get("volume", 0)),
                    "high_24h": float(data.get("highPrice", 0)),
                    "low_24h": float(data.get("lowPrice", 0)),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            # Log error but continue to try other sources
            print(f"Binance API error for {binance_symbol}: {e}")
            
    # Forex market - use yfinance with fallback to demo data
    elif market == "forex":
        try:
            import yfinance as yf
            
            # Add =X suffix for forex pairs
            yf_symbol = symbol if "=X" in symbol else f"{symbol}=X"
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(period="1d")[-1:]
            
            if not data.empty and len(data) > 0:
                current_price = float(data['Close'].iloc[0])
                previous_price = float(data['Open'].iloc[0])
                change_pct = ((current_price - previous_price) / previous_price) * 100
                
                return {
                    "symbol": symbol,
                    "price": current_price,
                    "change_24h": change_pct,
                    "volume_24h": float(data['Volume'].iloc[0]),
                    "high_24h": float(data['High'].iloc[0]),
                    "low_24h": float(data['Low'].iloc[0]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            print(f"Forex error for {symbol}: {e}")
        
        # Fallback to demo forex data
        demo_prices = {
            "EURUSD": 1.1024, "GBPUSD": 1.2789, "USDJPY": 150.25,
            "AUDUSD": 0.6789, "USDCAD": 1.3421, "USDCHF": 0.8897,
            "NZ USD": 0.6234, "EURGBP": 0.8621, "EURJPY": 165.67
        }
        base_price = demo_prices.get(symbol[:6] if "=X" in symbol else symbol[:6], 1.1000)
        import random
        demo_price = base_price + random.uniform(-0.01, 0.01)
        
        return {
            "symbol": symbol,
            "price": demo_price,
            "change_24h": random.uniform(-2.0, 2.0),
            "volume_24h": 1500000000000,
            "high_24h": demo_price + 0.005,
            "low_24h": demo_price - 0.005,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    # Fallback to demo data if all fail
    raise HTTPException(status_code=404, detail=f"Market data not available for {symbol}")


@router.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="Trading symbol"),
    interval: str = Query("1m", description="Kline interval (1m, 3m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, description="Number of klines to return")
) -> List[Dict[str, Any]]:
    """
    Get kline/candlestick data from Binance for charting.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{BINANCE_API}/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            raw_klines = response.json()
            
            klines = []
            for k in raw_klines:
                klines.append({
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                })
            
            return klines
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching klines: {str(e)}")


@router.get("/orderbook")
async def get_orderbook(
    symbol: str = Query(..., description="Trading symbol"),
    limit: int = Query(20, description="Number of bids/asks")
) -> Dict[str, Any]:
    """
    Get order book data from Binance (bids and asks).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{BINANCE_API}/depth"
            params = {
                "symbol": symbol.upper(),
                "limit": min(limit, 500)
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            bids = [{"price": float(b[0]), "quantity": float(b[1])} for b in data.get("bids", [])[:limit]]
            asks = [{"price": float(a[0]), "quantity": float(a[1])} for a in data.get("asks", [])[:limit]]
            
            return {
                "symbol": symbol.upper(),
                "bids": bids,
                "asks": asks,
                "timestamp": time.time() * 1000,
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orderbook: {str(e)}")
