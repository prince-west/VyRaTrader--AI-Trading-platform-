# backend/app/services/backtest/backtester.py
import math
from typing import List, Dict, Any, Callable, Optional
from backend.app.services.slippage import apply_slippage
import statistics

class Backtester:
    """
    Simple discrete-time backtester (one asset), single-position (no pyramiding).
    - prices: list of dicts with 'close' (float) and optionally 'volume' and 'adv' (avg daily volume)
    - strategy_fn: callable(symbol, price_history) -> decision dict with {'action','size'(notional) optional}
    - initial_cash: starting cash
    - fee_pct: e.g., 0.002 for 0.2%
    """

    def __init__(self, prices: List[Dict[str,Any]], slippage_apply: Callable = apply_slippage, fee_pct: float = 0.002, symbol: str = "SYM"):
        self.prices = prices
        self.slippage_apply = slippage_apply
        self.fee_pct = fee_pct
        self.symbol = symbol

    def run(self, strategy_fn: Callable[[str, List[float]], Dict[str,Any]], initial_cash: float = 10000.0, risk_max_pct: float = 0.1) -> Dict[str,Any]:
        cash = initial_cash
        position = None  # dict {entry_price, qty, entry_notional}
        trades = []
        equity_curve = []
        price_history = []

        for t, bar in enumerate(self.prices):
            price = float(bar["close"])
            price_history.append(price)
            decision = strategy_fn(self.symbol, price_history)

            # compute ADV for slippage model fallback
            adv = float(bar.get("adv") or bar.get("volume") or 0.0)

            # Buy
            if decision.get("action") == "buy" and not position:
                # determine notional to deploy
                size_notional = min(cash * risk_max_pct, float(decision.get("size") or cash * risk_max_pct))
                if size_notional <= 0:
                    continue
                qty = size_notional / price
                fill_price = self.slippage_apply("buy", price, size_notional, adv or 1.0)
                fee = size_notional * self.fee_pct
                cost = qty * fill_price + fee
                if cost > cash - 1e-8:
                    # insufficient cash; skip
                    continue
                cash -= cost
                position = {"entry_price": fill_price, "qty": qty, "entry_notional": qty*fill_price, "entry_fee": fee}
                trades.append({"type":"buy","time":t,"price":fill_price,"qty":qty,"notional":qty*fill_price,"fee":fee,"reason":decision.get("reason")})
            # Sell
            elif (decision.get("action") == "sell") and position:
                qty = position["qty"]
                notional = qty * price
                fill_price = self.slippage_apply("sell", price, position["entry_notional"], adv or 1.0)
                fee = qty * fill_price * self.fee_pct
                proceeds = qty * fill_price - fee
                # pnl
                pnl = proceeds - position["entry_notional"]
                cash += proceeds
                trades.append({"type":"sell","time":t,"price":fill_price,"qty":qty,"notional":qty*fill_price,"fee":fee,"pnl":pnl,"reason":decision.get("reason")})
                position = None

            # record equity
            market_value = position["qty"] * price if position else 0.0
            equity = cash + market_value
            equity_curve.append(equity)

        # close any open position at last price
        if position:
            last = float(self.prices[-1]["close"])
            adv = float(self.prices[-1].get("adv") or self.prices[-1].get("volume") or 0.0)
            fill_price = self.slippage_apply("sell", last, position["entry_notional"], adv or 1.0)
            fee = position["qty"] * fill_price * self.fee_pct
            proceeds = position["qty"] * fill_price - fee
            pnl = proceeds - position["entry_notional"]
            cash += proceeds
            trades.append({"type":"sell_end","time":len(self.prices)-1,"price":fill_price,"qty":position["qty"],"notional":position["qty"]*fill_price,"fee":fee,"pnl":pnl})
            position = None
            equity_curve.append(cash)

        # metrics
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i-1]
            cur = equity_curve[i]
            if prev <= 0:
                returns.append(0.0)
            else:
                returns.append((cur - prev) / prev)
        avg_ret = statistics.mean(returns) if returns else 0.0
        std_ret = statistics.pstdev(returns) if len(returns) > 1 else 0.0
        sharpe = (avg_ret / std_ret) * (252**0.5) if std_ret > 0 else 0.0

        # max drawdown
        peak = -math.inf
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        total_return = (equity_curve[-1] - initial_cash) / initial_cash if equity_curve else 0.0

        return {
            "initial_cash": initial_cash,
            "final_equity": equity_curve[-1] if equity_curve else initial_cash,
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "equity_curve": equity_curve,
            "trades": trades,
        }
