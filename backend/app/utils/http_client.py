"""
Robust HTTP client utilities for VyRaTrader data collectors.
- Provides retry logic, rate limiting, and error handling
- Supports both sync and async operations
- Graceful degradation when APIs are unavailable
"""

import asyncio
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import httpx
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.logger import logger


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class RateLimitError(HTTPClientError):
    """Raised when rate limit is exceeded."""
    pass


class TransientHTTPError(HTTPClientError):
    """Raised on 5xx or 429 responses to trigger retry."""
    pass


class HTTPClient:
    """Robust HTTP client with retry logic and rate limiting."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self.default_headers = headers or {
            "User-Agent": "VyRaTrader/1.0 (+https://vyratrader.com)",
            "Accept": "application/json",
        }
        self._last_request_time = 0.0
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    @retry(
        retry=retry_if_exception_type(TransientHTTPError),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        stop=stop_after_attempt(3),
        after=after_log(logger, "WARNING"),
    )
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make a GET request with retry logic."""
        self._rate_limit()
        
        full_url = urljoin(self.base_url or "", url) if self.base_url else url
        request_headers = {**self.default_headers, **(headers or {})}
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    full_url,
                    params=params,
                    headers=request_headers,
                    **kwargs
                )
                
                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {full_url}")
                elif response.status_code in (500, 502, 503, 504):
                    raise TransientHTTPError(f"{response.status_code} for {full_url}")
                
                response.raise_for_status()
                return response
                
        except httpx.RequestError as e:
            logger.error(f"Request error for {full_url}: {e}")
            raise HTTPClientError(f"Request failed: {e}")
    
    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make a POST request with retry logic."""
        self._rate_limit()
        
        full_url = urljoin(self.base_url or "", url) if self.base_url else url
        request_headers = {**self.default_headers, **(headers or {})}
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    full_url,
                    data=data,
                    json=json,
                    params=params,
                    headers=request_headers,
                    **kwargs
                )
                
                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {full_url}")
                elif response.status_code in (500, 502, 503, 504):
                    raise TransientHTTPError(f"{response.status_code} for {full_url}")
                
                response.raise_for_status()
                return response
                
        except httpx.RequestError as e:
            logger.error(f"Request error for {full_url}: {e}")
            raise HTTPClientError(f"Request failed: {e}")


class AsyncHTTPClient:
    """Async HTTP client with retry logic and rate limiting."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self.default_headers = headers or {
            "User-Agent": "VyRaTrader/1.0 (+https://vyratrader.com)",
            "Accept": "application/json",
        }
        self._last_request_time = 0.0
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        self._last_request_time = time.time()
    
    @retry(
        retry=retry_if_exception_type(TransientHTTPError),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        stop=stop_after_attempt(3),
        after=after_log(logger, "WARNING"),
    )
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an async GET request with retry logic."""
        await self._rate_limit()
        
        full_url = urljoin(self.base_url or "", url) if self.base_url else url
        request_headers = {**self.default_headers, **(headers or {})}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    full_url,
                    params=params,
                    headers=request_headers,
                    **kwargs
                )
                
                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {full_url}")
                elif response.status_code in (500, 502, 503, 504):
                    raise TransientHTTPError(f"{response.status_code} for {full_url}")
                
                response.raise_for_status()
                return response
                
        except httpx.RequestError as e:
            logger.error(f"Request error for {full_url}: {e}")
            raise HTTPClientError(f"Request failed: {e}")
    
    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an async POST request with retry logic."""
        await self._rate_limit()
        
        full_url = urljoin(self.base_url or "", url) if self.base_url else url
        request_headers = {**self.default_headers, **(headers or {})}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    full_url,
                    data=data,
                    json=json,
                    params=params,
                    headers=request_headers,
                    **kwargs
                )
                
                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {full_url}")
                elif response.status_code in (500, 502, 503, 504):
                    raise TransientHTTPError(f"{response.status_code} for {full_url}")
                
                response.raise_for_status()
                return response
                
        except httpx.RequestError as e:
            logger.error(f"Request error for {full_url}: {e}")
            raise HTTPClientError(f"Request failed: {e}")


def create_client(
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    async_client: bool = False,
    **kwargs
) -> Union[HTTPClient, AsyncHTTPClient]:
    """Factory function to create HTTP clients."""
    if async_client:
        return AsyncHTTPClient(base_url=base_url, timeout=timeout, **kwargs)
    else:
        return HTTPClient(base_url=base_url, timeout=timeout, **kwargs)


def safe_json_response(response: httpx.Response) -> Dict[str, Any]:
    """Safely extract JSON from response, returning empty dict on error."""
    try:
        return response.json()
    except Exception as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        return {}


def safe_text_response(response: httpx.Response) -> str:
    """Safely extract text from response, returning empty string on error."""
    try:
        return response.text
    except Exception as e:
        logger.warning(f"Failed to parse text response: {e}")
        return ""
