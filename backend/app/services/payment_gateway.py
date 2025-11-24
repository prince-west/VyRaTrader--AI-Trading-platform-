# backend/app/services/payment_gateway.py
"""
Payment gateway adapters: Hubtel, Paystack (Ghana), Stripe (card + bank transfers), PayPal, BinancePay (crypto).
Each adapter implements:
- async initialize_payment(user_email, amount, currency, callback_url, metadata)
- async verify_webhook(headers, raw_body)
- optionally payout/disburse methods (payout not implemented universally; if provider supports, adapter will expose)
"""
from typing import Optional, Dict, Any, TypedDict
import hmac, hashlib, json, asyncio
import httpx, base64, os

from backend.app.core.config import settings

# optional external libs
try:
    import stripe
except Exception:
    stripe = None

class PaymentResult(TypedDict, total=False):
    provider: str
    reference: Optional[str]
    authorization_url: Optional[str]
    client_secret: Optional[str]
    raw: Dict[str, Any]

class PaymentProvider:
    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        raise NotImplementedError()

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        raise NotImplementedError()

    async def create_payout(self, *args, **kwargs) -> Dict[str,Any]:
        raise NotImplementedError()

# ---------------------------
# HubtelAdapter (Ghana)
# ---------------------------
class HubtelAdapter(PaymentProvider):
    def __init__(self):
        self.client_id = settings.HUBTEL_CLIENT_ID
        self.client_secret = settings.HUBTEL_CLIENT_SECRET
        self.base_url = (settings.HUBTEL_BASE_URL or "https://api.hubtel.com/v1").rstrip("/")
        if not (self.client_id and self.client_secret):
            # Hubtel optional for dev; do not raise here — will raise when used
            pass

    async def _auth_headers(self) -> Dict[str,str]:
        if not (self.client_id and self.client_secret):
            raise RuntimeError("Hubtel credentials not configured")
        tok = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {tok}", "Content-Type": "application/json"}

    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        headers = await self._auth_headers()
        payload = {
            "clientReference": metadata.get("internal_tx_id") if metadata else None,
            "customerEmail": user_email,
            "items": [{"name":"Deposit","quantity":1,"price":int(round(amount*100))}],
            "callbackUrl": callback_url,
            "currency": currency
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/checkout/v2/register", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            d = resp.json()
            checkout = d.get("checkoutUrl") or d.get("data",{}).get("checkoutUrl")
            ref = d.get("reference") or (metadata.get("internal_tx_id") if metadata else None)
            return PaymentResult(provider="hubtel", reference=ref, authorization_url=checkout, raw=d)

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        # Hubtel may use HMAC SHA256 with a webhook secret
        secret = settings.SANDBOX_WEBHOOK_SECRET
        if secret:
            sig_header = headers.get("x-hubtel-signature") or headers.get("X-Hubtel-Signature")
            if sig_header:
                computed = hmac.new(secret.encode(), body, digestmod=hashlib.sha256).hexdigest()
                if not hmac.compare_digest(computed, sig_header):
                    raise ValueError("Invalid Hubtel webhook signature")
        return json.loads(body.decode("utf-8"))

# ---------------------------
# PaystackAdapter (Ghana)
# ---------------------------
class PaystackAdapter(PaymentProvider):
    def __init__(self):
        self.secret = settings.PAYSTACK_SECRET_KEY
        self.base_url = getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")
        if not self.secret:
            # not required until used
            pass

    def _headers(self):
        if not self.secret:
            raise RuntimeError("PAYSTACK_SECRET_KEY not configured")
        return {"Authorization": f"Bearer {self.secret}", "Content-Type": "application/json"}

    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        async with httpx.AsyncClient() as client:
            amt_smallest = int(round(amount * 100))
            payload = {"email": user_email, "amount": amt_smallest, "currency": currency, "callback_url": callback_url}
            if metadata:
                payload["metadata"] = metadata
            r = await client.post(f"{self.base_url}/transaction/initialize", json=payload, headers=self._headers(), timeout=30)
            r.raise_for_status()
            d = r.json()
            return PaymentResult(provider="paystack", reference=d["data"].get("reference"), authorization_url=d["data"].get("authorization_url"), raw=d)

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        sig = headers.get("x-paystack-signature") or headers.get("X-Paystack-Signature")
        if not sig:
            raise ValueError("Missing Paystack signature")
        computed = hmac.new(self.secret.encode(), body, digestmod=hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed, sig):
            raise ValueError("Invalid Paystack signature")
        return json.loads(body.decode("utf-8"))

# ---------------------------
# StripeAdapter (Cards + bank transfers)
# ---------------------------
class StripeAdapter(PaymentProvider):
    def __init__(self):
        self.secret = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if not self.secret:
            # allow creation; will raise if attempted without keys
            pass
        else:
            if stripe:
                stripe.api_key = self.secret

    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        if not stripe:
            raise RuntimeError("stripe python package not installed (pip install stripe)")
        # default: create a checkout session (card) for the amount
        amt_small = int(round(amount * 100))
        def blocking_create():
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {"name": "VyRaTrader Deposit"},
                        "unit_amount": amt_small,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=callback_url or "https://example.com/success",
                cancel_url=callback_url or "https://example.com/cancel",
                metadata=metadata or {}
            )
            return session
        loop = asyncio.get_event_loop()
        s = await loop.run_in_executor(None, blocking_create)
        url = s.url if hasattr(s, "url") else s.get("url")
        return PaymentResult(provider="stripe", reference=getattr(s, "id", None), authorization_url=url, raw={"session": s})

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        if not stripe or not self.webhook_secret:
            raise RuntimeError("Stripe lib or webhook secret missing")
        sig = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        if not sig:
            raise ValueError("Missing stripe signature header")
        def blocking_construct():
            return stripe.Webhook.construct_event(body, sig, self.webhook_secret)
        loop = asyncio.get_event_loop()
        ev = await loop.run_in_executor(None, blocking_construct)
        return ev

    async def create_payout(self, recipient: Dict[str, Any], amount: float, currency: str) -> Dict[str, Any]:
        """
        If you use Stripe Connect and have connected accounts, you can create payouts.
        This function is a convenience wrapper — it requires proper Stripe setup.
        """
        if not stripe:
            raise RuntimeError("stripe library required")
        # Expect recipient = {"connected_account": acct_id} when using Connect
        acct = recipient.get("connected_account")
        if not acct:
            raise RuntimeError("recipient.connected_account required for Stripe payouts")
        def blocking_payout():
            # This is a naive example: create a transfer to connected account, then a payout.
            # In production you MUST use Connect properly.
            tr = stripe.Transfers.create(
                amount=int(round(amount * 100)),
                currency=currency.lower(),
                destination=acct
            )
            return tr
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, blocking_payout)
        return {"ok": True, "raw": res}

