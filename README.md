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
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open Android App

Open `android/` in Android Studio, build and run on emulator or device.

**Emulator note:** The app connects to `10.0.2.2:8000` (Android emulator's alias for host machine).

**Real device:** Change the base URL in `ApiClient.kt` to your server's IP:
```kotlin
private var baseUrl: String = "http://100.109.134.3:8000"
```

## Configuration

Backend environment (`.env` file in `backend/`):
```env
PLATFORM_URL=http://127.0.0.1:8081
PLATFORM_ADMIN_KEY=change-me-admin-key
WEBHOOK_SECRET=your-webhook-secret-here
JWT_SECRET=your-jwt-secret-here
```

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

## Payment Flow

1. User enters amount and selects gateway in the app
2. App calls `POST /api/wallet/topup`
3. Backend calls paymentPlatform-v2 to create a transaction
4. **Sadad/Edfali:** App shows OTP input screen → user enters OTP → app calls `POST /api/wallet/topup/confirm`
5. **Moamalat:** App opens checkout page in WebView
6. Payment platform processes payment, sends webhook to backend
7. Backend credits wallet and pushes updated balance via WebSocket
8. App shows updated balance in real-time
