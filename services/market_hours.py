"""
Market Hours Utility
Checks if forex and crypto markets are currently open.
"""

from datetime import datetime, time
import pytz
from typing import Dict, Optional


class MarketHours:
    """
    Utility to check if markets are open.
    Crypto: 24/7 always open
    Forex: Sunday 5pm EST - Friday 5pm EST (closed Saturday)
    """
    
    # Major forex market timezones
    EST = pytz.timezone('America/New_York')
    GMT = pytz.timezone('Europe/London')
    JST = pytz.timezone('Asia/Tokyo')
    AEDT = pytz.timezone('Australia/Sydney')
    
    @staticmethod
    def is_crypto_market_open() -> bool:
        """Crypto markets are open 24/7."""
        return True
    
    @staticmethod
    def is_forex_market_open() -> bool:
        """
        Forex market hours:
        - Opens: Sunday 5:00 PM EST (Friday close continues into Sunday)
        - Closes: Friday 5:00 PM EST
        - Closed: Saturday all day
        """
        now_est = datetime.now(MarketHours.EST)
        current_day = now_est.weekday()  # 0=Monday, 6=Sunday
        current_time = now_est.time()
        
        # Forex is closed on Saturday (day 5)
        if current_day == 5:  # Saturday
            return False
        
        # Forex opens Sunday at 5pm EST
        if current_day == 6:  # Sunday
            if current_time >= time(17, 0):  # 5:00 PM or later
                return True
            else:
                return False  # Before 5pm Sunday = closed
        
        # Monday to Friday: market is open
        # Friday closes at 5pm EST
        if current_day == 4:  # Friday
            if current_time >= time(17, 0):  # After 5pm Friday = closed
                return False
        
        # Monday to Thursday: always open
        return True
    
    @staticmethod
    def get_market_status() -> Dict[str, bool]:
        """Get status of all markets."""
        return {
            "crypto": MarketHours.is_crypto_market_open(),
            "forex": MarketHours.is_forex_market_open(),
        }
    
    @staticmethod
    def get_market_status_message() -> str:
        """Get human-readable market status."""
        crypto_open = MarketHours.is_crypto_market_open()
        forex_open = MarketHours.is_forex_market_open()
        
        status_parts = []
        if crypto_open:
            status_parts.append("🟢 Crypto markets: OPEN (24/7)")
        else:
            status_parts.append("🔴 Crypto markets: CLOSED")
        
        if forex_open:
            status_parts.append("🟢 Forex markets: OPEN")
        else:
            status_parts.append("🔴 Forex markets: CLOSED (Forex closes Friday 5pm EST, reopens Sunday 5pm EST)")
        
        return " | ".join(status_parts)
    
    @staticmethod
    def is_symbol_market_open(symbol: str) -> bool:
        """
        Check if market is open for a specific symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT', 'EURUSD')
        
        Returns:
            True if market is open, False otherwise
        """
        # Crypto symbols typically end with USDT, BTC, ETH, or are common crypto tickers
        crypto_indicators = ['USDT', 'BTC', 'ETH', 'USDC', 'BNB', 'ADA', 'SOL', 'DOT', 'DOGE', 'XRP', 'LINK', 'UNI']
        
        # Check if it's a crypto symbol
        is_crypto = any(symbol.upper().endswith(indicator) for indicator in crypto_indicators) or \
                   symbol.upper() in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'DOGE', 'XRP', 'LINK', 'UNI', 'AVAX', 'MATIC', 'ATOM', 'LTC', 'BCH']
        
        if is_crypto:
            return MarketHours.is_crypto_market_open()
        else:
            # Assume it's forex
            return MarketHours.is_forex_market_open()

