import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas import WebhookPayload
from app.services import wallet_service
from app.ws_manager import manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(payload_body: bytes, timestamp: str, signature_header: str, secret: str) -> bool:
    if not signature_header or not timestamp or not secret:
        log.warning("webhook verify: missing params")
        return False
    data = f"{timestamp}.{payload_body.decode()}"
    expected = "sha256=" + hmac.new(
        secret.encode(), data.encode(), hashlib.sha256
    ).hexdigest()
    match = hmac.compare_digest(expected, signature_header)
    if not match:
        log.warning("SIG MISMATCH expected=%s got=%s ts=%s body=%s",
                     expected[:40], signature_header[:40], timestamp, payload_body.decode()[:500])
    return match


@router.post("/payment")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    timestamp = request.headers.get("x-timestamp", "")
    signature = request.headers.get("x-signature", "")

    if not verify_signature(body, timestamp, signature, settings.webhook_secret):
        log.warning("webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    log.info(
        "webhook received",
        extra={"event": payload.event, "transaction_id": payload.transaction_id},
    )

    if payload.event == "transaction.completed":
        user_id = int(payload.user_id)
        try:
            credited = await wallet_service.credit_wallet_once(db, user_id, payload.amount_minor, payload.transaction_id)
            if credited:
                await wallet_service.update_topup_status(db, payload.transaction_id, "completed")
                await db.commit()
                wallet = await wallet_service.get_wallet(db, user_id)
                await manager.send_balance(user_id, wallet.balance_minor)
            else:
                log.info("webhook: already credited, skipping", extra={"transaction_id": payload.transaction_id})
        except ValueError:
            log.warning("wallet not found for webhook user_id=%s", user_id)

    elif payload.event in ("transaction.failed", "transaction.expired"):
        await wallet_service.update_topup_status(db, payload.transaction_id, payload.event.split(".")[-1])
        await db.commit()

    return {"ok": True}
