from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=4, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WalletResponse(BaseModel):
    balance: str
    balance_minor: int
    currency: str = "LYD"


class TopupRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount in LYD")
    gateway: str = Field(pattern=r"^(moamalat|sadad|edfali)$")
    msisdn: str | None = Field(default=None, pattern=r"^[0-9+]{6,16}$")
    birth_year: str | None = Field(default=None, pattern=r"^\d{4}$")
    gateway_env: str = Field(default="test", pattern=r"^(test|prod)$")


class TopupResponse(BaseModel):
    transaction_id: str
    status: str
    checkout_url: str | None = None
    message: str = ""


class ConfirmOtpRequest(BaseModel):
    transaction_id: str
    otp: str = Field(min_length=1, max_length=10)


class WebhookPayload(BaseModel):
    event: str
    transaction_id: str = Field(alias="transactionId")
    user_id: str = Field(alias="userId")
    amount: str
    amount_minor: int = Field(alias="amountMinor")
    currency: str
    gateway: str
    merchant_reference: str = Field(alias="merchantReference")
    timestamp: str
