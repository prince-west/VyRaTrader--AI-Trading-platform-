"""
API Request Manager with Rate Limiting, Caching, and Smart Resource Allocation.
Manages API requests to prevent exceeding limits and intelligently caches responses.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from sqlmodel import select
from backend.app.core.logger import logger
from backend.app.db.session import get_session
from backend.app.db.models import PriceTick, NewsItem, OnchainMetric


class APICategory(str, Enum):
    """API categories for rate limiting"""
    CRYPTO = "crypto"
    FOREX = "forex"
    NEWS = "news"
    MACRO = "macro"
    ONCHAIN = "onchain"


@dataclass
class APIQuota:
    """Tracks API quota and usage"""
    daily_limit: int
    requests_today: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    minute_limit: Optional[int] = None
    requests_this_minute: int = 0
    minute_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def reset_if_needed(self):
        """Reset counters if a new day has started"""
        now = datetime.now(timezone.utc)
        if (now - self.last_reset).days >= 1:
            self.requests_today = 0
            self.last_reset = now
            logger.info(f"API quota reset for daily limit: {self.daily_limit}")
        
        # Reset minute counter if needed
        if self.minute_limit:
            if (now - self.minute_window_start).seconds >= 60:
                self.requests_this_minute = 0
                self.minute_window_start = now
    
    def is_available(self) -> bool:
        """Check if API can still be used"""
        self.reset_if_needed()
        
        if self.requests_today >= self.daily_limit:
            return False
        
        if self.minute_limit and self.requests_this_minute >= self.minute_limit:
            return False
        
        return True
    
    def record_request(self):
        """Record an API request"""
        self.requests_today += 1
        if self.minute_limit:
            self.requests_this_minute += 1
        logger.debug(f"API request recorded. Daily: {self.requests_today}/{self.daily_limit}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current quota status"""
        self.reset_if_needed()
        remaining_today = max(0, self.daily_limit - self.requests_today)
        return {
            "requests_today": self.requests_today,
            "daily_limit": self.daily_limit,
            "remaining_today": remaining_today,
            "utilization": self.requests_today / self.daily_limit if self.daily_limit > 0 else 0,
        }


# API Quotas - Based on free tiers from data_collector.py
API_QUOTAS: Dict[str, APIQuota] = {
    # Crypto APIs
    "coingecko": APIQuota(daily_limit=float('inf'), minute_limit=10),  # ~600/hour max
    "binance": APIQuota(daily_limit=float('inf')),
    "coinmarketcap": APIQuota(daily_limit=333, minute_limit=10),  # 10k/month
    "kraken": APIQuota(daily_limit=float('inf')),
    "messari": APIQuota(daily_limit=1000),
    "cryptocompare": APIQuota(daily_limit=3333, minute_limit=10),  # 100k/month
    "coinbase": APIQuota(daily_limit=float('inf')),
    "coinpaprika": APIQuota(daily_limit=667, minute_limit=20),  # 20k/month
    "etherscan": APIQuota(daily_limit=43200, minute_limit=5),  # 5 req/sec
    "bscscan": APIQuota(daily_limit=43200, minute_limit=5),
    "polygonscan": APIQuota(daily_limit=43200, minute_limit=5),
    
    # Additional crypto/forex APIs (FMP and EODHD removed - they don't provide crypto/forex)
    "alpha_vantage": APIQuota(daily_limit=25),
    "twelve_data": APIQuota(daily_limit=800),
    "finnhub": APIQuota(daily_limit=1000, minute_limit=10),  # 30k/month
    "polygon": APIQuota(daily_limit=720),  # 5 calls/min
    "tiingo": APIQuota(daily_limit=1667, minute_limit=10),  # 50k/month
    
    # Forex APIs
    "exchangerate_api": APIQuota(daily_limit=50),  # 1.5k/month
    "open_exchange_rates": APIQuota(daily_limit=33),  # 1k/month
    
    # Macro APIs
    "fred": APIQuota(daily_limit=float('inf')),
    "world_bank": APIQuota(daily_limit=float('inf')),
    
    # Forex (API Ninjas provides forex data)
    "api_ninjas": APIQuota(daily_limit=1667, minute_limit=10),  # 50k/month
    
    # News APIs
    "newsapi": APIQuota(daily_limit=100),
    "gnews": APIQuota(daily_limit=100),
    "marketaux": APIQuota(daily_limit=200),
}


