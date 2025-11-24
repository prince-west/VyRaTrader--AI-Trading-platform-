# backend/app/api/v1/portfolio.py
"""
Portfolio endpoints: returns portfolio summary computed from account + closed trades.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select, func
from typing import List
from backend.app.core.security import get_current_user
from backend.app.db.session import get_session
from backend.app.db.models import User, Trade, Portfolio, Account

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Get account balance
    acct_stmt = select(Account).where(Account.user_id == current_user.id)
    acct_result = await session.execute(acct_stmt)
    account = acct_result.scalar_one_or_none()
    balance = account.available_balance if account else 0.0
    
    # Get closed trades for P&L calculation
    closed_trades_stmt = select(Trade).where(Trade.user_id == current_user.id, Trade.status == "closed")
    closed_trades_result = await session.execute(closed_trades_stmt)
    closed_trades = closed_trades_result.scalars().all()
    
    total_pnl = sum(trade.profit_loss for trade in closed_trades if trade.profit_loss)
    
    # Get positions (open trades)
    positions_stmt = select(Trade).where(Trade.user_id == current_user.id, Trade.status == "open")
    positions_result = await session.execute(positions_stmt)
    positions = positions_result.scalars().all()
    
    return {
        "balance": balance,
        "positions": [{"symbol": p.symbol, "side": p.side, "quantity": p.quantity, "entry_price": p.entry_price} for p in positions],
        "pnl": total_pnl,
        "growth_percent": 0.0 if balance == 0 else (total_pnl / balance * 100),
        "equity_curve": [],
    }


@router.get("/stats")
async def portfolio_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Get account
    acct_stmt = select(Account).where(Account.user_id == current_user.id)
    acct_result = await session.execute(acct_stmt)
    account = acct_result.scalar_one_or_none()
    balance = account.available_balance if account else 0.0
    
    # Get all trades
    trades_stmt = select(Trade).where(Trade.user_id == current_user.id)
    trades_result = await session.execute(trades_stmt)
    trades = trades_result.scalars().all()
    
    # Calculate stats
    trades_count = len(trades)
    profitable_trades = [t for t in trades if t.profit_loss and t.profit_loss > 0]
    win_rate = (len(profitable_trades) / trades_count * 100) if trades_count > 0 else 0.0
    total_pnl = sum(t.profit_loss for t in trades if t.profit_loss)
    active_trades = len([t for t in trades if t.status == "open"])
    
    return {
        "trades_count": trades_count,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "balance": balance,
        "active_trades": active_trades,
        "profitable_percent": win_rate,
        "ai_strategy": "Balanced",
    }