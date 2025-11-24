# backend/app/services/ai_ensemble.py
from typing import List, Dict, Any

# Import strategy classes (from unified strategies folder)
from backend.app.strategies.trend_following import TrendFollowingStrategy
from backend.app.strategies.momentum import MomentumStrategy
from backend.app.strategies.mean_reversion import MeanReversionStrategy
# Arbitrage removed: Requires millisecond execution, not practical for manual trading
from backend.app.strategies.breakout import BreakoutStrategy
from backend.app.strategies.volatility_breakout import VolatilityBreakoutStrategy
from backend.app.strategies.sentiment import SentimentStrategy
from backend.app.strategies.sentiment_filter import SentimentFilterStrategy
from backend.app.strategies.social_copy import SocialCopyStrategy

# Import INSTITUTIONAL-LEVEL strategies
from backend.app.strategies.vwap_strategy import VWAPStrategy
from backend.app.strategies.support_resistance import SupportResistanceStrategy
from backend.app.strategies.order_blocks import OrderBlocksStrategy
from backend.app.strategies.fair_value_gaps import FairValueGapsStrategy
from backend.app.strategies.market_structure import MarketStructureStrategy
from backend.app.strategies.volume_profile import VolumeProfileStrategy
from backend.app.strategies.liquidity_zones import LiquidityZonesStrategy


class AIEnsemble:
    """
    Ensemble aggregator for the available strategies.
    Each strategy.run returns {'signal','score','confidence'}.
    """

    def __init__(self, weights: Dict[str, float] = None):
        # Default weights — adjustable via config/DB later
        # INSTITUTIONAL-LEVEL strategies get highest weights
        self.weights = weights or {
            # INSTITUTIONAL-LEVEL STRATEGIES (Highest Priority)
            "vwap": 3.0,  # VWAP - institutional traders' PRIMARY tool
            "liquidity_zones": 2.8,  # Liquidity grabs - extremely reliable
            "order_blocks": 2.7,  # Smart money zones - very accurate
            "fair_value_gaps": 2.6,  # FVG fills - 90%+ fill rate
            "market_structure": 2.5,  # BOS/CHoCH - eliminates 60% of losses
            "support_resistance": 2.4,  # Pivot-based S/R with order flow
            "volume_profile": 2.3,  # PVN bounces - very reliable
            
            # TECHNICAL INDICATOR STRATEGIES
            "trend": 1.2,
            "momentum": 1.1,
            "mean_reversion": 0.9,
            "breakout": 1.0,
            "volatility_breakout": 0.9,
            
            # SENTIMENT/SOCIAL STRATEGIES
            "sentiment": 0.7,
            "sentiment_filter": 0.5,
            "social_copy": 0.6,
            # Arbitrage removed: Requires millisecond execution
        }

        # Instantiate ALL strategies (including institutional-level)
        self.strategies = {
            # INSTITUTIONAL-LEVEL STRATEGIES
            "vwap": VWAPStrategy(),
            "support_resistance": SupportResistanceStrategy(),
            "order_blocks": OrderBlocksStrategy(),
            "fair_value_gaps": FairValueGapsStrategy(),
            "market_structure": MarketStructureStrategy(),
            "volume_profile": VolumeProfileStrategy(),
            "liquidity_zones": LiquidityZonesStrategy(),
            
            # TECHNICAL INDICATOR STRATEGIES
            "trend": TrendFollowingStrategy(),
            "momentum": MomentumStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "breakout": BreakoutStrategy(),
            "volatility_breakout": VolatilityBreakoutStrategy(),
            
            # SENTIMENT/SOCIAL STRATEGIES
            "sentiment": SentimentStrategy(),
            "sentiment_filter": SentimentFilterStrategy(),
            "social_copy": SocialCopyStrategy(),
            # Arbitrage removed: Not practical for manual trading
        }

    def aggregate(self, symbol: str, prices: List[float], extra: Dict[str, Any] = None) -> Dict[str, Any]:
        extra = extra or {}

        buy_score = 0.0
        sell_score = 0.0
        details: Dict[str, Any] = {}

        # run each strategy and weight their contributions
        for name, strat in self.strategies.items():
            try:
                res = strat.run(symbol, prices, **extra)
                if not isinstance(res, dict):
                    # safety: expect dict
                    res = {"signal": "hold", "score": 0.0, "confidence": 0.0}
            except Exception as e:
                # strategy crash -> treat as hold
                res = {"signal": "hold", "score": 0.0, "confidence": 0.0}
            # normalize fields
            sig = res.get("signal", "hold")
            score = float(res.get("score", 0.0))
            conf = float(res.get("confidence", 0.0))
            w = float(self.weights.get(name, 1.0))

            details[name] = {"signal": sig, "score": score, "confidence": conf, "weight": w}

            contrib = score * conf * w
            if sig == "buy":
                buy_score += contrib
            elif sig == "sell":
                sell_score += contrib
            # hold contributes nothing

        # Final decision
        if buy_score > sell_score and buy_score - sell_score > 1e-6:
            final = "buy"
        elif sell_score > buy_score and sell_score - buy_score > 1e-6:
            final = "sell"
        else:
            final = "hold"

        # final strength metric is difference normalized
        final_strength = abs(buy_score - sell_score)

        return {
            "symbol": symbol,
            "final_signal": final,
            "buy_score": round(buy_score, 6),
            "sell_score": round(sell_score, 6),
            "strength": float(final_strength),
            "details": details,
        }
