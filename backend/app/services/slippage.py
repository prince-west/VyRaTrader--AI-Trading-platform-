# backend/app/services/slippage.py
from typing import Dict

def compute_slippage_pct(size_notional: float, avg_daily_volume: float, base_slippage: float = 0.0005) -> float:
    """
    Deterministic slippage percentage model.
    - base_slippage: minimal slippage for tiny trades (0.05% default)
    - size_notional: trade notional (in asset currency)
    - avg_daily_volume: average daily volume (same currency) - liquidity proxy
    Formula: base + k * sqrt(size / adv) where k chosen to produce sensible scale.
    """
    if avg_daily_volume <= 0:
        return base_slippage
    # k tuned to produce ~0.1% slippage when size is ~0.5% of ADV
    k = 0.005
    ratio = size_notional / avg_daily_volume
    slippage = base_slippage + k * (ratio ** 0.5)
    return float(slippage)

def apply_slippage(side: str, price: float, size_notional: float, avg_daily_volume: float) -> float:
    """
    Returns the expected fill price after slippage:
    - For buys: price * (1 + slippage_pct)
    - For sells: price * (1 - slippage_pct)
    """
    pct = compute_slippage_pct(size_notional, avg_daily_volume)
    if side.lower() == "buy":
        return price * (1.0 + pct)
    else:
        return price * (1.0 - pct)
