package com.walletdemo.data

import com.google.gson.annotations.SerializedName

data class RegisterRequest(
    val username: String,
    val password: String
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class WalletResponse(
    val balance: String,
    @SerializedName("balance_minor") val balanceMinor: Int,
    val currency: String
)

data class TopupRequest(
    val amount: Double,
    val gateway: String,
    val msisdn: String? = null,
    @SerializedName("birth_year") val birthYear: String? = null,
    @SerializedName("gateway_env") val gatewayEnv: String = "test"
)

data class TopupResponse(
    @SerializedName("transaction_id") val transactionId: String,
    val status: String,
    @SerializedName("checkout_url") val checkoutUrl: String? = null,
    val message: String = ""
)

data class ConfirmOtpRequest(
    @SerializedName("transaction_id") val transactionId: String,
    val otp: String
)

data class TopupConfirmRequest(
    @SerializedName("transaction_id") val transactionId: String,
    val otp: String
)

data class WebSocketMessage(
    val type: String,
    @SerializedName("balance_minor") val balanceMinor: Int? = null,
    val balance: String? = null,
    val currency: String? = null
)
