import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "testuser", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "dupuser", "password": "pass1"})
    resp = await client.post("/api/auth/register", json={"username": "dupuser", "password": "pass2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "loginuser", "password": "loginpass"})
    resp = await client.post("/api/auth/login", json={"username": "loginuser", "password": "loginpass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "wrongpw", "password": "correct"})
    resp = await client.post("/api/auth/login", json={"username": "wrongpw", "password": "incorrect"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "nobody", "password": "nothing"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_short_username(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "ab", "password": "pass"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "validname", "password": "ab"})
    assert resp.status_code == 422
