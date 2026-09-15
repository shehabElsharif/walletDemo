import json
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections[user_id].append(ws)
        log.info("ws connected", extra={"user_id": user_id, "total": len(self._connections[user_id])})

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns and user_id in self._connections:
            del self._connections[user_id]

    async def send_balance(self, user_id: int, balance_minor: int, currency: str = "LYD"):
        conns = self._connections.get(user_id, [])
        message = json.dumps({
            "type": "balance_updated",
            "balance_minor": balance_minor,
            "balance": f"{balance_minor / 100:.2f}",
            "currency": currency,
        })
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)


manager = ConnectionManager()
