import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def register_and_login(client: AsyncClient, username: str = "confirmuser", password: str = "confirmpass") -> str:
    resp = await client.post("/api/auth/register", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_confirm_topup_credits_wallet_immediately(client: AsyncClient):
    """Issue #19: confirm_topup should credit wallet when status is 'success'."""
    token = await register_and_login(client)

    with patch("app.routers.wallet.payment_client.confirm_transaction", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = {
            "status": "success",
            "transactionId": "txn-test-1",
            "gatewayResponseCode": "0",
        }

        with patch("app.routers.wallet.payment_client.create_transaction", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "transactionId": "txn-test-1",
                "status": "initiated",
                "merchantReference": "PPV2-TEST",
            }
            resp = await client.post(
                "/api/wallet/topup",
                json={"amount": 10.0, "gateway": "edfali", "msisdn": "0910000000", "gateway_env": "test"},
                headers=auth_header(token),
            )
            assert resp.status_code == 200

        resp = await client.post(
            "/api/wallet/topup/confirm",
            json={"transaction_id": "txn-test-1", "otp": "1234"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance_minor"] == 1000
        assert data["balance"] == "10.00"


@pytest.mark.asyncio
async def test_confirm_topup_rejects_other_users_transaction(client: AsyncClient):
    """Issue #22: confirm_topup should reject transactions belonging to other users."""
    token1 = await register_and_login(client, username="user_a", password="pass_a")
    token2 = await register_and_login(client, username="user_b", password="pass_b")

    with patch("app.routers.wallet.payment_client.create_transaction", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "transactionId": "txn-cross-user",
            "status": "initiated",
            "merchantReference": "PPV2-CROSS",
        }
        await client.post(
            "/api/wallet/topup",
            json={"amount": 5.0, "gateway": "edfali", "msisdn": "0910000000", "gateway_env": "test"},
            headers=auth_header(token1),
        )

    with patch("app.routers.wallet.payment_client.confirm_transaction", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = {"status": "success", "transactionId": "txn-cross-user"}
        resp = await client.post(
            "/api/wallet/topup/confirm",
            json={"transaction_id": "txn-cross-user", "otp": "1234"},
            headers=auth_header(token2),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_topup_failure_marks_failed(client: AsyncClient):
    """Issue #19: confirm_topup should mark as failed on gateway failure."""
    token = await register_and_login(client, username="failuser", password="failpass")

    with patch("app.routers.wallet.payment_client.create_transaction", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "transactionId": "txn-fail-1",
            "status": "initiated",
            "merchantReference": "PPV2-FAIL",
        }
        await client.post(
            "/api/wallet/topup",
            json={"amount": 5.0, "gateway": "edfali", "msisdn": "0910000000", "gateway_env": "test"},
            headers=auth_header(token),
        )

    with patch("app.routers.wallet.payment_client.confirm_transaction", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = {"status": "failed", "gatewayMessage": "OTP incorrect"}
        resp = await client.post(
            "/api/wallet/topup/confirm",
            json={"transaction_id": "txn-fail-1", "otp": "0000"},
            headers=auth_header(token),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_confirm_topup_nonexistent_transaction(client: AsyncClient):
    """Confirming a nonexistent transaction should return 404."""
    token = await register_and_login(client, username="ghostuser", password="ghostpass")

    with patch("app.routers.wallet.payment_client.confirm_transaction", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = {"status": "success"}
        resp = await client.post(
            "/api/wallet/topup/confirm",
            json={"transaction_id": "txn-does-not-exist", "otp": "1234"},
            headers=auth_header(token),
        )
        assert resp.status_code == 404
