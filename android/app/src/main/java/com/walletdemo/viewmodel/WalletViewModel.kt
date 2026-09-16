package com.walletdemo.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.walletdemo.BuildConfig
import com.walletdemo.data.ApiClient
import com.walletdemo.data.ConfirmOtpRequest
import com.walletdemo.data.TokenStore
import com.walletdemo.data.TopupConfirmRequest
import com.walletdemo.data.TopupRequest
import com.walletdemo.data.WebSocketClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import retrofit2.Response

data class WalletState(
    val isLoading: Boolean = false,
    val balance: String = "0.00",
    val balanceMinor: Int = 0,
    val error: String? = null,
    val topupResult: TopupState? = null
)

data class TopupState(
    val transactionId: String? = null,
    val status: String = "",
    val checkoutUrl: String? = null,
    val message: String = "",
    val needsOtp: Boolean = false
)

class WalletViewModel(application: Application) : AndroidViewModel(application) {
    private val tokenStore = TokenStore(application)
    private val wsClient = WebSocketClient()
    private var authToken: String = ""
    private val gson = Gson()

    private val _state = MutableStateFlow(WalletState())
    val state: StateFlow<WalletState> = _state

    init {
        wsClient.onBalanceUpdated = { balanceMinor, balance ->
            _state.value = _state.value.copy(
                balance = balance,
                balanceMinor = balanceMinor,
                topupResult = null
            )
        }
    }

    fun connectWebSocket() {
        if (authToken.isNotEmpty()) return
        viewModelScope.launch {
            val token = tokenStore.token.first() ?: return@launch
            authToken = "Bearer $token"
            wsClient.connect(BuildConfig.BACKEND_URL, token)
        }
    }

    fun disconnectWebSocket() {
        wsClient.disconnect()
    }

    fun resetAuth() {
        authToken = ""
        _state.value = WalletState()
    }

    private fun parseError(resp: Response<*>): String {
        val body = resp.errorBody()?.string() ?: return "Unknown error"
        return try {
            val map = gson.fromJson(body, Map::class.java)
            map["detail"] as? String ?: body
        } catch (_: Exception) {
            body
        }
    }

    fun loadBalance() {
        viewModelScope.launch {
            if (authToken.isEmpty()) {
                val token = tokenStore.token.first() ?: run {
                    _state.value = _state.value.copy(isLoading = false, error = "Not authenticated")
                    return@launch
                }
                authToken = "Bearer $token"
            }
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = ApiClient.api.getBalance(authToken)
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    _state.value = _state.value.copy(
                        isLoading = false,
                        balance = body.balance,
                        balanceMinor = body.balanceMinor
                    )
                } else {
                    _state.value = _state.value.copy(isLoading = false, error = parseError(resp))
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun topup(amount: Double, gateway: String, msisdn: String? = null, birthYear: String? = null, gatewayEnv: String = "test") {
        viewModelScope.launch {
            if (authToken.isEmpty()) {
                val token = tokenStore.token.first() ?: run {
                    _state.value = _state.value.copy(isLoading = false, error = "Not authenticated")
                    return@launch
                }
                authToken = "Bearer $token"
            }
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = ApiClient.api.topup(authToken, TopupRequest(amount, gateway, msisdn, birthYear, gatewayEnv))
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    val needsOtp = body.status == "initiated" && gateway in listOf("sadad", "edfali")
                    _state.value = _state.value.copy(
                        isLoading = false,
                        topupResult = TopupState(
                            transactionId = body.transactionId,
                            status = body.status,
                            checkoutUrl = body.checkoutUrl,
                            message = body.message,
                            needsOtp = needsOtp
                        )
                    )
                } else {
                    _state.value = _state.value.copy(isLoading = false, error = parseError(resp))
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun confirmOtp(transactionId: String, otp: String) {
        viewModelScope.launch {
            if (authToken.isEmpty()) {
                val token = tokenStore.token.first() ?: run {
                    _state.value = _state.value.copy(isLoading = false, error = "Not authenticated")
                    return@launch
                }
                authToken = "Bearer $token"
            }
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = ApiClient.api.confirmTopup(authToken, TopupConfirmRequest(transactionId, otp))
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    _state.value = _state.value.copy(
                        isLoading = false,
                        balance = body.balance,
                        balanceMinor = body.balanceMinor,
                        topupResult = null
                    )
                } else {
                    _state.value = _state.value.copy(isLoading = false, error = parseError(resp))
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun clearTopupResult() {
        _state.value = _state.value.copy(topupResult = null)
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }
}
