# backend/app/services/trade_executor.py
from typing import Dict, Any, Optional
import datetime, random
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from backend.app.db.models import Trade, Account, AILog
from backend.app.services.broker_adapter import BrokerAdapter

broker = BrokerAdapter()

class TradeExecutor:
    def __init__(self):
        self.broker = broker

    async def execute(self, user_id: str, symbol: str, decision: Dict[str,Any], mode: str = "paper", session: Optional[AsyncSession] = None) -> Dict[str,Any]:
        """
        decision: {'signal','position_size', ...}
        mode: 'paper' or 'live'
        """
        position_size = decision.get("position_size", 0.0)
        signal = decision.get("signal", "hold")

        # Fetch account
        acct = None
        if session:
            q = await session.exec(select(Account).where(Account.user_id == user_id))
            acct = q.first()
        # Paper simulation
        if mode == "paper":
            entry_price = 100.0 * (1 + (random.random()-0.5)/100.0)
            move = 0.005 if signal == "buy" else -0.005
            exit_price = entry_price * (1 + move)
            pnl = (exit_price - entry_price) * position_size if signal == "buy" else (entry_price - exit_price) * position_size
            # record trade
            t = Trade(user_id=user_id, strategy=decision.get("strategy","ensemble"), symbol=symbol, side=signal, size=position_size, price=entry_price, profit_loss=pnl, status="closed", opened_at=datetime.datetime.utcnow(), closed_at=datetime.datetime.utcnow())
            if session:
                session.add(t)
                if acct:
                    acct.available_balance = (acct.available_balance or 0.0) + pnl
                    acct.ledger_balance = (acct.ledger_balance or 0.0) + pnl
                    session.add(acct)
                # log AI explanation
                ai_log = AILog(user_id=user_id, prompt=f"Execute {symbol} {signal}", response={"decision": decision, "entry": entry_price, "exit": exit_price, "pnl": pnl})
                session.add(ai_log)
                await session.commit()
                await session.refresh(t)
            return {"ok": True, "mode":"paper", "entry": entry_price, "exit": exit_price, "pnl": pnl, "trade_id": getattr(t, "id", None)}
        # Live execution via broker adapter
        resp = await self.broker.execute(decision, mode=mode, session=session, user_id=user_id, symbol=symbol)
        # record pending trade
        t = Trade(user_id=user_id, strategy=decision.get("strategy","ensemble"), symbol=symbol, side=signal, size=position_size, price=None, profit_loss=None, status=resp.get("status","submitted"), opened_at=datetime.datetime.utcnow())
        if session:
            session.add(t)
            ai_log = AILog(user_id=user_id, prompt=f"Execute live {symbol} {signal}", response={"decision": decision, "broker_resp": resp})
            session.add(ai_log)
            await session.commit()
            await session.refresh(t)
        return {"ok": True, "mode":"live", "broker": resp, "trade_id": getattr(t, "id", None)}


async def get_broker_status():
    """
    Return a simple status dict.
    In production, connect to real broker API (Alpaca, Binance, etc.).
    """
    return {"status": "ok", "broker": "mock"}
