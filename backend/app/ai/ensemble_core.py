# backend/app/ai/ensemble_core.py
from typing import List

def generate_final_signal(signals: List[str]) -> str:
    """
    Combine multiple strategy signals into one final trading decision.
    Example: signals = ["buy", "buy", "sell"] → returns "buy"
    """

    if not signals:
        return "hold"

    buy_count = signals.count("buy")
    sell_count = signals.count("sell")

    if buy_count > sell_count:
        return "buy"
    elif sell_count > buy_count:
        return "sell"
    else:
        return "hold"
