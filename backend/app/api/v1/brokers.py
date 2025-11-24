# backend/app/api/v1/brokers.py
"""
Brokers router: registration & listing (stores secrets in dev secret_store)
Not production-ready; demonstrates secret storage integration.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.app.core.secret_store import SecretStore
from backend.app.core.config import get_settings
from backend.app.services.trade_executor import get_broker_status

router = APIRouter(tags=["brokers"])
store = SecretStore()
settings = get_settings()


@router.get("/brokers/status")
async def broker_status():
    return await get_broker_status()

class RegisterBrokerRequest(BaseModel):
    provider: str
    api_key: str
    api_secret: str | None = None
    account_id: str | None = None
    testnet: bool = True


@router.post("/brokers/register")
async def register_broker(req: RegisterBrokerRequest):
    # Store sensitive values via secret store (dev)
    name_base = f"broker:{req.provider}:{req.account_id or 'default'}"
    store.set_secret(f"{name_base}:api_key", req.api_key)
    if req.api_secret:
        store.set_secret(f"{name_base}:api_secret", req.api_secret)
    return {"ok": True, "note": "Stored in dev secret store. Replace with Vault in prod."}
