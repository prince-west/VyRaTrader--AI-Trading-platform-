# backend/app/services/broker_adapter.py
from typing import Dict, Any, Optional
import asyncio
from backend.app.core.config import settings

class BrokerAdapter:
    def __init__(self):
        self._binance_adapter = None

    def _get_binance_adapter(self):
        """Lazy load Binance adapter only when needed"""
        if self._binance_adapter is None:
            try:
                from backend.app.services.brokers.binance_adapter import BinanceBrokerAdapter
                self._binance_adapter = BinanceBrokerAdapter()
            except Exception as e:
                print(f"Could not load Binance adapter: {e}")
                self._binance_adapter = False  # Mark as failed
        return self._binance_adapter

    async def execute(self, decision: Dict[str,Any], mode: str = "paper", session=None, user_id: Optional[str]=None, symbol: Optional[str]=None) -> Dict[str,Any]:
        """
        Execute trade:
        - paper: simulated immediate fill (handled by trade_executor)
        - live: call broker SDK / REST to submit order
        """
        if mode == "paper":
            return {"status":"simulated", "filled": True}
        
        # Live mode - try to use Binance
        binance_adapter = self._get_binance_adapter()
        if binance_adapter and binance_adapter is not False:
            try:
                signal = decision.get("signal", "buy")
                position_size = decision.get("position_size", 0.0)
                
                if not symbol:
                    return {"status":"error", "message": "Symbol required for live trading"}
                
                order_result = await binance_adapter.create_market_order(symbol, signal, position_size)
                return {"status":"filled", "broker_order_id": order_result.get("id"), "avg_price": order_result.get("avg_price"), "filled": order_result.get("filled")}
            except Exception as e:
                return {"status":"error", "message": f"Binance execution failed: {str(e)}"}
        
        # Fallback: simulated
        await asyncio.sleep(0.2)
        return {"status":"submitted", "broker_order_id":"sim-123456"}
