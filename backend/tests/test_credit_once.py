import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import TopupRequest, User, Wallet
from app.services.wallet_service import credit_wallet_once

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_race.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_teardown():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def seed(user_id: int, transaction_id: str, amount_minor: int):
    async with TestSession() as db:
        db.add(User(id=user_id, username=f"testuser{user_id}", password_hash="fake"))
        await db.flush()
        db.add(Wallet(user_id=user_id, balance_minor=0))
        db.add(TopupRequest(
            user_id=user_id,
            transaction_id=transaction_id,
            merchant_reference=None,
            amount_minor=amount_minor,
            gateway="edfali",
            status="pending",
        ))
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with TestSession() as db:
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none().balance_minor


@pytest.mark.asyncio
async def test_idempotent_credit_returns_none_on_second_call():
    """Calling credit_wallet_once twice sequentially returns None the second time."""
    user_id = 1
    txn_id = "idempotent-001"
    amount = 2000

    await seed(user_id, txn_id, amount)

    # First call — credits and commits
    async with TestSession() as db:
        result1 = await credit_wallet_once(db, user_id, amount, txn_id)
        assert result1 is not None, "First call should credit"
        await db.commit()

    # Second call in a fresh session — must return None
    async with TestSession() as db:
        result2 = await credit_wallet_once(db, user_id, amount, txn_id)
        assert result2 is None, "Second call should return None"

    balance = await get_balance(user_id)
    assert balance == amount, f"Balance should be {amount}, got {balance}"


@pytest.mark.asyncio
async def test_credit_with_already_completed_status():
    """If status is already 'completed', credit must be skipped."""
    user_id = 2
    txn_id = "completed-001"
    amount = 1000

    await seed(user_id, txn_id, amount)

    # Set status to 'completed' (mimics confirm flow)
    async with TestSession() as db:
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(TopupRequest)
            .where(TopupRequest.transaction_id == txn_id)
            .values(status="completed")
        )
        await db.commit()

    async with TestSession() as db:
        result = await credit_wallet_once(db, user_id, amount, txn_id)
        assert result is None, "Should not credit when status is 'completed'"

    balance = await get_balance(user_id)
    assert balance == 0, f"Balance should be 0, got {balance}"


@pytest.mark.asyncio
async def test_concurrent_credit_only_one_succeeds():
    """Two sessions try to credit the same transaction.
    The atomic UPDATE WHERE status='pending' guarantees exactly one wins."""
    user_id = 3
    txn_id = "race-001"
    amount = 5000

    await seed(user_id, txn_id, amount)

    results = []

    async def caller(session_id: int):
        async with TestSession() as db:
            r = await credit_wallet_once(db, user_id, amount, txn_id)
            if r is not None:
                await db.commit()
            results.append(r)

    # Fire both concurrently — SQLite serializes at the write lock level
    await asyncio.gather(caller(1), caller(2))

    credited = [r for r in results if r is not None]
    skipped = [r for r in results if r is None]
    assert len(credited) == 1, f"Expected exactly 1 credit, got {len(credited)}"
    assert len(skipped) == 1, f"Expected exactly 1 skip, got {len(skipped)}"

    balance = await get_balance(user_id)
    assert balance == amount, f"Balance should be {amount}, got {balance}"


@pytest.mark.asyncio
async def test_concurrent_credit_with_confirm_and_webhook():
    """Simulates confirm endpoint (credits + commits) racing with webhook (credits).
    If confirm commits first, webhook must see 'credited' and skip."""
    user_id = 4
    txn_id = "race-002"
    amount = 3000

    await seed(user_id, txn_id, amount)

    async def confirm_flow():
        async with TestSession() as db:
            credited = await credit_wallet_once(db, user_id, amount, txn_id)
            if credited:
                from sqlalchemy import update as sa_update
                await db.execute(
                    sa_update(TopupRequest)
                    .where(TopupRequest.transaction_id == txn_id)
                    .values(status="completed")
                )
                await db.commit()
            return credited

    async def webhook_flow():
        # Small delay so confirm starts first
        await asyncio.sleep(0.05)
        async with TestSession() as db:
            return await credit_wallet_once(db, user_id, amount, txn_id)

    results = await asyncio.gather(confirm_flow(), webhook_flow())

    credited = [r for r in results if r is not None]
    balance = await get_balance(user_id)
    assert len(credited) == 1, f"Expected exactly 1 credit, got {len(credited)}"
    assert balance == amount, f"Balance should be {amount}, got {balance}"


@pytest.mark.asyncio
async def test_webhook_before_confirm_still_only_once():
    """If webhook arrives before confirm, webhook credits first, confirm skips.

    NOTE: This test verifies the logic by running sequentially (webhook commits,
    then confirm reads). True concurrent UPDATE serialization is guaranteed by
    PostgreSQL's row-level locking in production — SQLite can't simulate that
    with asyncio.gather on a single thread."""
    user_id = 5
    txn_id = "race-003"
    amount = 4000

    await seed(user_id, txn_id, amount)

    # Webhook commits first
    async with TestSession() as db:
        r = await credit_wallet_once(db, user_id, amount, txn_id)
        assert r is not None, "Webhook should credit"
        await db.commit()

    # Confirm reads after webhook committed — must skip
    async with TestSession() as db:
        credited = await credit_wallet_once(db, user_id, amount, txn_id)
        assert credited is None, "Confirm should skip after webhook already credited"

    balance = await get_balance(user_id)
    assert balance == amount, f"Balance should be {amount}, got {balance}"
