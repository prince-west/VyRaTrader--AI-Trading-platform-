from fastapi import APIRouter, HTTPException
from backend.app.ai.engine import AIEngine

router = APIRouter(prefix="/ai", tags=["AI"])

ai_engine = AIEngine()

@router.post("/analyze")
async def analyze(symbol: str, prices: list[float]):
    """
    Trigger AI analysis and trading logic.
    Example request body:
    {
        "symbol": "BTC/USD",
        "prices": [58000.0, 58200.0, 57950.0, 58400.0]
    }
    """
    try:
        result = await ai_engine.analyze_and_trade(symbol, prices)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
