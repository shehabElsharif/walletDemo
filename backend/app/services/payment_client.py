import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


class GatewayError(Exception):
    """Platform returned a gateway-level error (422)."""

    def __init__(self, status_code: int, message: str, code: str | None = None):
        self.status_code = status_code
        self.message = message
        self.code = code
        super().__init__(message)


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.platform_url,
            headers={"x-api-key": settings.webhook_secret},
            timeout=15.0,
        )
    return _client


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def create_transaction(
    *,
    api_key: str,
    user_id: str,
    gateway: str,
    amount: float,
    idempotency_key: str,
    msisdn: str | None = None,
    birth_year: str | None = None,
    description: str | None = None,
    gateway_env: str = "test",
) -> dict:
    client = await get_client()
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    body: dict = {
        "userId": user_id,
        "gateway": gateway,
        "amount": round(amount, 2),
        "idempotencyKey": idempotency_key,
        "gatewayEnv": gateway_env,
    }
    if msisdn:
        body["msisdn"] = msisdn
    if birth_year:
        body["birthYear"] = birth_year
    if description:
        body["description"] = description

    resp = await client.post("/api/v1/transactions", json=body, headers=headers)
    if resp.status_code in (400, 422):
        data = resp.json()
        raise GatewayError(resp.status_code, data.get("message", "Transaction declined"), data.get("code"))
    resp.raise_for_status()
    return resp.json()


async def confirm_transaction(
    *,
    api_key: str,
    transaction_id: str,
    otp: str,
) -> dict:
    client = await get_client()
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/confirm",
        json={"otp": otp},
        headers=headers,
    )
    if resp.status_code in (400, 409, 422):
        data = resp.json()
        raise GatewayError(resp.status_code, data.get("message", "Transaction declined"), data.get("code"))
    resp.raise_for_status()
    return resp.json()


async def get_transaction(*, api_key: str, transaction_id: str) -> dict:
    client = await get_client()
    headers = {"x-api-key": api_key}

    resp = await client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()
