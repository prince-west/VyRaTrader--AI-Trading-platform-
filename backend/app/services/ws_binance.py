"""
Optional WebSocket connector for Binance real-time data.
- Connects to Binance WebSocket trades stream for configured symbols
- Writes trade messages to ephemeral in-memory buffer
- Periodically flushes top-of-book snapshots into orderbook_snapshots
- Reconnects with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Deque

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import OrderbookSnapshot, DataSource
from backend.app.db.session import get_session
from sqlmodel import select


class BinanceWebSocketCollector:
    """WebSocket collector for Binance real-time trade data."""
    
    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        buffer_size: int = 1000,
        flush_interval: int = 30,  # seconds
        max_reconnect_attempts: int = 10,
        base_reconnect_delay: float = 1.0
    ):
        self.symbols = symbols or getattr(settings, "CRYPTO_SYMBOLS", ["BTCUSDT", "ETHUSDT"])
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.base_reconnect_delay = base_reconnect_delay
        
        # In-memory buffers
        self.trade_buffers: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=buffer_size))
        self.orderbook_snapshots: Dict[str, Dict[str, Any]] = {}
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_flush_time = time.time()
        
        # Binance WebSocket URLs
        self.base_url = "wss://stream.binance.com:9443/ws/"
        self.stream_url = "wss://stream.binance.com:9443/stream"
    
    async def get_data_source_id(self) -> Optional[str]:
        """Get or create Binance data source ID."""
        async for session in get_session():
            # Check if Binance data source exists
            stmt = select(DataSource).where(DataSource.name == "binance")
            result = await session.exec(stmt)
            existing = result.first()
            
            if existing:
                return existing.id
            
            # Create new data source
            data_source = DataSource(
                name="binance",
                category="crypto",
                base_url="https://api.binance.com",
                docs_url="https://binance-docs.github.io/apidocs/",
                auth_type="none",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            session.add(data_source)
            await session.commit()
            await session.refresh(data_source)
            return data_source.id
    
    def build_stream_url(self) -> str:
        """Build WebSocket stream URL for multiple symbols."""
        # Convert symbols to lowercase for Binance streams
        stream_names = [f"{symbol.lower()}@trade" for symbol in self.symbols]
        streams = "/".join(stream_names)
        return f"{self.stream_url}?streams={streams}"
    
    async def connect(self) -> bool:
        """Connect to Binance WebSocket stream."""
        try:
            url = self.build_stream_url()
            logger.info(f"Connecting to Binance WebSocket: {url}")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.reconnect_attempts = 0
            logger.info("Connected to Binance WebSocket successfully")
            return True
            
        except Exception as exc:
            logger.error(f"Failed to connect to Binance WebSocket: {exc}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Disconnected from Binance WebSocket")
            except Exception as exc:
                logger.error(f"Error disconnecting from WebSocket: {exc}")
            finally:
                self.websocket = None
    
    def parse_trade_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse trade message from Binance WebSocket."""
        try:
            stream = message.get("stream", "")
            data = message.get("data", {})
            
            if not stream.endswith("@trade") or not data:
                return None
            
            # Extract symbol from stream name
            symbol = stream.replace("@trade", "").upper()
            
            return {
                "symbol": symbol,
                "price": float(data.get("p", 0.0)),
                "quantity": float(data.get("q", 0.0)),
                "timestamp": int(data.get("T", 0)),
                "trade_id": data.get("t", 0),
                "is_buyer_maker": data.get("m", False),
                "raw_data": data
            }
            
        except Exception as exc:
            logger.error(f"Error parsing trade message: {exc}")
            return None
    
    async def process_trade_message(self, trade_data: Dict[str, Any]):
        """Process and buffer trade message."""
        symbol = trade_data["symbol"]
        
        # Add to trade buffer
        self.trade_buffers[symbol].append(trade_data)
        
        # Update orderbook snapshot (simplified - using last trade as reference)
        self.orderbook_snapshots[symbol] = {
            "symbol": symbol,
            "last_price": trade_data["price"],
            "last_quantity": trade_data["quantity"],
            "timestamp": trade_data["timestamp"],
            "trade_count": len(self.trade_buffers[symbol]),
            "is_buyer_maker": trade_data["is_buyer_maker"]
        }
    
    async def flush_orderbook_snapshots(self):
        """Flush orderbook snapshots to database."""
        if not self.orderbook_snapshots:
            return
        
        try:
            source_id = await self.get_data_source_id()
            if not source_id:
                logger.error("Could not get Binance data source ID")
                return
            
            async for session in get_session():
                for symbol, snapshot in self.orderbook_snapshots.items():
                    # Create simplified orderbook snapshot
                    # In a real implementation, you'd aggregate multiple trades
                    # to create proper bid/ask levels
                    
                    # For now, create a minimal snapshot
                    orderbook = OrderbookSnapshot(
                        source_id=source_id,
                        symbol=symbol,
                        market="crypto",
                        bids=[],  # Would be populated with actual bid levels
                        asks=[],  # Would be populated with actual ask levels
                        depth=0,
                        ts=datetime.fromtimestamp(snapshot["timestamp"] / 1000, tz=timezone.utc),
                        received_at=datetime.now(timezone.utc),
                        extra={
                            "last_price": snapshot["last_price"],
                            "last_quantity": snapshot["last_quantity"],
                            "trade_count": snapshot["trade_count"],
                            "is_buyer_maker": snapshot["is_buyer_maker"]
                        }
                    )
                    
                    session.add(orderbook)
                
                await session.commit()
                logger.info(f"Flushed {len(self.orderbook_snapshots)} orderbook snapshots")
                
                # Clear snapshots after flushing
                self.orderbook_snapshots.clear()
                
        except Exception as exc:
            logger.exception(f"Error flushing orderbook snapshots: {exc}")
    
    async def handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Binance sends different message types
            if "stream" in data and "data" in data:
                # Stream data message
                trade_data = self.parse_trade_message(data)
                if trade_data:
                    await self.process_trade_message(trade_data)
            else:
                # Other message types (subscription confirmations, etc.)
                logger.debug(f"Received non-trade message: {data}")
                
        except json.JSONDecodeError as exc:
            logger.error(f"Error parsing WebSocket message: {exc}")
        except Exception as exc:
            logger.exception(f"Error handling WebSocket message: {exc}")
    
    async def message_loop(self):
        """Main message processing loop."""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
                
                # Check if it's time to flush snapshots
                current_time = time.time()
                if current_time - self.last_flush_time >= self.flush_interval:
                    await self.flush_orderbook_snapshots()
                    self.last_flush_time = current_time
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            raise
        except WebSocketException as exc:
            logger.error(f"WebSocket error: {exc}")
            raise
        except Exception as exc:
            logger.exception(f"Unexpected error in message loop: {exc}")
            raise
    
    async def reconnect_with_backoff(self) -> bool:
        """Reconnect with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            return False
        
        # Calculate backoff delay
        delay = self.base_reconnect_delay * (2 ** self.reconnect_attempts)
        delay = min(delay, 60.0)  # Cap at 60 seconds
        
        logger.info(f"Reconnecting in {delay:.1f} seconds (attempt {self.reconnect_attempts + 1})")
        await asyncio.sleep(delay)
        
        self.reconnect_attempts += 1
        return await self.connect()
    
    async def run(self):
        """Main run loop with reconnection logic."""
        self.is_running = True
        logger.info(f"Starting Binance WebSocket collector for symbols: {self.symbols}")
        
        while self.is_running:
            try:
                # Connect to WebSocket
                if not await self.connect():
                    if not await self.reconnect_with_backoff():
                        break
                    continue
                
                # Process messages
                await self.message_loop()
                
            except (ConnectionClosed, WebSocketException):
                logger.warning("WebSocket connection lost, attempting to reconnect...")
                if not await self.reconnect_with_backoff():
                    break
            except Exception as exc:
                logger.exception(f"Unexpected error in WebSocket collector: {exc}")
                if not await self.reconnect_with_backoff():
                    break
        
        logger.info("Binance WebSocket collector stopped")
        self.is_running = False
    
    async def stop(self):
        """Stop the WebSocket collector."""
        logger.info("Stopping Binance WebSocket collector...")
        self.is_running = False
        await self.disconnect()
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about current buffers."""
        return {
            "symbols": list(self.trade_buffers.keys()),
            "buffer_sizes": {symbol: len(buffer) for symbol, buffer in self.trade_buffers.items()},
            "orderbook_snapshots": len(self.orderbook_snapshots),
            "is_running": self.is_running,
            "reconnect_attempts": self.reconnect_attempts
        }


