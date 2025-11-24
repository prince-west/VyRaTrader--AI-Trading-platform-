"""
Async data collectors for prioritized free/public market and news APIs - Version 24 (FMP and EODHD removed).
- Uses httpx.AsyncClient with retries and basic rate-limit handling.
- Safely skips collectors when API keys are missing.
- Persists results into SQLModel models: PriceTick, NewsItem, OnchainMetric, DataSource.
- Supports crypto and forex market data collection.
- FMP (#12) and EODHD (#15) collectors removed (they don't provide crypto/forex data).

Supported APIs:
1. CoinGecko, 2. Binance, 3. CoinMarketCap, 4. Kraken, 5. Messari, 6. CryptoCompare,
7. Coinbase, 8. Coinpaprika, 9. Etherscan/BscScan/PolygonScan, 10. Alpha Vantage,
11. Twelve Data, 13. Finnhub, 14. Polygon.io, 16. Tiingo,
17. ExchangeRate API, 18. Open Exchange Rates, 19. FRED, 20. World Bank API,
21. API Ninjas, 22. NewsAPI.org, 23. GNews, 24. Marketaux,
25. CoinGecko (token metrics), 26. Messari (on-chain metrics)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx
from tenacity import after_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_session
from backend.app.db.models import DataSource, NewsItem, OnchainMetric, PriceTick
from sqlmodel import select

DEFAULT_TIMEOUT_S: float = 20.0
CONCURRENT_LIMIT: int = 10


def _now_utc() -> datetime:
    """
    Return timezone-aware UTC datetime for fields with DateTime(timezone=True).
    """
    return datetime.now(timezone.utc)


def _now_naive_utc() -> datetime:
    """
    Return naive UTC datetime for fields without timezone=True (e.g., PriceTick.ts, received_at).
    """
    return datetime.utcnow()


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert any tz-aware datetime to naive UTC, or return unchanged if already naive.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume already naive UTC
        return dt
    # convert to UTC then drop tzinfo
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _get_api_key(name: str) -> Optional[str]:
    """Get API key from settings."""
    return getattr(settings, name, None)


def _coalesce_symbols(symbols: Optional[Sequence[str]]) -> List[str]:
    return [s for s in (symbols or []) if s]


async def _ensure_data_source(name: str, category: str, base_url: Optional[str], docs_url: Optional[str]) -> str:
    """Upsert a DataSource and return its id."""
    async for session in get_session():
        existing = (await session.exec(select(DataSource).where(DataSource.name == name))).first()
        if existing:
            return existing.id or ""
        ds = DataSource(
            name=name,
            category=category,
            base_url=base_url,
            docs_url=docs_url,
            is_active=True,
            created_at=_now_utc(),
            updated_at=_now_utc(),
        )
        session.add(ds)
        await session.commit()
        await session.refresh(ds)
        return ds.id or ""


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {
        "User-Agent": "VyRaTrader/1.0 (+https://vyratrader.com)",
        "Accept": "application/json",
    }
    if extra:
        h.update({k: v for k, v in extra.items() if v is not None})
    return h


class TransientHTTPError(Exception):
    """Raised on 5xx or 429 responses to trigger retry."""


@retry(
    retry=retry_if_exception_type(TransientHTTPError),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
    stop=stop_after_attempt(5),
    after=after_log(logger, "WARNING"),
)
async def _fetch_json(client: httpx.AsyncClient, method: str, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
    resp = await client.request(method, url, params=params, headers=headers)
    if resp.status_code in (429, 500, 502, 503, 504):
        # Backoff on rate limit or transient server errors
        raise TransientHTTPError(f"{resp.status_code} for {url}")
    resp.raise_for_status()
    if resp.headers.get("Content-Type", "").startswith("application/json"):
        return resp.json()
    return resp.json()  # best-effort


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(DEFAULT_TIMEOUT_S))


# ------------------------
# CRYPTO APIs (1-9)
# ------------------------

# 1. CoinGecko - Free unlimited
async def collect_coingecko_markets(coin_ids: Sequence[str], vs_currency: str = "usd") -> List[PriceTick]:
    """Collect cryptocurrency market data from CoinGecko."""
    ids = ",".join(_coalesce_symbols(coin_ids))
    if not ids:
        return []
    source_id = await _ensure_data_source("coingecko", "crypto", "https://api.coingecko.com/api/v3", "https://www.coingecko.com/en/api/documentation")
    async with _client() as client:
        data = await _fetch_json(
            client,
            "GET",
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": vs_currency, "ids": ids, "order": "market_cap_desc", "per_page": 250, "page": 1, "sparkline": "false"},
        )
    out: List[PriceTick] = []
    now = _now_naive_utc()
    for row in data or []:
        try:
            symbol = (row.get("symbol") or "").upper()
            price = float(row.get("current_price") or 0.0)
            vol = float(row.get("total_volume") or 0.0)
            t = PriceTick(
                source_id=source_id,
                symbol=symbol,
                market="crypto",
                price=price,
                open=None,
                high=None,
                low=None,
                volume=vol,
                quote_volume=None,
                ts=now,
                received_at=now,
                extra={"id": row.get("id"), "market_cap": row.get("market_cap")},
            )
            out.append(t)
        except Exception as exc:
            logger.warning("CoinGecko parse error: %s", exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 2. Binance - Free unlimited
async def collect_binance_tickers(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect cryptocurrency ticker data from Binance."""
    symbols_list = _coalesce_symbols(symbols)
    if not symbols_list:
        return []
    source_id = await _ensure_data_source("binance", "crypto", "https://api.binance.com", "https://binance-docs.github.io/apidocs/")
    out: List[PriceTick] = []
    sem = asyncio.Semaphore(CONCURRENT_LIMIT)
    async with _client() as client:
        async def fetch_symbol(sym: str) -> Optional[PriceTick]:
            async with sem:
                try:
                    data = await _fetch_json(client, "GET", "https://api.binance.com/api/v3/ticker/24hr", params={"symbol": sym})
                    tick = PriceTick(
                        source_id=source_id,
                        symbol=sym,
                        market="crypto",
                        price=float(data.get("lastPrice") or data.get("weightedAvgPrice") or 0.0),
                        open=float(data.get("openPrice") or 0.0),
                        high=float(data.get("highPrice") or 0.0),
                        low=float(data.get("lowPrice") or 0.0),
                        volume=float(data.get("volume") or 0.0),
                        quote_volume=float(data.get("quoteVolume") or 0.0),
                        ts=_now_naive_utc(),
                        received_at=_now_naive_utc(),
                        extra={"bidPrice": data.get("bidPrice"), "askPrice": data.get("askPrice")},
                    )
                    return tick
                except Exception as exc:
                    logger.warning("Binance ticker failed for %s: %s", sym, exc)
                    return None
        results = await asyncio.gather(*(fetch_symbol(s) for s in symbols_list))
        out = [t for t in results if t is not None]
    if not out:
        return []
    # persist
    async for session in get_session():
        for t in out:
            session.add(t)
        await session.commit()
    return out


