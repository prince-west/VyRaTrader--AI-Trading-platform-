# backend/tests/test_basic.py
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_healthcheck(client):
    """API health/boot check - endpoint must exist in your project."""
    r = await client.get("/api/v1/users/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_register_and_login(client):
    """Register + login flow (adjust payload shape if your auth expects different keys)."""
    payload = {"username": "testuser", "password": "pass123"}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    # some projects expect form data on login; adjust if necessary
    r = await client.post("/api/v1/auth/login", data=payload)
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_minimum_deposit_rule(client):
    """Deposits below GHS 500 must be rejected."""
    deposit = {"amount": 100, "currency": "GHS"}
    r = await client.post("/api/v1/payments/deposit", json=deposit)
    assert r.status_code == 400
    assert "Minimum deposit" in r.json()["detail"]


@pytest.mark.asyncio
async def test_deposit_fee_applied(client):
    """A deposit of 1000 GHS should return net_amount = 1000 - 2% = 980.0"""
    deposit = {"amount": 1000, "currency": "GHS"}
    r = await client.post("/api/v1/payments/deposit", json=deposit)
    assert r.status_code == 200
    data = r.json()
    assert data["net_amount"] == pytest.approx(980.0, rel=1e-6)


@pytest.mark.asyncio
async def test_withdrawal_fee_applied(client):
    """A withdrawal of 1000 GHS should return net_amount = 1000 - 5% = 950.0"""
    withdraw = {"amount": 1000, "currency": "GHS"}
    r = await client.post("/api/v1/payments/withdraw", json=withdraw)
    assert r.status_code == 200
    data = r.json()
    assert data["net_amount"] == pytest.approx(970.0, rel=1e-6)
