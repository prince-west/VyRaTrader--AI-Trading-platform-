# backend/app/services/brokers/binance_adapter.py
import asyncio
from typing import Dict, Any, Optional
from backend.app.core.config import settings

# Try ccxt.async_support first (recommended)
try:
    import ccxt.async_support as ccxt  # type: ignore
except Exception:
    ccxt = None

# fallback to python-binance if ccxt isn't present
try:
    from binance import AsyncClient as BinanceAsyncClient  # type: ignore
    from binance.exceptions import BinanceAPIException  # type: ignore
except Exception:
    BinanceAsyncClient = None
    BinanceAPIException = None

class BinanceBrokerAdapter:
    """
    Binance live execution adapter. Requires settings.BINANCE_API_KEY and settings.BINANCE_API_SECRET.
    Uses ccxt.async_support if installed (recommended). If not, tries python-binance AsyncClient.
    """

    def __init__(self):
        self.api_key = getattr(settings, "BINANCE_API_KEY", None)
        self.api_secret = getattr(settings, "BINANCE_API_SECRET", None)
        if not (self.api_key and self.api_secret):
            raise RuntimeError("BINANCE_API_KEY / BINANCE_API_SECRET not set in config")

        self._ccxt_exchange = None
        self._python_binance_client = None

    async def _init_ccxt(self):
        if ccxt is None:
            return None
        exchange = ccxt.binance({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,
            # use testnet flag if requested:
            "options": {"defaultType": "spot"}
        })
        self._ccxt_exchange = exchange
        return exchange

    async def _init_python_binance(self):
        if BinanceAsyncClient is None:
            return None
        client = await BinanceAsyncClient.create(self.api_key, self.api_secret, testnet=getattr(settings, "BINANCE_TESTNET", False))
        self._python_binance_client = client
        return client

    async def create_market_order(self, symbol: str, side: str, amount: float, params: Optional[Dict[str,Any]] = None) -> Dict[str,Any]:
        """
        Create market order:
        - symbol: "BTC/USDT" (ccxt format) or "BTCUSDT" (python-binance accepted)
        - side: "buy" or "sell"
        - amount: quantity (not notional)
        Returns a dict with standard fields: id, status, filled, avg_fill_price, raw
        """
        params = params or {}
        # try ccxt
        if ccxt is not None:
            if self._ccxt_exchange is None:
                await self._init_ccxt()
            ex = self._ccxt_exchange
            try:
                # convert symbol if user passed no slash
                ccxt_symbol = symbol if "/" in symbol else f"{symbol[:-4]}/{symbol[-4:]}" if len(symbol) > 6 else symbol
                order = await ex.create_order(ccxt_symbol, "market", side, amount, None, params)
                return {"id": order.get("id"), "status": order.get("status"), "filled": float(order.get("filled",0)), "avg_price": float(order.get("average", 0)), "raw": order}
            except Exception as e:
                raise RuntimeError(f"ccxt order error: {e}")

        # try python-binance
        if BinanceAsyncClient is not None:
            if self._python_binance_client is None:
                await self._init_python_binance()
            client = self._python_binance_client
            try:
                # python-binance expects symbol like BTCUSDT and quantity param as 'quantity'
                sym = symbol.replace("/", "") if "/" in symbol else symbol
                # Note: python-binance client uses create_order sync? AsyncClient has create_order
                resp = await client.create_order(symbol=sym, side=side.upper(), type="MARKET", quantity=amount)
                # resp contains fills and executedQty
                avg_price = None
                fills = resp.get("fills") or []
                if fills:
                    total = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                    qty = sum(float(f["qty"]) for f in fills)
                    if qty:
                        avg_price = total / qty
                return {"id": resp.get("orderId"), "status": resp.get("status"), "filled": float(resp.get("executedQty", 0)), "avg_price": avg_price, "raw": resp}
            except Exception as e:
                raise RuntimeError(f"python-binance order error: {e}")

        raise RuntimeError("No supported Binance client installed. Install ccxt or python-binance.")
