import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    resp = await client.post("/api/auth/register", json={"username": "walletuser", "password": "walletpass"})
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_balance(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.get("/api/wallet", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == "0.00"
    assert data["balance_minor"] == 0
    assert data["currency"] == "LYD"


@pytest.mark.asyncio
async def test_get_balance_no_auth(client: AsyncClient):
    resp = await client.get("/api/wallet")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_balance_invalid_token(client: AsyncClient):
    resp = await client.get("/api/wallet", headers=auth_header("invalid-token"))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_topup_invalid_gateway(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/wallet/topup",
        json={"amount": 10.0, "gateway": "invalid"},
        headers=auth_header(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_topup_negative_amount(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/wallet/topup",
        json={"amount": -5.0, "gateway": "sadad"},
        headers=auth_header(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_topup_zero_amount(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/wallet/topup",
        json={"amount": 0, "gateway": "sadad"},
        headers=auth_header(token),
    )
    assert resp.status_code == 422
