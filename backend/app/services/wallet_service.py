import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TopupRequest, Wallet

log = logging.getLogger(__name__)


async def get_wallet(db: AsyncSession, user_id: int) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise ValueError("Wallet not found")
    return wallet


async def credit_wallet(db: AsyncSession, user_id: int, amount_minor: int, ref: str) -> Wallet:
    wallet = await get_wallet(db, user_id)
    wallet.balance_minor += amount_minor
    log.info("wallet credited", extra={"user_id": user_id, "amount_minor": amount_minor, "ref": ref})
    return wallet


async def credit_wallet_once(db: AsyncSession, user_id: int, amount_minor: int, transaction_id: str) -> Wallet | None:
    # Atomic UPDATE: only one caller can flip 'pending' → 'credited'.
    # On PostgreSQL this serializes via row-level locking; on SQLite via
    # the single-writer model. Either way, rowcount==0 means someone else
    # already claimed it.
    result = await db.execute(
        update(TopupRequest)
        .where(
            TopupRequest.transaction_id == transaction_id,
            TopupRequest.status == "pending",
        )
        .values(status="credited")
    )
    if result.rowcount == 0:
        return None  # already credited, completed, or not found

    wallet = await get_wallet(db, user_id)
    wallet.balance_minor += amount_minor
    log.info("wallet credited", extra={"user_id": user_id, "amount_minor": amount_minor, "ref": transaction_id})
    return wallet


async def create_topup_request(
    db: AsyncSession,
    *,
    user_id: int,
    transaction_id: str,
    merchant_reference: str | None,
    amount_minor: int,
    gateway: str,
) -> TopupRequest:
    req = TopupRequest(
        user_id=user_id,
        transaction_id=transaction_id,
        merchant_reference=merchant_reference,
        amount_minor=amount_minor,
        gateway=gateway,
        status="pending",
    )
    db.add(req)
    await db.flush()
    return req


async def update_topup_status(db: AsyncSession, transaction_id: str, status: str) -> TopupRequest | None:
    result = await db.execute(
        select(TopupRequest).where(TopupRequest.transaction_id == transaction_id)
    )
    req = result.scalar_one_or_none()
    if req:
        req.status = status
    return req
