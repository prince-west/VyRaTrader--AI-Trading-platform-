# backend/app/api/v1/trades.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from backend.app.db.session import get_session
from backend.app.db.models import User, Trade
from backend.app.services.trading_engine import TradingEngine
from backend.app.services.trade_executor import TradeExecutor
from backend.app.core.security import get_current_user

router = APIRouter(tags=["trades"])

engine = TradingEngine()
executor = TradeExecutor()


class SimulateRequest(BaseModel):
    user_id: str
    symbol: str
    prices: Optional[List[float]] = None
    risk_level: Optional[str] = "Medium"


class ExecuteRequest(BaseModel):
    user_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    market: str
    prices: Optional[List[float]] = None
    risk_level: Optional[str] = "Medium"
    mode: Optional[str] = "paper"  # 'paper' or 'live'


@router.post("/simulate")
async def simulate(req: SimulateRequest, session: AsyncSession = Depends(get_session)):
    # Get account balance for sizing (best-effort)
    user_q = await session.exec(select(User).where(User.id == req.user_id))
    user = user_q.first()
    account_balance = 0.0
    if user:
        # try to get account balance if Account model exists (best-effort)
        from backend.app.db.models import Account
        acct_q = await session.exec(select(Account).where(Account.user_id == user.id))
        acct = acct_q.first()
        if acct:
            account_balance = float(acct.available_balance or 0.0)
    prices = req.prices or []
    decision = engine.signal_for(req.symbol, prices, account_balance=account_balance, user_risk=req.risk_level)
    return {"decision": decision}


@router.get("/recent")
async def recent_trades(
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Get recent trades from database  
    from sqlalchemy import desc as desc_func
    trades_q = await session.exec(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(desc_func(Trade.opened_at))
        .limit(limit)
    )
    trades = trades_q.all()
    
    positions = [
        {
            "id": str(t.id),
            "symbol": t.symbol,
            "side": t.side,
            "price": t.entry_price,
            "quantity": t.quantity,
            "profit_loss": t.profit_loss or 0.0,
            "timestamp": t.opened_at.isoformat() if t.opened_at else "",
        }
        for t in trades
    ]
    
    return {"positions": positions}

@router.post("/execute")
async def execute(req: ExecuteRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    # Verify the authenticated user matches user_id or allow admins
    if current_user.id != req.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to execute trades for this user")

    # Validate side
    if req.side not in ['buy', 'sell']:
        raise HTTPException(status_code=400, detail="Invalid side. Must be 'buy' or 'sell'")
    
    # Validate size
    if req.size <= 0:
        raise HTTPException(status_code=400, detail="Trade size must be greater than 0")
    
    # Get account balance
    from backend.app.db.models import Account
    acct_q = await session.exec(select(Account).where(Account.user_id == req.user_id))
    acct = acct_q.first()
    
    # Create account if it doesn't exist
    if not acct:
        acct = Account(
            user_id=req.user_id,
            available_balance=10000.0,  # Demo starting balance
            ledger_balance=10000.0,
            currency="USD"
        )
        session.add(acct)
        await session.commit()
        await session.refresh(acct)
    
    account_balance = float(acct.available_balance or 0.0)
    
    # Risk management checks
    max_position_size = account_balance * 0.1  # Max 10% per trade
    if req.size > max_position_size:
        raise HTTPException(status_code=400, detail=f"Trade size exceeds risk limit. Max: {max_position_size:.2f}")
    
    # Check balance for buy orders
    if req.side == 'buy' and account_balance < req.size:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: {account_balance:.2f}")

    # Create decision dictionary
    decision = {
        "signal": req.side,
        "position_size": req.size,
        "strategy": "manual",
        "market": req.market,
    }

    # Execute via executor (paper/live)
    result = await executor.execute(req.user_id, req.symbol, decision, mode=req.mode, session=session)
    return {"ok": True, "result": result}
