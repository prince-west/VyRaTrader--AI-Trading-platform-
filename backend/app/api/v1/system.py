# backend/app/api/v1/system.py
from fastapi import APIRouter

router = APIRouter(tags=["system"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "VyRaTrader backend running"}
