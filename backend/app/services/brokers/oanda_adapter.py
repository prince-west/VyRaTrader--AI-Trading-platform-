# backend/app/services/brokers/oanda_adapter.py
import httpx
from typing import Dict, Any
from backend.app.core.config import settings

class OandaAdapter:
    def __init__(self):
        self.token = getattr(settings, "OANDA_API_TOKEN", None)
        self.account_id = getattr(settings, "OANDA_ACCOUNT_ID", None)
        self.base = getattr(settings, "OANDA_API_BASE", "https://api-fxpractice.oanda.com")
        if not (self.token and self.account_id):
            raise RuntimeError("OANDA_API_TOKEN or OANDA_ACCOUNT_ID not set in config")

    async def create_market_order(self, instrument: str, units: int) -> Dict[str,Any]:
        """
        creates a market order.
        instrument example: "EUR_USD"
        units: positive for buy (long), negative for sell (short)
        """
        url = f"{self.base}/v3/accounts/{self.account_id}/orders"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        body = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units)
            }
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            return r.json()
