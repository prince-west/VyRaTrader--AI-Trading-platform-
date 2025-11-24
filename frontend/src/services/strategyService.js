"""
AI Engine — centralized interface for all AI-driven trading logic.
This wraps the AIEnsemble, RiskManager, and TradingEngine.
"""

import logging

# Use the new ensemble implementation. Try both package layouts and fall back to a no-op.
try:
    from app.ai.ensemble_core import generate_final_signal
except Exception:
    try:
        from backend.app.ai.ensemble_core import generate_final_signal
    except Exception:
        def generate_final_signal(symbol: str) -> str:
            return "hold"
from backend.app.services.risk_manager import RiskManager
from backend.app.services.trading_engine import TradingEngine

logger = logging.getLogger(__name__)

class AIEngine:
    """
    Centralized interface for all AI-driven trading logic.
    Wraps the ensemble, risk manager, and trading engine.
    """
    def __init__(self):
        self.risk_manager: RiskManager = RiskManager()
        self.trading_engine: TradingEngine = TradingEngine()

    async def analyze_and_trade(self, symbol: str, prices: list[float]) -> dict:
        """
        Main AI workflow:
        1. Get AI signal (buy/sell/hold)
        2. Run through risk checks
        3. Execute trade if approved
        """
        try:
            signal = generate_final_signal(symbol)
        except Exception as e:
            logger.exception("Failed to generate signal for %s: %s", symbol, e)
            signal = "hold"
        risk_approved = self.risk_manager.evaluate(symbol, signal)

        if not risk_approved:
            logger.info("Trade for %s blocked by risk manager.", symbol)
            return {"status": "blocked", "symbol": symbol}

        try:
            trade_result = await self.trading_engine.process_trade(symbol, signal)
            logger.info("Trade executed for %s: %s", symbol, trade_result)
            return trade_result
        except Exception as e:
            logger.exception("Trade execution failed for %s: %s", symbol, e)
            return {"status": "error", "symbol": symbol, "error": str(e)}

export async function getStrategySignal(strategy, symbol) {
  try {
    const res = await fetch(`/api/strategy/${strategy}/${symbol}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    let signal = typeof data.signal === "number" ? data.signal : 0.0;
    signal = Math.max(-1, Math.min(1, signal));
    return signal;
  } catch (err) {
    console.error(`Failed to fetch signal for ${strategy}/${symbol}:`, err);
    return 0.0;
  }
}