# ---------------------------
# PayPalAdapter (orders)
# ---------------------------
class PayPalAdapter(PaymentProvider):
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.base_url = (settings.PAYPAL_BASE_URL or "https://api-m.paypal.com").rstrip("/")
        if not (self.client_id and self.client_secret):
            pass

    async def _get_access_token(self) -> str:
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/v1/oauth2/token", data={"grant_type":"client_credentials"}, auth=auth, timeout=20)
            r.raise_for_status()
            return r.json()["access_token"]

    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        order = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                "custom_id": metadata.get("internal_tx_id") if metadata else None
            }],
            "application_context": {
                "return_url": callback_url or "https://example.com/success",
                "cancel_url": callback_url or "https://example.com/cancel"
            }
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/v2/checkout/orders", json=order, headers=headers, timeout=30)
            r.raise_for_status()
            d = r.json()
            approval = next((l["href"] for l in d.get("links",[]) if l.get("rel") == "approve"), None)
            return PaymentResult(provider="paypal", reference=d.get("id"), authorization_url=approval, raw=d)

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        # validate via PayPal verify-webhook-signature endpoint
        token = await self._get_access_token()
        verify_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "cert_url": headers.get("paypal-cert-url"),
            "auth_algo": headers.get("paypal-auth-algo"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": json.loads(body.decode("utf-8"))
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/v1/notifications/verify-webhook-signature", json=payload, headers=verify_headers, timeout=20)
            r.raise_for_status()
            resp = r.json()
            if resp.get("verification_status") != "SUCCESS":
                raise ValueError("Invalid PayPal webhook signature")
            return json.loads(body.decode("utf-8"))

# ---------------------------
# BinancePayAdapter (Crypto)
# ---------------------------
class BinancePayAdapter(PaymentProvider):
    def __init__(self):
        self.api_key = getattr(settings, "BINANCEPAY_API_KEY", None)
        self.api_secret = getattr(settings, "BINANCEPAY_API_SECRET", None)
        self.base_url = getattr(settings, "BINANCEPAY_BASE_URL", "https://bpay.binanceapi.com")
        if not (self.api_key and self.api_secret):
            pass

    async def _sign(self, payload: str) -> str:
        # Binancpay requires timestamp/nonce and signature (HMAC-SHA384 typically) — implementation varies
        return hmac.new((self.api_secret or "").encode(), payload.encode(), hashlib.sha384).hexdigest()

    async def initialize_payment(self, user_email: str, amount: float, currency: str, callback_url: str, metadata: Optional[Dict[str,Any]] = None) -> PaymentResult:
        if not (self.api_key and self.api_secret):
            raise RuntimeError("BinancePay credentials not configured")
        # create order endpoint
        order = {
            "amount": f"{amount:.8f}",
            "currency": currency,
            "merchantTradeNo": metadata.get("internal_tx_id") if metadata else None,
            "notifyUrl": callback_url,
            "goods": [{"goodsType": "01", "goodsName": "VyRaTrader Deposit", "price": f"{amount:.8f}", "goodsQuantity": 1}]
        }
        body = json.dumps(order)
        sign = await self._sign(body)
        headers = {"Content-Type":"application/json", "Binancepay-Timestamp": "", "Binancepay-Nonce": "", "Binancepay-Signature": sign, "Binancepay-Api-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/binancepay/openapi/v2/order", data=body, headers=headers, timeout=20)
            r.raise_for_status()
            d = r.json()
            pay_url = d.get("data",{}).get("payUrl")
            return PaymentResult(provider="binancepay", reference=d.get("data",{}).get("merchantTradeNo"), authorization_url=pay_url, raw=d)

    async def verify_webhook(self, headers: Dict[str,str], body: bytes) -> Dict[str,Any]:
        # verify using API secret – signature header name varies
        sig = headers.get("Binancepay-Signature") or headers.get("binancepay-signature")
        if not sig:
            raise ValueError("Missing BinancePay signature")
        computed = hmac.new((self.api_secret or "").encode(), body, hashlib.sha384).hexdigest()
        if not hmac.compare_digest(computed, sig):
            raise ValueError("Invalid BinancePay signature")
        return json.loads(body.decode("utf-8"))

# ---------------------------
# Factory
# ---------------------------
def get_provider_by_name(name: str) -> PaymentProvider:
    n = (name or "").lower()
    if n == "hubtel":
        return HubtelAdapter()
    if n == "paystack":
        return PaystackAdapter()
    if n == "stripe":
        return StripeAdapter()
    if n == "paypal":
        return PayPalAdapter()
    if n in ("binancepay","crypto","crypto-pay"):
        return BinancePayAdapter()
    # fallback to default configured provider
    default = (settings.PAYMENT_PROVIDER or "hubtel").lower()
    return get_provider_by_name(default)
