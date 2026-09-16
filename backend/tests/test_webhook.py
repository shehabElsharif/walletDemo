import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient


def sign_payload(payload: dict, secret: str, timestamp: str = "1234567890") -> tuple[str, str]:
    body = json.dumps(payload, separators=(",", ":"))
    sig = "sha256=" + hmac.new(
        secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return sig, timestamp


def sign_and_body(payload: dict, secret: str, timestamp: str = "1234567890") -> tuple[str, str, bytes]:
    body_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = "sha256=" + hmac.new(
        secret.encode(), f"{timestamp}.{body_bytes.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    return sig, timestamp, body_bytes


@pytest.mark.asyncio
async def test_webhook_valid_signature(client: AsyncClient):
    secret = "test-webhook-secret"
    payload = {
        "event": "transaction.completed",
        "transactionId": "txn-001",
        "userId": "1",
        "amount": "10.00",
        "amountMinor": 1000,
        "currency": "LYD",
        "gateway": "sadad",
        "merchantReference": "PPV2-TEST0000000001",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    sig, ts, body = sign_and_body(payload, secret)

    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={
            "x-signature": sig,
            "x-timestamp": ts,
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    payload = {
        "event": "transaction.completed",
        "transaction_id": "txn-002",
        "user_id": "1",
        "amount": "10.00",
        "amount_minor": 1000,
        "currency": "LYD",
        "gateway": "sadad",
        "merchant_reference": "PPV2-TEST0000000002",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    body = json.dumps(payload, separators=(",", ":")).encode()

    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={
            "x-signature": "sha256=invalidsignature",
            "x-timestamp": "1234567890",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_missing_signature(client: AsyncClient):
    payload = {"event": "transaction.completed", "transaction_id": "txn-003"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_invalid_payload(client: AsyncClient):
    secret = "test-webhook-secret"
    payload = {"event": "bad"}
    sig, ts, body = sign_and_body(payload, secret)

    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={
            "x-signature": sig,
            "x-timestamp": ts,
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_failed_event(client: AsyncClient):
    secret = "test-webhook-secret"
    payload = {
        "event": "transaction.failed",
        "transactionId": "txn-004",
        "userId": "1",
        "amount": "5.00",
        "amountMinor": 500,
        "currency": "LYD",
        "gateway": "edfali",
        "merchantReference": "PPV2-TEST0000000003",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    sig, ts, body = sign_and_body(payload, secret)

    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={
            "x-signature": sig,
            "x-timestamp": ts,
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_webhook_expired_event(client: AsyncClient):
    secret = "test-webhook-secret"
    payload = {
        "event": "transaction.expired",
        "transactionId": "txn-005",
        "userId": "1",
        "amount": "3.00",
        "amountMinor": 300,
        "currency": "LYD",
        "gateway": "moamalat",
        "merchantReference": "PPV2-TEST0000000004",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    sig, ts, body = sign_and_body(payload, secret)

    resp = await client.post(
        "/webhooks/payment",
        content=body,
        headers={
            "x-signature": sig,
            "x-timestamp": ts,
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