class APIRequestManager:
    """Manages API requests with rate limiting, caching, and smart allocation"""
    
    def __init__(self):
        self.quotas: Dict[str, APIQuota] = {k: APIQuota(**vars(v)) for k, v in API_QUOTAS.items()}
        self.cache: Dict[str, Dict[str, Any]] = {}  # api_name -> {cache_key: {data, expires}}
        self.market_priorities: Dict[str, List[str]] = {
            "crypto": ["coingecko", "binance", "cryptocompare"],
            "stock": ["finnhub", "twelve_data", "alpha_vantage"],
            "forex": ["exchangerate_api", "open_exchange_rates"],
            "news": ["newsapi", "gnews"],
        }
    
    def check_quota(self, api_name: str) -> Dict[str, Any]:
        """Check if API is available and return status"""
        if api_name not in self.quotas:
            return {"available": False, "reason": "API not configured"}
        
        quota = self.quotas[api_name]
        available = quota.is_available()
        
        status = quota.get_status()
        status["available"] = available
        
        if not available:
            status["reason"] = "Daily limit exceeded" if quota.requests_today >= quota.daily_limit else "Minute limit exceeded"
            reset_time = quota.last_reset + timedelta(days=1)
            status["reset_at"] = reset_time.isoformat()
        
        return status
    
    def record_request(self, api_name: str):
        """Record an API request"""
        if api_name in self.quotas:
            self.quotas[api_name].record_request()
    
    async def get_cached_data(
        self, 
        api_name: str, 
        cache_key: str, 
        max_age_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """Get cached data if available and fresh"""
        if api_name not in self.cache:
            return None
        
        if cache_key not in self.cache[api_name]:
            return None
        
        cached = self.cache[api_name][cache_key]
        age = datetime.now(timezone.utc) - cached["expires"]
        
        if age.total_seconds() > (max_age_minutes * 60):
            del self.cache[api_name][cache_key]
            return None
        
        logger.debug(f"Cache hit for {api_name}:{cache_key}")
        return cached["data"]
    
    async def cache_data(
        self, 
        api_name: str, 
        cache_key: str, 
        data: Dict[str, Any], 
        ttl_minutes: int = 60
    ):
        """Cache data with TTL"""
        if api_name not in self.cache:
            self.cache[api_name] = {}
        
        self.cache[api_name][cache_key] = {
            "data": data,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.debug(f"Cached data for {api_name}:{cache_key} (TTL: {ttl_minutes}m)")
    
    async def get_available_apis(self, market_type: str) -> List[Dict[str, Any]]:
        """Get list of available APIs for a market type, ordered by priority"""
        apis = self.market_priorities.get(market_type, [])
        available = []
        
        for api_name in apis:
            status = self.check_quota(api_name)
            if status["available"]:
                available.append({
                    "api": api_name,
                    "status": status,
                    "priority": apis.index(api_name),
                })
        
        return sorted(available, key=lambda x: x["priority"])
    
    async def smart_fetch_with_fallback(
        self,
        market_type: str,
        symbol: Optional[str] = None,
        data_requirements: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Smart fetch with API availability checks and fallbacks.
        Returns data or suggests alternatives if unavailable.
        """
        available_apis = await self.get_available_apis(market_type)
        
        if not available_apis:
            # No APIs available - suggest alternatives or wait
            suggestions = self._get_alternative_markets(market_type)
            return {
                "status": "unavailable",
                "message": f"No {market_type} data available. Rate limits reached for today.",
                "suggestions": suggestions,
                "retry_after": "24 hours",
            }
        
        # Try to fetch from database first
        cached_db_data = await self._fetch_from_db(market_type, symbol)
        if cached_db_data:
            # Check if data is fresh (less than 5 minutes old)
            latest_tick = cached_db_data.get("latest_tick")
            if latest_tick:
                age = datetime.now(timezone.utc) - latest_tick
                if age.total_seconds() < 300:  # 5 minutes
                    return {
                        "status": "success",
                        "data": cached_db_data,
                        "source": "database",
                        "age_seconds": age.total_seconds(),
                    }
        
        # Use best available API
        best_api = available_apis[0]
        return {
            "status": "ready",
            "recommended_api": best_api["api"],
            "quota_status": best_api["status"],
            "alternatives": available_apis[1:] if len(available_apis) > 1 else [],
        }
    
    def _get_alternative_markets(self, market_type: str) -> List[Dict[str, str]]:
        """Suggest alternative markets when primary market is unavailable"""
        alternatives_map = {
            "crypto": [{"market": "forex", "reason": "Currency pairs available with live data"}],
            "stock": [{"market": "crypto", "reason": "Crypto markets are open 24/7"}],
            "forex": [{"market": "crypto", "reason": "Crypto markets available 24/7"}],
        }
        return alternatives_map.get(market_type, [])
    
    async def _fetch_from_db(self, market_type: str, symbol: Optional[str]) -> Optional[Dict[str, Any]]:
        """Fetch recent data from database"""
        try:
            async for session in get_session():
                # Find latest price tick for symbol
                if symbol:
                    stmt = select(PriceTick).where(
                        PriceTick.symbol == symbol,
                        PriceTick.market == market_type
                    ).order_by(PriceTick.ts.desc())
                    result = await session.exec(stmt)
                    tick = result.first()
                    
                    if tick:
                        return {
                            "latest_tick": tick.ts,
                            "price": tick.price,
                            "symbol": tick.symbol,
                            "market": tick.market,
                        }
        except Exception as e:
            logger.error(f"Error fetching from DB: {e}")
        
        return None


# Global instance
api_manager = APIRequestManager()


async def get_api_status_all() -> Dict[str, Dict[str, Any]]:
    """Get status of all APIs"""
    status = {}
    for api_name, quota in api_manager.quotas.items():
        status[api_name] = quota.get_status()
        status[api_name]["available"] = quota.is_available()
    
    return status


async def get_prince_smart_recommendation(
    requested_market: str,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prince AI's smart recommendation system.
    Checks API availability and suggests best actions.
    """
    result = await api_manager.smart_fetch_with_fallback(requested_market, symbol)
    
    if result["status"] == "unavailable":
        message = f"""Prince AI here. I'm temporarily unable to fetch {requested_market.upper()} data due to API rate limits. 
        
I recommend:
1. Wait until tomorrow for updated data
2. Consider these alternative markets: {', '.join([s['market'] for s in result['suggestions']])}
3. Use existing portfolio positions

Would you like me to analyze your current positions instead?"""
        
        return {
            "recommendation": message,
            "unavailable": True,
            "alternatives": result["suggestions"],
            "user_should_wait": True,
        }
    
    elif result["status"] == "ready":
        api_name = result["recommended_api"]
        quota = result["quota_status"]
        
        message = f"""Prince AI here. I can fetch {requested_market.upper()} data using {api_name}.
        
Available requests today: {quota.get('remaining_today', 0)}/{quota.get('daily_limit', '∞')}
Confidence: {'High' if quota.get('remaining_today', 0) > 50 else 'Medium' if quota.get('remaining_today', 0) > 10 else 'Low'}

Would you like me to proceed with the analysis?"""
        
        return {
            "recommendation": message,
            "available": True,
            "api": api_name,
            "quota": quota,
            "alternatives": result.get("alternatives", []),
        }
    
    else:  # success from cache
        data = result["data"]
        age = int(result["age_seconds"])
        
        message = f"""Prince AI here. I found recent {requested_market.upper()} data (from {age//60} minutes ago).
        
{data.get('symbol', '')}: ${data.get('price', 'N/A')}

This data is fresh and I'm using cached information to save API requests. Proceed with analysis?"""
        
        return {
            "recommendation": message,
            "available": True,
            "from_cache": True,
            "data_age_seconds": age,
            "data": data,
        }

