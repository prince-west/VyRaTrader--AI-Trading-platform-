# backend/app/services/trading_engine.py
from typing import List, Dict, Any
from backend.app.services.ai_ensemble import AIEnsemble
from backend.app.services.risk_manager import RiskManager
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session

async def process_trade():
    session: AsyncSession = await get_session()
    async with session.begin():
        # load portfolio
        # create trade record
        # update balances
        # commit happens automatically at end of block
        pass


class TradingEngine:
    def __init__(self, ensemble_weights: Dict[str,float] = None):
        self.ensemble = AIEnsemble(weights=ensemble_weights)
        self.risk_mgr = RiskManager()


    def signal_for(self, symbol: str, prices: List[float], account_balance: float = 0.0, user_risk: str = "Medium", extra: Dict[str,Any] = None) -> Dict[str,Any]:
        """
        Returns final trade decision, with position_size applied and risk params.
        """
        extra = extra or {}
        aggregated = self.ensemble.aggregate(symbol, prices, extra=extra)
        # apply risk sizing
        final = self.risk_mgr.apply(aggregated, account_balance, user_risk)
        return final