# 3. CoinMarketCap - API key required
async def collect_cmc_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect cryptocurrency quotes from CoinMarketCap."""
    key = _get_api_key("COINMARKETCAP_API_KEY")
    if not key:
        logger.info("CMC API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("coinmarketcap", "crypto", "https://pro-api.coinmarketcap.com", "https://coinmarketcap.com/api/")
    async with _client() as client:
        data = await _fetch_json(
            client,
            "GET",
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(_coalesce_symbols(symbols))},
            headers=_headers({"X-CMC_PRO_API_KEY": key}),
        )
    out: List[PriceTick] = []
    now = _now_naive_utc()
    quotes = (data or {}).get("data", {}) or {}
    for sym, payload in quotes.items():
        try:
            usd = (payload.get("quote", {}) or {}).get("USD", {})
            t = PriceTick(
                source_id=source_id,
                symbol=sym.upper(),
                market="crypto",
                price=float(usd.get("price") or 0.0),
                volume=float(usd.get("volume_24h") or 0.0),
                ts=now,
                received_at=now,
                extra={"market_cap": usd.get("market_cap")},
            )
            out.append(t)
        except Exception as exc:
            logger.warning("CMC parse error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 4. Kraken - Free unlimited
async def collect_kraken_tickers(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect cryptocurrency ticker data from Kraken."""
    symbols_list = _coalesce_symbols(symbols)
    if not symbols_list:
        return []
    source_id = await _ensure_data_source("kraken", "crypto", "https://api.kraken.com", "https://docs.kraken.com/rest")
    out: List[PriceTick] = []
    async with _client() as client:
        try:
            data = await _fetch_json(client, "GET", "https://api.kraken.com/0/public/Ticker", params={"pair": ",".join(symbols_list)})
            result = (data or {}).get("result", {})
            for pair, ticker_data in result.items():
                try:
                    price = float(ticker_data.get("c", [0])[0] or 0.0)
                    volume = float(ticker_data.get("v", [0])[0] or 0.0)
                    t = PriceTick(
                        source_id=source_id,
                        symbol=pair.replace("X", "").replace("Z", ""),
                        market="crypto",
                        price=price,
                        volume=volume,
                        ts=_now_naive_utc(),
                        received_at=_now_naive_utc(),
                        extra={"ask": ticker_data.get("a"), "bid": ticker_data.get("b")},
                    )
                    out.append(t)
                except Exception as exc:
                    logger.warning("Kraken parse error for %s: %s", pair, exc)
        except Exception as exc:
            logger.warning("Kraken API error: %s", exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 5. Messari - Limited endpoints
async def collect_messari_metrics(asset_keys: Sequence[str]) -> List[OnchainMetric]:
    """Collect on-chain metrics from Messari."""
    if not asset_keys:
        return []
    source_id = await _ensure_data_source("messari", "crypto", "https://data.messari.io/api", "https://messari.io/api")
    out: List[OnchainMetric] = []
    async with _client() as client:
        for asset in asset_keys:
            try:
                # Try the metrics endpoint
                data = await _fetch_json(client, "GET", f"https://data.messari.io/api/v1/assets/{asset}/metrics")
                # Safely extract metric value
                data_dict = data or {}
                risk_metrics = data_dict.get("data", {}).get("risk_metrics", {})
                sharpe = risk_metrics.get("sharpe_ratios", {})
                value = sharpe.get("last_30_days", 0.0) if isinstance(sharpe, dict) else 0.0
                
                m = OnchainMetric(
                    network=asset,
                    metric_name="messari_sharpe_30d",
                    value=float(value),
                    unit="score",
                    ts=_now_utc(),
                    source_id=source_id,
                    extra={"raw": data_dict},
                )
                out.append(m)
            except Exception as exc:
                logger.debug("Messari metrics failed for %s: %s", asset, str(exc))
    if out:
        async for session in get_session():
            for m in out:
                session.add(m)
            await session.commit()
    return out


# 6. CryptoCompare - API key optional
async def collect_cryptocompare_prices(symbols: Sequence[str], tsym: str = "USD") -> List[PriceTick]:
    """Collect cryptocurrency prices from CryptoCompare."""
    syms = _coalesce_symbols(symbols)
    if not syms:
        return []
    source_id = await _ensure_data_source("cryptocompare", "crypto", "https://min-api.cryptocompare.com", "https://min-api.cryptocompare.com/documentation")
    async with _client() as client:
        data = await _fetch_json(
            client,
            "GET",
            "https://min-api.cryptocompare.com/data/pricemultifull",
            params={"fsyms": ",".join(syms), "tsyms": tsym},
        )
    raw = (data or {}).get("RAW", {})
    out: List[PriceTick] = []
    now = _now_naive_utc()
    for sym in syms:
        try:
            row = raw.get(sym, {}).get(tsym, {})
            price = float(row.get("PRICE") or 0.0)
            vol = float(row.get("TOTALVOLUME24H") or 0.0)
            t = PriceTick(
                source_id=source_id,
                symbol=sym,
                market="crypto",
                price=price,
                open=float(row.get("OPEN24HOUR") or 0.0),
                high=float(row.get("HIGH24HOUR") or 0.0),
                low=float(row.get("LOW24HOUR") or 0.0),
                volume=vol,
                quote_volume=None,
                ts=now,
                received_at=now,
                extra={"MKTCAP": row.get("MKTCAP")},
            )
            out.append(t)
        except Exception as exc:
            logger.warning("CryptoCompare parse error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 7. Coinbase - Free unlimited
async def collect_coinbase_rates(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect cryptocurrency exchange rates from Coinbase."""
    symbols_list = _coalesce_symbols(symbols)
    if not symbols_list:
        return []
    source_id = await _ensure_data_source("coinbase", "crypto", "https://api.exchange.coinbase.com", "https://docs.cloud.coinbase.com/exchange/docs")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in symbols_list:
            try:
                # Convert BTCUSDT to BTC-USD format for Coinbase
                # Remove USDT/USTC/UST suffix and add USD
                if sym.endswith("USDT") or sym.endswith("USTC") or sym.endswith("UST"):
                    base = sym[:-4]  # Remove USDT
                    coinbase_sym = f"{base}-USD"
                elif len(sym) > 2:
                    # Try to split symbol like BTCUSD -> BTC-USD
                    if "USD" in sym:
                        base = sym.replace("USD", "")
                        coinbase_sym = f"{base}-USD"
                    else:
                        coinbase_sym = sym
                else:
                    continue  # Skip invalid formats
                
                data = await _fetch_json(client, "GET", f"https://api.exchange.coinbase.com/products/{coinbase_sym}/ticker")
                price = float(data.get("price") or 0.0)
                volume = float(data.get("volume") or 0.0)
                t = PriceTick(
                    source_id=source_id,
                    symbol=sym,  # Keep original symbol
                    market="crypto",
                    price=price,
                    volume=volume,
                    ts=_now_utc(),
                    received_at=_now_utc(),
                    extra={"bid": data.get("bid"), "ask": data.get("ask")},
                )
                out.append(t)
            except Exception as exc:
                logger.warning("Coinbase error for %s: %s", sym, str(exc))
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 8. Coinpaprika - Free 20,000/month
async def collect_coinpaprika_tickers(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect cryptocurrency market data from Coinpaprika."""
    source_id = await _ensure_data_source("coinpaprika", "crypto", "https://api.coinpaprika.com", "https://api.coinpaprika.com")
    out: List[PriceTick] = []
    async with _client() as client:
        try:
            data = await _fetch_json(client, "GET", "https://api.coinpaprika.com/v1/tickers")
            for ticker in data or []:
                try:
                    symbol = ticker.get("symbol", "").upper()
                    if not any(s.upper() in symbol for s in _coalesce_symbols(symbols)):
                        continue
                    t = PriceTick(
                        source_id=source_id,
                        symbol=symbol,
                        market="crypto",
                        price=float(ticker.get("quotes", {}).get("USD", {}).get("price", 0.0)),
                        volume=float(ticker.get("quotes", {}).get("USD", {}).get("volume_24h", 0.0)),
                        ts=_now_naive_utc(),
                        received_at=_now_naive_utc(),
                        extra={"market_cap": ticker.get("quotes", {}).get("USD", {}).get("market_cap")},
                    )
                    out.append(t)
                except Exception as exc:
                    logger.warning("Coinpaprika parse error: %s", exc)
        except Exception as exc:
            logger.warning("Coinpaprika API error: %s", exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 9. Etherscan, BscScan, PolygonScan - API key required
async def collect_etherscan_eth_stats() -> List[OnchainMetric]:
    """Collect Ethereum statistics from Etherscan."""
    key = _get_api_key("ETHERSCAN_API_KEY")
    if not key:
        logger.info("Etherscan API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("etherscan", "crypto", "https://api.etherscan.io", "https://etherscan.io/apis")
    try:
        async with _client() as client:
            data = await _fetch_json(client, "GET", "https://api.etherscan.io/api", params={"module": "stats", "action": "ethprice", "apikey": key})
        price = float(((data or {}).get("result", {}).get("ethusd") or 0.0))
    except Exception as exc:
        logger.warning("Etherscan API error: %s", str(exc))
        return []
    m = OnchainMetric(
        network="ethereum",
        metric_name="eth_usd",
        value=price,
        unit="USD",
        ts=_now_utc(),
        source_id=source_id,
        extra=None,
    )
    async for session in get_session():
        session.add(m)
        await session.commit()
    return [m]


async def collect_bscscan_stats() -> List[OnchainMetric]:
    """Collect Binance Smart Chain statistics from BscScan."""
    key = _get_api_key("BSCSCAN_API_KEY")
    if not key:
        logger.info("BscScan API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("bscscan", "crypto", "https://api.bscscan.com", "https://bscscan.com/apis")
    try:
        async with _client() as client:
            data = await _fetch_json(client, "GET", "https://api.bscscan.com/api", params={"module": "stats", "action": "bnbprice", "apikey": key})
        price = float(((data or {}).get("result", {}).get("ethusd") or 0.0))
    except Exception as exc:
        logger.warning("BscScan API error: %s", str(exc))
        return []
    m = OnchainMetric(
        network="binance_smart_chain",
        metric_name="bnb_usd",
        value=price,
        unit="USD",
        ts=_now_utc(),
        source_id=source_id,
        extra=None,
    )
    async for session in get_session():
        session.add(m)
        await session.commit()
    return [m]


async def collect_polygonscan_stats() -> List[OnchainMetric]:
    """Collect Polygon chain statistics from PolygonScan."""
    key = _get_api_key("POLYGONSCAN_API_KEY")
    if not key:
        logger.info("PolygonScan API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("polygonscan", "crypto", "https://api.polygonscan.com", "https://polygonscan.com/apis")
    try:
        async with _client() as client:
            data = await _fetch_json(client, "GET", "https://api.polygonscan.com/api", params={"module": "stats", "action": "maticprice", "apikey": key})
        price = float(((data or {}).get("result", {}).get("ethusd") or 0.0))
    except Exception as exc:
        logger.warning("PolygonScan API error: %s", str(exc))
        return []
    m = OnchainMetric(
        network="polygon",
        metric_name="matic_usd",
        value=price,
        unit="USD",
        ts=_now_utc(),
        source_id=source_id,
        extra=None,
    )
    async for session in get_session():
        session.add(m)
        await session.commit()
    return [m]


# ------------------------
# STOCK APIs (10-16) - Excluding FMP (#12) and EODHD (#15)
# ------------------------

# 10. Alpha Vantage - Free 25/day (provides crypto and forex data)
async def collect_alpha_vantage_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect stock quotes from Alpha Vantage."""
    key = _get_api_key("ALPHA_VANTAGE_API_KEY")
    if not key:
        logger.info("Alpha Vantage key missing; skipping.")
        return []
    source_id = await _ensure_data_source("alpha_vantage", "crypto", "https://www.alphavantage.co", "https://www.alphavantage.co/support/#api-key")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                data = await _fetch_json(client, "GET", "https://www.alphavantage.co/query", params={"function": "GLOBAL_QUOTE", "symbol": sym, "apikey": key})
                row = (data or {}).get("Global Quote") or {}
                price = float(row.get("05. price") or 0.0)
                t = PriceTick(source_id=source_id, symbol=sym, market="stock", price=price, ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=row)
                out.append(t)
            except Exception as exc:
                logger.warning("Alpha Vantage error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 11. Twelve Data - Free 800/day (provides crypto and forex data)
async def collect_twelve_data_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect stock quotes from Twelve Data."""
    key = _get_api_key("TWELVE_DATA_API_KEY")
    if not key:
        logger.info("Twelve Data key missing; skipping.")
        return []
    source_id = await _ensure_data_source("twelve_data", "crypto", "https://api.twelvedata.com", "https://twelvedata.com/pricing")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                data = await _fetch_json(client, "GET", "https://api.twelvedata.com/quote", params={"symbol": sym, "apikey": key})
                price = float(data.get("close") or 0.0)
                t = PriceTick(source_id=source_id, symbol=sym, market="stock", price=price, ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=data)
                out.append(t)
            except Exception as exc:
                logger.warning("Twelve Data error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# NOTE: FMP (#12) removed - only provides stocks/commodities, not crypto/forex


# 13. Finnhub - Free 30,000/month (provides crypto and forex data)
async def collect_finnhub_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect stock quotes from Finnhub."""
    key = _get_api_key("FINNHUB_API_KEY")
    if not key:
        logger.info("Finnhub key missing; skipping.")
        return []
    source_id = await _ensure_data_source("finnhub", "crypto", "https://finnhub.io", "https://finnhub.io/docs/api")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                data = await _fetch_json(client, "GET", "https://finnhub.io/api/v1/quote", params={"symbol": sym, "token": key})
                t = PriceTick(source_id=source_id, symbol=sym, market="stock", price=float(data.get("c") or 0.0), ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=data)
                out.append(t)
            except Exception as exc:
                logger.warning("Finnhub error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 14. Polygon.io - Free limited (provides crypto and forex data)
async def collect_polygon_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect stock quotes from Polygon.io."""
    key = _get_api_key("POLYGON_API_KEY")
    if not key:
        logger.info("Polygon key missing; skipping.")
        return []
    source_id = await _ensure_data_source("polygon", "crypto", "https://api.polygon.io", "https://polygon.io/docs")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                # Use the correct Polygon v3 endpoint
                data = await _fetch_json(
                    client, 
                    "GET", 
                    f"https://api.polygon.io/v2/aggs/ticker/{sym}/prev",
                    params={"adjusted": "true", "apikey": key}
                )
                results = (data or {}).get("results", [])
                if results and len(results) > 0:
                    price = float(results[0].get("c") or 0.0)  # close price
                    t = PriceTick(source_id=source_id, symbol=sym, market="stock", price=price, ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=data)
                    out.append(t)
            except Exception as exc:
                logger.warning("Polygon error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# NOTE: EODHD (#15) removed - only provides stocks/commodities, not crypto/forex


# 16. Tiingo - Free limited (provides crypto and forex data)
async def collect_tiingo_quotes(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect stock quotes from Tiingo."""
    key = _get_api_key("TIINGO_API_KEY")
    if not key:
        logger.info("Tiingo key missing; skipping.")
        return []
    source_id = await _ensure_data_source("tiingo", "crypto", "https://api.tiingo.com", "https://api.tiingo.com/documentation/general/overview")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                data = await _fetch_json(client, "GET", f"https://api.tiingo.com/tiingo/daily/{sym}/prices", headers=_headers({"Authorization": f"Token {key}"}))
                if data and len(data) > 0:
                    latest = data[0]
                    price = float(latest.get("close") or 0.0)
                    t = PriceTick(source_id=source_id, symbol=sym, market="stock", price=price, ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=latest)
                    out.append(t)
            except Exception as exc:
                logger.warning("Tiingo error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# ------------------------
# FOREX APIs (17-18)
# ------------------------

# 17. ExchangeRate-API - Free unlimited
async def collect_exchangerate_api(base: str = "USD") -> List[PriceTick]:
    """Collect forex rates from ExchangeRate-API."""
    key = _get_api_key("EXCHANGERATE_API_KEY")
    if not key:
        logger.info("ExchangeRate-API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("exchangerate_api", "forex", "https://v6.exchangerate-api.com", "https://www.exchangerate-api.com/docs/overview")
    async with _client() as client:
        data = await _fetch_json(client, "GET", f"https://v6.exchangerate-api.com/v6/{key}/latest/{base}")
    rates = (data or {}).get("conversion_rates", {}) or {}
    now = _now_naive_utc()
    out: List[PriceTick] = [
        PriceTick(source_id=source_id, symbol=f"{base}{quote}", market="forex", price=float(rate or 0.0), ts=now, received_at=now, extra=None)
        for quote, rate in rates.items()
    ]
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# 18. Open Exchange Rates - Free limited
async def collect_openexchangerates(base: str = "USD") -> List[PriceTick]:
    """Collect forex rates from Open Exchange Rates."""
    key = _get_api_key("OPEN_EXCHANGE_RATES_API_KEY")
    if not key:
        logger.info("Open Exchange Rates key missing; skipping.")
        return []
    source_id = await _ensure_data_source("open_exchange_rates", "forex", "https://openexchangerates.org", "https://docs.openexchangerates.org/")
    async with _client() as client:
        data = await _fetch_json(client, "GET", "https://openexchangerates.org/api/latest.json", params={"app_id": key, "base": base})
    rates = (data or {}).get("rates", {}) or {}
    now = _now_naive_utc()
    out: List[PriceTick] = [
        PriceTick(source_id=source_id, symbol=f"{base}{quote}", market="forex", price=float(rate or 0.0), ts=now, received_at=now, extra=None)
        for quote, rate in rates.items()
    ]
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# ------------------------
# MACRO APIs (19-20)
# ------------------------

# 19. FRED API - Free unlimited
async def collect_fred(series_ids: Sequence[str]) -> List[OnchainMetric]:
    """Collect economic data from FRED."""
    key = _get_api_key("FRED_API_KEY")
    if not key:
        logger.info("FRED API key missing; skipping.")
        return []
    source_id = await _ensure_data_source("fred", "macro", "https://api.stlouisfed.org", "https://fred.stlouisfed.org/docs/api/fred/")
    out: List[OnchainMetric] = []
    async with _client() as client:
        for sid in series_ids or []:
            try:
                data = await _fetch_json(client, "GET", "https://api.stlouisfed.org/fred/series/observations", params={"series_id": sid, "api_key": key, "file_type": "json"})
                obs = ((data or {}).get("observations", []) or [])
                if not obs:
                    continue
                last = obs[-1]
                val = float(last.get("value") or 0.0) if (last.get("value") not in (".", None)) else 0.0
                out.append(
                    OnchainMetric(
                        network="macro",
                        metric_name=f"fred_{sid}",
                        value=val,
                        unit=None,
                        ts=_now_utc(),
                        source_id=source_id,
                        extra={"date": last.get("date")},
                    )
                )
            except Exception as exc:
                logger.warning("FRED error for %s: %s", sid, exc)
    if out:
        async for session in get_session():
            for m in out:
                session.add(m)
            await session.commit()
    return out


# 20. World Bank API - Free unlimited
async def collect_world_bank_data(indicator: str = "NY.GDP.MKTP.CD") -> List[OnchainMetric]:
    """Collect economic indicators from World Bank API."""
    source_id = await _ensure_data_source("world_bank", "macro", "https://api.worldbank.org", "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392")
    out: List[OnchainMetric] = []
    async with _client() as client:
        try:
            data = await _fetch_json(client, "GET", "https://api.worldbank.org/v2/country/USA/indicator/" + indicator, params={"format": "json", "date": "2020"})
            if isinstance(data, list) and len(data) > 1:
                for item in (data[1] or []):
                    try:
                        value = float(item.get("value") or 0.0)
                        out.append(
                            OnchainMetric(
                                network="macro",
                                metric_name=f"wb_{indicator}",
                                value=value,
                                unit="USD",
                                ts=_now_utc(),
                                source_id=source_id,
                                extra={"country": item.get("countryiso3code"), "date": item.get("date")},
                            )
                        )
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning("World Bank API error: %s", exc)
    if out:
        async for session in get_session():
            for m in out:
                session.add(m)
            await session.commit()
    return out


# ------------------------
# COMMODITIES APIs (21)
# ------------------------

# 21. API Ninjas - Free 50,000/month (provides forex data)
async def collect_api_ninjas_commodities(symbols: Sequence[str]) -> List[PriceTick]:
    """Collect commodity prices from API Ninjas."""
    key = _get_api_key("API_NINJAS_KEY")
    if not key:
        logger.info("API Ninjas key missing; skipping.")
        return []
    source_id = await _ensure_data_source("api_ninjas", "forex", "https://api.api-ninjas.com", "https://api-ninjas.com/api/commodities")
    out: List[PriceTick] = []
    async with _client() as client:
        for sym in _coalesce_symbols(symbols):
            try:
                data = await _fetch_json(client, "GET", "https://api.api-ninjas.com/v1/commodityPrice", params={"symbol": sym}, headers=_headers({"X-Api-Key": key}))
                price = float(((data or [{}])[0] or {}).get("price") or 0.0) if isinstance(data, list) else 0.0
                out.append(PriceTick(source_id=source_id, symbol=sym, market="commodity", price=price, ts=_now_naive_utc(), received_at=_now_naive_utc(), extra=None))
            except Exception as exc:
                logger.warning("API Ninjas error for %s: %s", sym, exc)
    if out:
        async for session in get_session():
            for t in out:
                session.add(t)
            await session.commit()
    return out


# ------------------------
# NEWS APIs (22-24)
# ------------------------

# 22. NewsAPI.org - Free 100/day
async def collect_newsapi(query: str = "markets") -> List[NewsItem]:
    """Collect news from NewsAPI.org."""
    key = _get_api_key("NEWSAPI_KEY")
    if not key:
        logger.info("NewsAPI key missing; skipping NewsAPI collector.")
        return []
    source_id = await _ensure_data_source("newsapi_org", "news", "https://newsapi.org", "https://newsapi.org/docs")
    async with _client() as client:
        data = await _fetch_json(client, "GET", "https://newsapi.org/v2/everything", params={"q": query, "pageSize": 50, "language": "en", "apiKey": key})
    articles = (data or {}).get("articles", []) or []
    out: List[NewsItem] = []
    for a in articles:
        try:
            published_at = None
            if a.get("publishedAt"):
                try:
                    pa = datetime.fromisoformat(a.get("publishedAt").replace("Z", "+00:00"))
                    published_at = _to_naive_utc(pa)
                except Exception:
                    published_at = None
            item = NewsItem(
                source_id=source_id,
                title=a.get("title") or "",
                summary=a.get("description") or "",
                url=a.get("url") or "",
                language=a.get("language") or "en",
                published_at=published_at,
                tickers=None,
                categories=None,
                sentiment=None,
                extra={"source": (a.get("source") or {}).get("name")},
                created_at=_now_utc(),
            )
            out.append(item)
        except Exception as exc:
            logger.warning("NewsAPI parse error: %s", exc)
    if out:
        async for session in get_session():
            for n in out:
                session.add(n)
            try:
                await session.commit()
            except IntegrityError as ie:
                await session.rollback()
                logger.debug("Duplicate news item(s) ignored during commit: %s", ie)
    return out


# 23. GNews - Free 100/day
async def collect_gnews(query: str = "markets") -> List[NewsItem]:
    """Collect news from GNews."""
    key = _get_api_key("GNEWS_API_KEY")
    if not key:
        logger.info("GNews API key missing; skipping GNews collector.")
        return []
    source_id = await _ensure_data_source("gnews", "news", "https://gnews.io", "https://gnews.io/docs")
    async with _client() as client:
        data = await _fetch_json(client, "GET", "https://gnews.io/api/v4/search", params={"q": query, "max": 50, "apikey": key})
    articles = (data or {}).get("articles", []) or []
    out: List[NewsItem] = []
    for a in articles:
        try:
            published_at = None
            if a.get("publishedAt"):
                try:
                    pa = datetime.fromisoformat(a.get("publishedAt").replace("Z", "+00:00"))
                    published_at = _to_naive_utc(pa)
                except Exception:
                    published_at = None
            item = NewsItem(
                source_id=source_id,
                title=a.get("title") or "",
                summary=a.get("description") or "",
                url=a.get("url") or "",
                language=a.get("language") or "en",
                published_at=published_at,
                tickers=None,
                categories=None,
                sentiment=None,
                extra={"source": a.get("source", {}).get("name")},
                created_at=_now_utc(),
            )
            out.append(item)
        except Exception as exc:
            logger.warning("GNews parse error: %s", exc)
    if out:
        async for session in get_session():
            for n in out:
                session.add(n)
            try:
                await session.commit()
            except IntegrityError as ie:
                await session.rollback()
                logger.debug("Duplicate news item(s) ignored during commit: %s", ie)
    return out


# 24. Marketaux - Free limited
async def collect_marketaux(query: str = "markets") -> List[NewsItem]:
    """Collect financial news from Marketaux."""
    key = _get_api_key("MARKETAUX_API_KEY")
    if not key:
        logger.info("Marketaux API key missing; skipping Marketaux collector.")
        return []
    source_id = await _ensure_data_source("marketaux", "news", "https://marketaux.com", "https://www.marketaux.com/documentation")
    async with _client() as client:
        data = await _fetch_json(client, "GET", "https://api.marketaux.com/v1/news/all", params={"search": query, "limit": 50, "api_token": key})
    articles = (data or {}).get("data", []) or []
    out: List[NewsItem] = []
    for a in articles:
        try:
            published_at = None
            if a.get("published_at"):
                try:
                    pa = datetime.fromisoformat(a.get("published_at").replace("Z", "+00:00"))
                    published_at = _to_naive_utc(pa)
                except Exception:
                    published_at = None
            item = NewsItem(
                source_id=source_id,
                title=a.get("title") or "",
                summary=a.get("description") or "",
                url=a.get("url") or "",
                language=a.get("language") or "en",
                published_at=published_at,
                tickers=a.get("entities"),
                categories=None,
                sentiment=None,
                extra={"source": a.get("source")},
                created_at=_now_utc(),
            )
            out.append(item)
        except Exception as exc:
            logger.warning("Marketaux parse error: %s", exc)
    if out:
        async for session in get_session():
            for n in out:
                session.add(n)
            try:
                await session.commit()
            except IntegrityError as ie:
                await session.rollback()
                logger.debug("Duplicate news item(s) ignored during commit: %s", ie)
    return out


# ------------------------
# Orchestration helpers
# ------------------------

async def collect_crypto_batch(crypto_symbols: Sequence[str], coingecko_ids: Sequence[str]) -> Dict[str, List[Any]]:
    """Convenience to collect from multiple crypto sources concurrently."""
    results = await asyncio.gather(
        collect_binance_tickers(crypto_symbols),
        collect_coingecko_markets(coingecko_ids),
        collect_cryptocompare_prices(crypto_symbols),
        collect_kraken_tickers(crypto_symbols),
        collect_coinbase_rates(crypto_symbols),
        collect_coinpaprika_tickers(crypto_symbols),
        return_exceptions=True,
    )
    out: Dict[str, List[Any]] = {"binance": [], "coingecko": [], "cryptocompare": [], "kraken": [], "coinbase": [], "coinpaprika": []}
    for name, res in zip(out.keys(), results):
        if isinstance(res, Exception):
            logger.warning(f"Collector {name} failed: {str(res)}")
            out[name] = []
        else:
            out[name] = res
    return out


async def collect_additional_crypto_forex_batch(symbols: Sequence[str]) -> Dict[str, List[Any]]:
    """Collect crypto/forex data from collectors that also support stocks (excluding FMP and EODHD)."""
    # These collectors provide crypto and forex data, not just stocks
    results = await asyncio.gather(
        collect_alpha_vantage_quotes(symbols),
        collect_twelve_data_quotes(symbols),
        collect_finnhub_quotes(symbols),
        collect_polygon_quotes(symbols),
        collect_tiingo_quotes(symbols),
        return_exceptions=True,
    )
    names = ["alpha_vantage", "twelve_data", "finnhub", "polygon", "tiingo"]
    out: Dict[str, List[Any]] = {k: [] for k in names}
    for k, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning(f"Collector {k} failed: {str(res)}")
        else:
            out[k] = res
    return out


async def collect_forex_batch(forex_pairs: Sequence[str]) -> Dict[str, List[Any]]:
    """Convenience to collect from multiple forex sources concurrently."""
    results = await asyncio.gather(
        collect_exchangerate_api("USD"),
        collect_openexchangerates("USD"),
        collect_api_ninjas_commodities(["XAU"]),  # API Ninjas provides forex data
        return_exceptions=True,
    )
    names = ["exchangerate_api", "openexchangerates", "api_ninjas"]
    out: Dict[str, List[Any]] = {k: [] for k in names}
    for k, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning(f"Forex collector {k} failed: {str(res)}")
        else:
            out[k] = res
    return out


async def collect_blockchain_batch() -> Dict[str, List[Any]]:
    """Convenience to collect from blockchain explorers."""
    results = await asyncio.gather(
        collect_etherscan_eth_stats(),
        collect_bscscan_stats(),
        collect_polygonscan_stats(),
        return_exceptions=True,
    )
    names = ["etherscan", "bscscan", "polygonscan"]
    out: Dict[str, List[Any]] = {k: [] for k in names}
    for k, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning(f"Blockchain collector {k} failed: {str(res)}")
        else:
            out[k] = res
    return out


async def collect_news_batch(query: str = "markets") -> Dict[str, List[NewsItem]]:
    """Convenience to collect news from multiple sources."""
    results = await asyncio.gather(
        collect_newsapi(query),
        collect_gnews(query),
        collect_marketaux(query),
        return_exceptions=True,
    )
    names = ["newsapi", "gnews", "marketaux"]
    out: Dict[str, List[NewsItem]] = {k: [] for k in names}
    for k, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning(f"News collector {k} failed: {str(res)}")
        else:
            out[k] = res
    return out


async def collect_macro_batch(fred_series: Sequence[str]) -> Dict[str, List[Any]]:
    """Convenience to collect from macro sources."""
    results = await asyncio.gather(
        collect_fred(fred_series),
        collect_world_bank_data("NY.GDP.MKTP.CD"),
        return_exceptions=True,
    )
    names = ["fred", "world_bank"]
    out: Dict[str, List[Any]] = {k: [] for k in names}
    for k, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning(f"Macro collector {k} failed: {str(res)}")
        else:
            out[k] = res
    return out


# ------------------------
# Periodic runner
# ------------------------

async def run_periodic(interval_seconds: int = 60) -> None:
    """Run a periodic collection loop across configured sources.

    Uses settings.* to determine symbols/ids when available and safe defaults otherwise.
    """
    crypto_symbols: List[str] = list(getattr(settings, "CRYPTO_SYMBOLS", ["BTCUSDT", "ETHUSDT"]))
    coingecko_ids: List[str] = list(getattr(settings, "COINGECKO_IDS", ["bitcoin", "ethereum"]))
    forex_pairs: List[str] = list(getattr(settings, "FOREX_PAIRS", ["EURUSD", "USDJPY"]))
    news_query: str = getattr(settings, "NEWS_QUERY", "markets")
    fred_series: List[str] = list(getattr(settings, "FRED_SERIES", ["DGS10"]))

    while True:
        try:
            # Crypto (APIs 1-9)
            await collect_crypto_batch(crypto_symbols, coingecko_ids)
            await collect_cmc_quotes(crypto_symbols)
            await collect_messari_metrics(["btc", "eth"])

            # Blockchain explorers (APIs 9 cont.)
            await collect_blockchain_batch()

            # Additional crypto/forex collectors (Alpha Vantage, Twelve Data, Finnhub, Polygon, Tiingo)
            # These provide crypto and forex data (FMP and EODHD excluded - they don't provide crypto/forex)
            await collect_additional_crypto_forex_batch(crypto_symbols)

            # Forex (APIs 17-18, plus API Ninjas)
            await collect_forex_batch(forex_pairs)

            # Macro (APIs 19-20)
            await collect_macro_batch(fred_series)

            # News (APIs 22-24)
            await collect_news_batch(news_query)

            logger.info("Periodic data collection cycle completed")

        except Exception as exc:
            logger.exception("Periodic data collection error: %s", exc)

        await asyncio.sleep(max(5, int(interval_seconds)))
