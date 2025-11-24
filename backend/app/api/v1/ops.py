# backend/app/api/v1/ops.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.app.services.backtest.backtester import Backtester
from backend.app.services.backtest.hyperparam_tuner import grid_search
from backend.app.services.data_feed import BinanceMarketDataAdapter

router = APIRouter(tags=["ops"])

class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    lookback: int = 500
    initial_cash: float = 10000.0

class TuneRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    lookback: int = 500
    strategy: str
    param_grid: Dict[str, List[Any]]


executor = ThreadPoolExecutor(max_workers=2)

@router.post("/backtest")
async def run_backtest(req: BacktestRequest):
    # fetch data
    adapter = BinanceMarketDataAdapter()
    klines = await adapter.get_klines(req.symbol, interval=req.interval, limit=req.lookback)
    prices = [{"close": c["close"], "volume": c["volume"], "adv": c["volume"]} for c in klines]
    # simple example: use a trivial strategy that buys when price dips 1% from previous bar
    def simple_strategy(sym, hist):
        if len(hist) < 2:
            return {"action":"hold", "reason":"not_enough_data"}
        if hist[-1] < hist[-2] * 0.99:
            return {"action":"buy", "size": req.initial_cash * 0.1, "reason":"dip-buy"}
        return {"action":"hold", "reason":"no_signal"}
    bt = Backtester(prices)
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(executor, lambda: bt.run(simple_strategy, initial_cash=req.initial_cash))
    return res

@router.post("/tune")
async def tune(req: TuneRequest):
    # For safety: the server must not run heavy tuning on limited resources. This endpoint is for dev only.
    adapter = BinanceMarketDataAdapter()
    klines = await adapter.get_klines(req.symbol, interval=req.interval, limit=req.lookback)
    prices = [{"close": c["close"], "volume": c["volume"], "adv": c["volume"]} for c in klines]

    # Strategy factory mapping - you may expand this to real factory functions
    from backend.app.strategies.trend_following import TrendFollowingStrategy
    def factory(params):
        def strat(symbol, hist):
            # create instance with params
            st = TrendFollowingStrategy(fast_ema=params.get("fast",12), slow_ema=params.get("slow",26))
            out = st.run(symbol, hist) if hasattr(st, "run") else st.generate_signal(symbol, hist)
            # normalize to backtester decision
            return {"action": out.get("signal") or out.get("action"), "size": params.get("size", 0)}
        return strat

    res = grid_search(prices, factory, req.param_grid, metric="sharpe", initial_cash=10000.0)
    return res
