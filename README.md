# Wallet Demo

A demo wallet app that integrates with `paymentPlatform-v2` to accept payments via three Libyan gateways: **Moamalat**, **Sadad**, and **Edfali**.

## Architecture

```
Android App  ←──WebSocket/REST──→  FastAPI Backend  ←──REST/Webhooks──→  PaymentPlatform-v2
```

### Backend (Python + FastAPI)
- Runs on port `8000`
- Manages user accounts and wallet balances
- Calls paymentPlatform-v2 API to initiate/confirm payments
- Receives webhooks when payments complete and credits the wallet
- Pushes real-time balance updates via WebSocket

### Android App (Kotlin + Jetpack Compose)
- Connects to backend via REST + WebSocket
- Shows wallet balance with real-time updates
- Supports all 3 payment gateways
- Moamalat: opens checkout page in WebView
- Sadad/Edfali: OTP confirmation flow

## Quick Start

### 1. Start Payment Platform

```bash
cd ../paymentPlatform-v2
docker compose up -d
```

### 2. Start Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials (provided by platform admin)
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open Android App

Open `android/` in Android Studio, build and run on emulator or device.

**Emulator note:** The app connects to `10.0.2.2:8000` (Android emulator's alias for host machine).

**Real device:** Change the base URL in `ApiClient.kt` to your server's IP:
```kotlin
// Change this to your backend server address
private var baseUrl: String = "http://YOUR_SERVER_IP:8000"
```

## Configuration

Backend environment (`.env` file in `backend/` — copy from `.env.example`):
```env
PLATFORM_URL=http://127.0.0.1:8081
PLATFORM_API_KEY=pk_live_...        # Provided by platform admin
WEBHOOK_SECRET=your-webhook-secret  # Provided by platform admin
JWT_SECRET=your-jwt-secret
```

**Important:** The platform admin creates your client account and provides the `PLATFORM_API_KEY` and `WEBHOOK_SECRET`. You do not register yourself.

## Test Credentials

| Gateway | Phone / Card | OTP / Details |
|---------|-------------|---------------|
| **Sadad** | Phone: `0935598513` | OTP sent via SMS — ask the platform admin for the code |
| **Moamalat** | Card: `6395043165743733` | EXP: `01/27`, CVV: any 3 digits |
| **Edfali** | Any valid Libyan number | OTP: `1234` |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/auth/register` | None | Create account |
| `POST` | `/api/auth/login` | None | Login |
| `GET` | `/api/wallet` | JWT | Get balance |
| `POST` | `/api/wallet/topup` | JWT | Initiate payment |
| `POST` | `/api/wallet/topup/confirm` | JWT | Confirm with OTP |
| `WS` | `/ws?token=<jwt>` | JWT | Real-time balance |
| `POST` | `/webhooks/payment` | HMAC-SHA256 | Platform webhook |

## Running Tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

## Verifying the Setup

### 1. Check server health

```bash
curl http://127.0.0.1:8000/healthz
# Expected: {"status":"ok"}
```

### 2. Register a user

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234"}'
# Returns: {"access_token":"eyJ...","token_type":"bearer"}
```

Save the `access_token` — you'll need it for all subsequent requests.

### 3. Login

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234"}'
# Returns same JWT token
```

### 4. Check wallet balance

```bash
curl http://127.0.0.1:8000/api/wallet \
  -H "Authorization: Bearer YOUR_TOKEN"
# Returns: {"balance":"0.00","balance_minor":0,"currency":"LYD"}
```

### 5. Test a payment (Edfali example)

**Note:** `edfali` and `sadad` require `msisdn`. `moamalat` does not.

```bash
# Initiate top-up
curl -X POST http://127.0.0.1:8000/api/wallet/topup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":10,"gateway":"edfali","msisdn":"0935598513","gateway_env":"test"}'
# Returns: {"transaction_id":"...","status":"initiated","message":"OTP sent to your phone"}

# Confirm with OTP (use 1234 for edfali test)
curl -X POST http://127.0.0.1:8000/api/wallet/topup/confirm \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"TRANSACTION_ID_HERE","otp":"1234"}'
```

### 6. Verify wallet updated

Wait a few seconds for the webhook to deliver, then:

```bash
curl http://127.0.0.1:8000/api/wallet \
  -H "Authorization: Bearer YOUR_TOKEN"
# Returns: {"balance":"10.00","balance_minor":1000,"currency":"LYD"}
```

If the balance updates, the full payment flow is working.

### Gateway-specific notes

| Gateway | Required fields | OTP |
|---------|----------------|-----|
| **edfali** | `msisdn` | `1234` (test) |
| **sadad** | `msisdn` | SMS code — ask platform admin |
| **moamalat** | none (uses WebView checkout) | N/A |

## Payment Flow

1. User enters amount and selects gateway in the app
2. App calls `POST /api/wallet/topup`
3. Backend calls paymentPlatform-v2 to create a transaction
4. **Sadad/Edfali:** App shows OTP input screen → user enters OTP → app calls `POST /api/wallet/topup/confirm`
5. **Moamalat:** App opens checkout page in WebView
6. Payment platform processes payment, sends webhook to backend
7. Backend credits wallet and pushes updated balance via WebSocket
8. App shows updated balance in real-time
