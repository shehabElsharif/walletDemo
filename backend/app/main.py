import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, wallet, webhook
from app.services.payment_client import close_client
from app.ws_manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def register_with_platform():
    if not settings.webhook_secret:
        log.warning("No WEBHOOK_SECRET configured, skipping platform registration")
        return

    if settings.platform_api_key:
        log.info("platform_api_key already configured, skipping registration")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.platform_url}/admin/clients",
            headers={
                "x-admin-key": settings.platform_admin_key,
                "Content-Type": "application/json",
            },
            json={
                "name": "wallet-demo",
                "webhookUrl": f"http://127.0.0.1:8000/webhooks/payment",
                "webhookSecret": settings.webhook_secret,
            },
        )
        if resp.status_code == 201:
            data = resp.json()
            settings.platform_api_key = data["apiKey"]
            log.info("registered with payment platform, client_id=%s, apiKey=%s", data["client"]["id"], data["apiKey"])
        elif resp.status_code == 409:
            log.warning("already registered — set PLATFORM_API_KEY env var to avoid this warning")
        else:
            log.error("failed to register: %s %s", resp.status_code, resp.text)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("database initialized")
    await register_with_platform()
    yield
    await close_client()
    log.info("shutdown complete")


app = FastAPI(title="Wallet Demo", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(wallet.router, prefix="/api")
app.include_router(webhook.router)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    from app.routers.auth import decode_token

    if not token:
        await ws.close(code=4001, reason="Missing token")
        return

    try:
        user_id = decode_token(token)
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