# Global collector instance
_collector: Optional[BinanceWebSocketCollector] = None


def get_binance_collector(symbols: Optional[List[str]] = None) -> BinanceWebSocketCollector:
    """Get or create the global Binance WebSocket collector."""
    global _collector
    if _collector is None:
        _collector = BinanceWebSocketCollector(symbols)
    return _collector


async def start_binance_collector(symbols: Optional[List[str]] = None) -> BinanceWebSocketCollector:
    """Start the Binance WebSocket collector."""
    collector = get_binance_collector(symbols)
    if not collector.is_running:
        # Start collector in background task
        asyncio.create_task(collector.run())
    return collector


async def stop_binance_collector():
    """Stop the Binance WebSocket collector."""
    global _collector
    if _collector and _collector.is_running:
        await _collector.stop()


def get_collector_stats() -> Dict[str, Any]:
    """Get statistics from the Binance collector."""
    global _collector
    if _collector:
        return _collector.get_buffer_stats()
    return {"status": "not_initialized"}


# Convenience functions for external use
async def run_binance_websocket(symbols: Optional[List[str]] = None):
    """Run Binance WebSocket collector."""
    collector = BinanceWebSocketCollector(symbols)
    await collector.run()


async def start_binance_websocket_background(symbols: Optional[List[str]] = None):
    """Start Binance WebSocket collector in background."""
    return await start_binance_collector(symbols)
