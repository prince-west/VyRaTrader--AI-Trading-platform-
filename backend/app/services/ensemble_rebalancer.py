# backend/app/services/ensemble_rebalancer.py
from typing import Dict, List
import statistics

def reweight_by_performance(history_returns: Dict[str, List[float]]) -> Dict[str, float]:
    """
    history_returns: {strategy_name: [period_returns...]}
    Simple scheme: weight = max(0, mean_return / (std + eps)) normalized to sum=1 (Sharpe-like)
    """
    eps = 1e-8
    scores = {}
    for name, rets in history_returns.items():
        if not rets:
            scores[name] = 0.0
            continue
        mean_r = statistics.mean(rets)
        std_r = statistics.pstdev(rets) if len(rets) > 1 else 0.0
        scores[name] = max(0.0, mean_r / (std_r + eps))
    total = sum(scores.values())
    if total <= 0:
        # fallback equal weights
        n = max(1, len(scores))
        return {k: 1.0/n for k in scores}
    return {k: v/total for k,v in scores.items()}
