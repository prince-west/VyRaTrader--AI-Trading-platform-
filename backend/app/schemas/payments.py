from pydantic import BaseModel
from typing import Optional

class DepositRequest(BaseModel):
    user_id: str
    account_id: str
    amount: float

class WithdrawalRequest(BaseModel):
    user_id: str
    account_id: str
    amount: float

class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    fee_percent: Optional[float]
    fee_amount: Optional[float]
    status: str
    currency: str

    class Config:
        orm_mode = True



# Payments webhook (added by automated fixer)
from fastapi import Request, HTTPException, Depends
import hmac, hashlib, json
from decimal import Decimal, ROUND_HALF_UP
from backend.app.core.config import settings
from backend.app.db.session import get_session
from sqlmodel import select
from backend.app.db import models as db_models

WEBHOOK_SECRET = settings.SANDBOX_WEBHOOK_SECRET or ""

def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def verify_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)

@router.post("/webhook")
async def payments_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Signature", "") or request.headers.get("x-signature", "")
    if not verify_signature(body, sig, WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body)
    ext_ref = payload.get("external_reference") or payload.get("reference") or payload.get("transaction_id")
    status = payload.get("status", "").lower()
    amount = Decimal(str(payload.get("amount", "0")))
    currency = payload.get("currency", "GHS")

    if status not in ("success", "completed", "paid"):
        return {"status": "ignored", "reason": "not a success event"}

    async with get_session() as session:
        tx_cls = getattr(db_models, "Transaction", None)
        acct_cls = getattr(db_models, "Account", None)
        appwallet_cls = getattr(db_models, "AppWallet", None)

        q = await session.exec(select(tx_cls).where(tx_cls.external_reference == ext_ref))
        tx = q.first() if q else None
        if not tx:
            # create fallback deposit transaction
            tx = tx_cls(user_id=payload.get("user_id"), account_id=payload.get("account_id"), type="deposit",
                        amount=float(amount), currency=currency, status="completed", external_reference=ext_ref)
            session.add(tx)
            await session.commit()
            await session.refresh(tx)
        if getattr(tx, "status", None) == "completed":
            return {"status": "already_processed"}

        fee_percent = Decimal(str(settings.DEPOSIT_FEE_PERCENT)) if getattr(tx, "type", "") == "deposit" else Decimal(str(settings.WITHDRAWAL_FEE_PERCENT))
        fee_amount = _round2(amount * (fee_percent / Decimal('100')))
        net = _round2(amount - fee_amount)

        tx.status = "completed"
        if hasattr(tx, "fee_percent"):
            tx.fee_percent = float(fee_percent)
        if hasattr(tx, "fee_amount"):
            tx.fee_amount = float(fee_amount)
        await session.merge(tx)

        if getattr(tx, "account_id", None):
            q2 = await session.exec(select(acct_cls).where(acct_cls.id == tx.account_id))
            acct = q2.first() if q2 else None
            if acct and getattr(acct, "available_balance", None) is not None:
                if getattr(tx, "type", "") == "deposit":
                    acct.available_balance = float(Decimal(str(acct.available_balance)) + net)
                    acct.ledger_balance = float(Decimal(str(acct.ledger_balance)) + net)
                elif getattr(tx, "type", "") == "withdrawal":
                    acct.available_balance = float(Decimal(str(acct.available_balance)) - float(amount))
                    acct.ledger_balance = float(Decimal(str(acct.ledger_balance)) - float(amount))
                await session.merge(acct)

        # credit app wallet
        if appwallet_cls:
            q3 = await session.exec(select(appwallet_cls).where(appwallet_cls.currency == currency))
            app_w = q3.first() if q3 else None
            if not app_w:
                app_w = appwallet_cls(currency=currency, ledger_balance=float(fee_amount))
                session.add(app_w)
            else:
                if getattr(app_w, "ledger_balance", None) is not None:
                    app_w.ledger_balance = float(Decimal(str(app_w.ledger_balance)) + fee_amount)
                await session.merge(app_w)

        # create fee transaction if model supports it
        try:
            fee_tx = tx_cls(user_id=None, account_id=None, type="fee", amount=float(fee_amount),
                            currency=currency, status="completed", external_reference=f"fee-{ext_ref}")
            session.add(fee_tx)
        except Exception:
            pass

        await session.commit()

    return {"status": "ok", "tx_id": getattr(tx, 'id', None), "fee": float(fee_amount), "net": float(net)}
