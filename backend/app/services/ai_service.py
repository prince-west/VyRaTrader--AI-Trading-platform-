# backend/app/services/ai_service.py
import asyncio
import os
from typing import Optional, Dict, Any
from backend.app.db.models import AILog
from backend.app.core.config import settings

class AIAdapter:
    async def chat(self, user_id: Optional[str], message: str, context: dict) -> Dict[str,Any]:
        raise NotImplementedError()

    async def explain_trade(self, trade_id: str) -> Dict[str,Any]:
        raise NotImplementedError()

    async def suggest_portfolio(self, user_id: Optional[str], risk_level: str) -> Dict[str,Any]:
        raise NotImplementedError()

class DummyAdapter(AIAdapter):
    async def chat(self, user_id, message, context):
        await asyncio.sleep(0)
        return {"reply": f"Prince (local): I heard '{message[:120]}'. Check momentum and risk before placing large trades.", "meta": {"model": "dummy"}}

    async def explain_trade(self, trade_id):
        await asyncio.sleep(0)
        return {"rationale": f"Dummy rationale for {trade_id}", "expected_profit": 0.01, "expected_loss": 0.02}

    async def suggest_portfolio(self, user_id, risk_level):
        mapping = {
            "Low": {"risk_multiplier":0.3,"alloc":{"stocks":0.3,"bonds":0.6,"crypto":0.1},"expected":"0.5-2%"},
            "Medium": {"risk_multiplier":0.6,"alloc":{"stocks":0.5,"bonds":0.3,"crypto":0.2},"expected":"2-4%"},
            "High": {"risk_multiplier":1.0,"alloc":{"stocks":0.6,"bonds":0.1,"crypto":0.3},"expected":"5%+"},
        }
        return mapping.get(risk_level, mapping["Medium"])

class OpenAIAdapter(AIAdapter):
    def __init__(self, api_key: Optional[str]=None):
        try:
            import openai
            self.openai = openai
        except Exception:
            self.openai = None
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    async def chat(self, user_id, message, context):
        if not self.openai or not self.api_key:
            return await DummyAdapter().chat(user_id, message, context)
        # run blocking openai in executor
        loop = asyncio.get_event_loop()
        def blocking():
            self.openai.api_key = self.api_key
            resp = self.openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":message}])
            return resp
        res = await loop.run_in_executor(None, blocking)
        reply = res["choices"][0]["message"]["content"]
        return {"reply": reply, "meta": {"model":"openai", "raw": res}}

class AIService:
    def __init__(self, adapter: Optional[AIAdapter] = None):
        if adapter:
            self.adapter = adapter
        else:
            self.adapter = OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else DummyAdapter()

    async def chat(self, user_id: Optional[str], message: str, context: dict):
        resp = await self.adapter.chat(user_id, message, context)
        # Logging to DB should be handled by the router layer so we avoid importing DB here directly.
        return resp

    async def explain_trade(self, trade_id: str):
        return await self.adapter.explain_trade(trade_id)

    async def suggest_portfolio(self, user_id: Optional[str], risk_level: str):
        return await self.adapter.suggest_portfolio(user_id, risk_level)

# --- Backwards-compatibility wrapper: ensure run_strategies is available ---

def run_strategies(*args, **kwargs):
    """
    Compatibility wrapper. The API expects a top-level function `run_strategies`.
    This wrapper will create an AIService instance and call a suitable method
    (tries several common names). If none exist, it raises a clear error.
    """
    try:
        svc = AIService()
    except NameError:
        raise RuntimeError("AIService is not defined in ai_service.py — check that class exists")

    # Try a list of likely method names in order of preference
    for method_name in ("run_strategies", "run", "start", "execute", "process"):
        if hasattr(svc, method_name):
            return getattr(svc, method_name)(*args, **kwargs)

    raise AttributeError(
        "AIService instance found but no runnable method (tried: "
        "'run_strategies','run','start','execute','process'). "
        "Open backend/app/services/ai_service.py and implement one of those methods."
    )

# (Optional) ensure the symbol is available when doing `from ... import *`
__all__ = ["AIAdapter", "DummyAdapter", "OpenAIAdapter", "AIService"]
try:
    __all__.append("run_strategies")
except Exception:
    __all__ = getattr(globals().get("__all__", []), "copy", lambda: [])() + ["run_strategies"]
