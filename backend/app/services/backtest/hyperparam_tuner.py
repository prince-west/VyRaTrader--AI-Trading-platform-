# backend/app/services/backtest/hyperparam_tuner.py
import itertools
from typing import Dict, Any, Callable, List
from backend.app.services.backtest.backtester import Backtester

def grid_search(prices, strategy_factory: Callable[[Dict[str,Any]], Callable], param_grid: Dict[str, List[Any]], metric: str = "sharpe", initial_cash: float = 10000.0) -> Dict[str, Any]:
    """
    - strategy_factory(params) -> function(symbol, price_history) that returns decision dict
    - param_grid is dict param -> list of values
    Returns best param set and its results.
    """
    keys = list(param_grid.keys())
    best_score = float("-inf")
    best_result = None
    best_params = None
    for combo in itertools.product(*(param_grid[k] for k in keys)):
        params = dict(zip(keys, combo))
        strat_fn = strategy_factory(params)
        bt = Backtester(prices)
        res = bt.run(strat_fn, initial_cash=initial_cash)
        score = res.get(metric, 0.0)
        if score > best_score:
            best_score = score
            best_result = res
            best_params = params
    return {"best_params": best_params, "best_score": best_score, "best_result": best_result}
