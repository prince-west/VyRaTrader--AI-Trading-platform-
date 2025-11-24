# backend/tests/test_payments_api.py
import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.app.main import app

@pytest.mark.asyncio
async def test_deposit_requires_minimum(client):
    """Deposits below 500 GHS should be rejected"""
    deposit = {"amount": 100.0, "currency": "GHS", "user_id": "test-user-1"}
    r = await client.post("/api/v1/payments/deposit", json=deposit)
    assert r.status_code == 400

@pytest.mark.asyncio
async def test_deposit_creates_transaction(client):
    """A valid deposit creates a pending transaction and returns transaction_id"""
    deposit = {"amount": 1000.0, "currency": "GHS", "user_id": "test-user-1", "external_reference": "ext-1234"}
    r = await client.post("/api/v1/payments/deposit", json=deposit)
    assert r.status_code == 200
    data = r.json()
    assert "transaction_id" in data and data["transaction_id"] is not None
    assert data["net_amount"] == pytest.approx(980.0, rel=1e-6)
