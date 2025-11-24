# backend/app/services/data_feed.py
import asyncio
from typing import List, Dict, Any, Optional
import httpx
import time
from backend.app.core.config import settings

BINANCE_REST = "https://api.binance.com/api/v3"

class BinanceMarketDataAdapter:
    """
    Lightweight Binance public REST adapter for klines and ticker price.
    No API key required for public market data endpoints.
    """

    def __init__(self, base_url: str = BINANCE_REST, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_klines(self, symbol: str, interval: str = "1m", limit: int = 500) -> List[Dict[str, Any]]:
        """
        Returns list of candles: [{open_time, open, high, low, close, volume, close_time, ...}, ...]
        symbol: e.g., "BTCUSDT"
        """
        url = f"{self.base_url}/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            raw = r.json()
        candles = []
        for k in raw:
            candles.append({
                "open_time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": int(k[6]),
            })
        return candles

    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        url = f"{self.base_url}/ticker/price"
        params = {"symbol": symbol.upper()}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            d = r.json()
        return {"symbol": d.get("symbol"), "price": float(d.get("price", 0.0)), "ts": int(time.time() * 1000)}


class OandaMarketDataAdapter:
    """
    Minimal OANDA public adapter for pricing (requires OANDA_TOKEN and ACCOUNT_ID in config).
    You must set settings.OANDA_API_TOKEN and settings.OANDA_ACCOUNT_ID to use.
    """
    def __init__(self):
        self.token = getattr(settings, "OANDA_API_TOKEN", None)
        self.account_id = getattr(settings, "OANDA_ACCOUNT_ID", None)
        self.base_url = getattr(settings, "OANDA_API_BASE", "https://api-fxpractice.oanda.com")

    async def get_candles(self, instrument: str, granularity: str = "M1", count: int = 200) -> List[Dict[str, Any]]:
        if not self.token or not self.account_id:
            raise RuntimeError("OANDA_API_TOKEN or OANDA_ACCOUNT_ID not configured")
        url = f"{self.base_url}/v3/instruments/{instrument}/candles"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"granularity": granularity, "count": count, "price": "M"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            j = r.json()
        out = []
        for c in j.get("candles", []):
            out.append({
                "time": c.get("time"),
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
                "volume": int(c.get("volume", 0))
            })
        return out


async def get_historical_ohlc_fallback(symbol: str, period: str = "1d", limit: int = 365) -> List[Dict[str, Any]]:
    """
    Fallback historical fetch using yfinance for stocks or ETFs.
    symbol like 'AAPL' or 'BTC-USD' (yfinance supports crypto with -USD).
    """
    try:
        import yfinance as yf
    except Exception:
        raise RuntimeError("yfinance not installed. pip install yfinance to use fallback historical data.")
    loop = asyncio.get_event_loop()
    def _hist():
        df = yf.download(symbol, period=f"{limit}d", interval=period, progress=False)
        if df is None or df.empty:
            return []
        out = []
        for idx, row in df.iterrows():
            out.append({"time": int(pd.Timestamp(idx).timestamp()), "open": float(row["Open"]), "high": float(row["High"]), "low": float(row["Low"]), "close": float(row["Close"]), "volume": float(row["Volume"])})
        return out
    return await loop.run_in_executor(None, _hist)
