# backend/app/api/v1/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from backend.app.db.session import get_session
from backend.app.db.models import Transaction, Account
from backend.app.services.payment_gateway import get_provider_by_name
from backend.app.core.config import settings

router = APIRouter(tags=["webhooks"])

@router.post("/payments")
async def payments_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # try to infer provider
    provider_name = None
    if headers.get("x-paystack-signature"):
        provider_name = "paystack"
    elif headers.get("x-hubtel-signature"):
        provider_name = "hubtel"
    elif headers.get("stripe-signature"):
        provider_name = "stripe"
    elif headers.get("paypal-transmission-id"):
        provider_name = "paypal"
    elif headers.get("binancepay-signature") or headers.get("binancepay-signature".lower()):
        provider_name = "binancepay"
    else:
        provider_name = settings.PAYMENT_PROVIDER or "hubtel"

    adapter = get_provider_by_name(provider_name)
    try:
        event = await adapter.verify_webhook(headers, body)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Webhook verification failed: {str(e)}")

    data = event.get("data") or event
    # try to resolve transaction by reference or metadata
    ref = data.get("reference") or data.get("clientReference") or data.get("id") or None
    tx = None
    if ref:
        q = await session.exec(select(Transaction).where(Transaction.external_reference == ref))
        tx = q.first()
    if not tx:
        meta = data.get("metadata") or {}
        internal = meta.get("internal_tx_id")
        if internal:
            q = await session.exec(select(Transaction).where(Transaction.id == internal))
            tx = q.first()

    if not tx:
        # fallback – try by amount
        amount = data.get("amount") or data.get("value") or 0
        try:
            amount_major = float(amount) / 100.0 if isinstance(amount, (int, float)) and amount > 1000 else float(amount or 0.0)
        except Exception:
            amount_major = float(amount or 0.0)
        tx = Transaction(user_id=None, account_id=None, type="deposit", amount=amount_major, currency=data.get("currency","GHS"), status="pending", external_reference=ref)
        session.add(tx)
        await session.commit()
        await session.refresh(tx)

    # success detection
    status_val = (data.get("status") or data.get("transactionStatus") or "").lower()
    success_states = {"success","completed","paid","charge.success","ok"}
    if status_val in success_states or data.get("event") in ("charge.success","transaction.success","CHECKOUT_SESSION_COMPLETED"):
        tx.status = "completed"
        tx.fee_percent = tx.fee_percent or settings.DEPOSIT_FEE_PERCENT/100.0
        tx.fee_amount = tx.fee_amount or round(tx.amount * (tx.fee_percent or settings.DEPOSIT_FEE_PERCENT/100.0),2)
        # credit account if we have an account id
        if tx.account_id:
            acct_q = await session.exec(select(Account).where(Account.id == tx.account_id))
            acct = acct_q.first()
            if acct:
                net_amt = round(tx.amount - (tx.fee_amount or 0.0),2)
                acct.available_balance = (acct.available_balance or 0.0) + net_amt
                acct.ledger_balance = (acct.ledger_balance or 0.0) + net_amt
                session.add(acct)
        # create fee transaction
        fee_tx = Transaction(user_id=tx.user_id, account_id=tx.account_id, type="fee", amount=tx.fee_amount or 0.0, currency=tx.currency, status="completed", external_reference=f"{tx.external_reference}-fee")
        session.add(fee_tx)
        await session.commit()
        return {"ok": True, "tx_id": str(tx.id), "status": "completed"}

    tx.status = status_val or "failed"
    await session.commit()
    return {"ok": True, "tx_id": str(tx.id), "status": tx.status}
