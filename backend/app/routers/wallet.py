import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas import ConfirmOtpRequest, TopupRequest, TopupResponse, WalletResponse
from app.services import payment_client, wallet_service
from app.services.payment_client import GatewayError
from app.ws_manager import manager

router = APIRouter(prefix="/wallet", tags=["wallet"])
bearer_scheme = HTTPBearer()


async def require_user(cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> int:
    from app.routers.auth import decode_token
    return decode_token(cred.credentials)


@router.get("", response_model=WalletResponse)
async def get_balance(user_id: int = Depends(require_user), db: AsyncSession = Depends(get_db)):
    wallet = await wallet_service.get_wallet(db, user_id)
    return WalletResponse(
        balance=f"{wallet.balance_minor / 100:.2f}",
        balance_minor=wallet.balance_minor,
    )


@router.post("/topup", response_model=TopupResponse)
async def topup(
    body: TopupRequest,
    user_id: int = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    idempotency_key = f"wallet-{user_id}-{uuid.uuid4().hex[:16]}"

    try:
        result = await payment_client.create_transaction(
            api_key=settings.platform_api_key,
            user_id=str(user_id),
            gateway=body.gateway,
            amount=body.amount,
            idempotency_key=idempotency_key,
            msisdn=body.msisdn,
            birth_year=body.birth_year,
            description=f"Wallet top-up {body.amount} LYD via {body.gateway}",
            gateway_env=body.gateway_env,
        )
    except GatewayError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment platform error: {e}")

    amount_minor = int(round(body.amount * 100))
    await wallet_service.create_topup_request(
        db,
        user_id=user_id,
        transaction_id=result["transactionId"],
        merchant_reference=result.get("merchantReference"),
        amount_minor=amount_minor,
        gateway=body.gateway,
    )
    await db.commit()

    checkout_url = result.get("checkoutUrl")
    status = result.get("status", "initiated")
    msg = ""
    if status == "initiated" and body.gateway in ("sadad", "edfali"):
        msg = "OTP sent to your phone"
        if body.gateway == "edfali" and body.gateway_env != "prod":
            msg += " (test: enter 1234)"

    return TopupResponse(
        transaction_id=result["transactionId"],
        status=status,
        checkout_url=checkout_url,
        message=msg,
    )


@router.post("/topup/confirm", response_model=WalletResponse)
async def confirm_topup(
    body: ConfirmOtpRequest,
    user_id: int = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    # Ownership check: verify this transaction belongs to the requesting user
    from sqlalchemy import select
    from app.models import TopupRequest as TopupRequestModel
    result_check = await db.execute(
        select(TopupRequestModel).where(
            TopupRequestModel.transaction_id == body.transaction_id,
            TopupRequestModel.user_id == user_id,
        )
    )
    topup_req = result_check.scalar_one_or_none()
    if not topup_req:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        result = await payment_client.confirm_transaction(
            api_key=settings.platform_api_key,
            transaction_id=body.transaction_id,
            otp=body.otp,
        )
    except GatewayError as e:
        await wallet_service.update_topup_status(db, body.transaction_id, "failed")
        await db.commit()
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment platform error: {e}")

    status = result.get("status", "failed")
    if status == "success":
        # Credit wallet immediately instead of waiting for webhook
        credited = await wallet_service.credit_wallet_once(db, user_id, topup_req.amount_minor, body.transaction_id)
        if credited:
            await wallet_service.update_topup_status(db, body.transaction_id, "completed")
            await db.commit()
            wallet = await wallet_service.get_wallet(db, user_id)
            await manager.send_balance(user_id, wallet.balance_minor)
        else:
            await wallet_service.update_topup_status(db, body.transaction_id, "completed")
            await db.commit()
            wallet = await wallet_service.get_wallet(db, user_id)
    else:
        gateway_msg = result.get("gatewayMessage") or result.get("message") or "OTP confirmation failed"
        await wallet_service.update_topup_status(db, body.transaction_id, "failed")
        await db.commit()
        raise HTTPException(status_code=422, detail=gateway_msg)

    wallet = await wallet_service.get_wallet(db, user_id)
    return WalletResponse(
        balance=f"{wallet.balance_minor / 100:.2f}",
        balance_minor=wallet.balance_minor,
    )
